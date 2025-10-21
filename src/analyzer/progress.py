"""
Progress tracking module for MVP Analyzer.

This module handles progress events for SSE.
"""

import json
import sys
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Defines types of progress events."""
    STAGE_START = "stage_start"
    STAGE_COMPLETE = "stage_complete"
    PROGRESS_UPDATE = "progress_update"
    PROGRESS = "progress"  # Alias for backward compatibility
    STAGE = "stage"  # Alias for backward compatibility
    COMPLETE = "complete"  # Alias for backward compatibility
    INFO = "info"
    ERROR = "error"


class AnalysisStage(str, Enum):
    """Defines the stages of the analysis pipeline."""
    INITIALIZATION = "initialization"
    AUDIO_EXTRACTION = "audio_extraction"
    BEAT_TRACKING = "beat_tracking"
    NOVELTY_DETECTION = "novelty_detection"
    PEAK_DETECTION = "peak_detection"  # Alias for PEAK_PICKING
    PEAK_PICKING = "peak_picking"
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
        self.stage_start_time: Optional[datetime] = None
        self.stage_progress_ranges = {
            AnalysisStage.INITIALIZATION: (0, 5),
            AnalysisStage.AUDIO_EXTRACTION: (5, 15),
            AnalysisStage.BEAT_TRACKING: (15, 25),
            AnalysisStage.NOVELTY_DETECTION: (15, 35),  # Changed from (30, 50) to (15, 35)
            AnalysisStage.PEAK_DETECTION: (35, 50),
            AnalysisStage.PEAK_PICKING: (35, 50),
            AnalysisStage.SEGMENT_BUILDING: (50, 65),
            AnalysisStage.BEAT_QUANTIZATION: (65, 75),
            AnalysisStage.VIDEO_EXPORT: (75, 90),
            AnalysisStage.RESULT_EXPORT: (90, 100),
            AnalysisStage.COMPLETION: (100, 100),
        }
    
    def emit_event(self, event_type: EventType, **kwargs) -> None:
        """Emit a progress event to stdout."""
        if not self.enabled:
            return
        
        # Extract data field if present
        data = kwargs.pop('data', None)
        
        event = {
            "type": event_type.value,
            "timestamp": datetime.now().isoformat(),
            "elapsed": 0.0,  # Default elapsed time
            **kwargs
        }
        
        # Add data field if present
        if data:
            event.update(data)
        
        # Emit to stdout for SSE
        print(json.dumps(event), flush=True)
    
    def start_stage(self, stage: AnalysisStage, message: Optional[str] = None) -> None:
        """Start a new analysis stage."""
        if not self.enabled:
            return
        
        self.current_stage = stage
        self.stage_start_time = datetime.now()
        
        # Generate default message based on stage
        if message is None:
            stage_messages = {
                AnalysisStage.AUDIO_EXTRACTION: "Extracting audio from video...",
                AnalysisStage.BEAT_TRACKING: "Analyzing beat patterns...",
                AnalysisStage.NOVELTY_DETECTION: "Analyzing audio novelty...",
                AnalysisStage.PEAK_DETECTION: "Detecting peaks...",
                AnalysisStage.PEAK_PICKING: "Detecting peaks...",
                AnalysisStage.SEGMENT_BUILDING: "Building segments...",
                AnalysisStage.BEAT_QUANTIZATION: "Quantizing to beats...",
                AnalysisStage.VIDEO_EXPORT: "Exporting video clips...",
                AnalysisStage.RESULT_EXPORT: "Exporting results...",
                AnalysisStage.COMPLETION: "Analysis complete...",
            }
            message = stage_messages.get(stage, f"Starting {stage.value.replace('_', ' ').title()}")
        
        # Emit stage start event
        self.emit_event(
            EventType.STAGE,  # Use STAGE instead of STAGE_START for backward compatibility
            stage=stage.value,
            message=message
        )
    
    def complete_stage(self, message: Optional[str] = None) -> None:
        """Complete the current analysis stage."""
        if not self.enabled or not self.current_stage:
            return
        
        # Calculate stage duration
        stage_duration = 0.0
        if self.stage_start_time:
            if isinstance(self.stage_start_time, datetime):
                stage_duration = (datetime.now() - self.stage_start_time).total_seconds()
            else:
                # If it's a float (timestamp), calculate difference using time.time()
                stage_duration = time.time() - self.stage_start_time
        
        # Emit stage complete event
        self.emit_event(
            EventType.COMPLETE,  # Use COMPLETE instead of STAGE_COMPLETE for backward compatibility
            stage=self.current_stage.value,
            message=message or f"Completed {self.current_stage.value.replace('_', ' ').title()}",
            progress=100,  # Always 100% when completing
            stage_duration=stage_duration
        )
        
        self.current_stage = None
        self.stage_start_time = None
    
    def update_progress(self, percentage: int, message: str) -> None:
        """Update progress for the current stage."""
        if not self.enabled or not self.current_stage:
            return
        
        # Emit progress update event
        self.emit_event(
            EventType.PROGRESS,  # Use PROGRESS instead of PROGRESS_UPDATE for backward compatibility
            progress=percentage,  # Use 'progress' instead of 'percentage' for backward compatibility
            message=message,
            stage=self.current_stage.value
        )
    
    def emit_error(self, message: str, stage: Optional[AnalysisStage] = None) -> None:
        """Emit an error event."""
        if not self.enabled:
            return
        
        self.emit_event(
            EventType.ERROR,
            message=f"Error: {message}",
            stage=stage.value if stage else None
        )
    
    def emit_info(self, message: str, data: Optional[dict] = None) -> None:
        """Emit an info event."""
        if not self.enabled:
            return
        
        event_data = {"message": message}
        if data:
            event_data.update(data)
        
        self.emit_event(
            EventType.INFO,
            **event_data
        )
    
    def get_stage_progress_range(self, stage: AnalysisStage) -> tuple[int, int]:
        """Get the progress range for a stage."""
        return self.stage_progress_ranges.get(stage, (0, 100))
    
    def calculate_stage_progress(self, stage: AnalysisStage, progress: float) -> int:
        """Calculate overall progress percentage for a stage."""
        start, end = self.get_stage_progress_range(stage)
        return int(start + (end - start) * progress)