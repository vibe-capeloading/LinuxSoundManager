"""
Linux Sound Manager - A SteelSeries Sonar-like audio mixer for Linux
"""

__version__ = "0.1.0"
__author__ = "LinuxSoundManager Team"

# Import core components
from .core.audio_engine import AudioEngine
from .core.channels import ChannelManager, ChannelType
from .core.mixer import AudioMixer
from .core.effects import EffectsManager
from .core.spatial_audio import SpatialAudio

# Import services
from .services.easy_effects import EasyEffectsIntegration
from .services.pavucontrol import PavucontrolIntegration

# Import models
from .models.audio_device import AudioDevice
from .models.audio_source import AudioSource
from .models.preset import Preset

# Import utilities (logger is safe, config_manager is lazy-loaded)
from .utils.logger import get_logger

__all__ = [
    "AudioEngine",
    "ChannelManager",
    "ChannelType",
    "AudioMixer",
    "EffectsManager",
    "SpatialAudio",
    "EasyEffectsIntegration",
    "PavucontrolIntegration",
    "AudioDevice",
    "AudioSource",
    "Preset",
    "get_logger",
]
