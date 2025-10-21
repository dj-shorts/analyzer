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
        
        # Initialize HOG descriptor for people detection
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        
        # Detection parameters
        self.hit_threshold = 0.0
        self.win_stride = (8, 8)
        self.padding = (32, 32)
        self.scale = 1.05

    def detect_people_in_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect people in a single frame using HOG.
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            Dict containing detection results
        """
        try:
            # Run people detection
            (rects, weights) = self.hog.detectMultiScale(
                frame,
                hitThreshold=self.hit_threshold,
                winStride=self.win_stride,
                padding=self.padding,
                scale=self.scale
            )
            
            if len(rects) > 0:
                # Calculate center X coordinate of all detected people
                center_x = self.calculate_center_x(rects)
                
                return {
                    "success": True,
                    "people_count": len(rects),
                    "center_x": center_x,
                    "rects": rects.tolist(),
                    "weights": weights.tolist()
                }
            else:
                return {
                    "success": True,
                    "people_count": 0,
                    "center_x": None,
                    "rects": [],
                    "weights": []
                }
                
        except Exception as e:
            logger.error(f"Error detecting people in frame: {e}")
            return {
                "success": False,
                "error": str(e),
                "people_count": 0,
                "center_x": None
            }

    def calculate_center_x(self, rects: np.ndarray) -> float:
        """
        Calculate the median X-center of detected people rectangles.
        
        Args:
            rects: Array of rectangles (x, y, width, height)
            
        Returns:
            Median X-center coordinate
        """
        if len(rects) == 0:
            return None
        
        # Calculate center X for each rectangle
        center_xs = []
        for rect in rects:
            x, y, width, height = rect
            center_x = x + width / 2
            center_xs.append(center_x)
        
        # Return median center X
        return float(np.median(center_xs))

    def detect_people_in_video_segment(self, video_path: Path, start_time: float, duration: float) -> Dict[str, Any]:
        """
        Detect people in a video segment by sampling frames.
        
        Args:
            video_path: Path to video file
            start_time: Start time in seconds
            duration: Duration in seconds
            
        Returns:
            Dict containing detection results for the segment
        """
        logger.info(f"Detecting people in video segment: {start_time:.2f}s - {start_time + duration:.2f}s")
        
        try:
            # Open video capture
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                logger.error(f"Could not open video file: {video_path}")
                return {"success": False, "error": "Could not open video file"}
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calculate frame range for the segment
            start_frame = int(start_time * fps)
            end_frame = int((start_time + duration) * fps)
            
            # Sample frames (every 30 frames = ~1 second at 30fps)
            sample_interval = max(1, int(fps))
            
            all_center_xs = []
            total_people = 0
            
            # Seek to start frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            frame_count = start_frame
            while frame_count <= end_frame:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Sample frames
                if (frame_count - start_frame) % sample_interval == 0:
                    # Detect people in this frame
                    detection_result = self.detect_people_in_frame(frame)
                    
                    if detection_result["success"] and detection_result["center_x"] is not None:
                        all_center_xs.append(detection_result["center_x"])
                        total_people += detection_result["people_count"]
                
                frame_count += 1
            
            cap.release()
            
            # Calculate final results
            if all_center_xs:
                # Use median center X across all frames
                median_center_x = float(np.median(all_center_xs))
                avg_people_count = total_people / len(all_center_xs)
                
                return {
                    "success": True,
                    "center_x": median_center_x,
                    "people_count": avg_people_count,
                    "frames_processed": len(all_center_xs),
                    "total_detections": total_people
                }
            else:
                return {
                    "success": True,
                    "center_x": None,
                    "people_count": 0,
                    "frames_processed": 0,
                    "total_detections": 0
                }
                
        except Exception as e:
            logger.error(f"Error detecting people in video segment: {e}")
            return {
                "success": False,
                "error": str(e),
                "center_x": None,
                "people_count": 0
            }

    def calculate_crop_window(self, center_x: float, input_width: int, input_height: int, 
                            target_width: int, target_height: int) -> Tuple[int, int, int, int]:
        """
        Calculate crop window parameters for auto-reframe.
        
        Args:
            center_x: X-center of detected people
            input_width: Input video width
            input_height: Input video height
            target_width: Target crop width
            target_height: Target crop height
            
        Returns:
            Tuple of (crop_x, crop_y, crop_width, crop_height)
        """
        # Calculate aspect ratios
        input_aspect = input_width / input_height
        target_aspect = target_width / target_height
        
        if target_aspect > input_aspect:
            # Target is wider - crop height (use full height, calculate width)
            crop_height = input_height
            crop_width = int(input_height * target_aspect)
            
            # Clamp crop dimensions to input dimensions
            crop_width = min(crop_width, input_width)
            
            # Center crop horizontally around detected people
            crop_x = max(0, min(input_width - crop_width, int(center_x - crop_width / 2)))
            crop_y = 0
        else:
            # Target is taller - crop width (use full width, calculate height)
            crop_width = input_width
            crop_height = int(input_width / target_aspect)
            
            # Clamp crop dimensions to input dimensions
            crop_height = min(crop_height, input_height)
            
            # Center crop vertically
            crop_x = 0
            crop_y = max(0, min(input_height - crop_height, int(input_height / 2 - crop_height / 2)))
        
        return crop_x, crop_y, crop_width, crop_height
