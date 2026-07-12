"""
Spatial Audio - 360-degree audio simulation

This module provides spatial audio processing, simulating surround sound
on stereo headphones or speakers.
"""

import asyncio
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Tuple, Callable, Awaitable
import numpy as np

from .channels import ChannelManager, Channel, ChannelType
from .pipewire_manager import PipeWireManager
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SpatialMode(Enum):
    """Spatial audio modes"""
    HEADPHONES = auto()      # Binaural rendering for headphones
    SPEAKERS = auto()        # Stereo speaker setup
    SURROUND_5_1 = auto()    # 5.1 surround sound
    SURROUND_7_1 = auto()    # 7.1 surround sound


class HRTFType(Enum):
    """Head-Related Transfer Function types"""
    DEFAULT = auto()         # Default HRTF
    CUSTOM = auto()          # Custom HRTF
    MIT = auto()             # MIT KEMAR HRTF
    LISTEN = auto()          # LISTEN HRTF


@dataclass
class SpatialSettings:
    """Settings for spatial audio"""
    mode: SpatialMode = SpatialMode.HEADPHONES
    hrtf_type: HRTFType = HRTFType.DEFAULT
    enabled: bool = False
    
    # Position settings
    distance: float = 1.0    # Distance from listener (0.1 to 10)
    elevation: float = 0.0  # Elevation in degrees (-90 to 90)
    azimuth: float = 0.0     # Azimuth in degrees (0 to 360)
    
    # Performance settings
    quality: str = "high"    # "low", "medium", "high"
    max_sources: int = 16    # Maximum number of spatialized sources
    
    # Room simulation
    room_size: float = 5.0   # Room size in meters
    reverberation: float = 0.3  # Reverberation amount (0.0 to 1.0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.name,
            "hrtf_type": self.hrtf_type.name,
            "enabled": self.enabled,
            "distance": self.distance,
            "elevation": self.elevation,
            "azimuth": self.azimuth,
            "quality": self.quality,
            "max_sources": self.max_sources,
            "room_size": self.room_size,
            "reverberation": self.reverberation,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpatialSettings":
        return cls(
            mode=SpatialMode[data.get("mode", "HEADPHONES")],
            hrtf_type=HRTFType[data.get("hrtf_type", "DEFAULT")],
            enabled=data.get("enabled", False),
            distance=data.get("distance", 1.0),
            elevation=data.get("elevation", 0.0),
            azimuth=data.get("azimuth", 0.0),
            quality=data.get("quality", "high"),
            max_sources=data.get("max_sources", 16),
            room_size=data.get("room_size", 5.0),
            reverberation=data.get("reverberation", 0.3),
        )


@dataclass
class SoundSource:
    """
    Represents a sound source in 3D space
    
    Attributes:
        id: Unique identifier
        channel_type: Which channel this source belongs to
        position: (x, y, z) position in meters
        velocity: (vx, vy, vz) velocity in meters/second
        volume: Volume (0.0 to 1.0)
        distance_attenuation: How sound attenuates with distance
        spread: How spread out the sound is (0.0 to 1.0)
    """
    id: str
    channel_type: ChannelType
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    volume: float = 1.0
    distance_attenuation: bool = True
    spread: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "channel_type": self.channel_type.name,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "volume": self.volume,
            "distance_attenuation": self.distance_attenuation,
            "spread": self.spread,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoundSource":
        return cls(
            id=data["id"],
            channel_type=ChannelType[data["channel_type"]],
            position=tuple(data.get("position", [0.0, 0.0, 0.0])),
            velocity=tuple(data.get("velocity", [0.0, 0.0, 0.0])),
            volume=data.get("volume", 1.0),
            distance_attenuation=data.get("distance_attenuation", True),
            spread=data.get("spread", 0.5),
        )


@dataclass
class Listener:
    """
    Represents the listener (user) in 3D space
    
    Attributes:
        position: (x, y, z) position in meters
        orientation: (yaw, pitch, roll) in degrees
        velocity: (vx, vy, vz) velocity in meters/second
        hrtf: HRTF data for this listener
    """
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # yaw, pitch, roll
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    hrtf: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": list(self.position),
            "orientation": list(self.orientation),
            "velocity": list(self.velocity),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Listener":
        return cls(
            position=tuple(data.get("position", [0.0, 0.0, 0.0])),
            orientation=tuple(data.get("orientation", [0.0, 0.0, 0.0])),
            velocity=tuple(data.get("velocity", [0.0, 0.0, 0.0])),
        )


class SpatialAudio:
    """
    Manages spatial audio processing.
    
    Provides functionality for:
    - 3D positioning of audio sources
    - HRTF-based binaural rendering
    - Room simulation and reverberation
    - Doppler effect simulation
    - Distance attenuation
    """
    
    # Speed of sound in air (m/s)
    SPEED_OF_SOUND = 343.0
    
    def __init__(
        self, 
        pipewire_manager: PipeWireManager,
        channel_manager: ChannelManager
    ):
        self._pipewire_manager = pipewire_manager
        self._channel_manager = channel_manager
        self._settings = SpatialSettings()
        self._listener = Listener()
        self._sound_sources: Dict[str, SoundSource] = {}
        self._event_listeners: List[Callable[[str, Any], Awaitable[None]]] = []
        self._initialized = False
        
        # HRTF data (simplified for now)
        self._hrtf_data: Dict[Tuple[float, float], Tuple[np.ndarray, np.ndarray]] = {}
        
    async def initialize(self) -> bool:
        """Initialize spatial audio"""
        try:
            # Load default HRTF data
            await self._load_default_hrtf()
            
            self._initialized = True
            logger.info("Spatial audio initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize spatial audio: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown spatial audio"""
        self._initialized = False
        logger.info("Spatial audio shutdown")
    
    async def _load_default_hrtf(self) -> None:
        """Load default HRTF data"""
        try:
            # In a real implementation, this would load HRTF data from files
            # For now, we'll use a simplified model
            
            # Generate some basic HRTF filters for different angles
            angles = range(0, 360, 15)
            elevations = range(-45, 46, 15)
            
            for azimuth in angles:
                for elevation in elevations:
                    # Generate simplified HRTF filters
                    left_ear, right_ear = self._generate_simple_hrtf(azimuth, elevation)
                    self._hrtf_data[(azimuth, elevation)] = (left_ear, right_ear)
            
            logger.info(f"Loaded HRTF data for {len(self._hrtf_data)} positions")
            
        except Exception as e:
            logger.error(f"Failed to load HRTF data: {e}")
    
    def _generate_simple_hrtf(self, azimuth: float, elevation: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate simplified HRTF filters for a given position.
        
        This is a placeholder. In a real implementation, this would use
        pre-measured HRTF data or a more sophisticated model.
        """
        # Convert azimuth and elevation to radians
        az_rad = math.radians(azimuth)
        el_rad = math.radians(elevation)
        
        # Calculate interaural time difference (ITD)
        # Simplified: ITD = (head_radius / speed_of_sound) * sin(azimuth) * cos(elevation)
        head_radius = 0.0875  # Average head radius in meters
        itd = (head_radius / self.SPEED_OF_SOUND) * math.sin(az_rad) * math.cos(el_rad)
        
        # Calculate interaural level difference (ILD)
        # Simplified model based on azimuth
        ild = 0.5 * math.sin(az_rad) * math.cos(el_rad)
        
        # Generate simple FIR filters (64 taps)
        num_taps = 64
        sample_rate = 48000
        
        # Left ear filter
        left_filter = np.zeros(num_taps)
        # Right ear filter
        right_filter = np.zeros(num_taps)
        
        # Add delay based on ITD
        delay_samples = int(itd * sample_rate)
        if delay_samples > 0:
            # Left ear leads
            if delay_samples < num_taps:
                left_filter[delay_samples] = 1.0 - ild
                right_filter[0] = 1.0 + ild
            else:
                left_filter[-1] = 1.0 - ild
                right_filter[0] = 1.0 + ild
        elif delay_samples < 0:
            # Right ear leads
            delay_samples = abs(delay_samples)
            if delay_samples < num_taps:
                right_filter[delay_samples] = 1.0 + ild
                left_filter[0] = 1.0 - ild
            else:
                right_filter[-1] = 1.0 + ild
                left_filter[0] = 1.0 - ild
        else:
            # No delay
            left_filter[0] = 1.0 - ild
            right_filter[0] = 1.0 + ild
        
        # Apply some frequency-dependent filtering based on elevation
        # Higher elevations have more high-frequency attenuation
        for i in range(num_taps):
            # Simple low-pass effect for elevation
            elevation_factor = 1.0 - 0.5 * abs(elevation) / 90.0
            left_filter[i] *= elevation_factor
            right_filter[i] *= elevation_factor
        
        return left_filter, right_filter
    
    async def set_settings(self, settings: SpatialSettings) -> bool:
        """Set spatial audio settings"""
        try:
            self._settings = SpatialSettings.from_dict(settings.to_dict())
            
            # Notify listeners
            for listener in self._event_listeners:
                try:
                    await listener("settings_changed", settings.to_dict())
                except Exception as e:
                    logger.error(f"Event listener error: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set spatial settings: {e}")
            return False
    
    async def get_settings(self) -> SpatialSettings:
        """Get current spatial audio settings"""
        return self._settings.copy()
    
    async def set_listener_position(self, position: Tuple[float, float, float]) -> None:
        """Set listener position"""
        self._listener.position = position
    
    async def set_listener_orientation(self, orientation: Tuple[float, float, float]) -> None:
        """Set listener orientation (yaw, pitch, roll in degrees)"""
        self._listener.orientation = orientation
    
    async def add_sound_source(self, source: SoundSource) -> bool:
        """Add a sound source"""
        try:
            self._sound_sources[source.id] = source
            
            # Notify listeners
            for listener in self._event_listeners:
                try:
                    await listener("source_added", source.to_dict())
                except Exception as e:
                    logger.error(f"Event listener error: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add sound source: {e}")
            return False
    
    async def remove_sound_source(self, source_id: str) -> bool:
        """Remove a sound source"""
        try:
            if source_id in self._sound_sources:
                del self._sound_sources[source_id]
                
                # Notify listeners
                for listener in self._event_listeners:
                    try:
                        await listener("source_removed", {"id": source_id})
                    except Exception as e:
                        logger.error(f"Event listener error: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove sound source: {e}")
            return False
    
    async def update_sound_source_position(
        self, 
        source_id: str, 
        position: Tuple[float, float, float]
    ) -> bool:
        """Update sound source position"""
        try:
            if source_id in self._sound_sources:
                self._sound_sources[source_id].position = position
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update sound source position: {e}")
            return False
    
    async def process_audio(
        self, 
        audio: np.ndarray, 
        sample_rate: int, 
        channel_type: ChannelType
    ) -> np.ndarray:
        """
        Process audio through spatial audio effects.
        
        Args:
            audio: Input audio (mono)
            sample_rate: Sample rate in Hz
            channel_type: Channel type
        
        Returns:
            Processed stereo audio (2 channels)
        """
        try:
            if not self._settings.enabled:
                # Return stereo version of input
                return np.vstack([audio, audio]).T
            
            if len(audio) == 0:
                return np.array([]).reshape(0, 2)
            
            # Get the sound source for this channel
            source = None
            for s in self._sound_sources.values():
                if s.channel_type == channel_type:
                    source = s
                    break
            
            if not source:
                # No spatial positioning, return stereo
                return np.vstack([audio, audio]).T
            
            # Calculate relative position to listener
            rel_x = source.position[0] - self._listener.position[0]
            rel_y = source.position[1] - self._listener.position[1]
            rel_z = source.position[2] - self._listener.position[2]
            
            # Convert to spherical coordinates
            distance = math.sqrt(rel_x ** 2 + rel_y ** 2 + rel_z ** 2)
            
            if distance == 0:
                distance = 0.001  # Avoid division by zero
            
            azimuth = math.degrees(math.atan2(rel_y, rel_x))
            elevation = math.degrees(math.asin(rel_z / distance))
            
            # Normalize azimuth to 0-360
            azimuth = azimuth % 360
            
            # Apply distance attenuation
            if source.distance_attenuation:
                # Inverse square law with minimum distance
                min_distance = 0.1
                attenuation = min_distance / max(distance, min_distance)
                audio = audio * attenuation * source.volume
            else:
                audio = audio * source.volume
            
            # Get HRTF filters for this position
            left_filter, right_filter = self._get_hrtf_filters(azimuth, elevation)
            
            # Apply HRTF filters
            left_audio = np.convolve(audio, left_filter, mode='same')
            right_audio = np.convolve(audio, right_filter, mode='same')
            
            # Apply room effects
            if self._settings.reverberation > 0:
                left_audio, right_audio = self._apply_reverb(
                    left_audio, right_audio, sample_rate
                )
            
            # Stack into stereo
            stereo_audio = np.vstack([left_audio, right_audio]).T
            
            return stereo_audio
            
        except Exception as e:
            logger.error(f"Failed to process spatial audio: {e}")
            return np.vstack([audio, audio]).T
    
    def _get_hrtf_filters(self, azimuth: float, elevation: float) -> Tuple[np.ndarray, np.ndarray]:
        """Get HRTF filters for a given position"""
        # Find the closest HRTF data
        closest_az = min(
            self._hrtf_data.keys(),
            key=lambda x: abs(x[0] - azimuth) + abs(x[1] - elevation)
        )
        return self._hrtf_data[closest_az]
    
    def _apply_reverb(
        self, 
        left_audio: np.ndarray, 
        right_audio: np.ndarray, 
        sample_rate: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Apply reverberation effect"""
        try:
            # Simple comb filter for reverb
            reverb_amount = self._settings.reverberation
            room_size = self._settings.room_size
            
            # Calculate delay in samples
            delay_seconds = room_size / self.SPEED_OF_SOUND
            delay_samples = int(delay_seconds * sample_rate)
            
            if delay_samples < 1:
                delay_samples = 1
            
            # Apply comb filter
            def apply_comb(audio: np.ndarray, delay: int, feedback: float) -> np.ndarray:
                output = np.zeros_like(audio)
                buffer = np.zeros(delay)
                
                for i in range(len(audio)):
                    output[i] = audio[i] + buffer[i % delay] * feedback
                    buffer[i % delay] = audio[i] + buffer[i % delay] * feedback
                
                return output
            
            feedback = 0.7  # Feedback amount
            
            left_reverb = apply_comb(left_audio, delay_samples, feedback)
            right_reverb = apply_comb(right_audio, delay_samples * 2, feedback)
            
            # Mix dry and wet signals
            left_audio = left_audio * (1 - reverb_amount) + left_reverb * reverb_amount
            right_audio = right_audio * (1 - reverb_amount) + right_reverb * reverb_amount
            
            return left_audio, right_audio
            
        except Exception as e:
            logger.error(f"Failed to apply reverb: {e}")
            return left_audio, right_audio
    
    async def enable_spatial_for_channel(
        self, 
        channel_type: ChannelType, 
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    ) -> bool:
        """Enable spatial audio for a specific channel"""
        try:
            # Create a sound source for this channel
            source = SoundSource(
                id=f"spatial-{channel_type.name.lower()}",
                channel_type=channel_type,
                position=position,
            )
            
            await self.add_sound_source(source)
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable spatial for channel: {e}")
            return False
    
    async def disable_spatial_for_channel(self, channel_type: ChannelType) -> bool:
        """Disable spatial audio for a specific channel"""
        try:
            source_id = f"spatial-{channel_type.name.lower()}"
            if source_id in self._sound_sources:
                await self.remove_sound_source(source_id)
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable spatial for channel: {e}")
            return False
    
    async def set_channel_position(
        self, 
        channel_type: ChannelType, 
        position: Tuple[float, float, float]
    ) -> bool:
        """Set the position of a channel in 3D space"""
        try:
            source_id = f"spatial-{channel_type.name.lower()}"
            if source_id in self._sound_sources:
                await self.update_sound_source_position(source_id, position)
                return True
            
            # If source doesn't exist, create it
            return await self.enable_spatial_for_channel(channel_type, position)
            
        except Exception as e:
            logger.error(f"Failed to set channel position: {e}")
            return False
    
    def add_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Add an event listener for spatial audio changes"""
        self._event_listeners.append(listener)
    
    def remove_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Remove an event listener"""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)
    
    async def get_spatial_state(self) -> Dict[str, Any]:
        """Get the current spatial audio state"""
        return {
            "settings": self._settings.to_dict(),
            "listener": self._listener.to_dict(),
            "sound_sources": {
                src_id: src.to_dict()
                for src_id, src in self._sound_sources.items()
            },
            "enabled": self._settings.enabled,
        }
