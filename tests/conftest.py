"""
Pytest configuration for the analyzer test suite.
"""

import pytest


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory."""
    from pathlib import Path

    return Path(__file__).parent.parent / "data"


@pytest.fixture(scope="session")
def test_video_file(test_data_dir):
    """Provide path to test video file."""
    video_file = test_data_dir / "test_video.mp4"
    if not video_file.exists():
        pytest.skip("Test video file not found")
    return video_file


@pytest.fixture(scope="session")
def test_audio_file(test_data_dir):
    """Provide path to test audio file."""
    audio_file = test_data_dir / "test_audio.wav"
    if not audio_file.exists():
        pytest.skip("Test audio file not found")
    return audio_file


# Custom pytest markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit test")
    config.addinivalue_line("markers", "integration: Integration test")
    config.addinivalue_line("markers", "performance: Performance test")
    config.addinivalue_line("markers", "regression: Regression test")
    config.addinivalue_line("markers", "slow: Slow test (> 5s)")
    config.addinivalue_line("markers", "requires_ffmpeg: Requires ffmpeg")
    config.addinivalue_line("markers", "requires_video: Requires video file")
