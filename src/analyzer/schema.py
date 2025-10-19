"""
JSON schema definitions for MVP Analyzer output validation.
"""

from typing import Dict, Any, List
import json


def get_output_schema() -> Dict[str, Any]:
    """Get the JSON schema for analyzer output validation."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "title": "MVP Analyzer Output Schema",
        "description": "Schema for validating MVP Analyzer output JSON",
        "required": ["version", "clips", "metadata"],
        "properties": {
            "version": {
                "type": "string",
                "description": "Schema version",
                "pattern": r"^\d+\.\d+\.\d+$"
            },
            "clips": {
                "type": "array",
                "description": "Array of extracted clips",
                "items": {
                    "type": "object",
                    "required": ["clip_id", "start", "end", "center", "score", "length", "seed_based", "aligned"],
                    "properties": {
                        "clip_id": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Unique identifier for the clip"
                        },
                        "start": {
                            "type": "number",
                            "minimum": 0,
                            "description": "Start time in seconds"
                        },
                        "end": {
                            "type": "number",
                            "minimum": 0,
                            "description": "End time in seconds"
                        },
                        "center": {
                            "type": "number",
                            "minimum": 0,
                            "description": "Center time in seconds"
                        },
                        "score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Novelty score (0-1)"
                        },
                        "length": {
                            "type": "number",
                            "minimum": 0,
                            "description": "Clip length in seconds"
                        },
                        "seed_based": {
                            "type": "boolean",
                            "description": "Whether clip is based on seed timestamp"
                        },
                        "aligned": {
                            "type": "boolean",
                            "description": "Whether clip is aligned to beat boundaries"
                        }
                    }
                }
            },
            "metadata": {
                "type": "object",
                "description": "Analysis metadata",
                "required": ["input_file", "total_duration", "clips_count", "analysis_time"],
                "properties": {
                    "input_file": {
                        "type": "string",
                        "description": "Input video file path"
                    },
                    "total_duration": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Total video duration in seconds"
                    },
                    "clips_count": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Number of clips extracted"
                    },
                    "analysis_time": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Analysis time in seconds"
                    },
                    "with_motion": {
                        "type": "boolean",
                        "description": "Whether motion analysis was enabled"
                    },
                    "align_to_beat": {
                        "type": "boolean",
                        "description": "Whether beat alignment was enabled"
                    },
                    "export_video": {
                        "type": "boolean",
                        "description": "Whether video export was enabled"
                    },
                    "export_format": {
                        "type": "string",
                        "enum": ["original", "vertical", "square"],
                        "description": "Video export format"
                    },
                    "auto_reframe": {
                        "type": "boolean",
                        "description": "Whether auto-reframe was enabled"
                    },
                    "tempo_confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Beat tracking confidence (0-1)"
                    },
                    "novelty_peaks_count": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Number of novelty peaks detected"
                    }
                }
            },
            "video_export": {
                "type": "object",
                "description": "Video export results (if enabled)",
                "properties": {
                    "total_clips": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Total number of clips to export"
                    },
                    "exported_clips": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Number of successfully exported clips"
                    },
                    "failed_clips": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Number of failed clip exports"
                    },
                    "export_directory": {
                        "type": "string",
                        "description": "Directory where clips were exported"
                    },
                    "export_format": {
                        "type": "string",
                        "enum": ["original", "vertical", "square"],
                        "description": "Export format used"
                    },
                    "auto_reframe_used": {
                        "type": "boolean",
                        "description": "Whether auto-reframe was used"
                    }
                }
            }
        }
    }


def validate_output(output_data: Dict[str, Any]) -> List[str]:
    """
    Validate output data against the schema.
    
    Args:
        output_data: The output data to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    # For now, we'll do basic validation
    # In a full implementation, you'd use a JSON schema validator like jsonschema
    errors = []
    
    # Check required top-level fields
    required_fields = ["version", "clips", "metadata"]
    for field in required_fields:
        if field not in output_data:
            errors.append(f"Missing required field: {field}")
    
    # Check version format
    if "version" in output_data:
        version = output_data["version"]
        if not isinstance(version, str) or not version.count('.') == 2:
            errors.append("Version must be in format 'X.Y.Z'")
    
    # Check clips array
    if "clips" in output_data:
        clips = output_data["clips"]
        if not isinstance(clips, list):
            errors.append("Clips must be an array")
        else:
            required_clip_fields = ["clip_id", "start", "end", "center", "score", "length", "seed_based", "aligned"]
            for i, clip in enumerate(clips):
                if not isinstance(clip, dict):
                    errors.append(f"Clip {i} must be an object")
                    continue
                
                for field in required_clip_fields:
                    if field not in clip:
                        errors.append(f"Clip {i} missing required field: {field}")
                
                # Check score range
                if "score" in clip and not (0 <= clip["score"] <= 1):
                    errors.append(f"Clip {i} score must be between 0 and 1")
    
    # Check metadata
    if "metadata" in output_data:
        metadata = output_data["metadata"]
        if not isinstance(metadata, dict):
            errors.append("Metadata must be an object")
        else:
            required_metadata_fields = ["input_file", "total_duration", "clips_count", "analysis_time"]
            for field in required_metadata_fields:
                if field not in metadata:
                    errors.append(f"Metadata missing required field: {field}")
    
    return errors


def save_schema(schema_path: str) -> None:
    """Save the schema to a JSON file."""
    schema = get_output_schema()
    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2)
