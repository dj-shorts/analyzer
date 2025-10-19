"""
Video export functionality for Epic D1.
Handles 16:9 original export with stream copy / fallback h264.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

from .config import Config

logger = logging.getLogger(__name__)


class VideoExporter:
    """Exports video clips with stream copy or h264 transcoding."""

    def __init__(self, config: Config):
        """Initialize video exporter with configuration."""
        self.config = config
        
        # FFmpeg parameters for h264 transcoding
        self.h264_params = [
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p"
        ]
        
        # Audio codec parameters
        self.audio_params = [
            "-c:a", "aac",
            "-b:a", "128k"
        ]

    def export_clips(self, segments_data: Dict[str, Any], input_video_path: Path, output_dir: Path) -> Dict[str, Any]:
        """
        Export video clips from segments.
        
        Args:
            segments_data: Dict containing segments with timing information
            input_video_path: Path to input video file
            output_dir: Directory to save exported clips
            
        Returns:
            Dict containing export results and metadata
        """
        logger.info(f"Starting video export for {len(segments_data['segments'])} clips")
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exported_clips = []
        export_errors = []
        
        for i, segment in enumerate(segments_data["segments"]):
            clip_id = segment["clip_id"]
            start_time = segment["start"]
            end_time = segment["end"]
            
            logger.info(f"Exporting clip {clip_id}: {start_time:.2f}s - {end_time:.2f}s")
            
            # Generate output filename
            output_filename = f"clip_{clip_id:03d}_{start_time:.1f}s-{end_time:.1f}s.mp4"
            output_path = output_dir / output_filename
            
            try:
                # Export single clip
                export_result = self._export_single_clip(
                    input_video_path, output_path, start_time, end_time
                )
                
                if export_result["success"]:
                    exported_clips.append({
                        "clip_id": clip_id,
                        "output_path": str(output_path),
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": end_time - start_time,
                        "export_method": export_result["method"],
                        "file_size": export_result.get("file_size", 0)
                    })
                    logger.info(f"✅ Successfully exported clip {clip_id} using {export_result['method']}")
                else:
                    export_errors.append({
                        "clip_id": clip_id,
                        "error": export_result["error"]
                    })
                    logger.error(f"❌ Failed to export clip {clip_id}: {export_result['error']}")
                    
            except Exception as e:
                error_msg = f"Unexpected error exporting clip {clip_id}: {str(e)}"
                export_errors.append({
                    "clip_id": clip_id,
                    "error": error_msg
                })
                logger.error(f"❌ {error_msg}")
        
        # Create export summary
        export_summary = {
            "total_clips": len(segments_data["segments"]),
            "exported_clips": len(exported_clips),
            "failed_clips": len(export_errors),
            "exported_clips_list": exported_clips,
            "export_errors": export_errors,
            "output_directory": str(output_dir)
        }
        
        logger.info(f"Video export completed: {len(exported_clips)}/{len(segments_data['segments'])} clips exported successfully")
        
        return export_summary

    def _export_single_clip(self, input_path: Path, output_path: Path, start_time: float, end_time: float) -> Dict[str, Any]:
        """
        Export a single video clip.
        
        Args:
            input_path: Path to input video file
            output_path: Path for output clip
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            Dict containing export result and metadata
        """
        # First, try stream copy for compatible codecs
        stream_copy_result = self._try_stream_copy(input_path, output_path, start_time, end_time)
        
        if stream_copy_result["success"]:
            return stream_copy_result
        
        # If stream copy fails, fallback to h264 transcoding
        logger.info(f"Stream copy failed, falling back to h264 transcoding for {output_path.name}")
        return self._transcode_to_h264(input_path, output_path, start_time, end_time)

    def _try_stream_copy(self, input_path: Path, output_path: Path, start_time: float, end_time: float) -> Dict[str, Any]:
        """
        Try to export using stream copy for compatible codecs.
        
        Args:
            input_path: Path to input video file
            output_path: Path for output clip
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            Dict containing export result
        """
        duration = end_time - start_time
        
        # FFmpeg command for stream copy
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output files
            "-ss", str(start_time),  # Start time
            "-t", str(duration),  # Duration
            "-i", str(input_path),  # Input file
            "-c", "copy",  # Stream copy
            "-avoid_negative_ts", "make_zero",  # Handle negative timestamps
            str(output_path)
        ]
        
        try:
            logger.debug(f"Running stream copy command: {' '.join(cmd)}")
            
            # Run FFmpeg command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0 and output_path.exists():
                file_size = output_path.stat().st_size
                return {
                    "success": True,
                    "method": "stream_copy",
                    "file_size": file_size
                }
            else:
                error_msg = f"FFmpeg stream copy failed: {result.stderr}"
                logger.warning(f"Stream copy failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except subprocess.TimeoutExpired:
            error_msg = "FFmpeg stream copy timed out"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error in stream copy: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

    def _transcode_to_h264(self, input_path: Path, output_path: Path, start_time: float, end_time: float) -> Dict[str, Any]:
        """
        Transcode video to h264 with high quality settings.
        
        Args:
            input_path: Path to input video file
            output_path: Path for output clip
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            Dict containing export result
        """
        duration = end_time - start_time
        
        # FFmpeg command for h264 transcoding
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output files
            "-ss", str(start_time),  # Start time
            "-t", str(duration),  # Duration
            "-i", str(input_path),  # Input file
            *self.h264_params,  # Video codec parameters
            *self.audio_params,  # Audio codec parameters
            "-avoid_negative_ts", "make_zero",  # Handle negative timestamps
            str(output_path)
        ]
        
        try:
            logger.debug(f"Running h264 transcoding command: {' '.join(cmd)}")
            
            # Run FFmpeg command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for transcoding
            )
            
            if result.returncode == 0 and output_path.exists():
                file_size = output_path.stat().st_size
                return {
                    "success": True,
                    "method": "h264_transcode",
                    "file_size": file_size
                }
            else:
                error_msg = f"FFmpeg h264 transcoding failed: {result.stderr}"
                logger.error(f"H264 transcoding failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except subprocess.TimeoutExpired:
            error_msg = "FFmpeg h264 transcoding timed out"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error in h264 transcoding: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

    def get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """
        Get video information using FFprobe.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict containing video metadata
        """
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"FFprobe failed: {result.stderr}")
                return {"error": f"FFprobe failed: {result.stderr}"}
                
        except Exception as e:
            error_msg = f"Error getting video info: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def is_codec_compatible(self, video_path: Path) -> Dict[str, bool]:
        """
        Check if video codecs are compatible for stream copy.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict containing compatibility info
        """
        video_info = self.get_video_info(video_path)
        
        if "error" in video_info:
            return {"compatible": False, "error": video_info["error"]}
        
        video_compatible = False
        audio_compatible = False
        
        for stream in video_info.get("streams", []):
            if stream.get("codec_type") == "video":
                codec_name = stream.get("codec_name", "").lower()
                if codec_name in ["h264", "h.264", "avc"]:
                    video_compatible = True
            elif stream.get("codec_type") == "audio":
                codec_name = stream.get("codec_name", "").lower()
                if codec_name in ["aac", "mp4a"]:
                    audio_compatible = True
        
        return {
            "compatible": video_compatible and audio_compatible,
            "video_compatible": video_compatible,
            "audio_compatible": audio_compatible
        }
