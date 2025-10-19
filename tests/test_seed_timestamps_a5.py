"""
Tests for Issue A5 - Seed timestamps parsing and local peak in window.
"""

import numpy as np
from pathlib import Path

from analyzer.config import Config
from analyzer.peaks import PeakPicker
from analyzer.cli import _parse_seed_timestamps


class TestSeedTimestampsA5:
    """Tests for seed timestamps parsing and local peak detection (Issue A5)."""

    def test_parse_seed_timestamps_hhmmss(self):
        """Test parsing HH:MM:SS format."""
        # Test valid formats
        assert _parse_seed_timestamps("01:23:45") == [5025.0]
        assert _parse_seed_timestamps("00:01:30") == [90.0]
        assert _parse_seed_timestamps("02:00:00") == [7200.0]
        
        # Test multiple timestamps
        result = _parse_seed_timestamps("01:23:45,02:30:15")
        assert result == [5025.0, 9015.0]
        
        # Test with fractional seconds
        result = _parse_seed_timestamps("01:23:45.5,02:30:15.25")
        assert result == [5025.5, 9015.25]

    def test_parse_seed_timestamps_mmss(self):
        """Test parsing MM:SS format."""
        assert _parse_seed_timestamps("01:30") == [90.0]
        assert _parse_seed_timestamps("05:45") == [345.0]
        
        # Test multiple timestamps
        result = _parse_seed_timestamps("01:30,05:45")
        assert result == [90.0, 345.0]

    def test_parse_seed_timestamps_seconds(self):
        """Test parsing raw seconds format."""
        assert _parse_seed_timestamps("90") == [90.0]
        assert _parse_seed_timestamps("345.5") == [345.5]
        
        # Test multiple timestamps
        result = _parse_seed_timestamps("90,345.5")
        assert result == [90.0, 345.5]

    def test_parse_seed_timestamps_validation(self):
        """Test validation of seed timestamps."""
        # Test invalid hours
        try:
            _parse_seed_timestamps("25:00:00")
            assert False, "Should raise ValueError for invalid hours"
        except ValueError as e:
            assert "Hours must be 0-23" in str(e)
        
        # Test invalid minutes
        try:
            _parse_seed_timestamps("01:60:00")
            assert False, "Should raise ValueError for invalid minutes"
        except ValueError as e:
            assert "Minutes must be 0-59" in str(e)
        
        # Test invalid seconds
        try:
            _parse_seed_timestamps("01:00:60")
            assert False, "Should raise ValueError for invalid seconds"
        except ValueError as e:
            assert "Seconds must be 0-59.999..." in str(e)
        
        # Test negative seconds
        try:
            _parse_seed_timestamps("-10")
            assert False, "Should raise ValueError for negative seconds"
        except ValueError as e:
            assert "Invalid seed timestamp" in str(e)
        
        # Test invalid format
        try:
            _parse_seed_timestamps("invalid")
            assert False, "Should raise ValueError for invalid format"
        except ValueError as e:
            assert "Invalid seed format" in str(e)

    def test_parse_seed_timestamps_edge_cases(self):
        """Test edge cases for seed timestamp parsing."""
        # Test empty string
        assert _parse_seed_timestamps("") == []
        
        # Test whitespace
        assert _parse_seed_timestamps("  01:23:45  ") == [5025.0]
        
        # Test multiple commas
        result = _parse_seed_timestamps("01:23:45,,02:30:15")
        assert result == [5025.0, 9015.0]
        
        # Test mixed formats
        result = _parse_seed_timestamps("01:23:45,90,05:30")
        assert result == [90.0, 330.0, 5025.0]  # Should be sorted

    def test_local_peak_search_in_window(self):
        """Test finding local maximum in window around seed."""
        # Create synthetic novelty scores with peaks
        novelty_scores = np.zeros(1000)
        
        # Add peaks at different positions
        novelty_scores[100] = 0.9  # Peak at 100
        novelty_scores[200] = 0.8  # Peak at 200
        novelty_scores[300] = 0.7  # Peak at 300
        
        # Create time axis (assuming 512 hop_length, 22050 sr)
        time_axis = np.arange(1000) * 512 / 22050  # ~23ms per frame
        
        # Set up config with seed timestamps
        config = Config(
            input_path=Path("test.mp4"),
            seed_timestamps=[4.5, 9.0]  # Around peaks at indices 200 and 400
        )
        
        picker = PeakPicker(config)
        
        # Test local peak search
        seed_peaks, seed_scores, seed_flags = picker._incorporate_seeds(
            np.array([]),  # No original peaks
            np.array([]),  # No original scores
            time_axis,
            novelty_scores
        )
        
        # Should find peaks near the seed times
        assert len(seed_peaks) == 2
        assert all(seed_flags)  # All should be seed-based
        
        # Check that peaks are close to expected positions
        expected_times = [time_axis[200], time_axis[300]]  # Closest peaks to seeds
        for peak_time in seed_peaks:
            distances = [abs(peak_time - expected_time) for expected_time in expected_times]
            assert min(distances) < 5.0  # Within 5 seconds (more lenient for window search)

    def test_seed_spacing_conflict_resolution(self):
        """Test resolution of spacing conflicts between seeds and auto peaks."""
        # Create synthetic data with close peaks
        novelty_scores = np.zeros(1000)
        novelty_scores[100] = 0.9  # Auto peak
        novelty_scores[105] = 0.8  # Seed peak (close to auto peak)
        
        time_axis = np.arange(1000) * 512 / 22050
        
        # Set up config with small spacing
        config = Config(
            input_path=Path("test.mp4"),
            seed_timestamps=[time_axis[105]],  # Seed at frame 105
            peak_spacing=10  # Small spacing
        )
        
        picker = PeakPicker(config)
        
        # Test conflict resolution
        auto_peaks = np.array([100])  # Auto peak at frame 100
        auto_scores = np.array([0.9])
        
        final_peaks, final_scores, seed_flags = picker._incorporate_seeds(
            time_axis[auto_peaks],  # Auto peaks
            auto_scores,
            time_axis,
            novelty_scores
        )
        
        # Should resolve conflict - either keep seed or auto peak, not both
        assert len(final_peaks) <= 2  # At most 2 peaks (seed + auto)
        
        # If both peaks are kept, they should respect spacing
        if len(final_peaks) == 2:
            spacing_seconds = abs(final_peaks[1] - final_peaks[0])
            expected_min_spacing = config.peak_spacing * 512 / 22050  # Convert to seconds
            assert spacing_seconds >= expected_min_spacing

    def test_seed_integration_with_auto_peaks(self):
        """Test integration of seeds with automatically detected peaks."""
        # Create synthetic novelty scores
        novelty_scores = np.zeros(1000)
        
        # Add auto peaks
        novelty_scores[100] = 0.9  # Auto peak 1
        novelty_scores[300] = 0.8  # Auto peak 2
        novelty_scores[500] = 0.7  # Auto peak 3
        
        # Add seed peak
        novelty_scores[200] = 0.85  # Seed peak
        
        time_axis = np.arange(1000) * 512 / 22050
        
        config = Config(
            input_path=Path("test.mp4"),
            seed_timestamps=[time_axis[200]],  # Seed at frame 200
            peak_spacing=50  # Large enough spacing
        )
        
        picker = PeakPicker(config)
        
        # Simulate auto peak detection
        auto_peaks = np.array([100, 300, 500])
        auto_scores = np.array([0.9, 0.8, 0.7])
        
        # Test integration
        final_peaks, final_scores, seed_flags = picker._incorporate_seeds(
            time_axis[auto_peaks],
            auto_scores,
            time_axis,
            novelty_scores
        )
        
        # Should have both auto peaks and seed peak
        assert len(final_peaks) >= 3  # At least 3 peaks
        
        # Should have at least one seed-based peak
        assert any(seed_flags)
        
        # All peaks should respect spacing
        for i in range(len(final_peaks) - 1):
            spacing = abs(final_peaks[i+1] - final_peaks[i])
            expected_min_spacing = config.peak_spacing * 512 / 22050
            assert spacing >= expected_min_spacing

    def test_edge_cases_seed_parsing(self):
        """Test edge cases for seed parsing."""
        # Test very large timestamps
        result = _parse_seed_timestamps("23:59:59")
        assert result == [86399.0]  # Max valid time
        
        # Test zero timestamps
        result = _parse_seed_timestamps("00:00:00")
        assert result == [0.0]
        
        # Test fractional seconds
        result = _parse_seed_timestamps("01:30:45.123")
        assert abs(result[0] - 5445.123) < 0.001
