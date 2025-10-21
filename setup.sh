#!/bin/bash
# Automated setup script for MVP Analyzer dependencies (Unix/Linux/macOS)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists apt; then
            echo "ubuntu"
        elif command_exists yum; then
            echo "centos"
        elif command_exists dnf; then
            echo "fedora"
        elif command_exists pacman; then
            echo "arch"
        elif command_exists zypper; then
            echo "opensuse"
        else
            echo "linux"
        fi
    else
        echo "unknown"
    fi
}

# Function to install dependencies based on OS
install_dependencies() {
    local os=$1
    
    print_status "Installing dependencies for $os..."
    
    case $os in
        "macos")
            if command_exists brew; then
                print_status "Using Homebrew to install dependencies..."
                brew update
                brew install ffmpeg python@3.11 uv yt-dlp
            else
                print_error "Homebrew not found. Please install Homebrew first: https://brew.sh/"
                return 1
            fi
            ;;
        "ubuntu")
            print_status "Using apt to install dependencies..."
            sudo apt update
            sudo apt install -y ffmpeg python3.11 python3.11-pip python3.11-venv
            # Install uv and yt-dlp via pip
            python3.11 -m pip install --user uv yt-dlp
            ;;
        "centos")
            print_status "Using yum to install dependencies..."
            sudo yum update -y
            sudo yum install -y epel-release
            sudo yum install -y ffmpeg python311 python311-pip
            python3.11 -m pip install --user uv yt-dlp
            ;;
        "fedora")
            print_status "Using dnf to install dependencies..."
            sudo dnf update -y
            sudo dnf install -y ffmpeg python3.11 python3.11-pip
            python3.11 -m pip install --user uv yt-dlp
            ;;
        "arch")
            print_status "Using pacman to install dependencies..."
            sudo pacman -Syu --noconfirm
            sudo pacman -S --noconfirm ffmpeg python python-pip
            pip install --user uv yt-dlp
            ;;
        "opensuse")
            print_status "Using zypper to install dependencies..."
            sudo zypper refresh
            sudo zypper install -y ffmpeg python311 python311-pip
            python3.11 -m pip install --user uv yt-dlp
            ;;
        *)
            print_error "Unsupported operating system: $os"
            return 1
            ;;
    esac
}

# Function to verify installation
verify_installation() {
    print_status "Verifying installation..."
    
    local all_good=true
    
    # Check FFmpeg
    if command_exists ffmpeg; then
        print_success "FFmpeg is installed: $(ffmpeg -version | head -n1)"
    else
        print_error "FFmpeg not found"
        all_good=false
    fi
    
    # Check Python
    if command_exists python3.11; then
        print_success "Python 3.11 is installed: $(python3.11 --version)"
    elif command_exists python3; then
        local python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [[ "$python_version" == "3.11" ]]; then
            print_success "Python 3.11 is installed: $(python3 --version)"
        else
            print_warning "Python 3.11 not found, but Python $python_version is available"
        fi
    else
        print_error "Python 3.11 not found"
        all_good=false
    fi
    
    # Check uv
    if command_exists uv; then
        print_success "uv is installed: $(uv --version)"
    else
        print_warning "uv not found in PATH (may be installed in user directory)"
    fi
    
    # Check yt-dlp
    if command_exists yt-dlp; then
        print_success "yt-dlp is installed: $(yt-dlp --version)"
    else
        print_warning "yt-dlp not found in PATH (may be installed in user directory)"
    fi
    
    if $all_good; then
        print_success "All core dependencies are installed!"
        return 0
    else
        print_error "Some dependencies are missing"
        return 1
    fi
}

# Function to show next steps
show_next_steps() {
    print_status "Next steps to get started with MVP Analyzer:"
    echo ""
    echo "1. Clone the repository:"
    echo "   git clone https://github.com/dj-shorts/analyzer.git"
    echo "   cd analyzer"
    echo ""
    echo "2. Install Python dependencies:"
    echo "   uv sync"
    echo ""
    echo "3. Test the installation:"
    echo "   uv run python -m analyzer.cli --help"
    echo ""
    echo "4. Analyze a video:"
    echo "   uv run python -m analyzer.cli video.mp4 --export-video"
    echo ""
    echo "5. Download and analyze from YouTube:"
    echo "   uv run python -m analyzer.cli 'https://youtube.com/watch?v=VIDEO_ID' --export-video"
    echo ""
}

# Main function
main() {
    echo -e "${BLUE}🚀 MVP Analyzer - Automated Dependency Installation${NC}"
    echo ""
    
    # Detect OS
    local os=$(detect_os)
    print_status "Detected operating system: $os"
    
    # Check if running as root (not recommended)
    if [[ $EUID -eq 0 ]]; then
        print_warning "Running as root is not recommended. Consider using sudo for individual commands."
    fi
    
    # Install dependencies
    if install_dependencies "$os"; then
        print_success "Dependencies installed successfully!"
    else
        print_error "Failed to install dependencies"
        exit 1
    fi
    
    # Verify installation
    if verify_installation; then
        print_success "Installation verification passed!"
    else
        print_warning "Installation verification had some issues, but you can try to proceed"
    fi
    
    # Show next steps
    show_next_steps
    
    print_success "Setup completed! 🎉"
}

# Run main function
main "$@"
