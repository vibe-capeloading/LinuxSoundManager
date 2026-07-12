"""
Audio Device Model
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any
import uuid


class DeviceType(Enum):
    """Types of audio devices"""
    INPUT = auto()      # Microphone, line-in
    OUTPUT = auto()     # Headphones, speakers
    VIRTUAL = auto()    # Virtual devices (PipeWire sinks/sources)
    MONITOR = auto()    # Monitor of output devices


class DeviceState(Enum):
    """Device connection state"""
    CONNECTED = auto()
    DISCONNECTED = auto()
    SUSPENDED = auto()


@dataclass
class AudioDevice:
    """
    Represents an audio device in the system.
    
    Attributes:
        id: Unique identifier
        name: Human-readable name
        description: Detailed description
        device_type: Type of device (INPUT, OUTPUT, VIRTUAL, MONITOR)
        index: ALSA/PipeWire index
        api: API used (alsa, pipewire, pulseaudio)
        state: Current connection state
        volume: Current volume (0.0 to 1.0)
        muted: Whether device is muted
        latency: Current latency in ms
        sample_rate: Current sample rate
        channels: Number of channels
        format: Audio format
        properties: Additional properties
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    device_type: DeviceType = DeviceType.VIRTUAL
    index: int = -1
    api: str = "pipewire"
    state: DeviceState = DeviceState.DISCONNECTED
    volume: float = 1.0
    muted: bool = False
    latency: float = 0.0
    sample_rate: int = 48000
    channels: int = 2
    format: str = "S16LE"
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def is_input(self) -> bool:
        return self.device_type in (DeviceType.INPUT, DeviceType.MONITOR)
    
    @property
    def is_output(self) -> bool:
        return self.device_type in (DeviceType.OUTPUT, DeviceType.VIRTUAL)
    
    @property
    def is_virtual(self) -> bool:
        return self.device_type == DeviceType.VIRTUAL
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "device_type": self.device_type.name,
            "index": self.index,
            "api": self.api,
            "state": self.state.name,
            "volume": self.volume,
            "muted": self.muted,
            "latency": self.latency,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "format": self.format,
            "properties": self.properties,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioDevice":
        """Create from dictionary"""
        device = cls()
        device.id = data.get("id", str(uuid.uuid4()))
        device.name = data.get("name", "")
        device.description = data.get("description", "")
        device.device_type = DeviceType[data.get("device_type", "VIRTUAL")]
        device.index = data.get("index", -1)
        device.api = data.get("api", "pipewire")
        device.state = DeviceState[data.get("state", "DISCONNECTED")]
        device.volume = data.get("volume", 1.0)
        device.muted = data.get("muted", False)
        device.latency = data.get("latency", 0.0)
        device.sample_rate = data.get("sample_rate", 48000)
        device.channels = data.get("channels", 2)
        device.format = data.get("format", "S16LE")
        device.properties = data.get("properties", {})
        return device
