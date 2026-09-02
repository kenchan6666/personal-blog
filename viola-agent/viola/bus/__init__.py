"""Message bus module for decoupled channel-agent communication."""

from viola.bus.events import InboundMessage, OutboundMessage
from viola.bus.queue import MessageBus

__all__ = ["MessageBus", "InboundMessage", "OutboundMessage"]
