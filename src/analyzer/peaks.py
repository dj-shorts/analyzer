"""
Peak detection and selection module for MVP Analyzer.
"""

import logging
from typing import List, Tuple, Dict, Any

import numpy as np
from scipy.signal import find_peaks

from .config import Config

logger = logging.getLogger(__name__)


class PeakPicker:
    """Finds and selects peaks from novelty scores."""
    
    def __init__(self, config: Config):
        """Initialize peak picker with configuration."""
        self.config = config
    
    def find_peaks(self, novelty_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find peaks in novelty scores with spacing constraint.
        
        Args:
            novelty_data: Dict containing novelty scores and time axis
            
        Returns:
            Dict containing peak information
        """
        logger.info("Finding peaks in novelty scores")
        
        novelty_scores = novelty_data["novelty_scores"]
        time_axis = novelty_data["time_axis"]
        
        # Convert spacing from frames to samples (approximate)
        # Assuming hop_length = 512 and sr = 22050
        sr = novelty_data.get("sample_rate", 22050)
        hop_length = novelty_data.get("hop_length", 512)
        
        # Convert spacing from frames to samples
        spacing_frames = int(self.config.peak_spacing * hop_length / sr)
        
        # Find peaks using scipy
        peaks, properties = find_peaks(
            novelty_scores,
            distance=spacing_frames,
            prominence=0.1  # Minimum prominence for peak detection
        )
        
        # Get top-K peaks by score
        if len(peaks) > 0:
            peak_scores = novelty_scores[peaks]
            top_k_indices = np.argsort(peak_scores)[-self.config.clips_count:]
            top_peaks = peaks[top_k_indices]
            top_scores = peak_scores[top_k_indices]
            
            # Sort by time
            sort_indices = np.argsort(top_peaks)
            top_peaks = top_peaks[sort_indices]
            top_scores = top_scores[sort_indices]
        else:
            top_peaks = np.array([])
            top_scores = np.array([])
        
        # Convert frame indices to time
        peak_times = time_axis[top_peaks] if len(top_peaks) > 0 else np.array([])
        
        # Handle seed timestamps if provided
        final_peaks, final_scores, seed_flags = self._incorporate_seeds(
            peak_times, top_scores, time_axis, novelty_scores
        )
        
        logger.info(f"Found {len(final_peaks)} peaks")
        
        return {
            "peak_times": final_peaks,
            "peak_scores": final_scores,
            "seed_based": seed_flags,
            "total_peaks_found": len(peaks),
            "spacing_frames": spacing_frames
        }
    
    def _incorporate_seeds(
        self, 
        peak_times: np.ndarray, 
        peak_scores: np.ndarray,
        time_axis: np.ndarray,
        novelty_scores: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Incorporate seed timestamps into peak selection.
        
        Args:
            peak_times: Currently selected peak times
            peak_scores: Scores of selected peaks
            time_axis: Time axis of novelty scores
            novelty_scores: Raw novelty scores
            
        Returns:
            Tuple of (final_peaks, final_scores, seed_flags)
        """
        if not self.config.seed_timestamps:
            # No seeds provided, return original peaks
            return peak_times, peak_scores, np.zeros(len(peak_times), dtype=bool)
        
        logger.info(f"Incorporating {len(self.config.seed_timestamps)} seed timestamps")
        
        final_peaks = []
        final_scores = []
        seed_flags = []
        
        # Window size for local peak search around seeds (±15-20s)
        seed_window = 20.0  # seconds
        
        # Convert time axis to frame indices
        frame_indices = np.arange(len(time_axis))
        
        for seed_time in self.config.seed_timestamps:
            # Find frame index closest to seed time
            seed_frame_idx = np.argmin(np.abs(time_axis - seed_time))
            
            # Define search window around seed
            window_start = max(0, seed_frame_idx - int(seed_window * len(time_axis) / time_axis[-1]))
            window_end = min(len(novelty_scores), seed_frame_idx + int(seed_window * len(time_axis) / time_axis[-1]))
            
            # Find local maximum in window
            local_window = novelty_scores[window_start:window_end]
            if len(local_window) > 0:
                local_max_idx = np.argmax(local_window)
                actual_frame_idx = window_start + local_max_idx
                local_peak_time = time_axis[actual_frame_idx]
                local_peak_score = novelty_scores[actual_frame_idx]
                
                final_peaks.append(local_peak_time)
                final_scores.append(local_peak_score)
                seed_flags.append(True)
        
        # Add original peaks that don't conflict with seeds
        for i, (peak_time, peak_score) in enumerate(zip(peak_times, peak_scores)):
            # Check if this peak conflicts with any seed-based peak
            conflicts = False
            for seed_peak in final_peaks:
                # Convert spacing from frames to seconds
                spacing_seconds = self.config.peak_spacing * hop_length / sr
                if abs(peak_time - seed_peak) < spacing_seconds:
                    conflicts = True
                    break
            
            if not conflicts:
                final_peaks.append(peak_time)
                final_scores.append(peak_score)
                seed_flags.append(False)
        
        # Sort by time
        if final_peaks:
            sort_indices = np.argsort(final_peaks)
            final_peaks = np.array(final_peaks)[sort_indices]
            final_scores = np.array(final_scores)[sort_indices]
            seed_flags = np.array(seed_flags)[sort_indices]
        else:
            final_peaks = np.array([])
            final_scores = np.array([])
            seed_flags = np.array([], dtype=bool)
        
        return final_peaks, final_scores, seed_flags
