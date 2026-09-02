"""Tests for API WhatsApp recipient resolution."""

from viola.runtime.whatsapp_outbound import (
    whatsapp_recipient_for_job,
    whatsapp_recipient_from_session_key,
)


def test_session_key_digits():
    assert whatsapp_recipient_from_session_key("api:85264760285") == "whatsapp:+85264760285"


def test_session_key_default_returns_none():
    assert whatsapp_recipient_from_session_key("api:default") is None


def test_channel_meta_explicit():
    assert whatsapp_recipient_for_job(
        session_key="api:default",
        channel_meta={"whatsapp_recipient": "whatsapp:+85211112222"},
    ) == "whatsapp:+85211112222"
