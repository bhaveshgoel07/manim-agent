"""
Manim MCP Tools

This package contains all the tools for the Manim MCP server.
Tools are organized into logical modules:
- planning: Concept planning and ideation
- code_generation: Manim code generation and refinement
- rendering: Manim animation rendering
- vision: Frame analysis and visual feedback
- audio: Text-to-speech and narration
- video: Video processing and merging
"""

from .audio import generate_narration, generate_speech
from .code_generation import generate_manim_code, refine_animation
from .planning import plan_concept
from .quiz import generate_quiz
from .rendering import render_manim_animation, write_manim_file
from .video import check_file_exists, merge_video_audio, process_video_with_ffmpeg
from .vision import analyze_frame

__all__ = [
    # Planning
    "plan_concept",
    # Code Generation
    "generate_manim_code",
    "refine_animation",
    # Rendering
    "write_manim_file",
    "render_manim_animation",
    # Vision
    "analyze_frame",
    # Audio
    "generate_narration",
    "generate_speech",
    # Video
    "process_video_with_ffmpeg",
    "merge_video_audio",
    "check_file_exists",
    # Quiz
    "generate_quiz",
]
