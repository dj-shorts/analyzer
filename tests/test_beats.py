"""
Tests for beat tracking and quantization functionality.
"""

import pytest
import numpy as np
from pathlib import Path

from analyzer.beats import BeatTracker, BeatQuantizer
from analyzer.config import Config


class TestBeatTracker:
    """Test beat tracking functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(
            input_path=Path("test_video.mp4"),
            align_to_beat=True
        )
        self.beat_tracker = BeatTracker(self.config)
    
    def test_track_beats_synthetic_audio(self):
        """Test beat tracking with synthetic 4/4 audio."""
        # Create synthetic audio with clear beats
        duration = 10.0  # 10 seconds
        sr = 22050
        tempo = 120  # BPM
        
        # Generate click track
        beat_interval = 60.0 / tempo  # seconds per beat
        beat_times = np.arange(0, duration, beat_interval)
        
        # Create audio with clicks at beat positions
        audio = np.zeros(int(duration * sr))
        for beat_time in beat_times:
            beat_sample = int(beat_time * sr)
            if beat_sample < len(audio):
                # Add click (short burst of noise)
                click_length = int(0.01 * sr)  # 10ms click
                audio[beat_sample:beat_sample + click_length] = 0.5
        
        audio_data = {
            "audio": audio,
            "sample_rate": sr,
            "duration": duration,
            "samples": len(audio)
        }
        
        # Track beats
        result = self.beat_tracker.track_beats(audio_data)
        
        # Verify results
        assert "tempo" in result
        assert "beat_times" in result
        assert "confidence" in result
        assert "beat_grid" in result
        
        # Check tempo accuracy (should be close to 120 BPM)
        assert abs(result["tempo"] - tempo) < 10  # Within 10 BPM
        
        # Check confidence (should be high for clear beats)
        assert result["confidence"] > 0.5
        
        # Check beat count (should be close to expected)
        expected_beats = int(duration / beat_interval)
        assert abs(len(result["beat_times"]) - expected_beats) <= 2
    
    def test_calculate_confidence(self):
        """Test confidence calculation."""
        # Test with consistent beats
        consistent_beats = np.array([0, 0.5, 1.0, 1.5, 2.0, 2.5])
        tempo = 120
        confidence = self.beat_tracker._calculate_confidence(consistent_beats, tempo)
        assert confidence > 0.8
        
        # Test with inconsistent beats
        inconsistent_beats = np.array([0, 0.3, 1.2, 1.8, 2.1, 2.9])
        confidence = self.beat_tracker._calculate_confidence(inconsistent_beats, tempo)
        assert confidence < 0.6  # More lenient threshold
    
    def test_generate_beat_grid(self):
        """Test beat grid generation."""
        beat_times = np.array([0, 0.5, 1.0, 1.5, 2.0])
        tempo = 120
        sr = 22050
        
        grid = self.beat_tracker._generate_beat_grid(beat_times, tempo, sr)
        
        assert "grid_times" in grid
        assert "bar_times" in grid
        assert "beat_interval" in grid
        assert "bars_per_minute" in grid
        
        # Check beat interval
        expected_interval = 60.0 / tempo
        assert abs(grid["beat_interval"] - expected_interval) < 0.01
        
        # Check bars per minute
        expected_bars_per_minute = tempo / 4
        assert abs(grid["bars_per_minute"] - expected_bars_per_minute) < 0.1


class TestBeatQuantizer:
    """Test beat quantization functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(
            input_path=Path("test_video.mp4"),
            align_to_beat=True
        )
        self.quantizer = BeatQuantizer(self.config)
    
    def test_quantize_clip_high_confidence(self):
        """Test quantization with high confidence beat data."""
        # Create beat data with high confidence
        beat_data = {
            "tempo": 120,
            "confidence": 0.8,
            "beat_grid": {
                "grid_times": [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
                "bar_times": [0, 2.0, 4.0],
                "beat_interval": 0.5,
                "bars_per_minute": 30
            }
        }
        
        # Test quantization
        start_time = 1.2  # Between beats
        duration = 2.0   # Exactly 4 beats (2 seconds at 120 BPM)
        
        result = self.quantizer.quantize_clip(start_time, duration, beat_data)
        
        # Should be aligned
        assert result["aligned"] is True
        assert result["confidence"] == 0.8
        
        # Start should be quantized to nearest beat before original
        assert result["start_time"] <= start_time
        assert result["start_time"] in beat_data["beat_grid"]["grid_times"]
        
        # Duration should be quantized to bar boundaries
        bar_duration = 60.0 / (beat_data["tempo"] / 4)  # 2 seconds
        assert result["duration"] in [bar_duration * count for count in [2, 4, 6, 8, 12, 16]]
    
    def test_quantize_clip_low_confidence(self):
        """Test quantization with low confidence beat data."""
        beat_data = {
            "tempo": 120,
            "confidence": 0.2,  # Low confidence
            "beat_grid": {
                "grid_times": [],
                "bar_times": [],
                "beat_interval": 0.5,
                "bars_per_minute": 30
            }
        }
        
        result = self.quantizer.quantize_clip(1.0, 2.0, beat_data)
        
        # Should not be aligned due to low confidence
        assert result["aligned"] is False
        assert result["reason"] == "low_confidence"
        assert result["start_time"] == 1.0
        assert result["duration"] == 2.0
    
    def test_quantize_clip_no_beat_grid(self):
        """Test quantization with no beat grid."""
        beat_data = {
            "tempo": 120,
            "confidence": 0.8,
            "beat_grid": {
                "grid_times": [],
                "bar_times": [],
                "beat_interval": 0.5,
                "bars_per_minute": 30
            }
        }
        
        result = self.quantizer.quantize_clip(1.0, 2.0, beat_data)
        
        # Should not be aligned due to no beat grid
        assert result["aligned"] is False
        assert result["reason"] == "no_beat_grid"
    
    def test_quantize_start_time(self):
        """Test start time quantization."""
        grid_times = np.array([0, 0.5, 1.0, 1.5, 2.0, 2.5])
        
        # Test quantization to nearest beat before
        quantized = self.quantizer._quantize_start_time(1.2, grid_times)
        assert quantized == 1.0  # Nearest beat before 1.2
        
        quantized = self.quantizer._quantize_start_time(0.3, grid_times)
        assert quantized == 0.0  # Nearest beat before 0.3
        
        quantized = self.quantizer._quantize_start_time(2.0, grid_times)
        assert quantized == 2.0  # Exactly on beat
    
    def test_quantize_duration(self):
        """Test duration quantization."""
        beat_data = {
            "tempo": 120,  # 2 seconds per bar
        }
        
        # Test different durations
        quantized = self.quantizer._quantize_duration(15.0, beat_data)  # Close to 8 bars
        assert quantized == 16.0  # 8 bars * 2 seconds
        
        quantized = self.quantizer._quantize_duration(25.0, beat_data)  # Close to 12 bars
        assert quantized == 24.0  # 12 bars * 2 seconds
        
        quantized = self.quantizer._quantize_duration(35.0, beat_data)  # Close to 16 bars
        assert quantized == 32.0  # 16 bars * 2 seconds
    
    def test_is_quantization_reasonable(self):
        """Test quantization reasonableness check."""
        # Reasonable quantization
        assert self.quantizer._is_quantization_reasonable(1.0, 2.0, 0.5, 2.0) is True
        
        # Start moved too far back
        assert self.quantizer._is_quantization_reasonable(1.0, 2.0, -15.0, 2.0) is False
        
        # Duration changed too much
        assert self.quantizer._is_quantization_reasonable(1.0, 2.0, 0.5, 0.5) is False
        assert self.quantizer._is_quantization_reasonable(1.0, 2.0, 0.5, 5.0) is False


if __name__ == "__main__":
    pytest.main([__file__])
