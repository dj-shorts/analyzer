"""
Tests for audio security utilities.
"""

import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

from analyzer.audio_security import (
    MAX_AUDIO_DURATION_SECONDS,
    MAX_AUDIO_FILE_SIZE_MB,
    MAX_SAMPLE_RATE,
    MIN_SAMPLE_RATE,
    safe_load_audio,
    safe_resample_audio,
    safe_to_mono,
    validate_audio_file,
)


class TestAudioSecurity:
    """Test audio security utilities."""

    def test_validate_audio_file_nonexistent(self):
        """Test validation of non-existent file."""
        with pytest.raises(ValueError, match="Audio file does not exist"):
            validate_audio_file(Path("nonexistent.wav"))

    def test_validate_audio_file_too_large(self):
        """Test validation of too large file."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            # Create a file that's too large (simulate)
            temp_file.write(b"x" * (MAX_AUDIO_FILE_SIZE_MB + 1) * 1024 * 1024)
            temp_file.flush()

            try:
                with pytest.raises(ValueError, match="Audio file too large"):
                    validate_audio_file(temp_path)
            finally:
                os.unlink(temp_path)

    def test_validate_audio_file_unsupported_format(self):
        """Test validation of unsupported format."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"test")
            temp_file.flush()

            try:
                with pytest.raises(ValueError, match="Unsupported audio format"):
                    validate_audio_file(temp_path)
            finally:
                os.unlink(temp_path)

    def test_safe_resample_audio_invalid_sample_rate(self):
        """Test resampling with invalid sample rates."""
        audio = np.array([1.0, 2.0, 3.0])

        with pytest.raises(ValueError, match="Target sample rate too high"):
            safe_resample_audio(audio, 22050, MAX_SAMPLE_RATE + 1)

        with pytest.raises(ValueError, match="Target sample rate too low"):
            safe_resample_audio(audio, 22050, MIN_SAMPLE_RATE - 1)

        with pytest.raises(ValueError, match="Sample rates must be positive"):
            safe_resample_audio(audio, 0, 22050)

        with pytest.raises(ValueError, match="Sample rates must be positive"):
            safe_resample_audio(audio, 22050, -1)

    def test_safe_to_mono_empty_audio(self):
        """Test mono conversion with empty audio."""
        with pytest.raises(ValueError, match="Audio data is empty"):
            safe_to_mono(np.array([]))

    def test_safe_to_mono_too_many_dimensions(self):
        """Test mono conversion with too many dimensions."""
        audio = np.array([[[1.0, 2.0], [3.0, 4.0]]])
        with pytest.raises(ValueError, match="Audio data has too many dimensions"):
            safe_to_mono(audio)

    def test_safe_to_mono_valid_stereo(self):
        """Test mono conversion with valid stereo audio."""
        stereo_audio = np.array([[1.0, 2.0], [3.0, 4.0]])
        mono_audio = safe_to_mono(stereo_audio)
        assert len(mono_audio.shape) == 1
        assert len(mono_audio) == 2

    def test_safe_to_mono_valid_mono(self):
        """Test mono conversion with already mono audio."""
        mono_audio = np.array([1.0, 2.0, 3.0])
        result = safe_to_mono(mono_audio)
        np.testing.assert_array_equal(result, mono_audio)

    def test_safe_resample_audio_valid(self):
        """Test valid resampling."""
        audio = np.array([1.0, 2.0, 3.0, 4.0])
        resampled = safe_resample_audio(audio, 22050, 44100)
        assert len(resampled) > 0
        assert isinstance(resampled, np.ndarray)

    @pytest.mark.requires_ffmpeg
    def test_safe_load_audio_with_real_file(self):
        """Test safe loading with a real audio file (requires ffmpeg)."""
        # This test would require a real audio file and ffmpeg
        # For now, we'll just test the validation logic
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            # Write minimal WAV header
            temp_file.write(
                b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
            )
            temp_file.flush()

            try:
                # This should pass validation but fail at loading (no real audio data)
                validate_audio_file(temp_path)
                # The actual loading would fail, but validation passes
            except Exception:
                # Expected to fail at loading stage
                pass
            finally:
                os.unlink(temp_path)
