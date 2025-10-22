#!/usr/bin/env python3
"""
Automated setup script for MVP Analyzer dependencies.

This script automatically installs all required dependencies for the MVP Analyzer
on macOS, Linux, and Windows systems.
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class DependencyInstaller:
    """Handles automatic installation of dependencies."""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        self.package_managers = self._detect_package_managers()
        self.installed_packages = []
        self.failed_packages = []
    
    def _detect_package_managers(self) -> List[str]:
        """Detect available package managers on the system."""
        managers = []
        
        if self.system == "darwin":  # macOS
            if shutil.which("brew"):
                managers.append("brew")
            if shutil.which("port"):
                managers.append("port")
        elif self.system == "linux":
            if shutil.which("apt"):
                managers.append("apt")
            if shutil.which("yum"):
                managers.append("yum")
            if shutil.which("dnf"):
                managers.append("dnf")
            if shutil.which("pacman"):
                managers.append("pacman")
            if shutil.which("zypper"):
                managers.append("zypper")
        elif self.system == "windows":
            if shutil.which("choco"):
                managers.append("choco")
            if shutil.which("winget"):
                managers.append("winget")
        
        return managers
    
    def _get_dependencies(self) -> Dict[str, Dict[str, any]]:
        """Get system-specific dependencies."""
        deps = {
            "ffmpeg": {
                "description": "FFmpeg - Video processing library",
                "packages": {
                    "brew": "ffmpeg",
                    "apt": "ffmpeg",
                    "yum": "ffmpeg",
                    "dnf": "ffmpeg",
                    "pacman": "ffmpeg",
                    "zypper": "ffmpeg",
                    "choco": "ffmpeg",
                    "winget": "FFmpeg",
                },
                "verify_command": ["ffmpeg", "-version"],
                "required": True,
            },
            "python": {
                "description": "Python 3.11+ - Programming language",
                "packages": {
                    "brew": "python@3.11",
                    "apt": "python3.11",
                    "yum": "python311",
                    "dnf": "python3.11",
                    "pacman": "python",
                    "zypper": "python311",
                    "choco": "python",
                    "winget": "Python.Python.3.11",
                },
                "verify_command": ["python3", "--version"],
                "required": True,
            },
            "uv": {
                "description": "uv - Fast Python package manager",
                "packages": {
                    "brew": "uv",
                    "apt": "uv",  # May need custom repo
                    "yum": "uv",  # May need custom repo
                    "dnf": "uv",  # May need custom repo
                    "pacman": "uv",
                    "zypper": "uv",  # May need custom repo
                    "choco": "uv",
                    "winget": "astral-sh.uv",
                },
                "verify_command": ["uv", "--version"],
                "required": True,
                "fallback_install": "pip install uv",
            },
            "yt-dlp": {
                "description": "yt-dlp - YouTube and video downloader",
                "packages": {
                    "brew": "yt-dlp",
                    "apt": "yt-dlp",
                    "yum": "yt-dlp",
                    "dnf": "yt-dlp",
                    "pacman": "yt-dlp",
                    "zypper": "yt-dlp",
                    "choco": "yt-dlp",
                    "winget": "yt-dlp",
                },
                "verify_command": ["yt-dlp", "--version"],
                "required": True,
                "fallback_install": "pip install yt-dlp",
            },
        }
        
        return deps
    
    def _run_command(self, command: List[str], check: bool = True) -> Tuple[bool, str]:
        """Run a command and return success status and output."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip() if e.stderr else str(e)
        except FileNotFoundError:
            return False, f"Command not found: {command[0]}"
    
    def _is_package_installed(self, package_name: str, verify_command: List[str]) -> bool:
        """Check if a package is already installed."""
        success, _ = self._run_command(verify_command, check=False)
        return success
    
    def _install_with_package_manager(self, package_name: str, manager: str, package: str) -> bool:
        """Install package using specific package manager."""
        if manager == "brew":
            cmd = ["brew", "install", package]
        elif manager == "apt":
            cmd = ["sudo", "apt", "update"] + ["sudo", "apt", "install", "-y", package]
        elif manager == "yum":
            cmd = ["sudo", "yum", "install", "-y", package]
        elif manager == "dnf":
            cmd = ["sudo", "dnf", "install", "-y", package]
        elif manager == "pacman":
            cmd = ["sudo", "pacman", "-S", "--noconfirm", package]
        elif manager == "zypper":
            cmd = ["sudo", "zypper", "install", "-y", package]
        elif manager == "choco":
            cmd = ["choco", "install", package, "-y"]
        elif manager == "winget":
            cmd = ["winget", "install", package, "--accept-package-agreements", "--accept-source-agreements"]
        else:
            return False
        
        print(f"Installing {package_name} with {manager}...")
        success, output = self._run_command(cmd)
        
        if success:
            print(f"✅ {package_name} installed successfully")
            return True
        else:
            print(f"❌ Failed to install {package_name} with {manager}: {output}")
            return False
    
    def _install_with_pip(self, package_name: str, pip_package: str) -> bool:
        """Install package using pip."""
        print(f"Installing {package_name} with pip...")
        cmd = ["pip", "install", pip_package]
        success, output = self._run_command(cmd)
        
        if success:
            print(f"✅ {package_name} installed successfully with pip")
            return True
        else:
            print(f"❌ Failed to install {package_name} with pip: {output}")
            return False
    
    def install_dependency(self, package_name: str, dep_info: Dict[str, any]) -> bool:
        """Install a single dependency."""
        print(f"\n🔍 Checking {package_name}...")
        
        # Check if already installed
        if self._is_package_installed(package_name, dep_info["verify_command"]):
            print(f"✅ {package_name} is already installed")
            self.installed_packages.append(package_name)
            return True
        
        # Try to install with available package managers
        packages = dep_info.get("packages", {})
        
        for manager in self.package_managers:
            if manager in packages:
                if self._install_with_package_manager(package_name, manager, packages[manager]):
                    self.installed_packages.append(package_name)
                    return True
        
        # Try fallback installation if available
        if "fallback_install" in dep_info:
            fallback_cmd = dep_info["fallback_install"].split()
            if fallback_cmd[0] == "pip":
                pip_package = fallback_cmd[2] if len(fallback_cmd) > 2 else package_name
                if self._install_with_pip(package_name, pip_package):
                    self.installed_packages.append(package_name)
                    return True
        
        # Installation failed
        print(f"❌ Failed to install {package_name}")
        self.failed_packages.append(package_name)
        
        if dep_info.get("required", False):
            print(f"⚠️  {package_name} is required for MVP Analyzer to work properly")
        
        return False
    
    def install_all_dependencies(self) -> bool:
        """Install all dependencies."""
        print("🚀 MVP Analyzer - Automated Dependency Installation")
        print(f"📱 System: {self.system} ({self.arch})")
        print(f"📦 Available package managers: {', '.join(self.package_managers)}")
        
        if not self.package_managers:
            print("❌ No supported package managers found!")
            print("Please install one of the following:")
            if self.system == "darwin":
                print("  - Homebrew: https://brew.sh/")
            elif self.system == "linux":
                print("  - apt, yum, dnf, pacman, or zypper")
            elif self.system == "windows":
                print("  - Chocolatey: https://chocolatey.org/")
                print("  - Winget: https://docs.microsoft.com/en-us/windows/package-manager/winget/")
            return False
        
        dependencies = self._get_dependencies()
        all_success = True
        
        for package_name, dep_info in dependencies.items():
            success = self.install_dependency(package_name, dep_info)
            if not success and dep_info.get("required", False):
                all_success = False
        
        # Print summary
        print(f"\n📊 Installation Summary:")
        print(f"✅ Successfully installed: {', '.join(self.installed_packages)}")
        
        if self.failed_packages:
            print(f"❌ Failed to install: {', '.join(self.failed_packages)}")
        
        if all_success:
            print(f"\n🎉 All dependencies installed successfully!")
            print(f"🚀 You can now use MVP Analyzer!")
        else:
            print(f"\n⚠️  Some dependencies failed to install.")
            print(f"Please install them manually and try again.")
        
        return all_success
    
    def verify_installation(self) -> bool:
        """Verify that all dependencies are properly installed."""
        print(f"\n🔍 Verifying installation...")
        
        dependencies = self._get_dependencies()
        all_verified = True
        
        for package_name, dep_info in dependencies.items():
            if self._is_package_installed(package_name, dep_info["verify_command"]):
                print(f"✅ {package_name} - OK")
            else:
                print(f"❌ {package_name} - NOT FOUND")
                if dep_info.get("required", False):
                    all_verified = False
        
        return all_verified


def main():
    """Main function."""
    installer = DependencyInstaller()
    
    try:
        success = installer.install_all_dependencies()
        
        if success:
            installer.verify_installation()
            print(f"\n🎉 Setup completed successfully!")
            print(f"📖 Next steps:")
            print(f"  1. Clone the MVP Analyzer repository")
            print(f"  2. Run: uv sync")
            print(f"  3. Run: uv run python -m analyzer.cli --help")
        else:
            print(f"\n❌ Setup failed. Please install missing dependencies manually.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Installation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
