"""
Manim MCP - Model Context Protocol Server for Manim Animations

A unified MCP server providing comprehensive tools for STEM animation creation:
- Planning and ideation
- AI-powered code generation
- Manim rendering
- Vision-based analysis
- Audio narration and TTS
- Video processing

This package can be used standalone as an MCP server or integrated into
larger animation pipelines.
"""

from .server import main, server

__version__ = "0.1.0"
__all__ = ["server", "main"]
