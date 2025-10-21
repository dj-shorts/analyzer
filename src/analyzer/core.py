"""
Core analyzer module for MVP Analyzer.
"""

import logging
from typing import Dict, Any

from .config import Config
from .audio import AudioExtractor
from .novelty import NoveltyDetector
from .peaks import PeakPicker
from .segments import SegmentBuilder
from .export import ResultExporter
from .beats import BeatTracker, BeatQuantizer
from .metrics import MetricsCollector, AnalysisStage

logger = logging.getLogger(__name__)


class Analyzer:
    """Main analyzer class that orchestrates the analysis pipeline."""
    
    def __init__(self, config: Config):
        """Initialize the analyzer with configuration."""
        self.config = config
        
        # Initialize metrics collector
        self.metrics_collector = MetricsCollector()
        
        # Initialize components
        self.audio_extractor = AudioExtractor(config)
        self.novelty_detector = NoveltyDetector(config)
        self.peak_picker = PeakPicker(config)
        self.segment_builder = SegmentBuilder(config)
        self.result_exporter = ResultExporter(config)
        
        # Initialize beat tracking components if enabled
        if config.align_to_beat:
            self.beat_tracker = BeatTracker(config)
            self.beat_quantizer = BeatQuantizer(config)
    
    def analyze(self) -> Dict[str, Any]:
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
                align_to_beat=self.config.align_to_beat
            )
            
            # Step 1: Extract audio from video
            logger.info("Step 1: Extracting audio from video")
            self.metrics_collector.start_stage(AnalysisStage.AUDIO_EXTRACTION)
            audio_data = self.audio_extractor.extract()
            self.metrics_collector.finish_stage(AnalysisStage.AUDIO_EXTRACTION)
            
            # Set audio metrics
            self.metrics_collector.set_audio_metrics(
                duration=audio_data.get("duration", 0.0),
                sample_rate=audio_data.get("sample_rate", 0),
                bytes_count=len(audio_data.get("audio", [])) * 4  # Approximate bytes
            )
            
            # Step 2: Beat tracking (if enabled)
            beat_data = None
            if self.config.align_to_beat:
                logger.info("Step 2: Beat tracking and BPM estimation")
                self.metrics_collector.start_stage(AnalysisStage.BEAT_TRACKING)
                beat_data = self.beat_tracker.track_beats(audio_data)
                self.metrics_collector.finish_stage(AnalysisStage.BEAT_TRACKING)
            
            # Step 3: Compute novelty scores
            logger.info("Step 3: Computing novelty scores")
            self.metrics_collector.start_stage(AnalysisStage.NOVELTY_DETECTION)
            novelty_scores = self.novelty_detector.compute_novelty(audio_data)
            self.metrics_collector.finish_stage(AnalysisStage.NOVELTY_DETECTION)
            
            # Set novelty metrics
            self.metrics_collector.set_novelty_metrics(
                peaks_count=0,  # Will be updated after peak picking
                frames_count=len(novelty_scores.get("time_axis", []))
            )
            
            # Step 4: Find peaks
            logger.info("Step 4: Finding peaks")
            self.metrics_collector.start_stage(AnalysisStage.PEAK_PICKING)
            peaks = self.peak_picker.find_peaks(novelty_scores)
            self.metrics_collector.finish_stage(AnalysisStage.PEAK_PICKING)
            
            # Update novelty metrics with actual peaks count
            self.metrics_collector.set_novelty_metrics(
                peaks_count=len(peaks.get("peaks", [])),
                frames_count=len(novelty_scores.get("time_axis", []))
            )
            
            # Step 5: Build segments
            logger.info("Step 5: Building segments")
            self.metrics_collector.start_stage(AnalysisStage.SEGMENT_BUILDING)
            segments = self.segment_builder.build_segments(peaks)
            self.metrics_collector.finish_stage(AnalysisStage.SEGMENT_BUILDING)
            
            # Set processing metrics
            self.metrics_collector.set_processing_metrics(
                clips_generated=len(segments.get("segments", [])),
                segments_built=len(segments.get("segments", []))
            )
            
            # Step 6: Beat quantization (if enabled)
            if self.config.align_to_beat and beat_data:
                logger.info("Step 6: Quantizing segments to beat boundaries")
                segments = self._quantize_segments(segments, beat_data)
            
            # Step 7: Export results
            logger.info("Step 7: Exporting results")
            self.metrics_collector.start_stage(AnalysisStage.EXPORT)
            
            # Finish metrics collection first
            final_metrics = self.metrics_collector.finish()
            
            # Export with metrics
            results = self.result_exporter.export(segments, audio_data, final_metrics.to_json_metrics())
            self.metrics_collector.finish_stage(AnalysisStage.EXPORT)
            
            # Add beat data to results if available
            if beat_data:
                results["beat_data"] = beat_data
            
            logger.info("Analysis pipeline completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Analysis pipeline failed: {e}", exc_info=True)
            # Still finish metrics collection even on error
            self.metrics_collector.finish()
            raise
    
    def _quantize_segments(self, segments: Dict[str, Any], beat_data: Dict[str, Any]) -> Dict[str, Any]:
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
            quantized = self.beat_quantizer.quantize_clip(start_time, duration, beat_data)
            
            # Create updated segment
            updated_segment = segment.copy()
            updated_segment.update({
                "start": quantized["start_time"],
                "length": quantized["duration"],
                "end": quantized["start_time"] + quantized["duration"],
                "aligned_to_beat": quantized["aligned"],
                "beat_confidence": quantized["confidence"]
            })
            
            # Add quantization details if aligned
            if quantized["aligned"]:
                updated_segment.update({
                    "original_start": quantized["original_start"],
                    "original_duration": quantized["original_duration"],
                    "bars": quantized["bars"]
                })
            
            quantized_segments.append(updated_segment)
        
        # Update segments data
        updated_segments = segments.copy()
        updated_segments["segments"] = quantized_segments
        updated_segments["beat_aligned"] = True
        
        return updated_segments
