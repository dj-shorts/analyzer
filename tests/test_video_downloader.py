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
    
    @patch('analyzer.video_downloader.yt_dlp.YoutubeDL')
    def test_download_video_success(self, mock_ydl_class):
        """Test successful video download."""
        # Mock yt-dlp
        mock_ydl = MagicMock()
        mock_ydl_class.return_value = mock_ydl
        
        # Mock video info
        mock_info = {
            'title': 'Test Video',
            'duration': 120,
            'uploader': 'Test User',
            'view_count': 1000,
            'upload_date': '20231201',
            'description': 'Test description',
            'thumbnail': 'https://example.com/thumb.jpg',
            'webpage_url': 'https://youtube.com/watch?v=123'
        }
        mock_ydl.extract_info.return_value = mock_info
        
        # Mock file creation
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(Path(temp_dir))
            
            # Mock the downloaded file
            mock_file = Path(temp_dir) / "test_video.mp4"
            mock_file.touch()
            
            with patch.object(downloader, '_find_downloaded_file', return_value=mock_file):
                result = downloader.download_video("https://youtube.com/watch?v=123")
            
            assert result["success"] is True
            assert result["file_path"] == mock_file
            assert result["title"] == "Test Video"
            assert result["duration"] == 120
            assert result["uploader"] == "Test User"
            assert result["view_count"] == 1000
            assert result["upload_date"] == "20231201"
            assert result["description"] == "Test description"
            assert result["thumbnail"] == "https://example.com/thumb.jpg"
            assert result["webpage_url"] == "https://youtube.com/watch?v=123"
            assert "file_size" in result
    
    @patch('analyzer.video_downloader.yt_dlp.YoutubeDL')
    def test_download_video_failure(self, mock_ydl_class):
        """Test video download failure."""
        # Mock yt-dlp to raise exception
        mock_ydl = MagicMock()
        mock_ydl_class.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = Exception("Download failed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(Path(temp_dir))
            result = downloader.download_video("https://youtube.com/watch?v=123")
            
            assert result["success"] is False
            assert "error" in result
            assert result["url"] == "https://youtube.com/watch?v=123"
    
    @patch('analyzer.video_downloader.yt_dlp.YoutubeDL')
    def test_get_video_info_success(self, mock_ydl_class):
        """Test getting video info without download."""
        # Mock yt-dlp
        mock_ydl = MagicMock()
        mock_ydl_class.return_value = mock_ydl
        
        # Mock video info
        mock_info = {
            'title': 'Test Video',
            'duration': 120,
            'uploader': 'Test User',
            'view_count': 1000,
            'upload_date': '20231201',
            'description': 'Test description',
            'thumbnail': 'https://example.com/thumb.jpg',
            'webpage_url': 'https://youtube.com/watch?v=123',
            'formats': [{'format_id': 'best', 'ext': 'mp4'}]
        }
        mock_ydl.extract_info.return_value = mock_info
        
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
    
    @patch('analyzer.video_downloader.yt_dlp.YoutubeDL')
    def test_get_video_info_failure(self, mock_ydl_class):
        """Test getting video info failure."""
        # Mock yt-dlp to raise exception
        mock_ydl = MagicMock()
        mock_ydl_class.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = Exception("Info extraction failed")
        
        downloader = VideoDownloader()
        result = downloader.get_video_info("https://youtube.com/watch?v=123")
        
        assert result["success"] is False
        assert "error" in result
        assert result["url"] == "https://youtube.com/watch?v=123"
    
    def test_find_downloaded_file_with_output_path(self):
        """Test finding downloaded file with specified output path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(Path(temp_dir))
            
            # Create a test file
            test_file = Path(temp_dir) / "test_video.mp4"
            test_file.touch()
            
            mock_info = {'title': 'Test Video'}
            result = downloader._find_downloaded_file(mock_info, test_file)
            
            assert result == test_file
    
    def test_find_downloaded_file_by_title(self):
        """Test finding downloaded file by title."""
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = VideoDownloader(Path(temp_dir))
            
            # Create a test file with title-based name
            test_file = downloader.download_dir / "Test Video.mp4"
            test_file.touch()
            
            mock_info = {'title': 'Test Video'}
            result = downloader._find_downloaded_file(mock_info, None)
            
            assert result == test_file
    
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
