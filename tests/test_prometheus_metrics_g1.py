"""
Epic G1: Prometheus Metrics Tests

Tests for Prometheus metrics collection and export functionality.
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from analyzer.metrics import (
    AnalysisMetrics,
    AnalysisStage,
    MetricsCollector,
    StageTiming,
    format_prometheus_metrics,
)


class TestPrometheusMetricsEpicG1:
    """Tests for Prometheus metrics functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.collector = MetricsCollector()

    def teardown_method(self):
        """Clean up after tests."""
        # Finish any ongoing collection
        try:
            self.collector.finish()
        except Exception:
            pass

    def test_metrics_collector_initialization(self):
        """Test metrics collector initialization."""
        assert self.collector.metrics is not None
        assert self.collector.start_time > 0
        assert AnalysisStage.TOTAL in self.collector.metrics.stage_timings

    def test_stage_timing(self):
        """Test stage timing functionality."""
        # Start a stage
        self.collector.start_stage(AnalysisStage.AUDIO_EXTRACTION)

        # Check timing was started
        assert AnalysisStage.AUDIO_EXTRACTION in self.collector.metrics.stage_timings
        timing = self.collector.metrics.stage_timings[AnalysisStage.AUDIO_EXTRACTION]
        assert timing.start_time > 0
        assert timing.end_time is None
        assert timing.duration is None

        # Finish the stage
        time.sleep(0.01)  # Small delay to ensure duration > 0
        self.collector.finish_stage(AnalysisStage.AUDIO_EXTRACTION)

        # Check timing was finished
        assert timing.end_time is not None
        assert timing.duration is not None
        assert timing.duration > 0

    def test_audio_metrics(self):
        """Test audio metrics setting."""
        duration = 30.5
        sample_rate = 22050
        bytes_count = 1024000

        self.collector.set_audio_metrics(duration, sample_rate, bytes_count)

        assert self.collector.metrics.audio_duration == duration
        assert self.collector.metrics.audio_sample_rate == sample_rate
        assert self.collector.metrics.audio_bytes == bytes_count

    def test_video_metrics(self):
        """Test video metrics setting."""
        duration = 30.5
        bytes_count = 2048000
        width = 1920
        height = 1080

        self.collector.set_video_metrics(duration, bytes_count, width, height)

        assert self.collector.metrics.video_duration == duration
        assert self.collector.metrics.video_bytes == bytes_count
        assert self.collector.metrics.video_width == width
        assert self.collector.metrics.video_height == height

    def test_novelty_metrics(self):
        """Test novelty metrics setting."""
        peaks_count = 5
        frames_count = 1000

        self.collector.set_novelty_metrics(peaks_count, frames_count)

        assert self.collector.metrics.novelty_peaks_count == peaks_count
        assert self.collector.metrics.novelty_frames_count == frames_count

    def test_processing_metrics(self):
        """Test processing metrics setting."""
        clips_generated = 3
        segments_built = 5

        self.collector.set_processing_metrics(clips_generated, segments_built)

        assert self.collector.metrics.clips_generated == clips_generated
        assert self.collector.metrics.segments_built == segments_built

    def test_configuration_metrics(self):
        """Test configuration metrics setting."""
        clips_requested = 6
        min_length = 15.0
        max_length = 30.0
        with_motion = True
        align_to_beat = False

        self.collector.set_configuration_metrics(
            clips_requested, min_length, max_length, with_motion, align_to_beat
        )

        assert self.collector.metrics.clips_requested == clips_requested
        assert self.collector.metrics.min_clip_length == min_length
        assert self.collector.metrics.max_clip_length == max_length
        assert self.collector.metrics.with_motion == with_motion
        assert self.collector.metrics.align_to_beat == align_to_beat

    def test_memory_peak_metrics(self):
        """Test memory peak metrics setting."""
        peak_mb = 150.5

        self.collector.set_memory_peak(peak_mb)

        assert self.collector.metrics.memory_peak_mb == peak_mb

    def test_metrics_finish(self):
        """Test metrics collection finish."""
        # Set some test metrics
        self.collector.set_audio_metrics(30.0, 22050, 1024000)
        self.collector.set_novelty_metrics(5, 1000)

        # Finish collection
        final_metrics = self.collector.finish()

        assert final_metrics.total_duration > 0
        assert final_metrics.audio_duration == 30.0
        assert final_metrics.novelty_peaks_count == 5

    def test_json_metrics_export(self):
        """Test JSON metrics export."""
        # Set comprehensive metrics
        self.collector.set_audio_metrics(30.0, 22050, 1024000)
        self.collector.set_video_metrics(30.0, 2048000, 1920, 1080)
        self.collector.set_novelty_metrics(5, 1000)
        self.collector.set_processing_metrics(3, 5)
        self.collector.set_configuration_metrics(3, 15.0, 30.0, False, False)
        self.collector.set_memory_peak(150.5)

        # Finish and get JSON metrics
        final_metrics = self.collector.finish()
        json_metrics = final_metrics.to_json_metrics()

        # Verify JSON structure
        assert "timings" in json_metrics
        assert "novelty" in json_metrics
        assert "audio" in json_metrics
        assert "video" in json_metrics
        assert "processing" in json_metrics
        assert "configuration" in json_metrics

        # Verify specific values
        assert json_metrics["audio"]["duration_seconds"] == 30.0
        assert json_metrics["novelty"]["peaks_count"] == 5
        assert json_metrics["processing"]["clips_generated"] == 3
        assert json_metrics["configuration"]["clips_requested"] == 3

    def test_prometheus_metrics_format(self):
        """Test Prometheus metrics formatting."""
        # Set test metrics
        self.collector.set_audio_metrics(30.0, 22050, 1024000)
        self.collector.set_novelty_metrics(5, 1000)
        self.collector.set_processing_metrics(3, 5)
        self.collector.set_configuration_metrics(3, 15.0, 30.0, False, False)

        final_metrics = self.collector.finish()
        prometheus_metrics = format_prometheus_metrics(final_metrics)

        # Verify Prometheus format
        assert "# HELP" in prometheus_metrics
        assert "# TYPE" in prometheus_metrics
        assert "job_duration_seconds" in prometheus_metrics
        assert "novelty_peaks_count" in prometheus_metrics
        assert "audio_duration_seconds" in prometheus_metrics
        assert "clips_generated" in prometheus_metrics

        # Verify specific metric values
        assert "novelty_peaks_count 5" in prometheus_metrics
        assert "audio_duration_seconds 30.0" in prometheus_metrics
        assert "clips_generated 3" in prometheus_metrics
        assert "with_motion_enabled 0" in prometheus_metrics
        assert "align_to_beat_enabled 0" in prometheus_metrics

    def test_stage_duration_calculation(self):
        """Test stage duration calculation."""
        # Start and finish multiple stages
        self.collector.start_stage(AnalysisStage.AUDIO_EXTRACTION)
        time.sleep(0.01)
        self.collector.finish_stage(AnalysisStage.AUDIO_EXTRACTION)

        self.collector.start_stage(AnalysisStage.NOVELTY_DETECTION)
        time.sleep(0.02)
        self.collector.finish_stage(AnalysisStage.NOVELTY_DETECTION)

        # Check durations
        audio_duration = self.collector.metrics.get_stage_duration(
            AnalysisStage.AUDIO_EXTRACTION
        )
        novelty_duration = self.collector.metrics.get_stage_duration(
            AnalysisStage.NOVELTY_DETECTION
        )

        assert audio_duration > 0
        assert novelty_duration > 0
        assert novelty_duration > audio_duration  # Should be longer due to longer sleep

    def test_multiple_stage_timing(self):
        """Test timing multiple stages."""
        stages = [
            AnalysisStage.AUDIO_EXTRACTION,
            AnalysisStage.NOVELTY_DETECTION,
            AnalysisStage.PEAK_PICKING,
            AnalysisStage.SEGMENT_BUILDING,
            AnalysisStage.EXPORT,
        ]

        # Time all stages
        for stage in stages:
            self.collector.start_stage(stage)
            time.sleep(0.005)  # Small delay
            self.collector.finish_stage(stage)

        # Finish total
        final_metrics = self.collector.finish()

        # Check all stages have durations
        for stage in stages:
            duration = final_metrics.get_stage_duration(stage)
            assert duration > 0

        # Check total duration is reasonable
        assert final_metrics.total_duration > 0.025  # At least 5 * 0.005

    def test_metrics_collector_context_manager(self):
        """Test metrics collector as context manager."""
        with MetricsCollector() as collector:
            collector.set_audio_metrics(30.0, 22050, 1024000)
            collector.set_novelty_metrics(5, 1000)
            # Collector should be automatically finished

        # Metrics should be available
        assert collector.metrics.total_duration > 0
        assert collector.metrics.audio_duration == 30.0
        assert collector.metrics.novelty_peaks_count == 5

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Test finishing stage that wasn't started
        self.collector.finish_stage(AnalysisStage.AUDIO_EXTRACTION)
        # Should not raise exception

        # Test getting duration of unfinished stage
        self.collector.start_stage(AnalysisStage.NOVELTY_DETECTION)
        duration = self.collector.metrics.get_stage_duration(
            AnalysisStage.NOVELTY_DETECTION
        )
        assert duration == 0  # Should return 0 for unfinished stage

        # Test negative values
        self.collector.set_audio_metrics(-1.0, -1, -1)
        assert self.collector.metrics.audio_duration == -1.0
        assert self.collector.metrics.audio_sample_rate == -1
        assert self.collector.metrics.audio_bytes == -1

    def test_prometheus_metrics_file_export(self):
        """Test exporting Prometheus metrics to file."""
        # Set test metrics
        self.collector.set_audio_metrics(30.0, 22050, 1024000)
        self.collector.set_novelty_metrics(5, 1000)
        self.collector.set_processing_metrics(3, 5)

        final_metrics = self.collector.finish()

        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".prom", delete=False) as f:
            metrics_file = f.name

        try:
            prometheus_metrics = format_prometheus_metrics(final_metrics)
            with open(metrics_file, "w") as f:
                f.write(prometheus_metrics)

            # Verify file was created and contains metrics
            assert Path(metrics_file).exists()
            with open(metrics_file) as f:
                content = f.read()

            assert "job_duration_seconds" in content
            assert "novelty_peaks_count 5" in content
            assert "audio_duration_seconds 30.0" in content

        finally:
            Path(metrics_file).unlink()

    def test_json_metrics_file_export(self):
        """Test exporting JSON metrics to file."""
        # Set test metrics
        self.collector.set_audio_metrics(30.0, 22050, 1024000)
        self.collector.set_novelty_metrics(5, 1000)
        self.collector.set_processing_metrics(3, 5)

        final_metrics = self.collector.finish()

        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            metrics_file = f.name

        try:
            json_metrics = final_metrics.to_json_metrics()
            with open(metrics_file, "w") as f:
                json.dump(json_metrics, f, indent=2)

            # Verify file was created and contains metrics
            assert Path(metrics_file).exists()
            with open(metrics_file) as f:
                content = json.load(f)

            assert "timings" in content
            assert "novelty" in content
            assert "audio" in content
            assert content["audio"]["duration_seconds"] == 30.0
            assert content["novelty"]["peaks_count"] == 5

        finally:
            Path(metrics_file).unlink()

    def test_analysis_stage_enum(self):
        """Test AnalysisStage enum values."""
        assert AnalysisStage.INITIALIZATION.value == "initialization"
        assert AnalysisStage.AUDIO_EXTRACTION.value == "audio_extraction"
        assert AnalysisStage.NOVELTY_DETECTION.value == "novelty_detection"
        assert AnalysisStage.PEAK_PICKING.value == "peak_picking"
        assert AnalysisStage.BEAT_TRACKING.value == "beat_tracking"
        assert AnalysisStage.SEGMENT_BUILDING.value == "segment_building"
        assert AnalysisStage.MOTION_ANALYSIS.value == "motion_analysis"
        assert AnalysisStage.EXPORT.value == "export"
        assert AnalysisStage.TOTAL.value == "total"

    def test_stage_timing_dataclass(self):
        """Test StageTiming dataclass."""
        stage = AnalysisStage.AUDIO_EXTRACTION
        start_time = time.time()

        timing = StageTiming(stage=stage, start_time=start_time)

        assert timing.stage == stage
        assert timing.start_time == start_time
        assert timing.end_time is None
        assert timing.duration is None

        # Test finish method
        timing.finish()

        assert timing.end_time is not None
        assert timing.duration is not None
        assert timing.duration > 0
        assert timing.end_time > timing.start_time
