"""
EasyEffects Integration

This module provides integration with EasyEffects (formerly PulseEffects),
which is a powerful audio effects application for Linux.

EasyEffects provides:
- Parametric EQ
- Noise gate
- Compressor
- Limiter
- Reverb
- Echo
- And many more effects

We'll use D-Bus or command-line interface to control EasyEffects.
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Callable, Awaitable
import logging

from ..models.preset import Preset, EQBand, EQType, EffectPreset
from ..core.channels import ChannelType
from ..utils.logger import get_logger

logger = get_logger(__name__)


class EasyEffectsConnectionMethod(Enum):
    """Methods to connect to EasyEffects"""
    DBUS = auto()       # D-Bus interface
    CLI = auto()        # Command-line interface
    WEBSOCKET = auto()  # WebSocket interface (if available)


@dataclass
class EasyEffectsPreset:
    """Represents an EasyEffects preset"""
    id: str
    name: str
    description: str = ""
    input_device: str = ""
    output_device: str = ""
    effects: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "input_device": self.input_device,
            "output_device": self.output_device,
            "effects": self.effects,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EasyEffectsPreset":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            input_device=data.get("input_device", ""),
            output_device=data.get("output_device", ""),
            effects=data.get("effects", {}),
        )


class EasyEffectsIntegration:
    """
    Provides integration with EasyEffects for audio processing.
    
    This class allows the Linux Sound Manager to:
    - Control EasyEffects presets
    - Configure individual effects
    - Synchronize settings between LSM and EasyEffects
    - Apply LSM presets to EasyEffects
    """
    
    # EasyEffects D-Bus interface
    DBUS_SERVICE = "com.github.wwmm.easyeffects"
    DBUS_PATH = "/com/github/wwmm/easyeffects"
    DBUS_INTERFACE = "com.github.wwmm.easyeffects"
    
    def __init__(self):
        self._connection_method = EasyEffectsConnectionMethod.CLI
        self._presets: Dict[str, EasyEffectsPreset] = {}
        self._current_preset_id: Optional[str] = None
        self._event_listeners: List[Callable[[str, Any], Awaitable[None]]] = []
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize EasyEffects integration"""
        try:
            # Check if EasyEffects is installed
            if not await self._check_easyeffects_installed():
                logger.warning("EasyEffects is not installed")
                return False
            
            # Try to connect via D-Bus first
            if await self._try_dbus_connection():
                self._connection_method = EasyEffectsConnectionMethod.DBUS
                logger.info("Connected to EasyEffects via D-Bus")
            else:
                # Fall back to CLI
                self._connection_method = EasyEffectsConnectionMethod.CLI
                logger.info("Using EasyEffects CLI interface")
            
            # Load presets
            await self._load_presets()
            
            self._initialized = True
            logger.info("EasyEffects integration initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize EasyEffects integration: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown EasyEffects integration"""
        self._initialized = False
        logger.info("EasyEffects integration shutdown")
    
    async def _check_easyeffects_installed(self) -> bool:
        """Check if EasyEffects is installed"""
        try:
            result = await asyncio.create_subprocess_exec(
                "which", "easyeffects",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    async def _try_dbus_connection(self) -> bool:
        """Try to connect to EasyEffects via D-Bus"""
        try:
            # Check if D-Bus service is available
            result = await asyncio.create_subprocess_exec(
                "dbus-send",
                "--print-reply",
                "--dest=" + self.DBUS_SERVICE,
                "/",
                "org.freedesktop.DBus.Properties.Get",
                "string:" + self.DBUS_INTERFACE,
                "string:Version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"D-Bus connection failed: {e}")
            return False
    
    async def _load_presets(self) -> None:
        """Load all EasyEffects presets"""
        try:
            if self._connection_method == EasyEffectsConnectionMethod.DBUS:
                await self._load_presets_dbus()
            else:
                await self._load_presets_cli()
        except Exception as e:
            logger.error(f"Failed to load presets: {e}")
    
    async def _load_presets_dbus(self) -> None:
        """Load presets via D-Bus"""
        # Implementation would use D-Bus to list presets
        logger.info("Loading presets via D-Bus")
    
    async def _load_presets_cli(self) -> None:
        """Load presets via CLI"""
        try:
            # Use easyeffects CLI to list presets
            # Note: The actual CLI interface may vary
            result = await asyncio.create_subprocess_exec(
                "easyeffects", "--list-presets",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.warning("Failed to list EasyEffects presets via CLI")
                return
            
            # Parse output (this is a placeholder - actual parsing depends on CLI output format)
            output = stdout.decode()
            lines = output.strip().split('\n')
            
            for line in lines:
                if not line.strip():
                    continue
                
                # Parse preset information
                parts = line.split('|')
                if len(parts) >= 2:
                    preset_id = parts[0].strip()
                    preset_name = parts[1].strip()
                    
                    preset = EasyEffectsPreset(
                        id=preset_id,
                        name=preset_name,
                    )
                    self._presets[preset_id] = preset
            
            logger.info(f"Loaded {len(self._presets)} presets via CLI")
            
        except Exception as e:
            logger.error(f"Failed to load presets via CLI: {e}")
    
    async def get_presets(self) -> List[EasyEffectsPreset]:
        """Get all EasyEffects presets"""
        return list(self._presets.values())
    
    async def get_preset(self, preset_id: str) -> Optional[EasyEffectsPreset]:
        """Get a specific preset"""
        return self._presets.get(preset_id)
    
    async def apply_preset(self, preset_id: str) -> bool:
        """Apply a preset in EasyEffects"""
        try:
            if preset_id not in self._presets:
                logger.error(f"Preset {preset_id} not found")
                return False
            
            if self._connection_method == EasyEffectsConnectionMethod.DBUS:
                return await self._apply_preset_dbus(preset_id)
            else:
                return await self._apply_preset_cli(preset_id)
            
        except Exception as e:
            logger.error(f"Failed to apply preset: {e}")
            return False
    
    async def _apply_preset_dbus(self, preset_id: str) -> bool:
        """Apply preset via D-Bus"""
        try:
            # Use gdbus to call EasyEffects
            result = await asyncio.create_subprocess_exec(
                "gdbus", "call",
                "--dest", self.DBUS_SERVICE,
                "--object-path", self.DBUS_PATH,
                "--method", self.DBUS_INTERFACE + ".load_preset",
                preset_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Failed to apply preset via D-Bus: {stderr.decode()}")
                return False
            
            self._current_preset_id = preset_id
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply preset via D-Bus: {e}")
            return False
    
    async def _apply_preset_cli(self, preset_id: str) -> bool:
        """Apply preset via CLI"""
        try:
            result = await asyncio.create_subprocess_exec(
                "easyeffects", "--load-preset", preset_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Failed to apply preset via CLI: {stderr.decode()}")
                return False
            
            self._current_preset_id = preset_id
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply preset via CLI: {e}")
            return False
    
    async def create_preset(self, name: str, description: str = "") -> Optional[EasyEffectsPreset]:
        """Create a new preset in EasyEffects"""
        try:
            preset_id = f"lsm-{name.lower().replace(' ', '-')}"
            
            if self._connection_method == EasyEffectsConnectionMethod.DBUS:
                success = await self._create_preset_dbus(preset_id, name, description)
            else:
                success = await self._create_preset_cli(preset_id, name, description)
            
            if success:
                preset = EasyEffectsPreset(
                    id=preset_id,
                    name=name,
                    description=description,
                )
                self._presets[preset_id] = preset
                return preset
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create preset: {e}")
            return None
    
    async def _create_preset_dbus(self, preset_id: str, name: str, description: str) -> bool:
        """Create preset via D-Bus"""
        try:
            # This would use D-Bus to create a new preset
            # Implementation depends on EasyEffects D-Bus API
            return True
        except Exception as e:
            logger.error(f"Failed to create preset via D-Bus: {e}")
            return False
    
    async def _create_preset_cli(self, preset_id: str, name: str, description: str) -> bool:
        """Create preset via CLI"""
        try:
            # This would use CLI to create a new preset
            # Implementation depends on EasyEffects CLI API
            return True
        except Exception as e:
            logger.error(f"Failed to create preset via CLI: {e}")
            return False
    
    async def delete_preset(self, preset_id: str) -> bool:
        """Delete a preset from EasyEffects"""
        try:
            if preset_id not in self._presets:
                return False
            
            if self._connection_method == EasyEffectsConnectionMethod.DBUS:
                return await self._delete_preset_dbus(preset_id)
            else:
                return await self._delete_preset_cli(preset_id)
            
        except Exception as e:
            logger.error(f"Failed to delete preset: {e}")
            return False
    
    async def _delete_preset_dbus(self, preset_id: str) -> bool:
        """Delete preset via D-Bus"""
        try:
            # Implementation would use D-Bus
            return True
        except Exception as e:
            logger.error(f"Failed to delete preset via D-Bus: {e}")
            return False
    
    async def _delete_preset_cli(self, preset_id: str) -> bool:
        """Delete preset via CLI"""
        try:
            # Implementation would use CLI
            return True
        except Exception as e:
            logger.error(f"Failed to delete preset via CLI: {e}")
            return False
    
    async def import_lsm_preset(self, preset: Preset) -> Optional[EasyEffectsPreset]:
        """
        Import a Linux Sound Manager preset into EasyEffects.
        
        This converts an LSM preset to an EasyEffects-compatible format.
        """
        try:
            # Create a new EasyEffects preset
            preset_id = f"lsm-{preset.name.lower().replace(' ', '-')}"
            
            # Convert LSM preset to EasyEffects format
            ee_preset = EasyEffectsPreset(
                id=preset_id,
                name=preset.name,
                description=preset.description,
            )
            
            # Convert EQ bands
            if preset.preset_type in (PresetType.EQ, PresetType.COMPLETE):
                ee_preset.effects["equalizer"] = {
                    "enabled": True,
                    "bands": [
                        {
                            "frequency": band.frequency,
                            "gain": band.gain,
                            "q": band.q_factor,
                            "type": band.eq_type.name.lower(),
                        }
                        for band in preset.eq_bands
                    ]
                }
            
            # Convert effect presets
            for effect_preset in preset.effect_presets:
                ee_preset.effects[effect_preset.effect_type] = {
                    "enabled": effect_preset.enabled,
                    "parameters": effect_preset.parameters,
                }
            
            # Save the preset
            self._presets[preset_id] = ee_preset
            
            # Apply the preset to EasyEffects
            if self._connection_method == EasyEffectsConnectionMethod.DBUS:
                await self._apply_preset_dbus(preset_id)
            else:
                await self._apply_preset_cli(preset_id)
            
            return ee_preset
            
        except Exception as e:
            logger.error(f"Failed to import LSM preset: {e}")
            return None
    
    async def export_easyeffects_preset(self, preset_id: str) -> Optional[Preset]:
        """
        Export an EasyEffects preset to Linux Sound Manager format.
        """
        try:
            ee_preset = self._presets.get(preset_id)
            if not ee_preset:
                return None
            
            # Create LSM preset
            lsm_preset = Preset(
                name=ee_preset.name,
                description=ee_preset.description,
                preset_type=PresetType.COMPLETE,
            )
            
            # Convert EQ
            if "equalizer" in ee_preset.effects:
                eq_data = ee_preset.effects["equalizer"]
                if eq_data.get("enabled", False):
                    for band_data in eq_data.get("bands", []):
                        eq_band = EQBand(
                            frequency=band_data.get("frequency", 1000.0),
                            gain=band_data.get("gain", 0.0),
                            q_factor=band_data.get("q", 1.0),
                            eq_type=EQType[band_data.get("type", "PEAKING").upper()],
                            enabled=True,
                        )
                        lsm_preset.eq_bands.append(eq_band)
            
            # Convert other effects
            for effect_type, effect_data in ee_preset.effects.items():
                if effect_type == "equalizer":
                    continue
                
                effect_preset = EffectPreset(
                    name=effect_type,
                    effect_type=effect_type,
                    parameters=effect_data.get("parameters", {}),
                    enabled=effect_data.get("enabled", True),
                )
                lsm_preset.effect_presets.append(effect_preset)
            
            return lsm_preset
            
        except Exception as e:
            logger.error(f"Failed to export EasyEffects preset: {e}")
            return None
    
    async def set_effect_parameter(
        self, 
        effect_type: str, 
        parameter: str, 
        value: float
    ) -> bool:
        """Set a parameter for a specific effect"""
        try:
            if self._connection_method == EasyEffectsConnectionMethod.DBUS:
                return await self._set_effect_parameter_dbus(effect_type, parameter, value)
            else:
                return await self._set_effect_parameter_cli(effect_type, parameter, value)
            
        except Exception as e:
            logger.error(f"Failed to set effect parameter: {e}")
            return False
    
    async def _set_effect_parameter_dbus(
        self, 
        effect_type: str, 
        parameter: str, 
        value: float
    ) -> bool:
        """Set effect parameter via D-Bus"""
        try:
            # Implementation would use D-Bus
            return True
        except Exception as e:
            logger.error(f"Failed to set effect parameter via D-Bus: {e}")
            return False
    
    async def _set_effect_parameter_cli(
        self, 
        effect_type: str, 
        parameter: str, 
        value: float
    ) -> bool:
        """Set effect parameter via CLI"""
        try:
            # Implementation would use CLI
            return True
        except Exception as e:
            logger.error(f"Failed to set effect parameter via CLI: {e}")
            return False
    
    async def enable_effect(self, effect_type: str, enabled: bool) -> bool:
        """Enable or disable an effect"""
        try:
            if self._connection_method == EasyEffectsConnectionMethod.DBUS:
                return await self._enable_effect_dbus(effect_type, enabled)
            else:
                return await self._enable_effect_cli(effect_type, enabled)
            
        except Exception as e:
            logger.error(f"Failed to enable/disable effect: {e}")
            return False
    
    async def _enable_effect_dbus(self, effect_type: str, enabled: bool) -> bool:
        """Enable/disable effect via D-Bus"""
        try:
            return True
        except Exception as e:
            logger.error(f"Failed to enable/disable effect via D-Bus: {e}")
            return False
    
    async def _enable_effect_cli(self, effect_type: str, enabled: bool) -> bool:
        """Enable/disable effect via CLI"""
        try:
            return True
        except Exception as e:
            logger.error(f"Failed to enable/disable effect via CLI: {e}")
            return False
    
    async def get_current_preset_id(self) -> Optional[str]:
        """Get the ID of the currently active preset"""
        return self._current_preset_id
    
    def add_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Add an event listener for EasyEffects events"""
        self._event_listeners.append(listener)
    
    def remove_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Remove an event listener"""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)
    
    async def get_status(self) -> Dict[str, Any]:
        """Get the current status of EasyEffects integration"""
        return {
            "initialized": self._initialized,
            "connection_method": self._connection_method.name,
            "presets_count": len(self._presets),
            "current_preset_id": self._current_preset_id,
        }
