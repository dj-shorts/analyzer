"""
MVP Analyzer - AI-powered music video highlight extraction tool.

This package provides tools for analyzing audio and video content to extract
highlights and create short clips for social media platforms.
"""

__version__ = "0.1.0"
__author__ = "TerryBerk"
__email__ = "radygin.konstantin.s@gmail.com"

from .core import Analyzer
from .audio import AudioExtractor
from .novelty import NoveltyDetector
from .peaks import PeakPicker
from .segments import SegmentBuilder
from .export import ResultExporter

__all__ = [
    "Analyzer",
    "AudioExtractor", 
    "NoveltyDetector",
    "PeakPicker",
    "SegmentBuilder",
    "ResultExporter",
]