"""
Progress tracking module for MVP Analyzer.

This module handles progress events for SSE.
"""

import json
import sys
import logging
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Defines types of progress events."""
    STAGE_START = "stage_start"
    STAGE_COMPLETE = "stage_complete"
    PROGRESS_UPDATE = "progress_update"
    INFO = "info"
    ERROR = "error"


class AnalysisStage(str, Enum):
    """Defines the stages of the analysis pipeline."""
    INITIALIZATION = "initialization"
    AUDIO_EXTRACTION = "audio_extraction"
    BEAT_TRACKING = "beat_tracking"
    NOVELTY_DETECTION = "novelty_detection"
    PEAK_DETECTION = "peak_detection"
    SEGMENT_BUILDING = "segment_building"
    BEAT_QUANTIZATION = "beat_quantization"
    VIDEO_EXPORT = "video_export"
    RESULT_EXPORT = "result_export"
    COMPLETION = "completion"


class ProgressEmitter:
    """Emits JSON-formatted progress events to stdout for Server-Sent Events (SSE)."""
    
    def __init__(self, enabled: bool = True):
        """Initialize the progress emitter."""
        self.enabled = enabled
        self.current_stage: Optional[AnalysisStage] = None
    
    def start_stage(self, stage: AnalysisStage, message: Optional[str] = None) -> None:
        """Start a new analysis stage."""
        if not self.enabled:
            return
        self.current_stage = stage
        # Emit stage start event
        logger.debug(f"Starting stage: {stage}")
    
    def complete_stage(self, message: Optional[str] = None) -> None:
        """Complete the current analysis stage."""
        if not self.enabled:
            return
        # Emit stage complete event
        logger.debug(f"Completed stage: {self.current_stage}")
        self.current_stage = None
    
    def update_progress(self, percentage: int, message: str) -> None:
        """Update progress for the current stage."""
        if not self.enabled:
            return
        # Emit progress update event
        logger.debug(f"Progress update: {percentage}% - {message}")
    
    def emit_error(self, message: str) -> None:
        """Emit an error event."""
        if not self.enabled:
            return
        logger.error(f"Error: {message}")
    
    def emit_info(self, message: str) -> None:
        """Emit an info event."""
        if not self.enabled:
            return
        logger.info(f"Info: {message}")