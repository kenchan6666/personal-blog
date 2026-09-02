"""Twilio WhatsApp delivery helpers for API (serve) background tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from viola.session.manager import SessionManager


def whatsapp_recipient_from_session_key(session_key: str | None) -> str | None:
    """Map ``api:<digits>`` session keys to a Twilio ``whatsapp:+...`` recipient."""
    if not session_key or not session_key.startswith("api:"):
        return None
    chat_id = session_key.split(":", 1)[1].strip()
    if not chat_id or chat_id == "default":
        return None
    if chat_id.lower().startswith("whatsapp:"):
        return chat_id
    digits = "".join(c for c in chat_id if c.isdigit())
    if len(digits) < 8:
        return None
    return f"whatsapp:+{digits}"


def whatsapp_recipient_for_job(
    *,
    session_key: str | None,
    channel_meta: dict | None,
) -> str | None:
    """Resolve outbound WhatsApp recipient from cron/heartbeat job metadata."""
    meta = channel_meta or {}
    explicit = meta.get("whatsapp_recipient") or meta.get("whatsappRecipient")
    if isinstance(explicit, str) and explicit.strip():
        value = explicit.strip()
        return value if value.lower().startswith("whatsapp:") else f"whatsapp:{value.lstrip('+')}"
    return whatsapp_recipient_from_session_key(session_key)


async def deliver_whatsapp_text(
    text: str,
    *,
    session_key: str | None,
    channel_meta: dict | None = None,
    session_manager: SessionManager | None = None,
) -> bool:
    """Send *text* via Twilio and mirror into the API session when possible."""
    from viola.api.whatsapp_response_template import send_whatsapp_message_back

    recipient = whatsapp_recipient_for_job(
        session_key=session_key,
        channel_meta=channel_meta,
    )
    if not recipient or not text.strip():
        return False

    result = await send_whatsapp_message_back(text, recipient)
    if result.status_code >= 400:
        return False

    if session_manager and session_key:
        session = session_manager.get_or_create(session_key)
        session.add_message("assistant", text, _channel_delivery=True)
        session_manager.save(session)
    return True
