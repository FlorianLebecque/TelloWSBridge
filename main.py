#!/usr/bin/env python3
import asyncio
import argparse
import sys

from tello_bridge import TelloBridge
from tello_bridge.utils.logger import setup_logger, logger

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Tello WebSocket Bridge')
    parser.add_argument('--socket-host', default='192.168.10.1', help='Tello IP address')
    parser.add_argument('--socket-port', type=int, default=8889, help='Tello UDP port')
    parser.add_argument('--local-port', type=int, default=9000, help='Local UDP port to receive drone messages')
    parser.add_argument('--websocket-host', default='0.0.0.0', help='WebSocket host')
    parser.add_argument('--websocket-port', type=int, default=8765, help='WebSocket port')
    parser.add_argument('--video-port', type=int, default=8555, help='Video HTTP server port')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    return parser.parse_args()

async def main():
    """Main entry point for the Tello WebSocket Bridge"""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Setup logger with debug mode if requested
    setup_logger(args.debug)

    logger.info("Debug mode is enabled" if args.debug else "Debug mode is disabled")
    
    # Create bridge instance
    bridge = TelloBridge(
        socket_host=args.socket_host,
        socket_port=args.socket_port,
        local_port=args.local_port,
        websocket_host=args.websocket_host,
        websocket_port=args.websocket_port,
        # video_http_port=args.video_port
    )
    
    try:
        # Start the bridge and wait for it to complete
        await bridge.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in main function: {e}")
    finally:
        # Make sure we clean up properly
        await bridge.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bridge stopped by user")
        sys.exit(0)