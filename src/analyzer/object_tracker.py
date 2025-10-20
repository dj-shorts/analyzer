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
        
        logger.info(f"ObjectTracker initialized with smoothness={self.tracking_smoothness}, "
                   f"confidence={self.confidence_threshold}")
    
    def analyze_video_tracking(self, video_path: Path) -> Dict[str, Any]:
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
            
            # Calculate frame sampling interval for tracking (every 0.5 seconds)
            tracking_fps = 2.0  # Track at 2 fps for performance
            frame_interval = max(1, int(fps / tracking_fps))
            expected_processed_frames = total_frames // frame_interval
            
            logger.info(f"Object tracking: sampling every {frame_interval} frames (~{expected_processed_frames} frames to process)")
            
            # Initialize tracking data
            crop_positions = []  # List of (x, y) crop center positions
            frame_times = []
            confidence_scores = []
            
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
                        processed_count += 1
                        
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
            
            return {
                "crop_positions": smoothed_positions,
                "frame_times": frame_times,
                "confidence_scores": confidence_scores,
                "sample_rate": tracking_fps,
                "total_frames": processed_count,
                "video_duration": duration,
                "video_dimensions": (width, height),
                "tracking_available": True
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
                finalThreshold=2.0,
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
    
    def _smooth_crop_positions(self, positions: np.ndarray, confidences: np.ndarray) -> np.ndarray:
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
