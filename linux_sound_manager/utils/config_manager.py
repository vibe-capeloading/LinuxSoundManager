"""
Configuration Manager for Linux Sound Manager

Manages application configuration, including:
- Audio settings
- Channel configurations
- Effect presets
- User preferences
"""

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

from ..models.audio_device import AudioDevice
from ..models.audio_source import AudioSource
from ..models.preset import Preset, EQBand, EffectPreset
from ..core.channels import ChannelType
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """
    Manages application configuration.
    
    Configuration is stored in JSON format and includes:
    - Audio engine settings
    - Channel configurations
    - Effect settings
    - Presets
    - User preferences
    """
    
    # Configuration file path
    CONFIG_DIR = Path.home() / ".linux_sound_manager"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    PRESETS_FILE = CONFIG_DIR / "presets.json"
    
    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._presets: Dict[str, Preset] = {}
        self._loaded = False
        
    async def initialize(self) -> bool:
        """Initialize configuration manager and load configuration"""
        try:
            # Ensure config directory exists
            self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
            # Load configuration
            await self.load_config()
            
            # Load presets
            await self.load_presets()
            
            self._loaded = True
            logger.info("Configuration manager initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize configuration manager: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown configuration manager"""
        # Save configuration before shutdown
        if self._loaded:
            await self.save_config()
            await self.save_presets()
        
        self._loaded = False
        logger.info("Configuration manager shutdown")
    
    async def load_config(self) -> bool:
        """Load configuration from file"""
        try:
            if not self.CONFIG_FILE.exists():
                # Create default configuration
                self._create_default_config()
                return True
            
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            
            logger.info(f"Loaded configuration from {self.CONFIG_FILE}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Create default configuration on error
            self._create_default_config()
            return False
    
    async def save_config(self) -> bool:
        """Save configuration to file"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved configuration to {self.CONFIG_FILE}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    async def load_presets(self) -> bool:
        """Load presets from file"""
        try:
            if not self.PRESETS_FILE.exists():
                # No presets file, start with empty
                self._presets = {}
                return True
            
            with open(self.PRESETS_FILE, 'r', encoding='utf-8') as f:
                presets_data = json.load(f)
            
            # Convert data to Preset objects
            for preset_id, preset_data in presets_data.items():
                preset = Preset.from_dict(preset_data)
                self._presets[preset_id] = preset
            
            logger.info(f"Loaded {len(self._presets)} presets from {self.PRESETS_FILE}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load presets: {e}")
            self._presets = {}
            return False
    
    async def save_presets(self) -> bool:
        """Save presets to file"""
        try:
            presets_data = {
                preset_id: preset.to_dict()
                for preset_id, preset in self._presets.items()
            }
            
            with open(self.PRESETS_FILE, 'w', encoding='utf-8') as f:
                json.dump(presets_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self._presets)} presets to {self.PRESETS_FILE}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save presets: {e}")
            return False
    
    def _create_default_config(self) -> None:
        """Create default configuration"""
        self._config = {
            "version": "1.0",
            "audio_engine": {
                "sample_rate": 48000,
                "buffer_size": 1024,
                "latency": 0.01,
                "enable_spatial": False,
                "enable_effects": True,
                "enable_eq": True,
            },
            "channels": {
                "game": {
                    "volume": 1.0,
                    "muted": False,
                    "eq_enabled": True,
                    "effects_enabled": True,
                },
                "chat": {
                    "volume": 1.0,
                    "muted": False,
                    "eq_enabled": True,
                    "effects_enabled": True,
                },
                "media": {
                    "volume": 1.0,
                    "muted": False,
                    "eq_enabled": True,
                    "effects_enabled": True,
                },
                "aux": {
                    "volume": 1.0,
                    "muted": False,
                    "eq_enabled": True,
                    "effects_enabled": True,
                },
                "microphone": {
                    "volume": 1.0,
                    "muted": False,
                    "eq_enabled": True,
                    "effects_enabled": True,
                    "noise_gate_enabled": True,
                    "compressor_enabled": True,
                },
                "master": {
                    "volume": 1.0,
                    "muted": False,
                },
            },
            "mixer": {
                "mode": "STEREO",
                "master_volume": 1.0,
                "master_muted": False,
            },
            "spatial_audio": {
                "enabled": False,
                "mode": "HEADPHONES",
                "hrtf_type": "DEFAULT",
                "distance": 1.0,
                "elevation": 0.0,
                "azimuth": 0.0,
                "quality": "high",
                "room_size": 5.0,
                "reverberation": 0.3,
            },
            "ui": {
                "theme": "dark",
                "language": "en",
                "show_advanced": False,
            },
        }
    
    # Configuration getters and setters
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value"""
        keys = key.split('.')
        current = self._config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    # Engine settings
    def get_sample_rate(self) -> int:
        return self.get_config("audio_engine.sample_rate", 48000)
    
    def set_sample_rate(self, sample_rate: int) -> None:
        self.set_config("audio_engine.sample_rate", sample_rate)
    
    def get_buffer_size(self) -> int:
        return self.get_config("audio_engine.buffer_size", 1024)
    
    def set_buffer_size(self, buffer_size: int) -> None:
        self.set_config("audio_engine.buffer_size", buffer_size)
    
    def is_spatial_enabled(self) -> bool:
        return self.get_config("audio_engine.enable_spatial", False)
    
    def set_spatial_enabled(self, enabled: bool) -> None:
        self.set_config("audio_engine.enable_spatial", enabled)
    
    def are_effects_enabled(self) -> bool:
        return self.get_config("audio_engine.enable_effects", True)
    
    def set_effects_enabled(self, enabled: bool) -> None:
        self.set_config("audio_engine.enable_effects", enabled)
    
    # Channel settings
    def get_channel_volume(self, channel_type: ChannelType) -> float:
        channel_name = channel_type.name.lower()
        return self.get_config(f"channels.{channel_name}.volume", 1.0)
    
    def set_channel_volume(self, channel_type: ChannelType, volume: float) -> None:
        channel_name = channel_type.name.lower()
        self.set_config(f"channels.{channel_name}.volume", volume)
    
    def is_channel_muted(self, channel_type: ChannelType) -> bool:
        channel_name = channel_type.name.lower()
        return self.get_config(f"channels.{channel_name}.muted", False)
    
    def set_channel_muted(self, channel_type: ChannelType, muted: bool) -> None:
        channel_name = channel_type.name.lower()
        self.set_config(f"channels.{channel_name}.muted", muted)
    
    def is_channel_eq_enabled(self, channel_type: ChannelType) -> bool:
        channel_name = channel_type.name.lower()
        return self.get_config(f"channels.{channel_name}.eq_enabled", True)
    
    def set_channel_eq_enabled(self, channel_type: ChannelType, enabled: bool) -> None:
        channel_name = channel_type.name.lower()
        self.set_config(f"channels.{channel_name}.eq_enabled", enabled)
    
    # Preset management
    async def add_preset(self, preset: Preset) -> bool:
        """Add a preset to the configuration"""
        try:
            self._presets[preset.id] = preset
            await self.save_presets()
            return True
        except Exception as e:
            logger.error(f"Failed to add preset: {e}")
            return False
    
    async def remove_preset(self, preset_id: str) -> bool:
        """Remove a preset from the configuration"""
        try:
            if preset_id in self._presets:
                del self._presets[preset_id]
                await self.save_presets()
            return True
        except Exception as e:
            logger.error(f"Failed to remove preset: {e}")
            return False
    
    def get_preset(self, preset_id: str) -> Optional[Preset]:
        """Get a preset by ID"""
        return self._presets.get(preset_id)
    
    def get_all_presets(self) -> List[Preset]:
        """Get all presets"""
        return list(self._presets.values())
    
    # UI settings
    def get_theme(self) -> str:
        return self.get_config("ui.theme", "dark")
    
    def set_theme(self, theme: str) -> None:
        self.set_config("ui.theme", theme)
    
    def get_language(self) -> str:
        return self.get_config("ui.language", "en")
    
    def set_language(self, language: str) -> None:
        self.set_config("ui.language", language)
    
    def show_advanced(self) -> bool:
        return self.get_config("ui.show_advanced", False)
    
    def set_show_advanced(self, show: bool) -> None:
        self.set_config("ui.show_advanced", show)
    
    # Spatial audio settings
    def get_spatial_settings(self) -> Dict[str, Any]:
        return self.get_config("spatial_audio", {})
    
    def set_spatial_settings(self, settings: Dict[str, Any]) -> None:
        self.set_config("spatial_audio", settings)
    
    # Mixer settings
    def get_mixer_settings(self) -> Dict[str, Any]:
        return self.get_config("mixer", {})
    
    def set_mixer_settings(self, settings: Dict[str, Any]) -> None:
        self.set_config("mixer", settings)
    
    async def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self._create_default_config()
        self._presets = {}
        await self.save_config()
        await self.save_presets()
        logger.info("Configuration reset to defaults")
    
    async def import_config(self, config_path: str) -> bool:
        """Import configuration from a file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            
            logger.info(f"Imported configuration from {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            return False
    
    async def export_config(self, config_path: str) -> bool:
        """Export configuration to a file"""
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported configuration to {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False
    
    async def import_presets(self, presets_path: str) -> bool:
        """Import presets from a file"""
        try:
            with open(presets_path, 'r', encoding='utf-8') as f:
                presets_data = json.load(f)
            
            for preset_id, preset_data in presets_data.items():
                preset = Preset.from_dict(preset_data)
                self._presets[preset_id] = preset
            
            await self.save_presets()
            logger.info(f"Imported {len(presets_data)} presets from {presets_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import presets: {e}")
            return False
    
    async def export_presets(self, presets_path: str) -> bool:
        """Export presets to a file"""
        try:
            presets_data = {
                preset_id: preset.to_dict()
                for preset_id, preset in self._presets.items()
            }
            
            with open(presets_path, 'w', encoding='utf-8') as f:
                json.dump(presets_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(presets_data)} presets to {presets_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export presets: {e}")
            return False
