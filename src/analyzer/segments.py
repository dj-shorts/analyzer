"""
Segment building module for MVP Analyzer.
"""

import logging
from typing import Any

from .config import Config

logger = logging.getLogger(__name__)


class SegmentBuilder:
    """Builds video segments from detected peaks."""

    def __init__(self, config: Config):
        """Initialize segment builder with configuration."""
        self.config = config

    def build_segments(self, peaks_data: dict[str, Any]) -> dict[str, Any]:
        """
        Build segments from peak information.

        Args:
            peaks_data: Dict containing peak times, scores, and metadata

        Returns:
            Dict containing segment information
        """
        logger.info("Building segments from peaks")

        peak_times = peaks_data["peak_times"]
        peak_scores = peaks_data["peak_scores"]
        seed_based = peaks_data["seed_based"]

        if len(peak_times) == 0:
            logger.warning("No peaks found, returning empty segments")
            return {"segments": [], "total_segments": 0}

        segments = []

        for clip_id, (center_time, score, is_seed) in enumerate(
            zip(peak_times, peak_scores, seed_based, strict=True), 1
        ):
            # Calculate segment start time (with pre-roll)
            start_time = max(0, center_time - self.config.pre_roll)

            # Calculate segment length
            segment_length = self._calculate_segment_length(score)

            # Calculate end time
            end_time = start_time + segment_length

            segment = {
                "clip_id": clip_id,
                "start": start_time,
                "end": end_time,
                "center": center_time,
                "score": float(score),
                "seed_based": bool(is_seed),
                "aligned": False,  # Will be set to True in beat alignment step
                "length": segment_length,
            }

            segments.append(segment)

        logger.info(f"Built {len(segments)} segments")

        return {"segments": segments, "total_segments": len(segments)}

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
        length = max(
            self.config.min_clip_length, min(self.config.max_clip_length, length)
        )

        return length
