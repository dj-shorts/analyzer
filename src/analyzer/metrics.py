"""
Prometheus metrics module for MVP Analyzer.

This module provides Prometheus-compatible metrics for observability.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AnalysisStage(Enum):
    """Analysis pipeline stages for timing metrics."""
    INITIALIZATION = "initialization"
    AUDIO_EXTRACTION = "audio_extraction"
    NOVELTY_DETECTION = "novelty_detection"
    PEAK_PICKING = "peak_picking"
    BEAT_TRACKING = "beat_tracking"
    SEGMENT_BUILDING = "segment_building"
    MOTION_ANALYSIS = "motion_analysis"
    EXPORT = "export"
    VIDEO_EXPORT = "video_export"
    TOTAL = "total"


@dataclass
class StageTiming:
    """Timing information for a single stage."""
    stage: AnalysisStage
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    
    def finish(self) -> None:
        """Mark stage as finished and calculate duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time


@dataclass
class AnalysisMetrics:
    """Comprehensive metrics for analysis pipeline."""
    # Timing metrics
    stage_timings: Dict[AnalysisStage, StageTiming] = field(default_factory=dict)
    total_duration: float = 0.0
    
    # Novelty metrics
    novelty_peaks_count: int = 0
    novelty_frames_count: int = 0
    
    # Audio metrics
    audio_duration: float = 0.0
    audio_sample_rate: int = 0
    audio_bytes: int = 0
    
    # Video metrics
    video_duration: float = 0.0
    video_bytes: int = 0
    video_width: int = 0
    video_height: int = 0
    
    # Processing metrics
    clips_generated: int = 0
    segments_built: int = 0
    memory_peak_mb: float = 0.0
    
    # Configuration metrics
    clips_requested: int = 0
    min_clip_length: float = 0.0
    max_clip_length: float = 0.0
    with_motion: bool = False
    align_to_beat: bool = False
    
    def start_stage(self, stage: AnalysisStage) -> None:
        """Start timing a stage."""
        self.stage_timings[stage] = StageTiming(
            stage=stage,
            start_time=time.time()
        )
        logger.debug(f"Started stage: {stage.value}")
    
    def finish_stage(self, stage: AnalysisStage) -> None:
        """Finish timing a stage."""
        if stage in self.stage_timings:
            self.stage_timings[stage].finish()
            logger.debug(f"Finished stage: {stage.value} in {self.stage_timings[stage].duration:.3f}s")
    
    def finish_total(self) -> None:
        """Finish total timing."""
        self.finish_stage(AnalysisStage.TOTAL)
        self.total_duration = self.stage_timings[AnalysisStage.TOTAL].duration
    
    def get_stage_duration(self, stage: AnalysisStage) -> float:
        """Get duration for a specific stage."""
        if stage in self.stage_timings and self.stage_timings[stage].duration is not None:
            return self.stage_timings[stage].duration
        return 0.0
    
    def to_prometheus_metrics(self) -> Dict[str, Any]:
        """Convert metrics to Prometheus-compatible format."""
        metrics = {
            # Timing metrics
            "job_duration_seconds": {
                "total": self.total_duration,
                "stages": {
                    stage.value: self.get_stage_duration(stage)
                    for stage in AnalysisStage
                    if stage != AnalysisStage.TOTAL
                }
            },
            
            # Novelty metrics
            "novelty_peaks_count": self.novelty_peaks_count,
            "novelty_frames_count": self.novelty_frames_count,
            
            # Audio metrics
            "audio_duration_seconds": self.audio_duration,
            "audio_sample_rate_hz": self.audio_sample_rate,
            "audio_bytes": self.audio_bytes,
            
            # Video metrics
            "video_duration_seconds": self.video_duration,
            "video_bytes": self.video_bytes,
            "video_width_pixels": self.video_width,
            "video_height_pixels": self.video_height,
            
            # Processing metrics
            "clips_generated": self.clips_generated,
            "segments_built": self.segments_built,
            "memory_peak_mb": self.memory_peak_mb,
            
            # Configuration metrics
            "clips_requested": self.clips_requested,
            "min_clip_length_seconds": self.min_clip_length,
            "max_clip_length_seconds": self.max_clip_length,
            "with_motion_enabled": 1 if self.with_motion else 0,
            "align_to_beat_enabled": 1 if self.align_to_beat else 0,
        }
        
        return metrics
    
    def to_json_metrics(self) -> Dict[str, Any]:
        """Convert metrics to JSON format for export."""
        return {
            "timings": {
                "total_duration_seconds": self.total_duration,
                "stages": {
                    stage.value: {
                        "duration_seconds": self.get_stage_duration(stage),
                        "start_time": self.stage_timings[stage].start_time if stage in self.stage_timings else None,
                        "end_time": self.stage_timings[stage].end_time if stage in self.stage_timings else None
                    }
                    for stage in AnalysisStage
                    if stage != AnalysisStage.TOTAL
                }
            },
            "novelty": {
                "peaks_count": self.novelty_peaks_count,
                "frames_count": self.novelty_frames_count
            },
            "audio": {
                "duration_seconds": self.audio_duration,
                "sample_rate_hz": self.audio_sample_rate,
                "bytes": self.audio_bytes
            },
            "video": {
                "duration_seconds": self.video_duration,
                "bytes": self.video_bytes,
                "width_pixels": self.video_width,
                "height_pixels": self.video_height
            },
            "processing": {
                "clips_generated": self.clips_generated,
                "segments_built": self.segments_built,
                "memory_peak_mb": self.memory_peak_mb
            },
            "configuration": {
                "clips_requested": self.clips_requested,
                "min_clip_length_seconds": self.min_clip_length,
                "max_clip_length_seconds": self.max_clip_length,
                "with_motion": self.with_motion,
                "align_to_beat": self.align_to_beat
            }
        }


class MetricsCollector:
    """Collects and manages analysis metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = AnalysisMetrics()
        self.start_time = time.time()
        
        # Start total timing
        self.metrics.start_stage(AnalysisStage.TOTAL)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.finish()
    
    def start_stage(self, stage: AnalysisStage) -> None:
        """Start timing a stage."""
        self.metrics.start_stage(stage)
    
    def finish_stage(self, stage: AnalysisStage) -> None:
        """Finish timing a stage."""
        self.metrics.finish_stage(stage)
    
    def set_audio_metrics(self, duration: float, sample_rate: int, bytes_count: int) -> None:
        """Set audio-related metrics."""
        self.metrics.audio_duration = duration
        self.metrics.audio_sample_rate = sample_rate
        self.metrics.audio_bytes = bytes_count
    
    def set_video_metrics(self, duration: float, bytes_count: int, width: int, height: int) -> None:
        """Set video-related metrics."""
        self.metrics.video_duration = duration
        self.metrics.video_bytes = bytes_count
        self.metrics.video_width = width
        self.metrics.video_height = height
    
    def set_novelty_metrics(self, peaks_count: int, frames_count: int) -> None:
        """Set novelty detection metrics."""
        self.metrics.novelty_peaks_count = peaks_count
        self.metrics.novelty_frames_count = frames_count
    
    def set_processing_metrics(self, clips_generated: int, segments_built: int) -> None:
        """Set processing metrics."""
        self.metrics.clips_generated = clips_generated
        self.metrics.segments_built = segments_built
    
    def set_configuration_metrics(self, clips_requested: int, min_length: float, max_length: float, 
                                 with_motion: bool, align_to_beat: bool) -> None:
        """Set configuration metrics."""
        self.metrics.clips_requested = clips_requested
        self.metrics.min_clip_length = min_length
        self.metrics.max_clip_length = max_length
        self.metrics.with_motion = with_motion
        self.metrics.align_to_beat = align_to_beat
    
    def set_memory_peak(self, peak_mb: float) -> None:
        """Set peak memory usage."""
        self.metrics.memory_peak_mb = peak_mb
    
    def finish(self) -> AnalysisMetrics:
        """Finish metrics collection and return final metrics."""
        self.metrics.finish_total()
        logger.info(f"Analysis completed in {self.metrics.total_duration:.3f}s")
        return self.metrics
    
    def get_current_metrics(self) -> AnalysisMetrics:
        """Get current metrics (without finishing)."""
        return self.metrics


def format_prometheus_metrics(metrics: AnalysisMetrics) -> str:
    """
    Format metrics in Prometheus exposition format.
    
    Args:
        metrics: Analysis metrics
        
    Returns:
        Prometheus-formatted metrics string
    """
    lines = []
    
    # Job duration metrics
    lines.append(f"# HELP job_duration_seconds Duration of analysis job in seconds")
    lines.append(f"# TYPE job_duration_seconds counter")
    lines.append(f"job_duration_seconds{{stage=\"total\"}} {metrics.total_duration}")
    
    for stage in AnalysisStage:
        if stage != AnalysisStage.TOTAL:
            duration = metrics.get_stage_duration(stage)
            lines.append(f"job_duration_seconds{{stage=\"{stage.value}\"}} {duration}")
    
    # Novelty metrics
    lines.append(f"# HELP novelty_peaks_count Number of novelty peaks detected")
    lines.append(f"# TYPE novelty_peaks_count gauge")
    lines.append(f"novelty_peaks_count {metrics.novelty_peaks_count}")
    
    lines.append(f"# HELP novelty_frames_count Number of novelty frames processed")
    lines.append(f"# TYPE novelty_frames_count gauge")
    lines.append(f"novelty_frames_count {metrics.novelty_frames_count}")
    
    # Audio metrics
    lines.append(f"# HELP audio_duration_seconds Audio duration in seconds")
    lines.append(f"# TYPE audio_duration_seconds gauge")
    lines.append(f"audio_duration_seconds {metrics.audio_duration}")
    
    lines.append(f"# HELP audio_bytes Audio data size in bytes")
    lines.append(f"# TYPE audio_bytes gauge")
    lines.append(f"audio_bytes {metrics.audio_bytes}")
    
    # Video metrics
    lines.append(f"# HELP video_duration_seconds Video duration in seconds")
    lines.append(f"# TYPE video_duration_seconds gauge")
    lines.append(f"video_duration_seconds {metrics.video_duration}")
    
    lines.append(f"# HELP video_bytes Video file size in bytes")
    lines.append(f"# TYPE video_bytes gauge")
    lines.append(f"video_bytes {metrics.video_bytes}")
    
    # Processing metrics
    lines.append(f"# HELP clips_generated Number of clips generated")
    lines.append(f"# TYPE clips_generated gauge")
    lines.append(f"clips_generated {metrics.clips_generated}")
    
    lines.append(f"# HELP memory_peak_mb Peak memory usage in MB")
    lines.append(f"# TYPE memory_peak_mb gauge")
    lines.append(f"memory_peak_mb {metrics.memory_peak_mb}")
    
    # Configuration metrics
    lines.append(f"# HELP clips_requested Number of clips requested")
    lines.append(f"# TYPE clips_requested gauge")
    lines.append(f"clips_requested {metrics.clips_requested}")
    
    lines.append(f"# HELP with_motion_enabled Motion analysis enabled flag")
    lines.append(f"# TYPE with_motion_enabled gauge")
    lines.append(f"with_motion_enabled {1 if metrics.with_motion else 0}")
    
    lines.append(f"# HELP align_to_beat_enabled Beat alignment enabled flag")
    lines.append(f"# TYPE align_to_beat_enabled gauge")
    lines.append(f"align_to_beat_enabled {1 if metrics.align_to_beat else 0}")
    
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    """CLI for testing metrics."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Prometheus metrics")
    parser.add_argument("--format", choices=["json", "prometheus"], default="prometheus", 
                       help="Output format")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    # Create test metrics
    collector = MetricsCollector()
    
    # Simulate analysis stages
    collector.start_stage(AnalysisStage.AUDIO_EXTRACTION)
    time.sleep(0.1)  # Simulate work
    collector.finish_stage(AnalysisStage.AUDIO_EXTRACTION)
    
    collector.start_stage(AnalysisStage.NOVELTY_DETECTION)
    time.sleep(0.2)  # Simulate work
    collector.finish_stage(AnalysisStage.NOVELTY_DETECTION)
    
    # Set test metrics
    collector.set_audio_metrics(30.0, 22050, 1024000)
    collector.set_video_metrics(30.0, 2048000, 1920, 1080)
    collector.set_novelty_metrics(5, 1000)
    collector.set_processing_metrics(3, 5)
    collector.set_configuration_metrics(3, 15.0, 30.0, False, False)
    collector.set_memory_peak(150.5)
    
    # Finish and get metrics
    metrics = collector.finish()
    
    if args.format == "json":
        import json
        print(json.dumps(metrics.to_json_metrics(), indent=2))
    else:
        print(format_prometheus_metrics(metrics))
