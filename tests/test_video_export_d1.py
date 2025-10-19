"""
Tests for Epic D1: Video export functionality.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

from analyzer.config import Config
from analyzer.video import VideoExporter


class TestVideoExporterEpicD1:
    """Test video export functionality for Epic D1."""

    def test_video_exporter_initialization(self):
        """Test VideoExporter initialization."""
        config = Config(
            input_path="test.mp4",
            export_video=True,
            export_dir=Path("clips")
        )
        exporter = VideoExporter(config)
        
        assert exporter.config == config
        assert isinstance(exporter.h264_params, list)
        assert isinstance(exporter.audio_params, list)
        assert "-c:v" in exporter.h264_params
        assert "libx264" in exporter.h264_params
        assert "-crf" in exporter.h264_params
        assert "18" in exporter.h264_params

    def test_export_clips_basic(self):
        """Test basic export clips functionality."""
        config = Config(
            input_path="test.mp4",
            export_video=True,
            export_dir=Path("clips")
        )
        exporter = VideoExporter(config)
        
        # Mock segments data
        segments_data = {
            "segments": [
                {
                    "clip_id": 1,
                    "start": 10.0,
                    "end": 25.0,
                    "center": 17.5,
                    "score": 0.8,
                    "seed_based": False,
                    "aligned": False,
                    "length": 15.0
                },
                {
                    "clip_id": 2,
                    "start": 30.0,
                    "end": 45.0,
                    "center": 37.5,
                    "score": 0.7,
                    "seed_based": False,
                    "aligned": False,
                    "length": 15.0
                }
            ]
        }
        
        input_video_path = Path("test.mp4")
        output_dir = Path("clips")
        
        # Mock the _export_single_clip method
        with patch.object(exporter, '_export_single_clip') as mock_export:
            mock_export.side_effect = [
                {"success": True, "method": "stream_copy", "file_size": 1024000},
                {"success": True, "method": "h264_transcode", "file_size": 2048000}
            ]
            
            result = exporter.export_clips(segments_data, input_video_path, output_dir)
            
            assert result["total_clips"] == 2
            assert result["exported_clips"] == 2
            assert result["failed_clips"] == 0
            assert len(result["exported_clips_list"]) == 2
            assert len(result["export_errors"]) == 0

    def test_export_single_clip_stream_copy_success(self):
        """Test successful stream copy export."""
        config = Config(input_path="test.mp4")
        exporter = VideoExporter(config)
        
        input_path = Path("test.mp4")
        output_path = Path("output.mp4")
        start_time = 10.0
        end_time = 25.0
        
        # Mock successful FFmpeg execution
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")
            
            # Mock file existence
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value.st_size = 1024000
                    
                    result = exporter._export_single_clip(input_path, output_path, start_time, end_time)
                    
                    assert result["success"] is True
                    assert result["method"] == "stream_copy"
                    assert result["file_size"] == 1024000

    def test_export_single_clip_stream_copy_failure(self):
        """Test stream copy failure with h264 fallback."""
        config = Config(input_path="test.mp4")
        exporter = VideoExporter(config)
        
        input_path = Path("test.mp4")
        output_path = Path("output.mp4")
        start_time = 10.0
        end_time = 25.0
        
        # Mock stream copy failure
        with patch.object(exporter, '_try_stream_copy') as mock_stream_copy:
            mock_stream_copy.return_value = {"success": False, "error": "Codec not supported"}
            
            # Mock successful h264 transcoding
            with patch.object(exporter, '_transcode_to_h264') as mock_h264:
                mock_h264.return_value = {"success": True, "method": "h264_transcode", "file_size": 2048000}
                
                result = exporter._export_single_clip(input_path, output_path, start_time, end_time)
                
                assert result["success"] is True
                assert result["method"] == "h264_transcode"
                assert result["file_size"] == 2048000

    def test_try_stream_copy_success(self):
        """Test successful stream copy."""
        config = Config(input_path="test.mp4")
        exporter = VideoExporter(config)
        
        input_path = Path("test.mp4")
        output_path = Path("output.mp4")
        start_time = 10.0
        end_time = 25.0
        
        # Mock successful FFmpeg execution
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")
            
            # Mock file existence
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value.st_size = 1024000
                    
                    result = exporter._try_stream_copy(input_path, output_path, start_time, end_time)
                    
                    assert result["success"] is True
                    assert result["method"] == "stream_copy"
                    assert result["file_size"] == 1024000

    def test_try_stream_copy_failure(self):
        """Test stream copy failure."""
        config = Config(input_path="test.mp4")
        exporter = VideoExporter(config)
        
        input_path = Path("test.mp4")
        output_path = Path("output.mp4")
        start_time = 10.0
        end_time = 25.0
        
        # Mock failed FFmpeg execution
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Codec not supported")
            
            result = exporter._try_stream_copy(input_path, output_path, start_time, end_time)
            
            assert result["success"] is False
            assert "error" in result

    def test_transcode_to_h264_success(self):
        """Test successful h264 transcoding."""
        config = Config(input_path="test.mp4")
        exporter = VideoExporter(config)
        
        input_path = Path("test.mp4")
        output_path = Path("output.mp4")
        start_time = 10.0
        end_time = 25.0
        
        # Mock successful FFmpeg execution
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")
            
            # Mock file existence
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value.st_size = 2048000
                    
                    result = exporter._transcode_to_h264(input_path, output_path, start_time, end_time)
                    
                    assert result["success"] is True
                    assert result["method"] == "h264_transcode"
                    assert result["file_size"] == 2048000

    def test_transcode_to_h264_failure(self):
        """Test h264 transcoding failure."""
        config = Config(input_path="test.mp4")
        exporter = VideoExporter(config)
        
        input_path = Path("test.mp4")
        output_path = Path("output.mp4")
        start_time = 10.0
        end_time = 25.0
        
        # Mock failed FFmpeg execution
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Transcoding failed")
            
            result = exporter._transcode_to_h264(input_path, output_path, start_time, end_time)
            
            assert result["success"] is False
            assert "error" in result

    def test_get_video_info_success(self):
        """Test successful video info retrieval."""
        config = Config(input_path="test.mp4")
        exporter = VideoExporter(config)
        
        video_path = Path("test.mp4")
        
        # Mock successful FFprobe execution
        with patch('subprocess.run') as mock_run:
            mock_probe_result = {
                "format": {"duration": "120.0"},
                "streams": [
                    {"codec_type": "video", "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"}
                ]
            }
            mock_run.return_value = Mock(returncode=0, stdout=str(mock_probe_result))
            
            with patch('json.loads', return_value=mock_probe_result):
                result = exporter.get_video_info(video_path)
                
                assert "format" in result
                assert "streams" in result

    def test_get_video_info_failure(self):
        """Test video info retrieval failure."""
        config = Config(input_path="test.mp4")
        exporter = VideoExporter(config)
        
        video_path = Path("test.mp4")
        
        # Mock failed FFprobe execution
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="File not found")
            
            result = exporter.get_video_info(video_path)
            
            assert "error" in result

    def test_is_codec_compatible_h264_aac(self):
        """Test codec compatibility check for h264/aac."""
        config = Config(input_path="test.mp4")
        exporter = VideoExporter(config)
        
        video_path = Path("test.mp4")
        
        # Mock video info with h264/aac
        mock_video_info = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264"},
                {"codec_type": "audio", "codec_name": "aac"}
            ]
        }
        
        with patch.object(exporter, 'get_video_info', return_value=mock_video_info):
            result = exporter.is_codec_compatible(video_path)
            
            assert result["compatible"] is True
            assert result["video_compatible"] is True
            assert result["audio_compatible"] is True

    def test_is_codec_compatible_incompatible(self):
        """Test codec compatibility check for incompatible codecs."""
        config = Config(input_path="test.mp4")
        exporter = VideoExporter(config)
        
        video_path = Path("test.mp4")
        
        # Mock video info with incompatible codecs
        mock_video_info = {
            "streams": [
                {"codec_type": "video", "codec_name": "vp9"},
                {"codec_type": "audio", "codec_name": "opus"}
            ]
        }
        
        with patch.object(exporter, 'get_video_info', return_value=mock_video_info):
            result = exporter.is_codec_compatible(video_path)
            
            assert result["compatible"] is False
            assert result["video_compatible"] is False
            assert result["audio_compatible"] is False

    def test_export_clips_with_errors(self):
        """Test export clips with some failures."""
        config = Config(
            input_path="test.mp4",
            export_video=True,
            export_dir=Path("clips")
        )
        exporter = VideoExporter(config)
        
        # Mock segments data
        segments_data = {
            "segments": [
                {
                    "clip_id": 1,
                    "start": 10.0,
                    "end": 25.0,
                    "center": 17.5,
                    "score": 0.8,
                    "seed_based": False,
                    "aligned": False,
                    "length": 15.0
                },
                {
                    "clip_id": 2,
                    "start": 30.0,
                    "end": 45.0,
                    "center": 37.5,
                    "score": 0.7,
                    "seed_based": False,
                    "aligned": False,
                    "length": 15.0
                }
            ]
        }
        
        input_video_path = Path("test.mp4")
        output_dir = Path("clips")
        
        # Mock mixed results (one success, one failure)
        with patch.object(exporter, '_export_single_clip') as mock_export:
            mock_export.side_effect = [
                {"success": True, "method": "stream_copy", "file_size": 1024000},
                {"success": False, "error": "Transcoding failed"}
            ]
            
            result = exporter.export_clips(segments_data, input_video_path, output_dir)
            
            assert result["total_clips"] == 2
            assert result["exported_clips"] == 1
            assert result["failed_clips"] == 1
            assert len(result["exported_clips_list"]) == 1
            assert len(result["export_errors"]) == 1
            assert result["export_errors"][0]["clip_id"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
