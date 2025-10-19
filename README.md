# MVP Analyzer

AI-powered music video highlight extraction tool for creating short clips for social media platforms.

## Features

- **Audio Analysis**: Extracts audio from video files and analyzes novelty using onset strength and spectral contrast
- **Peak Detection**: Finds interesting moments using advanced peak detection algorithms
- **Segment Building**: Creates optimized segments with configurable length and pre-roll
- **Multiple Export Formats**: Exports results to both CSV and JSON formats
- **Seed Support**: Allows manual specification of interesting timestamps
- **Beat Alignment**: Optional alignment to musical beat boundaries

## Installation

This project uses `uv` for dependency management:

```bash
# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

## Usage

```bash
# Basic usage
analyzer input_video.mp4

# With custom parameters
analyzer input_video.mp4 --clips 8 --min-len 20 --max-len 45 --seeds "01:30:00,03:45:00"

# With motion analysis (requires video input)
analyzer input_video.mp4 --with-motion

# Enable beat alignment
analyzer input_video.mp4 --align-to-beat
```

## Configuration

The analyzer supports various configuration options:

- `--clips`: Number of clips to extract (default: 6)
- `--min-len`: Minimum clip length in seconds (default: 15.0)
- `--max-len`: Maximum clip length in seconds (default: 30.0)
- `--pre`: Pre-roll time in seconds (default: 10.0)
- `--spacing`: Minimum spacing between peaks in frames (default: 80)
- `--with-motion`: Include motion analysis (requires video input)
- `--align-to-beat`: Align clips to beat boundaries
- `--seeds`: Comma-separated seed timestamps (HH:MM:SS format)
- `--out-json`: Output JSON file path (default: highlights.json)
- `--out-csv`: Output CSV file path (default: highlights.csv)

## Output Formats

### CSV Output
Contains segment information in tabular format:
- `clip_id`: Unique identifier for each clip
- `start`: Start time in seconds
- `end`: End time in seconds
- `center`: Center time of the segment
- `score`: Novelty score (0-1)
- `seed_based`: Whether segment was based on seed timestamp
- `aligned`: Whether segment is aligned to beat boundaries
- `length`: Segment length in seconds

### JSON Output
Contains detailed metadata and analysis results:
- Configuration parameters used
- Audio file metadata
- Summary statistics
- Complete segment information

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=analyzer

# Run specific test file
uv run pytest tests/test_analyzer.py
```

### Code Quality

```bash
# Format code
uv run black analyzer tests

# Lint code
uv run ruff check analyzer tests

# Type checking
uv run mypy analyzer
```

## Requirements

- Python 3.11+
- ffmpeg (for audio extraction)
- librosa (for audio analysis)
- soundfile (for audio file handling)
- numpy (for numerical computations)
- opencv-python-headless (for motion analysis)
- click (for CLI interface)
- pydantic (for configuration validation)
- rich (for enhanced console output)

## License

MIT License
