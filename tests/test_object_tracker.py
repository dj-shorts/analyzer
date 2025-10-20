import numpy as np
from pathlib import Path
import pytest

from analyzer.config import Config
from analyzer.object_tracker import ObjectTracker


def test_fallback_tracking_data_structure():
    cfg = Config(input_path=Path("video.mp4"))
    tracker = ObjectTracker(cfg)
    data = tracker._create_fallback_tracking_data()
    assert "crop_positions" in data
    assert "tracking_available" in data
    assert data["tracking_available"] is False


def test_interpolation_returns_centers_when_no_tracking():
    cfg = Config(input_path=Path("video.mp4"))
    tracker = ObjectTracker(cfg)
    tracking_data = tracker._create_fallback_tracking_data()
    times = np.linspace(0, 1, 5)
    positions = tracker.interpolate_to_export_timeline(tracking_data, times)
    assert len(positions) == len(times)
    # with fallback dimensions 1920x1080 -> center 960,540
    assert positions[0] == (1920 // 2, 1080 // 2)


