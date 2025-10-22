# MVP Analyzer - Automated Setup

This directory contains automated setup scripts for installing all dependencies required for MVP Analyzer on different operating systems.

## 🚀 Quick Start

### macOS
```bash
# Using Python script (recommended)
python3 setup.py

# Using bash script
chmod +x setup.sh
./setup.sh
```

### Linux (Ubuntu/Debian/CentOS/Fedora/Arch)
```bash
# Using Python script (recommended)
python3 setup.py

# Using bash script
chmod +x setup.sh
./setup.sh
```

### Windows
```powershell
# Using Python script (recommended)
python setup.py

# Using PowerShell script
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup.ps1
```

## 📋 What Gets Installed

The setup scripts automatically install the following dependencies:

### Core Dependencies
- **FFmpeg** - Video processing library
- **Python 3.11+** - Programming language runtime
- **uv** - Fast Python package manager
- **yt-dlp** - YouTube and video downloader

### Package Manager Support

#### macOS
- **Homebrew** (brew) - Primary package manager
- **MacPorts** (port) - Alternative package manager

#### Linux
- **APT** (apt) - Ubuntu/Debian
- **YUM** (yum) - CentOS/RHEL
- **DNF** (dnf) - Fedora
- **Pacman** (pacman) - Arch Linux
- **Zypper** (zypper) - openSUSE

#### Windows
- **Chocolatey** (choco) - Primary package manager
- **Winget** (winget) - Microsoft's package manager

## 🔧 Manual Installation

If automated setup fails, you can install dependencies manually:

### macOS (with Homebrew)
```bash
brew install ffmpeg python@3.11 uv yt-dlp
```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y ffmpeg python3.11 python3.11-pip python3.11-venv
python3.11 -m pip install --user uv yt-dlp
```

### CentOS/RHEL
```bash
sudo yum update -y
sudo yum install -y epel-release
sudo yum install -y ffmpeg python311 python311-pip
python3.11 -m pip install --user uv yt-dlp
```

### Fedora
```bash
sudo dnf update -y
sudo dnf install -y ffmpeg python3.11 python3.11-pip
python3.11 -m pip install --user uv yt-dlp
```

### Arch Linux
```bash
sudo pacman -Syu --noconfirm
sudo pacman -S --noconfirm ffmpeg python python-pip
pip install --user uv yt-dlp
```

### Windows (with Chocolatey)
```powershell
choco install -y ffmpeg python311 uv yt-dlp
```

### Windows (with Winget)
```powershell
winget install --id FFmpeg.FFmpeg --accept-package-agreements --accept-source-agreements
winget install --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
winget install --id astral-sh.uv --accept-package-agreements --accept-source-agreements
winget install --id yt-dlp --accept-package-agreements --accept-source-agreements
```

## ✅ Verification

After installation, verify that all dependencies are working:

```bash
# Check FFmpeg
ffmpeg -version

# Check Python
python3 --version  # or python --version on Windows

# Check uv
uv --version

# Check yt-dlp
yt-dlp --version
```

## 🎯 Next Steps

Once dependencies are installed:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/dj-shorts/analyzer.git
   cd analyzer
   ```

2. **Install Python dependencies:**
   ```bash
   uv sync
   ```

3. **Test the installation:**
   ```bash
   uv run python -m analyzer.cli --help
   ```

4. **Analyze a video:**
   ```bash
   uv run python -m analyzer.cli video.mp4 --export-video
   ```

5. **Download and analyze from YouTube:**
   ```bash
   uv run python -m analyzer.cli 'https://youtube.com/watch?v=VIDEO_ID' --export-video
   ```

## 🐛 Troubleshooting

### Common Issues

#### Permission Errors
- **macOS/Linux**: Use `sudo` for system-wide installations
- **Windows**: Run PowerShell as Administrator

#### Python Version Issues
- Ensure Python 3.11+ is installed
- Use `python3.11` explicitly if multiple Python versions exist

#### PATH Issues
- Add Python user directory to PATH: `~/.local/bin` (Linux/macOS) or `%APPDATA%\Python\Scripts` (Windows)
- Restart terminal after installation

#### Package Manager Not Found
- Install the appropriate package manager for your system
- Use pip as fallback: `pip install uv yt-dlp`

### Getting Help

If you encounter issues:

1. Check the [Issues](https://github.com/dj-shorts/analyzer/issues) page
2. Run the setup script with verbose output
3. Try manual installation steps
4. Verify your system meets the requirements

## 📝 Requirements

### Minimum System Requirements
- **macOS**: 10.15+ (Catalina)
- **Linux**: Ubuntu 18.04+, CentOS 7+, Fedora 30+, Arch Linux
- **Windows**: Windows 10+ (version 1903+)

### Hardware Requirements
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB free space
- **CPU**: Any modern processor (x64 architecture)

## 🔄 Updates

To update dependencies:

```bash
# macOS
brew upgrade ffmpeg python@3.11 uv yt-dlp

# Ubuntu/Debian
sudo apt update && sudo apt upgrade ffmpeg python3.11
python3.11 -m pip install --upgrade uv yt-dlp

# Windows (Chocolatey)
choco upgrade ffmpeg python311 uv yt-dlp
```

## 📄 License

This setup script is part of MVP Analyzer and follows the same license terms.
