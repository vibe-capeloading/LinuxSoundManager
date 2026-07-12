"""
Logging utilities for Linux Sound Manager
"""

import logging
import sys
from typing import Optional
from pathlib import Path

# Default log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Default log level
DEFAULT_LOG_LEVEL = logging.INFO

# Log file path
LOG_FILE_PATH = Path.home() / ".linux_sound_manager" / "linux_sound_manager.log"


class ColorFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        message = super().format(record)
        
        # Add color if console supports it
        if hasattr(self, '_use_colors') and self._use_colors:
            color = self.COLORS.get(levelname, self.RESET)
            return f"{color}{message}{self.RESET}"
        
        return message


# Global logger instance
_logger: Optional[logging.Logger] = None


def setup_logging(
    level: int = DEFAULT_LOG_LEVEL,
    log_file: Optional[str] = None,
    console: bool = True,
    use_colors: bool = True
) -> logging.Logger:
    """
    Set up logging for the application.
    
    Args:
        level: Logging level (logging.DEBUG, logging.INFO, etc.)
        log_file: Path to log file (None to disable file logging)
        console: Whether to log to console
        use_colors: Whether to use colored output for console
    
    Returns:
        Configured logger
    """
    global _logger
    
    # Create logger
    logger = logging.getLogger("linux_sound_manager")
    logger.setLevel(level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        formatter = ColorFormatter(LOG_FORMAT, LOG_DATE_FORMAT)
        formatter._use_colors = use_colors
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        try:
            # Ensure directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
            
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Failed to set up file logging: {e}")
    
    _logger = logger
    return logger


def get_logger(name: str = "") -> logging.Logger:
    """
    Get a logger for a module.
    
    Args:
        name: Module name (usually __name__)
    
    Returns:
        Logger instance
    """
    global _logger
    
    if _logger is None:
        setup_logging()
    
    if name:
        return logging.getLogger(f"linux_sound_manager.{name}")
    return _logger or logging.getLogger("linux_sound_manager")


# Initialize default logging
setup_logging()
