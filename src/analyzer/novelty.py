"""
Novelty detection module for MVP Analyzer.
"""

import logging
from typing import Tuple, Dict, Any

import numpy as np

from .config import Config

logger = logging.getLogger(__name__)


class NoveltyDetector:
    """Detects novel moments in audio using onset strength and spectral contrast."""
    
    def __init__(self, config: Config):
        """Initialize novelty detector with configuration."""
        self.config = config
        self.hop_length = 512
        self.window_size = 2048
    
    def compute_novelty(self, audio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute novelty scores from audio data.
        
        Args:
            audio_data: Dict containing audio samples, sample_rate, etc.
            
        Returns:
            Dict containing novelty scores and metadata
        """
        logger.info("Computing novelty scores")
        
        audio = audio_data["audio"]
        sr = audio_data["sample_rate"]
        
        # TODO: Implement proper onset strength and spectral contrast in Issue A3
        # For now, create a simple novelty measure based on audio energy changes
        
        # Simple energy-based novelty (temporary implementation)
        hop_samples = self.hop_length
        frames = []
        
        for i in range(0, len(audio) - hop_samples, hop_samples):
            frame = audio[i:i + hop_samples]
            energy = np.mean(frame ** 2)
            frames.append(energy)
        
        energy_frames = np.array(frames)
        
        # Compute energy differences as novelty measure
        energy_diff = np.abs(np.diff(energy_frames, prepend=energy_frames[0]))
        
        # Normalize and smooth
        onset_norm = self._robust_normalize(energy_diff)
        contrast_norm = self._robust_normalize(energy_frames)
        
        # Combine features
        novelty_scores = 0.7 * onset_norm + 0.3 * contrast_norm
        
        # Smooth the novelty curve with simple moving average
        smoothing_frames = int(0.5 * sr / self.hop_length)
        if smoothing_frames > 1:
            novelty_scores = self._smooth_signal(novelty_scores, smoothing_frames)
        
        # Create time axis
        time_axis = np.arange(len(novelty_scores)) * self.hop_length / sr
        
        logger.info(f"Computed novelty scores: {len(novelty_scores)} frames")
        
        return {
            "novelty_scores": novelty_scores,
            "time_axis": time_axis,
            "onset_strength": onset_norm,
            "contrast_variance": contrast_norm,
            "sample_rate": sr,
            "hop_length": self.hop_length,
            "duration": time_axis[-1] if len(time_axis) > 0 else 0
        }
    
    def _robust_normalize(self, data: np.ndarray) -> np.ndarray:
        """
        Robust normalization using percentile-based scaling.
        
        Args:
            data: Input data array
            
        Returns:
            Normalized data in [0, 1] range
        """
        # Handle empty array
        if len(data) == 0:
            return data
        
        # Use 5th and 95th percentiles for robust normalization
        p5, p95 = np.percentile(data, [5, 95])
        
        if p95 - p5 == 0:
            # Handle edge case where all values are the same
            return np.zeros_like(data)
        
        # Normalize to [0, 1]
        normalized = (data - p5) / (p95 - p5)
        
        # Clip to ensure [0, 1] range
        normalized = np.clip(normalized, 0, 1)
        
        return normalized
    
    def _smooth_signal(self, signal: np.ndarray, window_size: int) -> np.ndarray:
        """
        Smooth signal using simple moving average.
        
        Args:
            signal: Input signal
            window_size: Window size for smoothing
            
        Returns:
            Smoothed signal
        """
        if window_size <= 1:
            return signal
        
        # Simple moving average
        kernel = np.ones(window_size) / window_size
        smoothed = np.convolve(signal, kernel, mode='same')
        
        return smoothed
