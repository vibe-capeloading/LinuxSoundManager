"""
Audio Engine - Main audio processing engine

This is the central module that coordinates all audio processing,
including channel management, mixing, effects, and spatial audio.
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Callable, Awaitable
import numpy as np

from .pipewire_manager import PipeWireManager
from .channels import ChannelManager, Channel, ChannelType
from .mixer import AudioMixer, MixerMode
from .effects import EffectsManager
from .spatial_audio import SpatialAudio, SpatialSettings
from ..models.audio_device import AudioDevice, DeviceType
from ..models.audio_source import AudioSource, SourceType
from ..models.preset import Preset, PresetType
from ..utils.logger import get_logger

logger = get_logger(__name__)


class EngineState(Enum):
    """Audio engine states"""
    STOPPED = auto()
    STARTING = auto()
    RUNNING = auto()
    STOPPING = auto()
    ERROR = auto()


@dataclass
class EngineSettings:
    """Settings for the audio engine"""
    sample_rate: int = 48000
    buffer_size: int = 1024
    latency: float = 0.01  # seconds
    enable_spatial: bool = False
    enable_effects: bool = True
    enable_eq: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_rate": self.sample_rate,
            "buffer_size": self.buffer_size,
            "latency": self.latency,
            "enable_spatial": self.enable_spatial,
            "enable_effects": self.enable_effects,
            "enable_eq": self.enable_eq,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EngineSettings":
        return cls(
            sample_rate=data.get("sample_rate", 48000),
            buffer_size=data.get("buffer_size", 1024),
            latency=data.get("latency", 0.01),
            enable_spatial=data.get("enable_spatial", False),
            enable_effects=data.get("enable_effects", True),
            enable_eq=data.get("enable_eq", True),
        )


class AudioEngine:
    """
    Main audio engine that coordinates all audio processing.
    
    This is the central class that:
    - Manages PipeWire integration
    - Coordinates channel management
    - Handles audio mixing
    - Applies effects
    - Processes spatial audio
    - Manages presets
    """
    
    def __init__(self):
        self._state = EngineState.STOPPED
        self._settings = EngineSettings()
        
        # Core components
        self._pipewire_manager: Optional[PipeWireManager] = None
        self._channel_manager: Optional[ChannelManager] = None
        self._mixer: Optional[AudioMixer] = None
        self._effects_manager: Optional[EffectsManager] = None
        self._spatial_audio: Optional[SpatialAudio] = None
        
        # Presets
        self._presets: Dict[str, Preset] = {}
        self._current_preset_id: Optional[str] = None
        
        # Event listeners
        self._event_listeners: List[Callable[[str, Any], Awaitable[None]]] = []
        
        # Audio processing task
        self._processing_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> bool:
        """Initialize the audio engine"""
        try:
            self._state = EngineState.STARTING
            
            # Initialize PipeWire manager
            self._pipewire_manager = PipeWireManager()
            if not await self._pipewire_manager.initialize():
                logger.error("Failed to initialize PipeWire manager")
                self._state = EngineState.ERROR
                return False
            
            # Initialize channel manager
            self._channel_manager = ChannelManager(self._pipewire_manager)
            if not await self._channel_manager.initialize():
                logger.error("Failed to initialize channel manager")
                self._state = EngineState.ERROR
                return False
            
            # Initialize mixer
            self._mixer = AudioMixer(self._pipewire_manager, self._channel_manager)
            if not await self._mixer.initialize():
                logger.error("Failed to initialize mixer")
                self._state = EngineState.ERROR
                return False
            
            # Initialize effects manager
            self._effects_manager = EffectsManager(
                self._pipewire_manager, 
                self._channel_manager
            )
            if not await self._effects_manager.initialize():
                logger.error("Failed to initialize effects manager")
                self._state = EngineState.ERROR
                return False
            
            # Initialize spatial audio
            self._spatial_audio = SpatialAudio(
                self._pipewire_manager, 
                self._channel_manager
            )
            if not await self._spatial_audio.initialize():
                logger.error("Failed to initialize spatial audio")
                self._state = EngineState.ERROR
                return False
            
            # Load default presets
            await self._load_default_presets()
            
            # Start monitoring
            await self._pipewire_manager.start_monitoring()
            
            self._state = EngineState.RUNNING
            logger.info("Audio engine initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize audio engine: {e}")
            self._state = EngineState.ERROR
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the audio engine"""
        try:
            self._state = EngineState.STOPPING
            
            # Stop processing task
            if self._processing_task:
                self._processing_task.cancel()
                try:
                    await self._processing_task
                except asyncio.CancelledError:
                    pass
            
            # Shutdown components
            if self._spatial_audio:
                await self._spatial_audio.shutdown()
            if self._effects_manager:
                await self._effects_manager.shutdown()
            if self._mixer:
                await self._mixer.shutdown()
            if self._channel_manager:
                await self._channel_manager.shutdown()
            if self._pipewire_manager:
                await self._pipewire_manager.shutdown()
            
            self._state = EngineState.STOPPED
            logger.info("Audio engine shutdown")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            self._state = EngineState.ERROR
    
    async def _load_default_presets(self) -> None:
        """Load default presets"""
        try:
            # Flat EQ preset
            flat_preset = Preset.create_default_eq_preset("Flat")
            self._presets[flat_preset.id] = flat_preset
            
            # Gaming preset
            gaming_preset = Preset.create_gaming_preset()
            self._presets[gaming_preset.id] = gaming_preset
            
            # Create some effect presets
            noise_gate_preset = EffectPreset(
                name="Aggressive Noise Gate",
                effect_type="noise_gate",
                parameters={
                    "threshold": -30.0,
                    "attack": 0.005,
                    "release": 0.05,
                    "hold": 0.02
                },
                enabled=True
            )
            
            gaming_preset.effect_presets.append(noise_gate_preset)
            
            logger.info(f"Loaded {len(self._presets)} default presets")
            
        except Exception as e:
            logger.error(f"Failed to load default presets: {e}")
    
    async def start_audio_processing(self) -> bool:
        """Start audio processing loop"""
        try:
            if self._state != EngineState.RUNNING:
                logger.error("Audio engine is not running")
                return False
            
            if self._processing_task and not self._processing_task.done():
                logger.warning("Audio processing is already running")
                return True
            
            async def processing_loop():
                while self._state == EngineState.RUNNING:
                    try:
                        # Process audio for each channel
                        await self._process_all_channels()
                        
                        # Sleep for buffer duration
                        buffer_duration = self._settings.buffer_size / self._settings.sample_rate
                        await asyncio.sleep(buffer_duration)
                        
                    except Exception as e:
                        logger.error(f"Error in audio processing loop: {e}")
                        await asyncio.sleep(0.1)  # Wait before retrying
            
            self._processing_task = asyncio.create_task(processing_loop())
            logger.info("Audio processing started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio processing: {e}")
            return False
    
    async def _process_all_channels(self) -> None:
        """Process audio for all channels"""
        try:
            if not self._channel_manager or not self._mixer:
                return
            
            channels = self._channel_manager.get_all_channels()
            
            for channel in channels:
                if channel.is_master:
                    continue
                
                # Get sources for this channel
                sources = await self._channel_manager.get_sources_in_channel(channel.channel_type)
                
                # Process each source
                for source in sources:
                    # In a real implementation, we would:
                    # 1. Capture audio from the source
                    # 2. Apply EQ
                    # 3. Apply effects
                    # 4. Apply spatial audio
                    # 5. Mix into the channel
                    pass
                
                # Apply channel effects
                if self._settings.enable_effects:
                    eq_bands = await self._effects_manager.get_channel_eq(channel.channel_type)
                    # Apply EQ to channel audio
                    
                # Apply spatial audio if enabled
                if self._settings.enable_spatial:
                    spatial_settings = await self._spatial_audio.get_settings()
                    if spatial_settings.enabled:
                        # Apply spatial processing
                        pass
            
            # Mix all channels
            if self._mixer:
                # Get mix levels
                mix_levels = await self._mixer.get_mix_levels()
                
            # Apply master effects
            if self._settings.enable_effects:
                # Apply master EQ, limiter, etc.
                pass
            
        except Exception as e:
            logger.error(f"Failed to process channels: {e}")
    
    async def set_settings(self, settings: EngineSettings) -> bool:
        """Set engine settings"""
        try:
            self._settings = EngineSettings.from_dict(settings.to_dict())
            
            # Update spatial audio settings
            if self._spatial_audio:
                spatial_settings = await self._spatial_audio.get_settings()
                spatial_settings.enabled = self._settings.enable_spatial
                await self._spatial_audio.set_settings(spatial_settings)
            
            # Notify listeners
            for listener in self._event_listeners:
                try:
                    await listener("settings_changed", settings.to_dict())
                except Exception as e:
                    logger.error(f"Event listener error: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set engine settings: {e}")
            return False
    
    async def get_settings(self) -> EngineSettings:
        """Get current engine settings"""
        return self._settings.copy()
    
    async def get_state(self) -> EngineState:
        """Get current engine state"""
        return self._state
    
    # Channel management
    async def get_channels(self) -> List[Channel]:
        """Get all channels"""
        if not self._channel_manager:
            return []
        return self._channel_manager.get_all_channels()
    
    async def get_channel(self, channel_type: ChannelType) -> Optional[Channel]:
        """Get a specific channel"""
        if not self._channel_manager:
            return None
        return self._channel_manager.get_channel(channel_type)
    
    async def set_channel_volume(self, channel_type: ChannelType, volume: float) -> bool:
        """Set volume for a channel"""
        if not self._channel_manager:
            return False
        return await self._channel_manager.set_channel_volume(channel_type, volume)
    
    async def set_channel_mute(self, channel_type: ChannelType, muted: bool) -> bool:
        """Set mute state for a channel"""
        if not self._channel_manager:
            return False
        return await self._channel_manager.set_channel_mute(channel_type, muted)
    
    # Source management
    async def get_sources(self) -> List[AudioSource]:
        """Get all audio sources"""
        if not self._pipewire_manager:
            return []
        return await self._pipewire_manager.get_sources()
    
    async def assign_source_to_channel(
        self, 
        source_id: str, 
        channel_type: ChannelType
    ) -> bool:
        """Assign an audio source to a channel"""
        if not self._channel_manager:
            return False
        return await self._channel_manager.assign_source_to_channel(source_id, channel_type)
    
    async def get_source_channel(self, source_id: str) -> Optional[ChannelType]:
        """Get the channel a source is assigned to"""
        if not self._channel_manager:
            return None
        return await self._channel_manager.get_source_channel(source_id)
    
    # Mixer management
    async def set_master_volume(self, volume: float) -> bool:
        """Set master volume"""
        if not self._mixer:
            return False
        return await self._mixer.set_master_volume(volume)
    
    async def set_master_mute(self, muted: bool) -> bool:
        """Set master mute state"""
        if not self._mixer:
            return False
        return await self._mixer.set_master_mute(muted)
    
    async def set_mixer_mode(self, mode: MixerMode) -> bool:
        """Set mixer mode"""
        if not self._mixer:
            return False
        self._mixer._settings.mode = mode
        return True
    
    # Effects management
    async def set_channel_eq(
        self, 
        channel_type: ChannelType, 
        eq_bands: List[Any]
    ) -> bool:
        """Set EQ bands for a channel"""
        if not self._effects_manager:
            return False
        return await self._effects_manager.set_channel_eq(channel_type, eq_bands)
    
    async def get_channel_eq(self, channel_type: ChannelType) -> List[Any]:
        """Get EQ bands for a channel"""
        if not self._effects_manager:
            return []
        return await self._effects_manager.get_channel_eq(channel_type)
    
    async def set_channel_noise_gate(
        self, 
        channel_type: ChannelType, 
        settings: Dict[str, Any]
    ) -> bool:
        """Set noise gate settings for a channel"""
        if not self._effects_manager:
            return False
        from .effects import NoiseGateSettings
        noise_gate_settings = NoiseGateSettings.from_dict(settings)
        return await self._effects_manager.set_channel_noise_gate(channel_type, noise_gate_settings)
    
    async def set_channel_compressor(
        self, 
        channel_type: ChannelType, 
        settings: Dict[str, Any]
    ) -> bool:
        """Set compressor settings for a channel"""
        if not self._effects_manager:
            return False
        from .effects import CompressorSettings
        compressor_settings = CompressorSettings.from_dict(settings)
        return await self._effects_manager.set_channel_compressor(channel_type, compressor_settings)
    
    async def set_channel_limiter(
        self, 
        channel_type: ChannelType, 
        settings: Dict[str, Any]
    ) -> bool:
        """Set limiter settings for a channel"""
        if not self._effects_manager:
            return False
        from .effects import LimiterSettings
        limiter_settings = LimiterSettings.from_dict(settings)
        return await self._effects_manager.set_channel_limiter(channel_type, limiter_settings)
    
    async def set_channel_clearcast(
        self, 
        channel_type: ChannelType, 
        settings: Dict[str, Any]
    ) -> bool:
        """Set ClearCast settings for a channel"""
        if not self._effects_manager:
            return False
        from .effects import ClearCastSettings
        clearcast_settings = ClearCastSettings.from_dict(settings)
        return await self._effects_manager.set_channel_clearcast(channel_type, clearcast_settings)
    
    # Spatial audio management
    async def set_spatial_settings(self, settings: Dict[str, Any]) -> bool:
        """Set spatial audio settings"""
        if not self._spatial_audio:
            return False
        from .spatial_audio import SpatialSettings
        spatial_settings = SpatialSettings.from_dict(settings)
        return await self._spatial_audio.set_settings(spatial_settings)
    
    async def get_spatial_settings(self) -> Dict[str, Any]:
        """Get spatial audio settings"""
        if not self._spatial_audio:
            return {}
        settings = await self._spatial_audio.get_settings()
        return settings.to_dict()
    
    async def enable_spatial_for_channel(
        self, 
        channel_type: ChannelType, 
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    ) -> bool:
        """Enable spatial audio for a channel"""
        if not self._spatial_audio:
            return False
        return await self._spatial_audio.enable_spatial_for_channel(channel_type, position)
    
    async def set_channel_position(
        self, 
        channel_type: ChannelType, 
        position: Tuple[float, float, float]
    ) -> bool:
        """Set the position of a channel in 3D space"""
        if not self._spatial_audio:
            return False
        return await self._spatial_audio.set_channel_position(channel_type, position)
    
    # Preset management
    async def get_presets(self) -> List[Preset]:
        """Get all presets"""
        return list(self._presets.values())
    
    async def get_preset(self, preset_id: str) -> Optional[Preset]:
        """Get a specific preset"""
        return self._presets.get(preset_id)
    
    async def add_preset(self, preset: Preset) -> bool:
        """Add a new preset"""
        try:
            self._presets[preset.id] = preset
            
            # Notify listeners
            for listener in self._event_listeners:
                try:
                    await listener("preset_added", preset.to_dict())
                except Exception as e:
                    logger.error(f"Event listener error: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add preset: {e}")
            return False
    
    async def remove_preset(self, preset_id: str) -> bool:
        """Remove a preset"""
        try:
            if preset_id in self._presets:
                del self._presets[preset_id]
                
                # Notify listeners
                for listener in self._event_listeners:
                    try:
                        await listener("preset_removed", {"id": preset_id})
                    except Exception as e:
                        logger.error(f"Event listener error: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove preset: {e}")
            return False
    
    async def apply_preset(self, preset_id: str) -> bool:
        """Apply a preset to all channels"""
        try:
            preset = self._presets.get(preset_id)
            if not preset:
                logger.error(f"Preset {preset_id} not found")
                return False
            
            self._current_preset_id = preset_id
            
            # Apply to all channels
            if not self._channel_manager or not self._effects_manager:
                return False
            
            channels = self._channel_manager.get_all_channels()
            
            for channel in channels:
                if channel.is_master:
                    continue
                
                # Apply preset to channel
                await self._effects_manager.apply_preset_to_channel(
                    preset, 
                    channel.channel_type
                )
                
                # Apply channel-specific settings if present
                if channel.channel_type.name.lower() in preset.channel_settings:
                    channel_settings = preset.channel_settings[channel.channel_type.name.lower()]
                    if "volume" in channel_settings:
                        await self.set_channel_volume(
                            channel.channel_type, 
                            channel_settings["volume"]
                        )
                    if "muted" in channel_settings:
                        await self.set_channel_mute(
                            channel.channel_type, 
                            channel_settings["muted"]
                        )
            
            # Apply spatial settings if present
            if preset.preset_type == PresetType.COMPLETE and preset.spatial_settings:
                await self.set_spatial_settings(preset.spatial_settings)
            
            # Notify listeners
            for listener in self._event_listeners:
                try:
                    await listener("preset_applied", {"id": preset_id})
                except Exception as e:
                    logger.error(f"Event listener error: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply preset: {e}")
            return False
    
    async def get_current_preset(self) -> Optional[Preset]:
        """Get the currently applied preset"""
        if not self._current_preset_id:
            return None
        return self._presets.get(self._current_preset_id)
    
    # Device management
    async def get_devices(self) -> List[AudioDevice]:
        """Get all audio devices"""
        if not self._pipewire_manager:
            return []
        return await self._pipewire_manager.get_devices()
    
    async def get_output_devices(self) -> List[AudioDevice]:
        """Get all output devices"""
        if not self._pipewire_manager:
            return []
        return await self._pipewire_manager.get_sinks()
    
    async def get_input_devices(self) -> List[AudioDevice]:
        """Get all input devices"""
        if not self._pipewire_manager:
            return []
        devices = await self._pipewire_manager.get_devices()
        return [d for d in devices if d.is_input]
    
    # Event listeners
    def add_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Add an event listener for engine events"""
        self._event_listeners.append(listener)
    
    def remove_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Remove an event listener"""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)
    
    async def get_full_state(self) -> Dict[str, Any]:
        """Get the complete state of the audio engine"""
        state = {
            "engine": {
                "state": self._state.name,
                "settings": self._settings.to_dict(),
            },
            "channels": {},
            "sources": [],
            "devices": [],
            "presets": {},
            "mixer": {},
            "effects": {},
            "spatial": {},
        }
        
        # Add channels
        if self._channel_manager:
            for channel in self._channel_manager.get_all_channels():
                state["channels"][channel.channel_type.name] = channel.to_dict()
        
        # Add sources
        if self._pipewire_manager:
            sources = await self._pipewire_manager.get_sources()
            state["sources"] = [s.to_dict() for s in sources]
        
        # Add devices
        if self._pipewire_manager:
            devices = await self._pipewire_manager.get_devices()
            state["devices"] = [d.to_dict() for d in devices]
        
        # Add presets
        state["presets"] = {pid: p.to_dict() for pid, p in self._presets.items()}
        
        # Add mixer state
        if self._mixer:
            state["mixer"] = await self._mixer.get_current_configuration()
        
        # Add effects summary
        if self._effects_manager:
            for channel_type in ChannelType:
                if channel_type != ChannelType.MASTER:
                    state["effects"][channel_type.name] = await self._effects_manager.get_channel_effects_summary(channel_type)
        
        # Add spatial state
        if self._spatial_audio:
            state["spatial"] = await self._spatial_audio.get_spatial_state()
        
        return state
