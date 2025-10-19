"""
Tests for Issue A7 - Results output CSV + JSON (contract).
"""

import json
import csv
import tempfile
from pathlib import Path

from analyzer.config import Config
from analyzer.export import ResultExporter


class TestResultsOutputA7:
    """Tests for results output in CSV and JSON formats (Issue A7)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(input_path=Path("test.mp4"))
        self.exporter = ResultExporter(self.config)

    def test_csv_output_format(self):
        """Test CSV output contains required fields: clip_id,start,end,center,score,seed_based,aligned."""
        # Create test segments
        segments = [
            {
                "clip_id": 1,
                "start": 10.0,
                "end": 25.0,
                "center": 15.0,
                "score": 0.8,
                "seed_based": False,
                "aligned": False,
                "length": 15.0
            },
            {
                "clip_id": 2,
                "start": 30.0,
                "end": 50.0,
                "center": 40.0,
                "score": 0.9,
                "seed_based": True,
                "aligned": False,
                "length": 20.0
            }
        ]
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            temp_csv_path = Path(tmp_file.name)
        
        # Override config output path
        self.config.output_csv = temp_csv_path
        
        try:
            # Export to CSV
            result_path = self.exporter._export_csv(segments)
            
            # Read and verify CSV content
            with open(result_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                # Check that we have the expected number of rows
                assert len(rows) == 2
                
                # Check required fields are present
                required_fields = ['clip_id', 'start', 'end', 'center', 'score', 'seed_based', 'aligned']
                for field in required_fields:
                    assert field in rows[0], f"Missing required field: {field}"
                
                # Check data types and values
                assert rows[0]['clip_id'] == '1'
                assert rows[0]['start'] == '10.000'
                assert rows[0]['end'] == '25.000'
                assert rows[0]['center'] == '15.000'
                assert rows[0]['score'] == '0.800'
                assert rows[0]['seed_based'] == 'False'
                assert rows[0]['aligned'] == 'False'
                
                assert rows[1]['clip_id'] == '2'
                assert rows[1]['seed_based'] == 'True'
        
        finally:
            # Clean up temporary file
            if temp_csv_path.exists():
                temp_csv_path.unlink()

    def test_json_output_format(self):
        """Test JSON output contains clips[], tempo_confidence, and schema version."""
        # Create test segments
        segments = [
            {
                "clip_id": 1,
                "start": 10.0,
                "end": 25.0,
                "center": 15.0,
                "score": 0.8,
                "seed_based": False,
                "aligned": False,
                "length": 15.0
            }
        ]
        
        # Create test audio data
        audio_data = {
            "duration": 120.0,
            "sample_rate": 22050
        }
        
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            temp_json_path = Path(tmp_file.name)
        
        # Override config output path
        self.config.output_json = temp_json_path
        
        try:
            # Export to JSON
            result_path = self.exporter._export_json(segments, audio_data)
            
            # Read and verify JSON content
            with open(result_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                # Check required top-level fields
                assert "clips" in data
                assert "tempo_confidence" in data
                assert "metadata" in data
                assert "summary" in data
                
                # Check clips array
                assert isinstance(data["clips"], list)
                assert len(data["clips"]) == 1
                
                # Check tempo_confidence
                assert isinstance(data["tempo_confidence"], (int, float))
                
                # Check metadata contains version
                assert "version" in data["metadata"]
                assert data["metadata"]["version"] == "1.0.0"
                
                # Check clip structure
                clip = data["clips"][0]
                required_clip_fields = ['clip_id', 'start', 'end', 'center', 'score', 'seed_based', 'aligned', 'length']
                for field in required_clip_fields:
                    assert field in clip, f"Missing required clip field: {field}"
        
        finally:
            # Clean up temporary file
            if temp_json_path.exists():
                temp_json_path.unlink()

    def test_json_schema_version(self):
        """Test JSON contains proper schema version."""
        segments = []
        audio_data = {"duration": 0, "sample_rate": 0}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            temp_json_path = Path(tmp_file.name)
        
        self.config.output_json = temp_json_path
        
        try:
            result_path = self.exporter._export_json(segments, audio_data)
            
            with open(result_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                # Check schema version
                assert data["metadata"]["version"] == "1.0.0"
        
        finally:
            if temp_json_path.exists():
                temp_json_path.unlink()

    def test_tempo_confidence_field(self):
        """Test that tempo_confidence field is present in JSON output."""
        segments = []
        audio_data = {"duration": 0, "sample_rate": 0}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            temp_json_path = Path(tmp_file.name)
        
        self.config.output_json = temp_json_path
        
        try:
            result_path = self.exporter._export_json(segments, audio_data)
            
            with open(result_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                # Check tempo_confidence field
                assert "tempo_confidence" in data
                assert isinstance(data["tempo_confidence"], (int, float))
                assert data["tempo_confidence"] == 0.0  # Current placeholder value
        
        finally:
            if temp_json_path.exists():
                temp_json_path.unlink()

    def test_csv_precision_formatting(self):
        """Test that CSV values are properly formatted with 3 decimal places."""
        segments = [
            {
                "clip_id": 1,
                "start": 10.123456789,
                "end": 25.987654321,
                "center": 15.555555555,
                "score": 0.888888888,
                "seed_based": False,
                "aligned": False,
                "length": 15.864197532
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            temp_csv_path = Path(tmp_file.name)
        
        self.config.output_csv = temp_csv_path
        
        try:
            result_path = self.exporter._export_csv(segments)
            
            with open(result_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                row = next(reader)
                
                # Check precision formatting
                assert row['start'] == '10.123'
                assert row['end'] == '25.988'
                assert row['center'] == '15.556'
                assert row['score'] == '0.889'
                assert row['length'] == '15.864'
        
        finally:
            if temp_csv_path.exists():
                temp_csv_path.unlink()

    def test_json_numpy_type_conversion(self):
        """Test that numpy types are properly converted to native Python types in JSON."""
        import numpy as np
        
        segments = [
            {
                "clip_id": np.int32(1),
                "start": np.float64(10.5),
                "end": np.float32(25.5),
                "center": np.float64(15.5),
                "score": np.float32(0.8),
                "seed_based": False,
                "aligned": False,
                "length": np.float64(15.0)
            }
        ]
        
        audio_data = {
            "duration": np.float64(120.0),
            "sample_rate": np.int32(22050)
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            temp_json_path = Path(tmp_file.name)
        
        self.config.output_json = temp_json_path
        
        try:
            result_path = self.exporter._export_json(segments, audio_data)
            
            with open(result_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                # Check that all values are native Python types
                clip = data["clips"][0]
                assert isinstance(clip["clip_id"], int)
                assert isinstance(clip["start"], (int, float))
                assert isinstance(clip["end"], (int, float))
                assert isinstance(clip["center"], (int, float))
                assert isinstance(clip["score"], (int, float))
                assert isinstance(clip["length"], (int, float))
                
                # Check metadata
                assert isinstance(data["metadata"]["audio_duration"], (int, float))
                assert isinstance(data["metadata"]["sample_rate"], (int, float))
        
        finally:
            if temp_json_path.exists():
                temp_json_path.unlink()

    def test_empty_segments_handling(self):
        """Test handling of empty segments list."""
        segments = []
        audio_data = {"duration": 0, "sample_rate": 0}
        
        # Test CSV export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            temp_csv_path = Path(tmp_file.name)
        
        self.config.output_csv = temp_csv_path
        
        try:
            result_path = self.exporter._export_csv(segments)
            
            with open(result_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                assert len(rows) == 0  # No data rows, only header
        
        finally:
            if temp_csv_path.exists():
                temp_csv_path.unlink()
        
        # Test JSON export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            temp_json_path = Path(tmp_file.name)
        
        self.config.output_json = temp_json_path
        
        try:
            result_path = self.exporter._export_json(segments, audio_data)
            
            with open(result_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                assert data["clips"] == []
                assert data["summary"]["total_clips"] == 0
                assert data["summary"]["average_score"] == 0
        
        finally:
            if temp_json_path.exists():
                temp_json_path.unlink()

    def test_full_export_integration(self):
        """Test full export integration with both CSV and JSON."""
        segments = [
            {
                "clip_id": 1,
                "start": 10.0,
                "end": 25.0,
                "center": 15.0,
                "score": 0.8,
                "seed_based": False,
                "aligned": False,
                "length": 15.0
            }
        ]
        
        audio_data = {
            "duration": 120.0,
            "sample_rate": 22050
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_csv:
            temp_csv_path = Path(tmp_csv.name)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_json:
            temp_json_path = Path(tmp_json.name)
        
        self.config.output_csv = temp_csv_path
        self.config.output_json = temp_json_path
        
        try:
            # Test full export
            segments_data = {"segments": segments}
            result = self.exporter.export(segments_data, audio_data)
            
            # Check return value
            assert "csv_path" in result
            assert "json_path" in result
            assert "segments_count" in result
            assert "export_timestamp" in result
            
            assert result["segments_count"] == 1
            assert result["csv_path"] == temp_csv_path
            assert result["json_path"] == temp_json_path
            
            # Verify both files exist and contain data
            assert temp_csv_path.exists()
            assert temp_json_path.exists()
            
            # Check CSV content
            with open(temp_csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                csv_rows = list(reader)
                assert len(csv_rows) == 1
            
            # Check JSON content
            with open(temp_json_path, 'r', encoding='utf-8') as jsonfile:
                json_data = json.load(jsonfile)
                assert len(json_data["clips"]) == 1
        
        finally:
            if temp_csv_path.exists():
                temp_csv_path.unlink()
            if temp_json_path.exists():
                temp_json_path.unlink()
