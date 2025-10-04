"""
Python package initialization for Unity Render Streaming client
"""

from .client import UnityRenderStreamingClient
from .signaling import WebSocketSignaling
from .webrtc_peer import WebRTCPeer
from .media_handlers import VideoReceiver, AudioReceiver, DataChannelHandler

__version__ = "1.0.0"
__author__ = "Unity Render Streaming Python Client"

__all__ = [
    "UnityRenderStreamingClient",
    "WebSocketSignaling", 
    "WebRTCPeer",
    "VideoReceiver",
    "AudioReceiver", 
    "DataChannelHandler"
]