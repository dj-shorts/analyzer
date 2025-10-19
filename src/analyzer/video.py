"""
Video export functionality for Epic D1 and D2.
Handles 16:9 original export with stream copy / fallback h264.
Supports 9:16 vertical and 1:1 square formats with crop and scale.
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
        
        # Format definitions
        self.formats = {
            "original": {"width": None, "height": None, "crop": False},
            "vertical": {"width": 1080, "height": 1920, "crop": True},  # 9:16
            "square": {"width": 1080, "height": 1080, "crop": True}     # 1:1
        }
        
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
            
            # Generate output filename with format suffix
            format_suffix = f"_{self.config.export_format}" if self.config.export_format != "original" else ""
            output_filename = f"clip_{clip_id:03d}_{start_time:.1f}s-{end_time:.1f}s{format_suffix}.mp4"
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
        # Check if we need format conversion (crop/scale)
        if self.config.export_format != "original":
            # Always use transcoding for format conversion
            logger.info(f"Format conversion required, using transcoding for {output_path.name}")
            return self._transcode_with_format(input_path, output_path, start_time, end_time)
        
        # For original format, try stream copy first
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

    def _transcode_with_format(self, input_path: Path, output_path: Path, start_time: float, end_time: float) -> Dict[str, Any]:
        """
        Transcode video with format conversion (crop/scale).
        
        Args:
            input_path: Path to input video file
            output_path: Path for output clip
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            Dict containing export result
        """
        duration = end_time - start_time
        format_config = self.formats[self.config.export_format]
        
        # Get video dimensions first
        video_info = self.get_video_info(input_path)
        if "error" in video_info:
            return {"success": False, "error": f"Could not get video info: {video_info['error']}"}
        
        # Find video stream dimensions
        input_width = None
        input_height = None
        for stream in video_info.get("streams", []):
            if stream.get("codec_type") == "video":
                input_width = stream.get("width")
                input_height = stream.get("height")
                break
        
        if not input_width or not input_height:
            return {"success": False, "error": "Could not determine input video dimensions"}
        
        # Build FFmpeg command with format conversion
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output files
            "-ss", str(start_time),  # Start time
            "-t", str(duration),  # Duration
            "-i", str(input_path),  # Input file
        ]
        
        # Add video filter for crop and scale
        if format_config["crop"]:
            crop_scale_filter = self._build_crop_scale_filter(
                input_width, input_height, 
                format_config["width"], format_config["height"]
            )
            cmd.extend(["-vf", crop_scale_filter])
        else:
            # Just scale if no crop needed
            cmd.extend(["-vf", f"scale={format_config['width']}:{format_config['height']}"])
        
        # Add codec parameters
        cmd.extend(self.h264_params)
        cmd.extend(self.audio_params)
        
        # Add output parameters
        cmd.extend([
            "-r", "30",  # 30 fps
            "-avoid_negative_ts", "make_zero",
            str(output_path)
        ])
        
        try:
            logger.debug(f"Running format transcoding command: {' '.join(cmd)}")
            
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
                    "method": f"transcode_{self.config.export_format}",
                    "file_size": file_size
                }
            else:
                error_msg = f"FFmpeg format transcoding failed: {result.stderr}"
                logger.error(f"Format transcoding failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except subprocess.TimeoutExpired:
            error_msg = "FFmpeg format transcoding timed out"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error in format transcoding: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

    def _build_crop_scale_filter(self, input_width: int, input_height: int, target_width: int, target_height: int) -> str:
        """
        Build FFmpeg filter for crop and scale operations.
        
        Args:
            input_width: Input video width
            input_height: Input video height
            target_width: Target output width
            target_height: Target output height
            
        Returns:
            FFmpeg filter string
        """
        # Calculate aspect ratios
        input_aspect = input_width / input_height
        target_aspect = target_width / target_height
        
        if input_aspect > target_aspect:
            # Input is wider than target, crop width
            crop_width = int(input_height * target_aspect)
            crop_height = input_height
            crop_x = (input_width - crop_width) // 2
            crop_y = 0
        else:
            # Input is taller than target, crop height
            crop_width = input_width
            crop_height = int(input_width / target_aspect)
            crop_x = 0
            crop_y = (input_height - crop_height) // 2
        
        # Build filter: crop then scale
        filter_parts = [
            f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y}",
            f"scale={target_width}:{target_height}"
        ]
        
        return ",".join(filter_parts)
