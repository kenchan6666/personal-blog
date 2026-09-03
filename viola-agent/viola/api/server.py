"""OpenAI-compatible HTTP API server for a fixed viola session.

Provides /v1/chat/completions and /v1/models endpoints.
All requests route to a single persistent API session.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import hmac
import json as _json
import mimetypes
import os
import time
import uuid
from pathlib import Path
from typing import Any

from aiohttp import web
from loguru import logger

from viola.agent.legacy_field_state_strategy import FIELD_STRATEGY_VERSION
from viola.agent.legacy_role_state_strategy import ROLE_STRATEGY_VERSION
from viola.agent.tools.mcp import _sanitize_name
from viola.api.twilio_media import ingest_twilio_media_lines
from viola.config.paths import get_media_dir
from viola.utils.artifacts import discover_attachment_paths_from_text
from viola.utils.helpers import safe_filename
from viola.utils.media_decode import (
    MAX_FILE_SIZE,
)
from viola.utils.media_decode import (
    FileSizeExceeded as _FileSizeExceeded,
)
from viola.utils.media_decode import (
    save_base64_data_url as _save_base64_data_url,
)
from viola.utils.runtime import EMPTY_FINAL_RESPONSE_MESSAGE

__all__ = (
    "MAX_FILE_SIZE",
    "_FileSizeExceeded",
    "_save_base64_data_url",
    "create_app",
    "handle_chat_completions",
)


API_SESSION_KEY = "api:default"
API_CHAT_ID = "default"


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _error_json(status: int, message: str, err_type: str = "invalid_request_error") -> web.Response:
    return web.json_response(
        {"error": {"message": message, "type": err_type, "code": status}},
        status=status,
    )


def _authorized(request: web.Request) -> bool:
    expected = os.getenv("VIOLA_API_SERVER_KEY", "").strip()
    if not expected:
        return True
    scheme, _, supplied = request.headers.get("Authorization", "").partition(" ")
    return scheme.lower() == "bearer" and hmac.compare_digest(supplied, expected)


def _media_token_secret() -> bytes:
    secret = (
        os.getenv("VIOLA_MEDIA_TOKEN_SECRET")
        or os.getenv("VIOLA_API_SERVER_KEY")
        or "viola-local-media-token"
    )
    return secret.encode("utf-8")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _allowed_media_roots(agent_loop: Any) -> list[Path]:
    roots = [get_media_dir().resolve(strict=False)]
    if hasattr(agent_loop, "workspace_roots"):
        for workspace in agent_loop.workspace_roots():
            roots.append(Path(workspace).expanduser().resolve(strict=False))
    else:
        workspace = getattr(agent_loop, "workspace", None)
        if workspace:
            roots.append(Path(workspace).expanduser().resolve(strict=False))
    return roots


def _create_media_token(path: str) -> str:
    payload = {"path": path, "exp": int(time.time()) + 3600}
    payload_raw = _json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = hmac.new(_media_token_secret(), payload_raw, hashlib.sha256).digest()
    return f"{_b64url_encode(payload_raw)}.{_b64url_encode(sig)}"


def _verify_media_token(token: str, agent_loop: Any) -> Path | None:
    try:
        payload_part, sig_part = token.split(".", 1)
        payload_raw = _b64url_decode(payload_part)
        expected = hmac.new(_media_token_secret(), payload_raw, hashlib.sha256).digest()
        actual = _b64url_decode(sig_part)
        if not hmac.compare_digest(expected, actual):
            return None
        payload = _json.loads(payload_raw.decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        path = Path(str(payload.get("path") or "")).expanduser().resolve(strict=False)
    except Exception:
        return None

    if not path.is_file():
        return None
    for root in _allowed_media_roots(agent_loop):
        if path == root or _is_under(path, root):
            return path
    return None


def _media_payload(media_paths: list[str]) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for raw in media_paths:
        path = Path(raw).expanduser().resolve(strict=False)
        if not path.is_file():
            continue
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        payload.append(
            {
                "token": _create_media_token(str(path)),
                "filename": path.name,
                "content_type": content_type,
            }
        )
    return payload


def _response_media(value: Any) -> list[str]:
    media = getattr(value, "media", None)
    if not isinstance(media, list):
        return []
    return [str(item) for item in media if isinstance(item, str) and item.strip()]


def _chat_completion_response(
    content: str,
    model: str,
    media_paths: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": content}
    media = _media_payload(media_paths or [])
    if media:
        message["media"] = media
    if metadata:
        message["metadata"] = metadata
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _parse_max_tokens(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        tokens = int(value)
    except (TypeError, ValueError):
        return None
    return tokens if tokens > 0 else None


def _response_text(value: Any) -> str:
    """Normalize process_direct output to plain assistant text."""
    if value is None:
        return ""
    if hasattr(value, "content"):
        return str(getattr(value, "content") or "")
    return str(value)

# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


def _sse_chunk(delta: str, model: str, chunk_id: str, finish_reason: str | None = None) -> bytes:
    """Format a single OpenAI-compatible SSE chunk."""
    payload = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": delta} if delta else {},
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {_json.dumps(payload)}\n\n".encode()


_SSE_DONE = b"data: [DONE]\n\n"

# ---------------------------------------------------------------------------
# Upload helpers
# ---------------------------------------------------------------------------


def _parse_json_content(body: dict) -> tuple[str, list[str]]:
    """Parse JSON request body. Returns (text, media_paths)."""
    messages = body.get("messages")
    if not isinstance(messages, list) or len(messages) != 1:
        raise ValueError("Only a single user message is supported")
    message = messages[0]
    if not isinstance(message, dict) or message.get("role") != "user":
        raise ValueError("Only a single user message is supported")

    user_content = message.get("content", "")
    media_dir = get_media_dir("api")
    media_paths: list[str] = []

    if isinstance(user_content, list):
        text_parts: list[str] = []
        for part in user_content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text":
                text_parts.append(part.get("text", ""))
            elif part.get("type") == "image_url":
                url = part.get("image_url", {}).get("url", "")
                if url.startswith("data:"):
                    saved = _save_base64_data_url(url, media_dir)
                    if saved:
                        media_paths.append(saved)
                elif url:
                    raise ValueError(
                        "Remote image URLs are not supported. "
                        "Use base64 data URLs or upload files via multipart/form-data."
                    )
        text = " ".join(text_parts)
    elif isinstance(user_content, str):
        text = user_content
    else:
        raise ValueError("Invalid content format")

    return text, media_paths


def _multipart_field_name(part: Any) -> str:
    """Normalize multipart field name for comparison (curl/clients vary by case)."""
    raw = getattr(part, "name", None)
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    return str(raw).strip().lower()


async def _parse_multipart(
    request: web.Request,
) -> tuple[str, list[str], str | None, str | None, bool, int | None]:
    """Parse multipart/form-data. Returns text, media, session, model, stream, max_tokens."""
    media_dir = get_media_dir("api")
    reader = await request.multipart()
    text = ""
    session_id = None
    model = None
    stream = False
    max_tokens = None
    media_paths: list[str] = []

    while True:
        part = await reader.next()
        if part is None:
            break
        pname = _multipart_field_name(part)
        filename = getattr(part, "filename", None)
        # Some clients omit `name` and only send filename; accept that as a file part.
        is_file_field = pname in ("files", "file") or (bool(filename) and pname == "")
        if pname == "message":
            text = (await part.read()).decode("utf-8")
        elif pname == "session_id":
            session_id = (await part.read()).decode("utf-8").strip()
        elif pname == "model":
            model = (await part.read()).decode("utf-8").strip()
        elif pname == "stream":
            raw_stream = (await part.read()).decode("utf-8").strip().lower()
            stream = raw_stream in {"1", "true", "yes", "on"}
        elif pname == "max_tokens":
            max_tokens = _parse_max_tokens((await part.read()).decode("utf-8"))
        elif is_file_field:
            raw = await part.read()
            if len(raw) > MAX_FILE_SIZE:
                raise _FileSizeExceeded(
                    f"File '{filename}' exceeds {MAX_FILE_SIZE // (1024 * 1024)}MB limit"
                )
            base = safe_filename(filename or "upload.bin")
            out_name = f"{uuid.uuid4().hex[:12]}_{base}"
            dest = media_dir / out_name
            dest.write_bytes(raw)
            media_paths.append(str(dest))
            logger.info(
                "API multipart saved upload name={!r} filename={!r} bytes={} -> {}",
                getattr(part, "name", None),
                filename,
                len(raw),
                dest,
            )

    if not text:
        text = "请分析上传的文件"

    return text, media_paths, session_id, model, stream, max_tokens


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


async def handle_chat_completions(request: web.Request) -> web.Response:
    """POST /v1/chat/completions — supports JSON and multipart/form-data."""
    if not _authorized(request):
        return _error_json(401, "Unauthorized", err_type="authentication_error")
    content_type = request.content_type or ""
    if not isinstance(content_type, str):
        content_type = ""

    agent_loop = request.app["agent_loop"]
    timeout_s: float = request.app.get("request_timeout", 120.0)
    model_name: str = request.app.get("model_name", "viola")

    stream = False
    max_tokens = None
    try:
        if content_type.startswith("multipart/"):
            text, media_paths, session_id, requested_model, stream, max_tokens = (
                await _parse_multipart(request)
            )
            twilio_dir = get_media_dir("api")
            text, twilio_paths = await ingest_twilio_media_lines(text, twilio_dir)
            media_paths.extend(twilio_paths)
        else:
            try:
                body = await request.json()
            except Exception:
                return _error_json(400, "Invalid JSON body")
            stream = body.get("stream", False)
            requested_model = body.get("model")
            max_tokens = _parse_max_tokens(body.get("max_tokens"))
            text, media_paths = _parse_json_content(body)
            twilio_dir = get_media_dir("api")
            text, twilio_paths = await ingest_twilio_media_lines(text, twilio_dir)
            media_paths.extend(twilio_paths)
            session_id = body.get("session_id")
    except ValueError as e:
        return _error_json(400, str(e))
    except _FileSizeExceeded as e:
        return _error_json(413, str(e), err_type="invalid_request_error")
    except Exception:
        logger.exception("Error parsing upload")
        return _error_json(413, "File too large or invalid upload")

    if requested_model and requested_model != model_name:
        # Legacy clients may still send the generic alias "viola".
        if requested_model not in {"viola", "viola-ai"}:
            return _error_json(400, f"Only configured model '{model_name}' is available")

    session_key = f"api:{session_id}" if session_id else API_SESSION_KEY
    session_locks: dict[str, asyncio.Lock] = request.app["session_locks"]
    session_lock = session_locks.setdefault(session_key, asyncio.Lock())

    logger.info(
        "API request session_key={} media={} text={} stream={}",
        session_key, len(media_paths), text[:80], stream,
    )
    # -- streaming path --
    if stream:
        resp = web.StreamResponse()
        resp.content_type = "text/event-stream"
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["Connection"] = "keep-alive"
        await resp.prepare(request)

        chunk_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        stream_failed = False
        emitted_content = False

        async def _on_stream(token: str) -> None:
            nonlocal emitted_content
            if token:
                emitted_content = True
            await queue.put(token)

        async def _on_stream_end(*_a: Any, **_kw: Any) -> None:
            # Agent stream-end callbacks mark generation segment boundaries.
            # Tool-backed requests may continue after a segment ends, so the
            # HTTP SSE stream is closed only when process_direct returns.
            return None

        async def _run() -> None:
            nonlocal stream_failed
            try:
                async with session_lock:
                    response = await asyncio.wait_for(
                        agent_loop.process_direct(
                            content=text,
                            media=media_paths if media_paths else None,
                            session_key=session_key,
                            channel="api",
                            chat_id=API_CHAT_ID,
                            on_stream=_on_stream,
                            on_stream_end=_on_stream_end,
                            max_tokens=max_tokens,
                        ),
                        timeout=timeout_s,
                    )
                    if not emitted_content:
                        response_text = _response_text(response)
                        if response_text.strip():
                            await queue.put(response_text)
            except Exception:
                stream_failed = True
                logger.exception("Streaming error for session {}", session_key)
            finally:
                await queue.put(None)

        task = asyncio.create_task(_run())
        try:
            while True:
                token = await queue.get()
                if token is None:
                    break
                await resp.write(_sse_chunk(token, model_name, chunk_id))
        finally:
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        if not stream_failed:
            await resp.write(_sse_chunk("", model_name, chunk_id, finish_reason="stop"))
            await resp.write(_SSE_DONE)
        return resp

    # -- non-streaming path (original logic) --
    fallback = EMPTY_FINAL_RESPONSE_MESSAGE

    try:
        async with session_lock:
            try:
                response = await asyncio.wait_for(
                    agent_loop.process_direct(
                        content=text,
                        media=media_paths if media_paths else None,
                        session_key=session_key,
                        channel="api",
                        chat_id=API_CHAT_ID,
                        max_tokens=max_tokens,
                    ),
                    timeout=timeout_s,
                )
                response_text = _response_text(response)

                if not response_text or not response_text.strip():
                    logger.warning("Empty response for session {}, retrying", session_key)
                    retry_response = await asyncio.wait_for(
                        agent_loop.process_direct(
                            content=text,
                            media=media_paths if media_paths else None,
                            session_key=session_key,
                            channel="api",
                            chat_id=API_CHAT_ID,
                            max_tokens=max_tokens,
                        ),
                        timeout=timeout_s,
                    )
                    response = retry_response
                    response_text = _response_text(retry_response)
                    if not response_text or not response_text.strip():
                        logger.warning("Empty response after retry, using fallback")
                        response_text = fallback

            except asyncio.TimeoutError:
                return _error_json(504, f"Request timed out after {timeout_s}s")
            except Exception:
                logger.exception("Error processing request for session {}", session_key)
                return _error_json(500, "Internal server error", err_type="server_error")
    except Exception:
        logger.exception("Unexpected API lock error for session {}", session_key)
        return _error_json(500, "Internal server error", err_type="server_error")

    response_media = _response_media(response)
    response_metadata = getattr(response, "metadata", None)
    if not isinstance(response_metadata, dict):
        response_metadata = None
    if not response_media:
        discover_workspace = (
            agent_loop.workspace_for_session_key(session_key)
            if hasattr(agent_loop, "workspace_for_session_key")
            else getattr(agent_loop, "workspace", get_media_dir())
        )
        response_media = discover_attachment_paths_from_text(
            f"{text}\n{response_text}",
            workspace=discover_workspace,
        )
    if response_media:
        logger.info(
            "API response includes {} attachment(s): {}",
            len(response_media),
            [Path(item).name for item in response_media],
        )
    return web.json_response(
        _chat_completion_response(
            response_text,
            model_name,
            response_media,
            response_metadata,
        )
    )


async def handle_models(request: web.Request) -> web.Response:
    """GET /v1/models"""
    if not _authorized(request):
        return _error_json(401, "Unauthorized", err_type="authentication_error")
    model_name = request.app.get("model_name", "viola")
    return web.json_response(
        {
            "object": "list",
            "data": [
                {
                    "id": model_name,
                    "object": "model",
                    "created": 0,
                    "owned_by": "viola",
                }
            ],
        }
    )


async def handle_health(request: web.Request) -> web.Response:
    """GET /health"""
    return web.json_response({"status": "ok"})


async def handle_diag(request: web.Request) -> web.Response:
    """GET /v1/diag — MCP servers + registered tools (for deployment health checks).

    Returns the configured MCP servers, which ones successfully connected, and the
    full list of tool names visible to the LLM.
    """
    if not _authorized(request):
        return _error_json(401, "Unauthorized", err_type="authentication_error")
    agent_loop = request.app["agent_loop"]
    # Trigger lazy MCP connect so the first /diag call gives an accurate picture.
    try:
        await agent_loop._connect_mcp()
    except Exception as exc:  # noqa: BLE001
        logger.warning("MCP connect during /v1/diag failed: {}", exc)

    configured = sorted((agent_loop._mcp_servers or {}).keys())
    connected = sorted((agent_loop._mcp_stacks or {}).keys())
    failed = [s for s in configured if s not in connected]
    raw_tool_names = agent_loop.tools.tool_names
    all_tools = raw_tool_names() if callable(raw_tool_names) else list(raw_tool_names)
    server_prefixes = {_sanitize_name(f"mcp_{s}_") for s in connected}
    mcp_tools = sorted(
        t for t in all_tools
        if any(t.startswith(prefix) for prefix in server_prefixes)
    )
    nanobot_configured = "nanobot" in configured
    nanobot_connected = "nanobot" in connected
    nanobot_prefix = _sanitize_name("mcp_nanobot_")
    nanobot_tools = sorted(t for t in all_tools if t.startswith(nanobot_prefix))
    nanobot_failed_reason = None
    if nanobot_configured and not nanobot_connected:
        nanobot_failed_reason = "connection_not_live"
    customer_service_only = (
        (os.getenv("VIOLA_CUSTOMER_SERVICE_ONLY", "true").strip().lower())
        not in ("0", "false", "no", "off")
    )
    return web.json_response(
        {
            "mcp_servers_configured": configured,
            "mcp_servers_connected": connected,
            "mcp_servers_failed": failed,
            "mcp_tools": mcp_tools,
            "tools_total": len(all_tools),
            "nanobot": {
                "configured": nanobot_configured,
                "connected": nanobot_connected,
                "tools_registered": len(nanobot_tools),
                "tools": nanobot_tools,
                "last_failure": nanobot_failed_reason,
            },
            "migration_mainline": {
                "enabled": (os.getenv("CS_VIOLA_MAINLINE_MODE", "off").strip().lower() != "off"),
                "mode": os.getenv("CS_VIOLA_MAINLINE_MODE", "off").strip().lower(),
                "fallback_enabled": (
                    os.getenv("CS_VIOLA_MAINLINE_FALLBACK_ENABLED", "true").strip().lower()
                    not in ("0", "false", "no", "off")
                ),
                "policy_id": os.getenv("CS_VIOLA_MAINLINE_POLICY_ID", "viola-hard-cutover"),
                "preview_engine": os.getenv("CS_VIOLA_PREVIEW_ENGINE", "viola_mainline").strip().lower(),
                "customer_service_only": customer_service_only,
                "strategy_versions": {
                    "role_state_strategy": ROLE_STRATEGY_VERSION,
                    "field_state_strategy": FIELD_STRATEGY_VERSION,
                },
                "latest_execution_path_summary": {
                    "allowed": ["agent_mcp_mainline", "degraded"],
                    "forbidden": ["langgraph_mainline"],
                },
            },
            "customer_service_only": customer_service_only,
        }
    )


async def handle_media(request: web.Request) -> web.Response:
    """Serve a signed generated attachment to trusted upstream proxies."""
    if not _authorized(request):
        return _error_json(401, "Unauthorized", err_type="authentication_error")
    token = request.match_info.get("token", "")
    path = _verify_media_token(token, request.app["agent_loop"])
    if path is None:
        return _error_json(404, "Media not found")

    headers = {
        "Content-Disposition": f'attachment; filename="{path.name}"',
        "Cache-Control": "private, max-age=300",
    }
    content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    headers["Content-Type"] = content_type
    return web.FileResponse(
        path,
        headers=headers,
        chunk_size=256 * 1024,
    )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(
    agent_loop, model_name: str = "viola", request_timeout: float = 120.0
) -> web.Application:
    """Create the aiohttp application.

    Args:
        agent_loop: An initialized AgentLoop instance.
        model_name: Model name reported in responses.
        request_timeout: Per-request timeout in seconds.
    """
    app = web.Application(client_max_size=20 * 1024 * 1024)  # 20MB for base64 images
    app["agent_loop"] = agent_loop
    app["model_name"] = model_name
    app["request_timeout"] = request_timeout
    app["session_locks"] = {}  # per-user locks, keyed by session_key

    app.router.add_post("/v1/chat/completions", handle_chat_completions)
    app.router.add_get("/v1/models", handle_models)
    app.router.add_get("/v1/media/{token}", handle_media)
    app.router.add_get("/v1/diag", handle_diag)
    app.router.add_get("/health", handle_health)
    return app
