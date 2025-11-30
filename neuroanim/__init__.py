"""
NeuroAnim - LangGraph-based Animation Pipeline

This package provides a modular, graph-based workflow for generating
educational STEM animations using Manim, AI models, and TTS.

The pipeline uses LangGraph to coordinate multiple agent nodes that handle:
- Concept planning
- Code generation
- Rendering
- Audio generation
- Video processing
"""

from neuroanim.graph.state import AnimationState, create_initial_state
from neuroanim.graph.workflow import run_animation_pipeline

__version__ = "0.1.0"
__all__ = ["run_animation_pipeline", "create_initial_state", "AnimationState"]
