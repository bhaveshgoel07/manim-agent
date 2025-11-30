"""
LangGraph Agent Nodes for NeuroAnim Pipeline

This module contains all the node functions used in the LangGraph workflow.
Each node represents a step in the animation generation pipeline and
communicates with the Manim MCP server to perform its task.
"""

import ast
import json
import logging
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

from mcp import ClientSession

from neuroanim.graph.state import AnimationState
from utils.tts import TTSGenerator

logger = logging.getLogger(__name__)


class AnimationNodes:
    """Container for all animation pipeline nodes."""

    def __init__(
        self,
        mcp_session: ClientSession,
        tts_generator: TTSGenerator,
        work_dir: Path,
        output_dir: Path,
    ):
        """
        Initialize the animation nodes.

        Args:
            mcp_session: MCP client session for tool calls
            tts_generator: TTS generator instance
            work_dir: Working directory for temporary files
            output_dir: Output directory for final files
        """
        self.mcp_session = mcp_session
        self.tts_generator = tts_generator
        self.work_dir = work_dir
        self.output_dir = output_dir

    async def call_mcp_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call an MCP tool and return the result.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Dictionary with 'text' and 'isError' keys
        """
        try:
            result = await self.mcp_session.call_tool(tool_name, arguments)

            if hasattr(result, "content") and result.content:
                content = result.content[0]
                if hasattr(content, "text"):
                    return {
                        "text": content.text,
                        "isError": getattr(result, "isError", False),
                    }

            return {"text": str(result), "isError": False}

        except Exception as e:
            logger.error(f"MCP tool call failed for {tool_name}: {e}")
            return {"text": f"Tool call failed: {str(e)}", "isError": True}

    async def initialize_node(self, state: AnimationState) -> AnimationState:
        """
        Initialize the pipeline state and working directories.

        Args:
            state: Current animation state

        Returns:
            Updated state with initialized paths and metadata
        """
        logger.info("🚀 Initializing animation pipeline")

        state["start_time"] = time.time()
        state["work_dir"] = str(self.work_dir)
        state["output_dir"] = str(self.output_dir)
        state["current_step"] = "initialization"
        state["completed_steps"].append("initialization")

        logger.info(f"Working directory: {self.work_dir}")
        logger.info(f"Output directory: {self.output_dir}")

        return state

    async def plan_concept_node(self, state: AnimationState) -> AnimationState:
        """
        Plan the animation concept using AI.

        Args:
            state: Current animation state

        Returns:
            Updated state with concept plan
        """
        logger.info("📋 Planning concept...")
        state["current_step"] = "concept_planning"

        try:
            result = await self.call_mcp_tool(
                "plan_concept",
                {
                    "topic": state["topic"],
                    "target_audience": state["target_audience"],
                    "animation_length_minutes": state["animation_length_minutes"],
                },
            )

            if result["isError"]:
                state["errors"].append(f"Concept planning failed: {result['text']}")
                return state

            concept_plan = result["text"]
            state["concept_plan"] = concept_plan

            # Try to parse JSON from the concept plan
            try:
                # Extract JSON if it's embedded in the response
                json_match = re.search(r"\{.*\}", concept_plan, re.DOTALL)
                if json_match:
                    plan_data = json.loads(json_match.group())
                    state["learning_objectives"] = plan_data.get(
                        "learning_objectives", []
                    )
                    state["visual_metaphors"] = plan_data.get("visual_metaphors", [])
                    state["scene_flow"] = plan_data.get("scene_flow", [])
            except json.JSONDecodeError:
                logger.warning("Could not parse concept plan as JSON")

            state["completed_steps"].append("concept_planning")
            logger.info("✅ Concept planning completed")

        except Exception as e:
            logger.error(f"Concept planning failed: {e}")
            state["errors"].append(f"Concept planning error: {str(e)}")

        return state

    async def generate_narration_node(self, state: AnimationState) -> AnimationState:
        """
        Generate narration script for the animation.

        Args:
            state: Current animation state

        Returns:
            Updated state with narration text
        """
        logger.info("🎙️  Generating narration...")
        state["current_step"] = "narration_generation"

        try:
            duration_seconds = int(state["animation_length_minutes"] * 60)

            result = await self.call_mcp_tool(
                "generate_narration",
                {
                    "concept": state["topic"],
                    "scene_description": state.get("concept_plan", ""),
                    "target_audience": state["target_audience"],
                    "duration_seconds": duration_seconds,
                },
            )

            if result["isError"]:
                state["errors"].append(f"Narration generation failed: {result['text']}")
                return state

            # Extract narration text from response
            narration_text = result["text"]
            if "Narration Script:" in narration_text:
                narration_text = narration_text.split("Narration Script:")[-1].strip()

            state["narration_text"] = narration_text
            state["narration_duration"] = duration_seconds
            state["completed_steps"].append("narration_generation")

            logger.info("✅ Narration generation completed")

        except Exception as e:
            logger.error(f"Narration generation failed: {e}")
            state["errors"].append(f"Narration generation error: {str(e)}")

        return state

    async def generate_code_node(self, state: AnimationState) -> AnimationState:
        """
        Generate Manim code for the animation.

        Args:
            state: Current animation state

        Returns:
            Updated state with generated code
        """
        logger.info("💻 Generating Manim code...")
        state["current_step"] = "code_generation"

        try:
            # Check if this is a retry
            previous_code = None
            error_message = None
            if state["code_generation_attempts"] > 0:
                previous_code = state.get("manim_code")
                if state.get("previous_code_errors"):
                    error_message = state["previous_code_errors"][-1]

            state["code_generation_attempts"] += 1

            arguments = {
                "concept": state["topic"],
                "scene_description": state.get("concept_plan", ""),
                "visual_elements": ["text", "shapes", "animations"],
            }

            if previous_code and error_message:
                arguments["previous_code"] = previous_code
                arguments["error_message"] = error_message
                logger.info(
                    f"Retrying code generation (attempt {state['code_generation_attempts']})"
                )

            result = await self.call_mcp_tool("generate_manim_code", arguments)

            if result["isError"]:
                state["errors"].append(f"Code generation failed: {result['text']}")
                return state

            # Extract Python code from response
            code_text = result["text"]
            manim_code = self._extract_python_code(code_text)

            # Validate syntax
            validation_error = self._validate_python_syntax(manim_code)
            if validation_error:
                logger.warning(f"Code validation failed: {validation_error}")
                if not state.get("previous_code_errors"):
                    state["previous_code_errors"] = []
                state["previous_code_errors"].append(validation_error)
                state["warnings"].append(f"Code validation issue: {validation_error}")
            else:
                logger.info("✅ Code validation passed")

            state["manim_code"] = manim_code
            state["scene_name"] = self._extract_scene_name(manim_code)
            state["completed_steps"].append("code_generation")

            logger.info(f"✅ Code generation completed (scene: {state['scene_name']})")

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            state["errors"].append(f"Code generation error: {str(e)}")

        return state

    async def write_file_node(self, state: AnimationState) -> AnimationState:
        """
        Write the Manim code to a file.

        Args:
            state: Current animation state

        Returns:
            Updated state with file path
        """
        logger.info("📝 Writing Manim file...")
        state["current_step"] = "file_writing"

        try:
            manim_file = Path(state["work_dir"]) / "animation.py"
            state["manim_file_path"] = str(manim_file)

            result = await self.call_mcp_tool(
                "write_manim_file",
                {"filepath": str(manim_file), "code": state["manim_code"]},
            )

            if result["isError"]:
                state["errors"].append(f"File writing failed: {result['text']}")
                return state

            state["completed_steps"].append("file_writing")
            logger.info(f"✅ Manim file written to {manim_file}")

        except Exception as e:
            logger.error(f"File writing failed: {e}")
            state["errors"].append(f"File writing error: {str(e)}")

        return state

    async def render_animation_node(self, state: AnimationState) -> AnimationState:
        """
        Render the Manim animation.

        Args:
            state: Current animation state

        Returns:
            Updated state with rendered video path
        """
        logger.info("🎬 Rendering animation...")
        state["current_step"] = "rendering"

        try:
            result = await self.call_mcp_tool(
                "render_manim_animation",
                {
                    "scene_name": state["scene_name"],
                    "file_path": state["manim_file_path"],
                    "output_dir": state["work_dir"],
                    "quality": state["rendering_quality"],
                    "format": state["rendering_format"],
                    "frame_rate": state["frame_rate"],
                },
            )

            if result["isError"]:
                state["errors"].append(f"Rendering failed: {result['text']}")
                return state

            # Find the rendered video file
            video_file = (
                Path(state["work_dir"])
                / f"{state['scene_name']}.{state['rendering_format']}"
            )
            if not video_file.exists():
                state["errors"].append(f"Rendered video not found at {video_file}")
                return state

            state["video_file_path"] = str(video_file)
            state["completed_steps"].append("rendering")

            logger.info(f"✅ Animation rendered: {video_file}")

        except Exception as e:
            logger.error(f"Rendering failed: {e}")
            state["errors"].append(f"Rendering error: {str(e)}")

        return state

    async def generate_audio_node(self, state: AnimationState) -> AnimationState:
        """
        Generate speech audio from narration text.

        Args:
            state: Current animation state

        Returns:
            Updated state with audio file path
        """
        logger.info("🔊 Generating speech audio...")
        state["current_step"] = "audio_generation"

        try:
            audio_file = Path(state["work_dir"]) / "narration.mp3"
            state["audio_file_path"] = str(audio_file)

            # Use TTS generator with automatic fallback
            tts_result = await self.tts_generator.generate_speech(
                text=state["narration_text"], output_path=audio_file, voice="rachel"
            )

            logger.info(f"Audio generated with {tts_result['provider']}")

            # Validate audio file
            validation = self.tts_generator.validate_audio_file(audio_file)
            if not validation["valid"]:
                state["warnings"].append(
                    f"Audio validation warning: {validation.get('error', 'Unknown issue')}"
                )
            else:
                logger.info(
                    f"Audio validated: {validation.get('duration', 'N/A')}s, {validation.get('size', 0)} bytes"
                )

            state["completed_steps"].append("audio_generation")
            logger.info(f"✅ Audio generated: {audio_file}")

        except Exception as e:
            logger.error(f"Audio generation failed: {e}")
            state["errors"].append(f"Audio generation error: {str(e)}")

        return state

    async def merge_video_audio_node(self, state: AnimationState) -> AnimationState:
        """
        Merge video and audio into final output.

        Args:
            state: Current animation state

        Returns:
            Updated state with final output path
        """
        logger.info("🎞️  Merging video and audio...")
        state["current_step"] = "video_audio_merge"

        try:
            final_output = Path(state["output_dir"]) / state["output_filename"]
            state["final_output_path"] = str(final_output)

            result = await self.call_mcp_tool(
                "merge_video_audio",
                {
                    "video_file": state["video_file_path"],
                    "audio_file": state["audio_file_path"],
                    "output_file": str(final_output),
                },
            )

            if result["isError"]:
                state["errors"].append(f"Video/audio merge failed: {result['text']}")
                return state

            state["completed_steps"].append("video_audio_merge")
            logger.info(f"✅ Video and audio merged: {final_output}")

        except Exception as e:
            logger.error(f"Video/audio merge failed: {e}")
            state["errors"].append(f"Merge error: {str(e)}")

        return state

    async def generate_quiz_node(self, state: AnimationState) -> AnimationState:
        """
        Generate quiz questions for the topic.

        Args:
            state: Current animation state

        Returns:
            Updated state with quiz content
        """
        logger.info("❓ Generating quiz...")
        state["current_step"] = "quiz_generation"

        try:
            result = await self.call_mcp_tool(
                "generate_quiz",
                {
                    "concept": state["topic"],
                    "difficulty": "medium",
                    "num_questions": 3,
                    "question_types": ["multiple_choice"],
                },
            )

            if result["isError"]:
                state["warnings"].append(f"Quiz generation failed: {result['text']}")
                state["quiz_content"] = "Quiz generation failed"
            else:
                state["quiz_content"] = result["text"]
                # Try to parse quiz questions
                try:
                    json_match = re.search(r"\[.*\]", result["text"], re.DOTALL)
                    if json_match:
                        state["quiz_questions"] = json.loads(json_match.group())
                except json.JSONDecodeError:
                    logger.warning("Could not parse quiz as JSON")

            state["completed_steps"].append("quiz_generation")
            logger.info("✅ Quiz generation completed")

        except Exception as e:
            logger.error(f"Quiz generation failed: {e}")
            state["warnings"].append(f"Quiz generation error: {str(e)}")
            state["quiz_content"] = "Quiz generation failed"

        return state

    async def finalize_node(self, state: AnimationState) -> AnimationState:
        """
        Finalize the pipeline and compute metadata.

        Args:
            state: Current animation state

        Returns:
            Final state with metadata
        """
        logger.info("🏁 Finalizing pipeline...")
        state["current_step"] = "finalization"

        state["end_time"] = time.time()
        state["total_duration"] = state["end_time"] - state["start_time"]

        # Check if pipeline succeeded
        if not state["errors"] and state.get("final_output_path"):
            state["success"] = True
            logger.info(
                f"✅ Pipeline completed successfully in {state['total_duration']:.2f}s"
            )
        else:
            state["success"] = False
            logger.error(f"❌ Pipeline failed with {len(state['errors'])} error(s)")

        state["completed_steps"].append("finalization")

        return state

    # Helper methods

    def _extract_python_code(self, response_text: str) -> str:
        """Extract Python code from markdown response."""
        if "```python" in response_text:
            start = response_text.find("```python") + 9
            end = response_text.find("```", start)
            if end == -1:
                end = len(response_text)
            return response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            if end == -1:
                end = len(response_text)
            return response_text[start:end].strip()
        else:
            return response_text.strip()

    def _extract_scene_name(self, code: str) -> str:
        """Extract the scene class name from Manim code."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it inherits from Scene or MovingCameraScene
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id in [
                            "Scene",
                            "MovingCameraScene",
                            "ThreeDScene",
                        ]:
                            return node.name
        except SyntaxError:
            pass

        # Fallback: use regex
        match = re.search(r"class\s+(\w+)\s*\(.*Scene.*\):", code)
        if match:
            return match.group(1)

        return "GenScene"

    def _validate_python_syntax(self, code: str) -> str | None:
        """
        Validate Python code syntax.

        Returns:
            Error message if validation fails, None if valid
        """
        try:
            ast.parse(code)
            return None
        except SyntaxError as e:
            return f"Syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return f"Validation error: {str(e)}"
