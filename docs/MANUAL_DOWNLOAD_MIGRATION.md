# Migration to Manual Video Download (v0.3.0)

## 📌 Summary

Starting from version 0.3.0, the analyzer **no longer supports automatic video downloads** from YouTube or other platforms. Instead, users must **manually download videos** using `yt-dlp` CLI before analysis.

## ❓ Why This Change?

After extensive testing and research, we discovered fundamental limitations when calling `yt-dlp` from Python:

### The Problem with Python Subprocess

When `yt-dlp` is called via Python's `subprocess.run()`:
- ❌ **nsig extraction fails** - YouTube's signature extraction doesn't work in non-TTY environments
- ❌ **403 Forbidden errors** - Many high-quality formats become unavailable
- ❌ **Unreliable downloads** - Frequent fragment failures and timeouts
- ❌ **Limited to 360p** - Only Android client workarounds worked, providing low quality

### The Solution: Manual CLI Download

When `yt-dlp` runs directly in terminal:
- ✅ **Works reliably** - No nsig extraction issues
- ✅ **High quality available** - 1080p and higher without restrictions
- ✅ **Full format control** - Choose exact format and quality
- ✅ **Better performance** - Direct CLI is faster than Python wrapper
- ✅ **Simpler architecture** - Less code, fewer dependencies

## 🚀 Migration Guide

### Before (v0.2.0)

```bash
# Old way - automatic download (removed in v0.3.0)
uv run analyzer "https://www.youtube.com/watch?v=VIDEO_ID" --clips 6
```

### After (v0.3.0)

```bash
# Step 1: Download video manually using yt-dlp
yt-dlp -f "best[height<=1080]" -o "video.mp4" "https://www.youtube.com/watch?v=VIDEO_ID"

# Step 2: Analyze downloaded file
uv run analyzer video.mp4 --clips 6 --export-video
```

## 📖 Download Quality Options

### Recommended: 1080p (Best Quality/Size Balance)
```bash
yt-dlp -f "best[height<=1080]" -o "video.mp4" "https://www.youtube.com/watch?v=VIDEO_ID"
```

### 720p (Smaller Size)
```bash
yt-dlp -f "best[height<=720]" -o "video.mp4" "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Best Available Quality
```bash
yt-dlp -o "video.mp4" "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Specific Format (Advanced)
```bash
# List all available formats
yt-dlp -F "https://www.youtube.com/watch?v=VIDEO_ID"

# Download specific format
yt-dlp -f 96 -o "video.mp4" "https://www.youtube.com/watch?v=VIDEO_ID"
```

## 🔧 What Changed in the Code

### Removed
- ✂️ `src/analyzer/video_downloader.py` - entire video download module
- ✂️ `tests/test_video_downloader.py` - related tests
- ✂️ `docs/VIDEO_DOWNLOAD_QUALITY.md` - download quality documentation
- ✂️ `yt-dlp` dependency from `pyproject.toml`

### Modified
- 📝 `src/analyzer/cli.py` - CLI now requires local file path only
  - Removed `--download-dir` option
  - Changed `input` argument to `video_file` with `exists=True` validation
  - Updated help text with manual download instructions
- 📝 `README.md` - Added "Downloading YouTube Videos" section with examples

### CLI Changes
```diff
- @click.argument("input", type=str)
+ @click.argument("video_file", type=click.Path(exists=True, path_type=Path))

- @click.option("--download-dir", ...)  # Removed

- def main(input: str, download_dir: Path, ...):
+ def main(video_file: Path, ...):
```

## 📊 Benefits

| Aspect | Old (v0.2.0) | New (v0.3.0) |
|--------|-------------|--------------|
| **Quality** | 360p (Android client) | 1080p+ (any format) |
| **Reliability** | ❌ Frequent failures | ✅ Always works |
| **Speed** | Slower (Python overhead) | Faster (direct CLI) |
| **Code complexity** | ~400 lines | Removed |
| **Dependencies** | yt-dlp + retry logic | None |
| **User control** | Limited | Full control |

## 🛠️ Installation

No special installation needed for `yt-dlp` if you already have it. If not:

```bash
# macOS
brew install yt-dlp

# Linux
sudo apt install yt-dlp
# or
pip install yt-dlp

# Windows
winget install yt-dlp
# or
pip install yt-dlp
```

## 📝 Examples

### Basic Workflow
```bash
# 1. Download video
yt-dlp -f "best[height<=1080]" -o "concert.mp4" "https://www.youtube.com/watch?v=EXAMPLE"

# 2. Analyze
uv run analyzer concert.mp4 --clips 6 --export-video
```

### Batch Processing
```bash
# Download multiple videos
yt-dlp -f "best[height<=1080]" -o "%(title)s.%(ext)s" --batch-file urls.txt

# Analyze all downloaded videos
for video in *.mp4; do
    uv run analyzer "$video" --clips 3 --export-video
done
```

### With Motion Analysis
```bash
# Download
yt-dlp -f "best[height<=1080]" -o "dj-set.mp4" "https://www.youtube.com/watch?v=EXAMPLE"

# Analyze with motion detection
uv run analyzer dj-set.mp4 --clips 6 --with-motion --align-to-beat --export-video
```

## ❓ FAQ

### Q: Why can't Python run yt-dlp properly?
A: Python's `subprocess` creates a non-TTY environment where JavaScript execution for YouTube's nsig extraction fails. This is a fundamental limitation.

### Q: Can I still use URLs directly?
A: No, v0.3.0+ only accepts local file paths. Download videos manually first.

### Q: What about other platforms (Vimeo, etc.)?
A: Same approach - download manually with `yt-dlp`, then analyze.

### Q: Is there a way to automate this?
A: Yes, create a shell script:
```bash
#!/bin/bash
VIDEO_URL="$1"
yt-dlp -f "best[height<=1080]" -o "temp_video.mp4" "$VIDEO_URL"
uv run analyzer temp_video.mp4 --clips 6 --export-video
```

### Q: What if I have existing scripts using URLs?
A: Update them to use the two-step process (download → analyze).

## 🔍 Technical Details

For those interested in the technical investigation:
- We tested `shell=True`, `shell=False`, various `extractor-args`, Android/iOS clients
- CLI always worked; Python subprocess consistently failed for 1080p+
- Root cause: nsig extraction requires proper TTY environment
- Format 18 (360p) worked via Android client but quality was insufficient
- HLS formats worked in CLI but not via Python subprocess

## 📅 Timeline

- **v0.2.0**: Automatic downloads with `video_downloader.py`
- **v0.3.0**: Manual downloads only (current)
- **Future**: No plans to re-add automatic downloads

---

**Updated**: October 22, 2025  
**Status**: Production Ready ✅

