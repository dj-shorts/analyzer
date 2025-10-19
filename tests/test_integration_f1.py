"""
Integration tests for the complete analysis pipeline (Epic F1).

Tests end-to-end functionality with synthetic data.
"""

import pytest
import numpy as np
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch
from analyzer.core import Analyzer
from analyzer.config import Config


class TestAnalysisPipelineIntegrationEpicF1:
    """Integration tests for the complete analysis pipeline."""

    def test_complete_pipeline_basic(self):
        """Test complete pipeline with basic synthetic data."""
        # Create temporary video file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            config = Config(
                input_path=temp_path,
                clips_count=3,
                min_clip_length=5.0,
                max_clip_length=15.0,
                pre_roll=2.0,
                peak_spacing=80
            )
            
            analyzer = Analyzer(config)
            
            # Mock the audio extractor to return synthetic data
            with patch('analyzer.audio.AudioExtractor.extract') as mock_extract:
                mock_extract.return_value = self._create_synthetic_audio_data()
                
                # Mock other components to avoid actual processing
                with patch('analyzer.novelty.NoveltyDetector.compute_novelty') as mock_novelty, \
                     patch('analyzer.peaks.PeakPicker.find_peaks') as mock_peaks, \
                     patch('analyzer.segments.SegmentBuilder.build_segments') as mock_segments, \
                     patch('analyzer.export.ResultExporter.export') as mock_export:
                    
                    # Setup mocks
                    mock_novelty.return_value = self._create_synthetic_novelty_scores()
                    mock_peaks.return_value = self._create_synthetic_peaks()
                    mock_segments.return_value = self._create_synthetic_segments()
                    mock_export.return_value = self._create_synthetic_results()
                    
                    # Run analysis
                    result = analyzer.analyze()
                    
                    # Verify result structure
                    assert isinstance(result, dict)
                    assert "segments" in result
                    assert "audio_data" in result
                    
        finally:
            # Cleanup
            if temp_path.exists():
                temp_path.unlink()

    def test_complete_pipeline_with_beat_tracking(self):
        """Test complete pipeline with beat tracking enabled."""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            config = Config(
                input_path=temp_path,
                clips_count=5,
                align_to_beat=True,
                min_clip_length=5.0,
                max_clip_length=15.0
            )
            
            analyzer = Analyzer(config)
            
            # Mock components
            with patch('analyzer.audio.AudioExtractor.extract') as mock_extract, \
                 patch('analyzer.beats.BeatTracker.track_beats') as mock_beats, \
                 patch('analyzer.novelty.NoveltyDetector.compute_novelty') as mock_novelty, \
                 patch('analyzer.peaks.PeakPicker.find_peaks') as mock_peaks, \
                 patch('analyzer.segments.SegmentBuilder.build_segments') as mock_segments, \
                 patch('analyzer.export.ResultExporter.export') as mock_export:
                
                # Setup mocks
                mock_extract.return_value = self._create_synthetic_audio_data()
                mock_beats.return_value = self._create_synthetic_beat_data()
                mock_novelty.return_value = self._create_synthetic_novelty_scores()
                mock_peaks.return_value = self._create_synthetic_peaks()
                mock_segments.return_value = self._create_synthetic_segments()
                mock_export.return_value = self._create_synthetic_results()
                
                # Run analysis
                result = analyzer.analyze()
                
                # Verify beat tracking was called
                mock_beats.assert_called_once()
                
                # Verify result includes beat data
                assert "beat_data" in result
                
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_complete_pipeline_with_motion_analysis(self):
        """Test complete pipeline with motion analysis enabled."""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            config = Config(
                input_path=temp_path,
                clips_count=3,
                with_motion=True,
                min_clip_length=5.0,
                max_clip_length=15.0
            )
            
            analyzer = Analyzer(config)
            
            # Mock components
            with patch('analyzer.audio.AudioExtractor.extract') as mock_extract, \
                 patch('analyzer.novelty.NoveltyDetector.compute_novelty') as mock_novelty, \
                 patch('analyzer.peaks.PeakPicker.find_peaks') as mock_peaks, \
                 patch('analyzer.segments.SegmentBuilder.build_segments') as mock_segments, \
                 patch('analyzer.export.ResultExporter.export') as mock_export:
                
                # Setup mocks
                mock_extract.return_value = self._create_synthetic_audio_data()
                mock_novelty.return_value = self._create_synthetic_novelty_scores()
                mock_peaks.return_value = self._create_synthetic_peaks()
                mock_segments.return_value = self._create_synthetic_segments()
                mock_export.return_value = self._create_synthetic_results()
                
                # Run analysis
                result = analyzer.analyze()
                
                # Verify analysis completed successfully
                assert "segments" in result
                
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_complete_pipeline_with_video_export(self):
        """Test complete pipeline with video export enabled."""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            config = Config(
                input_path=temp_path,
                clips_count=3,
                export_video=True,
                export_dir=Path("test_clips"),
                min_clip_length=5.0,
                max_clip_length=15.0
            )
            
            analyzer = Analyzer(config)
            
            # Mock components
            with patch('analyzer.audio.AudioExtractor.extract') as mock_extract, \
                 patch('analyzer.novelty.NoveltyDetector.compute_novelty') as mock_novelty, \
                 patch('analyzer.peaks.PeakPicker.find_peaks') as mock_peaks, \
                 patch('analyzer.segments.SegmentBuilder.build_segments') as mock_segments, \
                 patch('analyzer.export.ResultExporter.export') as mock_export:
                
                # Setup mocks
                mock_extract.return_value = self._create_synthetic_audio_data()
                mock_novelty.return_value = self._create_synthetic_novelty_scores()
                mock_peaks.return_value = self._create_synthetic_peaks()
                mock_segments.return_value = self._create_synthetic_segments()
                mock_export.return_value = self._create_synthetic_results()
                
                # Run analysis
                result = analyzer.analyze()
                
                # Verify result includes video export data
                assert "video_export" in result
                
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_pipeline_error_handling(self):
        """Test pipeline error handling."""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            config = Config(input_path=temp_path, clips_count=3)
            analyzer = Analyzer(config)
            
            # Mock audio extractor to raise exception
            with patch('analyzer.audio.AudioExtractor.extract') as mock_extract:
                mock_extract.side_effect = Exception("Audio extraction failed")
                
                # Should raise exception
                with pytest.raises(Exception, match="Audio extraction failed"):
                    analyzer.analyze()
                    
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_pipeline_with_seed_timestamps(self):
        """Test pipeline with seed timestamps."""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            config = Config(
                input_path=temp_path,
                clips_count=5,
                seed_timestamps=[10.0, 30.0, 60.0],
                min_clip_length=5.0,
                max_clip_length=15.0
            )
            
            analyzer = Analyzer(config)
            
            # Mock components
            with patch('analyzer.audio.AudioExtractor.extract') as mock_extract, \
                 patch('analyzer.novelty.NoveltyDetector.compute_novelty') as mock_novelty, \
                 patch('analyzer.peaks.PeakPicker.find_peaks') as mock_peaks, \
                 patch('analyzer.segments.SegmentBuilder.build_segments') as mock_segments, \
                 patch('analyzer.export.ResultExporter.export') as mock_export:
                
                # Setup mocks
                mock_extract.return_value = self._create_synthetic_audio_data()
                mock_novelty.return_value = self._create_synthetic_novelty_scores()
                mock_peaks.return_value = self._create_synthetic_peaks()
                mock_segments.return_value = self._create_synthetic_segments()
                mock_export.return_value = self._create_synthetic_results()
                
                # Run analysis
                result = analyzer.analyze()
                
                # Verify seed timestamps were used
                assert "segments" in result
                
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def _create_synthetic_audio_data(self):
        """Create synthetic audio data for testing."""
        return {
            "audio": np.random.randn(22050 * 60),  # 1 minute
            "sample_rate": 22050,
            "duration": 60.0,
            "analysis_time": 5.0
        }

    def _create_synthetic_novelty_scores(self):
        """Create synthetic novelty scores for testing."""
        times = np.linspace(0, 60, 1000)
        scores = np.random.rand(1000)
        
        # Add some clear peaks
        scores[100] = 0.9
        scores[300] = 0.8
        scores[500] = 0.7
        scores[700] = 0.6
        scores[900] = 0.5
        
        return {
            "time_axis": times,
            "novelty_scores": scores
        }

    def _create_synthetic_peaks(self):
        """Create synthetic peaks for testing."""
        return {
            "peak_times": [10.0, 30.0, 50.0],
            "peak_scores": [0.9, 0.8, 0.7]
        }

    def _create_synthetic_peaks_with_seeds(self):
        """Create synthetic peaks including seed-based peaks."""
        return {
            "peak_times": [10.0, 25.0, 30.0, 45.0, 60.0],
            "peak_scores": [0.9, 0.6, 0.8, 0.5, 0.7],
            "seed_based": [True, False, True, False, True]
        }

    def _create_synthetic_segments(self):
        """Create synthetic segments for testing."""
        return {
            "segments": [
                {
                    "clip_id": 1,
                    "start": 8.0,
                    "end": 18.0,
                    "center": 13.0,
                    "score": 0.9,
                    "seed_based": False,
                    "aligned": False,
                    "length": 10.0
                },
                {
                    "clip_id": 2,
                    "start": 28.0,
                    "end": 38.0,
                    "center": 33.0,
                    "score": 0.8,
                    "seed_based": False,
                    "aligned": False,
                    "length": 10.0
                },
                {
                    "clip_id": 3,
                    "start": 48.0,
                    "end": 58.0,
                    "center": 53.0,
                    "score": 0.7,
                    "seed_based": False,
                    "aligned": False,
                    "length": 10.0
                }
            ]
        }

    def _create_synthetic_segments_with_seeds(self):
        """Create synthetic segments including seed-based segments."""
        return {
            "segments": [
                {
                    "clip_id": 1,
                    "start": 8.0,
                    "end": 18.0,
                    "center": 13.0,
                    "score": 0.9,
                    "seed_based": True,
                    "aligned": False,
                    "length": 10.0
                },
                {
                    "clip_id": 2,
                    "start": 23.0,
                    "end": 33.0,
                    "center": 28.0,
                    "score": 0.6,
                    "seed_based": False,
                    "aligned": False,
                    "length": 10.0
                },
                {
                    "clip_id": 3,
                    "start": 28.0,
                    "end": 38.0,
                    "center": 33.0,
                    "score": 0.8,
                    "seed_based": True,
                    "aligned": False,
                    "length": 10.0
                },
                {
                    "clip_id": 4,
                    "start": 43.0,
                    "end": 53.0,
                    "center": 48.0,
                    "score": 0.5,
                    "seed_based": False,
                    "aligned": False,
                    "length": 10.0
                },
                {
                    "clip_id": 5,
                    "start": 58.0,
                    "end": 68.0,
                    "center": 63.0,
                    "score": 0.7,
                    "seed_based": True,
                    "aligned": False,
                    "length": 10.0
                }
            ]
        }

    def _create_synthetic_beat_data(self):
        """Create synthetic beat data for testing."""
        return {
            "tempo": 120.0,
            "beats": np.array([0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]),
            "confidence": 0.8
        }

    def _create_synthetic_motion_data(self):
        """Create synthetic motion data for testing."""
        return {
            "motion_available": True,
            "motion_scores": np.random.rand(1000),
            "time_axis": np.linspace(0, 60, 1000)
        }

    def _create_synthetic_video_export_results(self):
        """Create synthetic video export results for testing."""
        return {
            "export": {
                "total_clips": 3,
                "exported_clips": 3,
                "failed_clips": 0,
                "exported_clips_list": [
                    {"clip_id": 1, "path": "test_clips/clip_1.mp4"},
                    {"clip_id": 2, "path": "test_clips/clip_2.mp4"},
                    {"clip_id": 3, "path": "test_clips/clip_3.mp4"}
                ]
            }
        }

    def _create_synthetic_results(self):
        """Create synthetic analysis results for testing."""
        return {
            "segments": [
                {
                    "clip_id": 1,
                    "start": 8.0,
                    "end": 18.0,
                    "center": 13.0,
                    "score": 0.9,
                    "seed_based": False,
                    "aligned": False,
                    "length": 10.0
                },
                {
                    "clip_id": 2,
                    "start": 28.0,
                    "end": 38.0,
                    "center": 33.0,
                    "score": 0.8,
                    "seed_based": False,
                    "aligned": False,
                    "length": 10.0
                },
                {
                    "clip_id": 3,
                    "start": 48.0,
                    "end": 58.0,
                    "center": 53.0,
                    "score": 0.7,
                    "seed_based": False,
                    "aligned": False,
                    "length": 10.0
                }
            ],
            "audio_data": {
                "duration": 60.0,
                "analysis_time": 5.0
            }
        }


class TestAnalysisPipelineEdgeCasesEpicF1:
    """Tests for edge cases in the analysis pipeline."""

    def test_pipeline_with_empty_audio(self):
        """Test pipeline with empty audio data."""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            config = Config(input_path=temp_path, clips_count=3)
            analyzer = Analyzer(config)
            
            # Mock audio extractor to return empty data
            with patch('analyzer.audio.AudioExtractor.extract') as mock_extract:
                mock_extract.return_value = {
                    "audio": np.array([]),
                    "sample_rate": 22050,
                    "duration": 0.0
                }
                
                # Should handle empty audio gracefully
                with pytest.raises(Exception):
                    analyzer.analyze()
                    
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_pipeline_with_invalid_config(self):
        """Test pipeline with invalid configuration."""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Invalid config: min_clip_length > max_clip_length
            with pytest.raises(ValueError):
                config = Config(
                    input_path=temp_path,
                    clips_count=3,
                    min_clip_length=20.0,
                    max_clip_length=10.0
                )
                    
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_pipeline_with_negative_seed_timestamps(self):
        """Test pipeline with negative seed timestamps."""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Should raise validation error for negative seeds
            with pytest.raises(ValueError):
                config = Config(
                    input_path=temp_path,
                    clips_count=3,
                    seed_timestamps=[-10.0, 30.0]
                )
                    
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestAnalysisPipelinePerformanceEpicF1:
    """Performance tests for the analysis pipeline."""

    def test_pipeline_performance_benchmark(self):
        """Benchmark complete pipeline performance."""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            config = Config(
                input_path=temp_path,
                clips_count=10,
                min_clip_length=5.0,
                max_clip_length=15.0
            )
            
            analyzer = Analyzer(config)
            
            # Mock all components
            with patch('analyzer.audio.AudioExtractor.extract') as mock_extract, \
                 patch('analyzer.novelty.NoveltyDetector.compute_novelty') as mock_novelty, \
                 patch('analyzer.peaks.PeakPicker.find_peaks') as mock_peaks, \
                 patch('analyzer.segments.SegmentBuilder.build_segments') as mock_segments, \
                 patch('analyzer.export.ResultExporter.export') as mock_export:
                
                # Setup mocks
                mock_extract.return_value = {
                    "audio": np.random.randn(22050 * 300),  # 5 minutes
                    "sample_rate": 22050,
                    "duration": 300.0
                }
                mock_novelty.return_value = {
                    "times": np.linspace(0, 300, 5000),
                    "scores": np.random.rand(5000)
                }
                mock_peaks.return_value = {"peaks": []}
                mock_segments.return_value = {"segments": []}
                mock_export.return_value = {"segments": [], "audio_data": {"duration": 300.0}}
                
                import time
                start_time = time.time()
                result = analyzer.analyze()
                end_time = time.time()
                
                processing_time = end_time - start_time
                
                # Should complete in reasonable time (< 10 seconds)
                assert processing_time < 10.0
                assert isinstance(result, dict)
                
        finally:
            if temp_path.exists():
                temp_path.unlink()

