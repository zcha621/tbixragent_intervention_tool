"""
Video display and handling for Unity Render Streaming Python client
"""

import asyncio
import logging
import cv2
import numpy as np
from typing import Optional, Callable
import aiortc
from aiortc.contrib.media import MediaStreamTrack
import av


class VideoReceiver:
    """Handles video stream reception and display"""
    
    def __init__(self, display_window: bool = True, save_frames: bool = False, 
                 output_dir: str = "output"):
        """
        Initialize video receiver
        
        Args:
            display_window: Whether to display video in OpenCV window
            save_frames: Whether to save frames to disk
            output_dir: Directory to save frames
        """
        self.display_window = display_window
        self.save_frames = save_frames
        self.output_dir = output_dir
        self.frame_count = 0
        self.window_name = "Unity Render Streaming"
        
        # Event callbacks
        self.on_frame: Optional[Callable[[np.ndarray], None]] = None
        
        self.logger = logging.getLogger(__name__)
        
        # Create output directory if saving frames
        if self.save_frames:
            import os
            os.makedirs(self.output_dir, exist_ok=True)
    
    async def handle_track(self, track: MediaStreamTrack):
        """
        Handle incoming video track
        
        Args:
            track: Video track from WebRTC
        """
        self.logger.info(f"Starting to receive {track.kind} track")
        self.logger.info(f"Track details: {track}")
        
        # If displaying video, create window immediately
        if self.display_window:
            cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE | cv2.WINDOW_KEEPRATIO)
            cv2.moveWindow(self.window_name, 100, 100)  # Position window
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1)  # Keep on top
            
            # Show placeholder immediately
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder, "Starting video stream...", (150, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow(self.window_name, placeholder)
            cv2.waitKey(1)
            
            self.logger.info(f"Created video window: {self.window_name}")
        
        # Wait a moment for connection to stabilize
        await asyncio.sleep(1)
        
        try:
            frame_count = 0
            consecutive_failures = 0
            max_consecutive_failures = 10
            
            while True:
                try:
                    # Receive frame from track with timeout
                    frame = await asyncio.wait_for(track.recv(), timeout=10.0)  # Increased timeout
                    
                    if frame is None:
                        self.logger.warning("Received None frame")
                        break
                    
                    frame_count += 1
                    consecutive_failures = 0  # Reset failure counter
                    
                    # Log detailed frame information
                    self.logger.info(f"Received frame {frame_count}: type={type(frame)}, format={getattr(frame, 'format', 'unknown')}")
                    
                    # Handle different frame types
                    try:
                        if hasattr(frame, 'to_ndarray'):
                            # For video frames - try different formats
                            try:
                                img = frame.to_ndarray(format="bgr24")
                                self.logger.info(f"Frame {frame_count} successfully converted to BGR24: shape={img.shape}")
                                await self._process_frame(img)
                            except Exception as bgr_error:
                                self.logger.warning(f"Failed to convert frame to BGR24: {bgr_error}")
                                try:
                                    # Try RGB format
                                    img = frame.to_ndarray(format="rgb24")
                                    # Convert RGB to BGR for OpenCV
                                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                                    self.logger.info(f"Frame {frame_count} converted from RGB24 to BGR: shape={img.shape}")
                                    await self._process_frame(img)
                                except Exception as rgb_error:
                                    self.logger.error(f"Failed to convert frame from RGB24: {rgb_error}")
                                    # Show error frame
                                    if self.display_window:
                                        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                                        cv2.putText(error_frame, f"Decode Error: Frame {frame_count}", (100, 240), 
                                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                        cv2.imshow(self.window_name, error_frame)
                                        cv2.waitKey(1)
                        else:
                            self.logger.warning(f"Frame {frame_count} doesn't have to_ndarray method: {type(frame)}")
                            # Try to extract frame data manually
                            if hasattr(frame, 'planes'):
                                self.logger.info(f"Frame has planes: {len(frame.planes)}")
                                for i, plane in enumerate(frame.planes):
                                    self.logger.info(f"Plane {i}: {plane}")
                    
                    except Exception as frame_error:
                        self.logger.error(f"Error processing frame {frame_count}: {frame_error}")
                        consecutive_failures += 1
                        
                        # Show frame error
                        if self.display_window:
                            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                            cv2.putText(error_frame, f"Frame Error: {consecutive_failures}/10", (150, 240), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 100, 255), 2)
                            cv2.imshow(self.window_name, error_frame)
                            cv2.waitKey(1)
                    
                    # Log first frame received
                    if frame_count == 1:
                        self.logger.info(f"✅ First video frame received! Type: {type(frame)}")
                    
                    # Log every 30 frames
                    if frame_count % 30 == 0:
                        self.logger.info(f"Processed {frame_count} frames")
                        
                except asyncio.TimeoutError:
                    consecutive_failures += 1
                    self.logger.warning(f"Timeout waiting for frame (attempt {consecutive_failures}/{max_consecutive_failures})")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        self.logger.error("Too many consecutive frame timeout failures, stopping")
                        break
                        
                    # Show "waiting for frames" message
                    if self.display_window:
                        placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                        cv2.putText(placeholder, "Waiting for video frames...", (130, 240), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                        cv2.imshow(self.window_name, placeholder)
                        cv2.waitKey(1)
                    
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error in video track handler: {e}")
        finally:
            self.logger.info("Video track ended")
            if self.display_window:
                cv2.destroyWindow(self.window_name)
    
    async def _process_frame(self, frame: np.ndarray):
        """
        Process received video frame
        
        Args:
            frame: Video frame as numpy array
        """
        try:
            self.frame_count += 1
            
            self.logger.debug(f"Processing frame {self.frame_count}: shape={frame.shape}, dtype={frame.dtype}")
            
            # Call custom frame handler if provided
            if self.on_frame:
                self.on_frame(frame)
            
            # Display frame in window
            if self.display_window:
                self.logger.debug(f"Displaying frame {self.frame_count} in window '{self.window_name}'")
                cv2.imshow(self.window_name, frame)
                
                # Force window update and bring to front
                cv2.waitKey(1)  # Process window events
                
                # On first frame, bring window to front again 
                if self.frame_count == 1:
                    self.logger.info(f"✅ Displaying first frame in window!")
                    cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1)
                    cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 0)  # Reset topmost
            
            # Save frame to disk
            if self.save_frames:
                filename = f"{self.output_dir}/frame_{self.frame_count:06d}.jpg"
                cv2.imwrite(filename, frame)
            
            # Add small delay to prevent overwhelming the display
            await asyncio.sleep(0.001)
            
        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
        
        return True
    
    def cleanup(self):
        """Cleanup resources"""
        if self.display_window:
            cv2.destroyAllWindows()


class AudioReceiver:
    """Handles audio stream reception"""
    
    def __init__(self, save_audio: bool = False, output_file: str = "output.wav"):
        """
        Initialize audio receiver
        
        Args:
            save_audio: Whether to save audio to file
            output_file: Output audio file path
        """
        self.save_audio = save_audio
        self.output_file = output_file
        self.audio_samples = []
        
        self.logger = logging.getLogger(__name__)
    
    async def handle_track(self, track: MediaStreamTrack):
        """
        Handle incoming audio track
        
        Args:
            track: Audio track from WebRTC
        """
        self.logger.info(f"Starting to receive {track.kind} track")
        
        try:
            while True:
                frame = await track.recv()
                
                if frame is None:
                    break
                
                # Process audio frame
                await self._process_audio_frame(frame)
                
        except Exception as e:
            self.logger.error(f"Error in audio track handler: {e}")
        finally:
            self.logger.info("Audio track ended")
            
            # Save audio file if requested
            if self.save_audio and self.audio_samples:
                self._save_audio_file()
    
    async def _process_audio_frame(self, frame):
        """Process received audio frame"""
        try:
            if self.save_audio:
                # Convert frame to numpy array and store
                if hasattr(frame, 'to_ndarray'):
                    audio_data = frame.to_ndarray()
                    self.audio_samples.append(audio_data)
                    
        except Exception as e:
            self.logger.error(f"Error processing audio frame: {e}")
    
    def _save_audio_file(self):
        """Save collected audio samples to file"""
        try:
            import soundfile as sf
            
            # Concatenate all audio samples
            if self.audio_samples:
                audio_data = np.concatenate(self.audio_samples)
                
                # Save to file (assuming 48kHz sample rate)
                sf.write(self.output_file, audio_data, 48000)
                self.logger.info(f"Saved audio to {self.output_file}")
                
        except ImportError:
            self.logger.warning("soundfile not available, cannot save audio")
        except Exception as e:
            self.logger.error(f"Error saving audio file: {e}")


class DataChannelHandler:
    """Handles WebRTC data channel communication"""
    
    def __init__(self):
        """Initialize data channel handler"""
        self.channels = {}
        self.on_message: Optional[Callable[[str, str], None]] = None
        self.logger = logging.getLogger(__name__)
    
    def handle_datachannel(self, channel):
        """
        Handle incoming data channel
        
        Args:
            channel: WebRTC data channel
        """
        self.logger.info(f"Data channel '{channel.label}' opened")
        self.channels[channel.label] = channel
        
        @channel.on("message")
        def on_message(message):
            """Handle data channel message"""
            self.logger.debug(f"Received message on '{channel.label}': {message}")
            if self.on_message:
                self.on_message(channel.label, message)
        
        @channel.on("close")
        def on_close():
            """Handle data channel close"""
            self.logger.info(f"Data channel '{channel.label}' closed")
            if channel.label in self.channels:
                del self.channels[channel.label]
    
    async def send_message(self, channel_label: str, message: str):
        """
        Send message on data channel
        
        Args:
            channel_label: Label of the data channel
            message: Message to send
        """
        if channel_label in self.channels:
            channel = self.channels[channel_label]
            if channel.readyState == "open":
                channel.send(message)
                self.logger.debug(f"Sent message on '{channel_label}': {message}")
            else:
                self.logger.warning(f"Channel '{channel_label}' not open")
        else:
            self.logger.warning(f"Channel '{channel_label}' not found")