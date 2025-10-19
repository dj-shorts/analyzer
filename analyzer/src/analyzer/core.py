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
        
        try:
            # Start progress tracking
            self.progress_emitter.start_stage(AnalysisStage.INITIALIZATION, "Initializing analysis pipeline")
            
            # Step 1: Extract audio from video
            self.progress_emitter.start_stage(AnalysisStage.AUDIO_EXTRACTION, "Extracting audio from video")
            logger.info("Step 1: Extracting audio from video")
            audio_data = self.audio_extractor.extract()
            self.progress_emitter.complete_stage(AnalysisStage.AUDIO_EXTRACTION, "Audio extraction completed")
            
            # Step 2: Motion analysis (if enabled)
            motion_data = None
            if self.config.with_motion:
                self.progress_emitter.start_stage(AnalysisStage.MOTION_ANALYSIS, "Analyzing motion with optical flow")
                logger.info("Step 2: Motion analysis with optical flow")
                motion_data = self.motion_detector.extract_motion_features(self.config.input_path)
                self.progress_emitter.complete_stage(AnalysisStage.MOTION_ANALYSIS, "Motion analysis completed")
            
            # Step 3: Beat tracking (if enabled)
            beat_data = None
            if self.config.align_to_beat:
                self.progress_emitter.start_stage(AnalysisStage.BEAT_TRACKING, "Tracking beats and estimating BPM")
                logger.info("Step 3: Beat tracking and BPM estimation")
                beat_data = self.beat_tracker.track_beats(audio_data)
                self.progress_emitter.complete_stage(AnalysisStage.BEAT_TRACKING, "Beat tracking completed")
            
            # Step 4: Compute novelty scores
            self.progress_emitter.start_stage(AnalysisStage.NOVELTY_DETECTION, "Computing novelty scores")
            logger.info("Step 4: Computing novelty scores")
            novelty_scores = self.novelty_detector.compute_novelty(audio_data)
            self.progress_emitter.complete_stage(AnalysisStage.NOVELTY_DETECTION, "Novelty detection completed")
            
            # Step 4.5: Combine audio and motion scores (if motion enabled)
            if self.config.with_motion and motion_data and motion_data["motion_available"]:
                logger.info("Step 4.5: Combining audio and motion scores")
                # Interpolate motion scores to audio timeline
                motion_scores_interp = self.motion_detector.interpolate_to_audio_timeline(
                    motion_data, novelty_scores["time_axis"]
                )
                
                # Combine audio and motion scores (0.6*audio + 0.4*motion)
                combined_scores = self.motion_detector.combine_audio_and_motion_scores(
                    novelty_scores["novelty_scores"], motion_scores_interp
                )
                
                # Update novelty scores with combined scores
                novelty_scores["novelty_scores"] = combined_scores
                novelty_scores["motion_available"] = True
                novelty_scores["motion_scores"] = motion_scores_interp
            else:
                novelty_scores["motion_available"] = False
            
            # Step 5: Find peaks
            self.progress_emitter.start_stage(AnalysisStage.PEAK_DETECTION, "Finding peaks in novelty scores")
            logger.info("Step 5: Finding peaks")
            peaks = self.peak_picker.find_peaks(novelty_scores)
            self.progress_emitter.complete_stage(AnalysisStage.PEAK_DETECTION, "Peak detection completed")
            
            # Step 6: Build segments
            self.progress_emitter.start_stage(AnalysisStage.SEGMENT_BUILDING, "Building segments from peaks")
            logger.info("Step 6: Building segments")
            segments = self.segment_builder.build_segments(peaks)
            self.progress_emitter.complete_stage(AnalysisStage.SEGMENT_BUILDING, "Segment building completed")
            
            # Step 7: Beat quantization (if enabled)
            if self.config.align_to_beat and beat_data:
                logger.info("Step 7: Quantizing segments to beat boundaries")
                segments = self._quantize_segments(segments, beat_data)
            
            # Step 8: Export results
            self.progress_emitter.start_stage(AnalysisStage.RESULT_EXPORT, "Exporting analysis results")
            logger.info("Step 8: Exporting results")
            results = self.result_exporter.export(segments, audio_data)
            self.progress_emitter.complete_stage(AnalysisStage.RESULT_EXPORT, "Result export completed")
            
            # Step 9: Video export (if enabled)
            if self.config.export_video:
                self.progress_emitter.start_stage(AnalysisStage.VIDEO_EXPORT, "Exporting video clips")
                logger.info("Step 9: Exporting video clips")
                video_export_results = self.video_exporter.export_clips(
                    segments, self.config.input_path, self.config.export_dir
                )
                results["video_export"] = video_export_results
                self.progress_emitter.complete_stage(AnalysisStage.VIDEO_EXPORT, f"Video export completed: {video_export_results['exported_clips']}/{video_export_results['total_clips']} clips exported")
            
            # Add motion data to results if available
            if motion_data:
                results["motion_data"] = motion_data
            
            # Add beat data to results if available
            if beat_data:
                results["beat_data"] = beat_data
            
            # Complete analysis
            self.progress_emitter.start_stage(AnalysisStage.COMPLETION, "Analysis pipeline completed successfully")
            logger.info("Analysis pipeline completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Analysis pipeline failed: {e}", exc_info=True)
            self.progress_emitter.emit_error(f"Analysis pipeline failed: {e}")
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
