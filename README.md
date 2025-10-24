<div align="center">
  <img src="assets/logo.svg" alt="DJ Shorts Analyzer Logo" width="120" height="120">
  
  # DJ Shorts Analyzer
  
  AI-powered music video highlight extraction tool for creating short clips for social media platforms.
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
  [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
  [![Release](https://img.shields.io/github/v/release/dj-shorts/analyzer)](https://github.com/dj-shorts/analyzer/releases)
  [![CI](https://github.com/dj-shorts/analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/dj-shorts/analyzer/actions/workflows/ci.yml)
  [![Security](https://github.com/dj-shorts/analyzer/actions/workflows/security.yml/badge.svg)](https://github.com/dj-shorts/analyzer/actions/workflows/security.yml)
  [![Docker](https://github.com/dj-shorts/analyzer/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/dj-shorts/analyzer/actions/workflows/docker-publish.yml)
  
</div>

## 🚀 What's New in v0.4.1

This release focuses on **stability and performance improvements**.

### 🎯 Major Changes in v0.4.1
- **🔧 Enhanced Testing**: Improved test configuration and reporting capabilities
- **📈 Test Coverage**: Comprehensive test suite with ~200 tests across multiple categories
- **🚀 Performance**: Optimized audio and video processing algorithms
- **🐛 Bug Fixes**: Various stability improvements and bug fixes

### 🎯 Previous Changes in v0.4.0
- **🐳 Docker Support**: Complete containerization with multi-stage builds
- **🔄 CI/CD Pipeline**: Automated testing, linting, and security scanning
- **📊 Monitoring Stack**: Prometheus + Grafana integration for real-time monitoring
- **🔒 Security**: Bandit, Safety, and Trivy security scanning
- **📦 Package Management**: Modern Python packaging with uv support

## 🚀 Quick Start

### Docker (Recommended)
```bash
# Pull and run
docker pull ghcr.io/dj-shorts/analyzer:latest
docker run --rm -v $(pwd)/data:/data ghcr.io/dj-shorts/analyzer:latest python -m analyzer.cli /data/video.mp4 --clips 3 --out-json /data/highlights.json --out-csv /data/highlights.csv
```

### Local Installation
```bash
git clone https://github.com/dj-shorts/analyzer.git
cd analyzer
uv sync
uv run analyzer --help
```

## ✨ Key Features

- **🎵 Audio Analysis**: Novelty detection, beat tracking, and peak picking
- **🎬 Motion Analysis**: Optical flow for motion-based highlight detection  
- **🎥 Video Export**: Multi-format export (original, vertical, square) with object tracking
- **📊 Rich Output**: JSON/CSV export with comprehensive metadata
- **🐳 Docker Ready**: Complete containerization with monitoring stack
- **🔄 CI/CD**: Automated testing, security scanning, and deployment

## 📚 Documentation

**📖 [Complete Documentation Wiki](https://github.com/dj-shorts/analyzer/wiki)**

### Quick Links
- **[Setup Guide](https://github.com/dj-shorts/analyzer/wiki/Setup-Guide)** - Installation and configuration
- **[Docker Guide](https://github.com/dj-shorts/analyzer/wiki/Docker-Guide)** - Container usage and deployment
- **[Monitoring Setup](https://github.com/dj-shorts/analyzer/wiki/Monitoring-Setup)** - Prometheus + Grafana stack
- **[Testing Guide](https://github.com/dj-shorts/analyzer/wiki/Testing-Guide)** - Running tests and quality assurance
- **[CI/CD Pipeline](https://github.com/dj-shorts/analyzer/wiki/CI-CD-Pipeline)** - Automated workflows

## 🎯 Usage Examples

### Basic Analysis
```bash
# Extract 6 highlights
uv run analyzer video.mp4 --clips 6

# With beat alignment and motion analysis
uv run analyzer video.mp4 --clips 6 --align-to-beat --with-motion

# Export video clips in vertical format
uv run analyzer video.mp4 --clips 6 --export-video --export-format vertical
```

### Object Tracking
```bash
# Keep subject centered in vertical clips
uv run analyzer video.mp4 --clips 6 --export-video --export-format vertical \
  --enable-object-tracking --tracking-smoothness 0.8
```

## 📊 Output Formats

- **CSV**: Tabular segment data (start, end, length)
- **JSON**: Rich metadata with analysis results and configuration
- **Video Clips**: Exported clips in original, vertical, or square formats

## 🧪 Development

```bash
# Run tests
uv run pytest

# Code quality
uv run ruff format analyzer tests
uv run ruff check analyzer tests

# Type checking
uv run mypy analyzer
```

## 🔧 Technical Stack

- **Python 3.11+** with uv package management
- **Audio**: librosa + ffmpeg integration
- **Motion**: OpenCV optical flow
- **Video**: FFmpeg with stream copy and H264 transcoding
- **Containerization**: Docker with multi-stage builds
- **Monitoring**: Prometheus + Grafana
- **CI/CD**: GitHub Actions with security scanning

## 📈 Project Status

- **Version**: v0.4.1
- **Epic Coverage**: A, B, C, D, E1, E2, E3, F, G1, H1, H2, H3, H4
- **Test Coverage**: Comprehensive unit, integration, and performance tests
- **Production Ready**: ✅ Yes
- **Docker Support**: ✅ Complete containerization
- **CI/CD Pipeline**: ✅ Automated testing and security scanning

## 🐛 Support

- **Issues**: [GitHub Issues](https://github.com/dj-shorts/analyzer/issues)
- **Releases**: [GitHub Releases](https://github.com/dj-shorts/analyzer/releases)
- **Documentation**: [Wiki](https://github.com/dj-shorts/analyzer/wiki)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Ready for production use!** 🚀