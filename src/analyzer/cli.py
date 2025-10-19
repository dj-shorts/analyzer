"""
Command-line interface for MVP Analyzer.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.logging import RichHandler

from .core import Analyzer
from .config import Config

console = Console()


def _parse_seed_timestamps(seeds: str) -> List[float]:
    """
    Parse seed timestamps from string format.
    
    Args:
        seeds: Comma-separated seed timestamps in HH:MM:SS format
        
    Returns:
        List of timestamps in seconds
        
    Raises:
        ValueError: If seed format is invalid
    """
    seed_timestamps = []
    
    for seed in seeds.split(","):
        seed = seed.strip()
        if not seed:
            continue
            
        try:
            # Parse HH:MM:SS format
            parts = seed.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = parts
                hours = int(hours)
                minutes = int(minutes)
                seconds = float(seconds)  # Allow fractional seconds
                
                # Validate ranges
                if not (0 <= hours < 24):
                    raise ValueError(f"Hours must be 0-23, got {hours}")
                if not (0 <= minutes < 60):
                    raise ValueError(f"Minutes must be 0-59, got {minutes}")
                if not (0 <= seconds < 60):
                    raise ValueError(f"Seconds must be 0-59.999..., got {seconds}")
                
                total_seconds = hours * 3600 + minutes * 60 + seconds
                seed_timestamps.append(total_seconds)
                
            elif len(parts) == 2:
                # Allow MM:SS format
                minutes, seconds = parts
                minutes = int(minutes)
                seconds = float(seconds)
                
                if not (0 <= minutes < 60):
                    raise ValueError(f"Minutes must be 0-59, got {minutes}")
                if not (0 <= seconds < 60):
                    raise ValueError(f"Seconds must be 0-59.999..., got {seconds}")
                
                total_seconds = minutes * 60 + seconds
                seed_timestamps.append(total_seconds)
                
            else:
                # Try to parse as raw seconds
                try:
                    total_seconds = float(seed)
                    if total_seconds < 0:
                        raise ValueError(f"Timestamp must be positive, got {total_seconds}")
                    seed_timestamps.append(total_seconds)
                except ValueError:
                    raise ValueError(f"Invalid seed format: '{seed}'. Use HH:MM:SS, MM:SS, or seconds format.")
                    
        except ValueError as e:
            raise ValueError(f"Invalid seed timestamp '{seed}': {e}")
    
    # Sort timestamps
    seed_timestamps.sort()
    
    return seed_timestamps


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
            try:
                seed_timestamps = _parse_seed_timestamps(seeds)
                console.print(f"[green]Parsed {len(seed_timestamps)} seed timestamps: {[f'{s:.1f}s' for s in seed_timestamps]}[/green]")
            except ValueError as e:
                console.print(f"[red]Error parsing seed timestamps: {e}[/red]")
                sys.exit(1)
        
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
