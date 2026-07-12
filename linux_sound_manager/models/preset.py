"""
Preset Model - EQ and effect presets
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any
import uuid
import math


class PresetType(Enum):
    """Types of presets"""
    EQ = auto()              # Equalizer preset
    EFFECT = auto()          # Effect preset (noise gate, compressor, etc.)
    SPATIAL = auto()         # Spatial audio preset
    COMPLETE = auto()        # Complete profile (EQ + effects + spatial)


class EQType(Enum):
    """EQ band types"""
    PEAKING = auto()         # Peaking filter
    LOW_SHELF = auto()       # Low shelf
    HIGH_SHELF = auto()      # High shelf
    LOW_PASS = auto()        # Low pass
    HIGH_PASS = auto()       # High pass
    NOTCH = auto()           # Notch filter
    BAND_PASS = auto()       # Band pass


@dataclass
class EQBand:
    """
    Represents a single EQ band
    
    For parametric EQ:
    - frequency: Center frequency in Hz
    - gain: Gain in dB (-20 to +20)
    - q_factor: Quality factor (0.1 to 10)
    - type: Band type
    
    For graphic EQ:
    - frequency: Center frequency
    - gain: Gain in dB
    - q_factor: Fixed based on band spacing
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    frequency: float = 1000.0  # Hz
    gain: float = 0.0         # dB
    q_factor: float = 1.0     # Quality factor
    eq_type: EQType = EQType.PEAKING
    enabled: bool = True
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        # Clamp values
        self.frequency = max(20.0, min(20000.0, self.frequency))
        self.gain = max(-20.0, min(20.0, self.gain))
        self.q_factor = max(0.1, min(10.0, self.q_factor))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frequency": self.frequency,
            "gain": self.gain,
            "q_factor": self.q_factor,
            "eq_type": self.eq_type.name,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EQBand":
        band = cls()
        band.id = data.get("id", str(uuid.uuid4()))
        band.frequency = data.get("frequency", 1000.0)
        band.gain = data.get("gain", 0.0)
        band.q_factor = data.get("q_factor", 1.0)
        band.eq_type = EQType[data.get("eq_type", "PEAKING")]
        band.enabled = data.get("enabled", True)
        return band


@dataclass
class EffectPreset:
    """
    Preset for audio effects (Noise Gate, Compressor, etc.)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    effect_type: str = ""  # "noise_gate", "compressor", "limiter", etc.
    parameters: Dict[str, float] = field(default_factory=dict)
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "effect_type": self.effect_type,
            "parameters": self.parameters,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EffectPreset":
        preset = cls()
        preset.id = data.get("id", str(uuid.uuid4()))
        preset.name = data.get("name", "")
        preset.effect_type = data.get("effect_type", "")
        preset.parameters = data.get("parameters", {})
        preset.enabled = data.get("enabled", True)
        return preset


@dataclass
class Preset:
    """
    Audio preset containing EQ bands and effect settings
    
    Attributes:
        id: Unique identifier
        name: Preset name
        description: Description
        preset_type: Type of preset
        eq_bands: List of EQ bands (for EQ presets)
        effect_presets: List of effect presets
        spatial_settings: Spatial audio settings
        channel_settings: Per-channel settings
        is_factory: Whether this is a factory preset
        tags: Tags for categorization
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    preset_type: PresetType = PresetType.EQ
    eq_bands: List[EQBand] = field(default_factory=list)
    effect_presets: List[EffectPreset] = field(default_factory=list)
    spatial_settings: Dict[str, Any] = field(default_factory=dict)
    channel_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    is_factory: bool = False
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "preset_type": self.preset_type.name,
            "eq_bands": [b.to_dict() for b in self.eq_bands],
            "effect_presets": [e.to_dict() for e in self.effect_presets],
            "spatial_settings": self.spatial_settings,
            "channel_settings": self.channel_settings,
            "is_factory": self.is_factory,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Preset":
        preset = cls()
        preset.id = data.get("id", str(uuid.uuid4()))
        preset.name = data.get("name", "")
        preset.description = data.get("description", "")
        preset.preset_type = PresetType[data.get("preset_type", "EQ")]
        preset.eq_bands = [EQBand.from_dict(b) for b in data.get("eq_bands", [])]
        preset.effect_presets = [EffectPreset.from_dict(e) for e in data.get("effect_presets", [])]
        preset.spatial_settings = data.get("spatial_settings", {})
        preset.channel_settings = data.get("channel_settings", {})
        preset.is_factory = data.get("is_factory", False)
        preset.tags = data.get("tags", [])
        return preset
    
    @classmethod
    def create_default_eq_preset(cls, name: str = "Flat") -> "Preset":
        """Create a default flat EQ preset"""
        # Standard 10-band EQ frequencies (ISO standard)
        frequencies = [31, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
        eq_bands = [
            EQBand(frequency=f, gain=0.0, q_factor=1.0, eq_type=EQType.PEAKING)
            for f in frequencies
        ]
        return cls(
            name=name,
            description="Flat EQ response",
            preset_type=PresetType.EQ,
            eq_bands=eq_bands,
            is_factory=True,
            tags=["eq", "flat", "default"]
        )
    
    @classmethod
    def create_gaming_preset(cls) -> "Preset":
        """Create a gaming-focused EQ preset (enhances footstep frequencies)"""
        frequencies = [31, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
        # Boost low-mid for footsteps, reduce highs for clarity
        gains = [2.0, 3.0, 2.5, 1.5, 0.0, -1.0, -2.0, -1.5, -1.0, 0.0]
        eq_bands = [
            EQBand(frequency=f, gain=g, q_factor=1.2, eq_type=EQType.PEAKING)
            for f, g in zip(frequencies, gains)
        ]
        return cls(
            name="Gaming",
            description="Enhances footstep and low-frequency sounds for competitive gaming",
            preset_type=PresetType.EQ,
            eq_bands=eq_bands,
            is_factory=True,
            tags=["eq", "gaming", "footsteps"]
        )
