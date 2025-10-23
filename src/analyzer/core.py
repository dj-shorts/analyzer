"""
Core analyzer module for MVP Analyzer.
"""

import logging
from typing import Any

from .audio import AudioExtractor
from .beats import BeatQuantizer, BeatTracker
from .config import Config
from .export import ResultExporter
from .metrics import AnalysisStage as MetricsStage
from .metrics import MetricsCollector
from .motion import MotionDetector
from .novelty import NoveltyDetector
from .peaks import PeakPicker
from .progress import AnalysisStage as ProgressStage
from .progress import ProgressEmitter
from .segments import SegmentBuilder
from .video import VideoExporter

logger = logging.getLogger(__name__)


class Analyzer:
    """Main analyzer class that orchestrates the analysis pipeline."""

    def __init__(self, config: Config):
        """Initialize the analyzer with configuration."""
        self.config = config

        # Initialize metrics collector
        self.metrics_collector = MetricsCollector()

        # Initialize progress emitter if enabled
        if config.progress_events:
            self.progress_emitter = ProgressEmitter(enabled=True)
        else:
            self.progress_emitter = ProgressEmitter(enabled=False)

        # Initialize components
        self.audio_extractor = AudioExtractor(config)
        self.novelty_detector = NoveltyDetector(config)
        self.peak_picker = PeakPicker(config)
        self.segment_builder = SegmentBuilder(config)
        self.result_exporter = ResultExporter(config)

        # Initialize motion detector if enabled
        if config.with_motion:
            self.motion_detector = MotionDetector(config)
        else:
            self.motion_detector = None

        # Initialize video exporter if enabled
        if config.export_video:
            self.video_exporter = VideoExporter(config)
        else:
            self.video_exporter = None

        # Initialize beat tracking components if enabled
        if config.align_to_beat:
            self.beat_tracker = BeatTracker(config)
            self.beat_quantizer = BeatQuantizer(config)

    def analyze(self) -> dict[str, Any]:
        """
        Run the complete analysis pipeline with metrics collection.

        Returns:
            Dict containing analysis results and metadata
        """
        logger.info("Starting analysis pipeline")

        try:
            # Set configuration metrics
            self.metrics_collector.set_configuration_metrics(
                clips_requested=self.config.clips_count,
                min_length=self.config.min_clip_length,
                max_length=self.config.max_clip_length,
                with_motion=self.config.with_motion,
                align_to_beat=self.config.align_to_beat,
            )

            # Step 1: Extract audio from video
            logger.info("Step 1: Extracting audio from video")
            self.progress_emitter.start_stage(ProgressStage.AUDIO_EXTRACTION)
            self.metrics_collector.start_stage(MetricsStage.AUDIO_EXTRACTION)
            audio_data = self.audio_extractor.extract()
            self.metrics_collector.finish_stage(MetricsStage.AUDIO_EXTRACTION)
            self.progress_emitter.complete_stage()

            # Set audio metrics
            self.metrics_collector.set_audio_metrics(
                duration=audio_data.get("duration", 0.0),
                sample_rate=audio_data.get("sample_rate", 0),
                bytes_count=len(audio_data.get("audio", [])) * 4,  # Approximate bytes
            )

            # Step 2: Motion analysis (if enabled)
            motion_data = None
            if self.config.with_motion and self.motion_detector:
                logger.info("Step 2: Motion analysis")
                self.progress_emitter.start_stage(ProgressStage.MOTION_ANALYSIS)
                self.metrics_collector.start_stage(MetricsStage.MOTION_ANALYSIS)
                motion_data = self.motion_detector.analyze_motion(
                    self.config.input_path
                )
                self.metrics_collector.finish_stage(MetricsStage.MOTION_ANALYSIS)
                self.progress_emitter.complete_stage()

            # Step 3: Beat tracking (if enabled)
            beat_data = None
            if self.config.align_to_beat:
                logger.info("Step 3: Beat tracking and BPM estimation")
                self.progress_emitter.start_stage(ProgressStage.BEAT_TRACKING)
                self.metrics_collector.start_stage(MetricsStage.BEAT_TRACKING)
                beat_data = self.beat_tracker.track_beats(audio_data)
                self.metrics_collector.finish_stage(MetricsStage.BEAT_TRACKING)
                self.progress_emitter.complete_stage()

            # Step 4: Compute novelty scores
            logger.info("Step 4: Computing novelty scores")
            self.progress_emitter.start_stage(ProgressStage.NOVELTY_DETECTION)
            self.metrics_collector.start_stage(MetricsStage.NOVELTY_DETECTION)
            novelty_scores = self.novelty_detector.compute_novelty(audio_data)
            self.metrics_collector.finish_stage(MetricsStage.NOVELTY_DETECTION)
            self.progress_emitter.complete_stage()

            # Set novelty metrics
            self.metrics_collector.set_novelty_metrics(
                peaks_count=0,  # Will be updated after peak picking
                frames_count=len(novelty_scores.get("time_axis", [])),
            )

            # Combine audio and motion scores if motion analysis was performed
            if motion_data and motion_data.get("motion_available", False):
                logger.info("Combining audio and motion scores (60/40 blend)")
                # Use novelty timeline instead of raw audio samples
                novelty_timeline = novelty_scores["time_axis"]

                # Interpolate motion scores to novelty timeline
                motion_scores = self.motion_detector.interpolate_to_audio_timeline(
                    motion_data, novelty_timeline
                )
                # Combine with novelty scores
                combined_scores = self.motion_detector.combine_audio_and_motion_scores(
                    novelty_scores["novelty_scores"], motion_scores
                )
                # Update novelty scores with combined values
                novelty_scores["novelty_scores"] = combined_scores

            # Step 5: Find peaks
            logger.info("Step 5: Finding peaks")
            self.progress_emitter.start_stage(ProgressStage.PEAK_PICKING)
            self.metrics_collector.start_stage(MetricsStage.PEAK_PICKING)
            peaks = self.peak_picker.find_peaks(novelty_scores)
            self.metrics_collector.finish_stage(MetricsStage.PEAK_PICKING)
            self.progress_emitter.complete_stage()

            # Update novelty metrics with actual peaks count
            self.metrics_collector.set_novelty_metrics(
                peaks_count=len(peaks.get("peaks", [])),
                frames_count=len(novelty_scores.get("time_axis", [])),
            )

            # Step 6: Build segments
            logger.info("Step 6: Building segments")
            self.progress_emitter.start_stage(ProgressStage.SEGMENT_BUILDING)
            self.metrics_collector.start_stage(MetricsStage.SEGMENT_BUILDING)
            segments = self.segment_builder.build_segments(peaks)
            self.metrics_collector.finish_stage(MetricsStage.SEGMENT_BUILDING)
            self.progress_emitter.complete_stage()

            # Set processing metrics
            self.metrics_collector.set_processing_metrics(
                clips_generated=len(segments.get("segments", [])),
                segments_built=len(segments.get("segments", [])),
            )

            # Step 7: Beat quantization (if enabled)
            if self.config.align_to_beat and beat_data:
                logger.info("Step 7: Quantizing segments to beat boundaries")
                self.progress_emitter.start_stage(ProgressStage.BEAT_QUANTIZATION)
                segments = self._quantize_segments(segments, beat_data)
                self.progress_emitter.complete_stage()

            # Step 8: Export results (initial, without final metrics)
            logger.info("Step 8: Exporting results (initial)")
            self.progress_emitter.start_stage(ProgressStage.RESULT_EXPORT)
            self.metrics_collector.start_stage(MetricsStage.EXPORT)

            # Perform initial export without final metrics
            results = self.result_exporter.export(segments, audio_data)
            self.metrics_collector.finish_stage(MetricsStage.EXPORT)
            self.progress_emitter.complete_stage()

            # Step 9: Video export (if enabled)
            if self.video_exporter:
                logger.info("Step 9: Exporting video clips")
                self.progress_emitter.start_stage(ProgressStage.VIDEO_EXPORT)
                self.metrics_collector.start_stage(MetricsStage.VIDEO_EXPORT)

                video_results = self.video_exporter.export_clips(
                    segments, self.config.input_path, self.config.export_dir
                )
                results["video_export"] = video_results

                self.metrics_collector.finish_stage(MetricsStage.VIDEO_EXPORT)
                self.progress_emitter.complete_stage()

                logger.info(
                    f"Video export completed: {video_results['exported_clips']}/{video_results['total_clips']} clips exported"
                )

            # Finish metrics collection after all stages complete
            final_metrics = self.metrics_collector.finish()

            # Add metrics to results for CLI --metrics option
            results["metrics"] = final_metrics.to_json_metrics()

            # Step 10: Final export with complete metrics
            logger.info("Step 10: Finalizing results export with complete metrics")
            # Re-export the JSON with complete metrics to overwrite the initial file
            self.result_exporter.export(
                segments, audio_data, final_metrics.to_json_metrics()
            )

            # Add beat data to results if available
            if beat_data:
                results["beat_data"] = beat_data

            # Add motion data to results if available
            if motion_data:
                results["motion_data"] = motion_data

            logger.info("Analysis pipeline completed successfully")
            return results

        except Exception as e:
            logger.error(f"Analysis pipeline failed: {e}", exc_info=True)

            # Emit error event if progress tracking is enabled
            if hasattr(self, "progress_emitter") and self.progress_emitter.enabled:
                self.progress_emitter.emit_error(str(e))

            # Still finish metrics collection even on error
            self.metrics_collector.finish()
            raise

    def _quantize_segments(
        self, segments: dict[str, Any], beat_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Quantize segment boundaries to beat/bar boundaries.

        Args:
            segments: Original segments data
            beat_data: Beat tracking results

        Returns:
            Updated segments with quantized boundaries
        """
        logger.info("Quantizing segment boundaries to beat grid")

        quantized_segments = []

        for segment in segments.get("segments", []):
            start_time = segment["start"]
            duration = segment["length"]

            # Quantize this segment
            quantized = self.beat_quantizer.quantize_clip(
                start_time, duration, beat_data
            )

            # Create updated segment
            updated_segment = segment.copy()
            updated_segment.update(
                {
                    "start": quantized["start_time"],
                    "length": quantized["duration"],
                    "end": quantized["start_time"] + quantized["duration"],
                    "aligned_to_beat": quantized["aligned"],
                    "beat_confidence": quantized["confidence"],
                }
            )

            # Add quantization details if aligned
            if quantized["aligned"]:
                updated_segment.update(
                    {
                        "original_start": quantized["original_start"],
                        "original_duration": quantized["original_duration"],
                        "bars": quantized["bars"],
                    }
                )

            quantized_segments.append(updated_segment)

        # Update segments data
        updated_segments = segments.copy()
        updated_segments["segments"] = quantized_segments
        updated_segments["beat_aligned"] = True

        return updated_segments
