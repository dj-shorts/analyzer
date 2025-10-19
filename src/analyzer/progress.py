"""
Progress events module for MVP Analyzer.
Provides JSON events in stdout for SSE (Server-Sent Events) integration.
"""

import json
import sys
import time
from typing import Dict, Any, Optional
from enum import Enum


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
            message: Optional message for the stage
        """
        if not self.enabled:
            return
        
        self.current_stage = stage
        self.stage_start_time = time.time()
        
        default_messages = {
            AnalysisStage.INITIALIZATION: "Initializing analysis...",
            AnalysisStage.AUDIO_EXTRACTION: "Extracting audio from video...",
            AnalysisStage.NOVELTY_DETECTION: "Analyzing audio novelty...",
            AnalysisStage.PEAK_DETECTION: "Detecting peaks in audio...",
            AnalysisStage.BEAT_TRACKING: "Tracking beat patterns...",
            AnalysisStage.MOTION_ANALYSIS: "Analyzing video motion...",
            AnalysisStage.SEGMENT_BUILDING: "Building video segments...",
            AnalysisStage.VIDEO_EXPORT: "Exporting video clips...",
            AnalysisStage.RESULT_EXPORT: "Exporting analysis results...",
            AnalysisStage.COMPLETION: "Analysis completed successfully"
        }
        
        stage_message = message or default_messages.get(stage, f"Starting {stage.value}...")
        
        self.emit_event(
            EventType.STAGE,
            stage=stage,
            message=stage_message,
            data={"stage_start_time": self.stage_start_time}
        )
    
    def update_progress(self, progress: int, message: Optional[str] = None) -> None:
        """
        Update progress for current stage.
        
        Args:
            progress: Progress percentage (0-100)
            message: Optional progress message
        """
        if not self.enabled or self.current_stage is None:
            return
        
        self.emit_event(
            EventType.PROGRESS,
            stage=self.current_stage,
            progress=progress,
            message=message
        )
    
    def complete_stage(self, message: Optional[str] = None) -> None:
        """
        Complete current stage.
        
        Args:
            message: Optional completion message
        """
        if not self.enabled or self.current_stage is None:
            return
        
        stage_duration = time.time() - (self.stage_start_time or self.start_time)
        
        completion_message = message or f"Completed {self.current_stage.value}"
        
        self.emit_event(
            EventType.COMPLETE,
            stage=self.current_stage,
            progress=100,
            message=completion_message,
            data={"stage_duration": stage_duration}
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
            stage=stage or self.current_stage,
            message=f"Error: {error_message}"
        )
    
    def emit_info(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit an info event.
        
        Args:
            message: Information message
            data: Optional additional data
        """
        if not self.enabled:
            return
        
        self.emit_event(
            EventType.INFO,
            message=message,
            data=data
        )
    
    def get_stage_progress_range(self, stage: AnalysisStage) -> tuple[int, int]:
        """
        Get progress range for a specific stage.
        
        Args:
            stage: Analysis stage
            
        Returns:
            Tuple of (start_progress, end_progress) percentages
        """
        # Define progress ranges for each stage (total should add up to 100)
        stage_ranges = {
            AnalysisStage.INITIALIZATION: (0, 5),
            AnalysisStage.AUDIO_EXTRACTION: (5, 15),
            AnalysisStage.NOVELTY_DETECTION: (15, 35),
            AnalysisStage.PEAK_DETECTION: (35, 50),
            AnalysisStage.BEAT_TRACKING: (50, 60),
            AnalysisStage.MOTION_ANALYSIS: (60, 75),
            AnalysisStage.SEGMENT_BUILDING: (75, 85),
            AnalysisStage.VIDEO_EXPORT: (85, 95),
            AnalysisStage.RESULT_EXPORT: (95, 100),
            AnalysisStage.COMPLETION: (100, 100)
        }
        
        return stage_ranges.get(stage, (0, 100))
    
    def calculate_stage_progress(self, stage: AnalysisStage, stage_progress: float) -> int:
        """
        Calculate overall progress from stage progress.
        
        Args:
            stage: Current analysis stage
            stage_progress: Progress within stage (0.0-1.0)
            
        Returns:
            Overall progress percentage (0-100)
        """
        start_progress, end_progress = self.get_stage_progress_range(stage)
        stage_range = end_progress - start_progress
        overall_progress = start_progress + (stage_progress * stage_range)
        return int(overall_progress)
