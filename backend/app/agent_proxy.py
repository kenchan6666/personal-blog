from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, status
from fastapi.responses import Response, StreamingResponse

_SESSION_RE = re.compile(r"[^a-zA-Z0-9_-]")


def _agent_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _session_id(value: Any) -> str:
    clean = _SESSION_RE.sub("-", str(value or "main"))[:80].strip("-")
    return f"portfolio-owner-{clean or 'main'}"


def register_agent_routes(
    app: FastAPI,
    require_owner: Callable[..., Any],
) -> None:
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

        target = f"{settings.agent_api_url.rstrip('/')}/v1/chat/completions"
        content_type = request.headers.get("content-type", "")
        headers = _agent_headers(settings.agent_internal_token)

        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            message = str(form.get("message") or "").strip()
            session = _session_id(form.get("session_id"))
            files: list[tuple[str, tuple[str, bytes, str]]] = []
            total_bytes = 0
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
            data = {
                "message": message or "请分析我上传的内容。",
                "session_id": session,
                "stream": "true",
            }
            request_kwargs: dict[str, Any] = {"data": data, "files": files}
        else:
            try:
                body = await request.json()
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="invalid_agent_request",
                ) from None
            message = str(body.get("message") or "").strip()
            if not message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="agent_message_required",
                )
            request_kwargs = {
                "json": {
                    "model": "viola",
                    "stream": True,
                    "session_id": _session_id(body.get("session_id")),
                    "messages": [{"role": "user", "content": message}],
                }
            }

        async def relay() -> AsyncIterator[bytes]:
            timeout = httpx.Timeout(180.0, connect=10.0)
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
                        message = "Agent service unavailable"
                        try:
                            payload = json.loads(raw)
                            message = str(payload.get("error", {}).get("message") or message)
                        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                            message = "Agent service unavailable"
                        yield (
                            "event: error\n"
                            f"data: {json.dumps({'message': message})}\n\n"
                        ).encode()
                        return
                    async for chunk in upstream.aiter_bytes():
                        yield chunk
            except httpx.HTTPError:
                yield b'event: error\ndata: {"message":"Agent service unavailable"}\n\n'

        return StreamingResponse(
            relay(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="agent_media_not_found",
            )
        return Response(
            content=response.content,
            media_type=response.headers.get("content-type", "application/octet-stream"),
            headers={
                "Content-Disposition": response.headers.get(
                    "content-disposition", "attachment"
                )
            },
        )
