# Automated setup script for MVP Analyzer dependencies (Windows PowerShell)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Red
}

# Function to check if command exists
function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to install dependencies using Chocolatey
function Install-WithChocolatey {
    Write-Status "Installing dependencies with Chocolatey..."
    
    if (-not (Test-Command "choco")) {
        Write-Error "Chocolatey not found. Please install Chocolatey first: https://chocolatey.org/install"
        return $false
    }
    
    try {
        choco install -y ffmpeg python311 uv yt-dlp
        Write-Success "Dependencies installed with Chocolatey"
        return $true
    }
    catch {
        Write-Error "Failed to install dependencies with Chocolatey: $_"
        return $false
    }
}

# Function to install dependencies using Winget
function Install-WithWinget {
    Write-Status "Installing dependencies with Winget..."
    
    if (-not (Test-Command "winget")) {
        Write-Error "Winget not found. Please install Winget first or use Chocolatey"
        return $false
    }
    
    try {
        winget install --id FFmpeg.FFmpeg --accept-package-agreements --accept-source-agreements
        winget install --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
        winget install --id astral-sh.uv --accept-package-agreements --accept-source-agreements
        winget install --id yt-dlp --accept-package-agreements --accept-source-agreements
        Write-Success "Dependencies installed with Winget"
        return $true
    }
    catch {
        Write-Error "Failed to install dependencies with Winget: $_"
        return $false
    }
}

# Function to install dependencies using pip
function Install-WithPip {
    Write-Status "Installing Python dependencies with pip..."
    
    try {
        # Refresh PATH to include Python
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        
        # Install uv and yt-dlp
        python -m pip install --user uv yt-dlp
        Write-Success "Python dependencies installed with pip"
        return $true
    }
    catch {
        Write-Error "Failed to install Python dependencies with pip: $_"
        return $false
    }
}

# Function to verify installation
function Test-Installation {
    Write-Status "Verifying installation..."
    
    $allGood = $true
    
    # Check FFmpeg
    if (Test-Command "ffmpeg") {
        $version = & ffmpeg -version 2>&1 | Select-Object -First 1
        Write-Success "FFmpeg is installed: $version"
    }
    else {
        Write-Error "FFmpeg not found"
        $allGood = $false
    }
    
    # Check Python
    if (Test-Command "python") {
        $version = & python --version 2>&1
        Write-Success "Python is installed: $version"
    }
    elseif (Test-Command "python3") {
        $version = & python3 --version 2>&1
        Write-Success "Python is installed: $version"
    }
    else {
        Write-Error "Python not found"
        $allGood = $false
    }
    
    # Check uv
    if (Test-Command "uv") {
        $version = & uv --version 2>&1
        Write-Success "uv is installed: $version"
    }
    else {
        Write-Warning "uv not found in PATH (may be installed in user directory)"
    }
    
    # Check yt-dlp
    if (Test-Command "yt-dlp") {
        $version = & yt-dlp --version 2>&1
        Write-Success "yt-dlp is installed: $version"
    }
    else {
        Write-Warning "yt-dlp not found in PATH (may be installed in user directory)"
    }
    
    return $allGood
}

# Function to show next steps
function Show-NextSteps {
    Write-Status "Next steps to get started with MVP Analyzer:"
    Write-Host ""
    Write-Host "1. Clone the repository:"
    Write-Host "   git clone https://github.com/dj-shorts/analyzer.git"
    Write-Host "   cd analyzer"
    Write-Host ""
    Write-Host "2. Install Python dependencies:"
    Write-Host "   uv sync"
    Write-Host ""
    Write-Host "3. Test the installation:"
    Write-Host "   uv run python -m analyzer.cli --help"
    Write-Host ""
    Write-Host "4. Analyze a video:"
    Write-Host "   uv run python -m analyzer.cli video.mp4 --export-video"
    Write-Host ""
    Write-Host "5. Download and analyze from YouTube:"
    Write-Host "   uv run python -m analyzer.cli 'https://youtube.com/watch?v=VIDEO_ID' --export-video"
    Write-Host ""
}

# Main function
function Main {
    Write-Host "🚀 MVP Analyzer - Automated Dependency Installation" -ForegroundColor $Blue
    Write-Host ""
    
    # Check if running as administrator
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Write-Warning "Not running as administrator. Some installations may require elevation."
    }
    
    # Try to install dependencies
    $success = $false
    
    # Try Chocolatey first
    if (Test-Command "choco") {
        $success = Install-WithChocolatey
    }
    
    # Try Winget if Chocolatey failed or not available
    if (-not $success -and (Test-Command "winget")) {
        $success = Install-WithWinget
    }
    
    # Try pip for Python packages if package managers failed
    if (-not $success) {
        Write-Warning "Package managers not available, trying pip for Python packages..."
        $success = Install-WithPip
    }
    
    if ($success) {
        Write-Success "Dependencies installed successfully!"
    }
    else {
        Write-Error "Failed to install dependencies"
        exit 1
    }
    
    # Verify installation
    if (Test-Installation) {
        Write-Success "Installation verification passed!"
    }
    else {
        Write-Warning "Installation verification had some issues, but you can try to proceed"
    }
    
    # Show next steps
    Show-NextSteps
    
    Write-Success "Setup completed! 🎉"
}

# Run main function
try {
    Main
}
catch {
    Write-Error "Unexpected error: $_"
    exit 1
}
