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
    
    def analyze(self) -> Dict[str, Any]:
        """
        Run the complete analysis pipeline.
        
        Returns:
            Dict containing analysis results and metadata
        """
        logger.info("Starting analysis pipeline")
        
        try:
            # Step 1: Extract audio from video
            logger.info("Step 1: Extracting audio from video")
            audio_data = self.audio_extractor.extract()
            
            # Step 2: Compute novelty scores
            logger.info("Step 2: Computing novelty scores")
            novelty_scores = self.novelty_detector.compute_novelty(audio_data)
            
            # Step 3: Find peaks
            logger.info("Step 3: Finding peaks")
            peaks = self.peak_picker.find_peaks(novelty_scores)
            
            # Step 4: Build segments
            logger.info("Step 4: Building segments")
            segments = self.segment_builder.build_segments(peaks)
            
            # Step 5: Export results
            logger.info("Step 5: Exporting results")
            results = self.result_exporter.export(segments, audio_data)
            
            logger.info("Analysis pipeline completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Analysis pipeline failed: {e}", exc_info=True)
            raise
