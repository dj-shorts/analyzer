"""
Generated integration tests for DJ Shorts Analyzer

This file contains comprehensive integration tests that test the entire
analyzer pipeline from input to output.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from analyzer.core import Analyzer
from analyzer.config import Config


class TestAnalyzerIntegrationGenerated:
    """Generated integration tests for the analyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.testsprite(tags=["integration", "end-to-end"], priority="high")
    def test_full_analysis_pipeline(self):
        """Test the complete analysis pipeline."""
        # Test with mock video file
        config = Config(input_path=Path("data/test_video.mp4"))
        analyzer = Analyzer(config)
        
        # Mock the video processing to avoid actual file dependencies
        with patch('analyzer.video.VideoProcessor') as mock_video:
            mock_video.return_value.extract_frames.return_value = []
            
            result = analyzer.analyze()
            
            assert result is not None
    
    @pytest.mark.testsprite(tags=["integration", "config"], priority="normal")
    def test_config_validation_integration(self):
        """Test configuration validation in integration context."""
        # Test valid configuration
        valid_config = Config(input_path=Path("data/test_video.mp4"))
        assert valid_config.input_path == Path("data/test_video.mp4")
        
        # Test invalid configuration
        with pytest.raises(ValueError):
            Config(input_path=Path("nonexistent.mp4"), min_clip_length=30, max_clip_length=15)
    
    @pytest.mark.testsprite(tags=["integration", "error-handling"], priority="high")
    def test_error_handling_integration(self):
        """Test error handling in integration context."""
        # Test with non-existent file
        config = Config(input_path=Path("nonexistent.mp4"))
        analyzer = Analyzer(config)
        
        with pytest.raises(FileNotFoundError):
            analyzer.analyze()
    
    @pytest.mark.testsprite(tags=["integration", "performance"], priority="normal")
    def test_performance_integration(self):
        """Test performance in integration context."""
        # Test with mock large file
        config = Config(input_path=Path("data/test_video.mp4"))
        analyzer = Analyzer(config)
        
        # Mock performance-critical components
        with patch('analyzer.audio.AudioExtractor') as mock_audio:
            mock_audio.return_value.extract.return_value = np.random.random(1000)
            
            import time
            start_time = time.time()
            
            with patch('analyzer.video.VideoProcessor') as mock_video:
                mock_video.return_value.extract_frames.return_value = []
                result = analyzer.analyze()
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Assert reasonable execution time (adjust threshold as needed)
            assert execution_time < 5.0  # 5 seconds max
    
    @pytest.mark.testsprite(tags=["integration", "output"], priority="high")
    def test_output_generation_integration(self):
        """Test output generation in integration context."""
        config = Config(input_path=Path("data/test_video.mp4"))
        analyzer = Analyzer(config)
        
        # Mock successful analysis
        with patch('analyzer.video.VideoProcessor') as mock_video:
            mock_video.return_value.extract_frames.return_value = []
            
            with patch('analyzer.audio.AudioExtractor') as mock_audio:
                mock_audio.return_value.extract.return_value = np.random.random(1000)
                
                result = analyzer.analyze()
                
                # Test that result contains expected fields
                assert "clips" in result
                assert "metadata" in result
                assert "config" in result
