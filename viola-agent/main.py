"""
Twilio WhatsApp webhook → Viola OpenAI-compatible HTTP API (decoupled from BACKEND backend).

Prereqs:
  - ``viola serve`` reachable at ``VIOLA_API_BASE`` (default http://127.0.0.1:8900).
  - Twilio env: ``ACCOUNT_SID``, ``AUTH_TOKEN``, and ``WHATSAPP_NUMBER`` or ``MESSAGING_SERVICE_SID``.

Install::
    pip install ".[api,twilio,whatsapp_webhook]"
Run::
    uvicorn main:app --host 0.0.0.0 --port 8800

Probe in browser: GET ``http://127.0.0.1:8800/webhook`` (plain text). Twilio uses POST.

The handler returns **202 Accepted** immediately (Twilio-friendly) and runs Viola + outbound WhatsApp in a
background task: Twilio only waits ~15s on the callback while the LLM may take longer.

Backend business data (e.g. new projects) should be created by the Viola chatbot using configured
tools (e.g. MCP calling ``POST /api/projects``), not by regex parsing in this webhook.
Sender verification may still use ``BACKEND_API_BASE_URL``.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, NamedTuple

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from loguru import logger
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from twilio.twiml.messaging_response import MessagingResponse

from viola.api.whatsapp_response_template import (
    TwilioHttpResult,
    send_typing_indicator,
    send_whatsapp_message_back,
)
from viola.agent.legacy_cs_role_templates import (
    detect_legacy_service_role,
    legacy_full_contract_block,
)
from viola.agent.legacy_conversation_workflow import (
    LegacyConversationState,
    advance_on_assistant_message,
    advance_on_user_message,
)
from viola.agent.legacy_field_state_strategy import execute_field_strategy
from viola.agent.legacy_role_state_strategy import execute_role_strategy
from viola.command.builtin import is_new_session_command
from viola.utils.helpers import looks_like_html_response


class Settings(BaseSettings):
    """Viola HTTP client configuration (Twilio keys stay env-only via ``whatsapp_response_template``)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # os.getenv(...) is None when unset; str-typed fields reject None. Optional vars must be str | None.
    viola_api_base: str = Field(default="http://127.0.0.1:8900")
    backend_api_base_url: str | None = Field(default="http://127.0.0.1:8000")
    internal_secret: str | None = Field(default=None)
    # Prefer explicit model from env so webhook and serve stay aligned.
    # Order: VIOLA_MODEL > VIOLA_AGENTS__DEFAULTS__MODEL > unset (fallback to serve runtime default).
    viola_model: str | None = Field(default_factory=lambda: _default_viola_model())
    viola_timeout_s: float = Field(default=120.0)


@lru_cache
def _settings() -> Settings:
    return Settings()


app = FastAPI(title="Viola Twilio WhatsApp webhook", version="0.1.0")
_LEGACY_WORKFLOW_STATES: dict[str, LegacyConversationState] = {}


class ViolaChatReply(NamedTuple):
    content: str
    tool_events: list[dict[str, str]]


def _legacy_state_get(session_key: str) -> LegacyConversationState | None:
    return _LEGACY_WORKFLOW_STATES.get(session_key)


def _legacy_state_set(session_key: str, state: LegacyConversationState) -> None:
    _LEGACY_WORKFLOW_STATES[session_key] = state


def _legacy_state_reset(session_key: str) -> None:
    _LEGACY_WORKFLOW_STATES.pop(session_key, None)


def _first_nonempty_env(*keys: str) -> str:
    for key in keys:
        value = (os.environ.get(key) or "").strip()
        if value:
            return value
    return ""


def _default_viola_model() -> str | None:
    model = _first_nonempty_env("VIOLA_MODEL", "VIOLA_AGENTS__DEFAULTS__MODEL")
    return model or None


def _customer_service_only_enabled() -> bool:
    raw = (os.environ.get("VIOLA_CUSTOMER_SERVICE_ONLY") or "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _legacy_field_prompt_block() -> str:
    override = (os.environ.get("VIOLA_LEGACY_FIELD_PROMPT") or "").strip()
    if override:
        return override
    return (
        "[Legacy-Field-Contract]\n"
        "严格沿用旧 LangGraph 业务规则：\n"
        "- 字段名固定：product_no, name, phone, location, issue_description。\n"
        "- 取值优先级：已确认状态值 > 用户当前明确输入 > 正则/NLP猜测。\n"
        "- 非空已确认字段不得覆盖，除非用户明确要求“更新/改为/改成”。\n"
        "- 产品关键词：产品型号/產品型號/型号/型號/产品 + 形如[A-Z]{2,3}\\d{3,4}或“xxxx系列”。\n"
        "- 地址关键词：安装地点/安裝地點/地址/位置；电话关键词：联系电话/聯絡電話/电话/電話/手机/手機；姓名关键词：客户名称/客戶名稱/姓名/联系人姓名/聯絡人姓名。\n"
        "- 尺寸语义（如 3000x2000, 3000*2000, 3m×2m）应进入 issue_description，用于报价上下文。\n"
        "- 涉及创建/更新时，缺什么字段只追问缺失字段；未收到 MCP 写工具成功结果前，禁止宣称已创建/已更新。"
    )


def _select_legacy_service_role(user_body: str) -> str:
    return detect_legacy_service_role(user_body)


def _normalize_dimension_candidate(raw: str) -> str:
    text = (raw or "").strip().lower()
    if not text:
        return ""
    # Normalize separators and whitespace for mixed inputs:
    # "3000 x 2000", "3000*2000", "3m×2m", "3.0 乘 2.0".
    normalized = (
        text.replace("＊", "*")
        .replace("×", "x")
        .replace("乘", "x")
        .replace("*", "x")
    )
    normalized = re.sub(r"\s+", "", normalized)
    # Optional units on each side. If only one side has unit, apply it to both.
    m = re.search(
        r"(?P<w>\d{1,5}(?:\.\d{1,2})?)(?P<u1>mm|cm|m)?x(?P<h>\d{1,5}(?:\.\d{1,2})?)(?P<u2>mm|cm|m)?",
        normalized,
        re.IGNORECASE,
    )
    if not m:
        return ""
    w = m.group("w")
    h = m.group("h")
    u1 = (m.group("u1") or "").lower()
    u2 = (m.group("u2") or "").lower()
    unit = u1 or u2
    if unit:
        return f"{w}{unit}x{h}{unit}"
    return f"{w}x{h}"


def _extract_dimension_candidate(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""

    # Prioritize explicit size context markers.
    explicit_patterns = (
        r"(?:尺寸|size|呎吋|大小|長闊|长宽)\s*[:：=]?\s*([0-9\.\s\*xX×乘mMcC]{3,40})",
        r"([0-9]{2,5}(?:\.\d{1,2})?\s*(?:mm|cm|m)?\s*[xX×\*乘]\s*[0-9]{2,5}(?:\.\d{1,2})?\s*(?:mm|cm|m)?)",
    )
    for pattern in explicit_patterns:
        for match in re.finditer(pattern, raw, re.IGNORECASE):
            candidate = _normalize_dimension_candidate(match.group(1))
            if candidate:
                return candidate
    return ""


def _extract_legacy_field_candidates(text: str) -> dict[str, str]:
    extracted = {
        "product_no": "",
        "name": "",
        "phone": "",
        "location": "",
        "issue_description": "",
    }
    raw = (text or "").strip()
    if not raw:
        return extracted

    product_patterns = [
        r"產品型號[:：]\s*([A-Z0-9]+)",
        r"产品型号[:：]\s*([A-Z0-9]+)",
        r"型號[:：]\s*([A-Z0-9]+)",
        r"型号[:：]\s*([A-Z0-9]+)",
        r"產品[:：]\s*([A-Z0-9]+)",
        r"产品[:：]\s*([A-Z0-9]+)",
        r"\b[A-Z]{2,3}\d{3,4}\b",
        r"\b\d{4}系列\b",
    ]
    for pattern in product_patterns:
        match = re.search(pattern, raw, re.IGNORECASE)
        if not match:
            continue
        extracted["product_no"] = (match.group(1) if match.lastindex else match.group(0)).strip()
        break

    name_patterns = [
        r"客戶名稱[:：]\s*([A-Za-z\s]+[A-Za-z])",
        r"客户名称[:：]\s*([A-Za-z\s]+[A-Za-z])",
        r"姓名[:：]\s*([A-Za-z\s]+[A-Za-z])",
        r"聯絡人姓名[:：]\s*([A-Za-z\s]+[A-Za-z])",
        r"联系人姓名[:：]\s*([A-Za-z\s]+[A-Za-z])",
        r"我係([^\s，,。]{1,8})",
        r"我是([^\s，,。]{1,8})",
        r"我叫([^\s，,。]{1,8})",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, raw, re.IGNORECASE)
        if not match:
            continue
        name = (match.group(1) if match.lastindex else match.group(0)).strip()
        if len(name) >= 2:
            extracted["name"] = name
            break

    phone_patterns = [
        r"聯絡電話[:：]\s*([0-9\-\+\s]+)",
        r"联系电话[:：]\s*([0-9\-\+\s]+)",
        r"電話[:：]\s*([0-9\-\+\s]+)",
        r"电话[:：]\s*([0-9\-\+\s]+)",
        r"手機[:：]\s*([0-9\-\+\s]+)",
        r"手机[:：]\s*([0-9\-\+\s]+)",
        r"\b\d{8}\b",
        r"\b\+\d{11,12}\b",
        r"\b\d{4,5}[\-\s]?\d{4}\b",
    ]
    for pattern in phone_patterns:
        match = re.search(pattern, raw)
        if not match:
            continue
        phone = (match.group(1) if match.lastindex else match.group(0)).strip()
        cleaned = re.sub(r"[^\d\+]", "", phone)
        if len(cleaned) >= 8:
            extracted["phone"] = cleaned
            break

    location_patterns = [
        r"安裝地點[:：]\s*([^\n,，。]+)",
        r"安装地点[:：]\s*([^\n,，。]+)",
        r"安裝位置[:：]\s*([^\n,，。]+)",
        r"安装位置[:：]\s*([^\n,，。]+)",
        r"地址[:：]\s*([^\n,，。]+)",
        r"地址[：:]\s*([\u4e00-\u9fffA-Za-z0-9\-號座樓室苑邨灣區道街路]+)",
        r"位置[:：]\s*([^\n,，。]+)",
        r"\b[a-zA-Z\s]+bay\b",
        r"\b[a-zA-Z\s]+road\b",
        r"\b[a-zA-Z\s]+street\b",
        r"[\u4e00-\u9fff]+區",
        r"[\u4e00-\u9fff]+区",
        r"[\u4e00-\u9fff]+道",
    ]
    for pattern in location_patterns:
        match = re.search(pattern, raw, re.IGNORECASE)
        if not match:
            continue
        location = (match.group(1) if match.lastindex else match.group(0)).strip()
        if len(location) >= 2:
            extracted["location"] = location
            break

    dimension = _extract_dimension_candidate(raw)
    if dimension:
        extracted["issue_description"] = f"尺寸={dimension}"

    return extracted


def build_inbound_plaintext(
    *,
    body: str,
    profile_name: str,
    sender_mobile_digits: str | None,
    button_payload: str | None,
    media_urls: list[str],
    media_content_types: list[str | None],
    lat: str | None,
    lon: str | None,
    legacy_role: str | None = None,
    confirmed_state_fields: dict[str, str] | None = None,
    candidate_fields: dict[str, str] | None = None,
    legacy_workflow_state: LegacyConversationState | None = None,
) -> str:
    """Build text for Viola; Twilio media lines match ``viola.api.twilio_media`` conventions."""
    parts: list[str] = []
    if profile_name:
        parts.append(f"[User profile name: {profile_name}]")
    if sender_mobile_digits:
        parts.append(f"[Sender mobile_digits: {sender_mobile_digits}]")
    if lat and lon:
        parts.append(f"[Location: lat={lat}, lon={lon}]")
    if button_payload:
        parts.append(f"[Quick reply: {button_payload}]")
    parts.append(_legacy_field_prompt_block())
    role = (legacy_role or "general_staff").strip().lower() or "general_staff"
    role_strategy = execute_role_strategy(role)
    parts.append(f"[Legacy-Service-Role: {role}]")
    parts.append(role_strategy.to_prompt_block())
    parts.append(legacy_full_contract_block(role))
    if legacy_workflow_state is not None:
        parts.append(legacy_workflow_state.to_prompt_block())
    main = (body or "").strip()
    if main:
        effective_candidates = candidate_fields or _extract_legacy_field_candidates(main)
        field_strategy = execute_field_strategy(
            user_text=main,
            candidate_fields=effective_candidates,
            confirmed_state_fields=confirmed_state_fields or {},
        )
        parts.append(main)
        pairs = [f"{k}={v}" for k, v in effective_candidates.items() if v]
        parts.append("[Legacy-Field-Candidates] " + ("; ".join(pairs) if pairs else "none"))
        parts.append(field_strategy.to_prompt_block())
    for i, url in enumerate(media_urls):
        parts.append(f"[media:{i}:{url}]")
        ct = media_content_types[i] if i < len(media_content_types) else None
        if ct:
            parts.append(f"[media_content_type:{i}:{ct}]")
    return "\n".join(parts).strip() or "(empty message)"


async def _ingest_chatbot_message(
    *,
    session_key: str,
    body: str,
    is_new_session: bool,
    actor_id: str | None,
) -> dict[str, Any] | None:
    """Best-effort persist user utterance; never blocks the WhatsApp pipeline."""
    cfg = _settings()
    base = (cfg.backend_api_base_url or "").strip().rstrip("/")
    if base.lower().endswith("/api"):
        base = base[:-4]
    if not base:
        return None
    url = f"{base}/api/internal/chatbot-messages"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    secret = cfg.internal_secret
    if secret:
        headers["X-Backend-Secret"] = secret
    payload = {
        "session_key": session_key,
        "body": body,
        "is_new_session": is_new_session,
    }
    if actor_id:
        payload["actor_id"] = actor_id
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 201:
                return response.json()
            logger.warning(
                "chatbot-messages ingest HTTP {} body={!r}",
                response.status_code,
                (response.text or "")[:300],
            )
    except Exception:
        logger.exception("chatbot-messages ingest failed for session_key={!r}", session_key)
    return None


def _jwt_subject(token: str) -> str | None:
    import base64
    import json

    try:
        segment = token.split(".")[1]
        padded = segment + "=" * (-len(segment) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        sub = data.get("sub")
        return str(sub) if sub else None
    except Exception:
        return None


async def call_viola_chat(sender: str, message_text: str) -> ViolaChatReply:
    """POST user text to Viola ``/v1/chat/completions`` (same contract as OpenAI)."""
    cfg = _settings()
    base = cfg.viola_api_base.rstrip("/")
    url = f"{base}/v1/chat/completions"
    session_id = sender.replace("whatsapp:", "").strip() or "unknown"
    payload: dict[str, Any] = {
        "messages": [{"role": "user", "content": message_text}],
        "session_id": session_id,
    }
    if cfg.viola_model:
        payload["model"] = cfg.viola_model

    async with httpx.AsyncClient(timeout=cfg.viola_timeout_s) as client:
        response = await client.post(url, json=payload)
        if response.status_code >= 400:
            detail = (response.text or "").strip()
            if (
                response.status_code == 400
                and "Only configured model" in detail
                and "model" in payload
            ):
                sent_model = payload.pop("model", None)
                logger.warning(
                    "Viola model mismatch for sender={!r}; sent_model={!r}. Retrying without explicit model.",
                    sender,
                    sent_model,
                )
                response = await client.post(url, json=payload)
            if response.status_code >= 400:
                logger.error(
                    "Viola chat request failed status={} sender={!r} body={}",
                    response.status_code,
                    sender,
                    (response.text or "").strip()[:500],
                )
                response.raise_for_status()
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        return ViolaChatReply(content="", tool_events=[])
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    raw_metadata = msg.get("metadata")
    metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
    raw_tool_events = metadata.get("_tool_events")
    tool_events: list[dict[str, str]] = []
    if isinstance(raw_tool_events, list):
        for event in raw_tool_events:
            if not isinstance(event, dict):
                continue
            name = str(event.get("name") or "").strip()
            status = str(event.get("status") or "").strip()
            call_id = str(event.get("call_id") or "").strip()
            if not name:
                continue
            tool_events.append({"name": name, "status": status or "ok", "call_id": call_id})
    return ViolaChatReply(content=str(content).strip() if content else "", tool_events=tool_events)


def _whatsapp_sender_to_mobile_digits(sender: str) -> str | None:
    """Twilio ``From`` like ``whatsapp:+85264760285`` → digits ``85264760285`` (country + national)."""
    s = sender.strip()
    if s.lower().startswith("whatsapp:"):
        s = s[9:].strip()
    s = s.lstrip("+").strip()
    digits = "".join(c for c in s if c.isdigit())
    if len(digits) < 8:
        return None
    return digits


@dataclass
class _CachedToken:
    token: str
    expires_at: float  # time.monotonic()


_token_cache: dict[str, _CachedToken] = {}
_TOKEN_REFRESH_BUFFER_S: float = 60.0


NOT_REGISTERED_WHATSAPP_MSG = (
    "此 WhatsApp 號碼尚未在系統後台註冊，或帳戶已停用。請聯絡管理員。\n"
    "This WhatsApp number is not registered in backend or the account is inactive. "
    "Please contact your administrator."
)
VERIFY_FAILED_WHATSAPP_MSG = (
    "系統暫時無法驗證你的帳戶，請稍後再試。\n"
    "Account verification is temporarily unavailable. Please try again later."
)
CUSTOMER_SERVICE_ONLY_DENY_MSG = (
    "目前本助手仅提供客服咨询与问题解答，不提供创建/修改/删除业务数据的操作。\n"
    "如需处理项目或单据变更，请联系内部同事在后台系统操作。"
)


def _looks_like_mutation_request(user_body: str) -> bool:
    text = (user_body or "").strip().lower()
    if not text:
        return False
    write_verbs = (
        "create", "add", "new", "update", "edit", "delete", "remove", "cancel",
        "建立", "新增", "新建", "创建", "修改", "更新", "编辑", "刪除", "删除", "取消",
    )
    business_targets = (
        "project", "quotation", "quote", "invoice", "order", "vo",
        "项目", "報價", "报价", "發票", "发票", "訂單", "订单", "变更单", "變更單",
    )
    if any(v in text for v in write_verbs) and any(t in text for t in business_targets):
        return True
    if re.search(r"(帮我|幫我|please)\s*(create|update|delete|add|edit|remove)", text):
        return True
    if re.search(r"(帮我|幫我)?\s*(建立|创建|新增|修改|更新|删除|刪除)\s*", text):
        return True
    return False


async def _fetch_jwt_token_via_internal(mobile_digits: str) -> tuple[str | None, str]:
    """Obtain a JWT for the WhatsApp sender via POST /api/whatsapp-auth/token.

    Returns ``(token, reason)`` where *reason* is ``"ok"``, ``"not_registered"``, or
    ``"api_error"``.  Caches valid tokens per sender until ``_TOKEN_REFRESH_BUFFER_S``
    seconds before expiry so we don't issue a new token on every message.
    """
    cached = _token_cache.get(mobile_digits)
    if cached is not None and time.monotonic() < cached.expires_at:
        return cached.token, "ok"

    cfg = _settings()
    base = (cfg.backend_api_base_url or "").strip().rstrip("/")
    if base.lower().endswith("/api"):
        base = base[:-4]
    url = f"{base}/api/whatsapp-auth/token"
    try:
        headers: dict[str, str] = {"Accept": "application/json"}
        secret = cfg.internal_secret
        if secret:
            headers["X-Backend-Secret"] = secret
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json={"mobile_digits": mobile_digits}, headers=headers)
            if response.status_code == 401:
                logger.info(
                    "BACKEND token denied (not registered/inactive) mobile_digits={!r}",
                    mobile_digits,
                )
                return None, "not_registered"
            if response.status_code != 200:
                logger.warning(
                    "BACKEND token HTTP {} for mobile_digits={!r} body={!r}",
                    response.status_code,
                    mobile_digits,
                    (response.text or "")[:500],
                )
                return None, "api_error"
            data = response.json()
            token = data.get("access_token")
            if not token:
                logger.warning("BACKEND token response missing access_token for mobile_digits={!r}", mobile_digits)
                return None, "api_error"
            expires_in = int(data.get("expires_in_seconds") or 3600)
            _token_cache[mobile_digits] = _CachedToken(
                token=token,
                expires_at=time.monotonic() + expires_in - _TOKEN_REFRESH_BUFFER_S,
            )
            return token, "ok"
    except Exception:
        logger.exception("BACKEND token request failed for mobile_digits={!r}", mobile_digits)
        return None, "api_error"


def _twilio_sender_from_form(form_data: Mapping[str, Any]) -> str | None:
    """Resolve WhatsApp sender JID from Twilio inbound POST (``From`` or ``WaId``)."""
    for key in ("From", "from"):
        raw = form_data.get(key)
        if raw is not None:
            s = str(raw).strip()
            if s:
                return s
    waid = form_data.get("WaId") or form_data.get("waid")
    if waid is None:
        return None
    w = str(waid).strip()
    if not w:
        return None
    if w.startswith("whatsapp:"):
        return w
    return f"whatsapp:+{w.lstrip('+')}"


def _twilio_webhook_diagnosis(request: Request, form_data) -> str:
    """Safe log line when Twilio payload is unexpected."""
    keys = sorted(form_data.keys()) if hasattr(form_data, "keys") else []
    ct = request.headers.get("content-type") or ""
    cl = request.headers.get("content-length") or ""
    hints: list[str] = []
    if not keys:
        hints.append(
            "empty_form — expect application/x-www-form-urlencoded from Twilio; "
            "check reverse-proxy body size/buffering or POST URL (not GET)."
        )
    elif ("MessageStatus" in keys or "SmsStatus" in keys) and "From" not in keys and "WaId" not in keys:
        hints.append(
            "possible_status_callback — inbound webhook URL should be under "
            "\"when a message comes in\"; use another URL for status callbacks."
        )
    elif ct and "application/json" in ct.lower():
        hints.append("json_body — Twilio Messaging posts urlencoded form fields, not JSON.")
    hint_str = (" " + "; ".join(hints)) if hints else ""
    return f"content-type={ct!r} content-length={cl!r} keys={keys!r}{hint_str}"


def _form_to_plain_dict(form_data) -> dict[str, str]:
    """Snapshot Twilio form fields (single string values)."""
    out: dict[str, str] = {}
    for key in form_data.keys():
        val = form_data.get(key)
        if val is None:
            continue
        out[str(key)] = val if isinstance(val, str) else str(val)
    return out


def _log_twilio_send(where: str, result: object) -> None:
    if isinstance(result, TwilioHttpResult):
        if result.status_code >= 400:
            logger.error(
                "{} Twilio API error status={} detail={}",
                where,
                result.status_code,
                result.content,
            )
        else:
            logger.info("{} Twilio send status={}", where, result.status_code)
        return
    logger.warning("{} unexpected Twilio result type {!r}", where, type(result))


async def _whatsapp_reply_pipeline(snapshot: dict[str, str]) -> None:
    """Long work after webhook HTTP response (Twilio ~15s callback timeout)."""
    await _probe_viola_mcp_once()

    sender = _twilio_sender_from_form(snapshot)
    if not sender:
        logger.warning("Background pipeline: no sender in snapshot keys={}", list(snapshot.keys()))
        return

    profile_name = str(snapshot.get("ProfileName") or "")
    body = str(snapshot.get("Body") or "")
    lat_raw = snapshot.get("Latitude")
    lon_raw = snapshot.get("Longitude")
    lat_s = lat_raw if lat_raw else None
    lon_s = lon_raw if lon_raw else None
    bp_raw = snapshot.get("ButtonPayload")
    button_payload = bp_raw if bp_raw else None

    media_urls: list[str] = []
    media_content_types: list[str | None] = []
    i = 0
    while True:
        media_url = snapshot.get(f"MediaUrl{i}")
        if not media_url:
            break
        media_urls.append(media_url)
        ct_raw = snapshot.get(f"MediaContentType{i}")
        media_content_types.append(ct_raw if ct_raw else None)
        i += 1

    mg_sid = str(snapshot.get("MessagingServiceSid") or "").strip() or None
    msg_sid = str(snapshot.get("MessageSid") or snapshot.get("SmsMessageSid") or "").strip()

    logger.info(
        "Pipeline start sender={!r} body_preview={!r} media_count={} messaging_service={!r}",
        sender,
        body[:120],
        len(media_urls),
        mg_sid or "(env only)",
    )

    mobile_digits = _whatsapp_sender_to_mobile_digits(sender)

    cfg = _settings()
    if not (cfg.backend_api_base_url or "").strip():
        logger.error(
            "BACKEND_API_BASE_URL is empty; blocking pipeline.",
        )
        out = await send_whatsapp_message_back(
            NOT_REGISTERED_WHATSAPP_MSG,
            sender,
            webhook_messaging_service_sid=mg_sid,
        )
        _log_twilio_send("BACKEND_API_BASE_URL is empty", out)
        return

    if not mobile_digits:
        logger.warning("Cannot derive mobile_digits from sender={!r}", sender)
        out = await send_whatsapp_message_back(
            NOT_REGISTERED_WHATSAPP_MSG,
            sender,
            webhook_messaging_service_sid=mg_sid,
        )
        _log_twilio_send("verify_bad_sender", out)
        return

    token, token_reason = await _fetch_jwt_token_via_internal(mobile_digits)
    if token is None:
        if token_reason == "api_error":
            logger.error("BACKEND token fetch failed (API unavailable) mobile_digits={!r}", mobile_digits)
            out = await send_whatsapp_message_back(
                VERIFY_FAILED_WHATSAPP_MSG,
                sender,
                webhook_messaging_service_sid=mg_sid,
            )
            _log_twilio_send("token_api_error", out)
            return
        logger.info("WhatsApp sender rejected by BACKEND mobile_digits={!r}", mobile_digits)
        out = await send_whatsapp_message_back(
            NOT_REGISTERED_WHATSAPP_MSG,
            sender,
            webhook_messaging_service_sid=mg_sid,
        )
        _log_twilio_send("token_denied", out)
        return

    if msg_sid:
        await send_typing_indicator(msg_sid)

    body_stripped = body.strip()
    session_key = f"api:{mobile_digits}"
    is_new = is_new_session_command(body_stripped)
    if is_new:
        _legacy_state_reset(session_key)
    extracted_candidates = _extract_legacy_field_candidates(body_stripped)
    workflow_state = advance_on_user_message(
        _legacy_state_get(session_key),
        session_key=session_key,
        user_text=body_stripped,
        candidate_fields=extracted_candidates,
    )
    _legacy_state_set(session_key, workflow_state)
    selected_role = workflow_state.current_role
    if _customer_service_only_enabled() and _looks_like_mutation_request(body_stripped):
        logger.info(
            "Customer-service-only mode blocked mutation intent sender={!r} body_preview={!r}",
            sender,
            body_stripped[:120],
        )
        out = await send_whatsapp_message_back(
            CUSTOMER_SERVICE_ONLY_DENY_MSG,
            sender,
            webhook_messaging_service_sid=mg_sid,
        )
        _log_twilio_send("customer_service_only_block", out)
        return

    ingest = await _ingest_chatbot_message(
        session_key=session_key,
        body=body_stripped,
        is_new_session=is_new,
        actor_id=_jwt_subject(token),
    )

    if is_new:
        # New-session commands must not carry metadata headers — the command
        # router matches on the full content string, so any prefix prevents
        # the exact-match from firing and the LLM receives "/new" instead.
        message_text = body_stripped
    else:
        message_text = build_inbound_plaintext(
            body=body,
            profile_name=profile_name or "",
            sender_mobile_digits=mobile_digits,
            button_payload=button_payload,
            media_urls=media_urls,
            media_content_types=media_content_types,
            lat=lat_s,
            lon=lon_s,
            legacy_role=selected_role,
            confirmed_state_fields=workflow_state.to_confirmed_fields(),
            candidate_fields=extracted_candidates,
            legacy_workflow_state=workflow_state,
        )

    fallback = (
        "AI而家仲喺開發緊，撞到啲小問題😅麻煩你搵下管理員幫手啦～"
        "我哋會慢慢學多啲嘢，希望之後可以幫到你更多～😉"
    )
    try:
        chat_reply = await call_viola_chat(sender, message_text)
        reply = chat_reply.content
        if chat_reply.tool_events:
            logger.info(
                "Pipeline tool_events sender={!r} events={}",
                sender,
                chat_reply.tool_events,
            )
        if not reply:
            reply = fallback
        elif looks_like_html_response(reply):
            logger.error(
                "Suppressed HTML upstream reply sender={!r} preview={!r}",
                sender,
                reply[:120],
            )
            reply = fallback
        workflow_state = advance_on_assistant_message(workflow_state, assistant_text=reply)
        _legacy_state_set(session_key, workflow_state)
    except Exception:
        logger.exception("Viola /v1/chat/completions failed for {}", sender)
        reply = fallback
        workflow_state = advance_on_assistant_message(workflow_state, assistant_text=reply)
        _legacy_state_set(session_key, workflow_state)

    try:
        out = await send_whatsapp_message_back(
            reply,
            sender,
            webhook_messaging_service_sid=mg_sid,
        )
        _log_twilio_send("final_reply", out)
    except Exception:
        logger.exception("Twilio send (final reply) failed for {}", sender)



@app.post("/api/twilio-message-status")
async def twilio_outbound_status_callback(_request: Request) -> Response:
    """Ack Twilio outbound ``status_callback`` when ``VIOLA_API_BASE`` hits this webhook (avoids 404 noise)."""
    return Response(status_code=204)



@app.get("/check-webhook")
async def get_webhook() -> PlainTextResponse:
    """Health probe for Twilio console / ngrok (Twilio inbound uses POST)."""
    return PlainTextResponse("ok", status_code=200)


@app.post("/webhook")
async def post_webhook(request: Request) -> Response:
    """WhatsApp via Twilio: ack HTTP immediately; Viola + outbound sends run in background.

    Twilio webhook HTTP waits only ~15s; ``call_viola_chat`` can exceed that and would
    abort the callback if we blocked here.
    """
    try:
        form_data = await request.form()
        sender = _twilio_sender_from_form(form_data)
        if not sender:
            logger.warning(
                "Webhook missing sender (From/WaId). {}",
                _twilio_webhook_diagnosis(request, form_data),
            )
            return HTMLResponse(content="", status_code=200)

        snapshot = _form_to_plain_dict(form_data)
        msg_sid = str(snapshot.get("MessageSid") or snapshot.get("SmsMessageSid") or "").strip()
        logger.info(
            "Webhook accepted MessageSid={!r} sender={!r} — scheduling background pipeline",
            msg_sid or "(none)",
            sender,
        )

        def _log_pipeline_failure(done: asyncio.Task[None]) -> None:
            if done.cancelled():
                return
            exc = done.exception()
            if exc is not None:
                logger.exception(
                    "Background WhatsApp pipeline failed for sender={!r}",
                    sender,
                )

        task = asyncio.create_task(_whatsapp_reply_pipeline(snapshot))
        task.add_done_callback(_log_pipeline_failure)

        # Twilio recommends a fast 2xx ack; 202 Accepted when replying later via REST API.
        return Response(status_code=202)

    except Exception:
        logger.exception("Webhook handler error")
        error_response = MessagingResponse()
        error_response.message(
            "抱歉，處理您的訊息時發生錯誤。請稍後再試。\n"
            "Sorry, an error occurred while processing your message. Please try again later."
        )
        return HTMLResponse(content=str(error_response), media_type="application/xml", status_code=500)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


_DIAG_PROBED = False


async def _probe_viola_mcp_once() -> None:
    """Hit Viola's /v1/diag once and log MCP status — visible in webhook logs.

    This is a one-shot probe per webhook process so the operator sees, without
    needing to read viola serve logs separately, whether Viola has the expected
    MCP tools registered. Repeated probes are cheap (the diag endpoint is fast)
    but we only need to log once unless the count changes.
    """
    global _DIAG_PROBED
    if _DIAG_PROBED:
        return
    _DIAG_PROBED = True
    cfg = _settings()
    base = cfg.viola_api_base.rstrip("/")
    url = f"{base}/v1/diag"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.warning("Viola diag probe failed at {}: {}", url, exc)
        return

    configured = data.get("mcp_servers_configured") or []
    connected = data.get("mcp_servers_connected") or []
    failed = data.get("mcp_servers_failed") or []
    mcp_tools = data.get("mcp_tools") or []
    if not configured:
        logger.warning(
            "Viola has NO MCP servers configured. Backend tool calls (e.g. projects_create) will not happen. "
            "Set BACKEND_API_BASE_URL in the viola-agent container env."
        )
    elif failed:
        logger.error(
            "Viola MCP servers failed to connect: {}. Connected: {}. Run viola serve with --verbose to see the cause.",
            failed, connected,
        )
    else:
        logger.info(
            "Viola MCP ready: connected={} tools={} (sample: {})",
            connected, len(mcp_tools), mcp_tools[:5],
        )
