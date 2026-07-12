"""
Channel Management System

Manages the five main audio channels: Game, Chat, Media, Aux, and Microphone.
Each channel can have its own volume, effects, and routing.
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Callable, Awaitable
import uuid

from ..models.audio_device import AudioDevice, DeviceType, DeviceState
from ..models.audio_source import AudioSource, SourceType, SourceState
from ..models.preset import Preset, EQBand, EffectPreset
from .pipewire_manager import PipeWireManager
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ChannelType(Enum):
    """Channel types"""
    GAME = auto()
    CHAT = auto()
    MEDIA = auto()
    AUX = auto()
    MICROPHONE = auto()
    MASTER = auto()


@dataclass
class ChannelSettings:
    """Settings for a single channel"""
    volume: float = 1.0
    muted: bool = False
    pan: float = 0.0  # -1.0 (left) to 1.0 (right)
    eq_enabled: bool = True
    effects_enabled: bool = True
    spatial_enabled: bool = False
    preset_id: Optional[str] = None
    output_device_id: Optional[str] = None
    input_device_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "volume": self.volume,
            "muted": self.muted,
            "pan": self.pan,
            "eq_enabled": self.eq_enabled,
            "effects_enabled": self.effects_enabled,
            "spatial_enabled": self.spatial_enabled,
            "preset_id": self.preset_id,
            "output_device_id": self.output_device_id,
            "input_device_id": self.input_device_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChannelSettings":
        return cls(
            volume=data.get("volume", 1.0),
            muted=data.get("muted", False),
            pan=data.get("pan", 0.0),
            eq_enabled=data.get("eq_enabled", True),
            effects_enabled=data.get("effects_enabled", True),
            spatial_enabled=data.get("spatial_enabled", False),
            preset_id=data.get("preset_id"),
            output_device_id=data.get("output_device_id"),
            input_device_id=data.get("input_device_id"),
        )


@dataclass
class Channel:
    """
    Represents an audio channel with its sources, settings, and effects.
    
    Attributes:
        id: Unique identifier
        name: Channel name
        channel_type: Type of channel
        settings: Channel settings
        sources: List of audio sources assigned to this channel
        eq_bands: EQ bands for this channel
        effect_presets: Effect presets for this channel
        virtual_sink: Virtual sink for this channel
        virtual_source: Virtual source for this channel (for microphone)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    channel_type: ChannelType = ChannelType.GAME
    settings: ChannelSettings = field(default_factory=ChannelSettings)
    sources: List[str] = field(default_factory=list)  # List of source IDs
    eq_bands: List[EQBand] = field(default_factory=list)
    effect_presets: List[EffectPreset] = field(default_factory=list)
    virtual_sink: Optional[AudioDevice] = None
    virtual_source: Optional[AudioDevice] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.name:
            self.name = self.channel_type.name.capitalize()
    
    @property
    def is_microphone(self) -> bool:
        return self.channel_type == ChannelType.MICROPHONE
    
    @property
    def is_master(self) -> bool:
        return self.channel_type == ChannelType.MASTER
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "channel_type": self.channel_type.name,
            "settings": self.settings.to_dict(),
            "sources": self.sources,
            "eq_bands": [b.to_dict() for b in self.eq_bands],
            "effect_presets": [e.to_dict() for e in self.effect_presets],
            "virtual_sink_id": self.virtual_sink.id if self.virtual_sink else None,
            "virtual_source_id": self.virtual_source.id if self.virtual_source else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], pipewire_manager: Optional["PipeWireManager"] = None) -> "Channel":
        channel = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            channel_type=ChannelType[data.get("channel_type", "GAME")],
            settings=ChannelSettings.from_dict(data.get("settings", {})),
            sources=data.get("sources", []),
            eq_bands=[EQBand.from_dict(b) for b in data.get("eq_bands", [])],
            effect_presets=[EffectPreset.from_dict(e) for e in data.get("effect_presets", [])],
        )
        
        # Load virtual devices if PipeWire manager is provided
        if pipewire_manager:
            asyncio.create_task(channel._load_virtual_devices(pipewire_manager))
        
        return channel
    
    async def _load_virtual_devices(self, pipewire_manager: "PipeWireManager") -> None:
        """Load virtual devices for this channel"""
        sink_name = f"lsm-{self.name.lower()}-sink"
        source_name = f"lsm-{self.name.lower()}-source"
        
        self.virtual_sink = await pipewire_manager.get_device_by_name(sink_name)
        self.virtual_source = await pipewire_manager.get_device_by_name(source_name)
    
    async def create_virtual_devices(self, pipewire_manager: "PipeWireManager") -> bool:
        """Create virtual devices for this channel"""
        try:
            sink_name = f"lsm-{self.name.lower()}-sink"
            source_name = f"lsm-{self.name.lower()}-source"
            
            # Create virtual sink for output
            self.virtual_sink = await pipewire_manager.create_virtual_sink(
                name=sink_name,
                description=f"Linux Sound Manager - {self.name} Channel"
            )
            
            if not self.virtual_sink:
                logger.error(f"Failed to create virtual sink for {self.name}")
                return False
            
            # For microphone channel, also create a virtual source
            if self.is_microphone:
                self.virtual_source = await pipewire_manager.create_virtual_source(
                    name=source_name,
                    description=f"Linux Sound Manager - {self.name} Input"
                )
                
                if not self.virtual_source:
                    logger.error(f"Failed to create virtual source for {self.name}")
                    return False
            
            logger.info(f"Created virtual devices for {self.name} channel")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create virtual devices for {self.name}: {e}")
            return False
    
    async def assign_source(self, source_id: str, pipewire_manager: "PipeWireManager") -> bool:
        """Assign an audio source to this channel"""
        try:
            # Add to sources list
            if source_id not in self.sources:
                self.sources.append(source_id)
            
            # Move the source to this channel's virtual sink
            if self.virtual_sink:
                return await pipewire_manager.move_source_to_channel(
                    source_id, 
                    self.virtual_sink.name
                )
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to assign source {source_id} to {self.name}: {e}")
            return False
    
    async def remove_source(self, source_id: str, pipewire_manager: "PipeWireManager") -> bool:
        """Remove an audio source from this channel"""
        try:
            if source_id in self.sources:
                self.sources.remove(source_id)
            
            # Disconnect the source from this channel
            # (Implementation depends on how we track connections)
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove source {source_id} from {self.name}: {e}")
            return False
    
    async def set_volume(self, volume: float, pipewire_manager: "PipeWireManager") -> bool:
        """Set channel volume (0.0 to 1.0)"""
        try:
            self.settings.volume = max(0.0, min(1.0, volume))
            
            # Apply to virtual sink
            if self.virtual_sink:
                node = await pipewire_manager.get_node_by_name(self.virtual_sink.name)
                if node:
                    return await pipewire_manager.set_volume(node.id, self.settings.volume)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set volume for {self.name}: {e}")
            return False
    
    async def set_mute(self, muted: bool, pipewire_manager: "PipeWireManager") -> bool:
        """Set channel mute state"""
        try:
            self.settings.muted = muted
            
            if self.virtual_sink:
                node = await pipewire_manager.get_node_by_name(self.virtual_sink.name)
                if node:
                    return await pipewire_manager.set_mute(node.id, muted)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set mute for {self.name}: {e}")
            return False
    
    async def apply_preset(self, preset: Preset) -> None:
        """Apply a preset to this channel"""
        try:
            self.settings.preset_id = preset.id
            
            # Apply EQ bands
            if preset.preset_type in (PresetType.EQ, PresetType.COMPLETE):
                self.eq_bands = [EQBand.from_dict(b.to_dict()) for b in preset.eq_bands]
            
            # Apply effect presets
            if preset.preset_type in (PresetType.EFFECT, PresetType.COMPLETE):
                self.effect_presets = [EffectPreset.from_dict(e.to_dict()) for e in preset.effect_presets]
            
            # Apply channel-specific settings if present
            if self.name.lower() in preset.channel_settings:
                channel_settings = preset.channel_settings[self.name.lower()]
                for key, value in channel_settings.items():
                    if hasattr(self.settings, key):
                        setattr(self.settings, key, value)
            
            logger.info(f"Applied preset '{preset.name}' to {self.name} channel")
            
        except Exception as e:
            logger.error(f"Failed to apply preset to {self.name}: {e}")


class ChannelManager:
    """
    Manages all audio channels and their interactions.
    
    Provides functionality for:
    - Creating and managing the five main channels
    - Assigning sources to channels
    - Managing channel settings
    - Routing audio between channels
    """
    
    # Default channel names
    DEFAULT_CHANNELS = {
        ChannelType.GAME: "Game",
        ChannelType.CHAT: "Chat",
        ChannelType.MEDIA: "Media",
        ChannelType.AUX: "Aux",
        ChannelType.MICROPHONE: "Microphone",
        ChannelType.MASTER: "Master",
    }
    
    def __init__(self, pipewire_manager: PipeWireManager):
        self._pipewire_manager = pipewire_manager
        self._channels: Dict[ChannelType, Channel] = {}
        self._sources: Dict[str, str] = {}  # source_id -> channel_id
        self._initialized = False
        self._event_listeners: List[Callable[[str, Any], Awaitable[None]]] = []
        
    async def initialize(self) -> bool:
        """Initialize channel manager and create default channels"""
        try:
            # Create default channels
            for channel_type, name in self.DEFAULT_CHANNELS.items():
                channel = Channel(
                    name=name,
                    channel_type=channel_type,
                )
                self._channels[channel_type] = channel
            
            # Create virtual devices for each channel
            for channel in self._channels.values():
                if not channel.is_master:  # Master doesn't need virtual devices
                    await channel.create_virtual_devices(self._pipewire_manager)
            
            self._initialized = True
            logger.info("Channel manager initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize channel manager: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown channel manager"""
        self._initialized = False
        logger.info("Channel manager shutdown")
    
    def get_channel(self, channel_type: ChannelType) -> Optional[Channel]:
        """Get a channel by type"""
        return self._channels.get(channel_type)
    
    def get_all_channels(self) -> List[Channel]:
        """Get all channels"""
        return list(self._channels.values())
    
    async def assign_source_to_channel(
        self, 
        source_id: str, 
        channel_type: ChannelType
    ) -> bool:
        """
        Assign an audio source to a specific channel.
        
        Args:
            source_id: ID of the audio source
            channel_type: Target channel type
        
        Returns:
            True if assignment was successful
        """
        try:
            channel = self.get_channel(channel_type)
            if not channel:
                logger.error(f"Channel {channel_type.name} not found")
                return False
            
            # Remove from previous channel if assigned
            if source_id in self._sources:
                old_channel_type = self._sources[source_id]
                old_channel = self.get_channel(old_channel_type)
                if old_channel:
                    await old_channel.remove_source(source_id, self._pipewire_manager)
            
            # Assign to new channel
            success = await channel.assign_source(source_id, self._pipewire_manager)
            if success:
                self._sources[source_id] = channel_type.name
                
                # Notify listeners
                for listener in self._event_listeners:
                    try:
                        await listener("source_assigned", {
                            "source_id": source_id,
                            "channel_type": channel_type.name
                        })
                    except Exception as e:
                        logger.error(f"Event listener error: {e}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to assign source to channel: {e}")
            return False
    
    async def get_source_channel(self, source_id: str) -> Optional[ChannelType]:
        """Get the channel a source is assigned to"""
        channel_name = self._sources.get(source_id)
        if channel_name:
            for channel_type, name in self.DEFAULT_CHANNELS.items():
                if name == channel_name:
                    return channel_type
        return None
    
    async def set_channel_volume(self, channel_type: ChannelType, volume: float) -> bool:
        """Set volume for a channel"""
        channel = self.get_channel(channel_type)
        if not channel:
            return False
        return await channel.set_volume(volume, self._pipewire_manager)
    
    async def set_channel_mute(self, channel_type: ChannelType, muted: bool) -> bool:
        """Set mute state for a channel"""
        channel = self.get_channel(channel_type)
        if not channel:
            return False
        return await channel.set_mute(muted, self._pipewire_manager)
    
    async def apply_preset_to_channel(
        self, 
        preset: Preset, 
        channel_type: ChannelType
    ) -> None:
        """Apply a preset to a specific channel"""
        channel = self.get_channel(channel_type)
        if channel:
            await channel.apply_preset(preset)
    
    async def get_sources_in_channel(self, channel_type: ChannelType) -> List[AudioSource]:
        """Get all sources assigned to a channel"""
        channel = self.get_channel(channel_type)
        if not channel:
            return []
        
        sources = []
        for source_id in channel.sources:
            # Get source from PipeWire manager
            all_sources = await self._pipewire_manager.get_sources()
            for source in all_sources:
                if source.id == source_id:
                    sources.append(source)
                    break
        
        return sources
    
    async def move_source_between_channels(
        self, 
        source_id: str, 
        from_channel: ChannelType, 
        to_channel: ChannelType
    ) -> bool:
        """Move a source from one channel to another"""
        # First remove from old channel
        old_channel = self.get_channel(from_channel)
        if old_channel:
            await old_channel.remove_source(source_id, self._pipewire_manager)
        
        # Then assign to new channel
        return await self.assign_source_to_channel(source_id, to_channel)
    
    def add_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Add an event listener for channel changes"""
        self._event_listeners.append(listener)
    
    def remove_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Remove an event listener"""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)
    
    async def get_master_channel(self) -> Optional[Channel]:
        """Get the master channel"""
        return self.get_channel(ChannelType.MASTER)
    
    async def set_master_volume(self, volume: float) -> bool:
        """Set master volume"""
        master = await self.get_master_channel()
        if master:
            return await master.set_volume(volume, self._pipewire_manager)
        return False
    
    async def refresh_sources(self) -> None:
        """Refresh the list of sources from PipeWire"""
        try:
            all_sources = await self._pipewire_manager.get_sources()
            
            # Update source assignments
            for source in all_sources:
                if source.id not in self._sources:
                    # New source, assign to default channel based on type
                    default_channel = self._get_default_channel_for_source(source)
                    if default_channel:
                        await self.assign_source_to_channel(source.id, default_channel)
            
            # Remove sources that no longer exist
            existing_source_ids = {s.id for s in all_sources}
            for source_id in list(self._sources.keys()):
                if source_id not in existing_source_ids:
                    del self._sources[source_id]
            
        except Exception as e:
            logger.error(f"Failed to refresh sources: {e}")
    
    def _get_default_channel_for_source(self, source: AudioSource) -> Optional[ChannelType]:
        """Get the default channel for a source based on its type"""
        if source.is_microphone:
            return ChannelType.MICROPHONE
        
        # Try to match by application name
        app_name = source.name.lower() if source.name else ""
        
        if any(game_keyword in app_name for game_keyword in ["game", "wine", "steam", "lutris"]):
            return ChannelType.GAME
        elif any(chat_keyword in app_name for chat_keyword in ["discord", "teamspeak", "mumble", "zoom", "skype"]):
            return ChannelType.CHAT
        elif any(media_keyword in app_name for media_keyword in ["spotify", "vlc", "mpv", "firefox", "chrome", "browser"]):
            return ChannelType.MEDIA
        
        # Default to Game for applications
        if source.is_application:
            return ChannelType.GAME
        
        return None
