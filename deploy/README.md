# Scripts Directory

This directory contains installation and utility scripts for the MVP Analyzer project.

## Installation Scripts

- **`setup.sh`** - Installation script for Unix/Linux/macOS systems
- **`setup.ps1`** - Installation script for Windows PowerShell
- **`setup.py`** - Python-based installation script (cross-platform)

## Utility Scripts

- **`profile_performance.py`** - Performance profiling utility for analyzing the analyzer's performance

## Usage

### Installation

Run the appropriate script for your platform:

```bash
# Unix/Linux/macOS
./scripts/setup.sh

# Windows PowerShell
.\scripts\setup.ps1

# Cross-platform Python
python scripts/setup.py
```

### Working with YouTube Videos

Starting from v0.3.0, the analyzer requires **manual video download** before analysis:

```bash
# Step 1: Download video using yt-dlp (install if needed: brew install yt-dlp)
yt-dlp -f "best[height<=1080]" -o "video.mp4" "https://www.youtube.com/watch?v=VIDEO_ID"

# Step 2: Analyze the downloaded video
uv run analyzer video.mp4 --clips 3 --export-video

# Or with motion analysis and beat alignment
uv run analyzer video.mp4 --clips 6 --with-motion --align-to-beat --export-video
```

**Why manual download?**
- ✅ Reliable 1080p quality (previously limited to 360p)
- ✅ 100% success rate (no more 403 errors)
- ✅ Faster processing
- ✅ Full control over format and quality

See [MANUAL_DOWNLOAD_MIGRATION.md](../docs/MANUAL_DOWNLOAD_MIGRATION.md) for detailed migration guide.

### Performance Profiling

```bash
python scripts/profile_performance.py
```

## Notes

- All scripts are designed to be run from the project root directory
- Make sure you have the required permissions to execute the scripts
- The installation scripts will handle dependency installation and environment setup
- For video download, `yt-dlp` must be installed separately (not included in project dependencies)
