"""
Tests for Issue A6 - Pre-roll -10s and segment building (min/max length).
"""

import numpy as np
from pathlib import Path

from analyzer.config import Config
from analyzer.segments import SegmentBuilder


class TestPreRollSegmentsA6:
    """Tests for pre-roll and segment building with duration constraints (Issue A6)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(input_path=Path("test.mp4"))
        self.builder = SegmentBuilder(self.config)

    def test_pre_roll_calculation(self):
        """Test pre-roll calculation: start = max(0, center - pre_roll)."""
        # Create test data
        peaks_data = {
            "peak_times": np.array([10.0, 20.0, 5.0]),  # Centers at 10s, 20s, 5s
            "peak_scores": np.array([0.5, 0.8, 0.3]),
            "seed_based": np.array([False, True, False])
        }
        
        # Set pre-roll to 10 seconds
        self.config.pre_roll = 10.0
        
        # Build segments
        segments = self.builder.build_segments(peaks_data)
        
        # Check pre-roll calculation
        assert len(segments["segments"]) == 3
        
        # First peak at 10s: start = max(0, 10 - 10) = 0
        assert segments["segments"][0]["start"] == 0.0
        assert segments["segments"][0]["center"] == 10.0
        
        # Second peak at 20s: start = max(0, 20 - 10) = 10
        assert segments["segments"][1]["start"] == 10.0
        assert segments["segments"][1]["center"] == 20.0
        
        # Third peak at 5s: start = max(0, 5 - 10) = 0
        assert segments["segments"][2]["start"] == 0.0
        assert segments["segments"][2]["center"] == 5.0

    def test_segment_length_bounds(self):
        """Test segment length within min/max bounds."""
        # Create test data with different scores
        peaks_data = {
            "peak_times": np.array([10.0, 20.0, 30.0]),
            "peak_scores": np.array([0.0, 0.5, 1.0]),  # Low, medium, high scores
            "seed_based": np.array([False, False, False])
        }
        
        # Set min/max lengths
        self.config.min_clip_length = 15.0
        self.config.max_clip_length = 30.0
        
        # Build segments
        segments = self.builder.build_segments(peaks_data)
        
        # Check segment lengths
        assert len(segments["segments"]) == 3
        
        # Low score should give min length
        assert segments["segments"][0]["length"] == 15.0
        
        # Medium score should give intermediate length
        assert 15.0 < segments["segments"][1]["length"] < 30.0
        
        # High score should give max length
        assert segments["segments"][2]["length"] == 30.0

    def test_audio_duration_constraint(self):
        """Test that segments don't exceed audio duration."""
        # Create test data with peaks near the end
        peaks_data = {
            "peak_times": np.array([100.0, 110.0]),  # Peaks near end
            "peak_scores": np.array([0.8, 0.9]),
            "seed_based": np.array([False, False])
        }
        
        # Set audio duration to 120 seconds
        audio_duration = 120.0
        
        # Set pre-roll and segment lengths
        self.config.pre_roll = 10.0
        self.config.min_clip_length = 25.0
        self.config.max_clip_length = 30.0
        
        # Build segments with duration constraint
        segments = self.builder.build_segments(peaks_data, audio_duration)
        
        # Check that no segment exceeds audio duration
        for segment in segments["segments"]:
            assert segment["end"] <= audio_duration
            assert segment["start"] >= 0.0
            assert segment["length"] >= self.config.min_clip_length

    def test_segment_boundary_adjustment(self):
        """Test adjustment when segment would exceed duration."""
        # Create test data with peak very close to end
        peaks_data = {
            "peak_times": np.array([115.0]),  # Peak at 115s
            "peak_scores": np.array([0.8]),
            "seed_based": np.array([False])
        }
        
        # Set audio duration to 120 seconds
        audio_duration = 120.0
        
        # Set pre-roll and segment lengths
        self.config.pre_roll = 10.0
        self.config.min_clip_length = 20.0
        self.config.max_clip_length = 30.0
        
        # Build segments with duration constraint
        segments = self.builder.build_segments(peaks_data, audio_duration)
        
        segment = segments["segments"][0]
        
        # Check that segment is adjusted to fit within duration
        assert segment["end"] <= audio_duration
        assert segment["start"] >= 0.0
        assert segment["length"] >= self.config.min_clip_length
        
        # The segment should be adjusted to maintain minimum length
        assert segment["length"] >= 20.0

    def test_json_csv_output_format(self):
        """Test that segments contain required fields for JSON/CSV output."""
        # Create test data
        peaks_data = {
            "peak_times": np.array([10.0, 20.0]),
            "peak_scores": np.array([0.6, 0.8]),
            "seed_based": np.array([False, True])
        }
        
        # Build segments
        segments = self.builder.build_segments(peaks_data)
        
        # Check that all required fields are present
        required_fields = ["clip_id", "start", "end", "center", "score", "seed_based", "aligned", "length"]
        
        for segment in segments["segments"]:
            for field in required_fields:
                assert field in segment, f"Missing required field: {field}"
            
            # Check data types
            assert isinstance(segment["clip_id"], int)
            assert isinstance(segment["start"], (int, float))
            assert isinstance(segment["end"], (int, float))
            assert isinstance(segment["center"], (int, float))
            assert isinstance(segment["score"], (int, float))
            assert isinstance(segment["seed_based"], bool)
            assert isinstance(segment["aligned"], bool)
            assert isinstance(segment["length"], (int, float))

    def test_edge_cases(self):
        """Test edge cases for segment building."""
        # Test with empty peaks
        empty_peaks = {
            "peak_times": np.array([]),
            "peak_scores": np.array([]),
            "seed_based": np.array([])
        }
        
        segments = self.builder.build_segments(empty_peaks)
        assert segments["total_segments"] == 0
        assert segments["segments"] == []
        
        # Test with very short audio duration
        peaks_data = {
            "peak_times": np.array([5.0]),
            "peak_scores": np.array([0.8]),
            "seed_based": np.array([False])
        }
        
        # Very short audio duration
        audio_duration = 8.0
        self.config.min_clip_length = 10.0  # Longer than audio duration
        
        segments = self.builder.build_segments(peaks_data, audio_duration)
        
        # Should handle gracefully
        assert len(segments["segments"]) == 1
        segment = segments["segments"][0]
        assert segment["end"] <= audio_duration
        assert segment["start"] >= 0.0

    def test_precision_rounding(self):
        """Test that output values are properly rounded."""
        # Create test data that would result in floating point precision issues
        peaks_data = {
            "peak_times": np.array([10.123456789]),
            "peak_scores": np.array([0.123456789]),
            "seed_based": np.array([False])
        }
        
        segments = self.builder.build_segments(peaks_data)
        
        segment = segments["segments"][0]
        
        # Check that values are rounded to 3 decimal places
        assert segment["start"] == round(segment["start"], 3)
        assert segment["end"] == round(segment["end"], 3)
        assert segment["center"] == round(segment["center"], 3)
        assert segment["score"] == round(segment["score"], 3)
        assert segment["length"] == round(segment["length"], 3)

    def test_seed_based_flag_preservation(self):
        """Test that seed_based flag is correctly preserved."""
        # Create test data with mixed seed and auto peaks
        peaks_data = {
            "peak_times": np.array([10.0, 20.0, 30.0]),
            "peak_scores": np.array([0.6, 0.8, 0.7]),
            "seed_based": np.array([False, True, False])
        }
        
        segments = self.builder.build_segments(peaks_data)
        
        # Check that seed_based flags are preserved
        assert segments["segments"][0]["seed_based"] == False
        assert segments["segments"][1]["seed_based"] == True
        assert segments["segments"][2]["seed_based"] == False
