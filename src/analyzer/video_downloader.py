"""
Video downloader module for YouTube and external video sources.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

import yt_dlp

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Handles video downloads from various sources."""
    
    def __init__(self, download_dir: Optional[Path] = None):
        """
        Initialize video downloader.
        
        Args:
            download_dir: Directory to save downloaded videos (default: temp dir)
        """
        self.download_dir = download_dir or Path(tempfile.gettempdir()) / "analyzer_downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Default yt-dlp options
        self.default_options = {
            'outtmpl': str(self.download_dir / '%(title)s.%(ext)s'),
            'format': 'best[height<=1080]',  # Prefer HD but not 4K
            'noplaylist': True,  # Download single video, not playlist
            'extract_flat': False,
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': False,
            'no_warnings': False,
            'quiet': False,
        }
    
    def is_supported_url(self, url: str) -> bool:
        """
        Check if the URL is supported for download.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is supported, False otherwise
        """
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Check if it's a direct video file
            if parsed.path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v')):
                return True
            
            # Check if it's a supported platform
            supported_domains = [
                'youtube.com', 'youtu.be', 'm.youtube.com',
                'vimeo.com', 'dailymotion.com', 'twitch.tv',
                'drive.google.com', 'onedrive.live.com', 'dropbox.com'
            ]
            
            domain = parsed.netloc.lower()
            return any(supported in domain for supported in supported_domains)
            
        except Exception as e:
            logger.warning(f"Error checking URL support: {e}")
            return False
    
    def download_video(self, url: str, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Download video from URL.
        
        Args:
            url: Video URL to download
            output_path: Optional custom output path
            
        Returns:
            Dict containing download results and metadata
        """
        logger.info(f"Starting video download from: {url}")
        
        try:
            # Prepare output path
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                options = self.default_options.copy()
                # Preserve extension by adding %(ext)s placeholder
                options['outtmpl'] = str(output_path.with_suffix('')) + '.%(ext)s'
            else:
                options = self.default_options.copy()
            
            # Create yt-dlp instance
            ydl = yt_dlp.YoutubeDL(options)
            
            # Extract video info first
            info = ydl.extract_info(url, download=False)
            
            # Download the video
            ydl.download([url])
            
            # Find the downloaded file
            downloaded_file = self._find_downloaded_file(info, output_path)
            
            if not downloaded_file or not downloaded_file.exists():
                raise FileNotFoundError("Downloaded file not found")
            
            logger.info(f"Video downloaded successfully: {downloaded_file}")
            
            return {
                "success": True,
                "file_path": downloaded_file,
                "title": info.get('title', 'Unknown'),
                "duration": info.get('duration', 0),
                "uploader": info.get('uploader', 'Unknown'),
                "view_count": info.get('view_count', 0),
                "upload_date": info.get('upload_date', ''),
                "description": info.get('description', ''),
                "thumbnail": info.get('thumbnail', ''),
                "webpage_url": info.get('webpage_url', url),
                "file_size": downloaded_file.stat().st_size,
            }
            
        except Exception as e:
            logger.error(f"Video download failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url,
            }
    
    def _find_downloaded_file(self, info: Dict[str, Any], output_path: Optional[Path]) -> Optional[Path]:
        """
        Find the downloaded video file.
        
        Args:
            info: Video info from yt-dlp
            output_path: Expected output path
            
        Returns:
            Path to downloaded file or None if not found
        """
        if output_path and output_path.exists():
            return output_path
        
        # Determine search directory and base name based on output_path
        if output_path:
            # For custom paths, search in the output directory
            search_dir = output_path.parent
            base_name = output_path.stem  # filename without extension
        else:
            # For default downloads, search in download_dir by title
            search_dir = self.download_dir
            title = info.get('title', 'Unknown')
            # Clean title for filename
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            base_name = safe_title
        
        # Look for common video extensions
        extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov', '.m4v']
        
        for ext in extensions:
            filename = f"{base_name}{ext}"
            file_path = search_dir / filename
            if file_path.exists():
                return file_path
        
        # If not found by name, look for any video file in search directory
        for file_path in search_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                # Check if it's recent (downloaded in last 5 minutes)
                import time
                if time.time() - file_path.stat().st_mtime < 300:
                    return file_path
        
        return None
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video information without downloading.
        
        Args:
            url: Video URL
            
        Returns:
            Dict containing video metadata
        """
        try:
            ydl = yt_dlp.YoutubeDL({'quiet': True})
            info = ydl.extract_info(url, download=False)
            
            return {
                "success": True,
                "title": info.get('title', 'Unknown'),
                "duration": info.get('duration', 0),
                "uploader": info.get('uploader', 'Unknown'),
                "view_count": info.get('view_count', 0),
                "upload_date": info.get('upload_date', ''),
                "description": info.get('description', ''),
                "thumbnail": info.get('thumbnail', ''),
                "webpage_url": info.get('webpage_url', url),
                "formats": info.get('formats', []),
            }
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url,
            }
    
    def cleanup_downloads(self) -> None:
        """Clean up downloaded files."""
        try:
            import shutil
            if self.download_dir.exists():
                shutil.rmtree(self.download_dir)
                logger.info(f"Cleaned up download directory: {self.download_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup downloads: {e}")


def download_video_from_url(url: str, output_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Convenience function to download video from URL.
    
    Args:
        url: Video URL
        output_path: Optional output path
        
    Returns:
        Download result dictionary
    """
    downloader = VideoDownloader()
    return downloader.download_video(url, output_path)


def is_video_url(url: str) -> bool:
    """
    Convenience function to check if URL is a video URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL is supported for video download
    """
    downloader = VideoDownloader()
    return downloader.is_supported_url(url)
