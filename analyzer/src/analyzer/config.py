"""
Configuration models for MVP Analyzer.
"""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class Config(BaseModel):
    """Main configuration for the analyzer."""
    
    # Input/Output paths
    input_path: Path = Field(..., description="Path to input video file")
    output_json: Path = Field(default=Path("highlights.json"), description="Output JSON file path")
    output_csv: Path = Field(default=Path("highlights.csv"), description="Output CSV file path")
    
    # Analysis parameters
    clips_count: int = Field(default=6, ge=1, le=50, description="Number of clips to extract")
    min_clip_length: float = Field(default=15.0, gt=0, description="Minimum clip length in seconds")
    max_clip_length: float = Field(default=30.0, gt=0, description="Maximum clip length in seconds")
    pre_roll: float = Field(default=10.0, ge=0, description="Pre-roll time in seconds")
    
    # Peak detection parameters
    peak_spacing: int = Field(default=80, gt=0, description="Minimum spacing between peaks in frames")
    
    # Feature flags
    with_motion: bool = Field(default=False, description="Include motion analysis")
    align_to_beat: bool = Field(default=False, description="Align clips to beat boundaries")
    
    # Video export parameters
    export_video: bool = Field(default=False, description="Export video clips")
    export_dir: Path = Field(default=Path("clips"), description="Directory for exported video clips")
    
    # Seed timestamps (in seconds)
    seed_timestamps: List[float] = Field(default_factory=list, description="Seed timestamps for peak detection")
    
    # Performance settings
    threads: Optional[int] = Field(default=None, ge=1, description="Number of threads to use")
    ram_limit: Optional[str] = Field(default=None, description="RAM limit (e.g., '2GB')")
    
    @field_validator("max_clip_length")
    @classmethod
    def max_length_must_be_greater_than_min(cls, v, info):
        """Validate that max_clip_length > min_clip_length."""
        if info.data.get("min_clip_length") and v <= info.data["min_clip_length"]:
            raise ValueError("max_clip_length must be greater than min_clip_length")
        return v
    
    @field_validator("seed_timestamps")
    @classmethod
    def seeds_must_be_positive(cls, v):
        """Validate that all seed timestamps are positive."""
        for seed in v:
            if seed < 0:
                raise ValueError("Seed timestamps must be positive")
        return v
    
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True
    )
