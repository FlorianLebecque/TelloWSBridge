#!/usr/bin/env python3
import asyncio
import json
import time
from typing import Dict, Any

from ..utils.logger import logger
from .base_protocol import BaseProtocol

# This needs to be imported in the main module and provided to TelloStateProtocol
broadcast_to_websockets = None

class TelloStateProtocol(BaseProtocol):
    """
    Protocol for handling state information from Tello drone
    """
    def __init__(self, broadcast_function=None):
        super().__init__()
        
        # Reference to the broadcast function
        global broadcast_to_websockets
        broadcast_to_websockets = broadcast_function
        
        # Define field descriptions for state parameters
        self.state_descriptions = {
            "mid": "Mission Pad ID (-1 if not detected)",
            "x": "X coordinate on Mission Pad (0 if not detected)",
            "y": "Y coordinate on Mission Pad (0 if not detected)",
            "z": "Z coordinate on Mission Pad (0 if not detected)",
            "pitch": "Attitude pitch in degrees",
            "roll": "Attitude roll in degrees",
            "yaw": "Attitude yaw in degrees",
            "vgx": "Speed on X axis",
            "vgy": "Speed on Y axis",
            "vgz": "Speed on Z axis",
            "templ": "Lowest temperature in °C",
            "temph": "Highest temperature in °C",
            "tof": "Time of flight distance in cm",
            "h": "Height in cm",
            "bat": "Battery percentage",
            "baro": "Barometer measurement in cm",
            "time": "Motor time in seconds",
            "agx": "Acceleration on X axis",
            "agy": "Acceleration on Y axis",
            "agz": "Acceleration on Z axis"
        }
        
        # Define expected data types for parsing
        self.state_types = {
            "mid": int,
            "x": int,
            "y": int,
            "z": int,
            "pitch": float,
            "roll": float,
            "yaw": float,
            "vgx": float,
            "vgy": float,
            "vgz": float,
            "templ": float,
            "temph": float,
            "tof": float,
            "h": float,
            "bat": float,
            "baro": float,
            "time": float,
            "agx": float,
            "agy": float,
            "agz": float
        }

    def connection_made(self, transport):
        super().connection_made(transport)
        logger.info(f"UDP state server ready on port 8890")
        
    def parse_state_data(self, state_string: str) -> Dict[str, Any]:
        """
        Parse the state string from Tello into a structured dictionary
        
        Args:
            state_string (str): Raw state string from Tello
            
        Returns:
            Dict[str, Any]: Parsed state data
        """
        # Remove any trailing whitespace or newlines
        state_string = state_string.strip()
        
        # Split the string into key-value pairs
        pairs = state_string.split(';')
        
        # Initialize result dictionary
        state_data = {}
        
        # Process each key-value pair
        for pair in pairs:
            if not pair:  # Skip empty pairs
                continue
                
            # Split by colon to get key and value
            if ':' in pair:
                key, value = pair.split(':', 1)
                
                # Convert value to appropriate type if possible
                try:
                    if key in self.state_types:
                        value = self.state_types[key](value)
                except ValueError:
                    # If conversion fails, keep as string
                    pass
                    
                # Add to result dictionary
                state_data[key] = value
        
        return state_data
        
    def datagram_received(self, data, addr):
        """Handle incoming state data from Tello"""
        try:
            message = data.decode('utf-8')
            logger.debug(f"Tello state received from {addr}: {message}")
            
            # Update last response time for health monitoring
            self.last_response_time = asyncio.get_event_loop().time()
            
            # Parse the state data
            state_data = self.parse_state_data(message)
            
            # Create enhanced state response with parsed data, raw data, and descriptions
            enhanced_state = {
                "origin": "state",
                "raw": message,
                "parsed": state_data,
                "timestamp": time.time(),
                "fields": {}
            }
            
            # Add field descriptions and values in a structured way
            for key, value in state_data.items():
                enhanced_state["fields"][key] = {
                    "value": value,
                    "description": self.state_descriptions.get(key, "Unknown parameter")
                }
            
            # Encapsulate state data in JSON
            json_response = json.dumps(enhanced_state)
            
            # Broadcast state to all WebSocket clients if broadcast function is available
            if broadcast_to_websockets:
                asyncio.create_task(broadcast_to_websockets(json_response))
            
        except UnicodeDecodeError:
            # Handle binary data gracefully
            logger.debug(f"Binary state data received from {addr}, size: {len(data)} bytes")
            self.last_response_time = asyncio.get_event_loop().time()