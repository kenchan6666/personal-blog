"""Chat channels module with plugin architecture."""

from viola.channels.base import BaseChannel
from viola.channels.manager import ChannelManager

__all__ = ["BaseChannel", "ChannelManager"]
