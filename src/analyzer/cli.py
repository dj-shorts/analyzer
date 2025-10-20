"""
Command-line interface for MVP Analyzer.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler

from .core import Analyzer
from .config import Config

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )


@click.command()
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--clips", 
    "-k", 
    type=int, 
    default=6, 
    help="Number of clips to extract (default: 6)"
)
@click.option(
    "--min-len", 
    type=float, 
    default=15.0, 
    help="Minimum clip length in seconds (default: 15.0)"
)
@click.option(
    "--max-len", 
    type=float, 
    default=30.0, 
    help="Maximum clip length in seconds (default: 30.0)"
)
@click.option(
    "--pre", 
    type=float, 
    default=10.0, 
    help="Pre-roll time in seconds (default: 10.0)"
)
@click.option(
    "--spacing", 
    type=int, 
    default=80, 
    help="Minimum spacing between peaks in frames (default: 80)"
)
@click.option(
    "--with-motion", 
    is_flag=True, 
    help="Include motion analysis (requires video input)"
)
@click.option(
    "--align-to-beat", 
    is_flag=True, 
    help="Align clips to beat boundaries"
)
@click.option(
    "--seeds", 
    type=str, 
    help="Comma-separated seed timestamps (HH:MM:SS format)"
)
@click.option(
    "--out-json", 
    type=click.Path(path_type=Path), 
    default="highlights.json",
    help="Output JSON file path (default: highlights.json)"
)
@click.option(
    "--out-csv", 
    type=click.Path(path_type=Path), 
    default="highlights.csv",
    help="Output CSV file path (default: highlights.csv)"
)
@click.option(
    "--verbose", 
    "-v", 
    is_flag=True, 
    help="Enable verbose logging"
)
@click.option(
    "--threads", 
    type=int, 
    help="Number of threads to use (default: auto)"
)
@click.option(
    "--ram-limit", 
    type=str, 
    help="RAM limit (e.g., '2GB')"
)
@click.option(
    "--export-video",
    is_flag=True,
    help="Export video clips"
)
@click.option(
    "--export-dir",
    type=click.Path(path_type=Path),
    default="clips",
    help="Directory for exported video clips (default: clips)"
)
@click.option(
    "--export-format",
    type=click.Choice(["original", "vertical", "square"], case_sensitive=False),
    default="original",
    help="Export format: original (16:9), vertical (9:16), or square (1:1)"
)
@click.option(
    "--auto-reframe",
    is_flag=True,
    help="Enable auto-reframe with HOG people detection"
)
@click.option(
    "--progress-events",
    is_flag=True,
    help="Enable progress events in stdout for SSE"
)
@click.option(
    "--enable-object-tracking",
    is_flag=True,
    help="Enable dynamic object tracking for video export"
)
@click.option(
    "--tracking-smoothness",
    type=float,
    default=0.8,
    help="Tracking smoothness factor (0.0-1.0, default: 0.8)"
)
@click.option(
    "--tracking-confidence",
    type=float,
    default=0.5,
    help="Minimum confidence threshold for object detection (0.0-1.0, default: 0.5)"
)
@click.option(
    "--no-fallback-center",
    is_flag=True,
    help="Disable fallback to center crop when tracking fails"
)
def main(
    input: Path,
    clips: int,
    min_len: float,
    max_len: float,
    pre: float,
    spacing: int,
    with_motion: bool,
    align_to_beat: bool,
    seeds: Optional[str],
    out_json: Path,
    out_csv: Path,
    verbose: bool,
    threads: Optional[int],
    ram_limit: Optional[str],
    export_video: bool,
    export_dir: Path,
    export_format: str,
    auto_reframe: bool,
    progress_events: bool,
    enable_object_tracking: bool,
    tracking_smoothness: float,
    tracking_confidence: float,
    no_fallback_center: bool,
) -> None:
    """
    MVP Analyzer - Extract highlights from music videos.
    
    INPUT: Path to input video file (mp4, mov, etc.)
    """
    setup_logging(verbose)
    
    logger = logging.getLogger(__name__)
    
    try:
        # Parse seed timestamps if provided
        seed_timestamps = []
        if seeds:
            for seed in seeds.split(","):
                seed = seed.strip()
                # Convert HH:MM:SS to seconds
                parts = seed.split(":")
                if len(parts) == 3:
                    hours, minutes, seconds = map(int, parts)
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                    seed_timestamps.append(total_seconds)
                else:
                    logger.warning(f"Invalid seed format: {seed}. Use HH:MM:SS format.")
        
        # Create configuration
        config = Config(
            input_path=input,
            clips_count=clips,
            min_clip_length=min_len,
            max_clip_length=max_len,
            pre_roll=pre,
            peak_spacing=spacing,
            with_motion=with_motion,
            align_to_beat=align_to_beat,
            seed_timestamps=seed_timestamps,
            output_json=out_json,
            output_csv=out_csv,
            threads=threads,
            ram_limit=ram_limit,
            export_video=export_video,
            export_dir=export_dir,
            export_format=export_format.lower(),
            auto_reframe=auto_reframe,
            progress_events=progress_events,
            enable_object_tracking=enable_object_tracking,
            tracking_smoothness=tracking_smoothness,
            tracking_confidence_threshold=tracking_confidence,
            fallback_to_center=not no_fallback_center,
        )
        
        # Create and run analyzer
        analyzer = Analyzer(config)
        
        console.print(f"[bold green]Starting analysis of {input}[/bold green]")
        console.print(f"[blue]Configuration:[/blue]")
        console.print(f"  • Clips: {clips}")
        console.print(f"  • Length: {min_len}-{max_len}s")
        console.print(f"  • Pre-roll: {pre}s")
        console.print(f"  • Spacing: {spacing} frames")
        console.print(f"  • Motion analysis: {'Yes' if with_motion else 'No'}")
        console.print(f"  • Beat alignment: {'Yes' if align_to_beat else 'No'}")
        if seed_timestamps:
            console.print(f"  • Seeds: {len(seed_timestamps)} timestamps")
        if export_video:
            console.print(f"  • Video export: Yes ({export_format} format)")
            console.print(f"  • Export directory: {export_dir}")
            if auto_reframe:
                console.print(f"  • Auto-reframe: Yes")
            if enable_object_tracking:
                console.print(f"  • Object tracking: Yes")
                console.print(f"  • Tracking smoothness: {tracking_smoothness}")
                console.print(f"  • Tracking confidence: {tracking_confidence}")
        if progress_events:
            console.print(f"  • Progress events: Yes")
        
        # Run analysis
        results = analyzer.analyze()
        
        console.print(f"[bold green]✓ Analysis completed![/bold green]")
        console.print(f"[blue]Results saved to:[/blue]")
        console.print(f"  • JSON: {out_json}")
        console.print(f"  • CSV: {out_csv}")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
