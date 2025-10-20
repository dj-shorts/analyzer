"""
Object tracking module for MVP Analyzer.

Implements dynamic object tracking for video export to keep subjects centered.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import time

import numpy as np
import cv2

from .config import Config

logger = logging.getLogger(__name__)


class ObjectTracker:
    """Tracks objects (people) across video frames for dynamic cropping."""
    
    def __init__(self, config: Config):
        """Initialize object tracker with configuration."""
        self.config = config
        
        # Initialize HOG person detector (reuse existing infrastructure)
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        
        # Tracking parameters
        self.tracking_smoothness = getattr(config, 'tracking_smoothness', 0.8)
        self.confidence_threshold = getattr(config, 'tracking_confidence_threshold', 0.5)
        self.fallback_to_center = getattr(config, 'fallback_to_center', True)
        
        # Tracking state
        self.tracker = None
        self.last_bbox = None
        self.tracking_lost_frames = 0
        self.max_lost_frames = 10  # Re-detect after 10 lost frames
        
        # Debug visualization
        self.debug_tracking = getattr(config, 'debug_tracking', False)
        self.debug_frames = []  # Store frames with tracking visualization
        
        logger.info(f"ObjectTracker initialized with smoothness={self.tracking_smoothness}, "
                   f"confidence={self.confidence_threshold}")
    
    def analyze_segments_tracking(self, video_path: Path, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze tracking for segments with smooth interpolation to full video FPS.
        
        Strategy:
        1. Audio analysis finds best segments
        2. Track objects at 4-6fps in segments  
        3. Build camera displacement vectors from center
        4. Smooth interpolation to full video FPS (24/30fps)
        
        Args:
            video_path: Path to input video file
            segments: List of segments with start/end times
            
        Returns:
            Dict containing tracking data with full FPS interpolation
        """
        logger.info(f"Starting hybrid segment tracking for {len(segments)} segments")
        
        try:
            # Open video capture
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                logger.error(f"Could not open video file: {video_path}")
                return self._create_fallback_tracking_data()
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if fps <= 0:
                logger.warning(f"Invalid FPS ({fps}), using fallback tracking data")
                cap.release()
                return self._create_fallback_tracking_data()
            
            # Use 4-6fps for tracking (balance between quality and speed)
            tracking_fps = 5.0
            frame_interval = max(1, int(fps / tracking_fps))
            
            logger.info(f"Hybrid tracking: {tracking_fps:.1f} fps sampling, interpolating to {fps:.1f} fps")
            
            # Process each segment
            segment_data = []
            total_processed = 0
            
            for i, segment in enumerate(segments):
                start_time = segment["start"]
                end_time = segment["end"]
                duration = end_time - start_time
                
                logger.info(f"Processing segment {i+1}/{len(segments)}: {start_time:.1f}s-{end_time:.1f}s ({duration:.1f}s)")
                
                # Seek to segment start
                cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
                
                # Track at reduced FPS
                segment_positions = []
                segment_times = []
                segment_confidences = []
                
                frame_count = 0
                segment_frames = int(duration * fps)
                
                for _ in range(segment_frames):
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    # Sample frames at tracking fps
                    if frame_count % frame_interval == 0:
                        crop_center, confidence = self._process_frame(frame, width, height)
                        
                        segment_positions.append(crop_center)
                        segment_times.append(start_time + frame_count / fps)
                        segment_confidences.append(confidence)
                    
                    frame_count += 1
                
                # Store segment data for interpolation
                segment_data.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'positions': np.array(segment_positions),
                    'times': np.array(segment_times),
                    'confidences': np.array(segment_confidences)
                })
                
                total_processed += len(segment_positions)
                logger.info(f"Segment {i+1}: {len(segment_positions)} tracking points at {tracking_fps:.1f}fps")
            
            cap.release()
            
            if not segment_data:
                logger.warning("No tracking data extracted from segments, using fallback")
                return self._create_fallback_tracking_data()
            
            # Interpolate each segment to full video FPS for smooth movement
            all_crop_positions = []
            all_frame_times = []
            all_confidence_scores = []
            
            for segment in segment_data:
                # Create full FPS timeline for this segment
                segment_start = segment['start_time']
                segment_end = segment['end_time']
                segment_duration = segment_end - segment_start
                
                # Generate full FPS timeline
                full_fps_times = np.linspace(segment_start, segment_end, 
                                           int(segment_duration * fps) + 1)
                
                if len(segment['positions']) > 1:
                    # Interpolate positions to full FPS
                    interpolated_x = np.interp(full_fps_times, segment['times'], 
                                            segment['positions'][:, 0])
                    interpolated_y = np.interp(full_fps_times, segment['times'], 
                                            segment['positions'][:, 1])
                    interpolated_conf = np.interp(full_fps_times, segment['times'], 
                                                segment['confidences'])
                    
                    # Combine interpolated positions
                    interpolated_positions = np.column_stack([interpolated_x, interpolated_y])
                else:
                    # Single point - replicate for all frames
                    interpolated_positions = np.tile(segment['positions'][0], 
                                                   (len(full_fps_times), 1))
                    interpolated_conf = np.full(len(full_fps_times), 
                                              segment['confidences'][0] if len(segment['confidences']) > 0 else 0.0)
                
                all_crop_positions.extend(interpolated_positions)
                all_frame_times.extend(full_fps_times)
                all_confidence_scores.extend(interpolated_conf)
            
            # Convert to numpy arrays
            crop_positions = np.array(all_crop_positions)
            frame_times = np.array(all_frame_times)
            confidence_scores = np.array(all_confidence_scores)
            
            # Apply additional smoothing for ultra-smooth movement
            smoothed_positions = self._ultra_smooth_positions(crop_positions, confidence_scores, fps)
            
            logger.info(f"Hybrid tracking completed: {total_processed} tracking points → {len(crop_positions)} smooth positions at {fps:.1f}fps")
            
            return {
                "crop_positions": smoothed_positions,
                "frame_times": frame_times,
                "confidence_scores": confidence_scores,
                "sample_rate": fps,  # Full video FPS
                "tracking_fps": tracking_fps,  # Original tracking FPS
                "total_frames": len(crop_positions),
                "video_duration": sum(s["end"] - s["start"] for s in segments),
                "video_dimensions": (width, height),
                "tracking_available": True,
                "segment_based": True,
                "smooth_interpolation": True
            }
            
        except Exception as e:
            logger.error(f"Error in hybrid segment tracking: {e}")
            return self._create_fallback_tracking_data()
        """
        Analyze video to track objects and generate crop positions.
        
        Args:
            video_path: Path to input video file
            
        Returns:
            Dict containing tracking data and crop positions
        """
        logger.info(f"Starting object tracking analysis for {video_path}")
        
        try:
            # Open video capture
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                logger.error(f"Could not open video file: {video_path}")
                return self._create_fallback_tracking_data()
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if fps <= 0:
                logger.warning(f"Invalid FPS ({fps}), using fallback tracking data")
                cap.release()
                return self._create_fallback_tracking_data()
            
            duration = total_frames / fps
            
            logger.info(f"Video properties: {fps:.2f} fps, {total_frames} frames, {width}x{height}")
            
            # Calculate frame sampling interval for tracking (optimized fps)
            # Use lower fps for longer videos to improve performance
            if duration > 600:  # > 10 minutes
                tracking_fps = 2.0  # Very low fps for long videos
            elif duration > 300:  # > 5 minutes  
                tracking_fps = 4.0  # Low fps for medium videos
            else:
                tracking_fps = 8.0  # Higher fps for short videos
            
            logger.info(f"Adaptive tracking FPS: {tracking_fps:.1f} fps (duration: {duration:.1f}s)")
            frame_interval = max(1, int(fps / tracking_fps))
            expected_processed_frames = total_frames // frame_interval
            
            logger.info(f"Object tracking: sampling every {frame_interval} frames (~{expected_processed_frames} frames to process)")
            
            # Initialize tracking data
            crop_positions = []  # List of (x, y) crop center positions
            frame_times = []
            confidence_scores = []
            detections_count = 0
            low_confidence_count = 0
            
            frame_count = 0
            processed_count = 0
            start_time = time.time()
            
            # Create progress bar
            from tqdm import tqdm
            with tqdm(total=total_frames, desc="Object Tracking", unit="frames",
                     bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} frames [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
                
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    # Sample frames at tracking fps
                    if frame_count % frame_interval == 0:
                        # Process frame for object tracking
                        crop_center, confidence = self._process_frame(frame, width, height)
                        
                        crop_positions.append(crop_center)
                        frame_times.append(frame_count / fps)
                        confidence_scores.append(confidence)
                        if confidence >= self.confidence_threshold:
                            detections_count += 1
                        else:
                            low_confidence_count += 1
                        processed_count += 1
                        
                        # Debug visualization
                        if self.debug_tracking:
                            debug_frame = self._create_debug_frame(frame, crop_center, confidence, width, height)
                            self.debug_frames.append(debug_frame)
                        
                        # Update progress bar
                        pbar.set_postfix({
                            'objects': len([c for c in confidence_scores[-5:] if c > 0.5]),
                            'processed': processed_count
                        })
                    
                    frame_count += 1
                    pbar.update(1)
            
            cap.release()
            
            processing_time = time.time() - start_time
            logger.info(f"Object tracking completed: {processed_count} frames processed in {processing_time:.2f}s")
            
            if not crop_positions:
                logger.warning("No tracking data extracted, using fallback")
                return self._create_fallback_tracking_data()
            
            # Convert to numpy arrays
            crop_positions = np.array(crop_positions)
            frame_times = np.array(frame_times)
            confidence_scores = np.array(confidence_scores)
            
            # Smooth crop positions to avoid jittery movements
            smoothed_positions = self._smooth_crop_positions(crop_positions, confidence_scores)
            
            logger.info(f"Generated {len(crop_positions)} tracking positions")
            
            # Compute simple metrics
            avg_confidence = float(np.mean(confidence_scores)) if len(confidence_scores) else 0.0
            detection_rate = float(detections_count / processed_count) if processed_count else 0.0
            metrics = {
                "processed_frames": int(processed_count),
                "detections": int(detections_count),
                "low_confidence": int(low_confidence_count),
                "detection_rate": detection_rate,
                "avg_confidence": avg_confidence,
                "processing_time_sec": float(processing_time),
                "sample_fps": tracking_fps,
            }
            
            # Save debug video if debug tracking is enabled
            debug_video_path = None
            if self.debug_tracking and self.debug_frames:
                debug_video_path = self._save_debug_video(video_path, fps, width, height)
            
            return {
                "crop_positions": smoothed_positions,
                "frame_times": frame_times,
                "confidence_scores": confidence_scores,
                "sample_rate": tracking_fps,
                "total_frames": processed_count,
                "video_duration": duration,
                "video_dimensions": (width, height),
                "tracking_available": True,
                "debug_video_path": debug_video_path,
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"Error in object tracking: {e}")
            return self._create_fallback_tracking_data()
    
    def _process_frame(self, frame: np.ndarray, width: int, height: int) -> Tuple[Tuple[int, int], float]:
        """
        Process a single frame to detect and track objects.
        
        Args:
            frame: Input frame
            width: Frame width
            height: Frame height
            
        Returns:
            Tuple of (crop_center_x, crop_center_y) and confidence score
        """
        try:
            # Detect people in frame
            people, weights = self.hog.detectMultiScale(
                frame,
                winStride=(8, 8),
                padding=(32, 32),
                scale=1.05,
                hitThreshold=0.0,
                useMeanshiftGrouping=False
            )
            
            if len(people) > 0 and len(weights) > 0:
                # Find the person with highest confidence
                best_idx = np.argmax(weights)
                person = people[best_idx]
                confidence = weights[best_idx]
                
                if confidence > self.confidence_threshold:
                    # Calculate center of detected person
                    x, y, w, h = person
                    center_x = x + w // 2
                    center_y = y + h // 2
                    
                    # Update tracking state
                    self.last_bbox = person
                    self.tracking_lost_frames = 0
                    
                    return (center_x, center_y), float(confidence)
            
            # If no person detected or confidence too low
            self.tracking_lost_frames += 1
            
            if self.fallback_to_center:
                # Return center of frame as fallback
                center_x = width // 2
                center_y = height // 2
                return (center_x, center_y), 0.0
            
            # Return last known position if available
            if self.last_bbox is not None and self.tracking_lost_frames < self.max_lost_frames:
                x, y, w, h = self.last_bbox
                center_x = x + w // 2
                center_y = y + h // 2
                return (center_x, center_y), 0.3  # Lower confidence for predicted position
            
            # Complete fallback to center
            center_x = width // 2
            center_y = height // 2
            return (center_x, center_y), 0.0
            
        except Exception as e:
            logger.warning(f"Error processing frame: {e}")
            # Return center as fallback
            center_x = width // 2
            center_y = height // 2
            return (center_x, center_y), 0.0
    
    def _ultra_smooth_positions(self, positions: np.ndarray, confidences: np.ndarray, fps: float) -> np.ndarray:
        """
        Apply ultra-smooth smoothing for camera movement.
        
        Uses multiple smoothing techniques:
        1. Gaussian filter for noise reduction
        2. Moving average for stability
        3. Confidence-weighted smoothing
        
        Args:
            positions: Array of (x, y) crop positions
            confidences: Array of confidence scores
            fps: Video frame rate
            
        Returns:
            Ultra-smooth crop positions
        """
        if len(positions) <= 1:
            return positions
        
        smoothed = np.copy(positions)
        
        # Apply Gaussian smoothing (sigma = 0.5 seconds worth of frames)
        sigma_frames = int(0.5 * fps)  # 0.5 second smoothing window
        if sigma_frames > 0:
            from scipy import ndimage
            smoothed[:, 0] = ndimage.gaussian_filter1d(smoothed[:, 0], sigma=sigma_frames)
            smoothed[:, 1] = ndimage.gaussian_filter1d(smoothed[:, 1], sigma=sigma_frames)
        
        # Apply confidence-weighted smoothing
        for i in range(1, len(smoothed)):
            if confidences[i] > 0.7:  # High confidence - minimal smoothing
                alpha = 0.1
            elif confidences[i] > 0.4:  # Medium confidence - moderate smoothing
                alpha = 0.3
            else:  # Low confidence - heavy smoothing
                alpha = 0.6
            
            smoothed[i] = alpha * positions[i] + (1 - alpha) * smoothed[i-1]
        
        return smoothed
        """
        Smooth crop positions to avoid jittery movements.
        
        Args:
            positions: Array of (x, y) crop positions
            confidences: Array of confidence scores
            
        Returns:
            Smoothed crop positions
        """
        if len(positions) <= 1:
            return positions
        
        smoothed = np.copy(positions)
        
        # Apply weighted smoothing based on confidence
        for i in range(1, len(positions)):
            if confidences[i] > 0.5:  # High confidence detection
                # Use exponential smoothing
                alpha = 1.0 - self.tracking_smoothness
                smoothed[i] = alpha * positions[i] + (1 - alpha) * smoothed[i-1]
            else:  # Low confidence, use more smoothing
                alpha = 0.1  # Heavy smoothing for low confidence
                smoothed[i] = alpha * positions[i] + (1 - alpha) * smoothed[i-1]
        
        return smoothed
    
    def _create_debug_frame(self, frame: np.ndarray, crop_center: Tuple[int, int], confidence: float, width: int, height: int) -> np.ndarray:
        """
        Create a debug frame with tracking visualization.
        
        Args:
            frame: Original frame
            crop_center: Detected crop center position
            confidence: Detection confidence
            width: Frame width
            height: Frame height
            
        Returns:
            Frame with tracking visualization overlay
        """
        debug_frame = frame.copy()
        
        # Draw crop center point
        center_x, center_y = crop_center
        color = (0, 255, 0) if confidence > 0.5 else (0, 0, 255)  # Green if confident, red if low confidence
        
        # Draw center point
        cv2.circle(debug_frame, (center_x, center_y), 10, color, -1)
        cv2.circle(debug_frame, (center_x, center_y), 15, color, 2)
        
        # Draw crosshairs
        cv2.line(debug_frame, (center_x - 20, center_y), (center_x + 20, center_y), color, 2)
        cv2.line(debug_frame, (center_x, center_y - 20), (center_x, center_y + 20), color, 2)
        
        # Draw crop area outline (assuming vertical format)
        crop_width = int(height * 9 / 16)  # 9:16 aspect ratio
        crop_height = height
        crop_x = center_x - crop_width // 2
        crop_y = center_y - crop_height // 2
        
        # Ensure crop area is within frame bounds
        crop_x = max(0, min(crop_x, width - crop_width))
        crop_y = max(0, min(crop_y, height - crop_height))
        
        # Draw crop rectangle
        cv2.rectangle(debug_frame, (crop_x, crop_y), (crop_x + crop_width, crop_y + crop_height), color, 2)
        
        # Add confidence text
        confidence_text = f"Conf: {confidence:.2f}"
        cv2.putText(debug_frame, confidence_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        # Add position text
        position_text = f"Pos: ({center_x}, {center_y})"
        cv2.putText(debug_frame, position_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        # Add crop dimensions text
        crop_text = f"Crop: {crop_width}x{crop_height}"
        cv2.putText(debug_frame, crop_text, (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        return debug_frame
    
    def _save_debug_video(self, video_path: Path, fps: float, width: int, height: int) -> Optional[str]:
        """
        Save debug video with tracking visualization.
        
        Args:
            video_path: Original video path
            fps: Video frame rate
            width: Video width
            height: Video height
            
        Returns:
            Path to saved debug video or None if failed
        """
        try:
            # Create debug video path
            debug_video_path = video_path.parent / f"{video_path.stem}_debug_tracking.mp4"
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(debug_video_path), fourcc, fps, (width, height))
            
            if not out.isOpened():
                logger.error(f"Failed to create debug video writer for {debug_video_path}")
                return None
            
            # Write debug frames
            for debug_frame in self.debug_frames:
                out.write(debug_frame)
            
            out.release()
            
            logger.info(f"Debug tracking video saved to: {debug_video_path}")
            return str(debug_video_path)
            
        except Exception as e:
            logger.error(f"Error saving debug video: {e}")
            return None
    
    def _create_fallback_tracking_data(self) -> Dict[str, Any]:
        """
        Create fallback tracking data when video processing fails.
        
        Returns:
            Dict with default tracking data (center crop)
        """
        logger.info("Using fallback tracking data (center crop)")
        
        return {
            "crop_positions": np.array([[0, 0]]),  # Will be replaced with actual video center
            "frame_times": np.array([0.0]),
            "confidence_scores": np.array([0.0]),
            "sample_rate": 2.0,
            "total_frames": 1,
            "video_duration": 0.0,
            "video_dimensions": (1920, 1080),
            "tracking_available": False
        }
    
    def interpolate_to_export_timeline(
        self, 
        tracking_data: Dict[str, Any], 
        export_times: np.ndarray
    ) -> List[Tuple[int, int]]:
        """
        Interpolate tracking positions to match export timeline.
        
        Args:
            tracking_data: Tracking analysis results
            export_times: Export timeline (time axis)
            
        Returns:
            List of interpolated crop positions for each export time
        """
        if not tracking_data["tracking_available"]:
            # Return center positions if tracking failed
            width, height = tracking_data.get("video_dimensions", (1920, 1080))
            center_x, center_y = width // 2, height // 2
            return [(center_x, center_y)] * len(export_times)
        
        crop_positions = tracking_data["crop_positions"]
        frame_times = tracking_data["frame_times"]
        
        if len(crop_positions) <= 1:
            # Not enough tracking data, return center positions
            width, height = tracking_data.get("video_dimensions", (1920, 1080))
            center_x, center_y = width // 2, height // 2
            return [(center_x, center_y)] * len(export_times)
        
        # Interpolate x and y positions separately
        interpolated_x = np.interp(export_times, frame_times, crop_positions[:, 0])
        interpolated_y = np.interp(export_times, frame_times, crop_positions[:, 1])
        
        # Combine into list of tuples
        interpolated_positions = list(zip(interpolated_x.astype(int), interpolated_y.astype(int)))
        
        return interpolated_positions
