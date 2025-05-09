#!/usr/bin/env python3
import asyncio
from typing import Optional, Tuple
from ..utils.logger import logger

class BaseProtocol(asyncio.DatagramProtocol):
    """
    Base protocol class for UDP communication with the drone
    """
    def __init__(self):
        self.transport = None
        self.connected = False
        self.last_response_time = 0
        
    def connection_made(self, transport):
        """Called when a connection is made"""
        self.transport = transport
        self.connected = True
        
    def connection_lost(self, exc):
        """Called when the connection is lost or closed"""
        logger.info("UDP socket closed")
        self.connected = False
        
    def error_received(self, exc):
        """Called when an error is received"""
        logger.error(f"UDP socket error: {exc}")
        self.connected = False