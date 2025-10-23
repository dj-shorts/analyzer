"""
Epic E1: JSON Schema Validation Tests

Tests for JSON schema validation functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from jsonschema import ValidationError

from analyzer.schema import (
    JSONSchemaValidator,
    validate_analysis_result,
    validate_output_files,
)


class TestJSONSchemaValidationEpicE1:
    """Tests for JSON schema validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = JSONSchemaValidator()

        # Valid analysis result
        self.valid_result = {
            "metadata": {
                "version": "1.0.0",
                "created_at": "2025-10-20T00:08:14.622336",
                "input_file": "test.mp4",
                "audio_duration": 29.74,
                "sample_rate": 22050,
                "configuration": {
                    "clips_count": 2,
                    "min_clip_length": 15.0,
                    "max_clip_length": 30.0,
                    "pre_roll": 10.0,
                    "peak_spacing": 80,
                    "with_motion": False,
                    "align_to_beat": False,
                    "seed_timestamps": [],
                },
            },
            "clips": [
                {
                    "clip_id": 1,
                    "start": 0.17,
                    "end": 23.27,
                    "center": 10.17,
                    "score": 0.54,
                    "seed_based": False,
                    "aligned": False,
                    "length": 23.1,
                },
                {
                    "clip_id": 2,
                    "start": 11.83,
                    "end": 34.70,
                    "center": 21.83,
                    "score": 0.52,
                    "seed_based": False,
                    "aligned": False,
                    "length": 22.87,
                },
            ],
            "summary": {
                "total_clips": 2,
                "seed_based_clips": 0,
                "auto_detected_clips": 2,
                "average_score": 0.53,
                "total_duration": 45.97,
                "coverage_percentage": 154.58,
            },
        }

    def test_valid_result_validation(self):
        """Test validation of valid analysis result."""
        assert self.validator.validate_result(self.valid_result)

    def test_invalid_result_validation(self):
        """Test validation of invalid analysis result."""
        # Missing required field
        invalid_result = self.valid_result.copy()
        del invalid_result["metadata"]

        with pytest.raises(ValidationError):
            self.validator.validate_result(invalid_result)

    def test_invalid_clip_data(self):
        """Test validation with invalid clip data."""
        invalid_result = self.valid_result.copy()
        invalid_result["clips"][0]["score"] = 1.5  # Invalid score > 1

        with pytest.raises(ValidationError):
            self.validator.validate_result(invalid_result)

    def test_invalid_metadata_version(self):
        """Test validation with invalid version format."""
        invalid_result = self.valid_result.copy()
        invalid_result["metadata"]["version"] = "invalid-version"

        with pytest.raises(ValidationError):
            self.validator.validate_result(invalid_result)

    def test_invalid_configuration(self):
        """Test validation with invalid configuration."""
        invalid_result = self.valid_result.copy()
        invalid_result["metadata"]["configuration"]["clips_count"] = 0  # Invalid count

        with pytest.raises(ValidationError):
            self.validator.validate_result(invalid_result)

    def test_file_validation(self):
        """Test validation of JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.valid_result, f)
            json_path = f.name

        try:
            assert self.validator.validate_file(Path(json_path))
        finally:
            Path(json_path).unlink()

    def test_invalid_file_validation(self):
        """Test validation of invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            json_path = f.name

        try:
            assert not self.validator.validate_file(Path(json_path))
        finally:
            Path(json_path).unlink()

    def test_csv_validation(self):
        """Test CSV structure validation."""
        csv_content = """clip_id,start,end,center,score,seed_based,aligned,length
1,0.17,23.27,10.17,0.54,False,False,23.1
2,11.83,34.70,21.83,0.52,False,False,22.87"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            assert self.validator._validate_csv_structure(Path(csv_path))
        finally:
            Path(csv_path).unlink()

    def test_csv_validation_missing_fields(self):
        """Test CSV validation with missing required fields."""
        csv_content = """clip_id,start,end,center,score
1,0.17,23.27,10.17,0.54"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            assert not self.validator._validate_csv_structure(Path(csv_path))
        finally:
            Path(csv_path).unlink()

    def test_csv_validation_invalid_data_types(self):
        """Test CSV validation with invalid data types."""
        csv_content = """clip_id,start,end,center,score,seed_based,aligned,length
invalid,0.17,23.27,10.17,0.54,False,False,23.1"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            assert not self.validator._validate_csv_structure(Path(csv_path))
        finally:
            Path(csv_path).unlink()

    def test_cli_output_validation(self):
        """Test validation of both JSON and CSV files."""
        # Create valid JSON file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as json_f:
            json.dump(self.valid_result, json_f)
            json_path = json_f.name

        # Create valid CSV file
        csv_content = """clip_id,start,end,center,score,seed_based,aligned,length
1,0.17,23.27,10.17,0.54,False,False,23.1
2,11.83,34.70,21.83,0.52,False,False,22.87"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as csv_f:
            csv_f.write(csv_content)
            csv_path = csv_f.name

        try:
            assert self.validator.validate_cli_output(Path(json_path), Path(csv_path))
        finally:
            Path(json_path).unlink()
            Path(csv_path).unlink()

    def test_validation_errors_detection(self):
        """Test detailed validation error detection."""
        invalid_result = self.valid_result.copy()
        invalid_result["clips"][0]["score"] = 1.5  # Invalid score

        errors = self.validator.get_validation_errors(invalid_result)
        assert len(errors) > 0
        assert any("score" in error.lower() for error in errors)

    def test_convenience_functions(self):
        """Test convenience validation functions."""
        # Test validate_analysis_result
        assert validate_analysis_result(self.valid_result)

        # Test validate_output_files
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as json_f:
            json.dump(self.valid_result, json_f)
            json_path = json_f.name

        csv_content = """clip_id,start,end,center,score,seed_based,aligned,length
1,0.17,23.27,10.17,0.54,False,False,23.1"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as csv_f:
            csv_f.write(csv_content)
            csv_path = csv_f.name

        try:
            assert validate_output_files(Path(json_path), Path(csv_path))
        finally:
            Path(json_path).unlink()
            Path(csv_path).unlink()

    def test_schema_file_not_found(self):
        """Test behavior when schema file is not found."""
        with pytest.raises(FileNotFoundError):
            JSONSchemaValidator(Path("nonexistent_schema.json"))

    @patch("src.analyzer.schema.jsonschema", None)
    def test_validation_without_jsonschema(self):
        """Test validation behavior when jsonschema is not available."""
        validator = JSONSchemaValidator()
        # Should not raise exception, just return True
        assert validator.validate_result(self.valid_result)

    def test_edge_cases(self):
        """Test edge cases in validation."""
        # Test with empty clips array
        empty_clips_result = self.valid_result.copy()
        empty_clips_result["clips"] = []
        empty_clips_result["summary"]["total_clips"] = 0

        assert self.validator.validate_result(empty_clips_result)

        # Test with maximum clips
        max_clips_result = self.valid_result.copy()
        max_clips_result["metadata"]["configuration"]["clips_count"] = 50
        max_clips_result["clips"] = [
            {
                "clip_id": i + 1,
                "start": float(i * 10),
                "end": float((i + 1) * 10),
                "center": float(i * 10 + 5),
                "score": 0.5,
                "seed_based": False,
                "aligned": False,
                "length": 10.0,
            }
            for i in range(50)
        ]
        max_clips_result["summary"]["total_clips"] = 50

        assert self.validator.validate_result(max_clips_result)

    def test_seed_timestamps_validation(self):
        """Test validation with seed timestamps."""
        seed_result = self.valid_result.copy()
        seed_result["metadata"]["configuration"]["seed_timestamps"] = [10.0, 20.0]
        seed_result["clips"][0]["seed_based"] = True
        seed_result["summary"]["seed_based_clips"] = 1

        assert self.validator.validate_result(seed_result)

    def test_beat_alignment_validation(self):
        """Test validation with beat alignment."""
        beat_result = self.valid_result.copy()
        beat_result["metadata"]["configuration"]["align_to_beat"] = True
        beat_result["clips"][0]["aligned"] = True

        assert self.validator.validate_result(beat_result)

    def test_motion_analysis_validation(self):
        """Test validation with motion analysis."""
        motion_result = self.valid_result.copy()
        motion_result["metadata"]["configuration"]["with_motion"] = True

        assert self.validator.validate_result(motion_result)
