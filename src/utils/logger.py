"""Logging configuration for the application."""
import logging
import sys
from pathlib import Path
from colorlog import ColoredFormatter


def setup_logger(name: str = "infra_bot", level: str = "INFO") -> logging.Logger:
    """Set up colored logging with proper formatting."""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s%(reset)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    file_handler = logging.FileHandler(log_dir / "infra_bot.log")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger
