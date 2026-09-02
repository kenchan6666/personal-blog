"""Twilio WhatsApp outbound: typing indicator, template messages, text/media with chunking.

Environment (typical):
  ACCOUNT_SID / TWILIO_ACCOUNT_SID, AUTH_TOKEN / TWILIO_AUTH_TOKEN
  WHATSAPP_NUMBER — sender when MESSAGING_SERVICE_SID is not set
  MESSAGING_SERVICE_SID — preferred sender
  BACKEND_API_BASE_URL — optional **public** ``https://...`` base for outbound ``status_callback``. Omit locally.
    Invalid or internal URLs trigger Twilio **21609**.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, NamedTuple

from loguru import logger
from requests.exceptions import ConnectionError, Timeout
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from viola.api.twilio_media import twilio_rest_credentials

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

__all__ = (
    "TwilioHttpResult",
    "send_typing_indicator",
    "send_whatsapp_message_back",
    "send_whatsapp_template_message_back",
)


class TwilioHttpResult(NamedTuple):
    """Use with aiohttp ``web.json_response(r.content, status=r.status_code)`` or FastAPI."""

    content: dict[str, Any]
    status_code: int




_client: Client | None = None


def _twilio_client() -> Client | None:
    global _client
    if _client is not None:
        return _client
    creds = twilio_rest_credentials()
    if not creds:
        return None
    sid, token = creds
    _client = Client(sid, token)
    return _client


chatbot_waba = os.getenv("WHATSAPP_NUMBER")
messaging_service_sid = os.getenv("MESSAGING_SERVICE_SID")
backend_api_base_url = os.getenv("BACKEND_API_BASE_URL")

MAX_TWILIO_MSG_LENGTH = 1500
MAX_RETRY_ATTEMPTS = 3
INITIAL_RETRY_DELAY = 1  # seconds
MAX_RETRY_DELAY = 10  # seconds


async def send_typing_indicator(
    message_id: str,
    channel: str = "whatsapp",
) -> bool:
    """
    Signal to the WhatsApp user that a reply is being prepared (Twilio public beta).

    Twilio ties the indicator to the inbound message you are responding to: pass the
    webhook ``MessageSid`` (``SM...``) or a media SID (``MM...``), not raw phone numbers.

    See: https://www.twilio.com/docs/whatsapp/api/typing-indicators-resource
    """
    if not message_id or not str(message_id).strip():
        logger.warning("send_typing_indicator: empty message_id")
        return False
    client = _twilio_client()
    if not client:
        logger.error("send_typing_indicator: Twilio credentials not set")
        return False

    mid = str(message_id).strip()
    try:
        result = await asyncio.to_thread(client.messaging.v2.typing_indicator.create, channel=channel, message_id=message_id)
        return bool(result.success)
    except (ConnectionError, Timeout) as exc:
        logger.warning("send_typing_indicator: transient network error for message_id={}: {}", mid, exc)
        return False
    except TwilioRestException as exc:
        logger.warning("send_typing_indicator: Twilio error for message_id={}: {}", mid, exc)
    except TwilioRestException:
        logger.exception("Twilio typing indicator failed for message_id={}", mid)
        return False
    except Exception:
        logger.exception("Unexpected error sending typing indicator for message_id={}", mid)
        return False


def _is_retryable_error(error: Exception) -> bool:
    """Transient network/connection issues and server-side rate limits."""
    if isinstance(error, (ConnectionError, Timeout)):
        return True
    if isinstance(error, TwilioRestException):
        if error.status and (error.status >= 500 or error.status == 429):
            return True
    error_str = str(error).lower()
    retryable_keywords = [
        "connection aborted",
        "remote end closed",
        "connection reset",
        "timeout",
        "network",
        "temporary failure",
    ]
    return any(keyword in error_str for keyword in retryable_keywords)


async def _send_message_with_retry(client: Client, message_params: dict) -> tuple[bool, Any]:
    last_error = None

    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        try:
            logger.info(
                "Attempting to send message (attempt {}/{})",
                attempt,
                MAX_RETRY_ATTEMPTS,
            )
            msg = await asyncio.to_thread(
                lambda: client.messages.create(**message_params),
            )
            logger.info(
                "Message sent successfully. SID: {}, Status: {}",
                msg.sid,
                msg.status,
            )
            return True, msg

        except Exception as e:
            last_error = e
            error_str = str(e)

            if not _is_retryable_error(e):
                logger.error("Non-retryable error occurred: {}", error_str)
                return False, e

            if attempt < MAX_RETRY_ATTEMPTS:
                delay = min(INITIAL_RETRY_DELAY * (2 ** (attempt - 1)), MAX_RETRY_DELAY)
                logger.warning(
                    "Retryable error on attempt {}: {}. Retrying in {} seconds...",
                    attempt,
                    error_str,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Failed to send message after {} attempts. Last error: {}",
                    MAX_RETRY_ATTEMPTS,
                    error_str,
                )

    return False, last_error


async def send_whatsapp_template_message_back(
    content_sid: str,
    content_variables: dict | None,
    recipient: str,
) -> TwilioHttpResult:
    """
    Send a WhatsApp message using a Twilio Content Template (content_sid).

    content_variables: mapping for template placeholders, e.g. {"1": "123456"}
    recipient: WhatsApp recipient (with or without ``whatsapp:`` prefix)
    """
    try:
        if not recipient:
            logger.error("Empty recipient provided")
            return TwilioHttpResult(
                content={"status": "error", "message": "Empty recipient"},
                status_code=400,
            )

        if not content_sid or not str(content_sid).strip():
            logger.error("Empty content_sid provided")
            return TwilioHttpResult(
                content={"status": "error", "message": "Empty content template id"},
                status_code=400,
            )

        client = _twilio_client()
        if not client:
            logger.error("Twilio credentials not set")
            return TwilioHttpResult(
                content={"status": "error", "message": "Twilio not configured"},
                status_code=500,
            )

        to = recipient
        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"

        message_params: dict[str, Any] = {
            "to": to,
            "content_sid": str(content_sid).strip(),
        }
        msid = messaging_service_sid
        if msid:
            message_params["messaging_service_sid"] = msid
        else:
            if not chatbot_waba:
                logger.error(
                    "WHATSAPP_NUMBER is not set; cannot send without messaging_service_sid.",
                )
                return TwilioHttpResult(
                    content={
                        "status": "error",
                        "message": "WhatsApp sender not configured",
                    },
                    status_code=500,
                )
            message_params["from_"] = f"whatsapp:{chatbot_waba}"

        if content_variables:
            message_params["content_variables"] = json.dumps(
                {str(k): str(v) for k, v in content_variables.items()},
            )

        success, result = await _send_message_with_retry(client, message_params)
        if not success:
            error_msg = str(result)
            if isinstance(result, BaseException):
                logger.opt(exception=result).error(
                    "Failed to send WhatsApp template message after retries",
                )
            else:
                logger.error(
                    "Failed to send WhatsApp template message after retries: {}",
                    error_msg,
                )
            return TwilioHttpResult(
                content={
                    "status": "error",
                    "message": f"Failed to send WhatsApp template message: {error_msg}",
                },
                status_code=500,
            )

        msg = result
        return TwilioHttpResult(
            content={
                "status": "success",
                "sids": [msg.sid],
                "message": "Message sent successfully",
            },
            status_code=200,
        )

    except Exception as e:
        logger.exception("Error sending WhatsApp template message")
        return TwilioHttpResult(
            content={
                "status": "error",
                "message": f"Failed to send WhatsApp template message: {e!s}",
            },
            status_code=500,
        )


async def send_whatsapp_message_back(
    body_text: str | dict,
    recipient: str,
    media_url: str | list[str] | None = None,
    webhook_messaging_service_sid: str | None = None,
) -> TwilioHttpResult:
    try:
        if not recipient:
            logger.error("Empty recipient provided")
            return TwilioHttpResult(
                content={"status": "error", "message": "Empty recipient"},
                status_code=400,
            )

        client = _twilio_client()
        if not client:
            logger.error("Twilio credentials not set")
            return TwilioHttpResult(
                content={"status": "error", "message": "Twilio not configured"},
                status_code=500,
            )

        to = recipient
        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"

        if isinstance(body_text, dict):
            meta = body_text.get("meta", {})
            message_text = body_text.get("text", "")
        else:
            meta = {}
            message_text = str(body_text)

        if isinstance(media_url, str):
            media_urls = [media_url] if media_url.strip() else []
        elif isinstance(media_url, list):
            media_urls = [str(url).strip() for url in media_url if str(url).strip()]
        else:
            media_urls = []

        msid = messaging_service_sid
        logger.info("Preparing to send message to: {}", to)
        logger.info("Using WhatsApp number: {}", chatbot_waba)
        logger.info("Using messaging service SID: {}", msid or "(from WHATSAPP_NUMBER)")
        if media_urls:
            logger.info("Preparing {} WhatsApp media attachment(s)", len(media_urls))

        message_params: dict[str, Any] = {"to": to}
        if msid:
            message_params["messaging_service_sid"] = msid
        else:
            if not chatbot_waba:
                logger.error(
                    "WhatsApp sender not configured: set WHATSAPP_NUMBER or pass MessagingServiceSid / MESSAGING_SERVICE_SID.",
                )
                return TwilioHttpResult(
                    content={
                        "status": "error",
                        "message": "WhatsApp sender not configured",
                    },
                    status_code=500,
                )
            message_params["from_"] = f"whatsapp:{chatbot_waba}"

        message_sids: list[str] = []

        if len(message_text) > MAX_TWILIO_MSG_LENGTH:
            chunks: list[str] = []

            logical_breaks = [
                "\n\n",
                "\n---\n",
                "\n===\n",
                "\n• ",
            ]

            best_break = None
            best_position = 0

            for break_pattern in logical_breaks:
                if break_pattern in message_text:
                    pos = message_text.rfind(break_pattern, 0, MAX_TWILIO_MSG_LENGTH)
                    if pos > best_position:
                        best_position = pos + len(break_pattern)
                        best_break = break_pattern

            if best_break and best_position > 0:
                first_chunk = message_text[:best_position].strip()
                remaining_text = message_text[best_position:].strip()

                chunks = [first_chunk]

                while len(remaining_text) > MAX_TWILIO_MSG_LENGTH:
                    next_break_pos = 0
                    for break_pattern in logical_breaks:
                        pos = remaining_text.rfind(
                            break_pattern,
                            0,
                            MAX_TWILIO_MSG_LENGTH,
                        )
                        if pos > next_break_pos:
                            next_break_pos = pos + len(break_pattern)

                    if next_break_pos > 0:
                        chunks.append(remaining_text[:next_break_pos].strip())
                        remaining_text = remaining_text[next_break_pos:].strip()
                    else:
                        break

                if remaining_text:
                    chunks.append(remaining_text)
            else:
                single_newline_chunks: list[str] = []
                current_chunk = ""
                lines = message_text.split("\n")

                for line in lines:
                    if (
                        len(current_chunk) + len(line) + 1 > MAX_TWILIO_MSG_LENGTH
                        and current_chunk
                    ):
                        single_newline_chunks.append(current_chunk.strip())
                        current_chunk = line
                    else:
                        if current_chunk:
                            current_chunk += "\n" + line
                        else:
                            current_chunk = line

                if current_chunk:
                    single_newline_chunks.append(current_chunk.strip())

                if single_newline_chunks:
                    chunks = single_newline_chunks
                else:
                    prefix_len = len("(X/Y) ")
                    max_chunk = MAX_TWILIO_MSG_LENGTH - prefix_len
                    chunks = [
                        message_text[i : i + max_chunk]
                        for i in range(0, len(message_text), max_chunk)
                    ]
        else:
            chunks = [message_text]

        for idx, chunk in enumerate(chunks):
            formatted_chunk = (
                f"({idx + 1}/{len(chunks)}) {chunk}" if len(chunks) > 1 else chunk
            )
            logger.info(
                "Sending chunk {}/{}: {} characters",
                idx + 1,
                len(chunks),
                len(formatted_chunk),
            )
            message_params["body"] = formatted_chunk
            message_params.pop("media_url", None)

            success, result = await _send_message_with_retry(client, message_params)

            if not success:
                error_msg = str(result)
                if isinstance(result, BaseException):
                    logger.opt(exception=result).error("Failed to send chunk after retries")
                else:
                    logger.error("Failed to send chunk after retries: {}", error_msg)
                raise RuntimeError(f"Failed to send WhatsApp message chunk: {error_msg}")

            msg = result
            message_sids.append(msg.sid)
            logger.info("Message sent. SID: {}, Status: {}", msg.sid, msg.status)

            if idx < len(chunks) - 1:
                await asyncio.sleep(1)

        for media_idx, url in enumerate(media_urls, start=1):
            media_params = dict(message_params)
            media_params.pop("body", None)
            media_params["media_url"] = [url]
            logger.info(
                "Sending WhatsApp media attachment {}/{}: {}",
                media_idx,
                len(media_urls),
                url,
            )

            success, result = await _send_message_with_retry(client, media_params)
            if not success:
                error_msg = str(result)
                if isinstance(result, BaseException):
                    logger.opt(exception=result).error(
                        "Failed to send media attachment after retries",
                    )
                else:
                    logger.error(
                        "Failed to send media attachment after retries: {}",
                        error_msg,
                    )
                continue

            msg = result
            message_sids.append(msg.sid)
            logger.info(
                "Media attachment message sent. SID: {}, Status: {}",
                msg.sid,
                msg.status,
            )

        return TwilioHttpResult(
            content={
                "status": "success",
                "sids": message_sids,
                "message": "Messages sent successfully",
                "meta": meta,
            },
            status_code=200,
        )

    except Exception as e:
        logger.exception("Error sending WhatsApp message")
        return TwilioHttpResult(
            content={
                "status": "error",
                "message": f"Failed to send WhatsApp message: {str(e)}",
            },
            status_code=500,
        )
