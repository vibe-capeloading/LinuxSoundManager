"""
Utilities for Linux Sound Manager
"""

from .config_manager import ConfigManager
from .logger import get_logger, setup_logging
from .helpers import (
    clamp,
    db_to_linear,
    linear_to_db,
    frequency_to_midi,
    midi_to_frequency,
    resample_audio,
    normalize_audio,
)

__all__ = [
    "ConfigManager",
    "get_logger",
    "setup_logging",
    "clamp",
    "db_to_linear",
    "linear_to_db",
    "frequency_to_midi",
    "midi_to_frequency",
    "resample_audio",
    "normalize_audio",
]
