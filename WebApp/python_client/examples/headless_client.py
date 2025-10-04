"""
Headless Unity Render Streaming Python client example (no display)
"""

import asyncio
import logging
import sys
import os
import time

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.client import UnityRenderStreamingClient


class HeadlessFrameProcessor:
    """Process frames without displaying them"""
    
    def __init__(self, save_interval=30):
        """
        Args:
            save_interval: Save a frame every N frames
        """
        self.frame_count = 0
        self.save_interval = save_interval
        self.start_time = time.time()
        self.last_fps_time = time.time()
        self.fps_frame_count = 0
    
    def process_frame(self, frame):
        """Process frame without display"""
        self.frame_count += 1
        self.fps_frame_count += 1
        
        current_time = time.time()
        
        # Calculate and print FPS every 5 seconds
        if current_time - self.last_fps_time >= 5.0:
            fps = self.fps_frame_count / (current_time - self.last_fps_time)
            elapsed = current_time - self.start_time
            print(f"[{elapsed:.1f}s] Frames: {self.frame_count}, FPS: {fps:.1f}, Resolution: {frame.shape}")
            
            self.fps_frame_count = 0
            self.last_fps_time = current_time
        
        # Optionally save frames at intervals
        if self.frame_count % self.save_interval == 0:
            filename = f"output/frame_{self.frame_count:06d}.jpg"
            # You could save the frame here if needed
            # cv2.imwrite(filename, frame)
            print(f"Would save frame to {filename}")


async def main():
    """Headless client example"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting headless Unity Render Streaming client example")
    
    # Create frame processor
    frame_processor = HeadlessFrameProcessor(save_interval=60)
    
    # Create client without display
    client = UnityRenderStreamingClient(
        server_url="ws://localhost:8080",
        display_video=False,  # No display window
        save_frames=False,    # Don't auto-save all frames
        save_audio=True       # Save audio stream
    )
    
    # Setup custom frame processing for monitoring
    client.video_receiver.on_frame = frame_processor.process_frame
    
    # Setup connection state monitoring
    def on_connection_state_change(state):
        logger.info(f"Connection state changed to: {state}")
        if state == "connected":
            logger.info("Stream started successfully!")
        elif state == "failed":
            logger.error("Connection failed!")
        elif state == "disconnected":
            logger.info("Stream ended")
    
    # This will be set when peer is created
    original_setup_peer_handlers = client._setup_peer_handlers
    
    def setup_peer_handlers_with_monitoring():
        original_setup_peer_handlers()
        if client.peer:
            client.peer.on_connection_state_change = on_connection_state_change
    
    client._setup_peer_handlers = setup_peer_handlers_with_monitoring
    
    try:
        logger.info("Starting headless client - will process frames without display")
        logger.info("Press Ctrl+C to stop")
        
        # Run the client
        await client.run()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error running client: {e}")
    finally:
        logger.info(f"Client stopped. Processed {frame_processor.frame_count} frames total")


if __name__ == "__main__":
    # Create output directory
    os.makedirs("output", exist_ok=True)
    asyncio.run(main())