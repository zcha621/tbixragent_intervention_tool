"""
Custom handlers example for Unity Render Streaming Python client
"""

import asyncio
import logging
import sys
import os
import cv2
import numpy as np

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.client import UnityRenderStreamingClient


class CustomFrameHandler:
    """Custom frame processing handler"""
    
    def __init__(self):
        self.frame_count = 0
        self.fps_counter = 0
        self.last_time = asyncio.get_event_loop().time()
    
    def process_frame(self, frame):
        """Custom frame processing"""
        self.frame_count += 1
        self.fps_counter += 1
        
        # Calculate FPS every second
        current_time = asyncio.get_event_loop().time()
        if current_time - self.last_time >= 1.0:
            fps = self.fps_counter / (current_time - self.last_time)
            print(f"FPS: {fps:.1f}, Total frames: {self.frame_count}")
            self.fps_counter = 0
            self.last_time = current_time
        
        # Add frame counter overlay
        text = f"Frame: {self.frame_count}"
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Optional: Apply some image processing
        # frame = cv2.GaussianBlur(frame, (5, 5), 0)
        
        return frame


class DataChannelHandler:
    """Custom data channel message handler"""
    
    def __init__(self):
        self.message_count = 0
    
    def handle_message(self, channel_label, message):
        """Handle data channel messages"""
        self.message_count += 1
        print(f"Data channel '{channel_label}' message {self.message_count}: {message}")
        
        # Echo the message back (if channel is bidirectional)
        # You would need to implement sending capability for this
        pass


async def main():
    """Custom handlers example"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting custom handlers Unity Render Streaming client example")
    
    # Create custom handlers
    frame_handler = CustomFrameHandler()
    data_handler = DataChannelHandler()
    
    # Create client
    client = UnityRenderStreamingClient(
        server_url="ws://localhost:8080",
        display_video=True,
        save_frames=False,
        save_audio=False
    )
    
    # Setup custom frame processing
    original_process_frame = client.video_receiver._process_frame
    
    async def custom_process_frame(frame):
        """Custom frame processing wrapper"""
        # Apply custom processing
        processed_frame = frame_handler.process_frame(frame)
        # Call original processing with modified frame
        return await original_process_frame(processed_frame)
    
    client.video_receiver._process_frame = custom_process_frame
    
    # Setup custom data channel handling
    client.datachannel_handler.on_message = data_handler.handle_message
    
    try:
        # Run the client
        await client.run()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error running client: {e}")
    finally:
        logger.info("Client stopped")


if __name__ == "__main__":
    asyncio.run(main())