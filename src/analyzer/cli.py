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
@click.argument("input", type=str)
@click.option(
    "--download-dir",
    type=click.Path(path_type=Path),
    default="downloads",
    help="Directory for downloaded videos (default: downloads)"
)
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
    type=click.Choice(["original", "vertical", "square"]),
    default="original",
    help="Export format: original (16:9), vertical (9:16), square (1:1) (default: original)"
)
@click.option(
    "--auto-reframe",
    is_flag=True,
    help="Enable auto-reframe using people detection for vertical/square formats"
)
@click.option(
    "--metrics", 
    type=click.Path(path_type=Path), 
    help="Export Prometheus metrics to file"
)
def main(
    input: str,
    download_dir: Path,
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
    metrics: Optional[Path],
) -> None:
    """
    MVP Analyzer - Extract highlights from music videos.
    
    INPUT: Path to input video file (mp4, mov, etc.) or URL (YouTube, Google Drive, etc.)
    """
    setup_logging(verbose)
    
    logger = logging.getLogger(__name__)
    
    try:
        # Determine if input is a URL or file path
        input_path = Path(input)
        video_path = None
        
        if input.startswith(('http://', 'https://')):
            # Input is a URL - download the video
            from .video_downloader import VideoDownloader, is_video_url
            
            if not is_video_url(input):
                console.print(f"[red]Error: Unsupported video URL: {input}[/red]")
                console.print("[yellow]Supported platforms: YouTube, Vimeo, Google Drive, OneDrive, Dropbox, direct video links[/yellow]")
                sys.exit(1)
            
            console.print(f"[blue]Downloading video from: {input}[/blue]")
            downloader = VideoDownloader(download_dir)
            
            # Generate output filename based on URL
            output_filename = f"downloaded_video_{hash(input) % 10000}.mp4"
            output_path = download_dir / output_filename
            
            download_result = downloader.download_video(input, output_path)
            
            if not download_result["success"]:
                console.print(f"[red]Download failed: {download_result['error']}[/red]")
                sys.exit(1)
            
            video_path = download_result["file_path"]
            console.print(f"[green]✓ Video downloaded: {video_path}[/green]")
            console.print(f"[blue]Title: {download_result['title']}[/blue]")
            console.print(f"[blue]Duration: {download_result['duration']}s[/blue]")
            
        elif input_path.exists():
            # Input is a file path
            video_path = input_path
        else:
            console.print(f"[red]Error: File not found: {input}[/red]")
            console.print("[yellow]Provide either a valid file path or a supported video URL[/yellow]")
            sys.exit(1)
        
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
            input_path=video_path,
            clips_count=clips,
            min_clip_length=min_len,
            max_clip_length=max_len,
            pre_roll=pre,
            peak_spacing=spacing,
            with_motion=with_motion,
            align_to_beat=align_to_beat,
            export_video=export_video,
            export_dir=export_dir,
            export_format=export_format,
            auto_reframe=auto_reframe,
            seed_timestamps=seed_timestamps,
            output_json=out_json,
            output_csv=out_csv,
            threads=threads,
            ram_limit=ram_limit,
        )
        
        # Create and run analyzer
        analyzer = Analyzer(config)
        
        console.print(f"[bold green]Starting analysis of {video_path}[/bold green]")
        console.print(f"[blue]Configuration:[/blue]")
        console.print(f"  • Clips: {clips}")
        console.print(f"  • Length: {min_len}-{max_len}s")
        console.print(f"  • Pre-roll: {pre}s")
        console.print(f"  • Spacing: {spacing} frames")
        console.print(f"  • Motion analysis: {'Yes' if with_motion else 'No'}")
        console.print(f"  • Beat alignment: {'Yes' if align_to_beat else 'No'}")
        console.print(f"  • Video export: {'Yes' if export_video else 'No'}")
        if export_video:
            console.print(f"  • Export directory: {export_dir}")
            console.print(f"  • Export format: {export_format}")
            console.print(f"  • Auto-reframe: {'Yes' if auto_reframe else 'No'}")
        if seed_timestamps:
            console.print(f"  • Seeds: {len(seed_timestamps)} timestamps")
        
        # Run analysis
        results = analyzer.analyze()
        
        console.print(f"[bold green]✓ Analysis completed![/bold green]")
        console.print(f"[blue]Results saved to:[/blue]")
        console.print(f"  • JSON: {out_json}")
        console.print(f"  • CSV: {out_csv}")
        
        # Display video export results if enabled
        if export_video and "video_export" in results:
            video_export = results["video_export"]
            console.print(f"[blue]Video clips exported:[/blue]")
            console.print(f"  • Total clips: {video_export['total_clips']}")
            console.print(f"  • Exported: {video_export['exported_clips']}")
            console.print(f"  • Failed: {video_export['failed_clips']}")
            console.print(f"  • Directory: {export_dir}")
            console.print(f"  • Format: {export_format}")
            
            if video_export['failed_clips'] > 0:
                console.print(f"[yellow]⚠️  Some clips failed to export. Check logs for details.[/yellow]")
        
        # Export metrics if requested
        if metrics:
            from .metrics import format_prometheus_metrics
            metrics_data = results.get("metrics", {})
            if metrics_data:
                # Convert JSON metrics back to AnalysisMetrics for formatting
                from .metrics import AnalysisMetrics, AnalysisStage
                analysis_metrics = AnalysisMetrics()
                
                # Set timing data
                timings = metrics_data.get("timings", {})
                analysis_metrics.total_duration = timings.get("total_duration_seconds", 0.0)
                
                # Set other metrics
                novelty = metrics_data.get("novelty", {})
                analysis_metrics.novelty_peaks_count = novelty.get("peaks_count", 0)
                analysis_metrics.novelty_frames_count = novelty.get("frames_count", 0)
                
                audio = metrics_data.get("audio", {})
                analysis_metrics.audio_duration = audio.get("duration_seconds", 0.0)
                analysis_metrics.audio_sample_rate = audio.get("sample_rate_hz", 0)
                analysis_metrics.audio_bytes = audio.get("bytes", 0)
                
                processing = metrics_data.get("processing", {})
                analysis_metrics.clips_generated = processing.get("clips_generated", 0)
                analysis_metrics.segments_built = processing.get("segments_built", 0)
                analysis_metrics.memory_peak_mb = processing.get("memory_peak_mb", 0.0)
                
                configuration = metrics_data.get("configuration", {})
                analysis_metrics.clips_requested = configuration.get("clips_requested", 0)
                analysis_metrics.min_clip_length = configuration.get("min_clip_length_seconds", 0.0)
                analysis_metrics.max_clip_length = configuration.get("max_clip_length_seconds", 0.0)
                analysis_metrics.with_motion = configuration.get("with_motion", False)
                analysis_metrics.align_to_beat = configuration.get("align_to_beat", False)
                
                # Write Prometheus metrics
                prometheus_metrics = format_prometheus_metrics(analysis_metrics)
                with open(metrics, 'w') as f:
                    f.write(prometheus_metrics)
                
                console.print(f"  • Metrics: {metrics}")
                logger.info(f"Prometheus metrics exported to {metrics}")
        
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
