# MVP Analyzer v0.2.0

AI-powered music video highlight extraction tool for creating short clips for social media platforms.

## 🚀 What's New in v0.2.0

This release introduces major new features including motion analysis, video export capabilities, and progress tracking for Server-Sent Events integration.

### ✨ Core Features

#### 🎵 Audio Processing
- **Audio Extraction**: High-quality audio extraction from video files using ffmpeg
- **Novelty Detection**: Advanced onset strength and spectral contrast analysis
- **Peak Picking**: Intelligent peak detection with minimum spacing and top-K selection
- **Seed Timestamps**: Support for manual timestamp input with local peak detection

#### 🎯 Beat Analysis
- **Beat Tracking**: Local BPM estimation and beat grid detection using librosa
- **Beat Quantization**: Automatic alignment of clip boundaries to beat/bar boundaries
- **Musical Intelligence**: Smart clip positioning based on musical structure

#### 🎬 Motion Analysis
- **Optical Flow**: Farnebäck optical flow for motion detection
- **Motion Scoring**: Motion magnitude calculation and median scoring
- **Score Combination**: Weighted combination with audio scores (60% audio + 40% motion)
- **Timeline Interpolation**: Motion scores interpolated to audio timeline

#### 🎥 Video Export
- **Multi-Format Export**: Original (16:9), Vertical (9:16), and Square (1:1) formats
- **Stream Copy**: Fast export using stream copy for compatible codecs
- **H264 Fallback**: Automatic transcoding to H264 when needed
- **Auto-Reframe**: HOG people detection for intelligent crop positioning
- **Crop & Scale**: Automatic crop and scale operations for format conversion

#### 📊 Output & Export
- **CSV Export**: Structured data export for further processing
- **JSON Export**: Rich metadata export with full analysis results
- **Video Clips**: Direct video clip export with format options
- **Schema Validation**: Comprehensive JSON schema validation for data integrity

#### 🔄 Progress Events
- **Real-time Progress**: JSON-formatted progress events for SSE integration
- **Stage Tracking**: Detailed stage tracking throughout analysis pipeline
- **Error Reporting**: Comprehensive error reporting and completion status

#### 🧪 Testing & Quality
- **Unit Tests**: Comprehensive test suite for all core components
- **Integration Tests**: End-to-end testing with real video files
- **Performance Tests**: Profiling and optimization validation
- **Test Coverage**: High test coverage across all modules

## 📋 Epic Coverage

### ✅ Completed (v0.1.0)
- **Epic A**: Base Analyzer Implementation (A1-A7)
  - A1: Project initialization with uv and basic structure
  - A2: Audio extraction with improved ffmpeg handling
  - A3: Novelty detection with onset strength and spectral contrast
  - A4: Peak picking with minimum spacing and top-K selection
  - A5: Seed timestamps parsing and local peak detection
  - A6: Pre-roll and segment building with min/max length
  - A7: Results output CSV + JSON contract
- **Epic B**: Beat Quantization Implementation (B1-B2)
  - B1: Local BPM and beat grid detection
  - B2: Clip start and duration quantization to beat boundaries
- **Epic F**: Testing Suite (F1-F3)
  - F1: Unit tests for signal processing, peak detection, and beat quantization
  - F2: Integration tests on short clips
  - F3: Performance tests and profiling
- **Epic E1**: JSON Schema Validation

### ✅ Completed (v0.2.0)
- **Epic C**: Motion Analysis (C1)
  - C1: Optical flow Farnebäck (3-4 fps) and mixing with audio score
- **Epic D**: Video Export (D1-D3)
  - D1: Original 16:9 (stream copy / fallback h264)
  - D2: Export 9:16 and 1:1 (crop+scale)
  - D3: Auto-reframe (HOG/pose) for vertical/square
- **Epic E2**: Progress Events (E2)
  - E2: Progress/events in stdout (for SSE)

### 🔮 Roadmap (Future Releases)

#### v0.3.0 - Advanced CLI & Integration
- **Epic E**: CLI Integration (E3)
  - E3: Cancellation and resource management
- **Epic G**: Observability (G1)
  - G1: Prometheus metrics implementation with CLI flag

#### v0.3.0 - Advanced CLI & Integration
- **Epic E**: CLI Integration (E2-E3)
  - E2: Progress/events in stdout (for SSE)
  - E3: Cancellation and resource management

#### v0.4.0 - Packaging & Deployment
- **Epic H**: Packaging (H1-H2)
  - H1: Dockerfile for analyzer
  - H2: CI: tests, linters, security

#### v0.5.0 - Experimental Features
- **Epic I**: Experiment (I1-I2)
  - I1: Dataset collection and A/B/C/D generation script
  - I2: Online user preference evaluation

## 🛠️ Installation

This project uses `uv` for dependency management:

```bash
# Clone repository
git clone https://github.com/dj-shorts/analyzer.git
cd analyzer

# Install dependencies
uv sync

# Run analyzer
uv run analyzer --help
```

## 🎯 Usage Examples

### Basic Analysis
```bash
# Analyze video and extract highlights
uv run analyzer video.mp4 --clips 6

# With beat alignment
uv run analyzer video.mp4 --clips 6 --align-to-beat

# With seed timestamps
uv run analyzer video.mp4 --clips 6 --seeds "10.5,25.3,45.1"
```

### Motion Analysis
```bash
# Include motion analysis
uv run analyzer video.mp4 --clips 6 --with-motion

# Motion analysis with beat alignment
uv run analyzer video.mp4 --clips 6 --with-motion --align-to-beat
```

### Video Export
```bash
# Export video clips (original format)
uv run analyzer video.mp4 --clips 6 --export-video

# Export in vertical format (9:16)
uv run analyzer video.mp4 --clips 6 --export-video --export-format vertical

# Export in square format (1:1)
uv run analyzer video.mp4 --clips 6 --export-video --export-format square

# Auto-reframe with people detection
uv run analyzer video.mp4 --clips 6 --export-video --export-format vertical --auto-reframe
```

### Progress Events
```bash
# Enable progress events for SSE integration
uv run analyzer video.mp4 --clips 6 --progress-events

# Combined features with progress tracking
uv run analyzer video.mp4 --clips 6 --with-motion --export-video --export-format vertical --progress-events
```

### Advanced Usage
```bash
# Custom clip parameters
uv run analyzer video.mp4 --clips 8 --min-len 20 --max-len 40

# Performance profiling
uv run analyzer video.mp4 --clips 6 --threads 4 --ram-limit 2GB

# Custom export directory
uv run analyzer video.mp4 --clips 6 --export-video --export-dir my_clips
```

## ⚙️ Configuration

The analyzer supports various configuration options:

### Core Analysis
- `--clips`: Number of clips to extract (default: 6)
- `--min-len`: Minimum clip length in seconds (default: 15.0)
- `--max-len`: Maximum clip length in seconds (default: 30.0)
- `--pre`: Pre-roll time in seconds (default: 10.0)
- `--spacing`: Minimum spacing between peaks in frames (default: 80)
- `--seeds`: Comma-separated seed timestamps (HH:MM:SS format)

### Feature Flags
- `--with-motion`: Include motion analysis (requires video input)
- `--align-to-beat`: Align clips to beat boundaries
- `--progress-events`: Enable progress events in stdout for SSE (default: True)

### Video Export
- `--export-video`: Export video clips
- `--export-dir`: Directory for exported video clips (default: clips)
- `--export-format`: Export format: original, vertical, or square (default: original)
- `--auto-reframe`: Enable auto-reframe with HOG people detection

### Output & Performance
- `--out-json`: Output JSON file path (default: highlights.json)
- `--out-csv`: Output CSV file path (default: highlights.csv)
- `--threads`: Number of threads to use (default: auto)
- `--ram-limit`: RAM limit (e.g., '2GB')
- `--verbose`: Enable verbose logging

## 📊 Output Formats

### CSV Output
Contains segment information in tabular format:
- `start`: Start time in seconds
- `end`: End time in seconds
- `length`: Segment length in seconds

### JSON Output
Contains detailed metadata and analysis results:
- Configuration parameters used
- Audio file metadata
- Motion analysis results (if enabled)
- Beat tracking data (if enabled)
- Summary statistics
- Complete segment information

### Video Clips
Exported video clips in various formats:
- **Original**: 16:9 aspect ratio with stream copy or H264 fallback
- **Vertical**: 9:16 aspect ratio with crop and scale
- **Square**: 1:1 aspect ratio with crop and scale
- **Auto-reframe**: Intelligent crop positioning based on people detection

### Progress Events
JSON-formatted events for Server-Sent Events integration:
- Real-time progress updates
- Stage tracking throughout analysis
- Error reporting and completion status

## 🧪 Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=analyzer

# Run specific test file
uv run pytest tests/test_analyzer.py

# Run integration tests
uv run pytest tests/test_integration_f2.py

# Run performance tests
uv run pytest tests/test_performance_f3.py
```

### Code Quality

```bash
# Format code
uv run ruff format analyzer tests

# Check code quality
uv run ruff check analyzer tests

# Type checking
uv run mypy analyzer
```

### JSON Schema Validation

```bash
# Validate JSON file
python -m src.analyzer.schema output.json

# Validate JSON and CSV
python -m src.analyzer.schema output.json --csv output.csv

# Verbose validation
python -m src.analyzer.schema output.json --verbose
```

## 🔧 Technical Specifications

- **Python**: 3.11+ support
- **Dependencies**: numpy, librosa, click, pydantic, rich, opencv-python-headless
- **Audio Processing**: ffmpeg integration with librosa
- **Motion Analysis**: OpenCV optical flow Farnebäck
- **People Detection**: OpenCV HOG descriptor
- **Video Export**: FFmpeg integration with stream copy and H264 transcoding
- **Beat Analysis**: librosa beat tracking and quantization
- **Testing**: pytest with comprehensive coverage

## 📈 Performance

- **Processing Speed**: Optimized for real-time analysis
- **Memory Usage**: Efficient memory management with configurable limits
- **Accuracy**: High-quality novelty detection and beat alignment
- **Reliability**: Comprehensive error handling and validation

## 🐛 Bug Reports & Support

Please report issues and feature requests on our [GitHub Issues](https://github.com/dj-shorts/analyzer/issues) page.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Ready for production use!** 🚀

**Total Issues Completed**: 18/24 (75% completion rate)  
**Epic Coverage**: A, B, C, D, E1, E2, F  
**Test Coverage**: Comprehensive unit, integration, and performance tests  
**Production Ready**: ✅ Yes  
**Repository Status**: ✅ Clean and optimized