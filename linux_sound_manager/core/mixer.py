"""
Audio Mixer - Manages audio routing and mixing between channels

This module provides the core mixing functionality, allowing audio to be
routed between channels, mixed, and processed.
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Tuple, Callable, Awaitable
import math
import numpy as np

from ..models.audio_device import AudioDevice, DeviceType
from ..models.audio_source import AudioSource, SourceType
from .channels import ChannelManager, Channel, ChannelType
from .pipewire_manager import PipeWireManager
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MixerMode(Enum):
    """Mixer operating modes"""
    STEREO = auto()      # Standard stereo mixing
    SURROUND = auto()    # Surround sound mixing
    SPATIAL = auto()     # Spatial audio mixing
    CUSTOM = auto()      # Custom routing matrix


@dataclass
class RoutingRule:
    """
    Defines how audio should be routed between channels.
    
    Attributes:
        source_channel: Source channel type
        target_channel: Target channel type
        volume: Routing volume (0.0 to 1.0)
        pan: Pan position (-1.0 to 1.0)
        enabled: Whether this rule is active
    """
    source_channel: ChannelType
    target_channel: ChannelType
    volume: float = 1.0
    pan: float = 0.0
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_channel": self.source_channel.name,
            "target_channel": self.target_channel.name,
            "volume": self.volume,
            "pan": self.pan,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoutingRule":
        return cls(
            source_channel=ChannelType[data["source_channel"]],
            target_channel=ChannelType[data["target_channel"]],
            volume=data.get("volume", 1.0),
            pan=data.get("pan", 0.0),
            enabled=data.get("enabled", True),
        )


@dataclass
class MixerSettings:
    """Settings for the audio mixer"""
    mode: MixerMode = MixerMode.STEREO
    master_volume: float = 1.0
    master_muted: bool = False
    routing_rules: List[RoutingRule] = field(default_factory=list)
    crossfade_enabled: bool = False
    crossfade_duration: float = 0.5  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.name,
            "master_volume": self.master_volume,
            "master_muted": self.master_muted,
            "routing_rules": [r.to_dict() for r in self.routing_rules],
            "crossfade_enabled": self.crossfade_enabled,
            "crossfade_duration": self.crossfade_duration,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MixerSettings":
        return cls(
            mode=MixerMode[data.get("mode", "STEREO")],
            master_volume=data.get("master_volume", 1.0),
            master_muted=data.get("master_muted", False),
            routing_rules=[RoutingRule.from_dict(r) for r in data.get("routing_rules", [])],
            crossfade_enabled=data.get("crossfade_enabled", False),
            crossfade_duration=data.get("crossfade_duration", 0.5),
        )


class AudioMixer:
    """
    Manages audio mixing and routing between channels.
    
    Provides functionality for:
    - Routing audio between channels
    - Mixing multiple audio streams
    - Applying volume and pan controls
    - Managing the master output
    """
    
    def __init__(
        self, 
        pipewire_manager: PipeWireManager,
        channel_manager: ChannelManager
    ):
        self._pipewire_manager = pipewire_manager
        self._channel_manager = channel_manager
        self._settings = MixerSettings()
        self._routing_matrix: Dict[Tuple[ChannelType, ChannelType], float] = {}
        self._event_listeners: List[Callable[[str, Any], Awaitable[None]]] = []
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the audio mixer"""
        try:
            # Set up default routing
            await self._setup_default_routing()
            
            self._initialized = True
            logger.info("Audio mixer initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize audio mixer: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the audio mixer"""
        self._initialized = False
        logger.info("Audio mixer shutdown")
    
    async def _setup_default_routing(self) -> None:
        """Set up default routing between channels"""
        # By default, all channels route to Master
        for channel_type in ChannelType:
            if channel_type != ChannelType.MASTER:
                rule = RoutingRule(
                    source_channel=channel_type,
                    target_channel=ChannelType.MASTER,
                    volume=1.0,
                    pan=0.0,
                    enabled=True
                )
                self._settings.routing_rules.append(rule)
                self._routing_matrix[(channel_type, ChannelType.MASTER)] = 1.0
    
    async def set_master_volume(self, volume: float) -> bool:
        """Set the master volume (0.0 to 1.0)"""
        try:
            self._settings.master_volume = max(0.0, min(1.0, volume))
            
            # Apply to master channel
            master_channel = await self._channel_manager.get_master_channel()
            if master_channel and master_channel.virtual_sink:
                node = await self._pipewire_manager.get_node_by_name(master_channel.virtual_sink.name)
                if node:
                    return await self._pipewire_manager.set_volume(
                        node.id, 
                        self._settings.master_volume
                    )
            
            # Notify listeners
            for listener in self._event_listeners:
                try:
                    await listener("master_volume_changed", {"volume": self._settings.master_volume})
                except Exception as e:
                    logger.error(f"Event listener error: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set master volume: {e}")
            return False
    
    async def set_master_mute(self, muted: bool) -> bool:
        """Set the master mute state"""
        try:
            self._settings.master_muted = muted
            
            master_channel = await self._channel_manager.get_master_channel()
            if master_channel and master_channel.virtual_sink:
                node = await self._pipewire_manager.get_node_by_name(master_channel.virtual_sink.name)
                if node:
                    return await self._pipewire_manager.set_mute(node.id, muted)
            
            for listener in self._event_listeners:
                try:
                    await listener("master_mute_changed", {"muted": self._settings.master_muted})
                except Exception as e:
                    logger.error(f"Event listener error: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set master mute: {e}")
            return False
    
    async def add_routing_rule(self, rule: RoutingRule) -> bool:
        """Add a routing rule"""
        try:
            # Check if rule already exists
            for existing_rule in self._settings.routing_rules:
                if (existing_rule.source_channel == rule.source_channel and 
                    existing_rule.target_channel == rule.target_channel):
                    # Update existing rule
                    existing_rule.volume = rule.volume
                    existing_rule.pan = rule.pan
                    existing_rule.enabled = rule.enabled
                    return True
            
            # Add new rule
            self._settings.routing_rules.append(rule)
            self._routing_matrix[(rule.source_channel, rule.target_channel)] = rule.volume
            
            # Apply the routing
            await self._apply_routing()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add routing rule: {e}")
            return False
    
    async def remove_routing_rule(
        self, 
        source_channel: ChannelType, 
        target_channel: ChannelType
    ) -> bool:
        """Remove a routing rule"""
        try:
            # Remove from settings
            self._settings.routing_rules = [
                r for r in self._settings.routing_rules
                if not (r.source_channel == source_channel and 
                        r.target_channel == target_channel)
            ]
            
            # Remove from matrix
            if (source_channel, target_channel) in self._routing_matrix:
                del self._routing_matrix[(source_channel, target_channel)]
            
            # Apply the routing
            await self._apply_routing()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove routing rule: {e}")
            return False
    
    async def _apply_routing(self) -> None:
        """Apply the current routing configuration"""
        try:
            # For each routing rule, set up the connections in PipeWire
            for rule in self._settings.routing_rules:
                if not rule.enabled:
                    continue
                
                source_channel = self._channel_manager.get_channel(rule.source_channel)
                target_channel = self._channel_manager.get_channel(rule.target_channel)
                
                if source_channel and target_channel:
                    if source_channel.virtual_sink and target_channel.virtual_sink:
                        # Connect source sink to target sink
                        await self._pipewire_manager.connect_source_to_sink(
                            source_channel.virtual_sink.name,
                            target_channel.virtual_sink.name
                        )
            
            logger.info("Applied routing configuration")
            
        except Exception as e:
            logger.error(f"Failed to apply routing: {e}")
    
    async def set_channel_volume_in_mix(
        self, 
        channel_type: ChannelType, 
        volume: float
    ) -> bool:
        """Set the volume of a channel in the mix"""
        try:
            volume = max(0.0, min(1.0, volume))
            
            # Update all routing rules involving this channel as source
            for rule in self._settings.routing_rules:
                if rule.source_channel == channel_type:
                    rule.volume = volume
            
            # Update routing matrix
            for key in list(self._routing_matrix.keys()):
                if key[0] == channel_type:
                    self._routing_matrix[key] = volume
            
            # Apply the routing
            await self._apply_routing()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set channel volume in mix: {e}")
            return False
    
    async def get_mix_levels(self) -> Dict[ChannelType, float]:
        """Get the current mix levels for all channels"""
        levels = {}
        
        for channel_type in ChannelType:
            if channel_type == ChannelType.MASTER:
                continue
            
            channel = self._channel_manager.get_channel(channel_type)
            if channel:
                # Get the volume from the channel settings
                levels[channel_type] = channel.settings.volume
        
        return levels
    
    async def crossfade_between_channels(
        self, 
        from_channel: ChannelType, 
        to_channel: ChannelType, 
        duration: float = 0.5
    ) -> bool:
        """
        Crossfade audio from one channel to another.
        
        Gradually reduces volume on the source channel while increasing
        volume on the target channel.
        """
        try:
            if not self._settings.crossfade_enabled:
                # Just switch immediately
                from_channel_obj = self._channel_manager.get_channel(from_channel)
                to_channel_obj = self._channel_manager.get_channel(to_channel)
                
                if from_channel_obj and to_channel_obj:
                    # Move all sources from from_channel to to_channel
                    for source_id in from_channel_obj.sources[:]:
                        await self._channel_manager.assign_source_to_channel(
                            source_id, 
                            to_channel
                        )
                
                return True
            
            # Perform crossfade
            steps = 20
            step_duration = duration / steps
            
            from_vol = 1.0
            to_vol = 0.0
            
            for i in range(steps + 1):
                # Calculate volumes
                from_vol = 1.0 - (i / steps)
                to_vol = i / steps
                
                # Set volumes
                await self.set_channel_volume_in_mix(from_channel, from_vol)
                await self.set_channel_volume_in_mix(to_channel, to_vol)
                
                await asyncio.sleep(step_duration)
            
            # Move sources
            from_channel_obj = self._channel_manager.get_channel(from_channel)
            to_channel_obj = self._channel_manager.get_channel(to_channel)
            
            if from_channel_obj and to_channel_obj:
                for source_id in from_channel_obj.sources[:]:
                    await self._channel_manager.assign_source_to_channel(
                        source_id, 
                        to_channel
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to crossfade between channels: {e}")
            return False
    
    async def mix_audio_streams(
        self, 
        streams: Dict[ChannelType, np.ndarray]
    ) -> np.ndarray:
        """
        Mix multiple audio streams together.
        
        This is a software mixing function that can be used for
        processing audio before sending to PipeWire.
        
        Args:
            streams: Dictionary of channel type to audio stream (numpy array)
        
        Returns:
            Mixed audio stream
        """
        try:
            # Find the maximum length
            max_length = max(len(stream) for stream in streams.values()) if streams else 0
            
            if max_length == 0:
                return np.array([])
            
            # Initialize output
            output = np.zeros(max_length, dtype=np.float32)
            
            # Mix all streams
            for channel_type, stream in streams.items():
                # Get volume for this channel
                volume = self._routing_matrix.get(
                    (channel_type, ChannelType.MASTER), 
                    1.0
                )
                
                # Apply volume
                stream = stream * volume
                
                # Pad or truncate to match output length
                if len(stream) < max_length:
                    padded = np.zeros(max_length, dtype=np.float32)
                    padded[:len(stream)] = stream
                    stream = padded
                elif len(stream) > max_length:
                    stream = stream[:max_length]
                
                # Add to output
                output += stream
            
            # Apply master volume
            output *= self._settings.master_volume
            
            # Clamp to prevent clipping
            output = np.clip(output, -1.0, 1.0)
            
            return output
            
        except Exception as e:
            logger.error(f"Failed to mix audio streams: {e}")
            return np.array([])
    
    async def get_routing_matrix(self) -> Dict[Tuple[ChannelType, ChannelType], float]:
        """Get the current routing matrix"""
        return self._routing_matrix.copy()
    
    async def set_routing_matrix(
        self, 
        matrix: Dict[Tuple[ChannelType, ChannelType], float]
    ) -> bool:
        """Set the routing matrix"""
        try:
            self._routing_matrix = matrix.copy()
            
            # Update routing rules
            self._settings.routing_rules = []
            for (source, target), volume in matrix.items():
                rule = RoutingRule(
                    source_channel=source,
                    target_channel=target,
                    volume=volume,
                    enabled=volume > 0
                )
                self._settings.routing_rules.append(rule)
            
            # Apply the routing
            await self._apply_routing()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set routing matrix: {e}")
            return False
    
    def add_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Add an event listener for mixer changes"""
        self._event_listeners.append(listener)
    
    def remove_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Remove an event listener"""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)
    
    async def get_current_configuration(self) -> Dict[str, Any]:
        """Get the current mixer configuration"""
        return {
            "settings": self._settings.to_dict(),
            "routing_matrix": {
                f"{src.name}-{tgt.name}": vol
                for (src, tgt), vol in self._routing_matrix.items()
            },
            "channels": {
                ch.channel_type.name: {
                    "volume": ch.settings.volume,
                    "muted": ch.settings.muted,
                    "sources": len(ch.sources)
                }
                for ch in self._channel_manager.get_all_channels()
            }
        }
