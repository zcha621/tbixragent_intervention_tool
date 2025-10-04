#!/usr/bin/env python3
"""
Unity Render Streaming Python Client
High-performance client with H.264 support, interactive controls, and screenshot capture
"""

import asyncio
import logging
import argparse
import signal
import uuid
import json
import cv2
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable

import aiortc
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.codecs import get_capabilities
import numpy as np
from PIL import Image

# Import our existing modules
from src.signaling import WebSocketSignaling
from src.media_handlers import VideoReceiver

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

class EnhancedVideoReceiver(VideoReceiver):
    """Enhanced video receiver with screenshot and control capabilities"""
    
    def __init__(self, enable_screenshots=False, screenshot_dir="screenshots", screenshot_format="jpg"):
        super().__init__()
        self.enable_screenshots = enable_screenshots
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_format = screenshot_format.lower()
        self.screenshot_handler = None
        self.frame_handler = None
        self.current_frame = None
        self.quit_requested = False
        
        # Create screenshot directory
        if self.enable_screenshots:
            self.screenshot_dir.mkdir(exist_ok=True)
            logger.info(f"Screenshots will be saved to: {self.screenshot_dir}")
            
    def set_screenshot_handler(self, handler: Callable[[str], None]):
        """Set custom screenshot handler callback"""
        self.screenshot_handler = handler
        
    def set_frame_handler(self, handler: Callable[[np.ndarray, int], np.ndarray]):
        """Set custom frame processing handler"""
        self.frame_handler = handler
        
    async def handle_track(self, track):
        """Handle incoming video track with enhanced features"""
        frame_count = 0
        
        try:
            # Create window if displaying
            if not self.quit_requested:
                cv2.namedWindow("Unity Render Streaming", cv2.WINDOW_AUTOSIZE | cv2.WINDOW_KEEPRATIO)
                cv2.moveWindow("Unity Render Streaming", 100, 100)
                logger.info("Created video window with enhanced controls")
            
            # Main video loop using track.recv()
            while not self.quit_requested:
                try:
                    # Receive frame from track
                    frame = await asyncio.wait_for(track.recv(), timeout=5.0)
                    
                    if frame is None:
                        logger.warning("Received None frame")
                        break
                        
                    frame_count += 1
                    
                    # Convert to numpy array
                    img = frame.to_ndarray(format="bgr24")
                    self.current_frame = img.copy()
                    
                    # Call custom frame handler if set
                    if self.frame_handler:
                        try:
                            img = self.frame_handler(img, frame_count)
                        except Exception as e:
                            logger.error(f"Error in frame handler: {e}")
                            
                    # Display frame with enhanced controls
                    if not self.quit_requested:
                        self._display_frame_with_controls(img, frame_count)
                        
                    # Log progress every 30 frames (1 second at 30fps)
                    if frame_count % 30 == 0:
                        logger.info(f"Processed {frame_count} frames")
                        
                except asyncio.TimeoutError:
                    logger.warning("Frame receive timeout")
                    continue
                except Exception as e:
                    logger.error(f"Error receiving frame: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error in video track handler: {e}")
        finally:
            logger.info("Video track ended")
            cv2.destroyAllWindows()
            
    def _display_frame_with_controls(self, frame, frame_count):
        """Display frame with interactive controls"""
        try:
            # Add frame info overlay
            info_text = f"Frame: {frame_count} | Press 'Q' to quit"
            if self.enable_screenshots:
                info_text += " | 'S' to screenshot"
                
            cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (0, 255, 0), 2, cv2.LINE_AA)
            
            # Display frame
            cv2.imshow("Unity Render Streaming", frame)
            
            # Handle key presses (non-blocking)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == ord('Q') or key == 27:  # Q or ESC
                logger.info("Quit key pressed")
                self.quit_requested = True
                
            elif key == ord('s') or key == ord('S'):  # S for screenshot
                if self.enable_screenshots:
                    self._save_screenshot(frame, frame_count)
                else:
                    logger.info("Screenshots not enabled. Use --screenshots flag.")
                    
        except Exception as e:
            logger.error(f"Error displaying frame: {e}")
            
    def _save_screenshot(self, frame, frame_count):
        """Save screenshot in specified format(s)"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            base_filename = f"unity_frame_{timestamp}"
            
            saved_files = []
            
            if self.screenshot_format in ["jpg", "jpeg", "both"]:
                jpg_path = self.screenshot_dir / f"{base_filename}.jpg"
                cv2.imwrite(str(jpg_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                saved_files.append(str(jpg_path))
                
            if self.screenshot_format in ["png", "both"]:
                png_path = self.screenshot_dir / f"{base_filename}.png"
                cv2.imwrite(str(png_path), frame)
                saved_files.append(str(png_path))
                
            # Log successful saves
            for filepath in saved_files:
                logger.info(f"📸 Screenshot saved: {filepath}")
                
                # Call custom screenshot handler
                if self.screenshot_handler:
                    try:
                        self.screenshot_handler(filepath)
                    except Exception as e:
                        logger.error(f"Error in screenshot handler: {e}")
                        
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")

class UnityStreamingClient:
    """Unity Render Streaming client with enhanced features"""
    
    def __init__(self, server_url: str = "ws://localhost/", 
                 enable_screenshots: bool = False,
                 screenshot_dir: str = "screenshots",
                 screenshot_format: str = "jpg"):
        self.server_url = server_url
        self.enable_screenshots = enable_screenshots
        self.screenshot_dir = screenshot_dir
        self.screenshot_format = screenshot_format
        
        self.signaling = None
        self.pc = None
        self.video_receiver = None
        self.connection_id = str(uuid.uuid4())
        self.shutdown_event = asyncio.Event()
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # WebRTC configuration
        self.pc = RTCPeerConnection(configuration=aiortc.RTCConfiguration(
            iceServers=[
                aiortc.RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
                aiortc.RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
            ]
        ))
        
    def _setup_signal_handlers(self):
        """Setup signal handlers for Ctrl+C"""
        def signal_handler(signum, frame):
            logger.info("Ctrl+C received, shutting down gracefully...")
            self.shutdown_event.set()
            
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
            
    def set_frame_handler(self, handler: Callable[[np.ndarray, int], np.ndarray]):
        """Set custom frame processing handler"""
        if self.video_receiver:
            self.video_receiver.set_frame_handler(handler)
            
    def set_screenshot_handler(self, handler: Callable[[str], None]):
        """Set custom screenshot handler"""
        if self.video_receiver:
            self.video_receiver.set_screenshot_handler(handler)
        
    async def run(self):
        """Start the Unity streaming client"""
        try:
            # Initialize components
            self.signaling = WebSocketSignaling(self.server_url)
            self.video_receiver = EnhancedVideoReceiver(
                enable_screenshots=self.enable_screenshots,
                screenshot_dir=self.screenshot_dir, 
                screenshot_format=self.screenshot_format
            )
            
            # Set up WebRTC event handlers
            self._setup_webrtc_handlers()
            
            # Set up signaling callbacks
            self.signaling.on_offer = self._on_signaling_offer
            self.signaling.on_answer = self._on_signaling_answer
            self.signaling.on_candidate = self._on_signaling_candidate
            
            # Connect to signaling server
            logger.info("🔌 Connecting to Unity server...")
            await self.signaling.start()
            
            # Create connection ID
            self.connection_id = await self.signaling.create_connection(self.connection_id)
            logger.info(f"🆔 Created connection: {self.connection_id}")
            
            # Browser-like negotiation: wait a bit then create data channel and offer
            await asyncio.sleep(0.1)
            await self._create_data_channel_and_offer()
            
            # Wait for shutdown
            logger.info("🎮 Unity client started. Press Q to quit or Ctrl+C to exit.")
            await self.shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Error in client: {e}")
            raise
        finally:
            await self.cleanup()
            
    def _setup_webrtc_handlers(self):
        """Set up WebRTC peer connection event handlers"""
        
        @self.pc.on("icecandidate")
        def on_icecandidate(candidate):
            if candidate:
                asyncio.create_task(self._send_ice_candidate(candidate))
        
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            state = self.pc.connectionState
            logger.info(f"🔗 WebRTC connection state: {state}")
            
            if state == "connected":
                logger.info("🎉 WebRTC connection established with H.264 preference!")
            elif state in ["failed", "closed"]:
                logger.warning(f"❌ Connection {state}, shutting down...")
                self.shutdown_event.set()
        
        @self.pc.on("track")
        def on_track(track):
            logger.info(f"📺 Received {track.kind} track")
            if track.kind == "video":
                logger.info("🎬 Starting H.264 video playback...")
                asyncio.create_task(self.video_receiver.handle_track(track))
                
        # Monitor for quit requests from video receiver
        async def monitor_quit():
            while not self.shutdown_event.is_set():
                if self.video_receiver and self.video_receiver.quit_requested:
                    logger.info("Quit requested from video display")
                    self.shutdown_event.set()
                    break
                await asyncio.sleep(0.1)
                
        asyncio.create_task(monitor_quit())
                
    async def _create_data_channel_and_offer(self):
        """Create data channel and send offer (browser behavior)"""
        try:
            # Create data channel (this triggers Unity)
            data_channel = self.pc.createDataChannel("input")
            logger.info("📡 Created data channel: input")
            
            # Add video transceiver for receiving
            video_transceiver = self.pc.addTransceiver("video", direction="recvonly")
            logger.info("📹 Added video transceiver (recvonly)")
            
            # Create offer
            offer = await self.pc.createOffer()
            
            # Modify offer to prefer H.264
            modified_offer = self._modify_offer_for_h264(offer)
            
            await self.pc.setLocalDescription(modified_offer)
            logger.info("📝 Set local description (H.264-preferred offer)")
            
            # Send offer
            await self.signaling.send_offer(self.connection_id, modified_offer.sdp)
            logger.info("📤 Sent H.264-preferred offer to Unity")
            
        except Exception as e:
            logger.error(f"Error creating offer: {e}")
            raise
            
    def _modify_offer_for_h264(self, offer: RTCSessionDescription) -> RTCSessionDescription:
        """Modify SDP offer to prefer H.264 over VP8"""
        lines = offer.sdp.split('\r\n')
        modified_lines = []
        
        logger.info("🔧 Modifying SDP to prefer H.264...")
        
        for line in lines:
            if line.startswith('m=video'):
                # Reorder codecs in video media line to prefer H.264
                parts = line.split(' ')
                if len(parts) > 3:
                    codecs = parts[3:]
                    
                    # Separate H.264 and other codecs
                    h264_codecs = []
                    rtx_codecs = []
                    other_codecs = []
                    
                    for codec in codecs:
                        # Common H.264 payload types: 123, 122, 121, 120
                        if codec in ['123', '122', '121', '120']:
                            h264_codecs.append(codec)
                        # RTX (retransmission) for H.264: 115, 114, 111, 109
                        elif codec in ['115', '114', '111', '109']:
                            rtx_codecs.append(codec)
                        else:
                            other_codecs.append(codec)
                    
                    # Reorder: H.264 first, then RTX, then others (VP8, etc.)
                    reordered_codecs = h264_codecs + rtx_codecs + other_codecs
                    modified_line = ' '.join(parts[:3] + reordered_codecs)
                    modified_lines.append(modified_line)
                    
                    logger.info(f"Original codec order: {codecs}")
                    logger.info(f"H.264-preferred order: {reordered_codecs}")
                else:
                    modified_lines.append(line)
            else:
                modified_lines.append(line)
        
        modified_sdp = '\r\n'.join(modified_lines)
        return RTCSessionDescription(sdp=modified_sdp, type=offer.type)
        
    async def _on_signaling_offer(self, offer_data: Dict[str, Any]):
        """Handle offer from Unity - respond with answer"""
        try:
            sdp = offer_data.get('sdp')
            if not sdp:
                logger.error("No SDP in offer")
                return
                
            logger.info("📨 Received offer from Unity - setting as remote description and sending answer")
            
            # Set remote description
            offer = RTCSessionDescription(sdp=sdp, type="offer")
            await self.pc.setRemoteDescription(offer)
            logger.info("✅ Remote description set from Unity offer")
            
            # Create answer
            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)
            logger.info("📝 Created and set local answer")
            
            # Send answer
            await self.signaling.send_answer(self.connection_id, answer.sdp)
            logger.info("📤 Sent answer to Unity")
            
        except Exception as e:
            logger.error(f"Error handling Unity offer: {e}")
            
    async def _on_signaling_answer(self, answer_data: Dict[str, Any]):
        """Handle answer from signaling"""
        try:
            sdp = answer_data.get('sdp')
            if not sdp:
                logger.error("No SDP in answer")
                return
                
            logger.info("📨 Received answer from signaling")
            answer = RTCSessionDescription(sdp=sdp, type="answer")
            await self.pc.setRemoteDescription(answer)
            logger.info("✅ Remote description set from answer")
            
        except Exception as e:
            logger.error(f"Error handling answer: {e}")
            
    async def _on_signaling_candidate(self, candidate_data: Dict[str, Any]):
        """Handle ICE candidate from signaling"""
        try:
            # Handle ICE candidate properly
            if isinstance(candidate_data, dict) and 'candidate' in candidate_data:
                candidate_str = candidate_data['candidate']
                sdp_m_line_index = candidate_data.get('sdpMLineIndex', 0)
                
                # Create ICE candidate
                ice_candidate = aiortc.RTCIceCandidate(
                    component=1,
                    foundation="1",
                    ip="0.0.0.0",  # Will be parsed from candidate string
                    port=9,
                    priority=2113667326,
                    protocol="udp",
                    type="host",
                    sdpMLineIndex=sdp_m_line_index
                )
                
                # Parse the candidate string to extract actual values
                if candidate_str.startswith("candidate:"):
                    parts = candidate_str.split()
                    if len(parts) >= 8:
                        ice_candidate.foundation = parts[1]
                        ice_candidate.component = int(parts[2])
                        ice_candidate.protocol = parts[3]
                        ice_candidate.priority = int(parts[4])
                        ice_candidate.ip = parts[5]
                        ice_candidate.port = int(parts[6])
                        ice_candidate.type = parts[8]
                
                await self.pc.addIceCandidate(ice_candidate)
                logger.debug(f"Added ICE candidate: {candidate_str}")
                
        except Exception as e:
            logger.debug(f"Error handling ICE candidate: {e}")
            # Don't fail on ICE candidate errors, just log them
            
    async def _send_ice_candidate(self, candidate):
        """Send ICE candidate to signaling server"""
        try:
            candidate_data = {
                "candidate": f"candidate:{candidate.foundation} {candidate.component} {candidate.protocol} {candidate.priority} {candidate.ip} {candidate.port} typ {candidate.type}",
                "sdpMLineIndex": candidate.sdpMLineIndex,
                "sdpMid": None
            }
            
            await self.signaling.send_candidate(self.connection_id, candidate_data)
            logger.debug(f"Sent ICE candidate: {candidate_data['candidate']}")
            
        except Exception as e:
            logger.error(f"Error sending ICE candidate: {e}")
            
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up resources...")
        
        try:
            # Set quit flag for video receiver
            if self.video_receiver:
                self.video_receiver.quit_requested = True
                
            # Close peer connection
            if self.pc:
                await self.pc.close()
                
            # Close signaling - use stop() method instead of close()
            if self.signaling:
                await self.signaling.stop()
                
            # Close any OpenCV windows
            cv2.destroyAllWindows()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
        logger.info("✅ Cleanup completed")

# Compatibility alias
H264UnityClient = UnityStreamingClient


async def main():
    """Main entry point"""
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Unity Render Streaming Python Client", 
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python unity_client.py                                    # Basic usage
  python unity_client.py --server ws://192.168.1.100:8080  # Custom server
  python unity_client.py --screenshots --verbose           # With screenshots and debug
  python unity_client.py --screenshots --screenshot-format png  # PNG screenshots
        """)
    
    parser.add_argument("--server", default="ws://localhost/", 
                       help="WebSocket server URL (default: ws://localhost/)")
    parser.add_argument("--connection-id", default=None,
                       help="Specific connection ID to use")
    parser.add_argument("--screenshots", action="store_true",
                       help="Enable screenshot saving (press S to capture)")
    parser.add_argument("--screenshot-dir", default="screenshots",
                       help="Directory to save screenshots (default: screenshots/)")
    parser.add_argument("--screenshot-format", default="jpg", 
                       choices=["jpg", "jpeg", "png", "both"],
                       help="Screenshot format: jpg, png, or both (default: jpg)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('aiortc').setLevel(logging.DEBUG)
        logging.getLogger('websockets').setLevel(logging.DEBUG)
    else:
        logging.getLogger('aiortc').setLevel(logging.WARNING)
        logging.getLogger('websockets').setLevel(logging.WARNING)
        
    # Print startup information
    logger.info("🎮 Unity Render Streaming Python Client")
    logger.info(f"🔗 Server: {args.server}")
    if args.screenshots:
        logger.info(f"📸 Screenshots: Enabled ({args.screenshot_format} format)")
        logger.info(f"📁 Screenshot directory: {args.screenshot_dir}")
    logger.info("⌨️  Controls: Press Q to quit, Ctrl+C to exit")
    if args.screenshots:
        logger.info("📷 Press S to save screenshot")
        
    # Create and start client
    client = UnityStreamingClient(
        server_url=args.server,
        enable_screenshots=args.screenshots,
        screenshot_dir=args.screenshot_dir,
        screenshot_format=args.screenshot_format
    )
    
    try:
        await client.run()
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error running client: {e}")
        
    logger.info("👋 Unity Render Streaming client stopped")


if __name__ == "__main__":
    asyncio.run(main())