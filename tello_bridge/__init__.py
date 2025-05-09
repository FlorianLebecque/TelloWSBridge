#!/usr/bin/env python3
import asyncio
from typing import Optional, Tuple

from .utils.logger import logger
from .protocols.command_protocol import TelloProtocol, need_reconnect
from .protocols.state_protocol import TelloStateProtocol
from .websocket import broadcast_to_websockets, start_websocket_server

class TelloBridge:
    """
    Main bridge class that coordinates all components for the Tello WebSocket Bridge
    """
    def __init__(self, socket_host, socket_port, local_port, websocket_host, websocket_port):
        self.socket_host = socket_host
        self.socket_port = socket_port
        self.local_port = local_port
        self.websocket_host = websocket_host
        self.websocket_port = websocket_port
        
        # Components
        self.tello_protocol = None
        self.tello_state_protocol = None
        
        # Transport objects
        self.cmd_transport = None
        self.state_transport = None
        
        # Server
        self.websocket_server = None
        
        # Tasks
        self.health_task = None
        
    async def start(self):
        """Start the bridge and all its components"""
        logger.info("Starting Tello WebSocket Bridge")
        logger.info(f"Tello address: {self.socket_host}:{self.socket_port}")
        logger.info(f"Local UDP port: {self.local_port}")
        logger.info(f"WebSocket: {self.websocket_host}:{self.websocket_port}")
        
        # Start the health monitor
        self.health_task = asyncio.create_task(self._health_monitor())
        
        # Setup UDP sockets
        await self._setup_sockets()
        
        # Start the WebSocket server
        self.websocket_server = await start_websocket_server(
            self.websocket_host,
            self.websocket_port,
            self.tello_protocol.send_to_tello if self.tello_protocol else None
        )
        
        # Main loop to handle reconnection requests
        await self._main_loop()
        
    async def _setup_sockets(self):
        """Setup all UDP sockets for communication with Tello"""
        # Create UDP socket for commands
        self.cmd_transport, self.tello_protocol = await self._create_udp_socket()
        
        # Create UDP socket for state information
        self.state_transport, self.tello_state_protocol = await self._create_state_socket()
        
    async def _create_udp_socket(self) -> Tuple:
        """Create a UDP socket for sending commands to Tello"""
        loop = asyncio.get_running_loop()
        tello_addr = (self.socket_host, self.socket_port)
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: TelloProtocol(tello_addr, broadcast_to_websockets),
            local_addr=('0.0.0.0', self.local_port)  # Bind to specified local port
        )
        return transport, protocol
    
    async def _create_state_socket(self) -> Tuple:
        """Create a UDP socket for receiving state information from Tello"""
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: TelloStateProtocol(broadcast_to_websockets),
            local_addr=('0.0.0.0', 8890)
        )
        return transport, protocol
    
    async def _health_monitor(self, check_interval=10):
        """Monitor the health of the Tello connection"""
        global need_reconnect
        
        while True:
            await asyncio.sleep(check_interval)
            
            if self.tello_protocol and self.tello_protocol.connected:
                # Check if we've received any response in the last 15 seconds
                current_time = asyncio.get_event_loop().time()
                time_since_last_response = current_time - self.tello_protocol.last_response_time
                
                if self.tello_protocol.last_response_time > 0 and time_since_last_response > 15:
                    logger.warning(f"No response from Tello in {time_since_last_response:.1f} seconds, checking connection...")
                    # Send a status request to check if the drone is still responsive
                    self.tello_protocol.send_to_tello("command")
                    
            # Check if reconnection is needed
            if need_reconnect:
                logger.info("Reconnection request detected")
                need_reconnect = False  # Reset the flag
    
    async def _main_loop(self):
        """Main loop that handles reconnection requests"""
        global need_reconnect
        
        try:
            while True:
                if need_reconnect:
                    logger.info("Recreating UDP socket connection")
                    if self.cmd_transport:
                        self.cmd_transport.close()
                    self.cmd_transport, self.tello_protocol = await self._create_udp_socket()
                    need_reconnect = False
                    
                    # After reconnecting, send command to initialize
                    await asyncio.sleep(2)  # Wait for command mode to initialize
                    self.tello_protocol.send_to_tello("command")
                    
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Main loop cancelled, shutting down")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            raise
    
    async def stop(self):
        """Stop the bridge and cleanup resources"""
        logger.info("Stopping Tello Bridge...")
        
        # Cancel the health monitor task
        if self.health_task:
            self.health_task.cancel()
            
        # Close the WebSocket server
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
            
        # Close all transports
        if self.cmd_transport:
            self.cmd_transport.close()
        if self.state_transport:
            self.state_transport.close()
            
        logger.info("Bridge stopped")