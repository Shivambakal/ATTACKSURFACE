"""Application services package.

Provides domain logic for intelligence collection, diffing, classification,
scoring, provider coordination, AI safety, and pipeline orchestration.
"""
from .pipeline import TargetPipeline

__all__ = ["TargetPipeline"]
