"""
Audio security utilities for safe audio file handling.

This module provides secure wrappers for audio file operations to mitigate
potential security vulnerabilities in underlying libraries like libsndfile.
"""

import os
import logging
from pathlib import Path
from typing import Tuple, Optional
import librosa
import numpy as np

logger = logging.getLogger(__name__)

# Security limits
MAX_AUDIO_DURATION_SECONDS = 3600  # 1 hour max
MAX_AUDIO_FILE_SIZE_MB = 500  # 500 MB max
MAX_SAMPLE_RATE = 48000  # 48 kHz max
MIN_SAMPLE_RATE = 8000  # 8 kHz min


def validate_audio_file(file_path: Path) -> bool:
    """
    Validate audio file for security before processing.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        True if file is safe to process, False otherwise
        
    Raises:
        ValueError: If file validation fails
    """
    if not file_path.exists():
        raise ValueError(f"Audio file does not exist: {file_path}")
    
    # Check file size
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_AUDIO_FILE_SIZE_MB:
        raise ValueError(
            f"Audio file too large: {file_size_mb:.1f}MB > {MAX_AUDIO_FILE_SIZE_MB}MB"
        )
    
    # Check file extension (basic validation)
    allowed_extensions = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac'}
    if file_path.suffix.lower() not in allowed_extensions:
        raise ValueError(f"Unsupported audio format: {file_path.suffix}")
    
    logger.info(f"Audio file validation passed: {file_path.name} ({file_size_mb:.1f}MB)")
    return True


def safe_load_audio(
    file_path: Path, 
    sr: Optional[int] = None, 
    mono: bool = True,
    duration: Optional[float] = None
) -> Tuple[np.ndarray, int]:
    """
    Safely load audio file with security checks.
    
    Args:
        file_path: Path to audio file
        sr: Target sample rate (None for original)
        mono: Convert to mono
        duration: Maximum duration to load (None for full file)
        
    Returns:
        Tuple of (audio_data, sample_rate)
        
    Raises:
        ValueError: If file is unsafe or invalid
        RuntimeError: If audio loading fails
    """
    # Validate file first
    validate_audio_file(file_path)
    
    # Limit duration for security
    if duration is None:
        duration = MAX_AUDIO_DURATION_SECONDS
    else:
        duration = min(duration, MAX_AUDIO_DURATION_SECONDS)
    
    try:
        # Load audio with librosa (limited duration)
        audio_data, sample_rate = librosa.load(
            str(file_path),
            sr=sr,
            mono=mono,
            duration=duration,
            offset=0.0
        )
        
        # Additional security checks
        if sample_rate > MAX_SAMPLE_RATE:
            raise ValueError(f"Sample rate too high: {sample_rate} > {MAX_SAMPLE_RATE}")
        
        if sample_rate < MIN_SAMPLE_RATE:
            raise ValueError(f"Sample rate too low: {sample_rate} < {MIN_SAMPLE_RATE}")
        
        # Check for reasonable audio data
        if len(audio_data) == 0:
            raise ValueError("Audio file contains no data")
        
        # Check for NaN or infinite values
        if not np.all(np.isfinite(audio_data)):
            raise ValueError("Audio file contains invalid data (NaN or infinite values)")
        
        # Check audio duration
        actual_duration = len(audio_data) / sample_rate
        if actual_duration > MAX_AUDIO_DURATION_SECONDS:
            raise ValueError(f"Audio duration too long: {actual_duration:.1f}s > {MAX_AUDIO_DURATION_SECONDS}s")
        
        logger.info(f"Audio loaded safely: {len(audio_data)} samples, {sample_rate}Hz, {actual_duration:.1f}s")
        return audio_data, sample_rate
        
    except Exception as e:
        logger.error(f"Failed to load audio file {file_path}: {e}")
        raise RuntimeError(f"Audio loading failed: {e}") from e


def safe_resample_audio(
    audio: np.ndarray, 
    orig_sr: int, 
    target_sr: int
) -> np.ndarray:
    """
    Safely resample audio with security checks.
    
    Args:
        audio: Audio data
        orig_sr: Original sample rate
        target_sr: Target sample rate
        
    Returns:
        Resampled audio data
        
    Raises:
        ValueError: If parameters are invalid
    """
    if target_sr > MAX_SAMPLE_RATE:
        raise ValueError(f"Target sample rate too high: {target_sr} > {MAX_SAMPLE_RATE}")
    
    if orig_sr <= 0 or target_sr <= 0:
        raise ValueError("Sample rates must be positive")
    
    if target_sr < MIN_SAMPLE_RATE:
        raise ValueError(f"Target sample rate too low: {target_sr} < {MIN_SAMPLE_RATE}")
    
    try:
        return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
    except Exception as e:
        logger.error(f"Failed to resample audio: {e}")
        raise RuntimeError(f"Audio resampling failed: {e}") from e


def safe_to_mono(audio: np.ndarray) -> np.ndarray:
    """
    Safely convert audio to mono with security checks.
    
    Args:
        audio: Audio data
        
    Returns:
        Mono audio data
        
    Raises:
        ValueError: If audio data is invalid
    """
    if audio.size == 0:
        raise ValueError("Audio data is empty")
    
    if len(audio.shape) > 2:
        raise ValueError(f"Audio data has too many dimensions: {len(audio.shape)}")
    
    try:
        return librosa.to_mono(audio)
    except Exception as e:
        logger.error(f"Failed to convert audio to mono: {e}")
        raise RuntimeError(f"Audio mono conversion failed: {e}") from e
