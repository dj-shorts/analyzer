"""
Tests for MVP Analyzer.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from analyzer.audio import AudioExtractor
from analyzer.config import Config
from analyzer.core import Analyzer
from analyzer.export import ResultExporter
from analyzer.novelty import NoveltyDetector
from analyzer.peaks import PeakPicker
from analyzer.segments import SegmentBuilder


class TestConfig:
    """Test configuration validation."""

    def test_config_creation(self):
        """Test basic config creation."""
        config = Config(input_path=Path("test.mp4"))
        assert config.input_path == Path("test.mp4")
        assert config.clips_count == 6
        assert config.min_clip_length == 15.0
        assert config.max_clip_length == 30.0

    def test_config_validation(self):
        """Test config validation rules."""
        # Test max_length > min_length validation
        with pytest.raises(ValueError):
            Config(
                input_path=Path("test.mp4"), min_clip_length=20.0, max_clip_length=15.0
            )

    def test_seed_timestamps_validation(self):
        """Test seed timestamps validation."""
        # Test negative seed timestamps
        with pytest.raises(ValueError):
            Config(input_path=Path("test.mp4"), seed_timestamps=[-10.0, 20.0])


class TestNoveltyDetector:
    """Test novelty detection functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(input_path=Path("test.mp4"))
        self.detector = NoveltyDetector(self.config)

    def test_robust_normalize(self):
        """Test robust normalization function."""
        # Test normal case
        data = np.array([1, 2, 3, 4, 5, 10, 20, 30, 40, 50])
        normalized = self.detector._robust_normalize(data)

        assert np.all(normalized >= 0)
        assert np.all(normalized <= 1)
        assert normalized[0] == 0  # 5th percentile should be 0
        assert normalized[-1] == 1  # 95th percentile should be 1

    def test_robust_normalize_edge_cases(self):
        """Test robust normalization edge cases."""
        # Test all same values
        data = np.array([5, 5, 5, 5, 5])
        normalized = self.detector._robust_normalize(data)
        assert np.all(normalized == 0)

        # Test empty array
        data = np.array([])
        normalized = self.detector._robust_normalize(data)
        assert len(normalized) == 0


class TestPeakPicker:
    """Test peak detection functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(input_path=Path("test.mp4"))
        self.picker = PeakPicker(self.config)

    def test_find_peaks_basic(self):
        """Test basic peak detection."""
        # Create synthetic novelty data with known peaks
        novelty_scores = np.array([0.1, 0.2, 0.8, 0.3, 0.1, 0.9, 0.2, 0.1])
        time_axis = np.linspace(0, 7, 8)

        novelty_data = {
            "novelty_scores": novelty_scores,
            "time_axis": time_axis,
            "sample_rate": 22050,
            "hop_length": 512,
        }

        peaks_data = self.picker.find_peaks(novelty_data)

        assert "peak_times" in peaks_data
        assert "peak_scores" in peaks_data
        assert "seed_based" in peaks_data
        assert len(peaks_data["peak_times"]) <= self.config.clips_count

    def test_incorporate_seeds(self):
        """Test seed timestamp incorporation."""
        self.config.seed_timestamps = [2.0, 6.0]

        peak_times = np.array([1.0, 3.0])
        peak_scores = np.array([0.8, 0.7])
        time_axis = np.linspace(0, 7, 8)
        novelty_scores = np.array([0.1, 0.2, 0.8, 0.3, 0.1, 0.9, 0.2, 0.1])

        final_peaks, final_scores, seed_flags = self.picker._incorporate_seeds(
            peak_times, peak_scores, time_axis, novelty_scores
        )

        assert len(final_peaks) > 0
        assert len(seed_flags) == len(final_peaks)
        assert np.any(seed_flags)  # At least one seed-based peak


class TestSegmentBuilder:
    """Test segment building functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(input_path=Path("test.mp4"))
        self.builder = SegmentBuilder(self.config)

    def test_calculate_segment_length(self):
        """Test segment length calculation."""
        # Test low score (should be closer to min_clip_length)
        length_low = self.builder._calculate_segment_length(0.2)
        assert length_low >= self.config.min_clip_length
        assert (
            length_low < (self.config.min_clip_length + self.config.max_clip_length) / 2
        )

        # Test high score (should be closer to max_clip_length)
        length_high = self.builder._calculate_segment_length(0.8)
        assert length_high > length_low
        assert length_high <= self.config.max_clip_length

        # Test edge cases
        assert (
            self.builder._calculate_segment_length(0.0) == self.config.min_clip_length
        )
        assert (
            self.builder._calculate_segment_length(1.0) == self.config.max_clip_length
        )

    def test_build_segments(self):
        """Test segment building from peaks."""
        peaks_data = {
            "peak_times": np.array([10.0, 30.0, 50.0]),
            "peak_scores": np.array([0.8, 0.6, 0.9]),
            "seed_based": np.array([False, True, False]),
        }

        segments_data = self.builder.build_segments(peaks_data)

        assert "segments" in segments_data
        assert len(segments_data["segments"]) == 3

        for segment in segments_data["segments"]:
            assert "start" in segment
            assert "end" in segment
            assert "center" in segment
            assert "score" in segment
            assert segment["start"] >= 0
            assert segment["end"] > segment["start"]


class TestResultExporter:
    """Test result export functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(
            input_path=Path("test.mp4"),
            output_json=Path("test_highlights.json"),
            output_csv=Path("test_highlights.csv"),
        )
        self.exporter = ResultExporter(self.config)

    def test_export_csv(self, tmp_path):
        """Test CSV export."""
        segments = [
            {
                "clip_id": 1,
                "start": 10.0,
                "end": 25.0,
                "center": 15.0,
                "score": 0.8,
                "seed_based": False,
                "aligned": False,
                "length": 15.0,
            }
        ]

        # Override output path to tmp directory
        self.config.output_csv = tmp_path / "test.csv"

        csv_path = self.exporter._export_csv(segments)

        assert csv_path.exists()
        assert csv_path.name == "test.csv"

    def test_export_json(self, tmp_path):
        """Test JSON export."""
        segments = [
            {
                "clip_id": 1,
                "start": 10.0,
                "end": 25.0,
                "center": 15.0,
                "score": 0.8,
                "seed_based": False,
                "aligned": False,
                "length": 15.0,
            }
        ]

        audio_data = {"duration": 120.0, "sample_rate": 22050}

        # Override output path to tmp directory
        self.config.output_json = tmp_path / "test.json"

        json_path = self.exporter._export_json(segments, audio_data)

        assert json_path.exists()
        assert json_path.name == "test.json"


# Integration test
class TestAnalyzerIntegration:
    """Integration tests for the complete analyzer pipeline."""

    @patch("analyzer.audio.AudioExtractor.extract")
    @patch("analyzer.novelty.NoveltyDetector.compute_novelty")
    @patch("analyzer.peaks.PeakPicker.find_peaks")
    @patch("analyzer.segments.SegmentBuilder.build_segments")
    @patch("analyzer.export.ResultExporter.export")
    def test_analyzer_pipeline(
        self, mock_export, mock_segments, mock_peaks, mock_novelty, mock_audio
    ):
        """Test the complete analyzer pipeline with mocked components."""
        # Set up mocks
        mock_audio.return_value = {
            "audio": np.random.randn(1000),
            "sample_rate": 22050,
            "duration": 60.0,
        }

        mock_novelty.return_value = {
            "novelty_scores": np.random.rand(100),
            "time_axis": np.linspace(0, 60, 100),
        }

        mock_peaks.return_value = {
            "peak_times": np.array([10.0, 30.0]),
            "peak_scores": np.array([0.8, 0.6]),
            "seed_based": np.array([False, True]),
        }

        mock_segments.return_value = {
            "segments": [
                {
                    "clip_id": 1,
                    "start": 5.0,
                    "end": 20.0,
                    "center": 10.0,
                    "score": 0.8,
                    "seed_based": False,
                    "aligned": False,
                    "length": 15.0,
                }
            ]
        }

        mock_export.return_value = {
            "csv_path": Path("test.csv"),
            "json_path": Path("test.json"),
            "segments_count": 1,
        }

        # Create analyzer and run pipeline
        config = Config(input_path=Path("test.mp4"))
        analyzer = Analyzer(config)

        results = analyzer.analyze()

        # Verify all components were called
        mock_audio.assert_called_once()
        mock_novelty.assert_called_once()
        mock_peaks.assert_called_once()
        mock_segments.assert_called_once()
        # Verify export was called twice (initial export + final export with metrics)
        assert mock_export.call_count == 2

        # Verify results structure
        assert "csv_path" in results
        assert "json_path" in results
