# Testing Guide for MVP Analyzer

## Issue A1 - Project Initialization ✅ COMPLETED

### What was implemented:
- ✅ Complete uv project initialization with pyproject.toml
- ✅ Modular analyzer package structure (core, audio, novelty, peaks, segments, export)
- ✅ CLI interface with Click and Rich for enhanced UX
- ✅ Configuration validation with Pydantic v2
- ✅ Comprehensive test suite with pytest (12/12 tests passing)
- ✅ Basic audio extraction using ffmpeg
- ✅ Simple energy-based novelty detection (temporary implementation)
- ✅ Peak detection with spacing constraints and top-K selection
- ✅ Seed timestamp support for manual peak specification
- ✅ Segment building with configurable length and pre-roll
- ✅ Export results to both CSV and JSON formats with metadata

### How to test locally:

#### 1. Setup Environment
```bash
cd /Users/terryberk/git/djshorts
uv sync
```

#### 2. Run Tests
```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=analyzer

# Run specific test file
uv run pytest tests/test_analyzer.py -v
```

#### 3. Test CLI Interface
```bash
# Show help
uv run analyzer --help

# Test with sample video
uv run analyzer test_video.mp4 --clips 3 --verbose

# Test with custom parameters
uv run analyzer test_video.mp4 --clips 5 --min-len 20 --max-len 45 --seeds "00:01:00,00:02:30"
```

#### 4. Verify Output Files
```bash
# Check CSV output
cat highlights.csv

# Check JSON output
head -20 highlights.json

# Verify file structure
ls -la src/analyzer/
```

### Test Results:
- ✅ **12/12 tests passing**
- ✅ **CLI working correctly**
- ✅ **Audio extraction successful** (125.95s test video processed)
- ✅ **Peak detection working** (3 peaks found with proper spacing)
- ✅ **Segment building functional** (3 segments created with correct lengths)
- ✅ **Export formats working** (CSV and JSON generated with metadata)

### Dependencies Status:
- ✅ **uv project setup** - Complete with lockfile
- ✅ **Core dependencies** - numpy, scipy, click, pydantic, rich
- ⏳ **librosa** - Will be added in Issue A2 (temporary energy-based implementation used)
- ⏳ **soundfile** - Will be added in Issue A2 (temporary wave implementation used)
- ⏳ **opencv-python-headless** - Will be added in Issue C1

### Next Steps:
- **Issue A2**: Audio extraction with librosa integration
- **Issue A3**: Proper onset strength and spectral contrast implementation
- **Issue A4**: Enhanced peak picking algorithms
- **Issue A5**: Seed timestamp parsing and local peak detection
- **Issue A6**: Pre-roll and segment building improvements
- **Issue A7**: Final result export contract

### Performance Notes:
- Test video (125.95s) processed in ~2 seconds
- Memory usage: Minimal (basic numpy operations)
- CPU usage: Low (simple energy-based analysis)

### Known Limitations:
1. **Temporary audio loading**: Using wave module instead of librosa/soundfile
2. **Simple novelty detection**: Energy-based instead of proper onset strength + spectral contrast
3. **No motion analysis**: Feature not implemented yet (Issue C1)
4. **No beat alignment**: Feature not implemented yet (Issue B1)

### Validation Checklist:
- [x] `uv.lock` file present with fixed version pins
- [x] `analyzer --help` outputs complete argument list
- [x] Logging works in stdout with INFO/DEBUG levels
- [x] Project structure follows best practices
- [x] All tests pass
- [x] CLI interface functional
- [x] Basic analysis pipeline working
- [x] Export formats correct
