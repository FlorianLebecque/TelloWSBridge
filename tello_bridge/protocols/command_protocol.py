#!/usr/bin/env python3
import asyncio
import json
from typing import List, Optional

from ..utils.logger import logger
from .base_protocol import BaseProtocol

# This needs to be imported in the main module and provided to TelloProtocol
broadcast_to_websockets = None

class TelloProtocol(BaseProtocol):
    """
    Protocol for handling command communication with Tello drone
    """
    def __init__(self, tello_addr, broadcast_function=None):
        super().__init__()
        self.tello_addr = tello_addr
        self.command_queue = []
        self.reconnect_task = None
        # Reference to the broadcast function
        global broadcast_to_websockets
        broadcast_to_websockets = broadcast_function

    def connection_made(self, transport):
        """Called when connection is established"""
        super().connection_made(transport)
        logger.info(f"UDP socket ready, sending to Tello at {self.tello_addr}")
        # Process any queued commands
        self._process_command_queue()
        
        # Send initial "command" to establish connection with Tello
        self.send_to_tello("command")

    def datagram_received(self, data, addr):
        """Handle incoming data from the Tello drone"""
        try:
            message = data.decode('utf-8')
            logger.debug(f"UDP message received from {addr}: {message}")
            
            # Update last response time for health monitoring
            self.last_response_time = asyncio.get_event_loop().time()
            
            # Encapsulate response in JSON with origin=command
            json_response = json.dumps({
                "origin": "command",
                "data": message
            })
            
            # Schedule broadcasting to all WebSocket clients if a broadcast function is available
            if broadcast_to_websockets:
                asyncio.create_task(broadcast_to_websockets(json_response))
            
        except UnicodeDecodeError:
            # This is likely binary data (possibly video), don't try to decode it as UTF-8
            logger.debug(f"Binary data received from {addr}, size: {len(data)} bytes")
            self.last_response_time = asyncio.get_event_loop().time()

    def send_to_tello(self, message: str):
        """Send a command to the Tello drone"""
        if not self.connected:
            logger.warning(f"Not connected to Tello, queuing message: {message}")
            self.command_queue.append(message)
            return
            
        if not self.transport:
            logger.warning("Cannot send message: Transport not ready")
            return
        
        if isinstance(message, str):
            message = message.encode('utf-8')
        
        logger.debug(f"Sending to Tello: {message}")
        self.transport.sendto(message, self.tello_addr)

    def _process_command_queue(self):
        """Process any commands that were queued while disconnected."""
        if not self.command_queue:
            return
            
        logger.info(f"Processing {len(self.command_queue)} queued commands")
        for cmd in self.command_queue:
            self.send_to_tello(cmd)
        self.command_queue = []

    def connection_lost(self, exc):
        """Handle connection loss"""
        super().connection_lost(exc)
        # Start reconnection process
        self._schedule_reconnect()
        
    def error_received(self, exc):
        """Handle transport errors"""
        super().error_received(exc)
        # Start reconnection process
        self._schedule_reconnect()
        
    def _schedule_reconnect(self):
        """Schedule a reconnection attempt."""
        if self.reconnect_task and not self.reconnect_task.done():
            return  # Reconnection already in progress
            
        self.reconnect_task = asyncio.create_task(self._reconnect())
        
    async def _reconnect(self):
        """Attempt to reconnect to the Tello."""
        logger.info("Starting reconnection attempts to Tello")
        retry_delay = 5  # Start with 5 seconds delay
        max_retries = 10  # Maximum number of retry attempts
        retries = 0
        
        while not self.connected and retries < max_retries:
            try:
                logger.info(f"Reconnection attempt {retries + 1}/{max_retries}")
                # Signal to the main loop that reconnection is needed
                # This is used in the main module
                global need_reconnect
                need_reconnect = True
                
                await asyncio.sleep(retry_delay)
                retries += 1
                # Exponential backoff with a cap
                retry_delay = min(30, retry_delay * 1.5)
            except Exception as e:
                logger.error(f"Error during reconnection: {e}")
                
        if not self.connected:
            logger.error("Failed to reconnect to Tello after maximum retries")

# Module-level variable for tracking reconnection needs
need_reconnect = False