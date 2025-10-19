"""
Audio extraction module for MVP Analyzer.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Dict, Any

import wave
import numpy as np

from .config import Config

logger = logging.getLogger(__name__)


class AudioExtractor:
    """Handles audio extraction from video files."""
    
    def __init__(self, config: Config):
        """Initialize audio extractor with configuration."""
        self.config = config
        self.sample_rate = 22050  # Target sample rate
    
    def extract(self) -> Dict[str, Any]:
        """
        Extract audio from video file using ffmpeg.
        
        Returns:
            Dict containing audio data and metadata
        """
        logger.info(f"Extracting audio from {self.config.input_path}")
        
        # Check if input file exists
        if not self.config.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.config.input_path}")
        
        # Create temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_wav_path = Path(temp_file.name)
        
        try:
            # Extract audio using ffmpeg
            self._extract_with_ffmpeg(self.config.input_path, temp_wav_path)
            
            # Load audio with improved wave processing
            audio_data, sr = self._load_wav_with_resampling(temp_wav_path)
            
            # Get audio duration
            duration = len(audio_data) / sr
            
            logger.info(f"Audio extracted: {duration:.2f}s at {sr}Hz")
            
            return {
                "audio": audio_data,
                "sample_rate": sr,
                "duration": duration,
                "samples": len(audio_data),
                "temp_path": temp_wav_path
            }
            
        except Exception as e:
            # Clean up temp file on error
            if temp_wav_path.exists():
                temp_wav_path.unlink()
            raise
    
    def _extract_with_ffmpeg(self, input_path: Path, output_path: Path) -> None:
        """
        Extract audio using ffmpeg.
        
        Args:
            input_path: Path to input video file
            output_path: Path to output WAV file
        """
        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # PCM 16-bit little-endian
            "-ar", str(self.sample_rate),  # Sample rate
            "-ac", "1",  # Mono
            "-y",  # Overwrite output file
            str(output_path)
        ]
        
        logger.debug(f"Running ffmpeg command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug("ffmpeg extraction completed successfully")
            
        except subprocess.CalledProcessError as e:
            error_msg = f"ffmpeg failed with return code {e.returncode}"
            if e.stderr:
                error_msg += f": {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(f"Audio extraction failed: {error_msg}")
        except FileNotFoundError:
            error_msg = "ffmpeg not found. Please install ffmpeg and ensure it's in your PATH."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _load_wav_with_resampling(self, wav_path: Path) -> Tuple[np.ndarray, int]:
        """
        Load WAV file with proper resampling to target sample rate.
        
        Args:
            wav_path: Path to WAV file
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        try:
            with wave.open(str(wav_path), 'rb') as wav_file:
                # Get audio parameters
                original_sr = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                n_channels = wav_file.getnchannels()
                
                # Read audio data
                frames = wav_file.readframes(-1)
                
                # Convert to numpy array
                if wav_file.getsampwidth() == 2:  # 16-bit
                    audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                elif wav_file.getsampwidth() == 4:  # 32-bit
                    audio_data = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
                else:
                    raise ValueError(f"Unsupported sample width: {wav_file.getsampwidth()}")
                
                # Handle stereo to mono conversion
                if n_channels == 2:
                    audio_data = audio_data.reshape(-1, 2).mean(axis=1)
                
                # Resample if necessary
                if original_sr != self.sample_rate:
                    audio_data = self._resample_audio(audio_data, original_sr, self.sample_rate)
                    sr = self.sample_rate
                else:
                    sr = original_sr
                
                return audio_data, sr
                
        except Exception as e:
            raise RuntimeError(f"Failed to load WAV file: {e}")
    
    def _resample_audio(self, audio_data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """
        Simple resampling using linear interpolation.
        
        Args:
            audio_data: Input audio data
            orig_sr: Original sample rate
            target_sr: Target sample rate
            
        Returns:
            Resampled audio data
        """
        if orig_sr == target_sr:
            return audio_data
        
        # Calculate resampling ratio
        ratio = target_sr / orig_sr
        
        # Create new time axis
        orig_length = len(audio_data)
        new_length = int(orig_length * ratio)
        
        # Simple linear interpolation
        orig_indices = np.arange(orig_length)
        new_indices = np.linspace(0, orig_length - 1, new_length)
        
        # Interpolate
        resampled = np.interp(new_indices, orig_indices, audio_data)
        
        return resampled.astype(np.float32)
    
    def cleanup_temp_file(self, temp_path: Path) -> None:
        """Clean up temporary audio file."""
        if temp_path.exists():
            temp_path.unlink()
            logger.debug(f"Cleaned up temp file: {temp_path}")
