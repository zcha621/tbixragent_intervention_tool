"""
WebRTC peer connection handling for Unity Render Streaming Python client
"""

import asyncio
import logging
from typing import Optional, Callable
import aiortc
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.contrib.media import MediaPlayer, MediaRelay


class WebRTCPeer:
    """WebRTC peer connection for receiving video streams"""
    
    def __init__(self, signaling, rtc_config=None, connection_id: str = None, is_polite: bool = False):
        """
        Initialize WebRTC peer connection
        
        Args:
            signaling: Signaling client instance
            rtc_config: Optional RTCConfiguration object
            connection_id: Connection identifier (optional for enhanced client)
            is_polite: Whether this peer is "polite" in the negotiation
        """
        self.signaling = signaling
        self.connection_id = connection_id
        self.is_polite = is_polite
        
        # Use provided config or create default
        if rtc_config:
            self.pc = RTCPeerConnection(configuration=rtc_config)
        else:
            # WebRTC configuration with STUN servers
            self.pc = RTCPeerConnection(configuration=aiortc.RTCConfiguration(
                iceServers=[
                    aiortc.RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
                    aiortc.RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
                ]
            ))
        
        # State tracking
        self.is_making_offer = False
        self.ignore_offer = False
        
        # Event callbacks
        self.on_track: Optional[Callable[[aiortc.MediaStreamTrack], None]] = None
        self.on_datachannel: Optional[Callable[[aiortc.RTCDataChannel], None]] = None
        self.on_connection_state_change: Optional[Callable[[str], None]] = None
        
        self.logger = logging.getLogger(__name__)
        
        # Set up event handlers
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup WebRTC peer connection event handlers"""
        
        @self.pc.on("icecandidate")
        def on_icecandidate(candidate):
            """Handle ICE candidate events"""
            if candidate:
                asyncio.create_task(self._send_ice_candidate(candidate))
        
        @self.pc.on("track")
        def on_track(track):
            """Handle incoming media track"""
            self.logger.info(f"Received {track.kind} track")
            if self.on_track:
                self.on_track(track)
        
        @self.pc.on("datachannel")
        def on_datachannel(channel):
            """Handle incoming data channel"""
            self.logger.info(f"Received data channel: {channel.label}")
            if self.on_datachannel:
                self.on_datachannel(channel)
        
        @self.pc.on("connectionstatechange")
        def on_connectionstatechange():
            """Handle connection state changes"""
            state = self.pc.connectionState
            self.logger.info(f"Connection state changed to: {state}")
            if self.on_connection_state_change:
                self.on_connection_state_change(state)
    
    async def _send_ice_candidate(self, candidate):
        """Send ICE candidate to remote peer"""
        try:
            await self.signaling.send_candidate(
                self.connection_id,
                candidate.candidate,
                candidate.sdpMid,
                candidate.sdpMLineIndex
            )
        except Exception as e:
            self.logger.error(f"Failed to send ICE candidate: {e}")
    
    async def handle_offer(self, sdp: str):
        """
        Handle incoming SDP offer
        
        Args:
            sdp: SDP offer string
        """
        try:
            offer_collision = (self.pc.signalingState != "stable" or self.is_making_offer)
            self.ignore_offer = not self.is_polite and offer_collision
            
            if self.ignore_offer:
                self.logger.info("Ignoring offer due to collision")
                return
            
            # Set remote description
            offer = RTCSessionDescription(sdp=sdp, type="offer")
            await self.pc.setRemoteDescription(offer)
            
            # Create and send answer
            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)
            
            await self.signaling.send_answer(self.connection_id, answer.sdp)
            self.logger.info("Sent SDP answer")
            
        except Exception as e:
            self.logger.error(f"Error handling offer: {e}")
            raise
    
    async def handle_answer(self, sdp: str):
        """
        Handle incoming SDP answer
        
        Args:
            sdp: SDP answer string
        """
        try:
            answer = RTCSessionDescription(sdp=sdp, type="answer")
            await self.pc.setRemoteDescription(answer)
            self.logger.info("Set remote description from answer")
            
        except Exception as e:
            self.logger.error(f"Error handling answer: {e}")
            raise
    
    async def handle_ice_candidate(self, candidate_data: dict):
        """
        Handle incoming ICE candidate
        
        Args:
            candidate_data: ICE candidate data dict
        """
        try:
            self.logger.debug(f"ICE candidate data: {candidate_data}")
            if candidate_data.get('candidate'):
                candidate_str = candidate_data['candidate']
                
                # Parse the candidate string if it's in the format "candidate:..."
                if isinstance(candidate_str, str):
                    # Unity sends ICE candidates in the standard SDP format
                    # We need to create the RTCIceCandidate from the string
                    
                    # Handle sdpMid - convert to string if it's an int or None
                    sdp_mid = candidate_data.get('sdpMid')
                    if sdp_mid is not None:
                        sdp_mid = str(sdp_mid)
                    
                    # Handle sdpMLineIndex - ensure it's an int
                    sdp_mline_index = candidate_data.get('sdpMLineIndex')
                    if isinstance(sdp_mline_index, str):
                        sdp_mline_index = int(sdp_mline_index)
                    
                    # Parse the candidate string to extract fields
                    # Unity sends candidates in the format:
                    # "candidate:foundation component protocol priority ip port typ type ..."
                    
                    # Remove "candidate:" prefix if present
                    if candidate_str.startswith('candidate:'):
                        candidate_str = candidate_str[10:]
                    
                    # Split into components
                    parts = candidate_str.split()
                    if len(parts) >= 6:
                        foundation = parts[0]
                        component = int(parts[1])
                        protocol = parts[2]
                        priority = int(parts[3])
                        ip = parts[4]
                        port = int(parts[5])
                        
                        # Find the type (after "typ")
                        typ = "host"  # default
                        if "typ" in parts:
                            typ_index = parts.index("typ")
                            if typ_index + 1 < len(parts):
                                typ = parts[typ_index + 1]
                        
                        candidate = RTCIceCandidate(
                            foundation=foundation,
                            component=component,
                            protocol=protocol,
                            priority=priority,
                            ip=ip,
                            port=port,
                            type=typ,
                            sdpMid=sdp_mid,
                            sdpMLineIndex=sdp_mline_index
                        )
                    else:
                        self.logger.error(f"Invalid candidate format: {candidate_str}")
                        return
                else:
                    # If it's already parsed, use the individual fields
                    candidate = RTCIceCandidate(
                        foundation=candidate_data.get('foundation'),
                        component=candidate_data.get('component', 1),
                        protocol=candidate_data.get('protocol', 'udp'),
                        priority=candidate_data.get('priority', 0),
                        ip=candidate_data.get('ip'),
                        port=candidate_data.get('port'),
                        type=candidate_data.get('type', 'host'),
                        sdpMid=candidate_data.get('sdpMid'),
                        sdpMLineIndex=candidate_data.get('sdpMLineIndex')
                    )
                
                await self.pc.addIceCandidate(candidate)
                self.logger.debug("Added ICE candidate")
            
        except Exception as e:
            self.logger.error(f"Error handling ICE candidate: {e}")
            self.logger.error(f"Candidate data was: {candidate_data}")
    
    async def create_offer(self):
        """Create and send SDP offer"""
        try:
            self.is_making_offer = True
            offer = await self.pc.createOffer()
            await self.pc.setLocalDescription(offer)
            
            await self.signaling.send_offer(self.connection_id, offer.sdp)
            self.logger.info("Sent SDP offer")
            
        except Exception as e:
            self.logger.error(f"Error creating offer: {e}")
            raise
        finally:
            self.is_making_offer = False
    
    async def close(self):
        """Close peer connection"""
        if self.pc:
            await self.pc.close()
            self.logger.info("Peer connection closed")
    
    def get_connection_state(self) -> str:
        """Get current connection state"""
        return self.pc.connectionState if self.pc else "closed"
    
    def get_stats(self):
        """Get connection statistics"""
        if self.pc:
            return self.pc.getStats()
        return None
    
    def create_data_channel(self, label: str):
        """
        Create a data channel
        
        Args:
            label: Label for the data channel
            
        Returns:
            RTCDataChannel: Created data channel
        """
        if self.pc:
            channel = self.pc.createDataChannel(label)
            self.logger.info(f"Created data channel: {label}")
            return channel
        else:
            self.logger.error("Cannot create data channel: no peer connection")
            return None