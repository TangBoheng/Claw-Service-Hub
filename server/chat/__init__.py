"""Chat module for Claw Service Hub.

This module provides chat channel management for service communication.
"""

from .channel import ChatChannel, ChatMessage, ChatChannelManager, get_channel_manager
from .handlers import ChatHandler

__all__ = [
    'ChatChannel',
    'ChatMessage',
    'ChatChannelManager',
    'get_channel_manager',
    'ChatHandler',
]
