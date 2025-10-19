"""
People detection module for Epic D3.
Handles HOG people detection and pose estimation for auto-reframe.
"""

import logging
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .config import Config

logger = logging.getLogger(__name__)


class PeopleDetector:
    """Detects people in video frames for auto-reframe functionality."""

    def __init__(self, config: Config):
        """Initialize people detector with configuration."""
        self.config = config
        
        # Initialize HOG people detector
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        
        # Detection parameters
        self.hit_threshold = 0.0
        self.win_stride = (8, 8)
        self.padding = (32, 32)
        self.scale = 1.05
        self.final_threshold = 2.0
        self.use_meanshift = False

    def detect_people_in_frame(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect people in a single frame using HOG.
        
        Args:
            frame: Input video frame (BGR format)
            
        Returns:
            List of bounding boxes (x, y, width, height) for detected people
        """
        try:
            # Run people detection
            boxes, weights = self.hog.detectMultiScale(
                frame,
                hitThreshold=self.hit_threshold,
                winStride=self.win_stride,
                padding=self.padding,
                scale=self.scale,
                finalThreshold=self.final_threshold,
                useMeanshiftGrouping=self.use_meanshift
            )
            
            # Filter detections by weight (confidence)
            min_confidence = 0.3
            filtered_boxes = []
            for i, weight in enumerate(weights):
                if weight[0] >= min_confidence:
                    filtered_boxes.append(tuple(boxes[i]))
            
            logger.debug(f"Detected {len(filtered_boxes)} people with confidence >= {min_confidence}")
            return filtered_boxes
            
        except Exception as e:
            logger.warning(f"People detection failed: {e}")
            return []

    def calculate_center_x(self, boxes: List[Tuple[int, int, int, int]]) -> Optional[float]:
        """
        Calculate median center X coordinate from detected people.
        
        Args:
            boxes: List of bounding boxes (x, y, width, height)
            
        Returns:
            Median center X coordinate or None if no people detected
        """
        if not boxes:
            return None
        
        center_x_coords = []
        for x, y, width, height in boxes:
            center_x = x + width // 2
            center_x_coords.append(center_x)
        
        # Calculate median center X
        center_x_coords.sort()
        median_center_x = center_x_coords[len(center_x_coords) // 2]
        
        logger.debug(f"Calculated median center X: {median_center_x} from {len(boxes)} detections")
        return float(median_center_x)

    def detect_people_in_video_segment(self, video_path: Path, start_time: float, duration: float) -> Dict[str, Any]:
        """
        Detect people in a video segment and calculate center position.
        
        Args:
            video_path: Path to video file
            start_time: Start time in seconds
            duration: Duration in seconds
            
        Returns:
            Dictionary with detection results
        """
        try:
            # Open video capture
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return {
                    "success": False,
                    "error": "Could not open video file",
                    "center_x": None,
                    "people_count": 0
                }
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calculate frame range
            start_frame = int(start_time * fps)
            end_frame = int((start_time + duration) * fps)
            end_frame = min(end_frame, total_frames - 1)
            
            # Sample frames for detection (every 30 frames to avoid processing all)
            sample_interval = 30
            frame_centers = []
            people_counts = []
            
            for frame_num in range(start_frame, end_frame + 1, sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if not ret:
                    continue
                
                # Detect people in this frame
                boxes = self.detect_people_in_frame(frame)
                people_counts.append(len(boxes))
                
                if boxes:
                    center_x = self.calculate_center_x(boxes)
                    if center_x is not None:
                        frame_centers.append(center_x)
            
            cap.release()
            
            # Calculate overall results
            if frame_centers:
                # Use median center X across all frames
                frame_centers.sort()
                overall_center_x = frame_centers[len(frame_centers) // 2]
                avg_people_count = sum(people_counts) / len(people_counts) if people_counts else 0
                
                return {
                    "success": True,
                    "center_x": overall_center_x,
                    "people_count": avg_people_count,
                    "frames_processed": len(frame_centers),
                    "total_frames_sampled": len(people_counts)
                }
            else:
                return {
                    "success": True,
                    "center_x": None,
                    "people_count": 0,
                    "frames_processed": 0,
                    "total_frames_sampled": len(people_counts)
                }
                
        except Exception as e:
            logger.error(f"People detection in video segment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "center_x": None,
                "people_count": 0
            }

    def calculate_crop_window(self, center_x: float, frame_width: int, frame_height: int, 
                            target_width: int, target_height: int) -> Tuple[int, int, int, int]:
        """
        Calculate crop window centered around detected people.
        
        Args:
            center_x: Center X coordinate from people detection
            frame_width: Original frame width
            frame_height: Original frame height
            target_width: Target crop width
            target_height: Target crop height
            
        Returns:
            Tuple of (crop_x, crop_y, crop_width, crop_height)
        """
        # Calculate crop dimensions based on target aspect ratio
        target_aspect = target_width / target_height
        
        # Determine crop dimensions that maintain aspect ratio
        if frame_height * target_aspect <= frame_width:
            # Crop height, use full height
            crop_height = frame_height
            crop_width = int(frame_height * target_aspect)
        else:
            # Crop width, use full width
            crop_width = frame_width
            crop_height = int(frame_width / target_aspect)
        
        # Center crop around detected people center
        crop_x = max(0, min(center_x - crop_width // 2, frame_width - crop_width))
        crop_y = (frame_height - crop_height) // 2
        
        logger.debug(f"Crop window: ({crop_x}, {crop_y}, {crop_width}, {crop_height}) "
                    f"centered around X={center_x}")
        
        return crop_x, crop_y, crop_width, crop_height
