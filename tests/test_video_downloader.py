"""
Tests for video downloader module.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os

from analyzer.video_downloader import VideoDownloader, download_video_from_url, is_video_url


class TestVideoDownloader:
    """Test VideoDownloader class."""
    
    def test_init_default_download_dir(self):
        """Test initialization with default download directory."""
        downloader = VideoDownloader()
        assert downloader.download_dir.name == "analyzer_downloads"
        assert downloader.download_dir.exists()
    
    def test_init_custom_download_dir(self):
        """Test initialization with custom download directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            download_dir = Path(temp_dir) / "custom_downloads"
            downloader = VideoDownloader(download_dir)
            assert downloader.download_dir == download_dir
            assert downloader.download_dir.exists()
    
    def test_is_supported_url_youtube(self):
        """Test YouTube URL detection."""
        downloader = VideoDownloader()
        
        # Valid YouTube URLs
        assert downloader.is_supported_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert downloader.is_supported_url("https://youtu.be/dQw4w9WgXcQ")
        assert downloader.is_supported_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ")
        
        # Invalid URLs
        assert not downloader.is_supported_url("not-a-url")
        assert not downloader.is_supported_url("ftp://example.com")
    
    def test_is_supported_url_direct_video(self):
        """Test direct video file URL detection."""
        downloader = VideoDownloader()
        
        # Valid direct video URLs
        assert downloader.is_supported_url("https://example.com/video.mp4")
        assert downloader.is_supported_url("https://example.com/video.mov")
        assert downloader.is_supported_url("https://example.com/video.avi")
        assert downloader.is_supported_url("https://example.com/video.mkv")
        assert downloader.is_supported_url("https://example.com/video.webm")
        assert downloader.is_supported_url("https://example.com/video.m4v")
    
    def test_is_supported_url_other_platforms(self):
        """Test other platform URL detection."""
        downloader = VideoDownloader()
        
        # Valid platform URLs
        assert downloader.is_supported_url("https://vimeo.com/123456789")
        assert downloader.is_supported_url("https://drive.google.com/file/d/123/view")
        assert downloader.is_supported_url("https://onedrive.live.com/123")
        assert downloader.is_supported_url("https://dropbox.com/s/123/file.mp4")
    
    @patch('analyzer.video_downloader.subprocess.run')
    def test_download_video_success(self, mock_subprocess):
        """Test successful video download."""
        # Mock subprocess.run for successful download
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "[download] Test Video.mp4 has already been downloaded"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # Mock file creation in a fresh directory (no existing files)
        with tempfile.TemporaryDirectory() as temp_dir:
            download_dir = Path(temp_dir) / "downloads"
            download_dir.mkdir()
            downloader = VideoDownloader(download_dir)
            
            # Mock the downloaded file (will be created during download)
            mock_file = download_dir / "Test_Video.mp4"
            mock_file.write_text("fake video content")
            
            # Need to create file AFTER check for existing files but BEFORE find
            with patch.object(downloader, '_find_downloaded_file_from_template', return_value=mock_file):
                # Clear the directory before test to avoid "existing file" logic
                import time
                # Set old modification time to avoid "recent file" detection
                os.utime(mock_file, (time.time() - 86500, time.time() - 86500))
                
                result = downloader.download_video("https://youtube.com/watch?v=123")
            
            assert result["success"] is True
            assert result["file_path"] == mock_file
            assert result["title"] == "Test_Video"
            assert result["filesize"] > 0
            assert result["format"] == 'best[height<=1080]'
    
    @patch('analyzer.video_downloader.subprocess.run')
    def test_download_video_failure(self, mock_subprocess):
        """Test video download failure."""
        # Mock subprocess.run to return failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "ERROR: Video unavailable"
        mock_subprocess.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(Path(temp_dir))
            result = downloader.download_video("https://youtube.com/watch?v=123")
            
            assert result["success"] is False
            assert "error" in result
            assert result["file_path"] is None
    
    @patch('analyzer.video_downloader.subprocess.run')
    def test_get_video_info_success(self, mock_subprocess):
        """Test getting video info without download."""
        # Mock subprocess.run for info extraction
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '''
        {
            "title": "Test Video",
            "duration": 120,
            "uploader": "Test User",
            "view_count": 1000,
            "upload_date": "20231201",
            "description": "Test description",
            "thumbnail": "https://example.com/thumb.jpg",
            "webpage_url": "https://youtube.com/watch?v=123",
            "formats": [{"format_id": "best", "ext": "mp4"}]
        }
        '''
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        downloader = VideoDownloader()
        result = downloader.get_video_info("https://youtube.com/watch?v=123")
        
        assert result["success"] is True
        assert result["title"] == "Test Video"
        assert result["duration"] == 120
        assert result["uploader"] == "Test User"
        assert result["view_count"] == 1000
        assert result["upload_date"] == "20231201"
        assert result["description"] == "Test description"
        assert result["thumbnail"] == "https://example.com/thumb.jpg"
        assert result["webpage_url"] == "https://youtube.com/watch?v=123"
        assert "formats" in result
    
    @patch('analyzer.video_downloader.subprocess.run')
    def test_get_video_info_failure(self, mock_subprocess):
        """Test getting video info failure."""
        # Mock subprocess.run to raise exception
        mock_subprocess.side_effect = Exception("Info extraction failed")
        
        downloader = VideoDownloader()
        result = downloader.get_video_info("https://youtube.com/watch?v=123")
        
        assert result["success"] is False
        assert "error" in result
        assert result["url"] == "https://youtube.com/watch?v=123"
    
    def test_find_downloaded_file_from_template(self):
        """Test finding downloaded file from yt-dlp template."""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(Path(temp_dir))
            
            # Create a test file
            test_file = Path(temp_dir) / "test_video.mp4"
            test_file.touch()
            
            template = str(Path(temp_dir) / "test_video.%(ext)s")
            result = downloader._find_downloaded_file_from_template(template)
            
            assert result == test_file
    
    def test_analyze_download_errors_no_errors(self):
        """Test error analysis with no errors."""
        downloader = VideoDownloader()
        output = "[download] Downloading video..."
        
        errors = downloader._analyze_download_errors(output)
        
        assert errors['has_critical_errors'] is False
        assert errors['has_403_errors'] is False
        assert errors['error_summary'] == 'No errors'
    
    def test_analyze_download_errors_403(self):
        """Test error analysis with 403 errors."""
        downloader = VideoDownloader()
        output = "[download] HTTP Error 403: Forbidden"
        
        errors = downloader._analyze_download_errors(output)
        
        assert errors['has_critical_errors'] is True
        assert errors['has_403_errors'] is True
        assert errors['errors_403'] == 1
        assert '403 Forbidden errors' in errors['error_summary']
    
    def test_analyze_download_errors_skipped_fragments(self):
        """Test error analysis with skipped fragments."""
        downloader = VideoDownloader()
        output = """
        [download] Skipping fragment 1
        [download] Skipping fragment 2
        [download] Skipping fragment 3
        """
        
        errors = downloader._analyze_download_errors(output)
        
        assert errors['has_critical_errors'] is True
        assert errors['skipped_fragments'] == 3
    
    def test_cleanup_downloads(self):
        """Test cleanup of download directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            download_dir = Path(temp_dir) / "test_downloads"
            download_dir.mkdir()
            
            # Create some test files
            (download_dir / "test1.mp4").touch()
            (download_dir / "test2.mp4").touch()
            
            downloader = VideoDownloader(download_dir)
            downloader.cleanup_downloads()
            
            assert not download_dir.exists()


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('analyzer.video_downloader.VideoDownloader')
    def test_download_video_from_url(self, mock_downloader_class):
        """Test download_video_from_url convenience function."""
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.download_video.return_value = {"success": True, "file_path": Path("test.mp4")}
        
        result = download_video_from_url("https://youtube.com/watch?v=123")
        
        mock_downloader_class.assert_called_once()
        mock_downloader.download_video.assert_called_once_with("https://youtube.com/watch?v=123", None)
        assert result["success"] is True
    
    @patch('analyzer.video_downloader.VideoDownloader')
    def test_is_video_url(self, mock_downloader_class):
        """Test is_video_url convenience function."""
        mock_downloader = MagicMock()
        mock_downloader_class.return_value = mock_downloader
        mock_downloader.is_supported_url.return_value = True
        
        result = is_video_url("https://youtube.com/watch?v=123")
        
        mock_downloader_class.assert_called_once()
        mock_downloader.is_supported_url.assert_called_once_with("https://youtube.com/watch?v=123")
        assert result is True
