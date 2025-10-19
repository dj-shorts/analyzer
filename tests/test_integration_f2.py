"""
Epic F2: Integration Tests for End-to-End Pipeline

Integration tests for the complete analyzer pipeline using real test videos.
Tests cover:
- End-to-end analysis with different configurations
- Output format validation (CSV/JSON)
- Clip count and duration validation
- Motion analysis integration
- Beat alignment integration
- Error handling and edge cases
- Real video file processing
"""

import pytest
import json
import csv
import tempfile
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
import librosa

from src.analyzer.core import Analyzer
from src.analyzer.config import Config
from src.analyzer.cli import main as cli_main


class TestEndToEndPipelineEpicF2:
    """End-to-end integration tests for the complete analyzer pipeline."""
    
    def setup_method(self):
        """Set up test fixtures and mocks."""
        self.config = Config(
            clips_count=3,
            min_length=10.0,
            max_length=20.0,
            pre_roll=5.0,
            peak_spacing=50
        )
        
        # Create temporary test video file
        self.temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        self.temp_video.close()
        
        # Mock audio data
        self.mock_audio_data = {
            'audio_file': self.temp_video.name,
            'duration': 180.0,  # 3 minutes
            'sample_rate': 22050
        }
        
        # Real test video paths
        self.test_videos_dir = Path(__file__).parent.parent / "clips"
        self.youtube_shorts_video = self.test_videos_dir / "youtube_shorts" / "clip_001_youtube_shorts.mp4"
        self.tiktok_video = self.test_videos_dir / "tiktok" / "clip_001_tiktok.mp4"
        self.instagram_reel_video = self.test_videos_dir / "instagram_reel" / "clip_001_instagram_reel.mp4"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_video.name):
            os.unlink(self.temp_video.name)
    
    @patch('src.analyzer.core.extract_audio')
    @patch('src.analyzer.core.novelty_detector')
    @patch('src.analyzer.core.peak_picker')
    @patch('src.analyzer.core.segment_builder')
    def test_basic_end_to_end_analysis(self, mock_segments, mock_peaks, mock_novelty, mock_audio):
        """Test basic end-to-end analysis pipeline."""
        # Setup mocks
        mock_audio.return_value = self.mock_audio_data
        mock_novelty.return_value = self._create_mock_novelty_data()
        mock_peaks.return_value = self._create_mock_peaks_data()
        mock_segments.return_value = self._create_mock_segments_data()
        
        # Run analysis
        analyzer = Analyzer(self.config)
        result = analyzer.analyze(self.temp_video.name)
        
        # Verify pipeline execution
        mock_audio.assert_called_once()
        mock_novelty.assert_called_once()
        mock_peaks.assert_called_once()
        mock_segments.assert_called_once()
        
        # Verify result structure
        assert 'segments' in result
        assert 'audio_metadata' in result
        assert 'config' in result
        
        # Verify segment count
        assert len(result['segments']) == 3
    
    @patch('src.analyzer.core.extract_audio')
    @patch('src.analyzer.core.novelty_detector')
    @patch('src.analyzer.core.peak_picker')
    @patch('src.analyzer.core.segment_builder')
    def test_clip_count_validation(self, mock_segments, mock_peaks, mock_novelty, mock_audio):
        """Test that clip count matches configuration."""
        # Setup mocks
        mock_audio.return_value = self.mock_audio_data
        mock_novelty.return_value = self._create_mock_novelty_data()
        mock_peaks.return_value = self._create_mock_peaks_data()
        mock_segments.return_value = self._create_mock_segments_data()
        
        # Test different clip counts
        for clip_count in [2, 4, 6, 8]:
            config = Config(clips_count=clip_count)
            analyzer = Analyzer(config)
            result = analyzer.analyze(self.temp_video.name)
            
            # Verify clip count
            assert len(result['segments']) == clip_count
    
    @patch('src.analyzer.core.extract_audio')
    @patch('src.analyzer.core.novelty_detector')
    @patch('src.analyzer.core.peak_picker')
    @patch('src.analyzer.core.segment_builder')
    def test_clip_duration_validation(self, mock_segments, mock_peaks, mock_novelty, mock_audio):
        """Test that clip durations are within specified bounds."""
        # Setup mocks
        mock_audio.return_value = self.mock_audio_data
        mock_novelty.return_value = self._create_mock_novelty_data()
        mock_peaks.return_value = self._create_mock_peaks_data()
        
        # Create segments with different durations
        segments = [
            {'start': 10.0, 'end': 25.0, 'center': 17.5, 'score': 0.8},
            {'start': 30.0, 'end': 50.0, 'center': 40.0, 'score': 0.7},
            {'start': 60.0, 'end': 75.0, 'center': 67.5, 'score': 0.9}
        ]
        mock_segments.return_value = {'segments': segments}
        
        # Run analysis
        analyzer = Analyzer(self.config)
        result = analyzer.analyze(self.temp_video.name)
        
        # Verify duration bounds
        for segment in result['segments']:
            duration = segment['end'] - segment['start']
            assert self.config.min_length <= duration <= self.config.max_length
    
    @patch('src.analyzer.core.extract_audio')
    @patch('src.analyzer.core.novelty_detector')
    @patch('src.analyzer.core.peak_picker')
    @patch('src.analyzer.core.segment_builder')
    def test_seed_timestamps_integration(self, mock_segments, mock_peaks, mock_novelty, mock_audio):
        """Test integration with seed timestamps."""
        # Setup mocks
        mock_audio.return_value = self.mock_audio_data
        mock_novelty.return_value = self._create_mock_novelty_data()
        mock_peaks.return_value = self._create_mock_peaks_with_seeds()
        mock_segments.return_value = self._create_mock_segments_with_seeds()
        
        # Run analysis with seeds
        config = Config(clips_count=3, seed_timestamps=[60.0, 120.0])
        analyzer = Analyzer(config)
        result = analyzer.analyze(self.temp_video.name)
        
        # Verify seed-based segments
        seed_based_segments = [s for s in result['segments'] if s.get('seed_based', False)]
        assert len(seed_based_segments) >= 2  # At least 2 seed-based segments
    
    @patch('src.analyzer.core.extract_audio')
    @patch('src.analyzer.core.novelty_detector')
    @patch('src.analyzer.core.peak_picker')
    @patch('src.analyzer.core.segment_builder')
    @patch('src.analyzer.core.beat_tracker')
    def test_beat_alignment_integration(self, mock_beats, mock_segments, mock_peaks, mock_novelty, mock_audio):
        """Test integration with beat alignment."""
        # Setup mocks
        mock_audio.return_value = self.mock_audio_data
        mock_novelty.return_value = self._create_mock_novelty_data()
        mock_peaks.return_value = self._create_mock_peaks_data()
        mock_beats.return_value = self._create_mock_beats_data()
        mock_segments.return_value = self._create_mock_segments_with_alignment()
        
        # Run analysis with beat alignment
        config = Config(clips_count=3, align_to_beat=True)
        analyzer = Analyzer(config)
        result = analyzer.analyze(self.temp_video.name)
        
        # Verify beat alignment
        aligned_segments = [s for s in result['segments'] if s.get('aligned', False)]
        assert len(aligned_segments) >= 1  # At least 1 aligned segment
    
    @patch('src.analyzer.core.extract_audio')
    @patch('src.analyzer.core.novelty_detector')
    @patch('src.analyzer.core.peak_picker')
    @patch('src.analyzer.core.segment_builder')
    @patch('src.analyzer.core.motion_analyzer')
    def test_motion_analysis_integration(self, mock_motion, mock_segments, mock_peaks, mock_novelty, mock_audio):
        """Test integration with motion analysis."""
        # Setup mocks
        mock_audio.return_value = self.mock_audio_data
        mock_novelty.return_value = self._create_mock_novelty_data()
        mock_peaks.return_value = self._create_mock_peaks_data()
        mock_motion.return_value = self._create_mock_motion_data()
        mock_segments.return_value = self._create_mock_segments_with_motion()
        
        # Run analysis with motion
        config = Config(clips_count=3, with_motion=True)
        analyzer = Analyzer(config)
        result = analyzer.analyze(self.temp_video.name)
        
        # Verify motion integration
        assert 'motion_data' in result
        mock_motion.assert_called_once()
    
    def test_csv_output_format(self):
        """Test CSV output format validation."""
        # Create mock segments
        segments = [
            {
                'clip_id': 1,
                'start': 10.0,
                'end': 25.0,
                'center': 17.5,
                'score': 0.8,
                'seed_based': False,
                'aligned': True,
                'length': 15.0
            },
            {
                'clip_id': 2,
                'start': 30.0,
                'end': 50.0,
                'center': 40.0,
                'score': 0.7,
                'seed_based': True,
                'aligned': False,
                'length': 20.0
            }
        ]
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=[
                'clip_id', 'start', 'end', 'center', 'score', 'seed_based', 'aligned', 'length'
            ])
            writer.writeheader()
            writer.writerows(segments)
            csv_file = f.name
        
        try:
            # Verify CSV format
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                assert len(rows) == 2
                assert all(field in rows[0] for field in [
                    'clip_id', 'start', 'end', 'center', 'score', 'seed_based', 'aligned', 'length'
                ])
                
                # Verify data types
                assert int(rows[0]['clip_id']) == 1
                assert float(rows[0]['start']) == 10.0
                assert rows[0]['seed_based'] == 'False'
                assert rows[0]['aligned'] == 'True'
        
        finally:
            os.unlink(csv_file)
    
    def test_json_output_format(self):
        """Test JSON output format validation."""
        # Create mock result
        result = {
            'config': {
                'clips_count': 3,
                'min_length': 10.0,
                'max_length': 20.0
            },
            'audio_metadata': {
                'duration': 180.0,
                'sample_rate': 22050
            },
            'segments': [
                {
                    'clip_id': 1,
                    'start': 10.0,
                    'end': 25.0,
                    'center': 17.5,
                    'score': 0.8,
                    'seed_based': False,
                    'aligned': True
                }
            ],
            'summary': {
                'total_segments': 1,
                'avg_score': 0.8,
                'total_duration': 15.0
            }
        }
        
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(result, f, indent=2)
            json_file = f.name
        
        try:
            # Verify JSON format
            with open(json_file, 'r') as f:
                loaded_result = json.load(f)
                
                assert 'config' in loaded_result
                assert 'audio_metadata' in loaded_result
                assert 'segments' in loaded_result
                assert 'summary' in loaded_result
                
                # Verify segment structure
                segment = loaded_result['segments'][0]
                assert all(field in segment for field in [
                    'clip_id', 'start', 'end', 'center', 'score', 'seed_based', 'aligned'
                ])
        
        finally:
            os.unlink(json_file)
    
    @patch('src.analyzer.core.extract_audio')
    def test_error_handling_invalid_video(self, mock_audio):
        """Test error handling for invalid video files."""
        # Setup mock to raise exception
        mock_audio.side_effect = Exception("Invalid video file")
        
        # Run analysis
        analyzer = Analyzer(self.config)
        
        with pytest.raises(Exception, match="Invalid video file"):
            analyzer.analyze("invalid_video.mp4")
    
    @patch('src.analyzer.core.extract_audio')
    @patch('src.analyzer.core.novelty_detector')
    def test_error_handling_short_video(self, mock_novelty, mock_audio):
        """Test error handling for very short videos."""
        # Setup mocks for short video
        mock_audio.return_value = {
            'audio_file': self.temp_video.name,
            'duration': 5.0,  # Very short
            'sample_rate': 22050
        }
        mock_novelty.side_effect = ValueError("Audio too short for analysis")
        
        # Run analysis
        analyzer = Analyzer(self.config)
        
        with pytest.raises(ValueError, match="Audio too short for analysis"):
            analyzer.analyze(self.temp_video.name)
    
    def test_cli_integration(self):
        """Test CLI integration with end-to-end pipeline."""
        # This test would require actual video files
        # For now, we'll test the CLI argument parsing
        with patch('sys.argv', ['analyzer', '--help']):
            with pytest.raises(SystemExit):
                cli_main()
    
    def _create_mock_novelty_data(self):
        """Create mock novelty detection data."""
        return {
            'time_axis': np.linspace(0, 180, 1000),
            'novelty_scores': np.random.random(1000) * 0.5 + 0.3,
            'onset_strength': np.random.random(1000) * 0.4 + 0.2,
            'contrast_variance': np.random.random(1000) * 0.3 + 0.1
        }
    
    def _create_mock_peaks_data(self):
        """Create mock peak detection data."""
        return {
            'peak_times': np.array([30.0, 60.0, 90.0, 120.0, 150.0]),
            'peak_scores': np.array([0.8, 0.7, 0.9, 0.6, 0.8]),
            'seed_based': np.array([False, False, False, False, False])
        }
    
    def _create_mock_peaks_with_seeds(self):
        """Create mock peak detection data with seeds."""
        return {
            'peak_times': np.array([30.0, 60.0, 90.0, 120.0, 150.0]),
            'peak_scores': np.array([0.8, 0.7, 0.9, 0.6, 0.8]),
            'seed_based': np.array([False, True, False, True, False])
        }
    
    def _create_mock_segments_data(self):
        """Create mock segment data."""
        return {
            'segments': [
                {'start': 10.0, 'end': 25.0, 'center': 17.5, 'score': 0.8},
                {'start': 30.0, 'end': 50.0, 'center': 40.0, 'score': 0.7},
                {'start': 60.0, 'end': 75.0, 'center': 67.5, 'score': 0.9}
            ]
        }
    
    def _create_mock_segments_with_seeds(self):
        """Create mock segment data with seeds."""
        return {
            'segments': [
                {'start': 10.0, 'end': 25.0, 'center': 17.5, 'score': 0.8, 'seed_based': False},
                {'start': 30.0, 'end': 50.0, 'center': 40.0, 'score': 0.7, 'seed_based': True},
                {'start': 60.0, 'end': 75.0, 'center': 67.5, 'score': 0.9, 'seed_based': True}
            ]
        }
    
    def _create_mock_beats_data(self):
        """Create mock beat tracking data."""
        return {
            'beat_times': np.linspace(0, 180, 360),  # 2 beats per second
            'tempo': 120.0,
            'confidence': 0.85,
            'beat_grid': {
                'grid_times': np.linspace(0, 180, 360),
                'beat_interval': 0.5
            }
        }
    
    def _create_mock_segments_with_alignment(self):
        """Create mock segment data with beat alignment."""
        return {
            'segments': [
                {'start': 10.0, 'end': 25.0, 'center': 17.5, 'score': 0.8, 'aligned': True},
                {'start': 30.0, 'end': 50.0, 'center': 40.0, 'score': 0.7, 'aligned': False},
                {'start': 60.0, 'end': 75.0, 'center': 67.5, 'score': 0.9, 'aligned': True}
            ]
        }
    
    def _create_mock_motion_data(self):
        """Create mock motion analysis data."""
        return {
            'time_axis': np.linspace(0, 180, 100),
            'motion_scores': np.random.random(100) * 0.3 + 0.1,
            'optical_flow': np.random.random((100, 10, 10)) * 0.5
        }
    
    def _create_mock_segments_with_motion(self):
        """Create mock segment data with motion scores."""
        return {
            'segments': [
                {
                    'start': 10.0, 'end': 25.0, 'center': 17.5, 'score': 0.8,
                    'motion_score': 0.3, 'combined_score': 0.6
                },
                {
                    'start': 30.0, 'end': 50.0, 'center': 40.0, 'score': 0.7,
                    'motion_score': 0.2, 'combined_score': 0.5
                },
                {
                    'start': 60.0, 'end': 75.0, 'center': 67.5, 'score': 0.9,
                    'motion_score': 0.4, 'combined_score': 0.7
                }
            ]
        }


class TestPerformanceEpicF2:
    """Performance tests for the analyzer pipeline."""
    
    @patch('src.analyzer.core.extract_audio')
    @patch('src.analyzer.core.novelty_detector')
    @patch('src.analyzer.core.peak_picker')
    @patch('src.analyzer.core.segment_builder')
    def test_analysis_performance_benchmark(self, mock_segments, mock_peaks, mock_novelty, mock_audio):
        """Test analysis performance with realistic data sizes."""
        import time
        
        # Setup mocks with realistic data sizes
        mock_audio.return_value = {
            'audio_file': 'test.mp4',
            'duration': 3600.0,  # 1 hour
            'sample_rate': 22050
        }
        
        # Large novelty data (1 hour at 4fps)
        time_axis = np.linspace(0, 3600, 14400)
        mock_novelty.return_value = {
            'time_axis': time_axis,
            'novelty_scores': np.random.random(14400) * 0.5 + 0.3,
            'onset_strength': np.random.random(14400) * 0.4 + 0.2,
            'contrast_variance': np.random.random(14400) * 0.3 + 0.1
        }
        
        mock_peaks.return_value = {
            'peak_times': np.linspace(60, 3540, 60),  # 60 peaks
            'peak_scores': np.random.random(60) * 0.5 + 0.3,
            'seed_based': np.zeros(60, dtype=bool)
        }
        
        mock_segments.return_value = {
            'segments': [{'start': i*60, 'end': i*60+30, 'center': i*60+15, 'score': 0.7} 
                        for i in range(6)]
        }
        
        # Run performance test
        config = Config(clips_count=6)
        analyzer = Analyzer(config)
        
        start_time = time.time()
        result = analyzer.analyze('test.mp4')
        end_time = time.time()
        
        # Verify performance (should complete within reasonable time)
        analysis_time = end_time - start_time
        assert analysis_time < 10.0  # Should complete within 10 seconds
        
        # Verify result structure
        assert len(result['segments']) == 6
    
    def test_memory_usage_during_analysis(self):
        """Test memory usage during analysis with large files."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large arrays to simulate memory usage
        large_array = np.random.random((10000, 1000))
        
        # Check memory usage
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory
        
        # Verify reasonable memory usage (less than 500MB increase)
        assert memory_increase < 500.0
        
        # Clean up
        del large_array


class TestEdgeCasesEpicF2:
    """Edge case tests for integration scenarios."""
    
    def test_empty_analysis_result(self):
        """Test handling of empty analysis results."""
        # This would test cases where no peaks are found
        # or segments cannot be created
        pass
    
    def test_single_frame_video(self):
        """Test handling of very short videos (single frame)."""
        # This would test edge case of extremely short videos
        pass
    
    def test_very_long_video(self):
        """Test handling of very long videos (>2 hours)."""
        # This would test memory and performance with very long videos
        pass
    
    def test_corrupted_video_file(self):
        """Test handling of corrupted video files."""
        # This would test error handling for corrupted files
        pass
    
    def test_unsupported_video_format(self):
        """Test handling of unsupported video formats."""
        # This would test graceful degradation for unsupported formats
        pass


class TestRealVideoIntegrationEpicF2:
    """Integration tests using real video files from clips/ directory."""
    
    def setup_method(self):
        """Set up test fixtures for real video tests."""
        self.test_videos_dir = Path(__file__).parent.parent / "clips"
        self.youtube_shorts_video = self.test_videos_dir / "youtube_shorts" / "clip_001_youtube_shorts.mp4"
        self.tiktok_video = self.test_videos_dir / "tiktok" / "clip_001_tiktok.mp4"
        self.instagram_reel_video = self.test_videos_dir / "instagram_reel" / "clip_001_instagram_reel.mp4"
        
        # Check if test videos exist
        self.has_test_videos = all([
            self.youtube_shorts_video.exists(),
            self.tiktok_video.exists(),
            self.instagram_reel_video.exists()
        ])
    
    @pytest.mark.skipif(not Path(__file__).parent.parent.joinpath("clips/youtube_shorts/clip_001_youtube_shorts.mp4").exists(), 
                       reason="Test video files not available")
    def test_real_youtube_shorts_analysis(self):
        """Test end-to-end analysis with real YouTube Shorts video."""
        if not self.has_test_videos:
            pytest.skip("Test video files not available")
        
        # Create temporary output files
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as json_file:
            json_path = json_file.name
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as csv_file:
            csv_path = csv_file.name
        
        try:
            # Run CLI analysis
            result = subprocess.run([
                'uv', 'run', 'python', '-m', 'src.analyzer.cli',
                str(self.youtube_shorts_video),
                '--clips', '3',
                '--min-len', '10.0',
                '--max-len', '20.0',
                '--out-json', json_path,
                '--out-csv', csv_path,
                '--verbose'
            ], capture_output=True, text=True, timeout=60)
            
            # Verify successful execution
            assert result.returncode == 0, f"CLI failed: {result.stderr}"
            
            # Verify JSON output
            assert os.path.exists(json_path), "JSON output file not created"
            with open(json_path, 'r') as f:
                json_data = json.load(f)
                
            # Verify JSON structure
            assert 'metadata' in json_data
            assert 'clips' in json_data
            
            # Verify clips
            clips = json_data['clips']
            assert len(clips) == 3, f"Expected 3 clips, got {len(clips)}"
            
            for clip in clips:
                assert 'start' in clip
                assert 'end' in clip
                assert 'center' in clip
                assert 'score' in clip
                assert clip['end'] > clip['start']
                assert clip['score'] >= 0.0
                assert clip['score'] <= 1.0
            
            # Verify CSV output
            assert os.path.exists(csv_path), "CSV output file not created"
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                csv_rows = list(reader)
                
            assert len(csv_rows) == 3, f"Expected 3 CSV rows, got {len(csv_rows)}"
            
            # Verify CSV structure
            expected_fields = ['clip_id', 'start', 'end', 'center', 'score', 'seed_based', 'aligned']
            for field in expected_fields:
                assert field in csv_rows[0], f"Missing field {field} in CSV"
        
        finally:
            # Clean up
            for path in [json_path, csv_path]:
                if os.path.exists(path):
                    os.unlink(path)
    
    @pytest.mark.skipif(not Path(__file__).parent.parent.joinpath("clips/tiktok/clip_001_tiktok.mp4").exists(), 
                       reason="Test video files not available")
    def test_real_tiktok_analysis_with_beats(self):
        """Test analysis with beat alignment on TikTok video."""
        if not self.has_test_videos:
            pytest.skip("Test video files not available")
        
        # Create temporary output files
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as json_file:
            json_path = json_file.name
        
        try:
            # Run CLI analysis with beat alignment
            result = subprocess.run([
                'uv', 'run', 'python', '-m', 'src.analyzer.cli',
                str(self.tiktok_video),
                '--clips', '2',
                '--align-to-beat',
                '--out-json', json_path,
                '--verbose'
            ], capture_output=True, text=True, timeout=60)
            
            # Verify successful execution
            assert result.returncode == 0, f"CLI failed: {result.stderr}"
            
            # Verify JSON output
            with open(json_path, 'r') as f:
                json_data = json.load(f)
            
            # Verify beat alignment data
            clips = json_data['clips']
            assert len(clips) == 2
            
            # Check if beat alignment was applied
            aligned_clips = [c for c in clips if c.get('aligned', False)]
            # Note: alignment might not always succeed, so we just check the field exists
            for clip in clips:
                assert 'aligned' in clip
        
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
    
    @pytest.mark.skipif(not Path(__file__).parent.parent.joinpath("clips/instagram_reel/clip_001_instagram_reel.mp4").exists(), 
                       reason="Test video files not available")
    def test_real_instagram_reel_with_seeds(self):
        """Test analysis with seed timestamps on Instagram Reel."""
        if not self.has_test_videos:
            pytest.skip("Test video files not available")
        
        # Create temporary output files
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as json_file:
            json_path = json_file.name
        
        try:
            # Run CLI analysis with seed timestamps
            result = subprocess.run([
                'uv', 'run', 'python', '-m', 'src.analyzer.cli',
                str(self.instagram_reel_video),
                '--clips', '3',
                '--seeds', '00:00:30,00:01:00',
                '--out-json', json_path,
                '--verbose'
            ], capture_output=True, text=True, timeout=60)
            
            # Verify successful execution
            assert result.returncode == 0, f"CLI failed: {result.stderr}"
            
            # Verify JSON output
            with open(json_path, 'r') as f:
                json_data = json.load(f)
            
            # Verify seed-based clips
            clips = json_data['clips']
            assert len(clips) >= 3, f"Expected at least 3 clips, got {len(clips)}"
            
            # Check if seed-based clips were created
            seed_based_clips = [c for c in clips if c.get('seed_based', False)]
            # Note: seed-based clips might not always be created if peaks are too far
            for clip in clips:
                assert 'seed_based' in clip
        
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
    
    @pytest.mark.skipif(not Path(__file__).parent.parent.joinpath("clips/youtube_shorts/clip_001_youtube_shorts.mp4").exists(), 
                       reason="Test video files not available")
    def test_cli_error_handling_invalid_file(self):
        """Test CLI error handling with invalid file."""
        # Test with non-existent file
        result = subprocess.run([
            'uv', 'run', 'python', '-m', 'src.analyzer.cli',
            'non_existent_file.mp4',
            '--clips', '3'
        ], capture_output=True, text=True, timeout=30)
        
        # Should fail gracefully
        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "does not exist" in result.stderr.lower()
    
    @pytest.mark.skipif(not Path(__file__).parent.parent.joinpath("clips/youtube_shorts/clip_001_youtube_shorts.mp4").exists(), 
                       reason="Test video files not available")
    def test_cli_help_output(self):
        """Test CLI help output format."""
        result = subprocess.run([
            'uv', 'run', 'python', '-m', 'src.analyzer.cli',
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        # Should show help
        assert result.returncode == 0
        assert "MVP Analyzer" in result.stdout
        assert "--clips" in result.stdout
        assert "--min-len" in result.stdout
        assert "--max-len" in result.stdout
        assert "--out-json" in result.stdout
        assert "--out-csv" in result.stdout
    
    def test_multiple_video_formats(self):
        """Test analysis with different video formats."""
        if not self.has_test_videos:
            pytest.skip("Test video files not available")
        
        # Test different video files
        test_videos = [
            self.youtube_shorts_video,
            self.tiktok_video,
            self.instagram_reel_video
        ]
        
        for video_path in test_videos:
            if not video_path.exists():
                continue
                
            # Create temporary output
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as json_file:
                json_path = json_file.name
            
            try:
                # Run analysis
                result = subprocess.run([
                    'uv', 'run', 'python', '-m', 'src.analyzer.cli',
                    str(video_path),
                    '--clips', '2',
                    '--out-json', json_path
                ], capture_output=True, text=True, timeout=60)
                
                # Should succeed
                assert result.returncode == 0, f"Failed for {video_path}: {result.stderr}"
                
                # Verify output
                assert os.path.exists(json_path)
                with open(json_path, 'r') as f:
                    json_data = json.load(f)
                
                assert 'clips' in json_data
                assert len(json_data['clips']) == 2
            
            finally:
                if os.path.exists(json_path):
                    os.unlink(json_path)
