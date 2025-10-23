"""
Beat tracking and quantization module for MVP Analyzer.
"""

import logging
from typing import Any

import librosa
import numpy as np

from .audio_security import safe_resample_audio, safe_to_mono
from .config import Config

logger = logging.getLogger(__name__)


class BeatTracker:
    """Handles beat tracking and BPM estimation using librosa."""

    def __init__(self, config: Config):
        """Initialize beat tracker with configuration."""
        self.config = config
        self.sample_rate = 22050  # librosa default
        self.hop_length = 512  # librosa default

    def track_beats(self, audio_data: dict[str, Any]) -> dict[str, Any]:
        """
        Track beats and estimate BPM in audio data.

        Args:
            audio_data: Dict containing audio array and metadata

        Returns:
            Dict containing beat times, BPM, and confidence
        """
        logger.info("Starting beat tracking")

        audio = audio_data["audio"]
        sample_rate = audio_data.get("sample_rate", self.sample_rate)

        # Ensure audio is mono and at correct sample rate (using secure wrappers)
        if len(audio.shape) > 1:
            audio = safe_to_mono(audio)

        if sample_rate != self.sample_rate:
            audio = safe_resample_audio(
                audio, orig_sr=sample_rate, target_sr=self.sample_rate
            )
            sample_rate = self.sample_rate

        # Track beats using librosa
        tempo, beats = librosa.beat.beat_track(
            y=audio,
            sr=sample_rate,
            hop_length=self.hop_length,
            start_bpm=120,  # Initial BPM estimate
            tightness=100,  # Beat tracking tightness
        )

        # Convert beat frames to time
        beat_times = librosa.frames_to_time(
            beats, sr=sample_rate, hop_length=self.hop_length
        )

        # Calculate confidence based on beat consistency
        confidence = self._calculate_confidence(beat_times, tempo)

        # Generate beat grid for quantization
        beat_grid = self._generate_beat_grid(beat_times, tempo, sample_rate)

        logger.info(
            f"Beat tracking completed: BPM={tempo}, confidence={confidence}, beats={len(beats)}"
        )

        return {
            "tempo": float(tempo),
            "beat_times": beat_times.tolist(),
            "confidence": confidence,
            "beat_grid": beat_grid,
            "sample_rate": sample_rate,
            "hop_length": self.hop_length,
            "total_beats": len(beats),
        }

    def _calculate_confidence(self, beat_times: np.ndarray, tempo: float) -> float:
        """
        Calculate confidence in beat tracking based on consistency.

        Args:
            beat_times: Array of beat times in seconds
            tempo: Estimated BPM

        Returns:
            Confidence score between 0 and 1
        """
        if len(beat_times) < 4:
            return 0.0

        # Calculate inter-beat intervals
        intervals = np.diff(beat_times)
        expected_interval = 60.0 / tempo  # Expected interval in seconds

        # Calculate consistency as inverse of coefficient of variation
        if np.mean(intervals) > 0:
            cv = np.std(intervals) / np.mean(intervals)
            consistency = max(0, 1 - cv)
        else:
            consistency = 0.0

        # Weight by how close intervals are to expected
        interval_accuracy = (
            1 - np.mean(np.abs(intervals - expected_interval)) / expected_interval
        )
        interval_accuracy = max(0, interval_accuracy)

        # Combine consistency and accuracy
        confidence = consistency * 0.7 + interval_accuracy * 0.3

        return min(1.0, max(0.0, confidence))

    def _generate_beat_grid(
        self, beat_times: np.ndarray, tempo: float, sample_rate: int
    ) -> dict[str, Any]:
        """
        Generate a regular beat grid for quantization.

        Args:
            beat_times: Detected beat times
            tempo: Estimated BPM
            sample_rate: Audio sample rate

        Returns:
            Dict containing beat grid information
        """
        if len(beat_times) == 0:
            return {
                "grid_times": [],
                "bar_times": [],
                "beat_interval": 0,
                "bars_per_minute": 0,
            }

        # Calculate beat interval
        beat_interval = 60.0 / tempo  # seconds per beat

        # Generate regular grid starting from first beat
        start_time = float(beat_times[0])
        end_time = float(beat_times[-1])

        # Create regular beat grid
        grid_times = np.arange(start_time, end_time + beat_interval, beat_interval)

        # Calculate bar times (assuming 4/4 time signature)
        bars_per_minute = tempo / 4  # 4 beats per bar
        bar_interval = 60.0 / bars_per_minute
        bar_times = np.arange(start_time, end_time + bar_interval, bar_interval)

        return {
            "grid_times": grid_times.tolist(),
            "bar_times": bar_times.tolist(),
            "beat_interval": beat_interval,
            "bars_per_minute": bars_per_minute,
            "time_signature": "4/4",
        }


class BeatQuantizer:
    """Handles quantization of clip boundaries to beat/bar boundaries."""

    def __init__(self, config: Config):
        """Initialize beat quantizer with configuration."""
        self.config = config

    def quantize_clip(
        self, start_time: float, duration: float, beat_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Quantize clip start and duration to beat/bar boundaries.

        Args:
            start_time: Original clip start time
            duration: Original clip duration
            beat_data: Beat tracking results

        Returns:
            Dict containing quantized timing and alignment info
        """
        logger.info(
            f"Quantizing clip: start={start_time:.2f}s, duration={duration:.2f}s"
        )

        # Check if beat tracking confidence is sufficient
        confidence = beat_data.get("confidence", 0.0)
        if confidence < 0.3:  # Low confidence threshold
            logger.warning(
                f"Low beat confidence ({confidence:.3f}), skipping quantization"
            )
            return {
                "aligned": False,
                "start_time": start_time,
                "duration": duration,
                "reason": "low_confidence",
                "confidence": confidence,
            }

        beat_grid = beat_data.get("beat_grid", {})
        grid_times = np.array(beat_grid.get("grid_times", []))
        np.array(beat_grid.get("bar_times", []))

        if len(grid_times) == 0:
            logger.warning("No beat grid available, skipping quantization")
            return {
                "aligned": False,
                "start_time": start_time,
                "duration": duration,
                "reason": "no_beat_grid",
                "confidence": confidence,
            }

        # Quantize start time to nearest beat before the original start
        quantized_start = self._quantize_start_time(start_time, grid_times)

        # Quantize duration to bar boundaries (8, 12, or 16 bars)
        quantized_duration = self._quantize_duration(duration, beat_data)

        # Check if quantization is reasonable
        if self._is_quantization_reasonable(
            start_time, duration, quantized_start, quantized_duration
        ):
            logger.info(
                f"Quantization successful: {start_time:.2f}s→{quantized_start:.2f}s, {duration:.2f}s→{quantized_duration:.2f}s"
            )
            return {
                "aligned": True,
                "start_time": quantized_start,
                "duration": quantized_duration,
                "original_start": start_time,
                "original_duration": duration,
                "confidence": confidence,
                "bars": int(
                    quantized_duration / (60.0 / beat_data["tempo"] / 4)
                ),  # Number of bars
            }
        else:
            logger.warning(
                "Quantization resulted in unreasonable timing, using original"
            )
            return {
                "aligned": False,
                "start_time": start_time,
                "duration": duration,
                "reason": "unreasonable_quantization",
                "confidence": confidence,
            }

    def _quantize_start_time(self, start_time: float, grid_times: np.ndarray) -> float:
        """Quantize start time to nearest beat before the original start."""
        # Find beats before or at the start time
        valid_beats = grid_times[grid_times <= start_time]

        if len(valid_beats) == 0:
            # If no beats before start, use the first beat
            return float(grid_times[0]) if len(grid_times) > 0 else start_time

        # Use the last beat before or at start time
        return float(valid_beats[-1])

    def _quantize_duration(self, duration: float, beat_data: dict[str, Any]) -> float:
        """Quantize duration to bar boundaries (4, 6, 8, 12, or 16 bars)."""
        tempo = beat_data["tempo"]
        bar_duration = 60.0 / (tempo / 4)  # Duration of one bar in seconds

        # Choose appropriate bar counts based on duration
        if duration <= 4 * bar_duration:
            # For short durations, use 2, 4, 6 bars
            bar_counts = [2, 4, 6]
        elif duration <= 8 * bar_duration:
            # For medium durations, use 4, 6, 8 bars
            bar_counts = [4, 6, 8]
        else:
            # For long durations, use 8, 12, 16 bars
            bar_counts = [8, 12, 16]

        bar_durations = [count * bar_duration for count in bar_counts]

        # Find closest duration
        closest_idx = np.argmin([abs(dur - duration) for dur in bar_durations])
        return bar_durations[closest_idx]

    def _is_quantization_reasonable(
        self,
        orig_start: float,
        orig_duration: float,
        quant_start: float,
        quant_duration: float,
    ) -> bool:
        """Check if quantization results are reasonable."""
        # Check if start time moved too far back
        start_shift = orig_start - quant_start
        if start_shift > 10.0:  # More than 10 seconds back
            return False

        # Check if duration changed too much
        duration_ratio = quant_duration / orig_duration
        if duration_ratio < 0.5 or duration_ratio > 2.0:  # More than 50% change
            return False

        return True
