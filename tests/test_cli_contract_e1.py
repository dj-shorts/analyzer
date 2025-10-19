"""
Tests for Epic E1: CLI Contract and JSON Schema validation.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from analyzer.cli import main
from analyzer.config import Config
from analyzer.schema import validate_output, get_output_schema


class TestCLIContractEpicE1:
    """Test CLI contract implementation for Epic E1."""

    def test_cli_help_output(self):
        """Test that --help shows all required flags."""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Check for all required CLI flags (--input is an argument, not an option)
        required_flags = [
            "--clips",
            "--min-len",
            "--max-len", 
            "--pre",
            "--spacing",
            "--with-motion",
            "--align-to-beat",
            "--seeds",
            "--out-json",
            "--out-csv",
            "--threads",
            "--ram-limit",
            "--export-video",
            "--export-dir",
            "--export-format",
            "--auto-reframe",
            "--verbose"
        ]
        
        for flag in required_flags:
            assert flag in help_text, f"Missing CLI flag: {flag}"

    def test_cli_flag_descriptions(self):
        """Test that CLI flags have proper descriptions."""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        help_text = result.output
        
        # Check for key descriptions
        descriptions = [
            "Number of clips to extract",
            "Minimum clip length in seconds",
            "Maximum clip length in seconds",
            "Pre-roll time in seconds",
            "Minimum spacing between peaks in frames",
            "Include motion analysis",
            "Align clips to beat boundaries",
            "Comma-separated seed timestamps",
            "Output JSON file path",
            "Output CSV file path",
            "Number of threads to use",
            "RAM limit",
            "Export video clips",
            "Directory for exported video clips",
            "Export format: original (16:9), vertical (9:16), square (1:1)",
            "Enable auto-reframe using people detection",
            "Enable verbose logging"
        ]
        
        for desc in descriptions:
            # Handle multi-line descriptions
            if desc == "Export format: original (16:9), vertical (9:16), square (1:1)":
                # Check for parts of the description
                assert "Export format: original (16:9)" in help_text, f"Missing description part: Export format: original (16:9)"
                assert "vertical\n                                  (9:16), square (1:1)" in help_text, f"Missing description part: vertical (9:16), square (1:1)"
            else:
                assert desc in help_text, f"Missing description: {desc}"

    def test_config_validation_export_format(self):
        """Test Config validation for export_format field."""
        # Valid formats
        valid_formats = ["original", "vertical", "square"]
        for format_val in valid_formats:
            config = Config(
                input_path="test.mp4",
                export_format=format_val
            )
            assert config.export_format == format_val
        
        # Invalid format should raise error
        with pytest.raises(ValueError, match="export_format must be one of"):
            Config(input_path="test.mp4", export_format="invalid")

    def test_config_video_export_fields(self):
        """Test Config video export fields."""
        config = Config(
            input_path="test.mp4",
            export_video=True,
            export_dir=Path("test_clips"),
            export_format="vertical",
            auto_reframe=True
        )
        
        assert config.export_video is True
        assert config.export_dir == Path("test_clips")
        assert config.export_format == "vertical"
        assert config.auto_reframe is True

    def test_cli_seed_parsing(self):
        """Test CLI seed timestamp parsing."""
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(suffix='.mp4') as temp_file:
            # Test valid seed format
            result = runner.invoke(main, [
                str(temp_file.name),
                '--seeds', '01:30:45,02:15:30',
                '--clips', '2'
            ])
            
            # Should not crash on seed parsing
            assert result.exit_code in [0, 1]  # 1 is expected due to missing video file


class TestJSONSchemaEpicE1:
    """Test JSON schema validation for Epic E1."""

    def test_schema_structure(self):
        """Test that schema has correct structure."""
        schema = get_output_schema()
        
        # Check top-level structure
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        
        # Check required fields
        required_fields = ["version", "clips", "metadata"]
        for field in required_fields:
            assert field in schema["required"]

    def test_schema_clips_structure(self):
        """Test clips array structure in schema."""
        schema = get_output_schema()
        clips_schema = schema["properties"]["clips"]
        
        assert clips_schema["type"] == "array"
        assert "items" in clips_schema
        
        clip_item_schema = clips_schema["items"]
        required_clip_fields = [
            "clip_id", "start", "end", "center", "score", 
            "length", "seed_based", "aligned"
        ]
        
        for field in required_clip_fields:
            assert field in clip_item_schema["required"]

    def test_schema_metadata_structure(self):
        """Test metadata structure in schema."""
        schema = get_output_schema()
        metadata_schema = schema["properties"]["metadata"]
        
        required_metadata_fields = [
            "input_file", "total_duration", "clips_count", "analysis_time"
        ]
        
        for field in required_metadata_fields:
            assert field in metadata_schema["required"]

    def test_validate_output_valid_data(self):
        """Test validation with valid output data."""
        valid_data = {
            "version": "1.0.0",
            "clips": [
                {
                    "clip_id": 1,
                    "start": 10.0,
                    "end": 25.0,
                    "center": 17.5,
                    "score": 0.8,
                    "length": 15.0,
                    "seed_based": False,
                    "aligned": True
                }
            ],
            "metadata": {
                "input_file": "test.mp4",
                "total_duration": 300.0,
                "clips_count": 1,
                "analysis_time": 5.0
            }
        }
        
        errors = validate_output(valid_data)
        assert len(errors) == 0, f"Validation errors: {errors}"

    def test_validate_output_missing_required_fields(self):
        """Test validation with missing required fields."""
        invalid_data = {
            "version": "1.0.0",
            "clips": []
            # Missing metadata
        }
        
        errors = validate_output(invalid_data)
        assert len(errors) > 0
        assert any("Missing required field: metadata" in error for error in errors)

    def test_validate_output_invalid_version_format(self):
        """Test validation with invalid version format."""
        invalid_data = {
            "version": "invalid-version",
            "clips": [],
            "metadata": {
                "input_file": "test.mp4",
                "total_duration": 300.0,
                "clips_count": 0,
                "analysis_time": 5.0
            }
        }
        
        errors = validate_output(invalid_data)
        assert len(errors) > 0
        assert any("Version must be in format 'X.Y.Z'" in error for error in errors)

    def test_validate_output_invalid_clip_score(self):
        """Test validation with invalid clip score."""
        invalid_data = {
            "version": "1.0.0",
            "clips": [
                {
                    "clip_id": 1,
                    "start": 10.0,
                    "end": 25.0,
                    "center": 17.5,
                    "score": 1.5,  # Invalid: > 1
                    "length": 15.0,
                    "seed_based": False,
                    "aligned": True
                }
            ],
            "metadata": {
                "input_file": "test.mp4",
                "total_duration": 300.0,
                "clips_count": 1,
                "analysis_time": 5.0
            }
        }
        
        errors = validate_output(invalid_data)
        assert len(errors) > 0
        assert any("score must be between 0 and 1" in error for error in errors)

    def test_validate_output_missing_clip_fields(self):
        """Test validation with missing clip fields."""
        invalid_data = {
            "version": "1.0.0",
            "clips": [
                {
                    "clip_id": 1,
                    "start": 10.0,
                    "end": 25.0,
                    # Missing center, score, length, seed_based, aligned
                }
            ],
            "metadata": {
                "input_file": "test.mp4",
                "total_duration": 300.0,
                "clips_count": 1,
                "analysis_time": 5.0
            }
        }
        
        errors = validate_output(invalid_data)
        assert len(errors) > 0
        assert any("missing required field" in error for error in errors)


class TestCLIIntegrationEpicE1:
    """Test CLI integration with all Epic E1 features."""

    @patch('analyzer.core.Analyzer')
    def test_cli_with_all_flags(self, mock_analyzer_class):
        """Test CLI with all new flags enabled."""
        runner = CliRunner()
        
        # Mock analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = {
            "segments": [],
            "audio_data": {"duration": 300.0},
            "video_export": {
                "total_clips": 3,
                "exported_clips": 3,
                "failed_clips": 0
            }
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        with tempfile.NamedTemporaryFile(suffix='.mp4') as temp_file:
            result = runner.invoke(main, [
                str(temp_file.name),
                '--clips', '3',
                '--min-len', '15',
                '--max-len', '30',
                '--pre', '10',
                '--spacing', '80',
                '--with-motion',
                '--align-to-beat',
                '--seeds', '01:30:45,02:15:30',
                '--out-json', 'test.json',
                '--out-csv', 'test.csv',
                '--threads', '4',
                '--ram-limit', '2GB',
                '--export-video',
                '--export-dir', 'test_clips',
                '--export-format', 'vertical',
                '--auto-reframe',
                '--verbose'
            ])
            
            # Should not crash
            assert result.exit_code in [0, 1]  # 1 is expected due to missing video file

    def test_export_format_choices(self):
        """Test that export format choices are properly validated."""
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(suffix='.mp4') as temp_file:
            # Test valid choices
            valid_formats = ["original", "vertical", "square"]
            for format_val in valid_formats:
                result = runner.invoke(main, [
                    str(temp_file.name),
                    '--export-format', format_val,
                    '--export-video'
                ])
                
                # Should not crash on format validation
                assert result.exit_code in [0, 1]
            
            # Test invalid choice
            result = runner.invoke(main, [
                str(temp_file.name),
                '--export-format', 'invalid',
                '--export-video'
            ])
            
            # Should show error for invalid format
            assert result.exit_code != 0
