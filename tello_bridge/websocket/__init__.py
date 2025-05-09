#!/usr/bin/env python3
import asyncio
import websockets
from typing import Set, Optional, Callable, Any

from ..utils.logger import logger

# Set to store active WebSocket connections
connected_websockets: Set = set()

async def handle_websocket(websocket, tello_command_handler=None):
    """
    Handle WebSocket connections and messages.
    
    Args:
        websocket: WebSocket connection
        tello_command_handler: Function to send commands to Tello
    """
    logger.info(f"New WebSocket connection: {websocket.remote_address}")
    
    # Register the new WebSocket
    connected_websockets.add(websocket)
    
    try:
        async for message in websocket:
            logger.debug(f"WebSocket message received: {message}")
            
            # Send message to Tello if handler is ready
            if tello_command_handler:
                tello_command_handler(message)
            else:
                logger.warning("Tello command handler not ready, message discarded")
            
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"WebSocket connection closed: {websocket.remote_address}")
    finally:
        # Unregister the WebSocket when connection is closed
        connected_websockets.remove(websocket)

async def broadcast_to_websockets(message: str):
    """
    Send message to all connected WebSocket clients.
    
    Args:
        message: The message to broadcast
    """
    if connected_websockets:
        # Create a list of tasks to send the message to all WebSockets
        tasks = [ws.send(message) for ws in connected_websockets]
        # Execute all send tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

async def start_websocket_server(host: str, port: int, tello_command_handler: Optional[Callable[[str], Any]] = None):
    """
    Start the WebSocket server
    
    Args:
        host: Host address to bind to
        port: Port to listen on
        tello_command_handler: Function to handle commands for the Tello drone
    
    Returns:
        The WebSocket server instance
    """
    # Create a custom handler that includes the tello_command_handler
    async def handler(websocket):
        await handle_websocket(websocket, tello_command_handler)
    
    # Start the WebSocket server with heartbeat enabled
    server = await websockets.serve(
        handler, 
        host, 
        port,
        ping_interval=30,  # Send ping every 30 seconds
        ping_timeout=10    # Wait 10 seconds for pong response
    )
    
    logger.info(f"WebSocket server started on {host}:{port}")
    return server