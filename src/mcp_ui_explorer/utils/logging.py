"""Logging utilities for MCP UI Explorer."""

import logging
import sys
from typing import Optional

from ..config import get_settings


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    logger_name: str = "mcp_ui_explorer"
) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string for log messages
        logger_name: Name of the logger to configure
        
    Returns:
        Configured logger instance
    """
    settings = get_settings()
    
    # Use provided values or fall back to settings
    log_level = level or settings.logging.level
    log_format = format_string or settings.logging.format
    
    # Configure the logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str = "mcp_ui_explorer") -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name) 