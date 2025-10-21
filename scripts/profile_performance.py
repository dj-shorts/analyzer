#!/usr/bin/env python3
"""
Performance profiling script for MVP Analyzer.

This script provides comprehensive performance analysis tools for the analyzer pipeline.
Usage:
    python scripts/profile_performance.py --input video.mp4 --clips 6
    python scripts/profile_performance.py --benchmark --duration 60
"""

import argparse
import time
import psutil
import os
import json
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import cProfile
import pstats
import io
from memory_profiler import profile

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analyzer.core import Analyzer
from analyzer.config import Config
from analyzer.novelty import NoveltyDetector
from analyzer.beats import BeatTracker


class PerformanceProfiler:
    """Comprehensive performance profiler for the analyzer."""
    
    def __init__(self):
        """Initialize the profiler."""
        self.process = psutil.Process(os.getpid())
        self.results = {}
    
    def profile_analysis(self, input_path: Path, clips_count: int = 6) -> Dict[str, Any]:
        """Profile complete analysis pipeline."""
        print(f"Profiling analysis of {input_path}")
        
        # Create configuration
        config = Config(
            input_path=input_path,
            clips_count=clips_count,
            min_clip_length=15.0,
            max_clip_length=30.0
        )
        
        # Monitor system resources
        start_cpu = self.process.cpu_percent()
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        # Profile CPU usage
        profiler = cProfile.Profile()
        profiler.enable()
        
        start_time = time.time()
        
        # Run analysis
        analyzer = Analyzer(config)
        result = analyzer.analyze()
        
        end_time = time.time()
        profiler.disable()
        
        # Calculate metrics
        analysis_time = end_time - start_time
        end_cpu = self.process.cpu_percent()
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        cpu_usage = end_cpu - start_cpu
        memory_usage = end_memory - start_memory
        
        # Get profiling stats
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(10)  # Top 10 functions
        profiling_output = s.getvalue()
        
        # Compile results
        profile_result = {
            'input_file': str(input_path),
            'clips_count': clips_count,
            'analysis_time': analysis_time,
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'clips_generated': len(result.get('clips', [])),
            'profiling_stats': profiling_output,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print(f"\nPerformance Results:")
        print(f"  Analysis time: {analysis_time:.2f}s")
        print(f"  CPU usage: {cpu_usage:.1f}%")
        print(f"  Memory usage: {memory_usage:.2f}MB")
        print(f"  Clips generated: {len(result.get('clips', []))}")
        
        return profile_result
    
    @profile
    def profile_novelty_detection(self, audio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Profile novelty detection with memory profiling."""
        print("Profiling novelty detection...")
        
        config = Config(input_path=Path("test.mp4"))
        detector = NoveltyDetector(config)
        
        start_time = time.time()
        result = detector.compute_novelty(audio_data)
        processing_time = time.time() - start_time
        
        print(f"Novelty detection: {processing_time:.3f}s")
        return result
    
    def benchmark_stft_parameters(self, duration: float = 60.0) -> Dict[str, Any]:
        """Benchmark different STFT parameters."""
        print(f"Benchmarking STFT parameters for {duration}s audio...")
        
        # Create synthetic audio
        sr = 22050
        audio = np.random.randn(int(duration * sr)) * 0.1
        
        audio_data = {
            'audio': audio,
            'sample_rate': sr,
            'duration': duration
        }
        
        # Test different configurations
        configurations = [
            {'hop_length': 256, 'window_size': 1024, 'name': 'high_resolution'},
            {'hop_length': 512, 'window_size': 2048, 'name': 'default'},
            {'hop_length': 1024, 'window_size': 4096, 'name': 'optimized'},
            {'hop_length': 2048, 'window_size': 8192, 'name': 'low_resolution'},
        ]
        
        results = []
        
        for config in configurations:
            test_config = Config(input_path=Path("test.mp4"))
            detector = NoveltyDetector(test_config)
            detector.hop_length = config['hop_length']
            detector.window_size = config['window_size']
            
            start_time = time.time()
            start_memory = self.process.memory_info().rss / 1024 / 1024
            
            result = detector.compute_novelty(audio_data)
            
            end_time = time.time()
            end_memory = self.process.memory_info().rss / 1024 / 1024
            
            processing_time = end_time - start_time
            memory_usage = end_memory - start_memory
            
            results.append({
                'name': config['name'],
                'hop_length': config['hop_length'],
                'window_size': config['window_size'],
                'time': processing_time,
                'memory': memory_usage,
                'frames': len(result['time_axis']),
                'resolution': sr / config['hop_length']
            })
            
            print(f"  {config['name']}: {processing_time:.3f}s, {memory_usage:.2f}MB, {len(result['time_axis'])} frames")
        
        # Find optimal configuration
        optimal = min(results, key=lambda x: x['time'])
        print(f"\nOptimal configuration: {optimal['name']} ({optimal['time']:.3f}s)")
        
        return {
            'configurations': results,
            'optimal': optimal,
            'duration': duration
        }
    
    def performance_regression_test(self, baseline_file: str = "baseline_performance.json") -> bool:
        """Test for performance regressions against baseline."""
        print("Running performance regression test...")
        
        # Load baseline if exists
        baseline_path = Path(baseline_file)
        if baseline_path.exists():
            with open(baseline_path, 'r') as f:
                baseline = json.load(f)
        else:
            print(f"No baseline file found at {baseline_file}")
            return False
        
        # Run current performance test
        # This would typically use a standard test video
        # For now, we'll use synthetic data
        duration = 60.0
        sr = 22050
        audio = np.random.randn(int(duration * sr)) * 0.1
        
        audio_data = {
            'audio': audio,
            'sample_rate': sr,
            'duration': duration
        }
        
        config = Config(input_path=Path("test.mp4"))
        detector = NoveltyDetector(config)
        
        start_time = time.time()
        result = detector.compute_novelty(audio_data)
        current_time = time.time() - start_time
        
        # Compare with baseline
        baseline_time = baseline.get('novelty_detection_time', 2.0)
        regression_factor = current_time / baseline_time
        
        print(f"Baseline time: {baseline_time:.3f}s")
        print(f"Current time: {current_time:.3f}s")
        print(f"Regression factor: {regression_factor:.2f}x")
        
        # Check for significant regression (20% threshold)
        if regression_factor > 1.2:
            print(f"⚠️  Performance regression detected: {regression_factor:.2f}x slower")
            return False
        else:
            print(f"✅ Performance within acceptable range")
            return True
    
    def save_baseline(self, output_file: str = "baseline_performance.json"):
        """Save current performance as baseline."""
        print("Saving performance baseline...")
        
        # Run standard benchmark
        duration = 60.0
        sr = 22050
        audio = np.random.randn(int(duration * sr)) * 0.1
        
        audio_data = {
            'audio': audio,
            'sample_rate': sr,
            'duration': duration
        }
        
        config = Config(input_path=Path("test.mp4"))
        detector = NoveltyDetector(config)
        
        start_time = time.time()
        result = detector.compute_novelty(audio_data)
        processing_time = time.time() - start_time
        
        baseline = {
            'novelty_detection_time': processing_time,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration': duration,
            'frames': len(result['time_axis'])
        }
        
        with open(output_file, 'w') as f:
            json.dump(baseline, f, indent=2)
        
        print(f"Baseline saved to {output_file}")
        print(f"Novelty detection time: {processing_time:.3f}s")


def main():
    """Main function for performance profiling."""
    parser = argparse.ArgumentParser(description="Performance profiler for MVP Analyzer")
    parser.add_argument("--input", type=Path, help="Input video file to profile")
    parser.add_argument("--clips", type=int, default=6, help="Number of clips to extract")
    parser.add_argument("--benchmark", action="store_true", help="Run STFT parameter benchmark")
    parser.add_argument("--duration", type=float, default=60.0, help="Duration for synthetic audio benchmark")
    parser.add_argument("--regression", action="store_true", help="Run performance regression test")
    parser.add_argument("--baseline", action="store_true", help="Save performance baseline")
    parser.add_argument("--output", type=str, default="performance_results.json", help="Output file for results")
    
    args = parser.parse_args()
    
    profiler = PerformanceProfiler()
    
    if args.baseline:
        profiler.save_baseline(args.output)
    elif args.regression:
        success = profiler.performance_regression_test()
        sys.exit(0 if success else 1)
    elif args.benchmark:
        results = profiler.benchmark_stft_parameters(args.duration)
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Benchmark results saved to {args.output}")
    elif args.input:
        if not args.input.exists():
            print(f"Error: Input file {args.input} does not exist")
            sys.exit(1)
        
        results = profiler.profile_analysis(args.input, args.clips)
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Profile results saved to {args.output}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
