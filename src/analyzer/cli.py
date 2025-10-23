"""
Command-line interface for MVP Analyzer.
"""

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler

from .config import Config
from .core import Analyzer

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@click.command()
@click.argument("video_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--clips", "-k", type=int, default=6, help="Number of clips to extract (default: 6)"
)
@click.option(
    "--min-len",
    type=float,
    default=15.0,
    help="Minimum clip length in seconds (default: 15.0)",
)
@click.option(
    "--max-len",
    type=float,
    default=30.0,
    help="Maximum clip length in seconds (default: 30.0)",
)
@click.option(
    "--pre", type=float, default=10.0, help="Pre-roll time in seconds (default: 10.0)"
)
@click.option(
    "--spacing",
    type=int,
    default=80,
    help="Minimum spacing between peaks in frames (default: 80)",
)
@click.option(
    "--with-motion", is_flag=True, help="Include motion analysis (requires video input)"
)
@click.option("--align-to-beat", is_flag=True, help="Align clips to beat boundaries")
@click.option(
    "--seeds", type=str, help="Comma-separated seed timestamps (HH:MM:SS format)"
)
@click.option(
    "--out-json",
    type=click.Path(path_type=Path),
    default="data/highlights.json",
    help="Output JSON file path (default: data/highlights.json)",
)
@click.option(
    "--out-csv",
    type=click.Path(path_type=Path),
    default="data/highlights.csv",
    help="Output CSV file path (default: data/highlights.csv)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--threads", type=int, help="Number of threads to use (default: auto)")
@click.option("--ram-limit", type=str, help="RAM limit (e.g., '2GB')")
@click.option("--export-video", is_flag=True, help="Export video clips")
@click.option(
    "--export-dir",
    type=click.Path(path_type=Path),
    default="clips",
    help="Directory for exported video clips (default: clips)",
)
@click.option(
    "--export-format",
    type=click.Choice(["original", "vertical", "square"]),
    default="original",
    help="Export format: original (16:9), vertical (9:16), square (1:1) (default: original)",
)
@click.option(
    "--auto-reframe",
    is_flag=True,
    help="Enable auto-reframe using people detection for vertical/square formats",
)
@click.option(
    "--metrics",
    type=click.Path(path_type=Path),
    help="Export Prometheus metrics to file",
)
@click.option(
    "--progress-events", is_flag=True, help="Enable progress events in stdout for SSE"
)
def main(
    video_file: Path,
    clips: int,
    min_len: float,
    max_len: float,
    pre: float,
    spacing: int,
    with_motion: bool,
    align_to_beat: bool,
    seeds: str | None,
    out_json: Path,
    out_csv: Path,
    verbose: bool,
    threads: int | None,
    ram_limit: str | None,
    export_video: bool,
    export_dir: Path,
    export_format: str,
    auto_reframe: bool,
    metrics: Path | None,
    progress_events: bool,
) -> None:
    """
    MVP Analyzer - Extract highlights from music videos.

    VIDEO_FILE: Path to input video file (mp4, mov, webm, etc.)

    For YouTube videos, download manually first:
        yt-dlp -f "best[height<=1080]" -o "video.mp4" "https://www.youtube.com/watch?v=VIDEO_ID"
    Then analyze the downloaded file:
        analyzer video.mp4 --clips 3 --export-video
    """
    setup_logging(verbose)

    logger = logging.getLogger(__name__)

    try:
        video_path = video_file

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
            progress_events=progress_events,
        )

        # Create and run analyzer
        analyzer = Analyzer(config)

        console.print(f"[bold green]Starting analysis of {video_path}[/bold green]")
        console.print("[blue]Configuration:[/blue]")
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

        console.print("[bold green]✓ Analysis completed![/bold green]")
        console.print("[blue]Results saved to:[/blue]")
        console.print(f"  • JSON: {out_json}")
        console.print(f"  • CSV: {out_csv}")

        # Display video export results if enabled
        if export_video and "video_export" in results:
            video_export = results["video_export"]
            console.print("[blue]Video clips exported:[/blue]")
            console.print(f"  • Total clips: {video_export['total_clips']}")
            console.print(f"  • Exported: {video_export['exported_clips']}")
            console.print(f"  • Failed: {video_export['failed_clips']}")
            console.print(f"  • Directory: {export_dir}")
            console.print(f"  • Format: {export_format}")

            if video_export["failed_clips"] > 0:
                console.print(
                    "[yellow]⚠️  Some clips failed to export. Check logs for details.[/yellow]"
                )

        # Export metrics if requested
        if metrics:
            from .metrics import (
                AnalysisMetrics,
                AnalysisStage,
                StageTiming,
                format_prometheus_metrics,
            )

            metrics_data = results.get("metrics", {})
            if metrics_data:
                # Convert JSON metrics back to AnalysisMetrics for formatting
                analysis_metrics = AnalysisMetrics()

                # Set timing data
                timings = metrics_data.get("timings", {})
                analysis_metrics.total_duration = timings.get(
                    "total_duration_seconds", 0.0
                )

                # Reconstruct stage timings from JSON data
                stages_data = timings.get("stages", {})
                for stage_name, stage_data in stages_data.items():
                    try:
                        stage = AnalysisStage(stage_name)
                        duration = stage_data.get("duration_seconds", 0.0)
                        start_time = stage_data.get("start_time", 0.0)
                        end_time = stage_data.get("end_time")

                        # If end_time is not provided, calculate it from start_time + duration
                        if end_time is None and start_time is not None:
                            end_time = start_time + duration
                        elif end_time is None:
                            end_time = duration  # Fallback if start_time is also None

                        # Create StageTiming object
                        stage_timing = StageTiming(
                            stage=stage,
                            start_time=start_time,
                            end_time=end_time,
                            duration=duration,
                        )
                        analysis_metrics.stage_timings[stage] = stage_timing
                    except ValueError:
                        # Skip unknown stages
                        continue

                # Set other metrics
                novelty = metrics_data.get("novelty", {})
                analysis_metrics.novelty_peaks_count = novelty.get("peaks_count", 0)
                analysis_metrics.novelty_frames_count = novelty.get("frames_count", 0)

                audio = metrics_data.get("audio", {})
                analysis_metrics.audio_duration = audio.get("duration_seconds", 0.0)
                analysis_metrics.audio_sample_rate = audio.get("sample_rate_hz", 0)
                analysis_metrics.audio_bytes = audio.get("bytes", 0)

                # Set video metrics
                video = metrics_data.get("video", {})
                analysis_metrics.video_duration = video.get("duration_seconds", 0.0)
                analysis_metrics.video_bytes = video.get("bytes", 0)
                analysis_metrics.video_width = video.get("width_pixels", 0)
                analysis_metrics.video_height = video.get("height_pixels", 0)

                processing = metrics_data.get("processing", {})
                analysis_metrics.clips_generated = processing.get("clips_generated", 0)
                analysis_metrics.segments_built = processing.get("segments_built", 0)
                analysis_metrics.memory_peak_mb = processing.get("memory_peak_mb", 0.0)

                configuration = metrics_data.get("configuration", {})
                analysis_metrics.clips_requested = configuration.get(
                    "clips_requested", 0
                )
                analysis_metrics.min_clip_length = configuration.get(
                    "min_clip_length_seconds", 0.0
                )
                analysis_metrics.max_clip_length = configuration.get(
                    "max_clip_length_seconds", 0.0
                )
                analysis_metrics.with_motion = configuration.get("with_motion", False)
                analysis_metrics.align_to_beat = configuration.get(
                    "align_to_beat", False
                )

                # Write Prometheus metrics
                prometheus_metrics = format_prometheus_metrics(analysis_metrics)
                with open(metrics, "w") as f:
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
