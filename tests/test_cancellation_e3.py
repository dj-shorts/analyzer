"""
Tests for Epic E3 - Cancellation and resource management.

Tests signal handling, process cleanup, and resource management functionality.
"""

import signal
import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from analyzer.cancellation import (
    CancellationManager,
    ProcessMonitor,
    ResourceManager,
    managed_resources,
)


class TestResourceManagerEpicE3:
    """Tests for the ResourceManager class."""

    def test_resource_manager_initialization(self):
        """Test ResourceManager initialization."""
        # Test with no limits
        rm = ResourceManager()
        assert rm.max_threads is None
        assert rm.ram_limit is None
        assert len(rm.child_processes) == 0

        # Test with limits
        rm = ResourceManager(max_threads=4, ram_limit="2GB")
        assert rm.max_threads == 4
        assert rm.ram_limit == 2 * 1024**3  # 2GB in bytes

    def test_parse_ram_limit(self):
        """Test RAM limit parsing."""
        rm = ResourceManager()

        # Test various formats
        assert rm._parse_ram_limit("1GB") == 1024**3
        assert rm._parse_ram_limit("512MB") == 512 * 1024**2
        assert rm._parse_ram_limit("1024KB") == 1024 * 1024
        assert rm._parse_ram_limit("1024B") == 1024
        assert rm._parse_ram_limit("1024") == 1024

        # Test invalid formats
        assert rm._parse_ram_limit("invalid") is None
        assert rm._parse_ram_limit("") is None
        assert rm._parse_ram_limit(None) is None

    def test_register_unregister_process(self):
        """Test process registration and unregistration."""
        rm = ResourceManager()

        # Create a mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Still running

        # Register process
        rm.register_process(mock_process)
        assert len(rm.child_processes) == 1
        assert mock_process in rm.child_processes

        # Unregister process
        rm.unregister_process(mock_process)
        assert len(rm.child_processes) == 0
        assert mock_process not in rm.child_processes

    def test_cleanup_processes_success(self):
        """Test successful process cleanup."""
        rm = ResourceManager()

        # Create mock processes
        mock_process1 = Mock()
        mock_process1.pid = 12345
        mock_process1.poll.return_value = None  # Still running

        mock_process2 = Mock()
        mock_process2.pid = 12346
        mock_process2.poll.return_value = None  # Still running

        rm.register_process(mock_process1)
        rm.register_process(mock_process2)

        # Mock process termination
        mock_process1.terminate.return_value = None
        mock_process2.terminate.return_value = None

        # Mock process completion after terminate
        def mock_poll_completed():
            time.sleep(0.1)
            mock_process1.poll.return_value = 0
            mock_process2.poll.return_value = 0

        # Start cleanup in thread to simulate process completion
        cleanup_thread = threading.Thread(target=rm.cleanup_processes, args=(1.0,))
        completion_thread = threading.Thread(target=mock_poll_completed)

        completion_thread.start()
        cleanup_thread.start()

        cleanup_thread.join(timeout=2.0)
        completion_thread.join(timeout=2.0)

        # Verify processes were terminated
        mock_process1.terminate.assert_called_once()
        mock_process2.terminate.assert_called_once()

    def test_cleanup_processes_force_kill(self):
        """Test force kill when graceful termination fails."""
        rm = ResourceManager()

        # Create mock process that doesn't terminate gracefully
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Still running
        mock_process.terminate.return_value = None
        mock_process.kill.return_value = None

        rm.register_process(mock_process)

        # Mock process that never completes
        def mock_poll_running():
            return None

        mock_process.poll.side_effect = mock_poll_running

        # Run cleanup with short timeout
        success = rm.cleanup_processes(timeout=0.1)

        # Should have tried terminate and then kill
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        # Success should be False since process didn't terminate
        assert success is False

    def test_get_system_info(self):
        """Test system info retrieval."""
        rm = ResourceManager(max_threads=4, ram_limit="2GB")

        with (
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.cpu_count") as mock_cpu_count,
        ):
            mock_memory.return_value = Mock(
                total=8 * 1024**3,
                available=4 * 1024**3,
                percent=50.0,  # 8GB  # 4GB
            )
            mock_cpu_count.return_value = 8

            info = rm.get_system_info()

            assert info["cpu_count"] == 8
            assert info["memory_total"] == 8 * 1024**3
            assert info["memory_available"] == 4 * 1024**3
            assert info["memory_percent"] == 50.0
            assert info["max_threads"] == 4
            assert info["ram_limit"] == 2 * 1024**3


class TestCancellationManagerEpicE3:
    """Tests for the CancellationManager class."""

    def test_cancellation_manager_initialization(self):
        """Test CancellationManager initialization."""
        rm = ResourceManager()
        cm = CancellationManager(rm)

        assert cm.resource_manager is rm
        assert cm.cancelled is False
        assert len(cm._original_signal_handlers) == 0

    def test_setup_restore_signal_handlers(self):
        """Test signal handler setup and restoration."""
        rm = ResourceManager()
        cm = CancellationManager(rm)

        # Mock signal.signal to avoid actually setting signal handlers
        with patch("signal.signal") as mock_signal:
            # Return mock handlers for both setup and restore calls
            mock_signal.side_effect = [Mock(), Mock(), None, None]

            cm.setup_signal_handlers()

            # Should have set up handlers for SIGTERM and SIGINT
            assert mock_signal.call_count == 2
            assert len(cm._original_signal_handlers) == 2

            # Restore handlers
            cm.restore_signal_handlers()
            assert mock_signal.call_count == 4  # 2 for setup, 2 for restore

    def test_cancel(self):
        """Test cancellation functionality."""
        rm = ResourceManager()
        cm = CancellationManager(rm)

        # Mock resource manager cleanup
        rm.cleanup_processes = Mock(return_value=True)

        # Test cancellation
        success = cm.cancel()

        assert cm.cancelled is True
        assert success is True
        rm.cleanup_processes.assert_called_once_with(timeout=5.0)

    def test_is_cancelled(self):
        """Test cancellation status check."""
        rm = ResourceManager()
        cm = CancellationManager(rm)

        assert cm.is_cancelled() is False

        cm.cancelled = True
        assert cm.is_cancelled() is True

    def test_check_cancellation(self):
        """Test cancellation check with exception raising."""
        rm = ResourceManager()
        cm = CancellationManager(rm)

        # Should not raise when not cancelled
        cm.check_cancellation()

        # Should raise when cancelled
        cm.cancelled = True
        with pytest.raises(KeyboardInterrupt, match="Operation cancelled"):
            cm.check_cancellation()


class TestProcessMonitorEpicE3:
    """Tests for the ProcessMonitor class."""

    def test_process_monitor_initialization(self):
        """Test ProcessMonitor initialization."""
        rm = ResourceManager()
        pm = ProcessMonitor(rm)

        assert pm.resource_manager is rm

    @patch("subprocess.Popen")
    def test_run_subprocess(self, mock_popen):
        """Test subprocess execution with monitoring."""
        rm = ResourceManager()
        pm = ProcessMonitor(rm)

        # Mock subprocess
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        # Run subprocess
        result = pm.run_subprocess(["echo", "test"])

        assert result is mock_process
        mock_popen.assert_called_once()
        assert mock_process in rm.child_processes

    def test_wait_for_completion_success(self):
        """Test waiting for subprocess completion."""
        rm = ResourceManager()
        pm = ProcessMonitor(rm)

        # Create mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.communicate.return_value = ("stdout", "stderr")
        mock_process.returncode = 0
        mock_process.args = ["echo", "test"]

        # Wait for completion
        result = pm.wait_for_completion(mock_process)

        assert result.returncode == 0
        assert result.stdout == "stdout"
        assert result.stderr == "stderr"
        mock_process.communicate.assert_called_once()

    def test_wait_for_completion_timeout(self):
        """Test subprocess timeout handling."""
        rm = ResourceManager()
        pm = ProcessMonitor(rm)

        # Create mock process that times out
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.kill.return_value = None

        # Mock communicate to raise TimeoutExpired
        from subprocess import TimeoutExpired

        mock_process.communicate.side_effect = TimeoutExpired(["echo", "test"], 1.0)

        with pytest.raises(TimeoutExpired):
            pm.wait_for_completion(mock_process, timeout=1.0)

        mock_process.kill.assert_called_once()


class TestManagedResourcesContextManagerEpicE3:
    """Tests for the managed_resources context manager."""

    @patch("analyzer.cancellation.CancellationManager")
    @patch("analyzer.cancellation.ResourceManager")
    def test_managed_resources_context_manager(self, mock_rm_class, mock_cm_class):
        """Test the managed_resources context manager."""
        # Mock instances
        mock_rm = Mock()
        mock_cm = Mock()
        mock_rm_class.return_value = mock_rm
        mock_cm_class.return_value = mock_cm

        # Test context manager
        with managed_resources(max_threads=4, ram_limit="2GB") as rm:
            assert rm is mock_rm
            mock_rm_class.assert_called_once_with(4, "2GB")
            mock_cm_class.assert_called_once_with(mock_rm)
            mock_cm.setup_signal_handlers.assert_called_once()

        # Verify cleanup
        mock_cm.restore_signal_handlers.assert_called_once()
        mock_rm.cleanup_processes.assert_called_once_with(timeout=5.0)

    def test_managed_resources_with_exception(self):
        """Test managed_resources context manager with exception."""
        with (
            patch("analyzer.cancellation.CancellationManager") as mock_cm_class,
            patch("analyzer.cancellation.ResourceManager") as mock_rm_class,
        ):
            mock_rm = Mock()
            mock_cm = Mock()
            mock_rm_class.return_value = mock_rm
            mock_cm_class.return_value = mock_cm

            # Test with exception
            with pytest.raises(ValueError):
                with managed_resources() as _rm:
                    mock_cm.setup_signal_handlers.assert_called_once()
                    raise ValueError("Test exception")

            # Verify cleanup still happens
            mock_cm.restore_signal_handlers.assert_called_once()
            mock_rm.cleanup_processes.assert_called_once_with(timeout=5.0)


class TestIntegrationEpicE3:
    """Integration tests for Epic E3 functionality."""

    def test_signal_handling_integration(self):
        """Test signal handling integration."""
        rm = ResourceManager()
        cm = CancellationManager(rm)

        # Mock signal handlers to avoid actually setting them
        with patch("signal.signal") as mock_signal:
            # Setup signal handlers
            cm.setup_signal_handlers()

            # Simulate signal handler call
            signal_handler = mock_signal.call_args_list[0][0][1]
            signal_handler(signal.SIGTERM, None)

            # Verify cancellation was requested
            assert cm.is_cancelled() is True

    def test_process_cleanup_integration(self):
        """Test process cleanup integration."""
        rm = ResourceManager()

        # Create mock processes
        mock_process1 = Mock()
        mock_process1.pid = 12345
        mock_process1.poll.return_value = None

        mock_process2 = Mock()
        mock_process2.pid = 12346
        mock_process2.poll.return_value = None

        # Register processes
        rm.register_process(mock_process1)
        rm.register_process(mock_process2)

        # Mock cleanup behavior
        def mock_cleanup_behavior():
            time.sleep(0.1)
            mock_process1.poll.return_value = 0
            mock_process2.poll.return_value = 0

        # Start cleanup in thread
        cleanup_thread = threading.Thread(target=rm.cleanup_processes, args=(1.0,))
        behavior_thread = threading.Thread(target=mock_cleanup_behavior)

        behavior_thread.start()
        cleanup_thread.start()

        cleanup_thread.join(timeout=2.0)
        behavior_thread.join(timeout=2.0)

        # Verify processes were cleaned up
        assert len(rm.child_processes) == 0
