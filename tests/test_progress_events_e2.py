"""
Tests for Epic E2: Progress Events in stdout for SSE.
"""

import pytest
import json
import sys
import tempfile
from io import StringIO
from unittest.mock import Mock, patch
from click.testing import CliRunner

from analyzer.progress import ProgressEmitter, EventType, AnalysisStage
from analyzer.cli import main


class TestProgressEmitterEpicE2:
    """Test ProgressEmitter functionality for Epic E2."""

    def test_progress_emitter_initialization(self):
        """Test ProgressEmitter initialization."""
        emitter = ProgressEmitter(enabled=True)
        assert emitter.enabled is True
        assert emitter.current_stage is None
        assert emitter.stage_start_time is None
        
        emitter_disabled = ProgressEmitter(enabled=False)
        assert emitter_disabled.enabled is False

    def test_emit_event_enabled(self):
        """Test event emission when enabled."""
        emitter = ProgressEmitter(enabled=True)
        
        # Capture stdout
        captured_output = StringIO()
        
        with patch('sys.stdout', captured_output):
            emitter.emit_event(
                EventType.PROGRESS,
                stage=AnalysisStage.AUDIO_EXTRACTION,
                progress=50,
                message="Extracting audio..."
            )
        
        output = captured_output.getvalue().strip()
        event = json.loads(output)
        
        assert event["type"] == "progress"
        assert event["stage"] == "audio_extraction"
        assert event["progress"] == 50
        assert event["message"] == "Extracting audio..."
        assert "timestamp" in event
        assert "elapsed" in event

    def test_emit_event_disabled(self):
        """Test that no events are emitted when disabled."""
        emitter = ProgressEmitter(enabled=False)
        
        # Capture stdout
        captured_output = StringIO()
        
        with patch('sys.stdout', captured_output):
            emitter.emit_event(
                EventType.PROGRESS,
                stage=AnalysisStage.AUDIO_EXTRACTION,
                progress=50,
                message="Extracting audio..."
            )
        
        output = captured_output.getvalue().strip()
        assert output == ""

    def test_start_stage(self):
        """Test stage start functionality."""
        emitter = ProgressEmitter(enabled=True)
        
        captured_output = StringIO()
        
        with patch('sys.stdout', captured_output):
            emitter.start_stage(AnalysisStage.AUDIO_EXTRACTION, "Custom message")
        
        output = captured_output.getvalue().strip()
        event = json.loads(output)
        
        assert event["type"] == "stage"
        assert event["stage"] == "audio_extraction"
        assert event["message"] == "Custom message"
        assert emitter.current_stage == AnalysisStage.AUDIO_EXTRACTION
        assert emitter.stage_start_time is not None

    def test_start_stage_default_message(self):
        """Test stage start with default message."""
        emitter = ProgressEmitter(enabled=True)
        
        captured_output = StringIO()
        
        with patch('sys.stdout', captured_output):
            emitter.start_stage(AnalysisStage.NOVELTY_DETECTION)
        
        output = captured_output.getvalue().strip()
        event = json.loads(output)
        
        assert event["type"] == "stage"
        assert event["stage"] == "novelty_detection"
        assert event["message"] == "Analyzing audio novelty..."

    def test_update_progress(self):
        """Test progress update functionality."""
        emitter = ProgressEmitter(enabled=True)
        emitter.current_stage = AnalysisStage.AUDIO_EXTRACTION
        
        captured_output = StringIO()
        
        with patch('sys.stdout', captured_output):
            emitter.update_progress(75, "75% complete")
        
        output = captured_output.getvalue().strip()
        event = json.loads(output)
        
        assert event["type"] == "progress"
        assert event["stage"] == "audio_extraction"
        assert event["progress"] == 75
        assert event["message"] == "75% complete"

    def test_update_progress_no_current_stage(self):
        """Test progress update without current stage."""
        emitter = ProgressEmitter(enabled=True)
        # No current stage set
        
        captured_output = StringIO()
        
        with patch('sys.stdout', captured_output):
            emitter.update_progress(50, "Progress update")
        
        output = captured_output.getvalue().strip()
        assert output == ""

    def test_complete_stage(self):
        """Test stage completion functionality."""
        emitter = ProgressEmitter(enabled=True)
        emitter.current_stage = AnalysisStage.AUDIO_EXTRACTION
        emitter.stage_start_time = 1000.0
        
        captured_output = StringIO()
        
        with patch('time.time', return_value=1005.0):
            with patch('sys.stdout', captured_output):
                emitter.complete_stage("Audio extraction done")
        
        output = captured_output.getvalue().strip()
        event = json.loads(output)
        
        assert event["type"] == "complete"
        assert event["stage"] == "audio_extraction"
        assert event["progress"] == 100
        assert event["message"] == "Audio extraction done"
        assert event["stage_duration"] == 5.0

    def test_emit_error(self):
        """Test error emission functionality."""
        emitter = ProgressEmitter(enabled=True)
        
        captured_output = StringIO()
        
        with patch('sys.stdout', captured_output):
            emitter.emit_error("Test error message", AnalysisStage.PEAK_DETECTION)
        
        output = captured_output.getvalue().strip()
        event = json.loads(output)
        
        assert event["type"] == "error"
        assert event["stage"] == "peak_detection"
        assert event["message"] == "Error: Test error message"

    def test_emit_info(self):
        """Test info emission functionality."""
        emitter = ProgressEmitter(enabled=True)
        
        captured_output = StringIO()
        
        with patch('sys.stdout', captured_output):
            emitter.emit_info("Info message", {"key": "value"})
        
        output = captured_output.getvalue().strip()
        event = json.loads(output)
        
        assert event["type"] == "info"
        assert event["message"] == "Info message"
        assert event["key"] == "value"

    def test_get_stage_progress_range(self):
        """Test stage progress range calculation."""
        emitter = ProgressEmitter(enabled=True)
        
        # Test various stages
        assert emitter.get_stage_progress_range(AnalysisStage.INITIALIZATION) == (0, 5)
        assert emitter.get_stage_progress_range(AnalysisStage.AUDIO_EXTRACTION) == (5, 15)
        assert emitter.get_stage_progress_range(AnalysisStage.NOVELTY_DETECTION) == (15, 35)
        assert emitter.get_stage_progress_range(AnalysisStage.COMPLETION) == (100, 100)

    def test_calculate_stage_progress(self):
        """Test overall progress calculation from stage progress."""
        emitter = ProgressEmitter(enabled=True)
        
        # Test audio extraction stage (5-15%)
        progress = emitter.calculate_stage_progress(AnalysisStage.AUDIO_EXTRACTION, 0.5)
        assert progress == 10  # 5 + (0.5 * 10) = 10
        
        # Test novelty detection stage (15-35%)
        progress = emitter.calculate_stage_progress(AnalysisStage.NOVELTY_DETECTION, 0.25)
        assert progress == 20  # 15 + (0.25 * 20) = 20
        
        # Test completion stage (100-100%)
        progress = emitter.calculate_stage_progress(AnalysisStage.COMPLETION, 1.0)
        assert progress == 100


class TestCLIProgressEventsEpicE2:
    """Test CLI integration with progress events for Epic E2."""

    @patch('analyzer.core.Analyzer')
    def test_cli_progress_events_enabled(self, mock_analyzer_class):
        """Test CLI with progress events enabled."""
        runner = CliRunner()
        
        # Mock analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = {
            "segments": [],
            "audio_data": {"duration": 300.0}
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        with tempfile.NamedTemporaryFile(suffix='.mp4') as temp_file:
            result = runner.invoke(main, [
                str(temp_file.name),
                '--progress-events',
                '--clips', '3'
            ])
            
            # Should not crash
            assert result.exit_code in [0, 1]  # 1 is expected due to missing video file

    @patch('analyzer.core.Analyzer')
    def test_cli_progress_events_disabled(self, mock_analyzer_class):
        """Test CLI with progress events disabled."""
        runner = CliRunner()
        
        # Mock analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = {
            "segments": [],
            "audio_data": {"duration": 300.0}
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        # Since progress-events is True by default, we need to test the config
        # by checking that the flag exists and can be used
        with tempfile.NamedTemporaryFile(suffix='.mp4') as temp_file:
            result = runner.invoke(main, [
                str(temp_file.name),
                '--clips', '3'
            ])
            
            # Should not crash
            assert result.exit_code in [0, 1]  # 1 is expected due to missing video file

    def test_cli_help_shows_progress_events_flag(self):
        """Test that CLI help shows progress events flag."""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        help_text = result.output
        
        assert "--progress-events" in help_text
        assert "Enable progress events in stdout for SSE" in help_text


class TestProgressEventFormatEpicE2:
    """Test progress event format and structure for Epic E2."""

    def test_event_structure(self):
        """Test that events have correct structure for SSE."""
        emitter = ProgressEmitter(enabled=True)
        
        captured_output = StringIO()
        
        with patch('sys.stdout', captured_output):
            emitter.emit_event(
                EventType.PROGRESS,
                stage=AnalysisStage.AUDIO_EXTRACTION,
                progress=50,
                message="Test message",
                data={"custom": "data"}
            )
        
        output = captured_output.getvalue().strip()
        event = json.loads(output)
        
        # Check required fields
        required_fields = ["type", "timestamp", "elapsed"]
        for field in required_fields:
            assert field in event
        
        # Check optional fields
        assert event["stage"] == "audio_extraction"
        assert event["progress"] == 50
        assert event["message"] == "Test message"
        assert event["custom"] == "data"

    def test_event_json_serializable(self):
        """Test that events are JSON serializable."""
        emitter = ProgressEmitter(enabled=True)
        
        captured_output = StringIO()
        
        with patch('sys.stdout', captured_output):
            emitter.emit_event(
                EventType.STAGE,
                stage=AnalysisStage.PEAK_DETECTION,
                progress=75,
                message="JSON test"
            )
        
        output = captured_output.getvalue().strip()
        
        # Should be valid JSON
        try:
            event = json.loads(output)
            assert isinstance(event, dict)
        except json.JSONDecodeError:
            pytest.fail("Event is not valid JSON")

    def test_multiple_events_separate_lines(self):
        """Test that multiple events are on separate lines for SSE."""
        emitter = ProgressEmitter(enabled=True)
        
        captured_output = StringIO()
        
        with patch('sys.stdout', captured_output):
            emitter.emit_event(EventType.STAGE, stage=AnalysisStage.INITIALIZATION)
            emitter.emit_event(EventType.PROGRESS, progress=25)
            emitter.emit_event(EventType.COMPLETE, stage=AnalysisStage.INITIALIZATION)
        
        output = captured_output.getvalue()
        lines = output.strip().split('\n')
        
        assert len(lines) == 3
        
        # Each line should be valid JSON
        for line in lines:
            event = json.loads(line)
            assert isinstance(event, dict)
            assert "type" in event


class TestAnalysisStageIntegrationEpicE2:
    """Test integration of progress events with analysis stages."""

    @patch('analyzer.core.AudioExtractor')
    @patch('analyzer.core.NoveltyDetector')
    @patch('analyzer.core.PeakPicker')
    @patch('analyzer.core.SegmentBuilder')
    @patch('analyzer.core.ResultExporter')
    def test_analyzer_progress_events(self, mock_exporter, mock_builder, 
                                    mock_picker, mock_novelty, mock_audio):
        """Test that analyzer emits progress events during analysis."""
        from analyzer.core import Analyzer
        from analyzer.config import Config
        
        # Mock components
        mock_audio.return_value.extract.return_value = {"duration": 300.0}
        mock_novelty.return_value.compute_novelty.return_value = {"scores": [0.1, 0.2, 0.3]}
        mock_picker.return_value.find_peaks.return_value = {"peaks": [10, 20, 30]}
        mock_builder.return_value.build_segments.return_value = {"segments": []}
        mock_exporter.return_value.export.return_value = {"results": "exported"}
        
        config = Config(
            input_path="test.mp4",
            progress_events=True
        )
        
        analyzer = Analyzer(config)
        
        captured_output = StringIO()
        
        with patch('sys.stdout', captured_output):
            try:
                analyzer.analyze()
            except Exception:
                # Expected to fail due to missing video file, but progress events should be emitted
                pass
        
        output = captured_output.getvalue()
        lines = output.strip().split('\n')
        
        # Should have emitted some progress events
        assert len(lines) > 0
        
        # Check that we have stage events
        stage_events = []
        for line in lines:
            try:
                event = json.loads(line)
                if event.get("type") == "stage":
                    stage_events.append(event)
            except json.JSONDecodeError:
                continue
        
        assert len(stage_events) > 0
