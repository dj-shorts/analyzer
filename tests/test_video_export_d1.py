"""
Tests for Epic D1 and D2: Video export functionality.
Tests both original format (D1) and format conversion (D2).
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

    def test_export_format_vertical(self):
        """Test vertical format (9:16) export."""
        config = Config(
            input_path="test.mp4",
            export_video=True,
            export_dir=Path("clips"),
            export_format="vertical"
        )
        exporter = VideoExporter(config)
        
        # Verify format configuration
        assert config.export_format == "vertical"
        assert exporter.formats["vertical"]["width"] == 1080
        assert exporter.formats["vertical"]["height"] == 1920
        assert exporter.formats["vertical"]["crop"] is True

    def test_export_format_square(self):
        """Test square format (1:1) export."""
        config = Config(
            input_path="test.mp4",
            export_video=True,
            export_dir=Path("clips"),
            export_format="square"
        )
        exporter = VideoExporter(config)
        
        # Verify format configuration
        assert config.export_format == "square"
        assert exporter.formats["square"]["width"] == 1080
        assert exporter.formats["square"]["height"] == 1080
        assert exporter.formats["square"]["crop"] is True

    def test_build_crop_scale_filter_wider_input(self):
        """Test crop and scale filter for wider input (16:9 -> 9:16)."""
        config = Config(input_path="test.mp4")
        exporter = VideoExporter(config)
        
        # 1920x1080 input (16:9) -> 1080x1920 output (9:16)
        filter_str = exporter._build_crop_scale_filter(1920, 1080, 1080, 1920)
        
        # Should crop width and scale
        assert "crop=" in filter_str
        assert "scale=1080:1920" in filter_str
        
        # Verify crop dimensions (should crop to 607x1080)
        assert "crop=607:1080" in filter_str

    def test_build_crop_scale_filter_taller_input(self):
        """Test crop and scale filter for taller input (9:16 -> 16:9)."""
        config = Config(input_path="test.mp4")
        exporter = VideoExporter(config)
        
        # 1080x1920 input (9:16) -> 1920x1080 output (16:9)
        filter_str = exporter._build_crop_scale_filter(1080, 1920, 1920, 1080)
        
        # Should crop height and scale
        assert "crop=" in filter_str
        assert "scale=1920:1080" in filter_str
        
        # Verify crop dimensions (should crop to 1080x607)
        assert "crop=1080:607" in filter_str

    def test_transcode_with_format_vertical(self):
        """Test format transcoding for vertical format."""
        config = Config(
            input_path="test.mp4",
            export_format="vertical"
        )
        exporter = VideoExporter(config)
        
        input_path = Path("test.mp4")
        output_path = Path("output.mp4")
        start_time = 10.0
        end_time = 25.0
        
        # Mock video info with dimensions
        mock_video_info = {
            "streams": [
                {"codec_type": "video", "width": 1920, "height": 1080}
            ]
        }
        
        # Mock successful FFmpeg execution
        with patch.object(exporter, 'get_video_info', return_value=mock_video_info):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stderr="")
                
                # Mock file existence
                with patch.object(Path, 'exists', return_value=True):
                    with patch.object(Path, 'stat') as mock_stat:
                        mock_stat.return_value.st_size = 2048000
                        
                        result = exporter._transcode_with_format(input_path, output_path, start_time, end_time)
                        
                        assert result["success"] is True
                        assert result["method"] == "transcode_vertical"
                        assert result["file_size"] == 2048000

    def test_transcode_with_format_square(self):
        """Test format transcoding for square format."""
        config = Config(
            input_path="test.mp4",
            export_format="square"
        )
        exporter = VideoExporter(config)
        
        input_path = Path("test.mp4")
        output_path = Path("output.mp4")
        start_time = 10.0
        end_time = 25.0
        
        # Mock video info with dimensions
        mock_video_info = {
            "streams": [
                {"codec_type": "video", "width": 1920, "height": 1080}
            ]
        }
        
        # Mock successful FFmpeg execution
        with patch.object(exporter, 'get_video_info', return_value=mock_video_info):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stderr="")
                
                # Mock file existence
                with patch.object(Path, 'exists', return_value=True):
                    with patch.object(Path, 'stat') as mock_stat:
                        mock_stat.return_value.st_size = 1536000
                        
                        result = exporter._transcode_with_format(input_path, output_path, start_time, end_time)
                        
                        assert result["success"] is True
                        assert result["method"] == "transcode_square"
                        assert result["file_size"] == 1536000

    def test_transcode_with_format_failure(self):
        """Test format transcoding failure."""
        config = Config(
            input_path="test.mp4",
            export_format="vertical"
        )
        exporter = VideoExporter(config)
        
        input_path = Path("test.mp4")
        output_path = Path("output.mp4")
        start_time = 10.0
        end_time = 25.0
        
        # Mock video info failure
        with patch.object(exporter, 'get_video_info', return_value={"error": "Could not get video info"}):
            result = exporter._transcode_with_format(input_path, output_path, start_time, end_time)
            
            assert result["success"] is False
            assert "error" in result

    def test_export_clips_with_format(self):
        """Test export clips with format conversion."""
        config = Config(
            input_path="test.mp4",
            export_video=True,
            export_dir=Path("clips"),
            export_format="vertical"
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
                }
            ]
        }
        
        input_video_path = Path("test.mp4")
        output_dir = Path("clips")
        
        # Mock format transcoding
        with patch.object(exporter, '_transcode_with_format') as mock_transcode:
            mock_transcode.return_value = {"success": True, "method": "transcode_vertical", "file_size": 2048000}
            
            result = exporter.export_clips(segments_data, input_video_path, output_dir)
            
            assert result["total_clips"] == 1
            assert result["exported_clips"] == 1
            assert result["failed_clips"] == 0
            assert len(result["exported_clips_list"]) == 1
            assert len(result["export_errors"]) == 0

    def test_auto_reframe_enabled(self):
        """Test auto-reframe configuration."""
        config = Config(
            input_path="test.mp4",
            export_video=True,
            export_dir=Path("clips"),
            export_format="vertical",
            auto_reframe=True
        )
        exporter = VideoExporter(config)
        
        # Verify auto-reframe is enabled
        assert config.auto_reframe is True
        assert exporter.people_detector is not None

    def test_auto_reframe_disabled(self):
        """Test auto-reframe disabled."""
        config = Config(
            input_path="test.mp4",
            export_video=True,
            export_dir=Path("clips"),
            export_format="vertical",
            auto_reframe=False
        )
        exporter = VideoExporter(config)
        
        # Verify auto-reframe is disabled
        assert config.auto_reframe is False
        assert exporter.people_detector is None

    def test_build_auto_reframe_filter_success(self):
        """Test auto-reframe filter with people detection."""
        config = Config(
            input_path="test.mp4",
            export_format="vertical",
            auto_reframe=True
        )
        exporter = VideoExporter(config)
        
        input_path = Path("test.mp4")
        input_width = 1920
        input_height = 1080
        target_width = 1080
        target_height = 1920
        start_time = 10.0
        duration = 5.0
        
        # Mock people detection result
        mock_detection_result = {
            "success": True,
            "center_x": 960.0,  # Center of 1920px width
            "people_count": 2.0
        }
        
        with patch.object(exporter.people_detector, 'detect_people_in_video_segment', 
                         return_value=mock_detection_result):
            with patch.object(exporter.people_detector, 'calculate_crop_window',
                             return_value=(420, 0, 1080, 1920)):  # Mock crop window
                
                filter_str = exporter._build_auto_reframe_filter(
                    input_width, input_height, target_width, target_height,
                    input_path, start_time, duration
                )
                
                # Should contain auto-reframe crop
                assert "crop=1080:1920:420:0" in filter_str
                assert "scale=1080:1920" in filter_str

    def test_build_auto_reframe_filter_no_people(self):
        """Test auto-reframe filter fallback when no people detected."""
        config = Config(
            input_path="test.mp4",
            export_format="vertical",
            auto_reframe=True
        )
        exporter = VideoExporter(config)
        
        input_path = Path("test.mp4")
        input_width = 1920
        input_height = 1080
        target_width = 1080
        target_height = 1920
        start_time = 10.0
        duration = 5.0
        
        # Mock people detection result with no people
        mock_detection_result = {
            "success": True,
            "center_x": None,
            "people_count": 0
        }
        
        with patch.object(exporter.people_detector, 'detect_people_in_video_segment', 
                         return_value=mock_detection_result):
            with patch.object(exporter, '_build_crop_scale_filter',
                             return_value="crop=607:1080:656:0,scale=1080:1920"):
                
                filter_str = exporter._build_auto_reframe_filter(
                    input_width, input_height, target_width, target_height,
                    input_path, start_time, duration
                )
                
                # Should fallback to center crop
                assert filter_str == "crop=607:1080:656:0,scale=1080:1920"

    def test_build_auto_reframe_filter_error(self):
        """Test auto-reframe filter error handling."""
        config = Config(
            input_path="test.mp4",
            export_format="vertical",
            auto_reframe=True
        )
        exporter = VideoExporter(config)
        
        input_path = Path("test.mp4")
        input_width = 1920
        input_height = 1080
        target_width = 1080
        target_height = 1920
        start_time = 10.0
        duration = 5.0
        
        # Mock people detection failure
        with patch.object(exporter.people_detector, 'detect_people_in_video_segment', 
                         side_effect=Exception("Detection failed")):
            with patch.object(exporter, '_build_crop_scale_filter',
                             return_value="crop=607:1080:656:0,scale=1080:1920"):
                
                filter_str = exporter._build_auto_reframe_filter(
                    input_width, input_height, target_width, target_height,
                    input_path, start_time, duration
                )
                
                # Should fallback to center crop on error
                assert filter_str == "crop=607:1080:656:0,scale=1080:1920"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
