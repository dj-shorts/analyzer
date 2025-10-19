"""
Tests for Epic D3: People detection and auto-reframe functionality.
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import cv2

from analyzer.config import Config
from analyzer.people_detector import PeopleDetector


class TestPeopleDetectorEpicD3:
    """Test people detection functionality for Epic D3."""

    def test_people_detector_initialization(self):
        """Test PeopleDetector initialization."""
        config = Config(input_path="test.mp4", auto_reframe=True)
        detector = PeopleDetector(config)
        
        assert detector.config == config
        assert detector.hog is not None
        assert detector.hit_threshold == 0.0
        assert detector.win_stride == (8, 8)
        assert detector.padding == (32, 32)
        assert detector.scale == 1.05

    def test_detect_people_in_frame_basic(self):
        """Test people detection in frame (basic functionality)."""
        config = Config(input_path="test.mp4")
        detector = PeopleDetector(config)
        
        # Create empty frame (no people)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # This will likely return empty results on empty frame
        boxes = detector.detect_people_in_frame(frame)
        
        # Should return a list (even if empty)
        assert isinstance(boxes, list)

    def test_calculate_center_x_empty(self):
        """Test center X calculation with no people."""
        config = Config(input_path="test.mp4")
        detector = PeopleDetector(config)
        
        center_x = detector.calculate_center_x([])
        
        assert center_x is None

    def test_calculate_center_x_single_person(self):
        """Test center X calculation with single person."""
        config = Config(input_path="test.mp4")
        detector = PeopleDetector(config)
        
        boxes = [(100, 50, 80, 160)]  # x=100, width=80, center=140
        center_x = detector.calculate_center_x(boxes)
        
        assert center_x == 140.0

    def test_calculate_center_x_multiple_people(self):
        """Test center X calculation with multiple people."""
        config = Config(input_path="test.mp4")
        detector = PeopleDetector(config)
        
        boxes = [
            (100, 50, 80, 160),   # center_x = 140
            (300, 80, 90, 180),   # center_x = 345
            (200, 60, 70, 140)    # center_x = 235
        ]
        center_x = detector.calculate_center_x(boxes)
        
        # Median of [140, 235, 345] is 235
        assert center_x == 235.0

    def test_detect_people_in_video_segment_file_not_found(self):
        """Test people detection with nonexistent video file."""
        config = Config(input_path="test.mp4")
        detector = PeopleDetector(config)
        
        video_path = Path("nonexistent.mp4")
        start_time = 10.0
        duration = 5.0
        
        result = detector.detect_people_in_video_segment(video_path, start_time, duration)
        
        assert result["success"] is False
        assert "error" in result
        assert result["center_x"] is None

    def test_detect_people_in_video_segment_video_error(self):
        """Test people detection with video file error."""
        config = Config(input_path="test.mp4")
        detector = PeopleDetector(config)
        
        video_path = Path("nonexistent.mp4")
        start_time = 10.0
        duration = 5.0
        
        with patch('cv2.VideoCapture') as mock_cap:
            mock_cap_instance = Mock()
            mock_cap_instance.isOpened.return_value = False
            mock_cap.return_value = mock_cap_instance
            
            result = detector.detect_people_in_video_segment(video_path, start_time, duration)
            
            assert result["success"] is False
            assert "error" in result
            assert result["center_x"] is None

    def test_calculate_crop_window_center(self):
        """Test crop window calculation around center."""
        config = Config(input_path="test.mp4")
        detector = PeopleDetector(config)
        
        center_x = 320.0
        frame_width = 1920
        frame_height = 1080
        target_width = 1080
        target_height = 1920
        
        crop_x, crop_y, crop_width, crop_height = detector.calculate_crop_window(
            center_x, frame_width, frame_height, target_width, target_height
        )
        
        # Should crop around center X
        assert crop_x >= 0
        assert crop_x + crop_width <= frame_width
        assert crop_y >= 0
        assert crop_y + crop_height <= frame_height
        assert crop_width > 0
        assert crop_height > 0

    def test_calculate_crop_window_edge_case(self):
        """Test crop window calculation at edge."""
        config = Config(input_path="test.mp4")
        detector = PeopleDetector(config)
        
        center_x = 100.0  # Near left edge
        frame_width = 1920
        frame_height = 1080
        target_width = 1080
        target_height = 1920
        
        crop_x, crop_y, crop_width, crop_height = detector.calculate_crop_window(
            center_x, frame_width, frame_height, target_width, target_height
        )
        
        # Should not go negative
        assert crop_x >= 0
        assert crop_y >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
