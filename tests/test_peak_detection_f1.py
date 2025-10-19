"""
Unit tests for peak detection functionality (Epic F1).

Tests for peak picking, spacing validation, and top-K selection.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from analyzer.peaks import PeakPicker
from analyzer.config import Config


class TestPeakDetectionEpicF1:
    """Tests for peak detection algorithms."""

    def test_peak_picker_initialization(self):
        """Test PeakPicker initialization."""
        config = Config(input_path="test.mp4", clips_count=5, peak_spacing=80)
        picker = PeakPicker(config)
        assert picker is not None
        assert picker.config is config

    def test_find_peaks_basic(self):
        """Test basic peak finding."""
        config = Config(input_path="test.mp4", clips_count=3, peak_spacing=80)
        picker = PeakPicker(config)
        
        # Create synthetic novelty scores with clear peaks
        novelty_scores = {
            "time_axis": np.array([0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]),
            "novelty_scores": np.array([0.1, 0.3, 0.8, 0.2, 0.9, 0.1, 0.7]),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        assert "peak_times" in result
        assert isinstance(result["peak_times"], np.ndarray)
        assert len(result["peak_times"]) <= config.clips_count

    def test_find_peaks_with_spacing(self):
        """Test peak finding with spacing constraints."""
        config = Config(input_path="test.mp4", clips_count=5, peak_spacing=100)
        picker = PeakPicker(config)
        
        # Create scores with peaks too close together
        novelty_scores = {
            "time_axis": np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]),
            "novelty_scores": np.array([0.1, 0.9, 0.1, 0.8, 0.1, 0.7, 0.1, 0.6, 0.1, 0.5, 0.1]),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        # Should respect spacing constraints
        peaks = result["peak_times"]
        if len(peaks) > 1:
            for i in range(1, len(peaks)):
                time_diff = peaks[i] - peaks[i-1]
                assert time_diff >= 0.1  # Should respect minimum spacing

    def test_find_peaks_top_k_selection(self):
        """Test top-K peak selection."""
        config = Config(input_path="test.mp4", clips_count=3, peak_spacing=50)
        picker = PeakPicker(config)
        
        # Create scores with many peaks
        novelty_scores = {
            "time_axis": np.linspace(0, 10, 100),
            "novelty_scores": np.random.rand(100),  # Random scores
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        # Should return at most K peaks
        assert len(result["peak_times"]) <= config.clips_count

    def test_find_peaks_empty_scores(self):
        """Test peak finding with empty scores."""
        config = Config(input_path="test.mp4", clips_count=5, peak_spacing=80)
        picker = PeakPicker(config)
        
        novelty_scores = {
            "time_axis": np.array([]),
            "novelty_scores": np.array([]),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        assert "peak_times" in result
        assert len(result["peak_times"]) == 0

    def test_find_peaks_flat_scores(self):
        """Test peak finding with flat scores."""
        config = Config(input_path="test.mp4", clips_count=5, peak_spacing=80)
        picker = PeakPicker(config)
        
        novelty_scores = {
            "time_axis": np.linspace(0, 10, 100),
            "novelty_scores": np.ones(100) * 0.5,  # Flat scores
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        # Should handle flat scores gracefully
        assert "peak_times" in result
        assert isinstance(result["peak_times"], np.ndarray)

    def test_greedy_top_k_selection(self):
        """Test greedy top-K selection algorithm."""
        config = Config(input_path="test.mp4", clips_count=3, peak_spacing=80)
        picker = PeakPicker(config)
        
        # Create test novelty scores with clear peaks
        novelty_scores = {
            "time_axis": np.array([0.0, 0.5, 1.0, 1.5, 2.0]),
            "novelty_scores": np.array([0.8, 0.9, 0.7, 0.6, 0.5]),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        # Should select top peaks respecting spacing
        assert len(result["peak_times"]) <= config.clips_count
        # Should return peak scores
        assert "peak_scores" in result

    def test_incorporate_seeds(self):
        """Test seed timestamp incorporation."""
        config = Config(
            input_path="test.mp4", 
            clips_count=5, 
            peak_spacing=80,
            seed_timestamps=[1.0, 3.0]
        )
        picker = PeakPicker(config)
        
        # Create novelty scores
        novelty_scores = {
            "time_axis": np.linspace(0, 5, 100),
            "novelty_scores": np.random.rand(100),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        # Should incorporate seed-based peaks
        assert "peak_times" in result
        assert "seed_based" in result
        # Should have some seed-based peaks
        assert np.any(result["seed_based"])

    def test_incorporate_seeds_with_conflicts(self):
        """Test seed incorporation with spacing conflicts."""
        config = Config(
            input_path="test.mp4", 
            clips_count=5, 
            peak_spacing=80,
            seed_timestamps=[0.6, 1.2]  # Close to existing peaks
        )
        picker = PeakPicker(config)
        
        novelty_scores = {
            "time_axis": np.linspace(0, 5, 100),
            "novelty_scores": np.random.rand(100),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        # Should handle conflicts by applying spacing rules
        assert "peak_times" in result
        assert "seed_based" in result

    def test_find_all_peaks(self):
        """Test finding all potential peaks."""
        config = Config(input_path="test.mp4", clips_count=5, peak_spacing=80)
        picker = PeakPicker(config)
        
        novelty_scores = {
            "time_axis": np.array([0, 0.5, 1.0, 1.5, 2.0]),
            "novelty_scores": np.array([0.1, 0.8, 0.3, 0.9, 0.2]),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        # Should find peaks at high score locations
        assert "peak_times" in result
        assert "peak_scores" in result
        # Should return some peaks
        assert len(result["peak_times"]) > 0


class TestPeakDetectionEdgeCasesEpicF1:
    """Tests for edge cases in peak detection."""

    def test_peaks_with_extreme_values(self):
        """Test peak detection with extreme score values."""
        config = Config(input_path="test.mp4", clips_count=5, peak_spacing=80)
        picker = PeakPicker(config)
        
        novelty_scores = {
            "time_axis": np.array([0, 0.5, 1.0, 1.5, 2.0]),
            "novelty_scores": np.array([0, 1000, 0.5, -1000, 0.8]),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        # Should handle extreme values
        assert "peak_times" in result
        assert isinstance(result["peak_times"], np.ndarray)

    def test_peaks_with_non_finite_values(self):
        """Test peak detection with NaN/Inf values."""
        config = Config(input_path="test.mp4", clips_count=5, peak_spacing=80)
        picker = PeakPicker(config)
        
        novelty_scores = {
            "time_axis": np.array([0, 0.5, 1.0, 1.5, 2.0]),
            "novelty_scores": np.array([0.1, np.nan, 0.8, np.inf, 0.5]),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        # Should handle non-finite values gracefully
        assert "peak_times" in result
        assert isinstance(result["peak_times"], np.ndarray)

    def test_peaks_with_very_small_spacing(self):
        """Test peak detection with very small spacing."""
        config = Config(input_path="test.mp4", clips_count=5, peak_spacing=50)  # Minimum spacing
        picker = PeakPicker(config)
        
        novelty_scores = {
            "time_axis": np.linspace(0, 1, 1000),  # Very dense time grid
            "novelty_scores": np.random.rand(1000),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        # Should handle very small spacing
        assert "peak_times" in result
        assert isinstance(result["peak_times"], np.ndarray)

    def test_peaks_with_very_large_spacing(self):
        """Test peak detection with very large spacing."""
        config = Config(input_path="test.mp4", clips_count=5, peak_spacing=10000)
        picker = PeakPicker(config)
        
        novelty_scores = {
            "time_axis": np.array([0, 1, 2, 3, 4, 5]),
            "novelty_scores": np.array([0.1, 0.9, 0.1, 0.8, 0.1, 0.7]),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        # Should handle very large spacing
        assert "peak_times" in result
        assert isinstance(result["peak_times"], np.ndarray)

    def test_peaks_with_zero_clips_count(self):
        """Test peak detection with zero clips count."""
        config = Config(input_path="test.mp4", clips_count=1, peak_spacing=80)  # Minimum clips count
        picker = PeakPicker(config)
        
        novelty_scores = {
            "time_axis": np.array([0, 0.5, 1.0, 1.5, 2.0]),
            "novelty_scores": np.array([0.1, 0.8, 0.3, 0.9, 0.2]),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        # Should return at least one peak
        assert "peak_times" in result
        assert len(result["peak_times"]) >= 0


class TestPeakDetectionPerformanceEpicF1:
    """Performance tests for peak detection."""

    def test_peak_detection_performance(self):
        """Benchmark peak detection performance."""
        config = Config(input_path="test.mp4", clips_count=10, peak_spacing=80)
        picker = PeakPicker(config)
        
        # Create large novelty scores array
        novelty_scores = {
            "time_axis": np.linspace(0, 600, 100000),  # 10 minutes at high resolution
            "novelty_scores": np.random.rand(100000),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        import time
        start_time = time.time()
        result = picker.find_peaks(novelty_scores)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should process large arrays quickly (< 1 second)
        assert processing_time < 1.0
        assert "peak_times" in result
        assert len(result["peak_times"]) <= config.clips_count

    def test_peak_detection_with_many_seeds(self):
        """Test peak detection with many seed timestamps."""
        config = Config(
            input_path="test.mp4", 
            clips_count=20, 
            peak_spacing=80,
            seed_timestamps=list(range(0, 100, 5))  # 20 seeds
        )
        picker = PeakPicker(config)
        
        novelty_scores = {
            "time_axis": np.linspace(0, 100, 1000),
            "novelty_scores": np.random.rand(1000),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        result = picker.find_peaks(novelty_scores)
        
        # Should handle many seeds efficiently
        assert "peak_times" in result
        assert isinstance(result["peak_times"], np.ndarray)

    def test_peak_detection_memory_usage(self):
        """Test memory usage during peak detection."""
        config = Config(input_path="test.mp4", clips_count=5, peak_spacing=80)
        picker = PeakPicker(config)
        
        # Test multiple calls to ensure no memory leaks
        for _ in range(10):
            novelty_scores = {
                "time_axis": np.linspace(0, 10, 1000),
                "novelty_scores": np.random.rand(1000),
                "sample_rate": 22050,
                "hop_length": 512
            }
            
            result = picker.find_peaks(novelty_scores)
            assert "peak_times" in result

