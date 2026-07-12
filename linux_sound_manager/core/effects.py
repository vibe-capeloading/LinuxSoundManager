"""
Effects Manager - Manages audio effects (EQ, Noise Gate, Compressor, etc.)

This module provides audio effect processing using EasyEffects integration
and custom DSP implementations.
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Tuple, Callable, Awaitable
import math
import numpy as np
from scipy import signal

from ..models.preset import Preset, EQBand, EQType, EffectPreset, PresetType
from .channels import ChannelManager, Channel, ChannelType
from .pipewire_manager import PipeWireManager
from ..utils.logger import get_logger

logger = get_logger(__name__)


class EffectType(Enum):
    """Types of audio effects"""
    EQ = auto()              # Equalizer
    NOISE_GATE = auto()      # Noise gate
    COMPRESSOR = auto()      # Compressor
    LIMITER = auto()         # Limiter
    REVERB = auto()          # Reverb
    DELAY = auto()           # Delay
    CHORUS = auto()          # Chorus
    FLANGER = auto()         # Flanger
    PITCH_SHIFT = auto()     # Pitch shift
    CLEARCAST = auto()       # ClearCast AI noise suppression


class FilterType(Enum):
    """Types of EQ filters"""
    PEAKING = auto()
    LOW_SHELF = auto()
    HIGH_SHELF = auto()
    LOW_PASS = auto()
    HIGH_PASS = auto()
    NOTCH = auto()
    BAND_PASS = auto()


@dataclass
class EffectSettings:
    """Settings for a specific effect"""
    effect_type: EffectType
    enabled: bool = True
    parameters: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_type": self.effect_type.name,
            "enabled": self.enabled,
            "parameters": self.parameters,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EffectSettings":
        return cls(
            effect_type=EffectType[data["effect_type"]],
            enabled=data.get("enabled", True),
            parameters=data.get("parameters", {}),
        )


@dataclass
class NoiseGateSettings:
    """Settings for noise gate effect"""
    threshold: float = -40.0  # dB
    attack: float = 0.01     # seconds
    release: float = 0.1     # seconds
    hold: float = 0.05       # seconds
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "threshold": self.threshold,
            "attack": self.attack,
            "release": self.release,
            "hold": self.hold,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NoiseGateSettings":
        return cls(
            threshold=data.get("threshold", -40.0),
            attack=data.get("attack", 0.01),
            release=data.get("release", 0.1),
            hold=data.get("hold", 0.05),
            enabled=data.get("enabled", True),
        )


@dataclass
class CompressorSettings:
    """Settings for compressor effect"""
    threshold: float = -20.0  # dB
    ratio: float = 4.0       # Compression ratio
    attack: float = 0.01     # seconds
    release: float = 0.1     # seconds
    knee: float = 5.0        # dB
    makeup_gain: float = 0.0 # dB
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "threshold": self.threshold,
            "ratio": self.ratio,
            "attack": self.attack,
            "release": self.release,
            "knee": self.knee,
            "makeup_gain": self.makeup_gain,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompressorSettings":
        return cls(
            threshold=data.get("threshold", -20.0),
            ratio=data.get("ratio", 4.0),
            attack=data.get("attack", 0.01),
            release=data.get("release", 0.1),
            knee=data.get("knee", 5.0),
            makeup_gain=data.get("makeup_gain", 0.0),
            enabled=data.get("enabled", True),
        )


@dataclass
class LimiterSettings:
    """Settings for limiter effect"""
    threshold: float = -3.0   # dB
    ceiling: float = 0.0     # dB
    attack: float = 0.001    # seconds
    release: float = 0.05    # seconds
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "threshold": self.threshold,
            "ceiling": self.ceiling,
            "attack": self.attack,
            "release": self.release,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LimiterSettings":
        return cls(
            threshold=data.get("threshold", -3.0),
            ceiling=data.get("ceiling", 0.0),
            attack=data.get("attack", 0.001),
            release=data.get("release", 0.05),
            enabled=data.get("enabled", True),
        )


@dataclass
class ClearCastSettings:
    """Settings for ClearCast AI noise suppression"""
    noise_suppression_level: float = 0.8  # 0.0 to 1.0
    voice_enhancement: bool = True
    echo_cancellation: bool = True
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "noise_suppression_level": self.noise_suppression_level,
            "voice_enhancement": self.voice_enhancement,
            "echo_cancellation": self.echo_cancellation,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClearCastSettings":
        return cls(
            noise_suppression_level=data.get("noise_suppression_level", 0.8),
            voice_enhancement=data.get("voice_enhancement", True),
            echo_cancellation=data.get("echo_cancellation", True),
            enabled=data.get("enabled", True),
        )


class EffectsManager:
    """
    Manages audio effects for all channels.
    
    Provides functionality for:
    - Parametric EQ (10 bands per channel)
    - Noise gate
    - Compressor
    - Limiter
    - ClearCast AI noise suppression
    - Custom effect chains
    """
    
    # Default EQ frequencies (ISO standard 10-band)
    DEFAULT_EQ_FREQUENCIES = [31, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    
    def __init__(
        self, 
        pipewire_manager: PipeWireManager,
        channel_manager: ChannelManager
    ):
        self._pipewire_manager = pipewire_manager
        self._channel_manager = channel_manager
        self._event_listeners: List[Callable[[str, Any], Awaitable[None]]] = []
        
        # Effect settings per channel
        self._channel_eq: Dict[ChannelType, List[EQBand]] = {}
        self._channel_noise_gate: Dict[ChannelType, NoiseGateSettings] = {}
        self._channel_compressor: Dict[ChannelType, CompressorSettings] = {}
        self._channel_limiter: Dict[ChannelType, LimiterSettings] = {}
        self._channel_clearcast: Dict[ChannelType, ClearCastSettings] = {}
        
        # Global effect settings
        self._global_eq: List[EQBand] = []
        self._global_noise_gate = NoiseGateSettings()
        self._global_compressor = CompressorSettings()
        self._global_limiter = LimiterSettings()
        self._global_clearcast = ClearCastSettings()
        
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize effects manager"""
        try:
            # Initialize default EQ for each channel
            for channel_type in ChannelType:
                if channel_type != ChannelType.MASTER:
                    self._channel_eq[channel_type] = self._create_default_eq()
                    self._channel_noise_gate[channel_type] = NoiseGateSettings()
                    self._channel_compressor[channel_type] = CompressorSettings()
                    self._channel_limiter[channel_type] = LimiterSettings()
                    self._channel_clearcast[channel_type] = ClearCastSettings()
            
            # Initialize global EQ
            self._global_eq = self._create_default_eq()
            
            self._initialized = True
            logger.info("Effects manager initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize effects manager: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown effects manager"""
        self._initialized = False
        logger.info("Effects manager shutdown")
    
    def _create_default_eq(self) -> List[EQBand]:
        """Create a default flat EQ with 10 bands"""
        return [
            EQBand(
                frequency=freq,
                gain=0.0,
                q_factor=1.0,
                eq_type=EQType.PEAKING,
                enabled=True
            )
            for freq in self.DEFAULT_EQ_FREQUENCIES
        ]
    
    async def set_channel_eq(
        self, 
        channel_type: ChannelType, 
        eq_bands: List[EQBand]
    ) -> bool:
        """Set EQ bands for a channel"""
        try:
            if channel_type not in self._channel_eq:
                return False
            
            self._channel_eq[channel_type] = [EQBand.from_dict(b.to_dict()) for b in eq_bands]
            
            # Apply to EasyEffects if available
            await self._apply_eq_to_easyeffects(channel_type)
            
            # Notify listeners
            for listener in self._event_listeners:
                try:
                    await listener("eq_changed", {
                        "channel_type": channel_type.name,
                        "eq_bands": [b.to_dict() for b in eq_bands]
                    })
                except Exception as e:
                    logger.error(f"Event listener error: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set channel EQ: {e}")
            return False
    
    async def get_channel_eq(self, channel_type: ChannelType) -> List[EQBand]:
        """Get EQ bands for a channel"""
        return self._channel_eq.get(channel_type, []).copy()
    
    async def set_eq_band(
        self, 
        channel_type: ChannelType, 
        band_index: int, 
        frequency: float, 
        gain: float, 
        q_factor: float
    ) -> bool:
        """Set a single EQ band"""
        try:
            if channel_type not in self._channel_eq:
                return False
            
            if band_index < 0 or band_index >= len(self._channel_eq[channel_type]):
                return False
            
            band = self._channel_eq[channel_type][band_index]
            band.frequency = frequency
            band.gain = gain
            band.q_factor = q_factor
            
            # Apply changes
            await self._apply_eq_to_easyeffects(channel_type)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set EQ band: {e}")
            return False
    
    async def set_channel_noise_gate(
        self, 
        channel_type: ChannelType, 
        settings: NoiseGateSettings
    ) -> bool:
        """Set noise gate settings for a channel"""
        try:
            if channel_type not in self._channel_noise_gate:
                return False
            
            self._channel_noise_gate[channel_type] = NoiseGateSettings.from_dict(settings.to_dict())
            
            # Apply to EasyEffects
            await self._apply_noise_gate_to_easyeffects(channel_type)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set channel noise gate: {e}")
            return False
    
    async def get_channel_noise_gate(self, channel_type: ChannelType) -> NoiseGateSettings:
        """Get noise gate settings for a channel"""
        return self._channel_noise_gate.get(channel_type, NoiseGateSettings()).copy()
    
    async def set_channel_compressor(
        self, 
        channel_type: ChannelType, 
        settings: CompressorSettings
    ) -> bool:
        """Set compressor settings for a channel"""
        try:
            if channel_type not in self._channel_compressor:
                return False
            
            self._channel_compressor[channel_type] = CompressorSettings.from_dict(settings.to_dict())
            
            # Apply to EasyEffects
            await self._apply_compressor_to_easyeffects(channel_type)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set channel compressor: {e}")
            return False
    
    async def get_channel_compressor(self, channel_type: ChannelType) -> CompressorSettings:
        """Get compressor settings for a channel"""
        return self._channel_compressor.get(channel_type, CompressorSettings()).copy()
    
    async def set_channel_limiter(
        self, 
        channel_type: ChannelType, 
        settings: LimiterSettings
    ) -> bool:
        """Set limiter settings for a channel"""
        try:
            if channel_type not in self._channel_limiter:
                return False
            
            self._channel_limiter[channel_type] = LimiterSettings.from_dict(settings.to_dict())
            
            # Apply to EasyEffects
            await self._apply_limiter_to_easyeffects(channel_type)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set channel limiter: {e}")
            return False
    
    async def get_channel_limiter(self, channel_type: ChannelType) -> LimiterSettings:
        """Get limiter settings for a channel"""
        return self._channel_limiter.get(channel_type, LimiterSettings()).copy()
    
    async def set_channel_clearcast(
        self, 
        channel_type: ChannelType, 
        settings: ClearCastSettings
    ) -> bool:
        """Set ClearCast settings for a channel"""
        try:
            if channel_type not in self._channel_clearcast:
                return False
            
            self._channel_clearcast[channel_type] = ClearCastSettings.from_dict(settings.to_dict())
            
            # Apply ClearCast (requires special handling)
            await self._apply_clearcast(channel_type)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set channel ClearCast: {e}")
            return False
    
    async def get_channel_clearcast(self, channel_type: ChannelType) -> ClearCastSettings:
        """Get ClearCast settings for a channel"""
        return self._channel_clearcast.get(channel_type, ClearCastSettings()).copy()
    
    async def apply_preset_to_channel(
        self, 
        preset: Preset, 
        channel_type: ChannelType
    ) -> bool:
        """Apply a preset to a channel"""
        try:
            # Apply EQ if present
            if preset.preset_type in (PresetType.EQ, PresetType.COMPLETE):
                await self.set_channel_eq(channel_type, preset.eq_bands)
            
            # Apply effect presets
            for effect_preset in preset.effect_presets:
                if effect_preset.effect_type == "noise_gate":
                    noise_gate_settings = NoiseGateSettings.from_dict(effect_preset.parameters)
                    await self.set_channel_noise_gate(channel_type, noise_gate_settings)
                elif effect_preset.effect_type == "compressor":
                    compressor_settings = CompressorSettings.from_dict(effect_preset.parameters)
                    await self.set_channel_compressor(channel_type, compressor_settings)
                elif effect_preset.effect_type == "limiter":
                    limiter_settings = LimiterSettings.from_dict(effect_preset.parameters)
                    await self.set_channel_limiter(channel_type, limiter_settings)
                elif effect_preset.effect_type == "clearcast":
                    clearcast_settings = ClearCastSettings.from_dict(effect_preset.parameters)
                    await self.set_channel_clearcast(channel_type, clearcast_settings)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply preset to channel: {e}")
            return False
    
    async def _apply_eq_to_easyeffects(self, channel_type: ChannelType) -> None:
        """Apply EQ settings to EasyEffects"""
        try:
            channel = self._channel_manager.get_channel(channel_type)
            if not channel or not channel.virtual_sink:
                return
            
            # This would integrate with EasyEffects API
            # For now, we'll use a placeholder
            logger.info(f"Applying EQ to {channel_type.name} via EasyEffects")
            
        except Exception as e:
            logger.error(f"Failed to apply EQ to EasyEffects: {e}")
    
    async def _apply_noise_gate_to_easyeffects(self, channel_type: ChannelType) -> None:
        """Apply noise gate settings to EasyEffects"""
        try:
            channel = self._channel_manager.get_channel(channel_type)
            if not channel or not channel.virtual_sink:
                return
            
            logger.info(f"Applying noise gate to {channel_type.name} via EasyEffects")
            
        except Exception as e:
            logger.error(f"Failed to apply noise gate to EasyEffects: {e}")
    
    async def _apply_compressor_to_easyeffects(self, channel_type: ChannelType) -> None:
        """Apply compressor settings to EasyEffects"""
        try:
            channel = self._channel_manager.get_channel(channel_type)
            if not channel or not channel.virtual_sink:
                return
            
            logger.info(f"Applying compressor to {channel_type.name} via EasyEffects")
            
        except Exception as e:
            logger.error(f"Failed to apply compressor to EasyEffects: {e}")
    
    async def _apply_limiter_to_easyeffects(self, channel_type: ChannelType) -> None:
        """Apply limiter settings to EasyEffects"""
        try:
            channel = self._channel_manager.get_channel(channel_type)
            if not channel or not channel.virtual_sink:
                return
            
            logger.info(f"Applying limiter to {channel_type.name} via EasyEffects")
            
        except Exception as e:
            logger.error(f"Failed to apply limiter to EasyEffects: {e}")
    
    async def _apply_clearcast(self, channel_type: ChannelType) -> None:
        """Apply ClearCast noise suppression"""
        try:
            channel = self._channel_manager.get_channel(channel_type)
            if not channel or not channel.virtual_source:
                return
            
            # ClearCast would typically use a noise suppression library
            # like RNNoise or NVIDIA Noise2Noise
            logger.info(f"Applying ClearCast to {channel_type.name}")
            
        except Exception as e:
            logger.error(f"Failed to apply ClearCast: {e}")
    
    async def process_audio_with_eq(
        self, 
        audio: np.ndarray, 
        sample_rate: int, 
        eq_bands: List[EQBand]
    ) -> np.ndarray:
        """
        Process audio through EQ filters.
        
        This is a software implementation of parametric EQ.
        For production, we'd use EasyEffects or a dedicated DSP library.
        """
        try:
            if len(audio) == 0:
                return audio
            
            # Apply each EQ band
            for band in eq_bands:
                if not band.enabled:
                    continue
                
                # Design the filter
                nyquist = sample_rate / 2
                freq = band.frequency / nyquist
                
                # Calculate filter coefficients based on EQ type
                if band.eq_type == EQType.PEAKING:
                    # Peaking filter
                    q = band.q_factor
                    gain = band.gain
                    
                    # Convert gain from dB to linear
                    A = 10 ** (gain / 20)
                    
                    # Calculate coefficients
                    w0 = 2 * math.pi * freq
                    alpha = w0 / (2 * q)
                    
                    b0 = 1 + alpha * A
                    b1 = -2 * math.cos(w0)
                    b2 = 1 - alpha * A
                    a0 = 1 + alpha / A
                    a1 = -2 * math.cos(w0)
                    a2 = 1 - alpha / A
                    
                    # Normalize
                    b0 /= a0
                    b1 /= a0
                    b2 /= a0
                    a1 /= a0
                    a2 /= a0
                    
                    # Apply filter
                    audio = signal.lfilter([b0, b1, b2], [1, a1, a2], audio)
                
                elif band.eq_type == EQType.LOW_SHELF:
                    # Low shelf filter
                    q = band.q_factor
                    gain = band.gain
                    
                    A = 10 ** (gain / 20)
                    w0 = 2 * math.pi * freq
                    
                    alpha = w0 / (2 * q)
                    k = math.tan(w0 / 2)
                    
                    b0 = A * ((A + 1) + (A - 1) * k + (A + 1) * k * k)
                    b1 = 2 * A * ((A - 1) + (A + 1) * k * k)
                    b2 = A * ((A + 1) + (A - 1) * k - (A + 1) * k * k)
                    a0 = (A + 1) + (A - 1) * k + (A + 1) * k * k
                    a1 = -2 * ((A - 1) + (A + 1) * k * k)
                    a2 = (A + 1) + (A - 1) * k - (A + 1) * k * k
                    
                    b0 /= a0
                    b1 /= a0
                    b2 /= a0
                    a1 /= a0
                    a2 /= a0
                    
                    audio = signal.lfilter([b0, b1, b2], [1, a1, a2], audio)
                
                elif band.eq_type == EQType.HIGH_SHELF:
                    # High shelf filter
                    q = band.q_factor
                    gain = band.gain
                    
                    A = 10 ** (gain / 20)
                    w0 = 2 * math.pi * freq
                    
                    alpha = w0 / (2 * q)
                    k = math.tan(w0 / 2)
                    
                    b0 = A * ((A + 1) - (A - 1) * k + (A + 1) * k * k)
                    b1 = -2 * A * ((A - 1) - (A + 1) * k * k)
                    b2 = A * ((A + 1) - (A - 1) * k - (A + 1) * k * k)
                    a0 = (A + 1) - (A - 1) * k + (A + 1) * k * k
                    a1 = 2 * ((A - 1) - (A + 1) * k * k)
                    a2 = (A + 1) - (A - 1) * k - (A + 1) * k * k
                    
                    b0 /= a0
                    b1 /= a0
                    b2 /= a0
                    a1 /= a0
                    a2 /= a0
                    
                    audio = signal.lfilter([b0, b1, b2], [1, a1, a2], audio)
            
            return audio
            
        except Exception as e:
            logger.error(f"Failed to process audio with EQ: {e}")
            return audio
    
    async def process_audio_with_noise_gate(
        self, 
        audio: np.ndarray, 
        sample_rate: int, 
        settings: NoiseGateSettings
    ) -> np.ndarray:
        """
        Process audio through a noise gate.
        
        This is a software implementation of a noise gate.
        """
        try:
            if len(audio) == 0 or not settings.enabled:
                return audio
            
            # Convert threshold from dB to linear
            threshold_linear = 10 ** (settings.threshold / 20)
            
            # Calculate attack and release in samples
            attack_samples = int(settings.attack * sample_rate)
            release_samples = int(settings.release * sample_rate)
            hold_samples = int(settings.hold * sample_rate)
            
            # Initialize state
            state = "closed"
            hold_counter = 0
            output = np.zeros_like(audio)
            
            for i in range(len(audio)):
                sample = abs(audio[i])
                
                if state == "closed":
                    if sample > threshold_linear:
                        state = "attack"
                        attack_start = i
                    output[i] = 0
                    
                elif state == "attack":
                    if i - attack_start >= attack_samples:
                        state = "open"
                        hold_counter = 0
                    else:
                        # Apply attack curve
                        progress = (i - attack_start) / attack_samples
                        output[i] = audio[i] * progress
                    
                elif state == "open":
                    if sample <= threshold_linear:
                        state = "hold"
                        hold_counter = 0
                    output[i] = audio[i]
                    
                elif state == "hold":
                    if hold_counter >= hold_samples:
                        state = "release"
                        release_start = i
                    else:
                        hold_counter += 1
                    output[i] = audio[i]
                    
                elif state == "release":
                    if i - release_start >= release_samples:
                        state = "closed"
                    else:
                        # Apply release curve
                        progress = 1 - ((i - release_start) / release_samples)
                        output[i] = audio[i] * progress
            
            return output
            
        except Exception as e:
            logger.error(f"Failed to process audio with noise gate: {e}")
            return audio
    
    async def process_audio_with_compressor(
        self, 
        audio: np.ndarray, 
        sample_rate: int, 
        settings: CompressorSettings
    ) -> np.ndarray:
        """
        Process audio through a compressor.
        
        This is a software implementation of a compressor.
        """
        try:
            if len(audio) == 0 or not settings.enabled:
                return audio
            
            # Convert parameters from dB to linear
            threshold_linear = 10 ** (settings.threshold / 20)
            knee_linear = 10 ** (settings.knee / 20)
            makeup_gain_linear = 10 ** (settings.makeup_gain / 20)
            
            # Calculate attack and release in samples
            attack_samples = max(1, int(settings.attack * sample_rate))
            release_samples = max(1, int(settings.release * sample_rate))
            
            # Initialize state
            envelope = 0.0
            output = np.zeros_like(audio)
            
            for i in range(len(audio)):
                sample = abs(audio[i])
                
                # Calculate envelope
                if sample > envelope:
                    # Attack
                    alpha = 1 - math.exp(-1 / attack_samples)
                    envelope = alpha * sample + (1 - alpha) * envelope
                else:
                    # Release
                    alpha = 1 - math.exp(-1 / release_samples)
                    envelope = alpha * sample + (1 - alpha) * envelope
                
                # Apply compression
                if envelope < threshold_linear - knee_linear / 2:
                    # Below threshold, no compression
                    gain = 1.0
                elif envelope < threshold_linear + knee_linear / 2:
                    # In knee region, smooth transition
                    over = envelope - (threshold_linear - knee_linear / 2)
                    gain = 1 - (settings.ratio - 1) * (over / knee_linear) ** 2
                else:
                    # Above threshold, full compression
                    over = envelope - threshold_linear
                    gain = 1 / (settings.ratio + (over * (1 - 1 / settings.ratio)) / threshold_linear)
                
                # Apply makeup gain
                gain *= makeup_gain_linear
                
                output[i] = audio[i] * gain
            
            return output
            
        except Exception as e:
            logger.error(f"Failed to process audio with compressor: {e}")
            return audio
    
    def add_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Add an event listener for effect changes"""
        self._event_listeners.append(listener)
    
    def remove_event_listener(self, listener: Callable[[str, Any], Awaitable[None]]) -> None:
        """Remove an event listener"""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)
    
    async def get_channel_effects_summary(self, channel_type: ChannelType) -> Dict[str, Any]:
        """Get a summary of all effects for a channel"""
        return {
            "eq": {
                "enabled": any(b.enabled for b in self._channel_eq.get(channel_type, [])),
                "bands": len(self._channel_eq.get(channel_type, []))
            },
            "noise_gate": self._channel_noise_gate.get(channel_type, NoiseGateSettings()).to_dict(),
            "compressor": self._channel_compressor.get(channel_type, CompressorSettings()).to_dict(),
            "limiter": self._channel_limiter.get(channel_type, LimiterSettings()).to_dict(),
            "clearcast": self._channel_clearcast.get(channel_type, ClearCastSettings()).to_dict(),
        }
