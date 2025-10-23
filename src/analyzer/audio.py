"""
Audio extraction module for MVP Analyzer.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import librosa
from .audio_security import safe_load_audio, validate_audio_file

from .config import Config

logger = logging.getLogger(__name__)


class AudioExtractor:
    """Handles audio extraction from video files."""

    def __init__(self, config: Config):
        """Initialize audio extractor with configuration."""
        self.config = config
        self.sample_rate = 22050  # Target sample rate

    def extract(self) -> dict[str, Any]:
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

            # Load audio with librosa (using secure wrapper)
            audio_data, sr = safe_load_audio(
                temp_wav_path, sr=self.sample_rate, mono=True
            )

            # Get audio duration
            duration = len(audio_data) / sr

            logger.info(f"Audio extracted: {duration:.2f}s at {sr}Hz")

            return {
                "audio": audio_data,
                "sample_rate": sr,
                "duration": duration,
                "samples": len(audio_data),
                "temp_path": temp_wav_path,
            }

        except Exception:
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
            "-i",
            str(input_path),
            "-vn",  # No video
            "-acodec",
            "pcm_s16le",  # PCM 16-bit little-endian
            "-ar",
            str(self.sample_rate),  # Sample rate
            "-ac",
            "1",  # Mono
            "-y",  # Overwrite output file
            str(output_path),
        ]

        logger.debug(f"Running ffmpeg command: {' '.join(cmd)}")

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.debug("ffmpeg extraction completed successfully")

        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed with return code {e.returncode}")
            logger.error(f"stderr: {e.stderr}")
            raise RuntimeError(f"Audio extraction failed: {e.stderr}") from e
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found. Please install ffmpeg and ensure it's in your PATH."
            ) from None

    def cleanup_temp_file(self, temp_path: Path) -> None:
        """Clean up temporary audio file."""
        if temp_path.exists():
            temp_path.unlink()
            logger.debug(f"Cleaned up temp file: {temp_path}")
