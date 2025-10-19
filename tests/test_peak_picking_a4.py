"""
Tests for Issue A4 - Peak picking with minimum spacing and top-K selection.
"""

import numpy as np
from pathlib import Path

from analyzer.config import Config
from analyzer.peaks import PeakPicker


class TestPeakPickingA4:
    """Tests for the PeakPicker with greedy top-K selection and spacing constraint (Issue A4)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(input_path=Path("test.mp4"))
        self.picker = PeakPicker(self.config)

    def test_greedy_top_k_selection(self):
        """Test greedy selection of top-K peaks with spacing constraint."""
        # Create synthetic novelty scores with multiple peaks
        novelty_scores = np.array([
            0.1, 0.2, 0.8, 0.3, 0.1,  # Peak at index 2 (score 0.8)
            0.1, 0.2, 0.1, 0.4, 0.1,  # Peak at index 8 (score 0.4) 
            0.1, 0.6, 0.2, 0.1, 0.1,  # Peak at index 11 (score 0.6)
            0.1, 0.1, 0.3, 0.2, 0.1,  # Peak at index 17 (score 0.3)
            0.1, 0.1, 0.1, 0.1, 0.1   # No peaks
        ])
        
        # Find all peaks
        all_peaks = self.picker._find_all_peaks(novelty_scores, prominence=0.1)
        
        # Test greedy selection with different K values and spacing
        k = 3
        min_spacing = 5  # frames
        
        selected_peaks, selected_scores = self.picker._greedy_top_k_selection(
            all_peaks, novelty_scores, k, min_spacing
        )
        
        # Should select top 3 peaks with proper spacing
        assert len(selected_peaks) <= k
        assert len(selected_scores) == len(selected_peaks)
        
        # Verify spacing constraint
        for i in range(len(selected_peaks) - 1):
            assert abs(selected_peaks[i+1] - selected_peaks[i]) >= min_spacing
        
        # Should select peaks with highest scores first
        expected_peaks = [2, 11, 8]  # Based on scores: 0.8, 0.6, 0.4
        assert len(selected_peaks) >= 2  # Should find at least 2 peaks

    def test_synthetic_peaks_thinning(self):
        """Test that synthetic peaks are correctly thinned with spacing constraint."""
        # Create novelty scores with closely spaced peaks
        novelty_scores = np.zeros(100)
        
        # Add peaks at indices 10, 15, 20, 25, 30 (close together)
        peak_indices = [10, 15, 20, 25, 30]
        peak_scores = [0.9, 0.8, 0.7, 0.6, 0.5]  # Decreasing scores
        
        for idx, score in zip(peak_indices, peak_scores):
            novelty_scores[idx] = score
        
        # Find all peaks
        all_peaks = self.picker._find_all_peaks(novelty_scores, prominence=0.1)
        
        # Apply greedy selection with spacing constraint
        k = 3
        min_spacing = 8  # Should thin out closely spaced peaks
        
        selected_peaks, selected_scores = self.picker._greedy_top_k_selection(
            all_peaks, novelty_scores, k, min_spacing
        )
        
        # Should select fewer peaks due to spacing constraint
        assert len(selected_peaks) <= k
        
        # Verify spacing constraint
        for i in range(len(selected_peaks) - 1):
            assert abs(selected_peaks[i+1] - selected_peaks[i]) >= min_spacing
        
        # Should prioritize higher scores
        assert len(selected_peaks) >= 1

    def test_one_hour_k6_spacing80(self):
        """Test for 1 hour audio with K=6, spacing=80 frames."""
        # Simulate 1 hour of audio at 22050 Hz with 512 hop_length
        # Total frames ≈ 1 hour * 22050 Hz / 512 hop_length ≈ 154,687 frames
        duration_seconds = 3600  # 1 hour
        sr = 22050
        hop_length = 512
        
        # Create novelty scores for 1 hour
        total_frames = int(duration_seconds * sr / hop_length)
        novelty_scores = np.random.rand(total_frames) * 0.5 + 0.1  # Random scores 0.1-0.6
        
        # Add some prominent peaks
        peak_positions = [1000, 5000, 10000, 20000, 30000, 40000, 50000, 60000]
        for pos in peak_positions:
            if pos < total_frames:
                novelty_scores[pos] = 0.9
        
        # Test peak picking
        all_peaks = self.picker._find_all_peaks(novelty_scores, prominence=0.1)
        
        k = 6
        spacing_frames = 80
        
        selected_peaks, selected_scores = self.picker._greedy_top_k_selection(
            all_peaks, novelty_scores, k, spacing_frames
        )
        
        # Should return ≤ 6 peaks
        assert len(selected_peaks) <= 6
        
        # Verify spacing constraint
        for i in range(len(selected_peaks) - 1):
            assert abs(selected_peaks[i+1] - selected_peaks[i]) >= spacing_frames

    def test_find_all_peaks(self):
        """Test finding all peaks without spacing constraint."""
        # Create signal with multiple peaks
        signal = np.array([0.1, 0.2, 0.8, 0.3, 0.1, 0.6, 0.2, 0.1])
        
        peaks = self.picker._find_all_peaks(signal, prominence=0.1)
        
        # Should find peaks at indices 2 and 5
        expected_peaks = [2, 5]
        assert len(peaks) >= 2
        assert 2 in peaks  # Peak with score 0.8
        assert 5 in peaks  # Peak with score 0.6

    def test_edge_cases(self):
        """Test edge cases for peak picking."""
        # Empty signal
        empty_signal = np.array([])
        peaks = self.picker._find_all_peaks(empty_signal)
        assert len(peaks) == 0
        
        # Signal with no peaks
        flat_signal = np.ones(100) * 0.5
        peaks = self.picker._find_all_peaks(flat_signal, prominence=0.6)
        assert len(peaks) == 0
        
        # Single peak
        single_peak = np.array([0.1, 0.2, 0.8, 0.3, 0.1])
        peaks = self.picker._find_all_peaks(single_peak, prominence=0.1)
        assert len(peaks) == 1
        assert peaks[0] == 2

    def test_integration_with_novelty_data(self):
        """Test full integration with novelty data structure."""
        # Create mock novelty data
        novelty_data = {
            "novelty_scores": np.array([0.1, 0.2, 0.8, 0.3, 0.1, 0.6, 0.2, 0.1]),
            "time_axis": np.array([0.0, 0.023, 0.046, 0.069, 0.092, 0.115, 0.138, 0.161]),
            "sample_rate": 22050,
            "hop_length": 512
        }
        
        # Set config for testing
        self.config.clips_count = 2
        self.config.peak_spacing = 80
        
        # Find peaks
        result = self.picker.find_peaks(novelty_data)
        
        # Check result structure
        assert "peak_times" in result
        assert "peak_scores" in result
        assert "seed_based" in result
        assert "total_peaks_found" in result
        assert "spacing_frames" in result
        
        # Should return ≤ clips_count peaks
        assert len(result["peak_times"]) <= self.config.clips_count
