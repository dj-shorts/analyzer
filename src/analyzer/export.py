"""
Result export module for MVP Analyzer.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from .config import Config
from .schema import JSONSchemaValidator

logger = logging.getLogger(__name__)


class ResultExporter:
    """Exports analysis results to CSV and JSON formats."""

    def __init__(self, config: Config):
        """Initialize result exporter with configuration."""
        self.config = config

    def export(
        self,
        segments_data: dict[str, Any],
        audio_data: dict[str, Any],
        metrics_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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
        json_path = self._export_json(segments, audio_data, metrics_data)

        # Validate exported files
        self._validate_exports(json_path, csv_path)

        logger.info(f"Results exported to {csv_path} and {json_path}")

        return {
            "csv_path": csv_path,
            "json_path": json_path,
            "segments_count": len(segments),
            "export_timestamp": datetime.now().isoformat(),
        }

    def _export_csv(self, segments: list[dict[str, Any]]) -> Path:
        """
        Export segments to CSV format.

        Args:
            segments: List of segment dictionaries

        Returns:
            Path to exported CSV file
        """
        csv_path = self.config.output_csv

        # Ensure parent directory exists
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "clip_id",
                "start",
                "end",
                "center",
                "score",
                "seed_based",
                "aligned",
                "length",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header
            writer.writeheader()

            # Write segments
            for segment in segments:
                writer.writerow(
                    {
                        "clip_id": segment["clip_id"],
                        "start": f"{segment['start']:.3f}",
                        "end": f"{segment['end']:.3f}",
                        "center": f"{segment['center']:.3f}",
                        "score": f"{segment['score']:.3f}",
                        "seed_based": segment["seed_based"],
                        "aligned": segment["aligned"],
                        "length": f"{segment['length']:.3f}",
                    }
                )

        logger.info(f"CSV exported to {csv_path}")
        return csv_path

    def _export_json(
        self,
        segments: list[dict[str, Any]],
        audio_data: dict[str, Any],
        metrics_data: dict[str, Any] | None = None,
    ) -> Path:
        """
        Export segments to JSON format with metadata.

        Args:
            segments: List of segment dictionaries
            audio_data: Dict containing audio metadata

        Returns:
            Path to exported JSON file
        """
        json_path = self.config.output_json

        # Ensure parent directory exists
        json_path.parent.mkdir(parents=True, exist_ok=True)

        # Prepare JSON data structure
        json_data = {
            "metadata": {
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "input_file": str(self.config.input_path),
                "audio_duration": audio_data.get("duration", 0),
                "sample_rate": audio_data.get("sample_rate", 0),
                "configuration": {
                    "clips_count": self.config.clips_count,
                    "min_clip_length": self.config.min_clip_length,
                    "max_clip_length": self.config.max_clip_length,
                    "pre_roll": self.config.pre_roll,
                    "peak_spacing": self.config.peak_spacing,
                    "with_motion": self.config.with_motion,
                    "align_to_beat": self.config.align_to_beat,
                    "seed_timestamps": self.config.seed_timestamps,
                },
            },
            "clips": segments,
            "summary": {
                "total_clips": len(segments),
                "seed_based_clips": sum(1 for s in segments if s["seed_based"]),
                "auto_detected_clips": sum(1 for s in segments if not s["seed_based"]),
                "average_score": np.mean([s["score"] for s in segments])
                if segments
                else 0,
                "total_duration": sum(s["length"] for s in segments),
                "coverage_percentage": (
                    sum(s["length"] for s in segments)
                    / audio_data.get("duration", 1)
                    * 100
                    if audio_data.get("duration", 0) > 0
                    else 0
                ),
            },
        }

        # Add metrics if provided
        if metrics_data:
            json_data["metrics"] = metrics_data

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

        # Write JSON file
        with open(json_path, "w", encoding="utf-8") as jsonfile:
            json.dump(json_data, jsonfile, indent=2, ensure_ascii=False)

        logger.info(f"JSON exported to {json_path}")
        return json_path

    def _validate_exports(self, json_path: Path, csv_path: Path) -> None:
        """
        Validate exported files against schema.

        Args:
            json_path: Path to JSON file
            csv_path: Path to CSV file
        """
        try:
            validator = JSONSchemaValidator()
            if validator.validate_cli_output(json_path, csv_path):
                logger.debug("Export validation successful")
            else:
                logger.warning("Export validation failed")
        except Exception as e:
            logger.warning(f"Export validation error: {e}")
