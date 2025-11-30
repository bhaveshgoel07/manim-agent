"""
LangGraph Workflow Definition for NeuroAnim Pipeline

This module defines the complete animation generation workflow using LangGraph.
The workflow coordinates multiple agent nodes to transform a STEM topic into
an educational animation with narration.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from neuroanim.agents.nodes import AnimationNodes
from neuroanim.graph.state import AnimationState, create_initial_state

logger = logging.getLogger(__name__)


def should_retry_code_generation(state: AnimationState) -> str:
    """
    Determine if code generation should be retried.

    Args:
        state: Current animation state

    Returns:
        Next node name: "generate_code" for retry, "write_file" to proceed
    """
    if (
        state.get("previous_code_errors")
        and state["code_generation_attempts"] < state["max_retries"]
    ):
        logger.info(
            f"Code has errors, retrying (attempt {state['code_generation_attempts']}/{state['max_retries']})"
        )
        return "generate_code"
    return "write_file"


def should_continue_after_error(state: AnimationState) -> str:
    """
    Determine if pipeline should continue after errors.

    Args:
        state: Current animation state

    Returns:
        Next node name or END
    """
    if state["errors"]:
        logger.error(f"Pipeline encountered {len(state['errors'])} error(s), stopping")
        return "finalize"
    return "next"


def create_animation_workflow(nodes: AnimationNodes) -> StateGraph:
    """
    Create the LangGraph workflow for animation generation.

    The workflow follows this sequence:
    1. Initialize - Set up directories and state
    2. Plan Concept - Generate animation concept plan
    3. Generate Narration - Create narration script
    4. Generate Code - Create Manim code (with retry logic)
    5. Write File - Save code to file
    6. Render Animation - Execute Manim rendering
    7. Generate Audio - Create speech audio
    8. Merge Video/Audio - Combine into final output
    9. Generate Quiz - Create assessment questions
    10. Finalize - Compute metadata and complete

    Args:
        nodes: AnimationNodes instance with all node functions

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph
    workflow = StateGraph(AnimationState)

    # Add all nodes
    workflow.add_node("initialize", nodes.initialize_node)
    workflow.add_node("plan_concept", nodes.plan_concept_node)
    workflow.add_node("generate_narration", nodes.generate_narration_node)
    workflow.add_node("generate_code", nodes.generate_code_node)
    workflow.add_node("write_file", nodes.write_file_node)
    workflow.add_node("render_animation", nodes.render_animation_node)
    workflow.add_node("generate_audio", nodes.generate_audio_node)
    workflow.add_node("merge_video_audio", nodes.merge_video_audio_node)
    workflow.add_node("generate_quiz", nodes.generate_quiz_node)
    workflow.add_node("finalize", nodes.finalize_node)

    # Set entry point
    workflow.set_entry_point("initialize")

    # Define the workflow edges (sequential flow with error checking)

    # Initialize -> Plan Concept
    workflow.add_edge("initialize", "plan_concept")

    # Plan Concept -> Check for errors -> Generate Narration
    workflow.add_conditional_edges(
        "plan_concept",
        lambda state: "generate_narration" if not state["errors"] else "finalize",
    )

    # Generate Narration -> Check for errors -> Generate Code
    workflow.add_conditional_edges(
        "generate_narration",
        lambda state: "generate_code" if not state["errors"] else "finalize",
    )

    # Generate Code -> Check syntax -> Retry or Write File
    workflow.add_conditional_edges(
        "generate_code",
        should_retry_code_generation,
    )

    # Write File -> Check for errors -> Render
    workflow.add_conditional_edges(
        "write_file",
        lambda state: "render_animation" if not state["errors"] else "finalize",
    )

    # Render -> Check for errors -> Generate Audio
    workflow.add_conditional_edges(
        "render_animation",
        lambda state: "generate_audio" if not state["errors"] else "finalize",
    )

    # Generate Audio -> Check for errors -> Merge
    workflow.add_conditional_edges(
        "generate_audio",
        lambda state: "merge_video_audio" if not state["errors"] else "finalize",
    )

    # Merge -> Check for errors -> Generate Quiz
    workflow.add_conditional_edges(
        "merge_video_audio",
        lambda state: "generate_quiz" if not state["errors"] else "finalize",
    )

    # Generate Quiz -> Finalize (quiz errors are non-critical)
    workflow.add_edge("generate_quiz", "finalize")

    # Finalize -> END
    workflow.add_edge("finalize", END)

    # Compile the graph
    return workflow.compile()


async def run_animation_pipeline(
    mcp_session: Any,
    tts_generator: Any,
    topic: str,
    target_audience: str = "general",
    animation_length_minutes: float = 2.0,
    output_filename: str = "animation.mp4",
    rendering_quality: str = "medium",
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Run the complete animation generation pipeline.

    This is the main entry point for generating animations. It creates
    the workflow, initializes the state, and executes all steps.

    Args:
        mcp_session: MCP client session
        tts_generator: TTS generator instance
        topic: STEM topic to animate
        target_audience: Target audience level
        animation_length_minutes: Desired animation length
        output_filename: Name for output file
        rendering_quality: Manim rendering quality
        max_retries: Maximum retry attempts

    Returns:
        Dictionary with pipeline results including:
        - success: Whether pipeline completed successfully
        - final_output_path: Path to final video
        - errors: List of errors encountered
        - warnings: List of warnings
        - completed_steps: List of completed steps
        - metadata: Timing and other metadata
    """
    # Create working directories
    work_dir = Path(tempfile.mkdtemp(prefix="neuroanim_work_"))
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    logger.info(f"📁 Working directory: {work_dir}")
    logger.info(f"📁 Output directory: {output_dir}")

    # Initialize nodes
    nodes = AnimationNodes(
        mcp_session=mcp_session,
        tts_generator=tts_generator,
        work_dir=work_dir,
        output_dir=output_dir,
    )

    # Create workflow
    workflow = create_animation_workflow(nodes)

    # Create initial state
    initial_state = create_initial_state(
        topic=topic,
        target_audience=target_audience,
        animation_length_minutes=animation_length_minutes,
        output_filename=output_filename,
        rendering_quality=rendering_quality,
        max_retries=max_retries,
    )

    logger.info(f"🎬 Starting animation pipeline for topic: '{topic}'")

    try:
        # Run the workflow
        final_state = await workflow.ainvoke(initial_state)

        # Build result summary
        result = {
            "success": final_state.get("success", False),
            "topic": final_state["topic"],
            "target_audience": final_state["target_audience"],
            "final_output_path": final_state.get("final_output_path"),
            "concept_plan": final_state.get("concept_plan"),
            "narration": final_state.get("narration_text"),
            "manim_code": final_state.get("manim_code"),
            "quiz": final_state.get("quiz_content"),
            "errors": final_state.get("errors", []),
            "warnings": final_state.get("warnings", []),
            "completed_steps": final_state.get("completed_steps", []),
            "total_duration": final_state.get("total_duration"),
            "work_dir": str(work_dir),
            "output_dir": str(output_dir),
        }

        if result["success"]:
            logger.info(f"✅ Animation pipeline completed successfully!")
            logger.info(f"📹 Output file: {result['final_output_path']}")
            logger.info(f"⏱️  Total time: {result['total_duration']:.2f}s")
        else:
            logger.error(f"❌ Animation pipeline failed")
            logger.error(f"Errors: {result['errors']}")

        return result

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "work_dir": str(work_dir),
            "output_dir": str(output_dir),
        }

    finally:
        # Note: We don't clean up work_dir here so users can inspect artifacts
        logger.info(f"Work directory preserved at: {work_dir}")
