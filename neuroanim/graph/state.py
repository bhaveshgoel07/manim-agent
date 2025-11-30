"""
LangGraph State Definition for NeuroAnim Pipeline

This module defines the state structure that flows through the animation
generation workflow. The state is updated by each node in the graph.
"""

from typing import Any, Dict, List, Optional, TypedDict


class AnimationState(TypedDict, total=False):
    """
    State for the animation generation pipeline.

    This state is passed through all nodes in the LangGraph workflow.
    Each node reads from and writes to this state to coordinate the
    animation generation process.
    """

    # Input Parameters
    topic: str
    target_audience: str
    animation_length_minutes: float
    output_filename: str

    # Concept Planning
    concept_plan: Optional[str]
    learning_objectives: Optional[List[str]]
    visual_metaphors: Optional[List[str]]
    scene_flow: Optional[List[Dict[str, str]]]

    # Narration
    narration_text: Optional[str]
    narration_duration: Optional[float]

    # Code Generation
    manim_code: Optional[str]
    scene_name: Optional[str]
    code_generation_attempts: int
    previous_code_errors: Optional[List[str]]

    # File Paths
    work_dir: Optional[str]
    output_dir: Optional[str]
    manim_file_path: Optional[str]
    video_file_path: Optional[str]
    audio_file_path: Optional[str]
    final_output_path: Optional[str]

    # Rendering
    rendering_quality: str
    rendering_format: str
    frame_rate: int

    # Analysis & Feedback
    frame_analysis: Optional[str]
    visual_quality_score: Optional[float]
    needs_refinement: bool
    refinement_feedback: Optional[str]

    # Quiz
    quiz_content: Optional[str]
    quiz_questions: Optional[List[Dict[str, Any]]]

    # Error Handling
    errors: List[str]
    warnings: List[str]
    current_step: str
    retry_count: Dict[str, int]
    max_retries: int

    # Status
    success: bool
    completed_steps: List[str]

    # Metadata
    start_time: Optional[float]
    end_time: Optional[float]
    total_duration: Optional[float]


def create_initial_state(
    topic: str,
    target_audience: str = "general",
    animation_length_minutes: float = 2.0,
    output_filename: str = "animation.mp4",
    rendering_quality: str = "medium",
    rendering_format: str = "mp4",
    frame_rate: int = 30,
    max_retries: int = 3,
) -> AnimationState:
    """
    Create the initial state for the animation pipeline.

    Args:
        topic: The STEM topic to animate
        target_audience: Target audience level
        animation_length_minutes: Desired animation length
        output_filename: Name for the final output file
        rendering_quality: Manim rendering quality
        rendering_format: Output video format
        frame_rate: Video frame rate
        max_retries: Maximum retry attempts per step

    Returns:
        Initial AnimationState with default values
    """
    return AnimationState(
        # Input parameters
        topic=topic,
        target_audience=target_audience,
        animation_length_minutes=animation_length_minutes,
        output_filename=output_filename,
        # Initialize optional fields
        concept_plan=None,
        learning_objectives=None,
        visual_metaphors=None,
        scene_flow=None,
        narration_text=None,
        narration_duration=None,
        manim_code=None,
        scene_name=None,
        code_generation_attempts=0,
        previous_code_errors=None,
        # File paths
        work_dir=None,
        output_dir=None,
        manim_file_path=None,
        video_file_path=None,
        audio_file_path=None,
        final_output_path=None,
        # Rendering config
        rendering_quality=rendering_quality,
        rendering_format=rendering_format,
        frame_rate=frame_rate,
        # Analysis
        frame_analysis=None,
        visual_quality_score=None,
        needs_refinement=False,
        refinement_feedback=None,
        # Quiz
        quiz_content=None,
        quiz_questions=None,
        # Error handling
        errors=[],
        warnings=[],
        current_step="initialization",
        retry_count={},
        max_retries=max_retries,
        # Status
        success=False,
        completed_steps=[],
        # Metadata
        start_time=None,
        end_time=None,
        total_duration=None,
    )
