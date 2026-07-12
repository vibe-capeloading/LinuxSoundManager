"""
Services for Linux Sound Manager
"""

from .easy_effects import EasyEffectsIntegration
from .pavucontrol import PavucontrolIntegration

__all__ = [
    "EasyEffectsIntegration",
    "PavucontrolIntegration",
]
