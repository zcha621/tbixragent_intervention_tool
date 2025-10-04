"""
Main Unity Render Streaming Python client
"""

import asyncio
import logging
import argparse
import sys
import os
from typing import Optional

# Add the src directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signaling import WebSocketSignaling
from webrtc_peer import WebRTCPeer
from media_handlers import VideoReceiver, AudioReceiver, DataChannelHandler


class UnityRenderStreamingClient:
    """Main client class for Unity Render Streaming"""
    
    def __init__(self, server_url: str = "ws://localhost:80", 
                 connection_id: Optional[str] = None,
                 display_video: bool = True,
                 save_frames: bool = False,
                 save_audio: bool = False):
        """
        Initialize Unity Render Streaming client
        
        Args:
            server_url: WebSocket server URL
            connection_id: Optional connection ID
            display_video: Whether to display video
            save_frames: Whether to save video frames
            save_audio: Whether to save audio
        """
        self.server_url = server_url
        self.connection_id = connection_id
        
        # Initialize components
        self.signaling = WebSocketSignaling(server_url)
        self.peer = None
        self.video_receiver = VideoReceiver(display_video, save_frames)
        self.audio_receiver = AudioReceiver(save_audio)
        self.datachannel_handler = DataChannelHandler()
        
        self.logger = logging.getLogger(__name__)
        
        # Setup signaling event handlers
        self._setup_signaling_handlers()
    
    def _setup_signaling_handlers(self):
        """Setup signaling event handlers"""
        
        self.signaling.on_connect = self._on_connect
        self.signaling.on_disconnect = self._on_disconnect
        self.signaling.on_offer = self._on_offer
        self.signaling.on_answer = self._on_answer
        self.signaling.on_candidate = self._on_candidate
        self.signaling.on_error = self._on_error
    
    def _on_connect(self, data: dict):
        """Handle connection event"""
        connection_id = data.get('connectionId')
        is_polite = data.get('polite', False)
        
        self.logger.info(f"Connected with ID: {connection_id}, polite: {is_polite}")
        
        # Create WebRTC peer
        self.peer = WebRTCPeer(self.signaling, connection_id, is_polite)
        self._setup_peer_handlers()
    
    def _on_disconnect(self, data: dict):
        """Handle disconnection event"""
        self.logger.info(f"Disconnected: {data}")
        if self.peer:
            asyncio.create_task(self.peer.close())
            self.peer = None
    
    async def _on_offer(self, data: dict):
        """Handle SDP offer"""
        if self.peer:
            await self.peer.handle_offer(data.get('sdp'))
    
    async def _on_answer(self, data: dict):
        """Handle SDP answer"""
        if self.peer:
            await self.peer.handle_answer(data.get('sdp'))
    
    async def _on_candidate(self, data: dict):
        """Handle ICE candidate"""
        if self.peer:
            await self.peer.handle_ice_candidate(data)
    
    def _on_error(self, data: dict):
        """Handle signaling error"""
        self.logger.error(f"Signaling error: {data}")
    
    def _setup_peer_handlers(self):
        """Setup WebRTC peer event handlers"""
        if not self.peer:
            return
        
        self.peer.on_track = self._on_track
        self.peer.on_datachannel = self.datachannel_handler.handle_datachannel
        self.peer.on_connection_state_change = self._on_connection_state_change
    
    def _on_track(self, track):
        """Handle incoming media track"""
        self.logger.info(f"Received {track.kind} track")
        
        if track.kind == "video":
            asyncio.create_task(self.video_receiver.handle_track(track))
        elif track.kind == "audio":
            asyncio.create_task(self.audio_receiver.handle_track(track))
    
    def _on_connection_state_change(self, state: str):
        """Handle connection state changes"""
        self.logger.info(f"WebRTC connection state: {state}")
        
        if state == "connected":
            self.logger.info("WebRTC connection established successfully!")
        elif state == "failed":
            self.logger.error("WebRTC connection failed")
        elif state == "disconnected":
            self.logger.info("WebRTC connection disconnected")
    
    async def start(self):
        """Start the client"""
        self.logger.info("Starting Unity Render Streaming client...")
        
        # Connect to signaling server
        if not await self.signaling.start():
            raise RuntimeError("Failed to connect to signaling server")
        
        # Create connection
        connection_id = await self.signaling.create_connection(self.connection_id)
        self.logger.info(f"Created connection: {connection_id}")
        
        return connection_id
    
    async def stop(self):
        """Stop the client"""
        self.logger.info("Stopping Unity Render Streaming client...")
        
        # Close peer connection
        if self.peer:
            await self.peer.close()
        
        # Close signaling connection
        await self.signaling.stop()
        
        # Cleanup media handlers
        self.video_receiver.cleanup()
    
    async def run(self):
        """Run the client until interrupted"""
        try:
            await self.start()
            
            self.logger.info("Client running. Press Ctrl+C to stop.")
            
            # Keep running until interrupted
            while self.signaling.is_connected:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Error running client: {e}")
            raise
        finally:
            await self.stop()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Unity Render Streaming Python Client")
    parser.add_argument("--server", default="ws://localhost:80", 
                       help="WebSocket server URL")
    parser.add_argument("--connection-id", help="Connection ID to use")
    parser.add_argument("--no-display", action="store_true", 
                       help="Don't display video window")
    parser.add_argument("--save-frames", action="store_true",
                       help="Save video frames to disk")
    parser.add_argument("--save-audio", action="store_true",
                       help="Save audio to file")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run client
    client = UnityRenderStreamingClient(
        server_url=args.server,
        connection_id=args.connection_id,
        display_video=not args.no_display,
        save_frames=args.save_frames,
        save_audio=args.save_audio
    )
    
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())