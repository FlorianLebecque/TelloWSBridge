#!/usr/bin/env python3
import logging
import sys

# Configure logger
def setup_logger(debug=True):
    """
    Setup and configure the logger for the application
    
    Args:
        debug (bool): Whether to set logging level to DEBUG
    
    Returns:
        logging.Logger: Configured logger instance
    """
    
    # Configure logging format
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    # Create and return logger
    logger = logging.getLogger("TelloBridge")
    return logger

# Create a default logger instance that can be imported directly
logger = setup_logger()