"""
MCP Servers for NeuroAnim.

This package contains the MCP servers that provide different capabilities:
- renderer.py: Animation rendering using Manim and FFmpeg
- creative.py: Creative tasks using Hugging Face models
"""

from . import renderer
from . import creative

__all__ = ["renderer", "creative"]