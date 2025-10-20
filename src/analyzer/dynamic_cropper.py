"""
Dynamic cropping module for MVP Analyzer.

Implements adaptive cropping that follows tracked objects for vertical video export.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
import math

import numpy as np

from .config import Config

logger = logging.getLogger(__name__)


class DynamicCropper:
    """Handles dynamic cropping for video export with object tracking."""
    
    def __init__(self, config: Config):
        """Initialize dynamic cropper with configuration."""
        self.config = config
        
        # Cropping parameters
        self.tracking_smoothness = getattr(config, 'tracking_smoothness', 0.8)
        self.fallback_to_center = getattr(config, 'fallback_to_center', True)
        
        logger.info(f"DynamicCropper initialized with smoothness={self.tracking_smoothness}")
    
    def generate_crop_filter(
        self, 
        tracking_positions: List[Tuple[int, int]], 
        video_width: int, 
        video_height: int,
        crop_width: int,
        crop_height: int,
        start_time: float,
        duration: float
    ) -> str:
        """
        Generate FFmpeg crop filter with dynamic positioning.
        
        Args:
            tracking_positions: List of (x, y) crop center positions over time
            video_width: Input video width
            video_height: Input video height
            crop_width: Desired crop width
            crop_height: Desired crop height
            start_time: Start time of the clip
            duration: Duration of the clip
            
        Returns:
            FFmpeg filter string for dynamic cropping
        """
        if not tracking_positions:
            # Fallback to center crop
            center_x = (video_width - crop_width) // 2
            center_y = (video_height - crop_height) // 2
            return f"crop={crop_width}:{crop_height}:{center_x}:{center_y}"
        
        if len(tracking_positions) == 1:
            # Single position, use static crop
            center_x, center_y = tracking_positions[0]
            crop_x = max(0, min(center_x - crop_width // 2, video_width - crop_width))
            crop_y = max(0, min(center_y - crop_height // 2, video_height - crop_height))
            return f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y}"
        
        # Generate dynamic crop filter with time-based positioning
        return self._generate_dynamic_filter(
            tracking_positions, video_width, video_height, 
            crop_width, crop_height, start_time, duration
        )
    
    def _generate_dynamic_filter(
        self,
        tracking_positions: List[Tuple[int, int]],
        video_width: int,
        video_height: int,
        crop_width: int,
        crop_height: int,
        start_time: float,
        duration: float
    ) -> str:
        """
        Generate FFmpeg filter with time-based dynamic positioning.
        
        Args:
            tracking_positions: List of (x, y) positions
            video_width: Input video width
            video_height: Input video height
            crop_width: Desired crop width
            crop_height: Desired crop height
            start_time: Start time of the clip
            duration: Duration of the clip
            
        Returns:
            FFmpeg filter string with dynamic positioning
        """
        # Calculate time intervals for each position
        # Use higher resolution for 24fps tracking
        time_interval = duration / (len(tracking_positions) - 1) if len(tracking_positions) > 1 else 0
        
        # Generate crop positions with bounds checking
        crop_x_positions = []
        crop_y_positions = []
        
        for center_x, center_y in tracking_positions:
            # Calculate crop position (top-left corner)
            crop_x = max(0, min(center_x - crop_width // 2, video_width - crop_width))
            crop_y = max(0, min(center_y - crop_height // 2, video_height - crop_height))
            
            crop_x_positions.append(crop_x)
            crop_y_positions.append(crop_y)
        
        # Generate FFmpeg expression for x position
        x_expr = self._generate_position_expression(crop_x_positions, time_interval, start_time)
        
        # Generate FFmpeg expression for y position  
        y_expr = self._generate_position_expression(crop_y_positions, time_interval, start_time)
        
        # Create dynamic crop filter
        filter_str = f"crop={crop_width}:{crop_height}:{x_expr}:{y_expr}"
        
        logger.debug(f"Generated dynamic crop filter: {filter_str}")
        
        return filter_str
    
    def _generate_position_expression(
        self, 
        positions: List[int], 
        time_interval: float, 
        start_time: float
    ) -> str:
        """
        Generate FFmpeg expression for position interpolation.
        
        Args:
            positions: List of position values
            time_interval: Time interval between positions
            start_time: Start time offset
            
        Returns:
            FFmpeg expression string
        """
        if len(positions) == 1:
            return str(positions[0])
        
        # For 24fps tracking, use more sophisticated interpolation
        avg_position = int(sum(positions) / len(positions))
        
        # Check for movement patterns
        position_variance = max(positions) - min(positions)
        
        if position_variance > 20:  # Significant movement detected
            # Use linear interpolation for smooth movement
            if len(positions) >= 2:
                start_pos = positions[0]
                end_pos = positions[-1]
                total_duration = time_interval * (len(positions) - 1)
                
                # Create smooth linear interpolation
                expr = f"({start_pos}+({end_pos}-{start_pos})*t/{total_duration:.3f})"
                logger.debug(f"Using linear interpolation: {start_pos} -> {end_pos} over {total_duration:.3f}s")
                return expr
        
        elif position_variance > 5:  # Small movement
            # Use average with slight smoothing
            return str(avg_position)
        
        else:  # Very stable tracking
            # Use exact center position
            return str(avg_position)
    
    def calculate_crop_dimensions(
        self, 
        video_width: int, 
        video_height: int, 
        target_format: str
    ) -> Tuple[int, int]:
        """
        Calculate crop dimensions for target format.
        
        Args:
            video_width: Input video width
            video_height: Input video height
            target_format: Target format ('vertical', 'square', 'original')
            
        Returns:
            Tuple of (crop_width, crop_height)
        """
        if target_format == "original":
            return video_width, video_height
        
        elif target_format == "vertical":
            # 9:16 aspect ratio
            target_ratio = 9.0 / 16.0
            if video_height * target_ratio <= video_width:
                # Crop width
                crop_width = int(video_height * target_ratio)
                crop_height = video_height
            else:
                # Crop height
                crop_width = video_width
                crop_height = int(video_width / target_ratio)
        
        elif target_format == "square":
            # 1:1 aspect ratio
            min_dimension = min(video_width, video_height)
            crop_width = min_dimension
            crop_height = min_dimension
        
        else:
            # Default to original
            crop_width, crop_height = video_width, video_height
        
        # Ensure dimensions are even (required by some codecs)
        crop_width = (crop_width // 2) * 2
        crop_height = (crop_height // 2) * 2
        
        logger.debug(f"Calculated crop dimensions for {target_format}: {crop_width}x{crop_height}")
        
        return crop_width, crop_height
    
    def validate_crop_positions(
        self, 
        positions: List[Tuple[int, int]], 
        video_width: int, 
        video_height: int,
        crop_width: int,
        crop_height: int
    ) -> List[Tuple[int, int]]:
        """
        Validate and clamp crop positions to video bounds.
        
        Args:
            positions: List of (x, y) crop center positions
            video_width: Input video width
            video_height: Input video height
            crop_width: Crop width
            crop_height: Crop height
            
        Returns:
            Validated crop positions
        """
        validated_positions = []
        
        for center_x, center_y in positions:
            # Calculate crop bounds
            max_x = video_width - crop_width
            max_y = video_height - crop_height
            
            # Clamp center position to valid crop area
            clamped_x = max(crop_width // 2, min(center_x, video_width - crop_width // 2))
            clamped_y = max(crop_height // 2, min(center_y, video_height - crop_height // 2))
            
            validated_positions.append((clamped_x, clamped_y))
        
        return validated_positions
