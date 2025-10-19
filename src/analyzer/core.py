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
from .progress import ProgressEmitter, AnalysisStage

logger = logging.getLogger(__name__)


class Analyzer:
    """Main analyzer class that orchestrates the analysis pipeline."""
    
    def __init__(self, config: Config):
        """Initialize the analyzer with configuration."""
        self.config = config
        
        # Initialize progress emitter
        self.progress_emitter = ProgressEmitter(enabled=config.progress_events)
        
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
        Run the complete analysis pipeline.
        
        Returns:
            Dict containing analysis results and metadata
        """
        logger.info("Starting analysis pipeline")
        
        # Start initialization stage
        self.progress_emitter.start_stage(AnalysisStage.INITIALIZATION)
        self.progress_emitter.update_progress(0, "Initializing analysis pipeline...")
        
        try:
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
            
            # Step 3: Compute novelty scores
            self.progress_emitter.start_stage(AnalysisStage.NOVELTY_DETECTION)
            logger.info("Step 3: Computing novelty scores")
            novelty_scores = self.novelty_detector.compute_novelty(audio_data)
            self.progress_emitter.complete_stage("Novelty detection completed")
            
            # Step 4: Find peaks
            self.progress_emitter.start_stage(AnalysisStage.PEAK_DETECTION)
            logger.info("Step 4: Finding peaks")
            peaks = self.peak_picker.find_peaks(novelty_scores)
            self.progress_emitter.complete_stage("Peak detection completed")
            
            # Step 5: Build segments
            self.progress_emitter.start_stage(AnalysisStage.SEGMENT_BUILDING)
            logger.info("Step 5: Building segments")
            segments = self.segment_builder.build_segments(peaks)
            self.progress_emitter.complete_stage("Segment building completed")
            
            # Step 6: Beat quantization (if enabled)
            if self.config.align_to_beat and beat_data:
                logger.info("Step 6: Quantizing segments to beat boundaries")
                segments = self._quantize_segments(segments, beat_data)
            
            # Step 7: Export results
            self.progress_emitter.start_stage(AnalysisStage.RESULT_EXPORT)
            logger.info("Step 7: Exporting results")
            results = self.result_exporter.export(segments, audio_data)
            self.progress_emitter.complete_stage("Result export completed")
            
            # Add beat data to results if available
            if beat_data:
                results["beat_data"] = beat_data
            
            # Complete analysis
            self.progress_emitter.start_stage(AnalysisStage.COMPLETION)
            self.progress_emitter.update_progress(100, "Analysis completed successfully")
            self.progress_emitter.complete_stage("Analysis pipeline completed successfully")
            
            logger.info("Analysis pipeline completed successfully")
            return results
            
        except Exception as e:
            self.progress_emitter.emit_error(str(e))
            logger.error(f"Analysis pipeline failed: {e}", exc_info=True)
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
