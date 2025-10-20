"""
Motion analysis module for MVP Analyzer.

Implements Epic C: Optical flow Farnebäck (3-4 fps) and mixing with audio score.
"""

import logging
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
import time

import numpy as np
import cv2
from tqdm import tqdm

from .config import Config

logger = logging.getLogger(__name__)


class MotionDetector:
    """Detects motion in video using optical flow Farnebäck."""
    
    def __init__(self, config: Config):
        """Initialize motion detector with configuration."""
        self.config = config
        
        # Optical flow parameters
        self.flow_params = {
            'pyr_scale': 0.5,
            'levels': 3,
            'winsize': 15,
            'iterations': 3,
            'poly_n': 5,
            'poly_sigma': 1.2,
            'flags': 0
        }
        
        # Motion analysis parameters - adaptive based on video duration
        self.base_target_fps = 4.0  # Base 4 fps for motion analysis
        self.motion_window_size = 0.5  # 0.5 second smoothing window
        
        # Adaptive sampling for long videos
        self.long_video_threshold = 1800  # 30 minutes
        self.very_long_video_threshold = 3600  # 1 hour
        self.min_target_fps = 1.0  # Minimum 1 fps for very long videos
        self.max_target_fps = 6.0  # Maximum 6 fps for short videos
    
    def _calculate_adaptive_fps(self, duration: float) -> float:
        """
        Calculate adaptive target FPS based on video duration.
        
        For long videos, reduce FPS to speed up processing while maintaining quality.
        
        Args:
            duration: Video duration in seconds
            
        Returns:
            Target FPS for motion analysis
        """
        if duration <= self.long_video_threshold:
            # Short videos (< 30 min): use base FPS
            return self.base_target_fps
        elif duration <= self.very_long_video_threshold:
            # Long videos (30 min - 1 hour): reduce to 2 fps
            return 2.0
        else:
            # Very long videos (> 1 hour): reduce to 1 fps
            return 1.0
    
    def analyze_motion(self, video_path: Path) -> Dict[str, Any]:
        """
        Analyze motion in video file.
        
        Args:
            video_path: Path to input video file
            
        Returns:
            Dict containing motion analysis results
        """
        return self.extract_motion_features(video_path)
    
    def extract_motion_features(self, video_path: Path) -> Dict[str, Any]:
        """
        Extract motion features from video using optical flow.
        
        Args:
            video_path: Path to input video file
            
        Returns:
            Dict containing motion scores and metadata
        """
        logger.info(f"Extracting motion features from {video_path}")
        
        try:
            # Open video capture
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                logger.error(f"Could not open video file: {video_path}")
                return self._create_fallback_motion_data()
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Check for zero FPS (common in some containers)
            if fps <= 0:
                logger.warning(f"Invalid FPS ({fps}), using fallback motion data")
                cap.release()
                return self._create_fallback_motion_data()
            
            duration = total_frames / fps
            
            # Calculate adaptive target FPS based on video duration
            target_fps = self._calculate_adaptive_fps(duration)
            
            logger.info(f"Video properties: {fps:.2f} fps, {total_frames} frames, {duration:.2f}s")
            logger.info(f"Adaptive motion analysis: using {target_fps:.1f} fps (duration-based optimization)")
            
            # Calculate frame sampling interval for adaptive target fps
            frame_interval = max(1, int(fps / target_fps))
            expected_processed_frames = total_frames // frame_interval
            
            logger.info(f"Processing motion analysis: sampling every {frame_interval} frames (~{expected_processed_frames} frames to process)")
            
            # Initialize optical flow variables
            prev_frame = None
            motion_scores = []
            frame_times = []
            
            frame_count = 0
            processed_count = 0
            start_time = time.time()
            
            # Create progress bar
            with tqdm(total=total_frames, desc="Motion Analysis", unit="frames", 
                     bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} frames [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
                
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    # Sample frames at target fps
                    if frame_count % frame_interval == 0:
                        # Convert to grayscale
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        
                        if prev_frame is not None:
                            # Use Farnebäck method for dense optical flow
                            flow_dense = cv2.calcOpticalFlowFarneback(
                                prev_frame, gray, None,
                                **self.flow_params
                            )
                            
                            # Calculate motion magnitude
                            motion_magnitude = np.sqrt(
                                flow_dense[..., 0]**2 + flow_dense[..., 1]**2
                            )
                            
                            # Calculate median motion score
                            motion_score = np.median(motion_magnitude)
                            
                            motion_scores.append(motion_score)
                            frame_times.append(frame_count / fps)
                            processed_count += 1
                            
                            # Update progress bar with motion score info
                            pbar.set_postfix({
                                'motion': f'{motion_score:.3f}',
                                'processed': processed_count
                            })
                        
                        prev_frame = gray
                    
                    frame_count += 1
                    pbar.update(1)
            
            cap.release()
            
            processing_time = time.time() - start_time
            logger.info(f"Motion analysis completed: {processed_count} frames processed in {processing_time:.2f}s")
            
            if not motion_scores:
                logger.warning("No motion features extracted, using fallback")
                return self._create_fallback_motion_data()
            
            # Convert to numpy arrays
            motion_scores = np.array(motion_scores)
            frame_times = np.array(frame_times)
            
            # Normalize motion scores to [0, 1]
            motion_scores_norm = self._normalize_motion_scores(motion_scores)
            
            # Smooth motion scores
            motion_scores_smooth = self._smooth_motion_scores(motion_scores_norm, frame_times)
            
            logger.info(f"Extracted {len(motion_scores)} motion features")
            
            return {
                "motion_scores": motion_scores_smooth,
                "motion_times": frame_times,
                "sample_rate": target_fps,
                "total_frames": processed_count,
                "video_duration": duration,
                "motion_available": True,
                "adaptive_fps": True
            }
            
        except Exception as e:
            logger.error(f"Error extracting motion features: {e}")
            return self._create_fallback_motion_data()
    
    def _normalize_motion_scores(self, motion_scores: np.ndarray) -> np.ndarray:
        """
        Normalize motion scores to [0, 1] range using robust normalization.
        
        Args:
            motion_scores: Raw motion scores
            
        Returns:
            Normalized motion scores
        """
        if len(motion_scores) == 0:
            return motion_scores
        
        # Use percentile-based normalization for robustness
        p5 = np.percentile(motion_scores, 5)
        p95 = np.percentile(motion_scores, 95)
        
        if p95 > p5:
            # Normalize to [0, 1] using percentiles
            normalized = (motion_scores - p5) / (p95 - p5)
            # Clamp to [0, 1]
            normalized = np.clip(normalized, 0, 1)
        else:
            # Fallback: use min-max normalization
            min_val = np.min(motion_scores)
            max_val = np.max(motion_scores)
            if max_val > min_val:
                normalized = (motion_scores - min_val) / (max_val - min_val)
            else:
                normalized = np.zeros_like(motion_scores)
        
        return normalized
    
    def _smooth_motion_scores(self, motion_scores: np.ndarray, times: np.ndarray) -> np.ndarray:
        """
        Smooth motion scores using a moving average window.
        
        Args:
            motion_scores: Normalized motion scores
            times: Time axis for motion scores
            
        Returns:
            Smoothed motion scores
        """
        if len(motion_scores) <= 1:
            return motion_scores
        
        # Calculate window size in samples
        window_duration = self.motion_window_size  # 0.5 seconds
        window_samples = max(1, int(window_duration * self.base_target_fps))
        
        # Apply moving average smoothing
        smoothed = np.convolve(
            motion_scores, 
            np.ones(window_samples) / window_samples, 
            mode='same'
        )
        
        return smoothed
    
    def _create_fallback_motion_data(self) -> Dict[str, Any]:
        """
        Create fallback motion data when video processing fails.
        
        Returns:
            Dict with default motion data
        """
        logger.info("Using fallback motion data (no motion analysis)")
        
        return {
            "motion_scores": np.array([0.5]),  # Neutral motion score
            "motion_times": np.array([0.0]),
            "sample_rate": self.base_target_fps,
            "total_frames": 1,
            "video_duration": 0.0,
            "motion_available": False,
            "adaptive_fps": False
        }
    
    def interpolate_to_audio_timeline(
        self, 
        motion_data: Dict[str, Any], 
        audio_times: np.ndarray
    ) -> np.ndarray:
        """
        Interpolate motion scores to match audio timeline.
        
        Args:
            motion_data: Motion analysis results
            audio_times: Audio timeline (time axis)
            
        Returns:
            Motion scores interpolated to audio timeline
        """
        if not motion_data["motion_available"]:
            # Return neutral motion scores if motion analysis failed
            return np.full(len(audio_times), 0.5)
        
        motion_scores = motion_data["motion_scores"]
        motion_times = motion_data["motion_times"]
        
        # Debug: check data types
        logger.debug(f"Motion scores type: {type(motion_scores)}, shape: {np.array(motion_scores).shape if hasattr(motion_scores, '__len__') else 'scalar'}")
        logger.debug(f"Motion times type: {type(motion_times)}, shape: {np.array(motion_times).shape if hasattr(motion_times, '__len__') else 'scalar'}")
        
        # Ensure we have numpy arrays
        if not isinstance(motion_scores, np.ndarray):
            motion_scores = np.array(motion_scores)
        if not isinstance(motion_times, np.ndarray):
            motion_times = np.array(motion_times)
        
        if len(motion_scores) <= 1:
            # Not enough motion data, return neutral scores
            return np.full(len(audio_times), 0.5)
        
        # Interpolate motion scores to audio timeline
        interpolated = np.interp(audio_times, motion_times, motion_scores)
        
        return interpolated
    
    def combine_audio_and_motion_scores(
        self, 
        audio_scores: np.ndarray, 
        motion_scores: np.ndarray
    ) -> np.ndarray:
        """
        Combine audio and motion scores using weighted average.
        
        Args:
            audio_scores: Audio novelty scores
            motion_scores: Motion scores (interpolated to audio timeline)
            
        Returns:
            Combined scores: 0.6*audio + 0.4*motion
        """
        # Check if arrays have different lengths
        if len(audio_scores) != len(motion_scores):
            logger.warning(f"Audio and motion scores have different lengths ({len(audio_scores)} vs {len(motion_scores)}). Using audio scores only.")
            return audio_scores
        
        # Weighted combination: 60% audio, 40% motion
        audio_weight = 0.6
        motion_weight = 0.4
        
        combined_scores = audio_weight * audio_scores + motion_weight * motion_scores
        
        # Ensure scores are in [0, 1] range
        combined_scores = np.clip(combined_scores, 0, 1)
        
        return combined_scores
