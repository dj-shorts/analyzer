# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2025-01-24

### Added
- **TestSprite Integration**: Advanced test reporting platform integration
- **Test Analytics**: Historical tracking, flaky test detection, and performance metrics
- **Enhanced Test Configuration**: Comprehensive test suite with ~200 tests across multiple categories
- **TestSprite Configuration**: YAML configuration file for test reporting settings
- **Test Metadata Support**: Tags, priority, and requirements tracking for tests
- **Artifact Upload**: Screenshots, videos, and logs attachment to test reports

### Changed
- **Version**: Updated from v0.4.0 to v0.4.1
- **Dependencies**: Added testsprite>=1.0.0,<2.0.0
- **README**: Updated with TestSprite integration information
- **Epic Coverage**: Added H4 (TestSprite Integration) to completed epics

### Technical Details
- **TestSprite SDK**: Integrated with pytest hooks for automatic test reporting
- **Configuration**: Added testsprite.yml for project-specific settings
- **Test Categories**: Unit, integration, performance, and regression test categorization
- **Test Tags**: Audio, video, motion, beats, export, critical, and slow test tagging
- **Reporting**: Automatic upload of test results, screenshots, and artifacts

### Documentation
- **TestSprite Guide**: Comprehensive documentation in wiki
- **Testing Guide**: Updated with TestSprite integration instructions
- **README**: Added TestSprite information to development section

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
