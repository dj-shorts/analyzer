"""
Tests for Epic C: Motion Analysis with Optical Flow Farnebäck.

Tests motion detection functionality including:
- Motion feature extraction from video
- Motion score normalization and smoothing
- Timeline interpolation
- Audio-motion score combination
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from analyzer.config import Config
from analyzer.motion import MotionDetector


class TestMotionDetectorEpicC:
    """Test motion detection functionality for Epic C."""
    
    def test_motion_detector_initialization(self):
        """Test MotionDetector initialization."""
        config = Config(input_path="test.mp4", with_motion=True)
        detector = MotionDetector(config)
        
        assert detector.config == config
        assert isinstance(detector.flow_params, dict)
        assert detector.target_fps == 4.0
        assert detector.motion_window_size == 0.5
    
    def test_normalize_motion_scores(self):
        """Test _normalize_motion_scores method."""
        config = Config(input_path="test.mp4")
        detector = MotionDetector(config)
        
        # Test normal case
        scores = np.array([10, 20, 30, 40, 50])
        normalized = detector._normalize_motion_scores(scores)
        
        assert np.all(normalized >= 0) and np.all(normalized <= 1)
        assert normalized[0] == 0.0  # 5th percentile
        assert normalized[-1] == 1.0  # 95th percentile
        
        # Test edge case: flat scores
        flat_scores = np.array([25, 25, 25])
        normalized_flat = detector._normalize_motion_scores(flat_scores)
        # For flat scores, normalization should return zeros (since min=max)
        assert np.allclose(normalized_flat, 0.0)
        
        # Test edge case: empty scores
        empty_scores = np.array([])
        normalized_empty = detector._normalize_motion_scores(empty_scores)
        assert len(normalized_empty) == 0
    
    def test_smooth_motion_scores(self):
        """Test _smooth_motion_scores method."""
        config = Config(input_path="test.mp4")
        detector = MotionDetector(config)
        
        # Test normal case
        scores = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        times = np.array([0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75])
        smoothed = detector._smooth_motion_scores(scores, times)
        
        # Should be same length as input
        assert len(smoothed) == len(scores)
        # Should be smoothed (less variation)
        assert np.std(smoothed) <= np.std(scores)
        
        # Test edge case: single score
        single_score = np.array([1.0])
        single_time = np.array([0.0])
        smoothed_single = detector._smooth_motion_scores(single_score, single_time)
        assert len(smoothed_single) == 1
    
    def test_interpolate_to_audio_timeline(self):
        """Test interpolate_to_audio_timeline method."""
        config = Config(input_path="test.mp4")
        detector = MotionDetector(config)
        
        # Test normal case
        motion_data = {
            "motion_scores": np.array([0.1, 0.5, 0.9]),
            "motion_times": np.array([0.0, 5.0, 10.0]),
            "motion_available": True
        }
        audio_times = np.array([0.0, 2.5, 5.0, 7.5, 10.0])
        
        interpolated = detector.interpolate_to_audio_timeline(motion_data, audio_times)
        
        assert len(interpolated) == len(audio_times)
        assert np.all(interpolated >= 0) and np.all(interpolated <= 1)
        # Should interpolate correctly
        assert np.allclose(interpolated, np.array([0.1, 0.3, 0.5, 0.7, 0.9]))
        
        # Test with motion unavailable
        motion_data_unavailable = {
            "motion_scores": np.array([0.5]),
            "motion_times": np.array([0.0]),
            "motion_available": False
        }
        interpolated_unavailable = detector.interpolate_to_audio_timeline(motion_data_unavailable, audio_times)
        assert np.allclose(interpolated_unavailable, 0.5)
    
    def test_combine_audio_and_motion_scores(self):
        """Test combine_audio_and_motion_scores method."""
        config = Config(input_path="test.mp4")
        detector = MotionDetector(config)
        
        # Test normal case
        audio_scores = np.array([0.2, 0.8])
        motion_scores = np.array([0.4, 0.6])
        
        combined = detector.combine_audio_and_motion_scores(audio_scores, motion_scores)
        
        # Should be weighted combination: 0.6*audio + 0.4*motion
        expected = 0.6 * audio_scores + 0.4 * motion_scores
        assert np.allclose(combined, expected)
        assert np.all(combined >= 0) and np.all(combined <= 1)
        
        # Test edge case: different lengths
        audio_long = np.array([0.2, 0.8, 0.5])
        combined_mismatch = detector.combine_audio_and_motion_scores(audio_long, motion_scores)
        # Should return audio scores when lengths don't match
        assert np.allclose(combined_mismatch, audio_long)
    
    def test_create_fallback_motion_data(self):
        """Test _create_fallback_motion_data method."""
        config = Config(input_path="test.mp4")
        detector = MotionDetector(config)
        
        fallback = detector._create_fallback_motion_data()
        
        assert "motion_scores" in fallback
        assert "motion_times" in fallback
        assert "sample_rate" in fallback
        assert "total_frames" in fallback
        assert "video_duration" in fallback
        assert "motion_available" in fallback
        
        assert fallback["motion_available"] is False
        assert len(fallback["motion_scores"]) == 1
        assert fallback["motion_scores"][0] == 0.5  # Neutral score
        assert fallback["sample_rate"] == detector.target_fps
    
    @patch('cv2.VideoCapture')
    def test_extract_motion_features_fallback(self, mock_video_capture):
        """Test motion feature extraction fallback behavior."""
        config = Config(
            input_path="test.mp4",
            with_motion=True,
            clips_count=3,
            peak_spacing=80,
            min_clip_length=15.0,
            max_clip_length=30.0,
            pre_roll=10.0
        )
        
        detector = MotionDetector(config)
        
        # Mock video capture to fail
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap
        
        result = detector.extract_motion_features(Path("test.mp4"))
        
        assert "motion_scores" in result
        assert "motion_times" in result
        assert "sample_rate" in result
        assert "total_frames" in result
        assert "video_duration" in result
        assert "motion_available" in result
        
        # Should use fallback due to video not opening
        assert result["motion_available"] is False
        assert len(result["motion_scores"]) == 1
        assert result["motion_scores"][0] == 0.5
    
    def test_extract_motion_features_file_not_found(self):
        """Test motion feature extraction when file doesn't exist."""
        config = Config(
            input_path="nonexistent.mp4",
            with_motion=True,
            clips_count=3,
            peak_spacing=80,
            min_clip_length=15.0,
            max_clip_length=30.0,
            pre_roll=10.0
        )
        
        detector = MotionDetector(config)
        
        result = detector.extract_motion_features(Path("nonexistent.mp4"))
        
        assert result["motion_available"] is False
        assert len(result["motion_scores"]) == 1
        assert result["motion_scores"][0] == 0.5
    
    def test_motion_analysis_integration(self):
        """Test motion analysis integration with audio timeline."""
        config = Config(
            input_path="test.mp4",
            with_motion=True,
            clips_count=3,
            peak_spacing=80,
            min_clip_length=15.0,
            max_clip_length=30.0,
            pre_roll=10.0
        )
        
        detector = MotionDetector(config)
        
        # Simulate motion data
        motion_data = {
            "motion_scores": np.array([0.1, 0.3, 0.5, 0.7, 0.9]),
            "motion_times": np.array([0.0, 1.0, 2.0, 3.0, 4.0]),
            "motion_available": True,
            "sample_rate": 4.0,
            "total_frames": 5,
            "video_duration": 4.0
        }
        
        # Simulate audio timeline
        audio_times = np.linspace(0, 4, 20)  # 20 audio samples
        
        # Test interpolation
        interpolated = detector.interpolate_to_audio_timeline(motion_data, audio_times)
        
        assert len(interpolated) == len(audio_times)
        assert np.all(interpolated >= 0) and np.all(interpolated <= 1)
        
        # Test combination with audio scores
        audio_scores = np.random.random(len(audio_times))
        combined = detector.combine_audio_and_motion_scores(audio_scores, interpolated)
        
        assert len(combined) == len(audio_scores)
        assert np.all(combined >= 0) and np.all(combined <= 1)
        
        # Should be weighted combination
        expected = 0.6 * audio_scores + 0.4 * interpolated
        assert np.allclose(combined, expected)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
