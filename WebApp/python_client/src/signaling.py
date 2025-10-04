"""
Python client for Unity Render Streaming
Receives video streams from Unity Render Streaming server via WebRTC
"""

import asyncio
import json
import logging
import uuid
from typing import Optional, Callable, Any
import websockets
from websockets.exceptions import ConnectionClosed


class WebSocketSignaling:
    """WebSocket signaling client for Unity Render Streaming"""
    
    def __init__(self, server_url: str = "ws://localhost:80"):
        """
        Initialize WebSocket signaling client
        
        Args:
            server_url: WebSocket server URL (default: ws://localhost:8080)
        """
        self.server_url = server_url
        self.websocket = None
        self.is_connected = False
        self.connection_id = None
        
        # Event callbacks
        self.on_connect: Optional[Callable[[dict], None]] = None
        self.on_disconnect: Optional[Callable[[dict], None]] = None
        self.on_offer: Optional[Callable[[dict], None]] = None
        self.on_answer: Optional[Callable[[dict], None]] = None
        self.on_candidate: Optional[Callable[[dict], None]] = None
        self.on_error: Optional[Callable[[dict], None]] = None
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self) -> bool:
        """
        Start WebSocket connection to signaling server
        
        Returns:
            bool: True if connection successful
        """
        try:
            self.logger.info(f"Connecting to signaling server: {self.server_url}")
            self.websocket = await websockets.connect(self.server_url)
            self.is_connected = True
            self.logger.info("WebSocket connection established")
            
            # Start message handling task
            asyncio.create_task(self._handle_messages())
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to signaling server: {e}")
            return False
    
    async def stop(self):
        """Stop WebSocket connection"""
        if self.websocket:
            self.is_connected = False
            await self.websocket.close()
            self.logger.info("WebSocket connection closed")
    
    async def _handle_messages(self):
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    
        except ConnectionClosed:
            self.logger.info("WebSocket connection closed by server")
            self.is_connected = False
        except Exception as e:
            self.logger.error(f"Error in message handler: {e}")
            self.is_connected = False
    
    async def _process_message(self, data: dict):
        """Process incoming signaling message"""
        message_type = data.get('type')
        
        if message_type == 'connect':
            self.logger.info(f"Received connect: {data}")
            if self.on_connect:
                self.on_connect(data)
                
        elif message_type == 'disconnect':
            self.logger.info(f"Received disconnect: {data}")
            if self.on_disconnect:
                self.on_disconnect(data)
                
        elif message_type == 'offer':
            self.logger.info(f"Received offer from {data.get('from')}")
            if self.on_offer:
                # Transform message format to match expected structure
                offer_data = {
                    'connectionId': data.get('from'),
                    'sdp': data.get('data', {}).get('sdp'),
                    'polite': data.get('data', {}).get('polite', False)
                }
                if asyncio.iscoroutinefunction(self.on_offer):
                    asyncio.create_task(self.on_offer(offer_data))
                else:
                    self.on_offer(offer_data)
                
        elif message_type == 'answer':
            self.logger.info(f"Received answer from {data.get('from')}")
            if self.on_answer:
                answer_data = {
                    'connectionId': data.get('from'),
                    'sdp': data.get('data', {}).get('sdp')
                }
                if asyncio.iscoroutinefunction(self.on_answer):
                    asyncio.create_task(self.on_answer(answer_data))
                else:
                    self.on_answer(answer_data)
                
        elif message_type == 'candidate':
            self.logger.debug(f"Received ICE candidate from {data.get('from')}")
            if self.on_candidate:
                candidate_data = {
                    'connectionId': data.get('from'),
                    'candidate': data.get('data', {}).get('candidate'),
                    'sdpMLineIndex': data.get('data', {}).get('sdpMLineIndex'),
                    'sdpMid': data.get('data', {}).get('sdpMid')
                }
                if asyncio.iscoroutinefunction(self.on_candidate):
                    asyncio.create_task(self.on_candidate(candidate_data))
                else:
                    self.on_candidate(candidate_data)
                
        elif message_type == 'error':
            self.logger.error(f"Received error: {data.get('message')}")
            if self.on_error:
                self.on_error(data)
        else:
            self.logger.warning(f"Unknown message type: {message_type}")
    
    async def send_message(self, message: dict):
        """Send message to signaling server"""
        if not self.is_connected or not self.websocket:
            raise RuntimeError("WebSocket not connected")
        
        try:
            await self.websocket.send(json.dumps(message))
            self.logger.debug(f"Sent message: {message}")
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise
    
    async def create_connection(self, connection_id: Optional[str] = None):
        """
        Create a new connection
        
        Args:
            connection_id: Optional connection ID (generates UUID if None)
        """
        if not connection_id:
            connection_id = str(uuid.uuid4())
        
        self.connection_id = connection_id
        message = {
            'type': 'connect',
            'connectionId': connection_id
        }
        await self.send_message(message)
        return connection_id
    
    async def delete_connection(self, connection_id: str):
        """Delete a connection"""
        message = {
            'type': 'disconnect',
            'connectionId': connection_id
        }
        await self.send_message(message)
    
    async def send_offer(self, connection_id: str, sdp: str):
        """Send SDP offer"""
        message = {
            'type': 'offer',
            'from': connection_id,
            'data': {
                'sdp': sdp,
                'connectionId': connection_id
            }
        }
        await self.send_message(message)

    async def send_answer(self, connection_id: str, sdp: str):
        """Send SDP answer"""
        message = {
            'type': 'answer',
            'from': connection_id,
            'data': {
                'sdp': sdp,
                'connectionId': connection_id
            }
        }
        await self.send_message(message)
    
    async def send_candidate(self, connection_id: str, candidate: str, 
                           sdp_mid: str, sdp_mline_index: int):
        """Send ICE candidate"""
        message = {
            'type': 'candidate',
            'from': connection_id,
            'data': {
                'candidate': candidate,
                'sdpMLineIndex': sdp_mline_index,
                'sdpMid': sdp_mid,
                'connectionId': connection_id
            }
        }
        await self.send_message(message)