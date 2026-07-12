"""
Audio Source Model - Represents an application or input source
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any
import uuid


class SourceType(Enum):
    """Types of audio sources"""
    APPLICATION = auto()  # Application producing audio
    SYSTEM = auto()       # System sounds
    MICROPHONE = auto()   # Microphone input
    MEDIA = auto()        # Media playback
    GAME = auto()         # Game audio
    CHAT = auto()         # Chat/VoIP audio
    AUX = auto()          # Auxiliary input


class SourceState(Enum):
    """Source state"""
    ACTIVE = auto()
    INACTIVE = auto()
    MUTED = auto()
    PAUSED = auto()


@dataclass
class AudioSource:
    """
    Represents an audio source (application, microphone, etc.)
    
    Attributes:
        id: Unique identifier
        name: Human-readable name
        source_type: Type of source
        application_id: For application sources, the app identifier
        process_id: Process ID for application sources
        channel_id: Which channel this source is assigned to
        volume: Source volume (0.0 to 1.0)
        muted: Whether source is muted
        state: Current state
        peak_level: Current audio level (0.0 to 1.0)
        properties: Additional properties
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    source_type: SourceType = SourceType.APPLICATION
    application_id: Optional[str] = None
    process_id: Optional[int] = None
    channel_id: Optional[str] = None
    volume: float = 1.0
    muted: bool = False
    state: SourceState = SourceState.INACTIVE
    peak_level: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def is_application(self) -> bool:
        return self.source_type == SourceType.APPLICATION
    
    @property
    def is_microphone(self) -> bool:
        return self.source_type == SourceType.MICROPHONE
    
    @property
    def is_active(self) -> bool:
        return self.state == SourceState.ACTIVE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "source_type": self.source_type.name,
            "application_id": self.application_id,
            "process_id": self.process_id,
            "channel_id": self.channel_id,
            "volume": self.volume,
            "muted": self.muted,
            "state": self.state.name,
            "peak_level": self.peak_level,
            "properties": self.properties,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioSource":
        """Create from dictionary"""
        source = cls()
        source.id = data.get("id", str(uuid.uuid4()))
        source.name = data.get("name", "")
        source.source_type = SourceType[data.get("source_type", "APPLICATION")]
        source.application_id = data.get("application_id")
        source.process_id = data.get("process_id")
        source.channel_id = data.get("channel_id")
        source.volume = data.get("volume", 1.0)
        source.muted = data.get("muted", False)
        source.state = SourceState[data.get("state", "INACTIVE")]
        source.peak_level = data.get("peak_level", 0.0)
        source.properties = data.get("properties", {})
        return source
