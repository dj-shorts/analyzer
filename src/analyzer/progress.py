"""
Progress events module for Epic E2.
Handles JSON-formatted events to stdout for Server-Sent Events (SSE).
"""

import json
import time
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of progress events."""
    PROGRESS = "progress"
    STAGE = "stage"
    COMPLETE = "complete"
    ERROR = "error"
    INFO = "info"


class AnalysisStage(Enum):
    """Analysis pipeline stages."""
    INITIALIZATION = "initialization"
    AUDIO_EXTRACTION = "audio_extraction"
    NOVELTY_DETECTION = "novelty_detection"
    PEAK_DETECTION = "peak_detection"
    BEAT_TRACKING = "beat_tracking"
    MOTION_ANALYSIS = "motion_analysis"
    SEGMENT_BUILDING = "segment_building"
    VIDEO_EXPORT = "video_export"
    RESULT_EXPORT = "result_export"
    COMPLETION = "completion"


class ProgressEmitter:
    """Emits JSON progress events to stdout for SSE integration."""
    
    def __init__(self, enabled: bool = True):
        """
        Initialize progress emitter.
        
        Args:
            enabled: Whether to emit progress events (default: True)
        """
        self.enabled = enabled
        self.start_time = time.time()
        self.current_stage = None
        self.stage_start_time = None
    
    def emit_event(self, event_type: EventType, stage: Optional[AnalysisStage] = None, 
                   progress: Optional[int] = None, message: Optional[str] = None,
                   data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit a progress event to stdout.
        
        Args:
            event_type: Type of event to emit
            stage: Current analysis stage
            progress: Progress percentage (0-100)
            message: Human-readable message
            data: Additional event data
        """
        if not self.enabled:
            return
        
        event = {
            "type": event_type.value,
            "timestamp": time.time(),
            "elapsed": time.time() - self.start_time
        }
        
        if stage is not None:
            event["stage"] = stage.value
        
        if progress is not None:
            event["progress"] = min(100, max(0, progress))
        
        if message is not None:
            event["message"] = message
        
        if data is not None:
            event.update(data)
        
        # Write JSON event to stdout (one per line for SSE compatibility)
        print(json.dumps(event, ensure_ascii=False), flush=True)
    
    def start_stage(self, stage: AnalysisStage, message: Optional[str] = None) -> None:
        """
        Start a new analysis stage.
        
        Args:
            stage: Stage to start
            message: Optional stage description
        """
        if not self.enabled:
            return
        
        self.current_stage = stage
        self.stage_start_time = time.time()
        
        self.emit_event(
            EventType.STAGE,
            stage=stage,
            message=message or f"Starting {stage.value.replace('_', ' ').title()}"
        )
    
    def update_progress(self, progress: int, message: Optional[str] = None) -> None:
        """
        Update progress within current stage.
        
        Args:
            progress: Progress percentage (0-100)
            message: Optional progress message
        """
        if not self.enabled:
            return
        
        self.emit_event(
            EventType.PROGRESS,
            stage=self.current_stage,
            progress=progress,
            message=message
        )
    
    def complete_stage(self, stage: AnalysisStage, message: Optional[str] = None) -> None:
        """
        Complete an analysis stage.
        
        Args:
            stage: Stage that was completed
            message: Optional completion message
        """
        if not self.enabled:
            return
        
        elapsed = time.time() - self.stage_start_time if self.stage_start_time else 0
        
        self.emit_event(
            EventType.COMPLETE,
            stage=stage,
            message=message or f"Completed {stage.value.replace('_', ' ').title()}",
            data={"stage_duration": elapsed}
        )
    
    def emit_error(self, error_message: str, stage: Optional[AnalysisStage] = None) -> None:
        """
        Emit an error event.
        
        Args:
            error_message: Error description
            stage: Optional stage where error occurred
        """
        if not self.enabled:
            return
        
        self.emit_event(
            EventType.ERROR,
            stage=stage,
            message=f"Error: {error_message}"
        )
    
    def emit_info(self, message: str, stage: Optional[AnalysisStage] = None) -> None:
        """
        Emit an info event.
        
        Args:
            message: Info message
            stage: Optional current stage
        """
        if not self.enabled:
            return
        
        self.emit_event(
            EventType.INFO,
            stage=stage,
            message=message
        )
