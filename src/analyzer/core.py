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
from .motion import MotionDetector
from .video import VideoExporter
from .progress import ProgressEmitter, AnalysisStage
from .cancellation import managed_resources, ProcessMonitor

logger = logging.getLogger(__name__)


class Analyzer:
    """Main analyzer class that orchestrates the analysis pipeline."""
    
    def __init__(self, config: Config):
        """Initialize the analyzer with configuration."""
        self.config = config
        
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
        
        # Initialize motion detection if enabled
        if config.with_motion:
            self.motion_detector = MotionDetector(config)
        
        # Initialize video export if enabled
        if config.export_video:
            self.video_exporter = VideoExporter(config)
        
        # Initialize progress emitter
        self.progress_emitter = ProgressEmitter(enabled=config.progress_events)
    
    def analyze(self) -> Dict[str, Any]:
        """
        Run the complete analysis pipeline.
        
        Returns:
            Dict containing analysis results and metadata
        """
        logger.info("Starting analysis pipeline")
        
        # Use resource management context manager
        with managed_resources(
            max_threads=self.config.threads,
            ram_limit=self.config.ram_limit
        ) as resource_manager:
            try:
                # Start initialization stage
                self.progress_emitter.start_stage(AnalysisStage.INITIALIZATION)
                self.progress_emitter.update_progress(0, "Initializing analysis pipeline...")
                
                # Step 1: Extract audio from video
                self.progress_emitter.start_stage(AnalysisStage.AUDIO_EXTRACTION)
                logger.info("Step 1: Extracting audio from video")
                audio_data = self.audio_extractor.extract()
                self.progress_emitter.complete_stage("Audio extraction completed")
                
                # Step 2: Beat tracking (if enabled)
                beat_data = None
                if self.config.align_to_beat:
                    self.progress_emitter.start_stage(AnalysisStage.BEAT_TRACKING)
                    logger.info("Step 2: Beat tracking and BPM estimation")
                    beat_data = self.beat_tracker.track_beats(audio_data)
                    self.progress_emitter.complete_stage("Beat tracking completed")
                
                # Step 3: Motion analysis (if enabled)
                motion_data = None
                if self.config.with_motion:
                    logger.info("Step 3: Motion analysis")
                    motion_data = self.motion_detector.extract_motion_features(self.config.input_path)
                
                # Step 4: Compute novelty scores
                self.progress_emitter.start_stage(AnalysisStage.NOVELTY_DETECTION)
                logger.info("Step 4: Computing novelty scores")
                novelty_scores = self.novelty_detector.compute_novelty(audio_data)
                
                # Combine motion and novelty scores if motion analysis is enabled
                if motion_data:
                    novelty_scores = self.motion_detector.combine_audio_and_motion_scores(novelty_scores, motion_data)
                
                self.progress_emitter.complete_stage("Novelty detection completed")
                
                # Step 5: Find peaks
                self.progress_emitter.start_stage(AnalysisStage.PEAK_DETECTION)
                logger.info("Step 5: Finding peaks")
                peaks = self.peak_picker.find_peaks(novelty_scores)
                self.progress_emitter.complete_stage("Peak detection completed")
                
                # Step 6: Build segments
                self.progress_emitter.start_stage(AnalysisStage.SEGMENT_BUILDING)
                logger.info("Step 6: Building segments")
                segments = self.segment_builder.build_segments(peaks)
                self.progress_emitter.complete_stage("Segment building completed")
                
                # Step 7: Beat quantization (if enabled)
                if self.config.align_to_beat and beat_data:
                    self.progress_emitter.start_stage(AnalysisStage.BEAT_QUANTIZATION)
                    logger.info("Step 7: Quantizing segments to beat boundaries")
                    segments = self._quantize_segments(segments, beat_data)
                    self.progress_emitter.complete_stage("Beat quantization completed")
                
                # Step 8: Export results
                self.progress_emitter.start_stage(AnalysisStage.RESULT_EXPORT)
                logger.info("Step 8: Exporting results")
                results = self.result_exporter.export(segments, audio_data)
                self.progress_emitter.complete_stage("Result export completed")
                
                # Step 9: Video export (if enabled)
                if self.config.export_video:
                    self.progress_emitter.start_stage(AnalysisStage.VIDEO_EXPORT)
                    logger.info("Step 9: Exporting video clips")
                    video_results = self.video_exporter.export_clips(segments)
                    results["video_export"] = video_results
                    self.progress_emitter.complete_stage("Video export completed")
                
                # Add beat data to results if available
                if beat_data:
                    results["beat_data"] = beat_data
                
                # Complete analysis
                self.progress_emitter.start_stage(AnalysisStage.COMPLETION)
                self.progress_emitter.update_progress(100, "Analysis completed successfully")
                self.progress_emitter.complete_stage("Analysis pipeline completed successfully")
                
                logger.info("Analysis pipeline completed successfully")
                return results
                
            except KeyboardInterrupt:
                logger.info("Analysis cancelled by user")
                self.progress_emitter.emit_error("Analysis cancelled by user")
                raise
            except Exception as e:
                logger.error(f"Analysis pipeline failed: {e}", exc_info=True)
                self.progress_emitter.emit_error(str(e))
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
        if not segments or "segments" not in segments:
            return segments
        
        quantized_segments = []
        for segment in segments["segments"]:
            quantized = self.beat_quantizer.quantize_clip(
                start_time=segment["start"],
                duration=segment["end"] - segment["start"],
                beat_data=beat_data
            )
            
            # Update segment with quantized values
            updated_segment = segment.copy()
            updated_segment["start"] = quantized["start_time"]
            updated_segment["end"] = quantized["start_time"] + quantized["duration"]
            updated_segment["center"] = (updated_segment["start"] + updated_segment["end"]) / 2
            updated_segment["length"] = updated_segment["end"] - updated_segment["start"]
            updated_segment["aligned"] = quantized["aligned"]
            
            quantized_segments.append(updated_segment)
        
        return {
            "segments": quantized_segments,
            "metadata": segments.get("metadata", {})
        }