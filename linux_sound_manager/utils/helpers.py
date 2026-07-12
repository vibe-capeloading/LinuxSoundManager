"""
Helper functions for Linux Sound Manager
"""

import math
import numpy as np
from typing import Optional, Tuple, List
from scipy import signal


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp a value between minimum and maximum"""
    return max(min_val, min(max_val, value))


def db_to_linear(db: float) -> float:
    """Convert decibels to linear scale"""
    return 10 ** (db / 20)


def linear_to_db(linear: float) -> float:
    """Convert linear scale to decibels"""
    if linear <= 0:
        return -float('inf')
    return 20 * math.log10(linear)


def frequency_to_midi(frequency: float) -> float:
    """Convert frequency in Hz to MIDI note number"""
    return 69 + 12 * math.log2(frequency / 440.0)


def midi_to_frequency(midi: float) -> float:
    """Convert MIDI note number to frequency in Hz"""
    return 440.0 * 2 ** ((midi - 69) / 12)


def resample_audio(
    audio: np.ndarray,
    original_sample_rate: int,
    target_sample_rate: int
) -> np.ndarray:
    """
    Resample audio to a different sample rate.
    
    Args:
        audio: Input audio as numpy array
        original_sample_rate: Original sample rate in Hz
        target_sample_rate: Target sample rate in Hz
    
    Returns:
        Resampled audio as numpy array
    """
    if original_sample_rate == target_sample_rate:
        return audio.copy()
    
    try:
        # Calculate resampling ratio
        ratio = target_sample_rate / original_sample_rate
        
        # Use scipy's resample function
        new_length = int(len(audio) * ratio)
        resampled = signal.resample(audio, new_length)
        
        return resampled.astype(np.float32)
        
    except Exception as e:
        print(f"Failed to resample audio: {e}")
        return audio.copy()


def normalize_audio(audio: np.ndarray, target_peak: float = 0.99) -> np.ndarray:
    """
    Normalize audio to a target peak level.
    
    Args:
        audio: Input audio as numpy array
        target_peak: Target peak level (0.0 to 1.0)
    
    Returns:
        Normalized audio as numpy array
    """
    if len(audio) == 0:
        return audio
    
    try:
        # Find current peak
        current_peak = np.max(np.abs(audio))
        
        if current_peak == 0:
            return audio.copy()
        
        # Calculate normalization factor
        factor = target_peak / current_peak
        
        # Apply normalization
        normalized = audio * factor
        
        return normalized.astype(np.float32)
        
    except Exception as e:
        print(f"Failed to normalize audio: {e}")
        return audio.copy()


def apply_gain(audio: np.ndarray, gain_db: float) -> np.ndarray:
    """
    Apply gain to audio in decibels.
    
    Args:
        audio: Input audio as numpy array
        gain_db: Gain in decibels
    
    Returns:
        Audio with gain applied
    """
    gain_linear = db_to_linear(gain_db)
    return audio * gain_linear


def mix_audio(streams: List[np.ndarray], weights: Optional[List[float]] = None) -> np.ndarray:
    """
    Mix multiple audio streams together.
    
    Args:
        streams: List of audio streams as numpy arrays
        weights: Optional list of weights for each stream
    
    Returns:
        Mixed audio as numpy array
    """
    if not streams:
        return np.array([])
    
    try:
        # Find maximum length
        max_length = max(len(s) for s in streams)
        
        # Initialize output
        output = np.zeros(max_length, dtype=np.float32)
        
        # Apply weights if provided
        if weights is None:
            weights = [1.0] * len(streams)
        elif len(weights) != len(streams):
            weights = [1.0] * len(streams)
        
        # Mix all streams
        for stream, weight in zip(streams, weights):
            # Pad or truncate to match output length
            if len(stream) < max_length:
                padded = np.zeros(max_length, dtype=np.float32)
                padded[:len(stream)] = stream
                stream = padded
            elif len(stream) > max_length:
                stream = stream[:max_length]
            
            # Apply weight and add to output
            output += stream * weight
        
        # Clamp to prevent clipping
        output = np.clip(output, -1.0, 1.0)
        
        return output
        
    except Exception as e:
        print(f"Failed to mix audio: {e}")
        return np.array([])


def fade_in(audio: np.ndarray, duration: int = 100) -> np.ndarray:
    """
    Apply fade-in to audio.
    
    Args:
        audio: Input audio as numpy array
        duration: Fade duration in samples
    
    Returns:
        Audio with fade-in applied
    """
    if len(audio) == 0 or duration <= 0:
        return audio.copy()
    
    try:
        output = audio.copy()
        fade_length = min(duration, len(audio))
        
        # Create fade-in curve (linear)
        fade = np.linspace(0, 1, fade_length)
        
        # Apply fade-in
        output[:fade_length] *= fade
        
        return output
        
    except Exception as e:
        print(f"Failed to apply fade-in: {e}")
        return audio.copy()


def fade_out(audio: np.ndarray, duration: int = 100) -> np.ndarray:
    """
    Apply fade-out to audio.
    
    Args:
        audio: Input audio as numpy array
        duration: Fade duration in samples
    
    Returns:
        Audio with fade-out applied
    """
    if len(audio) == 0 or duration <= 0:
        return audio.copy()
    
    try:
        output = audio.copy()
        fade_length = min(duration, len(audio))
        
        # Create fade-out curve (linear)
        fade = np.linspace(1, 0, fade_length)
        
        # Apply fade-out
        output[-fade_length:] *= fade
        
        return output
        
    except Exception as e:
        print(f"Failed to apply fade-out: {e}")
        return audio.copy()


def crossfade(
    audio1: np.ndarray,
    audio2: np.ndarray,
    duration: int = 100
) -> np.ndarray:
    """
    Crossfade between two audio streams.
    
    Args:
        audio1: First audio stream
        audio2: Second audio stream
        duration: Crossfade duration in samples
    
    Returns:
        Crossfaded audio
    """
    try:
        # Make sure both streams have the same length
        max_length = max(len(audio1), len(audio2))
        
        # Pad streams to same length
        padded1 = np.zeros(max_length, dtype=np.float32)
        padded1[:len(audio1)] = audio1
        
        padded2 = np.zeros(max_length, dtype=np.float32)
        padded2[:len(audio2)] = audio2
        
        # Create crossfade curves
        fade_out = np.ones(max_length)
        fade_in = np.zeros(max_length)
        
        if duration > 0:
            fade_length = min(duration, max_length)
            fade_out[-fade_length:] = np.linspace(1, 0, fade_length)
            fade_in[-fade_length:] = np.linspace(0, 1, fade_length)
        
        # Apply crossfade
        output = padded1 * fade_out + padded2 * fade_in
        
        # Clamp to prevent clipping
        output = np.clip(output, -1.0, 1.0)
        
        return output
        
    except Exception as e:
        print(f"Failed to crossfade audio: {e}")
        return audio2.copy()


def detect_silence(
    audio: np.ndarray,
    threshold: float = 0.01,
    min_duration: int = 100
) -> List[Tuple[int, int]]:
    """
    Detect silent regions in audio.
    
    Args:
        audio: Input audio as numpy array
        threshold: Silence threshold (0.0 to 1.0)
        min_duration: Minimum duration of silence in samples
    
    Returns:
        List of (start, end) tuples for silent regions
    """
    try:
        if len(audio) == 0:
            return []
        
        # Calculate absolute values
        abs_audio = np.abs(audio)
        
        # Find where audio is below threshold
        silent = abs_audio < threshold
        
        # Find start and end of silent regions
        silent_regions = []
        in_silence = False
        start = 0
        
        for i in range(len(silent)):
            if silent[i] and not in_silence:
                # Start of silence
                start = i
                in_silence = True
            elif not silent[i] and in_silence:
                # End of silence
                end = i
                duration = end - start
                if duration >= min_duration:
                    silent_regions.append((start, end))
                in_silence = False
        
        # Check if we're still in silence at the end
        if in_silence:
            end = len(silent)
            duration = end - start
            if duration >= min_duration:
                silent_regions.append((start, end))
        
        return silent_regions
        
    except Exception as e:
        print(f"Failed to detect silence: {e}")
        return []


def calculate_rms(audio: np.ndarray) -> float:
    """
    Calculate RMS (Root Mean Square) level of audio.
    
    Args:
        audio: Input audio as numpy array
    
    Returns:
        RMS level (0.0 to 1.0)
    """
    try:
        if len(audio) == 0:
            return 0.0
        
        # Calculate RMS
        squares = np.square(audio)
        mean = np.mean(squares)
        rms = np.sqrt(mean)
        
        return float(rms)
        
    except Exception as e:
        print(f"Failed to calculate RMS: {e}")
        return 0.0


def calculate_peak(audio: np.ndarray) -> float:
    """
    Calculate peak level of audio.
    
    Args:
        audio: Input audio as numpy array
    
    Returns:
        Peak level (0.0 to 1.0)
    """
    try:
        if len(audio) == 0:
            return 0.0
        
        return float(np.max(np.abs(audio)))
        
    except Exception as e:
        print(f"Failed to calculate peak: {e}")
        return 0.0
