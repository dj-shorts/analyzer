"""
Segment building module for MVP Analyzer.
"""

import logging
from typing import Dict, Any, List

import numpy as np

from .config import Config

logger = logging.getLogger(__name__)


class SegmentBuilder:
    """Builds video segments from detected peaks."""
    
    def __init__(self, config: Config):
        """Initialize segment builder with configuration."""
        self.config = config
    
    def build_segments(self, peaks_data: Dict[str, Any], audio_duration: float = None) -> Dict[str, Any]:
        """
        Build segments from peak information.
        
        Args:
            peaks_data: Dict containing peak times, scores, and metadata
            audio_duration: Total duration of the audio in seconds (optional)
            
        Returns:
            Dict containing segment information
        """
        logger.info("Building segments from peaks")
        
        peak_times = peaks_data["peak_times"]
        peak_scores = peaks_data["peak_scores"]
        seed_based = peaks_data["seed_based"]
        
        if len(peak_times) == 0:
            logger.warning("No peaks found, returning empty segments")
            return {
                "segments": [],
                "total_segments": 0
            }
        
        segments = []
        
        for i, (center_time, score, is_seed) in enumerate(zip(peak_times, peak_scores, seed_based)):
            # Calculate segment start time (with pre-roll)
            start_time = max(0, center_time - self.config.pre_roll)
            
            # Calculate segment length
            segment_length = self._calculate_segment_length(score)
            
            # Calculate end time
            end_time = start_time + segment_length
            
            # Ensure segment doesn't exceed audio duration
            if audio_duration is not None:
                end_time = min(end_time, audio_duration)
                # Recalculate start time if needed to maintain segment length
                if end_time - start_time < self.config.min_clip_length:
                    # If segment is too short, adjust start time
                    start_time = max(0, end_time - self.config.min_clip_length)
            
            # Recalculate actual segment length after adjustments
            actual_length = end_time - start_time
            
            segment = {
                "clip_id": i + 1,
                "start": round(start_time, 3),
                "end": round(end_time, 3),
                "center": round(center_time, 3),
                "score": round(float(score), 3),
                "seed_based": bool(is_seed),
                "aligned": False,  # Will be set to True in beat alignment step
                "length": round(actual_length, 3)
            }
            
            segments.append(segment)
        
        logger.info(f"Built {len(segments)} segments")
        
        return {
            "segments": segments,
            "total_segments": len(segments)
        }
    
    def _calculate_segment_length(self, score: float) -> float:
        """
        Calculate segment length based on novelty score.
        
        Higher scores get longer segments, within the min/max bounds.
        
        Args:
            score: Novelty score (0-1)
            
        Returns:
            Segment length in seconds
        """
        # Simple linear interpolation from min to max based on score
        length = self.config.min_clip_length + score * (
            self.config.max_clip_length - self.config.min_clip_length
        )
        
        # Ensure within bounds
        length = max(self.config.min_clip_length, min(self.config.max_clip_length, length))
        
        return length
