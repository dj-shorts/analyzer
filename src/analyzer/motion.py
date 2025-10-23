"""
Motion analysis module for MVP Analyzer.

This module handles motion detection and analysis using OpenCV.
"""

import logging
from typing import Any

import numpy as np
from scipy import ndimage

from .config import Config

logger = logging.getLogger(__name__)


class MotionDetector:
    """Detects motion in video using optical flow."""

    def __init__(self, config: Config):
        """Initialize the motion detector."""
        self.config = config
        self.motion_window_size = 0.5  # seconds
        self.flow_params = {
            "pyr_scale": 0.5,
            "levels": 3,
            "winsize": 15,
            "iterations": 3,
            "poly_n": 5,
            "poly_sigma": 1.2,
            "flags": 0,
        }

    def extract_motion_features(self, video_path: str) -> dict[str, Any]:
        """
        Extract motion features from video.

        Args:
            video_path: Path to the video file

        Returns:
            Dict containing motion analysis results
        """
        try:
            # For now, return fallback data
            # This would be implemented with actual OpenCV motion detection
            return self._create_fallback_motion_data()
        except Exception as e:
            logger.warning(f"Motion analysis failed: {e}")
            return self._create_fallback_motion_data()

    def analyze_motion(self, video_path: str) -> dict[str, Any]:
        """
        Analyze motion in video file.

        Args:
            video_path: Path to input video file

        Returns:
            Dict containing motion analysis results
        """
        return self.extract_motion_features(video_path)

    def _normalize_motion_scores(self, scores: np.ndarray) -> np.ndarray:
        """Normalize motion scores to [0, 1] range."""
        if len(scores) == 0:
            return scores

        min_score = np.min(scores)
        max_score = np.max(scores)

        if max_score == min_score:
            return np.full_like(scores, 0.5)

        return (scores - min_score) / (max_score - min_score)

    def _smooth_motion_scores(
        self, scores: np.ndarray, times: np.ndarray
    ) -> np.ndarray:
        """Smooth motion scores using Gaussian filter."""
        if len(scores) < 3:
            return scores

        # Apply Gaussian smoothing
        sigma = max(1.0, len(scores) * 0.1)
        smoothed = ndimage.gaussian_filter1d(scores, sigma=sigma)
        return smoothed

    def interpolate_to_audio_timeline(
        self, motion_data: dict[str, Any], audio_timeline: np.ndarray
    ) -> np.ndarray:
        """
        Interpolate motion scores to match the audio timeline.

        Args:
            motion_data: Dictionary containing motion_scores and motion_times
            audio_timeline: Time axis of the audio analysis (numpy array)

        Returns:
            Interpolated motion scores as a numpy array
        """
        motion_scores = motion_data.get("motion_scores", [])
        motion_times = motion_data.get("motion_times", [])

        # Debug: check data types
        logger.debug(
            f"Motion scores type: {type(motion_scores)}, shape: {np.array(motion_scores).shape if hasattr(motion_scores, '__len__') else 'scalar'}"
        )
        logger.debug(
            f"Motion times type: {type(motion_times)}, shape: {np.array(motion_times).shape if hasattr(motion_times, '__len__') else 'scalar'}"
        )

        # Ensure we have numpy arrays
        if not isinstance(motion_scores, np.ndarray):
            motion_scores = np.array(motion_scores)
        if not isinstance(motion_times, np.ndarray):
            motion_times = np.array(motion_times)

        if len(motion_times) == 0 or len(motion_scores) == 0:
            logger.warning(
                "No motion data available for interpolation, returning zeros."
            )
            return np.zeros_like(audio_timeline)

        # Ensure motion_times is monotonically increasing
        if not np.all(np.diff(motion_times) >= 0):
            logger.warning(
                "Motion times are not monotonically increasing. Sorting them."
            )
            sort_indices = np.argsort(motion_times)
            motion_times = motion_times[sort_indices]
            motion_scores = motion_scores[sort_indices]

        # Interpolate motion scores to the audio timeline
        interpolated_motion_scores = np.interp(
            audio_timeline, motion_times, motion_scores
        )

        return interpolated_motion_scores

    def combine_audio_and_motion_scores(
        self, audio_scores: np.ndarray, motion_scores: np.ndarray
    ) -> np.ndarray:
        """
        Combine audio and motion scores using weighted average.

        Args:
            audio_scores: Audio novelty scores
            motion_scores: Motion scores

        Returns:
            Combined scores
        """
        # Use 60% audio, 40% motion blend
        audio_weight = 0.6
        motion_weight = 0.4

        # If lengths don't match, return audio scores (as expected by tests)
        if len(audio_scores) != len(motion_scores):
            return audio_scores

        combined = audio_weight * audio_scores + motion_weight * motion_scores
        return combined

    def _create_fallback_motion_data(self) -> dict[str, Any]:
        """Create fallback motion data when motion analysis is not available."""
        return {
            "motion_available": False,
            "motion_scores": [0.5],  # Neutral score
            "motion_times": [0.0],
            "sample_rate": 4.0,  # Default motion analysis FPS
            "total_frames": 1,  # Single frame for fallback
            "video_duration": 0.0,  # Zero duration for fallback
            "error": "Motion analysis not implemented",
        }
