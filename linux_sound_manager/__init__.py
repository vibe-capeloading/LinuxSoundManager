"""
Linux Sound Manager - A SteelSeries Sonar-like audio mixer for Linux
"""

__version__ = "0.1.0"
__author__ = "LinuxSoundManager Team"

from .core.audio_engine import AudioEngine
from .core.channels import ChannelManager
from .core.mixer import AudioMixer
from .core.effects import EffectsManager
from .core.spatial_audio import SpatialAudio
from .services.easy_effects import EasyEffectsIntegration
from .services.pavucontrol import PavucontrolIntegration
from .models.audio_device import AudioDevice
from .models.audio_source import AudioSource
from .models.preset import Preset
from .utils.config_manager import ConfigManager
from .utils.logger import get_logger

__all__ = [
    "AudioEngine",
    "ChannelManager", 
    "AudioMixer",
    "EffectsManager",
    "SpatialAudio",
    "EasyEffectsIntegration",
    "PavucontrolIntegration",
    "AudioDevice",
    "AudioSource",
    "Preset",
    "ConfigManager",
    "get_logger",
]
