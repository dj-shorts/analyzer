import pytest

from analyzer.config import Config
from analyzer.dynamic_cropper import DynamicCropper


def test_calculate_crop_dimensions_vertical():
    cfg = Config(input_path="video.mp4")
    cropper = DynamicCropper(cfg)
    w, h = cropper.calculate_crop_dimensions(1920, 1080, "vertical")
    # 9:16 => width should be 1080*9/16=607.5=>606 even, height=1080
    assert h == 1080
    assert w % 2 == 0
    assert 600 <= w <= 608


def test_calculate_crop_dimensions_square():
    cfg = Config(input_path="video.mp4")
    cropper = DynamicCropper(cfg)
    w, h = cropper.calculate_crop_dimensions(1920, 1080, "square")
    assert w == h
    assert w == 1080


def test_generate_crop_filter_static_position():
    cfg = Config(input_path="video.mp4")
    cropper = DynamicCropper(cfg)
    # single position -> static crop expression
    filter_str = cropper.generate_crop_filter(
        tracking_positions=[(960, 540)],
        video_width=1920,
        video_height=1080,
        crop_width=606,
        crop_height=1080,
        start_time=0.0,
        duration=2.0,
    )
    assert filter_str.startswith("crop=")
    assert ":" in filter_str


def test_validate_crop_positions_bounds():
    cfg = Config(input_path="video.mp4")
    cropper = DynamicCropper(cfg)
    positions = [(0, 0), (5000, 5000), (960, 540)]
    validated = cropper.validate_crop_positions(
        positions, video_width=1920, video_height=1080, crop_width=606, crop_height=1080
    )
    # y center must remain within [h/2, H-h/2] -> here H==crop_height => y becomes exactly center
    for x, y in validated:
        assert 606 // 2 <= x <= 1920 - 606 // 2
        assert y == 1080 // 2


