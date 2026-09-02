"""Runtime helpers for gateway and API background services."""

from viola.runtime.background_tasks import (
    ApiBackgroundHandles,
    install_api_background_tasks,
    start_api_background_tasks,
    stop_api_background_tasks,
)
from viola.runtime.whatsapp_outbound import whatsapp_recipient_from_session_key

__all__ = [
    "ApiBackgroundHandles",
    "install_api_background_tasks",
    "start_api_background_tasks",
    "stop_api_background_tasks",
    "whatsapp_recipient_from_session_key",
]
