"""Logging configuration for server"""

import logging
import sys

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)

logger = logging.getLogger("claw-service-hub")

def configure_logging(level=logging.INFO):
    """Configure logging level"""
    logger.setLevel(level)