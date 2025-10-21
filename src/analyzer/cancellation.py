"""
Cancellation and resource management module for MVP Analyzer.
Handles signal processing, process cleanup, and resource management.
"""

import os
import signal
import psutil
import subprocess
import threading
import time
import logging
from typing import List, Optional, Set, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ResourceManager:
    """Manages system resources and process cleanup."""
    
    def __init__(self, max_threads: Optional[int] = None, ram_limit: Optional[str] = None):
        """
        Initialize resource manager.
        
        Args:
            max_threads: Maximum number of threads to use
            ram_limit: RAM limit (e.g., '2GB', '512MB')
        """
        self.max_threads = max_threads
        self.ram_limit = self._parse_ram_limit(ram_limit)
        self.child_processes: Set[subprocess.Popen] = set()
        self._lock = threading.Lock()
        self._cancellation_manager: Optional['CancellationManager'] = None
    
    def set_cancellation_manager(self, cancellation_manager: 'CancellationManager') -> None:
        """
        Set the cancellation manager for this resource manager.
        
        Args:
            cancellation_manager: CancellationManager instance
        """
        self._cancellation_manager = cancellation_manager
        
    def _parse_ram_limit(self, ram_limit: Optional[str]) -> Optional[int]:
        """
        Parse RAM limit string to bytes.
        
        Args:
            ram_limit: RAM limit string (e.g., '2GB', '512MB')
            
        Returns:
            RAM limit in bytes or None
        """
        if not ram_limit:
            return None
            
        ram_limit = ram_limit.upper().strip()
        
        # Parse number and unit
        try:
            if ram_limit.endswith('GB'):
                return int(float(ram_limit[:-2]) * 1024**3)
            elif ram_limit.endswith('MB'):
                return int(float(ram_limit[:-2]) * 1024**2)
            elif ram_limit.endswith('KB'):
                return int(float(ram_limit[:-2]) * 1024)
            elif ram_limit.endswith('B'):
                return int(ram_limit[:-1])
            else:
                # Assume bytes if no unit
                return int(ram_limit)
        except (ValueError, IndexError):
            logger.warning(f"Invalid RAM limit format: {ram_limit}")
            return None
    
    def register_process(self, process: subprocess.Popen) -> None:
        """
        Register a child process for cleanup.
        
        Args:
            process: Subprocess to register
        """
        with self._lock:
            self.child_processes.add(process)
    
    def unregister_process(self, process: subprocess.Popen) -> None:
        """
        Unregister a child process.
        
        Args:
            process: Subprocess to unregister
        """
        with self._lock:
            self.child_processes.discard(process)
    
    def cleanup_processes(self, timeout: float = 5.0) -> bool:
        """
        Clean up all registered child processes.
        
        Args:
            timeout: Maximum time to wait for processes to terminate
            
        Returns:
            True if all processes were cleaned up, False otherwise
        """
        with self._lock:
            if not self.child_processes:
                return True
                
            processes_to_cleanup = self.child_processes.copy()
            self.child_processes.clear()
        
        logger.info(f"Cleaning up {len(processes_to_cleanup)} child processes")
        
        # First, try graceful termination
        for process in processes_to_cleanup:
            if process.poll() is None:  # Process is still running
                try:
                    logger.debug(f"Terminating process {process.pid}")
                    process.terminate()
                except (OSError, subprocess.SubprocessError) as e:
                    logger.warning(f"Failed to terminate process {process.pid}: {e}")
        
        # Wait for processes to terminate gracefully
        start_time = time.time()
        while time.time() - start_time < timeout:
            running_processes = [p for p in processes_to_cleanup if p.poll() is None]
            if not running_processes:
                logger.info("All processes terminated gracefully")
                return True
            
            time.sleep(0.1)
        
        # Force kill remaining processes
        logger.warning("Force killing remaining processes")
        for process in processes_to_cleanup:
            if process.poll() is None:
                try:
                    logger.debug(f"Force killing process {process.pid}")
                    process.kill()
                except (OSError, subprocess.SubprocessError) as e:
                    logger.warning(f"Failed to kill process {process.pid}: {e}")
        
        # Wait a bit more for force kill to take effect
        time.sleep(0.5)
        
        # Check if any processes are still running
        still_running = [p for p in processes_to_cleanup if p.poll() is None]
        if still_running:
            logger.error(f"Failed to cleanup {len(still_running)} processes")
            return False
        
        logger.info("All processes cleaned up successfully")
        return True
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get current system resource information.
        
        Returns:
            Dict with system resource information
        """
        try:
            memory = psutil.virtual_memory()
            cpu_count = psutil.cpu_count()
            
            info = {
                "cpu_count": cpu_count,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "memory_percent": memory.percent,
                "max_threads": self.max_threads or cpu_count,
                "ram_limit": self.ram_limit
            }
            
            if self.ram_limit:
                info["ram_limit_percent"] = (memory.available / self.ram_limit) * 100
            
            return info
        except Exception as e:
            logger.warning(f"Failed to get system info: {e}")
            return {}


class CancellationManager:
    """Manages cancellation signals and cleanup."""
    
    def __init__(self, resource_manager: ResourceManager):
        """
        Initialize cancellation manager.
        
        Args:
            resource_manager: Resource manager instance
        """
        self.resource_manager = resource_manager
        self.cancelled = False
        self._original_signal_handlers = {}
        self._lock = threading.Lock()
    
    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.cancel()
        
        # Store original handlers
        self._original_signal_handlers[signal.SIGTERM] = signal.signal(signal.SIGTERM, signal_handler)
        self._original_signal_handlers[signal.SIGINT] = signal.signal(signal.SIGINT, signal_handler)
        
        logger.debug("Signal handlers set up")
    
    def restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_signal_handlers.items():
            signal.signal(sig, handler)
        
        logger.debug("Signal handlers restored")
    
    def cancel(self) -> bool:
        """
        Cancel the current operation.
        
        Returns:
            True if cancellation was successful
        """
        with self._lock:
            if self.cancelled:
                return True
            
            self.cancelled = True
            logger.info("Cancellation requested")
        
        # Clean up processes
        success = self.resource_manager.cleanup_processes(timeout=5.0)
        
        if success:
            logger.info("Cancellation completed successfully")
        else:
            logger.warning("Cancellation completed with some processes still running")
        
        return success
    
    def is_cancelled(self) -> bool:
        """
        Check if cancellation has been requested.
        
        Returns:
            True if cancellation has been requested
        """
        with self._lock:
            return self.cancelled
    
    def check_cancellation(self) -> None:
        """
        Check if cancellation has been requested and raise exception if so.
        
        Raises:
            KeyboardInterrupt: If cancellation has been requested
        """
        if self.is_cancelled():
            raise KeyboardInterrupt("Operation cancelled")


@contextmanager
def managed_resources(max_threads: Optional[int] = None, ram_limit: Optional[str] = None):
    """
    Context manager for resource management and cleanup.
    
    Args:
        max_threads: Maximum number of threads to use
        ram_limit: RAM limit (e.g., '2GB', '512MB')
        
    Yields:
        ResourceManager instance
    """
    resource_manager = ResourceManager(max_threads, ram_limit)
    cancellation_manager = CancellationManager(resource_manager)
    
    # Wire cancellation manager into resource manager
    resource_manager.set_cancellation_manager(cancellation_manager)
    
    try:
        cancellation_manager.setup_signal_handlers()
        logger.info(f"Resource management initialized (threads: {max_threads}, RAM: {ram_limit})")
        yield resource_manager
    finally:
        cancellation_manager.restore_signal_handlers()
        resource_manager.cleanup_processes(timeout=5.0)
        logger.info("Resource management cleanup completed")


class ProcessMonitor:
    """Monitors and manages subprocess execution with resource limits."""
    
    def __init__(self, resource_manager: ResourceManager):
        """
        Initialize process monitor.
        
        Args:
            resource_manager: Resource manager instance
        """
        self.resource_manager = resource_manager
    
    def run_subprocess(self, cmd: List[str], **kwargs) -> subprocess.Popen:
        """
        Run a subprocess with resource monitoring.
        
        Args:
            cmd: Command to run
            **kwargs: Additional arguments for subprocess.Popen
            
        Returns:
            Subprocess instance
        """
        # Check cancellation before starting
        if hasattr(self.resource_manager, '_cancellation_manager') and self.resource_manager._cancellation_manager is not None:
            self.resource_manager._cancellation_manager.check_cancellation()
        
        # Set default subprocess options
        default_kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'text': True
        }
        default_kwargs.update(kwargs)
        
        try:
            process = subprocess.Popen(cmd, **default_kwargs)
            self.resource_manager.register_process(process)
            logger.debug(f"Started subprocess {process.pid}: {' '.join(cmd)}")
            return process
        except Exception as e:
            logger.error(f"Failed to start subprocess: {e}")
            raise
    
    def wait_for_completion(self, process: subprocess.Popen, timeout: Optional[float] = None) -> subprocess.CompletedProcess:
        """
        Wait for subprocess completion with cancellation support.
        
        Args:
            process: Subprocess to wait for
            timeout: Maximum time to wait
            
        Returns:
            CompletedProcess result
            
        Raises:
            subprocess.TimeoutExpired: If process times out
            subprocess.CalledProcessError: If process fails
        """
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            
            # Unregister process after completion
            self.resource_manager.unregister_process(process)
            
            result = subprocess.CompletedProcess(
                args=process.args,
                returncode=process.returncode,
                stdout=stdout,
                stderr=stderr
            )
            
            if result.returncode != 0:
                logger.warning(f"Subprocess failed with return code {result.returncode}")
                logger.debug(f"stderr: {result.stderr}")
            
            return result
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Subprocess timed out, terminating...")
            process.kill()
            self.resource_manager.unregister_process(process)
            raise
        except Exception as e:
            logger.error(f"Error waiting for subprocess: {e}")
            self.resource_manager.unregister_process(process)
            raise
