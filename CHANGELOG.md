# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2025-01-24

### Added
- **Enhanced Testing**: Improved test configuration and reporting capabilities
- **Performance Optimizations**: Optimized audio and video processing algorithms
- **Test Coverage**: Comprehensive test suite with ~200 tests across multiple categories

### Changed
- **Version**: Updated from v0.4.0 to v0.4.1
- **README**: Updated with stability and performance improvements
- **Epic Coverage**: Added H4 (Performance Improvements) to completed epics

### Fixed
- **Bug Fixes**: Various stability improvements and bug fixes
- **Performance**: Optimized memory usage and processing speed

### Technical Details
- **Test Configuration**: Enhanced pytest configuration and fixtures
- **Test Categories**: Unit, integration, performance, and regression test categorization
- **Test Tags**: Audio, video, motion, beats, export, critical, and slow test tagging

### Documentation
- **Testing Guide**: Updated with enhanced testing instructions
- **README**: Added performance improvements information

## [0.4.0] - 2025-01-23

### Added
- **Docker Support**: Complete containerization with multi-stage builds
- **CI/CD Pipeline**: Automated testing, linting, and security scanning
- **Monitoring Stack**: Prometheus + Grafana integration for real-time monitoring
- **Security Scanning**: Bandit, Safety, and Trivy security scanning
- **Modern Packaging**: Python packaging with uv support
- **Project Structure**: Reorganized codebase with proper directory structure

### Changed
- **README**: Streamlined from 473 to 125 lines with wiki references
- **Documentation**: Moved detailed guides to GitHub wiki
- **Docker Commands**: Updated to use `python -m analyzer.cli`
- **CI/CD**: Automated workflows for testing and deployment

## [0.3.0] - 2025-01-22

### Added
- **Manual Video Download**: Users download videos using `yt-dlp` CLI before analysis
- **Better Quality**: 1080p+ video support (was limited to 360p)
- **100% Reliability**: No more download failures or 403 errors
- **Simpler Codebase**: Removed 400+ lines of download code and yt-dlp dependency

### Changed
- **Architecture**: Removed automatic video download functionality
- **CLI Interface**: Now accepts only local file paths
- **Quality**: Improved video quality support up to 1080p

## [0.2.0] - 2025-01-21

### Added
- **Motion Analysis**: Optical flow Farnebäck (3-4 fps) and mixing with audio score
- **Video Export**: Original 16:9 (stream copy / fallback h264)
- **Export Formats**: 9:16 and 1:1 (crop+scale)
- **Auto-reframe**: HOG/pose detection for vertical/square
- **Progress Events**: Progress/events in stdout (for SSE)

## [0.1.0] - 2025-01-20

### Added
- **Base Analyzer**: Core functionality implementation
- **Audio Processing**: Audio extraction with improved ffmpeg handling
- **Novelty Detection**: Onset strength and spectral contrast analysis
- **Peak Picking**: Minimum spacing and top-K selection
- **Seed Timestamps**: Parsing and local peak detection
- **Beat Quantization**: Local BPM and beat grid detection
- **Testing Suite**: Unit, integration, and performance tests
- **JSON Schema**: Validation for output data integrity

---

**Legend:**
- 🎯 **Major Changes**: Significant new features or improvements
- 🔧 **Technical Details**: Implementation specifics
- 📚 **Documentation**: Updates to guides and documentation
- 🐛 **Bug Fixes**: Issues resolved
- 🔒 **Security**: Security-related changes
- ⚡ **Performance**: Performance improvements
