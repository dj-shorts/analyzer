"""
Video downloader module for YouTube and external video sources.
"""

import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Handles video downloads from various sources using system yt-dlp."""
    
    def __init__(self, download_dir: Optional[Path] = None):
        """
        Initialize video downloader.
        
        Args:
            download_dir: Directory to save downloaded videos (default: temp dir)
        """
        self.download_dir = download_dir or Path(tempfile.gettempdir()) / "analyzer_downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)
    
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
        Download video from URL using system yt-dlp.
        
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
                output_template = str(output_path.with_suffix('')) + '.%(ext)s'
            else:
                output_template = str(self.download_dir / '%(title)s.%(ext)s')
            
            # Check if file already exists (common video extensions)
            video_extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov', '.m4v']
            template_path = Path(output_template)
            search_dir = template_path.parent
            
            # Look for existing files in the search directory
            for file_path in search_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                    # Check if it's a recent video file (downloaded in last 24 hours)
                    if time.time() - file_path.stat().st_mtime < 86400:  # 24 hours
                        logger.info(f"Found existing video file: {file_path}")
                        return {
                            "success": True,
                            "file_path": file_path,
                            "title": file_path.stem,
                            "duration": 0,  # Would need ffprobe to get duration
                            "format": "existing",
                            "filesize": file_path.stat().st_size
                        }
            
            # Try different format strategies (matching working yt-dlp command)
            # For HLS videos, let yt-dlp auto-select the best combination
            format_strategies = [
                'best[height<=1080]',  # Best quality up to 1080p (matches working CLI)
                'best[height<=720]',    # Best quality up to 720p
                'best',                # Any available format
                'worst',               # Last resort
            ]
            
            downloaded_file = None
            last_error = None
            
            for format_strategy in format_strategies:
                try:
                    logger.info(f"Trying format strategy: {format_strategy}")
                    
                    # Build yt-dlp command (matching working example)
                    # Critical: Add options to prevent 403 errors on fragments
                    cmd = [
                        'yt-dlp',
                        '-f', format_strategy,
                        '-o', output_template,
                        '--no-playlist',
                        '--no-check-certificate',  # Skip certificate verification
                        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',  # Use browser UA
                        '--referer', 'https://www.youtube.com/',  # Set referer
                        '--fragment-retries', '10',  # Retry failed fragments
                        '--retries', '10',  # Retry connection failures
                        '--concurrent-fragments', '1',  # Download fragments sequentially to avoid rate limiting
                        url
                    ]
                    
                    # Run yt-dlp command with stderr capture for error detection
                    logger.info(f"Running command: {' '.join(cmd)}")
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=1800  # 30 minutes timeout
                    )
                    
                    # Check for critical errors in output
                    error_output = result.stderr + result.stdout
                    fragment_errors = self._analyze_download_errors(error_output)
                    
                    if fragment_errors['has_critical_errors']:
                        error_msg = f"Critical download errors detected: {fragment_errors['error_summary']}"
                        logger.error(error_msg)
                        last_error = error_msg
                        
                        # If we have 403 errors, try next strategy
                        if fragment_errors['has_403_errors']:
                            logger.warning("403 Forbidden errors detected, trying next format strategy...")
                            continue
                        else:
                            # Other critical errors - stop trying
                            raise RuntimeError(error_msg)
                    
                    if result.returncode == 0:
                        # Find the downloaded file
                        downloaded_file = self._find_downloaded_file_from_template(output_template)
                        
                        if downloaded_file and downloaded_file.exists():
                            logger.info(f"Successfully downloaded with format: {format_strategy}")
                            
                            # Log any warnings from download
                            if fragment_errors['skipped_fragments'] > 0:
                                logger.warning(f"Download completed with {fragment_errors['skipped_fragments']} skipped fragments")
                            
                            break
                        else:
                            logger.warning(f"Download completed but file not found: {output_template}")
                    else:
                        logger.warning(f"yt-dlp failed with return code {result.returncode}")
                        logger.debug(f"Error output: {error_output}")
                        
                except subprocess.TimeoutExpired:
                    logger.warning(f"Download timeout for format: {format_strategy}")
                    last_error = f"Download timeout for format: {format_strategy}"
                    continue
                except Exception as e:
                    logger.warning(f"Format strategy '{format_strategy}' failed: {str(e)}")
                    last_error = str(e)
                    continue
            
            if not downloaded_file or not downloaded_file.exists():
                error_msg = f"Downloaded file not found with any format strategy. Last error: {last_error}"
                raise FileNotFoundError(error_msg)
            
            logger.info(f"Video downloaded successfully: {downloaded_file}")
            
            # Get basic file info
            file_size = downloaded_file.stat().st_size if downloaded_file.exists() else 0
            
            return {
                "success": True,
                "file_path": downloaded_file,
                "title": downloaded_file.stem,  # Use filename as title
                "duration": 0,  # Would need ffprobe to get duration
                "format": format_strategy,
                "filesize": file_size
            }
            
        except Exception as e:
            logger.error(f"Video download failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "file_path": None
            }
    
    def _analyze_download_errors(self, output: str) -> Dict[str, Any]:
        """
        Analyze yt-dlp output for critical errors.
        
        Args:
            output: Combined stderr and stdout from yt-dlp
            
        Returns:
            Dict with error analysis results
        """
        # Count different error types
        errors_403 = output.count('HTTP Error 403: Forbidden')
        errors_404 = output.count('HTTP Error 404')
        errors_timeout = output.count('timed out')
        skipped_fragments = output.count('Skipping fragment')
        failed_fragments = output.count('unable to download fragment')
        
        # Determine if errors are critical
        # Allow up to 2 skipped fragments as non-critical (video might still be usable)
        has_critical_errors = (
            errors_403 > 0 or 
            errors_404 > 0 or 
            errors_timeout > 2 or
            failed_fragments > 2 or
            skipped_fragments > 2
        )
        
        # Build error summary
        error_summary = []
        if errors_403 > 0:
            error_summary.append(f"{errors_403} 403 Forbidden errors")
        if errors_404 > 0:
            error_summary.append(f"{errors_404} 404 Not Found errors")
        if errors_timeout > 0:
            error_summary.append(f"{errors_timeout} timeout errors")
        if skipped_fragments > 0:
            error_summary.append(f"{skipped_fragments} skipped fragments")
        if failed_fragments > 0:
            error_summary.append(f"{failed_fragments} failed fragments")
        
        return {
            'has_critical_errors': has_critical_errors,
            'has_403_errors': errors_403 > 0,
            'errors_403': errors_403,
            'errors_404': errors_404,
            'errors_timeout': errors_timeout,
            'skipped_fragments': skipped_fragments,
            'failed_fragments': failed_fragments,
            'error_summary': ', '.join(error_summary) if error_summary else 'No errors'
        }
    
    def _find_downloaded_file_from_template(self, template: str) -> Optional[Path]:
        """
        Find the downloaded video file from yt-dlp template.
        
        Args:
            template: yt-dlp output template
            
        Returns:
            Path to downloaded file or None if not found
        """
        # Extract directory and filename pattern from template
        template_path = Path(template)
        search_dir = template_path.parent
        filename_pattern = template_path.name
        
        # Look for common video extensions
        extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov', '.m4v']
        
        # Try to find file by pattern
        for ext in extensions:
            # Replace %(ext)s with actual extension
            filename = filename_pattern.replace('%(ext)s', ext[1:])  # Remove dot
            file_path = search_dir / filename
            if file_path.exists():
                return file_path
        
        # If not found by pattern, look for any video file in search directory
        for file_path in search_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                # Check if it's recent (downloaded in last 5 minutes)
                if time.time() - file_path.stat().st_mtime < 300:
                    return file_path
        
        return None
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video information without downloading using system yt-dlp.
        
        Args:
            url: Video URL
            
        Returns:
            Dict containing video metadata
        """
        try:
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-download',
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                
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
            else:
                logger.error(f"yt-dlp info failed: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "url": url,
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