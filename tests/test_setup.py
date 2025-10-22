"""
Tests for automated setup script.
"""

import pytest
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import platform

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from setup import DependencyInstaller


class TestDependencyInstaller:
    """Test DependencyInstaller class."""
    
    def test_init(self):
        """Test DependencyInstaller initialization."""
        installer = DependencyInstaller()
        
        assert installer.system == platform.system().lower()
        assert installer.arch == platform.machine().lower()
        assert isinstance(installer.package_managers, list)
        assert isinstance(installer.installed_packages, list)
        assert isinstance(installer.failed_packages, list)
    
    @patch('setup.shutil.which')
    def test_detect_package_managers_macos(self, mock_which):
        """Test package manager detection on macOS."""
        mock_which.side_effect = lambda cmd: cmd if cmd in ['brew', 'port'] else None
        
        installer = DependencyInstaller()
        installer.system = 'darwin'
        
        managers = installer._detect_package_managers()
        
        assert 'brew' in managers
        assert 'port' in managers
    
    @patch('setup.shutil.which')
    def test_detect_package_managers_linux(self, mock_which):
        """Test package manager detection on Linux."""
        def which_side_effect(cmd):
            if cmd in ['apt', 'yum', 'dnf', 'pacman', 'zypper']:
                return cmd
            return None
        
        mock_which.side_effect = which_side_effect
        
        # Create installer and manually set system
        installer = DependencyInstaller()
        installer.system = 'linux'
        
        # Call the method directly
        managers = installer._detect_package_managers()
        
        assert 'apt' in managers
        assert 'yum' in managers
        assert 'dnf' in managers
        assert 'pacman' in managers
        assert 'zypper' in managers
    
    @patch('setup.shutil.which')
    def test_detect_package_managers_windows(self, mock_which):
        """Test package manager detection on Windows."""
        mock_which.side_effect = lambda cmd: cmd if cmd in ['choco', 'winget'] else None
        
        installer = DependencyInstaller()
        installer.system = 'windows'
        
        managers = installer._detect_package_managers()
        
        assert 'choco' in managers
        assert 'winget' in managers
    
    def test_get_dependencies(self):
        """Test dependency configuration."""
        installer = DependencyInstaller()
        deps = installer._get_dependencies()
        
        # Check required dependencies
        assert 'ffmpeg' in deps
        assert 'python' in deps
        assert 'uv' in deps
        assert 'yt-dlp' in deps
        
        # Check dependency structure
        for dep_name, dep_info in deps.items():
            assert 'description' in dep_info
            assert 'packages' in dep_info
            assert 'verify_command' in dep_info
            assert 'required' in dep_info
            
            # Check packages for different managers
            packages = dep_info['packages']
            assert 'brew' in packages
            assert 'apt' in packages
            assert 'choco' in packages
    
    @patch('setup.subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test successful command execution."""
        mock_result = MagicMock()
        mock_result.stdout = "test output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        installer = DependencyInstaller()
        success, output = installer._run_command(['test', 'command'])
        
        assert success is True
        assert output == "test output"
        mock_run.assert_called_once()
    
    @patch('setup.subprocess.run')
    def test_run_command_failure(self, mock_run):
        """Test failed command execution."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'test')
        
        installer = DependencyInstaller()
        success, output = installer._run_command(['test', 'command'])
        
        assert success is False
        assert isinstance(output, str)
    
    @patch('setup.subprocess.run')
    def test_run_command_not_found(self, mock_run):
        """Test command not found."""
        mock_run.side_effect = FileNotFoundError()
        
        installer = DependencyInstaller()
        success, output = installer._run_command(['nonexistent', 'command'])
        
        assert success is False
        assert "Command not found" in output
    
    @patch.object(DependencyInstaller, '_run_command')
    def test_is_package_installed_true(self, mock_run_command):
        """Test package installation check - installed."""
        mock_run_command.return_value = (True, "version info")
        
        installer = DependencyInstaller()
        result = installer._is_package_installed('test', ['test', '--version'])
        
        assert result is True
        mock_run_command.assert_called_once_with(['test', '--version'], check=False)
    
    @patch.object(DependencyInstaller, '_run_command')
    def test_is_package_installed_false(self, mock_run_command):
        """Test package installation check - not installed."""
        mock_run_command.return_value = (False, "not found")
        
        installer = DependencyInstaller()
        result = installer._is_package_installed('test', ['test', '--version'])
        
        assert result is False
    
    @patch.object(DependencyInstaller, '_run_command')
    def test_install_with_package_manager_brew(self, mock_run_command):
        """Test installation with Homebrew."""
        mock_run_command.return_value = (True, "installed")
        
        installer = DependencyInstaller()
        result = installer._install_with_package_manager('test', 'brew', 'test-package')
        
        assert result is True
        mock_run_command.assert_called_once_with(['brew', 'install', 'test-package'])
    
    @patch.object(DependencyInstaller, '_run_command')
    def test_install_with_package_manager_apt(self, mock_run_command):
        """Test installation with apt."""
        mock_run_command.return_value = (True, "installed")
        
        installer = DependencyInstaller()
        result = installer._install_with_package_manager('test', 'apt', 'test-package')
        
        assert result is True
        # Should call apt install (apt update is handled separately in the method)
        assert mock_run_command.call_count == 1
    
    @patch.object(DependencyInstaller, '_run_command')
    def test_install_with_package_manager_failure(self, mock_run_command):
        """Test installation failure."""
        mock_run_command.return_value = (False, "installation failed")
        
        installer = DependencyInstaller()
        result = installer._install_with_package_manager('test', 'brew', 'test-package')
        
        assert result is False
    
    @patch.object(DependencyInstaller, '_run_command')
    def test_install_with_pip_success(self, mock_run_command):
        """Test pip installation success."""
        mock_run_command.return_value = (True, "installed")
        
        installer = DependencyInstaller()
        result = installer._install_with_pip('test', 'test-package')
        
        assert result is True
        mock_run_command.assert_called_once_with(['pip', 'install', 'test-package'])
    
    @patch.object(DependencyInstaller, '_run_command')
    def test_install_with_pip_failure(self, mock_run_command):
        """Test pip installation failure."""
        mock_run_command.return_value = (False, "pip failed")
        
        installer = DependencyInstaller()
        result = installer._install_with_pip('test', 'test-package')
        
        assert result is False
    
    @patch.object(DependencyInstaller, '_is_package_installed')
    @patch.object(DependencyInstaller, '_install_with_package_manager')
    @patch.object(DependencyInstaller, '_install_with_pip')
    def test_install_dependency_already_installed(self, mock_pip, mock_pkg_mgr, mock_installed):
        """Test installing already installed dependency."""
        mock_installed.return_value = True
        
        installer = DependencyInstaller()
        installer.package_managers = ['brew']
        
        deps = installer._get_dependencies()
        result = installer.install_dependency('ffmpeg', deps['ffmpeg'])
        
        assert result is True
        assert 'ffmpeg' in installer.installed_packages
        mock_pkg_mgr.assert_not_called()
        mock_pip.assert_not_called()
    
    @patch.object(DependencyInstaller, '_is_package_installed')
    @patch.object(DependencyInstaller, '_install_with_package_manager')
    @patch.object(DependencyInstaller, '_install_with_pip')
    def test_install_dependency_success(self, mock_pip, mock_pkg_mgr, mock_installed):
        """Test successful dependency installation."""
        mock_installed.return_value = False
        mock_pkg_mgr.return_value = True
        
        installer = DependencyInstaller()
        installer.package_managers = ['brew']
        
        deps = installer._get_dependencies()
        result = installer.install_dependency('ffmpeg', deps['ffmpeg'])
        
        assert result is True
        assert 'ffmpeg' in installer.installed_packages
        mock_pkg_mgr.assert_called_once()
    
    @patch.object(DependencyInstaller, '_is_package_installed')
    @patch.object(DependencyInstaller, '_install_with_package_manager')
    @patch.object(DependencyInstaller, '_install_with_pip')
    def test_install_dependency_fallback_pip(self, mock_pip, mock_pkg_mgr, mock_installed):
        """Test dependency installation with pip fallback."""
        mock_installed.return_value = False
        mock_pkg_mgr.return_value = False
        mock_pip.return_value = True
        
        installer = DependencyInstaller()
        installer.package_managers = ['brew']
        
        deps = installer._get_dependencies()
        result = installer.install_dependency('uv', deps['uv'])
        
        assert result is True
        assert 'uv' in installer.installed_packages
        mock_pip.assert_called_once()
    
    @patch.object(DependencyInstaller, '_is_package_installed')
    @patch.object(DependencyInstaller, '_install_with_package_manager')
    @patch.object(DependencyInstaller, '_install_with_pip')
    def test_install_dependency_failure(self, mock_pip, mock_pkg_mgr, mock_installed):
        """Test dependency installation failure."""
        mock_installed.return_value = False
        mock_pkg_mgr.return_value = False
        mock_pip.return_value = False
        
        installer = DependencyInstaller()
        installer.package_managers = ['brew']
        
        deps = installer._get_dependencies()
        result = installer.install_dependency('ffmpeg', deps['ffmpeg'])
        
        assert result is False
        assert 'ffmpeg' in installer.failed_packages
    
    @patch.object(DependencyInstaller, 'install_dependency')
    def test_install_all_dependencies_no_managers(self, mock_install):
        """Test installation with no package managers."""
        installer = DependencyInstaller()
        installer.package_managers = []
        
        result = installer.install_all_dependencies()
        
        assert result is False
        mock_install.assert_not_called()
    
    @patch.object(DependencyInstaller, 'install_dependency')
    def test_install_all_dependencies_success(self, mock_install):
        """Test successful installation of all dependencies."""
        mock_install.return_value = True
        
        installer = DependencyInstaller()
        installer.package_managers = ['brew']
        
        result = installer.install_all_dependencies()
        
        assert result is True
        # Should call install_dependency for each dependency
        deps = installer._get_dependencies()
        assert mock_install.call_count == len(deps)
    
    @patch.object(DependencyInstaller, 'install_dependency')
    def test_install_all_dependencies_partial_failure(self, mock_install):
        """Test installation with some failures."""
        # Make some dependencies fail
        def side_effect(package_name, dep_info):
            return package_name != 'ffmpeg'  # Only ffmpeg fails
        
        mock_install.side_effect = side_effect
        
        installer = DependencyInstaller()
        installer.package_managers = ['brew']
        
        result = installer.install_all_dependencies()
        
        assert result is False  # Should fail because ffmpeg is required
    
    @patch.object(DependencyInstaller, '_is_package_installed')
    def test_verify_installation_success(self, mock_installed):
        """Test successful installation verification."""
        mock_installed.return_value = True
        
        installer = DependencyInstaller()
        result = installer.verify_installation()
        
        assert result is True
    
    @patch.object(DependencyInstaller, '_is_package_installed')
    def test_verify_installation_failure(self, mock_installed):
        """Test installation verification failure."""
        # Make required packages fail verification
        def side_effect(package_name, verify_command):
            return package_name != 'ffmpeg'  # ffmpeg fails verification
        
        mock_installed.side_effect = side_effect
        
        installer = DependencyInstaller()
        result = installer.verify_installation()
        
        assert result is False
