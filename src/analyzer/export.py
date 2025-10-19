"""
Result export module for MVP Analyzer.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import numpy as np

from .config import Config
from .schema import validate_output

logger = logging.getLogger(__name__)


class ResultExporter:
    """Exports analysis results to CSV and JSON formats."""
    
    def __init__(self, config: Config):
        """Initialize result exporter with configuration."""
        self.config = config
    
    def export(self, segments_data: Dict[str, Any], audio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export results to CSV and JSON files.
        
        Args:
            segments_data: Dict containing segment information
            audio_data: Dict containing audio metadata
            
        Returns:
            Dict containing export results and file paths
        """
        logger.info("Exporting results to CSV and JSON")
        
        segments = segments_data["segments"]
        
        # Export to CSV
        csv_path = self._export_csv(segments)
        
        # Export to JSON
        json_path = self._export_json(segments, audio_data)
        
        logger.info(f"Results exported to {csv_path} and {json_path}")
        
        return {
            "csv_path": csv_path,
            "json_path": json_path,
            "segments_count": len(segments),
            "export_timestamp": datetime.now().isoformat()
        }
    
    def _export_csv(self, segments: List[Dict[str, Any]]) -> Path:
        """
        Export segments to CSV format.
        
        Args:
            segments: List of segment dictionaries
            
        Returns:
            Path to exported CSV file
        """
        csv_path = self.config.output_csv
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'clip_id', 'start', 'end', 'center', 'score', 
                'seed_based', 'aligned', 'length'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header
            writer.writeheader()
            
            # Write segments
            for segment in segments:
                writer.writerow({
                    'clip_id': segment['clip_id'],
                    'start': f"{segment['start']:.3f}",
                    'end': f"{segment['end']:.3f}",
                    'center': f"{segment['center']:.3f}",
                    'score': f"{segment['score']:.3f}",
                    'seed_based': segment['seed_based'],
                    'aligned': segment['aligned'],
                    'length': f"{segment['length']:.3f}"
                })
        
        logger.info(f"CSV exported to {csv_path}")
        return csv_path
    
    def _export_json(self, segments: List[Dict[str, Any]], audio_data: Dict[str, Any]) -> Path:
        """
        Export segments to JSON format with metadata.
        
        Args:
            segments: List of segment dictionaries
            audio_data: Dict containing audio metadata
            
        Returns:
            Path to exported JSON file
        """
        json_path = self.config.output_json
        
        # Prepare JSON data structure according to schema
        json_data = {
            "version": "1.0.0",
            "clips": segments,
            "metadata": {
                "input_file": str(self.config.input_path),
                "total_duration": audio_data.get("duration", 0),
                "clips_count": len(segments),
                "analysis_time": audio_data.get("analysis_time", 0),
                "with_motion": self.config.with_motion,
                "align_to_beat": self.config.align_to_beat,
                "export_video": self.config.export_video,
                "export_format": self.config.export_format,
                "auto_reframe": self.config.auto_reframe,
                "tempo_confidence": audio_data.get("tempo_confidence", 0.0),
                "novelty_peaks_count": audio_data.get("novelty_peaks_count", 0)
            }
        }
        
        # Convert numpy types to native Python types for JSON serialization
        def convert_numpy_types(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        # Recursively convert numpy types
        def recursive_convert(data):
            if isinstance(data, dict):
                return {k: recursive_convert(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [recursive_convert(item) for item in data]
            else:
                return convert_numpy_types(data)
        
        json_data = recursive_convert(json_data)
        
        # Validate against schema
        validation_errors = validate_output(json_data)
        if validation_errors:
            logger.warning(f"JSON validation errors: {validation_errors}")
            # Continue anyway, but log the errors
        
        # Write JSON file
        with open(json_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON exported to {json_path}")
        return json_path
