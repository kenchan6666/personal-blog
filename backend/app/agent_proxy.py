from __future__ import annotations

import asyncio
import codecs
import json
import re
from collections.abc import AsyncIterator, Callable
from time import monotonic
from typing import Any, Literal

import httpx
from beanie import PydanticObjectId
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from app.agent_activity import rewrite_owner_sse_block
from app.agent_budget import owner_chat_max_tokens, strip_tool_noise
from app.agent_limits import owner_turn_available
from app.agent_rag import AgentRag, knowledge_context
from app.models import AgentConversation, AgentMessage, KnowledgeRecord, utc_now
from app.store import current_store, new_document

_SESSION_RE = re.compile(r"[^a-zA-Z0-9_-]")
_KNOWLEDGE_CATEGORIES = {
    "identity",
    "experience",
    "education",
    "skills",
    "project",
    "preference",
    "other",
}


def pin_changed_knowledge_rows(
    rows: list[KnowledgeRecord],
    changed_ids: list[str],
) -> list[KnowledgeRecord]:
    wanted = set(changed_ids)
    head = [row for row in rows if str(row.id) in wanted]
    tail = [row for row in rows if str(row.id) not in wanted]
    return head + tail


class ConversationCreate(BaseModel):
    title: str = "新对话"


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=80)


class ConversationRewind(BaseModel):
    index: int = Field(ge=0)
    content: str = Field(min_length=1, max_length=20000)


class KnowledgeWrite(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    category: Literal[
        "identity",
        "experience",
        "education",
        "skills",
        "project",
        "preference",
        "other",
    ] = "other"
    content: str = Field(min_length=1, max_length=20000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    order: int = 0


def _agent_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _session_id(value: Any) -> str:
    clean = _SESSION_RE.sub("-", str(value or "main"))[:80].strip("-")
    return f"portfolio-owner-{clean or 'main'}"


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _sse_delta(block: str) -> str:
    data = "\n".join(
        line[5:].lstrip()
        for line in block.splitlines()
        if line.startswith("data:")
    )
    if not data or data == "[DONE]":
        return ""
    try:
        payload = json.loads(data)
        value = payload.get("choices", [{}])[0].get("delta", {}).get("content")
        return value if isinstance(value, str) else ""
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError):
        return ""


def empty_turn_sse() -> bytes:
    return (
        "event: error\n"
        f"data: {json.dumps({'message': '这一轮没有收到完整回复，请再试一次。'}, ensure_ascii=False)}\n\n"
    ).encode()


async def _sync_knowledge(rag: AgentRag, record: KnowledgeRecord) -> None:
    record.vector_synced, record.vector_sync_error = await rag.sync_with_status(record)
    record.updated_at = utc_now()
    await current_store().save(record)


async def sync_stale_knowledge(settings: Any) -> None:
    rag = AgentRag(settings)
    rows = await current_store().find_all(KnowledgeRecord)
    for row in rows:
        if row.vector_synced:
            continue
        try:
            await _sync_knowledge(rag, row)
        except Exception:
            continue


def register_agent_routes(
    app: FastAPI,
    require_owner: Callable[..., Any],
) -> None:
    rag = AgentRag(app.state.settings)
    app.state.agent_turns = {}

    @app.get("/api/owner/agent/conversations")
    async def list_conversations(
        _: str = Depends(require_owner),
    ) -> list[dict[str, Any]]:
        rows = await current_store().find_all(AgentConversation)
        rows.sort(key=lambda row: row.updated_at, reverse=True)
        return [row.to_summary_dict() for row in rows]

    @app.post("/api/owner/agent/conversations")
    async def create_conversation(
        body: ConversationCreate,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        title = body.title.strip()[:80] or "新对话"
        row = new_document(AgentConversation, title=title)
        await current_store().insert(row)
        return row.to_owner_dict()

    @app.get("/api/owner/agent/conversations/{conversation_id}")
    async def get_conversation(
        conversation_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        row = await current_store().get(AgentConversation, conversation_id)
        if row is None:
            raise _not_found("agent_conversation_not_found")
        return row.to_owner_dict()

    @app.patch("/api/owner/agent/conversations/{conversation_id}")
    async def update_conversation(
        conversation_id: PydanticObjectId,
        body: ConversationUpdate,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        row = await current_store().get(AgentConversation, conversation_id)
        if row is None:
            raise _not_found("agent_conversation_not_found")
        row.title = body.title.strip()
        row.updated_at = utc_now()
        await current_store().save(row)
        return row.to_summary_dict()

    @app.delete("/api/owner/agent/conversations/{conversation_id}")
    async def delete_conversation(
        conversation_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, bool]:
        row = await current_store().get(AgentConversation, conversation_id)
        if row is None:
            raise _not_found("agent_conversation_not_found")
        await current_store().delete(row)
        return {"ok": True}

    @app.get("/api/owner/agent/knowledge")
    async def list_knowledge(
        _: str = Depends(require_owner),
    ) -> list[dict[str, Any]]:
        rows = await current_store().find_all(KnowledgeRecord)
        rows.sort(key=lambda row: (row.order, row.updated_at), reverse=True)
        return [row.to_owner_dict() for row in rows]

    @app.post("/api/owner/agent/knowledge/sync")
    async def sync_all_knowledge(
        _: str = Depends(require_owner),
    ) -> list[dict[str, Any]]:
        rows = await current_store().find_all(KnowledgeRecord)
        for row in rows:
            await _sync_knowledge(rag, row)
        if any(
            row.vector_sync_error == "vector_dimension_mismatch" for row in rows
        ) and await rag.reset_collection():
            for row in rows:
                await _sync_knowledge(rag, row)
        rows.sort(key=lambda row: (row.order, row.updated_at), reverse=True)
        return [row.to_owner_dict() for row in rows]

    @app.post("/api/owner/agent/knowledge/{record_id}/sync")
    async def sync_one_knowledge(
        record_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        row = await current_store().get(KnowledgeRecord, record_id)
        if row is None:
            raise _not_found("agent_knowledge_not_found")
        await _sync_knowledge(rag, row)
        if (
            row.vector_sync_error == "vector_dimension_mismatch"
            and await rag.reset_collection()
        ):
            await _sync_knowledge(rag, row)
        return row.to_owner_dict()

    @app.post("/api/owner/agent/knowledge")
    async def create_knowledge(
        body: KnowledgeWrite,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        row = new_document(
            KnowledgeRecord,
            title=body.title.strip(),
            category=body.category,
            content=body.content.strip(),
            tags=[tag.strip()[:40] for tag in body.tags if tag.strip()],
            order=body.order,
        )
        await current_store().insert(row)
        await _sync_knowledge(rag, row)
        return row.to_owner_dict()

    @app.put("/api/owner/agent/knowledge/{record_id}")
    async def update_knowledge(
        record_id: PydanticObjectId,
        body: KnowledgeWrite,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        row = await current_store().get(KnowledgeRecord, record_id)
        if row is None:
            raise _not_found("agent_knowledge_not_found")
        row.title = body.title.strip()
        row.category = body.category
        row.content = body.content.strip()
        row.tags = [tag.strip()[:40] for tag in body.tags if tag.strip()]
        row.order = body.order
        row.updated_at = utc_now()
        row.vector_synced = False
        row.vector_sync_error = ""
        await current_store().save(row)
        await _sync_knowledge(rag, row)
        return row.to_owner_dict()

    @app.delete("/api/owner/agent/knowledge/{record_id}")
    async def delete_knowledge(
        record_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, bool]:
        row = await current_store().get(KnowledgeRecord, record_id)
        if row is None:
            raise _not_found("agent_knowledge_not_found")
        await current_store().delete(row)
        await rag.delete(str(record_id))
        return {"ok": True}

    @app.post("/api/owner/agent/chat")
    async def owner_agent_chat(
        request: Request,
        _: str = Depends(require_owner),
    ) -> StreamingResponse:
        settings = app.state.settings
        if not settings.agent_api_url.strip():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="agent_not_configured",
            )

        content_type = request.headers.get("content-type", "")
        files: list[tuple[str, tuple[str, bytes, str]]] = []
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            message = str(form.get("message") or "").strip()
            editor_context = str(form.get("context") or "").strip()
            conversation_id = str(form.get("conversation_id") or "")
            total_bytes = 0
            file_names: list[str] = []
            for _, item in form.multi_items():
                if not isinstance(item, UploadFile):
                    continue
                raw = await item.read()
                total_bytes += len(raw)
                if total_bytes > settings.agent_upload_max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="agent_file_too_large",
                    )
                file_names.append(item.filename or "upload.bin")
                files.append(
                    (
                        "files",
                        (
                            item.filename or "upload.bin",
                            raw,
                            item.content_type or "application/octet-stream",
                        ),
                    )
                )
        else:
            try:
                body = await request.json()
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="invalid_agent_request",
                ) from None
            message = str(body.get("message") or "").strip()
            editor_context = str(body.get("context") or "").strip()
            conversation_id = str(body.get("conversation_id") or "")
            file_names = []

        if not message and not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="agent_message_required",
            )
        try:
            parsed_id = PydanticObjectId(conversation_id)
        except (ValueError, TypeError):
            raise _not_found("agent_conversation_not_found") from None
        conversation = await current_store().get(AgentConversation, parsed_id)
        if conversation is None:
            raise _not_found("agent_conversation_not_found")

        turn_key = str(parsed_id)
        turns: dict[str, asyncio.Task[None]] = app.state.agent_turns
        running = turns.get(turn_key)
        if running is not None and not running.done():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="agent_turn_in_progress",
            )
        if not owner_turn_available(turns, settings.owner_agent_max_concurrent):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="agent_too_many_turns",
            )

        display_message = message or "请分析这些文件。"
        conversation.messages.append(
            AgentMessage(role="user", content=display_message, files=file_names)
        )
        if not conversation.messages[:-1] and conversation.title == "新对话":
            conversation.title = display_message.replace("\n", " ")[:36]
        conversation.thinking = True
        conversation.thinking_at = utc_now()
        conversation.updated_at = utc_now()
        await current_store().save(conversation)

        knowledge = await current_store().find_all(KnowledgeRecord)
        matches = await rag.search(display_message, knowledge, limit=4)
        additions = [knowledge_context(matches)]
        if editor_context:
            additions.append(
                "\n\n以下是用户当前正在编辑的内容，仅用于本轮回答：\n"
                + editor_context
            )
        forwarded_message = display_message + "".join(additions)
        max_tokens = owner_chat_max_tokens(
            display_message,
            editor_context=editor_context,
        )
        target = f"{settings.agent_api_url.rstrip('/')}/v1/chat/completions"
        headers = _agent_headers(settings.agent_internal_token)
        if files:
            data = {
                "message": forwarded_message,
                "session_id": _session_id(conversation_id),
                "stream": "true",
                "max_tokens": str(max_tokens),
            }
            request_kwargs: dict[str, Any] = {"data": data, "files": files}
        else:
            request_kwargs = {
                "json": {
                    "model": "viola",
                    "stream": True,
                    "session_id": _session_id(conversation_id),
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": forwarded_message}],
                }
            }

        outbound: asyncio.Queue[bytes | None] = asyncio.Queue()

        async def persist_assistant(text: str) -> None:
            cleaned = strip_tool_noise(text)
            latest = await current_store().get(AgentConversation, parsed_id)
            if latest is None:
                return
            if cleaned and (
                not latest.messages
                or latest.messages[-1].role != "assistant"
                or latest.messages[-1].content != cleaned
            ):
                latest.messages.append(
                    AgentMessage(role="assistant", content=cleaned)
                )
            latest.thinking = False
            latest.thinking_at = None
            latest.updated_at = utc_now()
            await current_store().save(latest)

        async def consume() -> None:
            assistant = ""
            buffer = ""
            decoder = codecs.getincrementaldecoder("utf-8")()
            seen_knowledge = {
                str(row.id): (row.updated_at.isoformat(), row.vector_synced)
                for row in knowledge
            }
            last_knowledge_check = 0.0
            timeout = httpx.Timeout(620.0, connect=10.0)

            async def knowledge_update_event(
                *,
                force: bool = False,
            ) -> bytes | None:
                nonlocal last_knowledge_check, seen_knowledge
                now = monotonic()
                if not force and now - last_knowledge_check < 0.75:
                    return None
                last_knowledge_check = now
                rows = await current_store().find_all(KnowledgeRecord)
                current = {
                    str(row.id): (row.updated_at.isoformat(), row.vector_synced)
                    for row in rows
                }
                if current == seen_knowledge:
                    return None
                changed_ids = sorted(
                    record_id
                    for record_id in set(seen_knowledge) | set(current)
                    if seen_knowledge.get(record_id) != current.get(record_id)
                )
                seen_knowledge = current
                rows.sort(key=lambda row: (row.order, row.updated_at), reverse=True)
                rows = pin_changed_knowledge_rows(rows, changed_ids)
                payload = {
                    "changedIds": changed_ids,
                    "items": [row.to_owner_dict() for row in rows],
                }
                return (
                    "event: knowledge_updated\n"
                    f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                ).encode()

            try:
                try:
                    async with (
                        httpx.AsyncClient(timeout=timeout) as client,
                        client.stream(
                            "POST",
                            target,
                            headers=headers,
                            **request_kwargs,
                        ) as upstream,
                    ):
                        if upstream.status_code >= 400:
                            raw = await upstream.aread()
                            error_message = "Agent service unavailable"
                            try:
                                payload = json.loads(raw)
                                error_message = str(
                                    payload.get("error", {}).get("message")
                                    or error_message
                                )
                            except (
                                json.JSONDecodeError,
                                UnicodeDecodeError,
                                AttributeError,
                            ):
                                pass
                            await outbound.put(
                                (
                                    "event: error\n"
                                    f"data: {json.dumps({'message': error_message})}\n\n"
                                ).encode()
                            )
                            return
                        async for chunk in upstream.aiter_bytes():
                            text = decoder.decode(chunk)
                            buffer += text
                            blocks = re.split(r"\r?\n\r?\n", buffer)
                            buffer = blocks.pop()
                            for block in blocks:
                                assistant += _sse_delta(block)
                                forwarded = rewrite_owner_sse_block(block)
                                if forwarded:
                                    await outbound.put(forwarded)
                            if not buffer:
                                event = await knowledge_update_event()
                                if event is not None:
                                    await outbound.put(event)
                        buffer += decoder.decode(b"", final=True)
                        if buffer.strip():
                            assistant += _sse_delta(buffer)
                            forwarded = rewrite_owner_sse_block(buffer)
                            if forwarded:
                                await outbound.put(forwarded)
                        event = await knowledge_update_event(force=True)
                        if event is not None:
                            await outbound.put(event)
                except asyncio.CancelledError:
                    await persist_assistant(assistant)
                    raise
                except httpx.HTTPError:
                    await outbound.put(
                        b'event: error\ndata: {"message":"Agent service unavailable"}\n\n'
                    )
                    return
                cleaned = strip_tool_noise(assistant)
                await persist_assistant(assistant)
                if not cleaned:
                    await outbound.put(empty_turn_sse())
            finally:
                latest = await current_store().get(AgentConversation, parsed_id)
                if latest is not None and latest.thinking:
                    latest.thinking = False
                    latest.thinking_at = None
                    latest.updated_at = utc_now()
                    await current_store().save(latest)
                turns.pop(turn_key, None)
                await outbound.put(None)

        async def relay() -> AsyncIterator[bytes]:
            task = turns[turn_key]
            try:
                while True:
                    if await request.is_disconnected():
                        if not task.done():
                            task.cancel()
                        break
                    try:
                        item = await asyncio.wait_for(outbound.get(), timeout=0.4)
                    except TimeoutError:
                        continue
                    if item is None:
                        break
                    yield item
            finally:
                if not task.done():
                    task.cancel()

        turns[turn_key] = asyncio.create_task(consume())
        return StreamingResponse(
            relay(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

    async def _cancel_turn(turn_key: str) -> None:
        running = app.state.agent_turns.get(turn_key)
        if running is None or running.done():
            return
        running.cancel()
        try:
            await running
        except asyncio.CancelledError:
            pass

    @app.post("/api/owner/agent/conversations/{conversation_id}/stop")
    async def stop_conversation(
        conversation_id: PydanticObjectId,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        row = await current_store().get(AgentConversation, conversation_id)
        if row is None:
            raise _not_found("agent_conversation_not_found")
        await _cancel_turn(str(conversation_id))
        latest = await current_store().get(AgentConversation, conversation_id)
        if latest is None:
            raise _not_found("agent_conversation_not_found")
        if latest.thinking:
            latest.thinking = False
            latest.thinking_at = None
            latest.updated_at = utc_now()
            await current_store().save(latest)
        return latest.to_owner_dict()

    @app.post("/api/owner/agent/conversations/{conversation_id}/rewind")
    async def rewind_conversation(
        conversation_id: PydanticObjectId,
        body: ConversationRewind,
        _: str = Depends(require_owner),
    ) -> dict[str, Any]:
        row = await current_store().get(AgentConversation, conversation_id)
        if row is None:
            raise _not_found("agent_conversation_not_found")
        await _cancel_turn(str(conversation_id))
        latest = await current_store().get(AgentConversation, conversation_id)
        if latest is None:
            raise _not_found("agent_conversation_not_found")
        if body.index >= len(latest.messages):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_message_index",
            )
        if latest.messages[body.index].role != "user":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_message_index",
            )
        latest.messages = latest.messages[: body.index]
        latest.thinking = False
        latest.thinking_at = None
        latest.updated_at = utc_now()
        await current_store().save(latest)
        return latest.to_owner_dict()

    @app.get("/api/owner/agent/media/{token}")
    async def owner_agent_media(
        token: str,
        _: str = Depends(require_owner),
    ) -> Response:
        settings = app.state.settings
        url = f"{settings.agent_api_url.rstrip('/')}/v1/media/{token}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                url,
                headers=_agent_headers(settings.agent_internal_token),
            )
        if response.status_code != 200:
            raise _not_found("agent_media_not_found")
        return Response(
            content=response.content,
            media_type=response.headers.get("content-type", "application/octet-stream"),
            headers={
                "Content-Disposition": response.headers.get(
                    "content-disposition",
                    "attachment",
                )
            },
        )
