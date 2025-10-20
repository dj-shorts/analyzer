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
from .people_detector import PeopleDetector
from .object_tracker import ObjectTracker
from .dynamic_cropper import DynamicCropper

logger = logging.getLogger(__name__)


class VideoExporter:
    """Exports video clips with stream copy or h264 transcoding."""

    def __init__(self, config: Config):
        """Initialize video exporter with configuration."""
        self.config = config
        
        # Initialize people detector if auto-reframe is enabled
        if config.auto_reframe:
            self.people_detector = PeopleDetector(config)
        else:
            self.people_detector = None
        
        # Initialize object tracker and dynamic cropper if object tracking is enabled
        if config.enable_object_tracking:
            self.object_tracker = ObjectTracker(config)
            self.dynamic_cropper = DynamicCropper(config)
        else:
            self.object_tracker = None
            self.dynamic_cropper = None
        
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
        
        # Perform object tracking analysis if enabled
        tracking_data = None
        if self.config.enable_object_tracking and self.object_tracker:
            logger.info("Performing object tracking analysis for dynamic cropping")
            tracking_data = self.object_tracker.analyze_video_tracking(input_video_path)
            
            # Log debug video path if available
            if tracking_data.get("debug_video_path"):
                logger.info(f"Debug tracking video saved: {tracking_data['debug_video_path']}")
            # Log tracking metrics if available
            if tracking_data and tracking_data.get("metrics"):
                m = tracking_data["metrics"]
                logger.info(
                    "Tracking metrics — frames: %s, detections: %s (rate=%.2f), avg_conf=%.2f, time=%.2fs",
                    m.get("processed_frames"), m.get("detections"), m.get("detection_rate", 0.0), m.get("avg_confidence", 0.0), m.get("processing_time_sec", 0.0)
                )
        
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
                    input_video_path, output_path, start_time, end_time, tracking_data
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

    def _export_single_clip(self, input_path: Path, output_path: Path, start_time: float, end_time: float, tracking_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
        # Check if format requires transcoding
        if self.config.export_format == "original":
            # For original format, try stream copy first
            stream_copy_result = self._try_stream_copy(input_path, output_path, start_time, end_time)
            
            if stream_copy_result["success"]:
                return stream_copy_result
            
            # If stream copy fails, fallback to h264 transcoding
            logger.info(f"Stream copy failed, falling back to h264 transcoding for {output_path.name}")
            return self._transcode_to_h264(input_path, output_path, start_time, end_time)
        else:
            # For non-original formats, use transcoding with format conversion
            return self._transcode_with_format(input_path, output_path, start_time, end_time, tracking_data)

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
            Dict containing compatibility information
        """
        video_info = self.get_video_info(video_path)
        
        if "error" in video_info:
            return {"error": video_info["error"]}
        
        compatible = {"video": False, "audio": False}
        
        # Check video streams
        for stream in video_info.get("streams", []):
            if stream.get("codec_type") == "video":
                codec = stream.get("codec_name", "")
                # Check for common compatible codecs
                if codec in ["h264", "h265", "hevc", "vp9", "av1"]:
                    compatible["video"] = True
            elif stream.get("codec_type") == "audio":
                codec = stream.get("codec_name", "")
                # Check for common compatible audio codecs
                if codec in ["aac", "mp3", "ac3", "eac3"]:
                    compatible["audio"] = True
        
        return compatible

    def _transcode_with_format(self, input_path: Path, output_path: Path, start_time: float, end_time: float, tracking_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transcode video with format conversion (vertical/square).
        
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
        
        # Build FFmpeg command with format conversion
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output files
            "-ss", str(start_time),  # Start time
            "-t", str(duration),  # Duration
            "-i", str(input_path),  # Input file
        ]
        
        # Add video filter for format conversion
        if format_config["crop"]:
            # Check if object tracking is enabled
            if self.config.enable_object_tracking and tracking_data and self.dynamic_cropper:
                crop_scale_filter = self._build_dynamic_crop_filter(
                    input_path, start_time, duration, format_config, tracking_data
                )
            # Check if auto-reframe is enabled
            elif self.config.auto_reframe and self.people_detector:
                crop_scale_filter = self._build_auto_reframe_filter(
                    input_path, start_time, duration, format_config
                )
            else:
                crop_scale_filter = self._build_crop_scale_filter(format_config)
            cmd.extend(["-vf", crop_scale_filter])
        else:
            cmd.extend(self.h264_params)
        
        # Add audio codec parameters
        cmd.extend(self.audio_params)
        cmd.extend(["-avoid_negative_ts", "make_zero"])
        cmd.append(str(output_path))
        
        try:
            logger.debug(f"Running format conversion command: {' '.join(cmd)}")
            
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
                    "method": f"format_conversion_{self.config.export_format}",
                    "file_size": file_size
                }
            else:
                error_msg = f"FFmpeg format conversion failed: {result.stderr}"
                logger.error(f"Format conversion failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except subprocess.TimeoutExpired:
            error_msg = "FFmpeg format conversion timed out"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error in format conversion: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

    def _build_crop_scale_filter(self, format_config: Dict[str, Any]) -> str:
        """
        Build FFmpeg filter for crop and scale operations.
        
        Args:
            format_config: Format configuration dictionary
            
        Returns:
            FFmpeg filter string
        """
        width = format_config["width"]
        height = format_config["height"]
        
        # For vertical (9:16) and square (1:1) formats, we need to crop and scale
        # Crop to center and scale to target dimensions
        filter_parts = []
        
        # Crop to center (assuming 16:9 input)
        # For 16:9 to 9:16: crop width to maintain aspect ratio
        # For 16:9 to 1:1: crop both width and height
        if self.config.export_format == "vertical":
            # Crop to 9:16 aspect ratio from center
            filter_parts.append("crop=ih*9/16:ih")
        elif self.config.export_format == "square":
            # Crop to square from center
            filter_parts.append("crop=ih:ih")
        
        # Scale to target dimensions
        filter_parts.append(f"scale={width}:{height}")
        
        # Join filters
        filter_string = ",".join(filter_parts)
        
        return filter_string

    def _build_dynamic_crop_filter(self, input_path: Path, start_time: float, duration: float, format_config: Dict[str, Any], tracking_data: Dict[str, Any]) -> str:
        """
        Build FFmpeg filter with dynamic cropping using object tracking.
        
        Args:
            input_path: Path to input video file
            start_time: Start time in seconds
            duration: Duration in seconds
            format_config: Format configuration dictionary
            tracking_data: Object tracking analysis results
            
        Returns:
            FFmpeg filter string with dynamic cropping
        """
        try:
            # Get video dimensions from tracking data
            video_width, video_height = tracking_data.get("video_dimensions", (1920, 1080))
            
            # Calculate crop dimensions for target format
            crop_width, crop_height = self.dynamic_cropper.calculate_crop_dimensions(
                video_width, video_height, self.config.export_format
            )
            
            # Generate timeline for this clip
            import numpy as np
            clip_times = np.linspace(start_time, start_time + duration, num=10)  # 10 points for smooth interpolation
            
            # Interpolate tracking positions for this clip timeline
            tracking_positions = self.object_tracker.interpolate_to_export_timeline(
                tracking_data, clip_times
            )
            
            # Validate and clamp crop positions
            validated_positions = self.dynamic_cropper.validate_crop_positions(
                tracking_positions, video_width, video_height, crop_width, crop_height
            )
            
            # Generate dynamic crop filter
            crop_filter = self.dynamic_cropper.generate_crop_filter(
                validated_positions, video_width, video_height, 
                crop_width, crop_height, start_time, duration
            )
            
            # Add scale filter
            scale_filter = f"scale={format_config['width']}:{format_config['height']}"
            
            # Combine filters
            combined_filter = f"{crop_filter},{scale_filter}"
            
            logger.info(f"Dynamic crop: Generated filter for {len(validated_positions)} tracking positions")
            
            return combined_filter
            
        except Exception as e:
            logger.warning(f"Dynamic crop failed: {e}, falling back to center crop")
            return self._build_crop_scale_filter(format_config)

    def _build_auto_reframe_filter(self, input_path: Path, start_time: float, duration: float, format_config: Dict[str, Any]) -> str:
        """
        Build FFmpeg filter with auto-reframe using people detection.
        
        Args:
            input_path: Path to input video file
            start_time: Start time in seconds
            duration: Duration in seconds
            format_config: Format configuration dictionary
            
        Returns:
            FFmpeg filter string with auto-reframe
        """
        try:
            # Detect people in the video segment
            detection_result = self.people_detector.detect_people_in_video_segment(
                input_path, start_time, duration
            )
            
            if detection_result["success"] and detection_result["center_x"] is not None:
                # Use people detection for crop center
                center_x = detection_result["center_x"]
                logger.info(f"Auto-reframe: Using people detection center X={center_x}")
                
                # Get input video dimensions (simplified - in practice you'd get from video info)
                input_width = 1920  # Default assumption
                input_height = 1080  # Default assumption
                
                # Calculate crop window around detected people
                crop_x, crop_y, crop_width, crop_height = self.people_detector.calculate_crop_window(
                    center_x, input_width, input_height, format_config["width"], format_config["height"]
                )
                
                # Build filter with auto-reframe crop
                filter_parts = [
                    f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y}",
                    f"scale={format_config['width']}:{format_config['height']}"
                ]
                
                return ",".join(filter_parts)
            else:
                # Fallback to center crop if no people detected
                logger.info("Auto-reframe: No people detected, falling back to center crop")
                return self._build_crop_scale_filter(format_config)
                
        except Exception as e:
            logger.warning(f"Auto-reframe failed: {e}, falling back to center crop")
            return self._build_crop_scale_filter(format_config)
