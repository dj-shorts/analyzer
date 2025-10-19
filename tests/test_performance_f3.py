"""
Epic F3: Performance Tests and Profiling

Performance tests for the analyzer pipeline focusing on:
- Processing time for 60-minute videos
- CPU and RAM usage monitoring
- STFT/FFT parameter optimization
- Memory usage profiling
- Performance benchmarks and regression tests
"""

import pytest
import time
import psutil
import os
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
import librosa
from memory_profiler import profile
import cProfile
import pstats
import io

from src.analyzer.core import Analyzer
from src.analyzer.config import Config
from src.analyzer.novelty import NoveltyDetector
from src.analyzer.beats import BeatTracker


class TestPerformanceEpicF3:
    """Performance tests for the analyzer pipeline."""
    
    def setup_method(self):
        """Set up test fixtures for performance testing."""
        self.test_videos_dir = Path(__file__).parent.parent / "clips"
        self.youtube_shorts_video = self.test_videos_dir / "youtube_shorts" / "clip_001_youtube_shorts.mp4"
        
        # Performance monitoring
        self.process = psutil.Process(os.getpid())
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
    def teardown_method(self):
        """Clean up after performance tests."""
        # Force garbage collection
        import gc
        gc.collect()
    
    @pytest.mark.skipif(not Path(__file__).parent.parent.joinpath("clips/youtube_shorts/clip_001_youtube_shorts.mp4").exists(), 
                       reason="Test video files not available")
    def test_analysis_performance_60min_target(self):
        """Test analysis performance with target ≤8 minutes for 6 clips."""
        if not self.youtube_shorts_video.exists():
            pytest.skip("Test video files not available")
        
        # Create temporary output files
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as json_file:
            json_path = json_file.name
        
        try:
            # Monitor performance
            start_time = time.time()
            start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            
            # Run CLI analysis
            result = subprocess.run([
                'uv', 'run', 'python', '-m', 'src.analyzer.cli',
                str(self.youtube_shorts_video),
                '--clips', '6',
                '--min-len', '15.0',
                '--max-len', '30.0',
                '--out-json', json_path,
                '--verbose'
            ], capture_output=True, text=True, timeout=600)  # 10 minute timeout
            
            end_time = time.time()
            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            
            # Verify successful execution
            assert result.returncode == 0, f"CLI failed: {result.stderr}"
            
            # Performance metrics
            analysis_time = end_time - start_time
            memory_usage = end_memory - start_memory
            
            # Target: ≤8 minutes for 6 clips (this is a 30-second video, so should be much faster)
            # Scale factor: 30s video vs 60min = 120x scale factor
            # Expected time: 8min / 120 = 4 seconds
            expected_max_time = 4.0  # seconds for 30s video
            
            print(f"\nPerformance Metrics:")
            print(f"  Analysis time: {analysis_time:.2f}s")
            print(f"  Memory usage: {memory_usage:.2f}MB")
            print(f"  Expected max time: {expected_max_time:.2f}s")
            
            # Verify performance targets
            assert analysis_time <= expected_max_time, f"Analysis took {analysis_time:.2f}s, expected ≤{expected_max_time:.2f}s"
            assert memory_usage < 500, f"Memory usage {memory_usage:.2f}MB too high"
            
            # Verify output quality
            assert os.path.exists(json_path)
            import json
            with open(json_path, 'r') as f:
                json_data = json.load(f)
            
            assert len(json_data['clips']) == 6
        
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
    
    def test_stft_parameter_optimization(self):
        """Test different STFT parameters for performance optimization."""
        # Create synthetic audio data (1 minute)
        duration = 60.0  # 1 minute
        sr = 22050
        audio = np.random.randn(int(duration * sr)) * 0.1
        
        audio_data = {
            'audio': audio,
            'sample_rate': sr,
            'duration': duration
        }
        
        # Test different STFT parameters
        stft_configs = [
            {'hop_length': 512, 'window_size': 2048, 'name': 'default'},
            {'hop_length': 1024, 'window_size': 4096, 'name': 'larger_window'},
            {'hop_length': 256, 'window_size': 1024, 'name': 'smaller_window'},
            {'hop_length': 512, 'window_size': 1024, 'name': 'small_window'},
        ]
        
        results = []
        
        for config in stft_configs:
            # Create config
            test_config = Config(
                input_path=Path("test.mp4"),
                clips_count=6
            )
            
            # Create novelty detector with custom parameters
            detector = NoveltyDetector(test_config)
            detector.hop_length = config['hop_length']
            detector.window_size = config['window_size']
            
            # Measure performance
            start_time = time.time()
            start_memory = self.process.memory_info().rss / 1024 / 1024
            
            novelty_result = detector.compute_novelty(audio_data)
            
            end_time = time.time()
            end_memory = self.process.memory_info().rss / 1024 / 1024
            
            processing_time = end_time - start_time
            memory_usage = end_memory - start_memory
            
            results.append({
                'config': config['name'],
                'hop_length': config['hop_length'],
                'window_size': config['window_size'],
                'time': processing_time,
                'memory': memory_usage,
                'frames': len(novelty_result['time_axis'])
            })
            
            print(f"STFT Config {config['name']}: {processing_time:.3f}s, {memory_usage:.2f}MB, {len(novelty_result['time_axis'])} frames")
        
        # Find optimal configuration
        optimal_config = min(results, key=lambda x: x['time'])
        print(f"\nOptimal STFT config: {optimal_config['config']} ({optimal_config['time']:.3f}s)")
        
        # Verify reasonable performance
        assert optimal_config['time'] < 5.0, f"STFT processing too slow: {optimal_config['time']:.3f}s"
        assert optimal_config['memory'] < 100, f"STFT memory usage too high: {optimal_config['memory']:.2f}MB"
    
    def test_memory_profiling_novelty_detection(self):
        """Profile memory usage during novelty detection."""
        # Create longer synthetic audio (5 minutes)
        duration = 300.0  # 5 minutes
        sr = 22050
        audio = np.random.randn(int(duration * sr)) * 0.1
        
        audio_data = {
            'audio': audio,
            'sample_rate': sr,
            'duration': duration
        }
        
        # Profile memory usage
        @profile
        def profile_novelty_detection():
            test_config = Config(input_path=Path("test.mp4"))
            detector = NoveltyDetector(test_config)
            return detector.compute_novelty(audio_data)
        
        # Run profiling
        result = profile_novelty_detection()
        
        # Verify result quality
        assert 'time_axis' in result
        assert 'novelty_scores' in result
        assert len(result['time_axis']) > 0
        
        # Check memory efficiency
        current_memory = self.process.memory_info().rss / 1024 / 1024
        memory_increase = current_memory - self.initial_memory
        
        print(f"\nMemory Profiling Results:")
        print(f"  Initial memory: {self.initial_memory:.2f}MB")
        print(f"  Current memory: {current_memory:.2f}MB")
        print(f"  Memory increase: {memory_increase:.2f}MB")
        print(f"  Frames processed: {len(result['time_axis'])}")
        
        # Verify reasonable memory usage
        assert memory_increase < 200, f"Memory increase too high: {memory_increase:.2f}MB"
    
    def test_cpu_profiling_beat_tracking(self):
        """Profile CPU usage during beat tracking."""
        # Create synthetic audio with clear beats
        duration = 120.0  # 2 minutes
        sr = 22050
        t = np.linspace(0, duration, int(duration * sr))
        
        # Create audio with 120 BPM (2 beats per second)
        beat_freq = 2.0  # Hz
        audio = np.sin(2 * np.pi * beat_freq * t) * 0.3
        audio += np.random.randn(len(audio)) * 0.05  # Add some noise
        
        audio_data = {
            'audio': audio,
            'sample_rate': sr,
            'duration': duration
        }
        
        # Profile CPU usage
        profiler = cProfile.Profile()
        profiler.enable()
        
        # Run beat tracking
        test_config = Config(input_path=Path("test.mp4"))
        beat_tracker = BeatTracker(test_config)
        beat_result = beat_tracker.track_beats(audio_data)
        
        profiler.disable()
        
        # Analyze profiling results
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(10)  # Top 10 functions
        
        profiling_output = s.getvalue()
        print(f"\nCPU Profiling Results for Beat Tracking:")
        print(profiling_output)
        
        # Verify beat tracking quality
        assert 'beat_times' in beat_result
        assert 'tempo' in beat_result
        assert 'confidence' in beat_result
        
        # Verify reasonable tempo detection
        detected_tempo = beat_result['tempo']
        expected_tempo = 120.0  # BPM
        tempo_error = abs(detected_tempo - expected_tempo) / expected_tempo
        
        print(f"\nBeat Tracking Quality:")
        print(f"  Expected tempo: {expected_tempo} BPM")
        print(f"  Detected tempo: {detected_tempo:.2f} BPM")
        print(f"  Tempo error: {tempo_error:.2%}")
        
        # Verify reasonable tempo detection (within 20% error)
        assert tempo_error < 0.2, f"Tempo detection error too high: {tempo_error:.2%}"
    
    def test_concurrent_analysis_performance(self):
        """Test performance with concurrent analysis tasks."""
        import concurrent.futures
        import threading
        
        # Create multiple synthetic audio files
        audio_files = []
        for i in range(3):  # 3 concurrent tasks
            duration = 60.0  # 1 minute each
            sr = 22050
            audio = np.random.randn(int(duration * sr)) * 0.1
            
            audio_data = {
                'audio': audio,
                'sample_rate': sr,
                'duration': duration
            }
            audio_files.append(audio_data)
        
        def analyze_audio(audio_data):
            """Analyze single audio file."""
            test_config = Config(input_path=Path("test.mp4"))
            detector = NoveltyDetector(test_config)
            return detector.compute_novelty(audio_data)
        
        # Run concurrent analysis
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(analyze_audio, audio_data) for audio_data in audio_files]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024
        
        concurrent_time = end_time - start_time
        memory_usage = end_memory - start_memory
        
        print(f"\nConcurrent Analysis Performance:")
        print(f"  Concurrent time: {concurrent_time:.2f}s")
        print(f"  Memory usage: {memory_usage:.2f}MB")
        print(f"  Tasks completed: {len(results)}")
        
        # Verify all tasks completed successfully
        assert len(results) == 3
        for result in results:
            assert 'time_axis' in result
            assert 'novelty_scores' in result
        
        # Verify reasonable concurrent performance
        assert concurrent_time < 15.0, f"Concurrent analysis too slow: {concurrent_time:.2f}s"
        assert memory_usage < 300, f"Concurrent memory usage too high: {memory_usage:.2f}MB"
    
    def test_large_file_memory_efficiency(self):
        """Test memory efficiency with large audio files."""
        # Create large synthetic audio (10 minutes)
        duration = 600.0  # 10 minutes
        sr = 22050
        audio = np.random.randn(int(duration * sr)) * 0.1
        
        audio_data = {
            'audio': audio,
            'sample_rate': sr,
            'duration': duration
        }
        
        # Monitor memory usage
        start_memory = self.process.memory_info().rss / 1024 / 1024
        
        # Process in chunks to test memory efficiency
        chunk_size = int(60 * sr)  # 1 minute chunks
        chunks = [audio[i:i+chunk_size] for i in range(0, len(audio), chunk_size)]
        
        results = []
        for i, chunk in enumerate(chunks):
            chunk_data = {
                'audio': chunk,
                'sample_rate': sr,
                'duration': len(chunk) / sr
            }
            
            test_config = Config(input_path=Path("test.mp4"))
            detector = NoveltyDetector(test_config)
            result = detector.compute_novelty(chunk_data)
            results.append(result)
            
            # Check memory usage after each chunk
            current_memory = self.process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - start_memory
            
            print(f"Chunk {i+1}/{len(chunks)}: Memory increase: {memory_increase:.2f}MB")
            
            # Verify memory doesn't grow excessively
            assert memory_increase < 500, f"Memory usage too high after chunk {i+1}: {memory_increase:.2f}MB"
        
        # Verify all chunks processed successfully
        assert len(results) == len(chunks)
        for result in results:
            assert 'time_axis' in result
            assert 'novelty_scores' in result
        
        print(f"\nLarge File Processing:")
        print(f"  Total chunks: {len(chunks)}")
        print(f"  Final memory increase: {memory_increase:.2f}MB")
    
    def test_performance_regression_detection(self):
        """Test for performance regressions by comparing with baseline."""
        # Create baseline performance data
        duration = 60.0  # 1 minute
        sr = 22050
        audio = np.random.randn(int(duration * sr)) * 0.1
        
        audio_data = {
            'audio': audio,
            'sample_rate': sr,
            'duration': duration
        }
        
        # Measure current performance
        test_config = Config(input_path=Path("test.mp4"))
        detector = NoveltyDetector(test_config)
        
        start_time = time.time()
        result = detector.compute_novelty(audio_data)
        processing_time = time.time() - start_time
        
        # Baseline performance (these are target values)
        baseline_time = 2.0  # seconds for 1 minute of audio
        baseline_memory = 50  # MB
        
        current_memory = self.process.memory_info().rss / 1024 / 1024
        memory_usage = current_memory - self.initial_memory
        
        print(f"\nPerformance Regression Test:")
        print(f"  Current time: {processing_time:.2f}s")
        print(f"  Baseline time: {baseline_time:.2f}s")
        print(f"  Current memory: {memory_usage:.2f}MB")
        print(f"  Baseline memory: {baseline_memory:.2f}MB")
        
        # Check for performance regression (allow 20% degradation)
        time_regression = processing_time / baseline_time
        memory_regression = memory_usage / baseline_memory
        
        print(f"  Time regression factor: {time_regression:.2f}x")
        print(f"  Memory regression factor: {memory_regression:.2f}x")
        
        # Verify no significant regression
        assert time_regression <= 1.2, f"Performance regression detected: {time_regression:.2f}x slower"
        assert memory_regression <= 1.5, f"Memory regression detected: {memory_regression:.2f}x more memory"
        
        # Verify result quality maintained
        assert 'time_axis' in result
        assert 'novelty_scores' in result
        assert len(result['time_axis']) > 0


class TestSTFTOptimizationEpicF3:
    """STFT parameter optimization tests."""
    
    def test_hop_length_optimization(self):
        """Test different hop lengths for optimal performance."""
        duration = 60.0
        sr = 22050
        audio = np.random.randn(int(duration * sr)) * 0.1
        
        hop_lengths = [256, 512, 1024, 2048]
        results = []
        
        for hop_length in hop_lengths:
            test_config = Config(input_path=Path("test.mp4"))
            detector = NoveltyDetector(test_config)
            detector.hop_length = hop_length
            
            start_time = time.time()
            result = detector.compute_novelty({
                'audio': audio,
                'sample_rate': sr,
                'duration': duration
            })
            processing_time = time.time() - start_time
            
            results.append({
                'hop_length': hop_length,
                'time': processing_time,
                'frames': len(result['time_axis']),
                'resolution': sr / hop_length
            })
            
            print(f"Hop length {hop_length}: {processing_time:.3f}s, {len(result['time_axis'])} frames, {sr/hop_length:.1f} Hz resolution")
        
        # Find optimal hop length
        optimal = min(results, key=lambda x: x['time'])
        print(f"\nOptimal hop length: {optimal['hop_length']} ({optimal['time']:.3f}s)")
        
        # Verify reasonable performance
        assert optimal['time'] < 3.0, f"Optimal hop length too slow: {optimal['time']:.3f}s"
    
    def test_window_size_optimization(self):
        """Test different window sizes for optimal performance."""
        duration = 60.0
        sr = 22050
        audio = np.random.randn(int(duration * sr)) * 0.1
        
        window_sizes = [1024, 2048, 4096, 8192]
        results = []
        
        for window_size in window_sizes:
            test_config = Config(input_path=Path("test.mp4"))
            detector = NoveltyDetector(test_config)
            detector.window_size = window_size
            
            start_time = time.time()
            result = detector.compute_novelty({
                'audio': audio,
                'sample_rate': sr,
                'duration': duration
            })
            processing_time = time.time() - start_time
            
            results.append({
                'window_size': window_size,
                'time': processing_time,
                'frames': len(result['time_axis']),
                'frequency_resolution': sr / window_size
            })
            
            print(f"Window size {window_size}: {processing_time:.3f}s, {len(result['time_axis'])} frames, {sr/window_size:.1f} Hz resolution")
        
        # Find optimal window size
        optimal = min(results, key=lambda x: x['time'])
        print(f"\nOptimal window size: {optimal['window_size']} ({optimal['time']:.3f}s)")
        
        # Verify reasonable performance
        assert optimal['time'] < 3.0, f"Optimal window size too slow: {optimal['time']:.3f}s"
