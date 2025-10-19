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
        
        # Compute onset strength (proxy for spectral flux)
        onset_strength = self._compute_onset_strength(audio, sr)
        
        # Compute spectral contrast variance
        spectral_contrast_var = self._compute_spectral_contrast_variance(audio, sr)

        # Ensure both arrays have the same length (onset_strength is shorter by 1 due to diff)
        min_length = min(len(onset_strength), len(spectral_contrast_var))
        onset_strength = onset_strength[:min_length]
        spectral_contrast_var = spectral_contrast_var[:min_length]

        # Robust normalization
        onset_norm = self._robust_normalize(onset_strength)
        contrast_norm = self._robust_normalize(spectral_contrast_var)
        
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
    
    def _compute_onset_strength(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Compute onset strength as a proxy for spectral flux.
        
        Args:
            audio: Input audio signal
            sr: Sample rate
            
        Returns:
            Onset strength time series
        """
        # Compute Short-Time Fourier Transform
        stft = self._compute_stft(audio)
        
        # Compute spectral flux (magnitude differences between consecutive frames)
        magnitude = np.abs(stft)
        
        # Compute differences between consecutive frames
        flux = np.diff(magnitude, axis=1)
        
        # Only keep positive differences (increases in magnitude)
        flux = np.maximum(flux, 0)
        
        # Sum across frequency bins to get onset strength
        onset_strength = np.sum(flux, axis=0)
        
        return onset_strength
    
    def _compute_spectral_contrast_variance(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Compute spectral contrast variance across time.
        
        Args:
            audio: Input audio signal
            sr: Sample rate
            
        Returns:
            Spectral contrast variance time series
        """
        # Compute Short-Time Fourier Transform
        stft = self._compute_stft(audio)
        magnitude = np.abs(stft)
        
        # Compute spectral contrast for each frame
        # Divide spectrum into frequency bands and compute contrast
        n_bins = magnitude.shape[0]
        
        # Define frequency bands (low, mid, high)
        low_band = magnitude[:n_bins//3, :]
        mid_band = magnitude[n_bins//3:2*n_bins//3, :]
        high_band = magnitude[2*n_bins//3:, :]
        
        # Compute mean energy in each band
        low_energy = np.mean(low_band, axis=0)
        mid_energy = np.mean(mid_band, axis=0)
        high_energy = np.mean(high_band, axis=0)
        
        # Compute contrast as variance of band energies
        band_energies = np.vstack([low_energy, mid_energy, high_energy])
        contrast_variance = np.var(band_energies, axis=0)
        
        return contrast_variance
    
    def _compute_stft(self, audio: np.ndarray) -> np.ndarray:
        """
        Compute Short-Time Fourier Transform.
        
        Args:
            audio: Input audio signal
            
        Returns:
            STFT matrix
        """
        # Simple STFT implementation
        n_fft = self.window_size
        hop_length = self.hop_length
        
        # Pad audio to ensure we can compute frames
        audio_padded = np.pad(audio, (0, n_fft), mode='constant')
        
        # Compute frames
        frames = []
        for i in range(0, len(audio_padded) - n_fft + 1, hop_length):
            frame = audio_padded[i:i + n_fft]
            # Apply window (Hanning window)
            windowed = frame * np.hanning(n_fft)
            frames.append(windowed)
        
        # Convert to numpy array and compute FFT
        frames_array = np.array(frames).T
        stft = np.fft.fft(frames_array, n=n_fft, axis=0)
        
        # Return only positive frequencies
        return stft[:n_fft//2 + 1, :]
