"""
NeuroAnim Orchestrator

This script coordinates the entire STEM animation generation pipeline:
1. Concept Planning
2. Code Generation
3. Rendering
4. Vision-based Analysis
5. Audio Generation
6. Final Merging

It uses the MCP servers (renderer and creative) to accomplish these tasks.
"""

import ast
import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from utils.tts import TTSGenerator

load_dotenv()
# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NeuroAnimOrchestrator:
    """Main orchestrator for NeuroAnim pipeline."""

    def __init__(
        self, hf_api_key: Optional[str] = None, elevenlabs_api_key: Optional[str] = None
    ):
        self.hf_api_key = hf_api_key or os.getenv("HUGGINGFACE_API_KEY")
        self.elevenlabs_api_key = elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")
        self.renderer_session: Optional[ClientSession] = None
        self.creative_session: Optional[ClientSession] = None

        # Initialize TTS generator
        self.tts_generator = TTSGenerator(
            elevenlabs_api_key=self.elevenlabs_api_key,
            hf_api_key=self.hf_api_key,
            fallback_enabled=True,
        )

        # Context managers for MCP client connections
        self._renderer_cm = None
        self._creative_cm = None
        self._renderer_streams = None
        self._creative_streams = None

        # Working directories
        self.work_dir: Optional[Path] = None
        self.output_dir: Optional[Path] = None

    async def initialize(self):
        """Initialize MCP server connections."""
        # Set up working directories
        self.work_dir = Path(tempfile.mkdtemp(prefix="neuroanim_work_"))
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)

        logger.info(f"Working directory: {self.work_dir}")
        logger.info(f"Output directory: {self.output_dir}")

        # Initialize renderer server
        # stdio_client is an async context manager, must use async with
        renderer_params = StdioServerParameters(
            command="python", args=["mcp_servers/renderer.py"]
        )

        self._renderer_cm = stdio_client(renderer_params)
        self._renderer_streams = await self._renderer_cm.__aenter__()
        read_stream, write_stream = self._renderer_streams
        self.renderer_session = ClientSession(read_stream, write_stream)
        # Start background receive loop for the client session
        await self.renderer_session.__aenter__()
        await self.renderer_session.initialize()
        logger.info("Renderer MCP server connected")

        # Initialize creative server
        creative_params = StdioServerParameters(
            command="python",
            args=["mcp_servers/creative.py"],
            env={"HUGGINGFACE_API_KEY": self.hf_api_key} if self.hf_api_key else None,
        )

        self._creative_cm = stdio_client(creative_params)
        self._creative_streams = await self._creative_cm.__aenter__()
        read_stream, write_stream = self._creative_streams
        self.creative_session = ClientSession(read_stream, write_stream)
        # Start background receive loop for the client session
        await self.creative_session.__aenter__()
        await self.creative_session.initialize()
        logger.info("Creative MCP server connected")

    async def cleanup(self):
        """Clean up resources."""
        import shutil

        # Close sessions first
        if self.renderer_session:
            try:
                await self.renderer_session.__aexit__(None, None, None)
            except (Exception, asyncio.CancelledError) as e:
                logger.debug(f"Error closing renderer session: {e}")

        if self.creative_session:
            try:
                await self.creative_session.__aexit__(None, None, None)
            except (Exception, asyncio.CancelledError) as e:
                logger.debug(f"Error closing creative session: {e}")

        # Then close the stdio_client context managers with timeout
        if self._renderer_cm:
            try:
                async with asyncio.timeout(2):  # 2 second timeout
                    await self._renderer_cm.__aexit__(None, None, None)
            except (Exception, asyncio.CancelledError, TimeoutError) as e:
                logger.debug(f"Error closing renderer context manager: {e}")

        if self._creative_cm:
            try:
                async with asyncio.timeout(2):  # 2 second timeout
                    await self._creative_cm.__aexit__(None, None, None)
            except (Exception, asyncio.CancelledError, TimeoutError) as e:
                logger.debug(f"Error closing creative context manager: {e}")

        # Clean up working directory
        if self.work_dir and self.work_dir.exists():
            try:
                shutil.rmtree(self.work_dir)
                logger.info(f"Cleaned up working directory: {self.work_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up working directory: {e}")

    async def call_tool(
        self, session: ClientSession, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool on an MCP server."""
        result = await session.call_tool(tool_name, arguments)

        if hasattr(result, "content") and result.content:
            content = result.content[0]
            if hasattr(content, "text"):
                return {
                    "text": content.text,
                    "isError": getattr(result, "isError", False),
                }

        return {"text": str(result), "isError": False}

    async def generate_animation(
        self,
        topic: str,
        target_audience: str = "general",
        animation_length_minutes: float = 2.0,
        output_filename: str = "animation.mp4",
        quality: str = "medium",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """Complete animation generation pipeline."""

        def report_progress(step: str, progress: float):
            if progress_callback:
                try:
                    progress_callback(step, progress)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

        try:
            logger.info(f"Starting animation generation for: {topic}")
            report_progress("Planning concept", 0.1)

            # Step 1: Concept Planning
            logger.info("Step 1: Planning concept...")
            concept_result = await self.call_tool(
                self.creative_session,
                "plan_concept",
                {
                    "topic": topic,
                    "target_audience": target_audience,
                    "animation_length_minutes": animation_length_minutes,
                },
            )

            if concept_result["isError"]:
                raise Exception(f"Concept planning failed: {concept_result['text']}")

            concept_plan = concept_result["text"]
            logger.info("Concept planning completed")
            report_progress("Generating narration script", 0.25)

            # Step 2: Generate Narration
            logger.info("Step 2: Generating narration...")
            narration_result = await self.call_tool(
                self.creative_session,
                "generate_narration",
                {
                    "concept": topic,
                    "scene_description": concept_plan,
                    "target_audience": target_audience,
                    "duration_seconds": int(animation_length_minutes * 60),
                },
            )

            if narration_result["isError"]:
                raise Exception(
                    f"Narration generation failed: {narration_result['text']}"
                )

            narration_text = narration_result["text"]
            logger.info("Narration generation completed")
            report_progress("Creating Manim animation code", 0.40)

            # Step 3: Generate Manim Code with retry logic
            logger.info("Step 3: Generating Manim code...")
            manim_code = await self._generate_and_validate_code(
                topic=topic, concept_plan=concept_plan, max_retries=3
            )
            logger.info("Manim code generation completed and validated")

            # Step 4: Write Manim File
            logger.info("Step 4: Writing Manim file...")
            manim_file = self.work_dir / "animation.py"
            write_result = await self.call_tool(
                self.renderer_session,
                "write_manim_file",
                {"filepath": str(manim_file), "code": manim_code},
            )

            if write_result["isError"]:
                raise Exception(f"File writing failed: {write_result['text']}")

            # Extract scene name from code
            scene_name = self._extract_scene_name(manim_code)
            logger.info(f"Scene name detected: {scene_name}")
            report_progress("Rendering animation video", 0.55)

            # Step 5: Render Animation
            logger.info("Step 5: Rendering animation...")
            render_result = await self.call_tool(
                self.renderer_session,
                "render_manim_animation",
                {
                    "scene_name": scene_name,
                    "file_path": str(manim_file),
                    "output_dir": str(self.work_dir),
                    "quality": quality,
                    "format": "mp4",
                    "frame_rate": 30,
                },
            )

            if render_result["isError"]:
                raise Exception(f"Rendering failed: {render_result['text']}")

            # Find rendered video file
            video_file = self._find_output_file(self.work_dir, scene_name, "mp4")
            if not video_file:
                raise Exception("Could not find rendered video file")

            logger.info(f"Animation rendered: {video_file}")
            report_progress("Generating audio narration", 0.75)

            # Step 6: Generate Speech Audio
            logger.info("Step 6: Generating speech audio...")
            audio_file = self.work_dir / "narration.mp3"

            # Use TTS generator with automatic fallback
            try:
                tts_result = await self.tts_generator.generate_speech(
                    text=narration_text, output_path=audio_file, voice="rachel"
                )
                logger.info(
                    f"Audio generated with {tts_result['provider']}: {audio_file}"
                )

                # Validate audio file
                validation = self.tts_generator.validate_audio_file(audio_file)
                if not validation["valid"]:
                    logger.warning(
                        f"Audio validation warning: {validation.get('error', 'Unknown issue')}"
                    )
                    logger.info("Audio file may have issues but continuing...")
                else:
                    logger.info(
                        f"Audio validated: {validation.get('duration', 'N/A')}s, {validation.get('size', 0)} bytes"
                    )

            except Exception as e:
                logger.error(f"TTS generation failed: {e}")
                raise Exception(f"Speech generation failed: {str(e)}")

            report_progress("Merging video and audio", 0.90)

            # Step 7: Merge Video and Audio
            logger.info("Step 7: Merging video and audio...")
            final_output = self.output_dir / output_filename
            merge_result = await self.call_tool(
                self.renderer_session,
                "merge_video_audio",
                {
                    "video_file": str(video_file),
                    "audio_file": str(audio_file),
                    "output_file": str(final_output),
                },
            )

            if merge_result["isError"]:
                raise Exception(f"Merging failed: {merge_result['text']}")

            logger.info(f"Final video created: {final_output}")
            report_progress("Creating quiz questions", 0.95)

            # Step 8: Generate Quiz
            logger.info("Step 8: Generating quiz...")
            quiz_result = await self.call_tool(
                self.creative_session,
                "generate_quiz",
                {"topic": topic, "target_audience": target_audience},
            )
            quiz_content = (
                quiz_result["text"] if not quiz_result["isError"] else "Not available"
            )

            report_progress("Finalizing", 1.0)

            return {
                "success": True,
                "output_file": str(final_output),
                "topic": topic,
                "target_audience": target_audience,
                "concept_plan": concept_plan,
                "narration": narration_text,
                "manim_code": manim_code,
                "quiz": quiz_content,
            }

            # Step 8: Generate Quiz
            logger.info("Step 8: Generating quiz...")
            quiz_result = await self.call_tool(
                self.creative_session,
                "generate_quiz",
                {
                    "concept": topic,
                    "difficulty": "medium",
                    "num_questions": 3,
                    "question_types": ["multiple_choice"],
                },
            )

            quiz_content = (
                quiz_result["text"]
                if not quiz_result["isError"]
                else "Quiz generation failed"
            )

            # Return results
            results = {
                "success": True,
                "topic": topic,
                "target_audience": target_audience,
                "concept_plan": concept_plan,
                "narration": narration_text,
                "manim_code": manim_code,
                "output_file": str(final_output),
                "quiz": quiz_content,
                "work_dir": str(self.work_dir),
            }

            logger.info(f"Animation generation completed successfully: {final_output}")
            return results

        except Exception as e:
            logger.error(f"Animation generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "work_dir": str(self.work_dir) if self.work_dir else None,
            }

    def _extract_python_code(self, response_text: str) -> str:
        """Extract Python code from markdown response."""
        # Look for code blocks
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

    async def _generate_and_validate_code(
        self,
        topic: str,
        concept_plan: str,
        max_retries: int = 3,
        previous_error: Optional[str] = None,
        previous_code: Optional[str] = None,
    ) -> str:
        """Generate Manim code with retry logic for syntax errors."""
        for attempt in range(max_retries):
            try:
                logger.info(f"Code generation attempt {attempt + 1}/{max_retries}")

                # Build arguments for code generation
                arguments = {
                    "concept": topic,
                    "scene_description": concept_plan,
                    "visual_elements": ["text", "shapes", "animations"],
                }

                # If this is a retry, include error feedback
                if previous_error and previous_code:
                    arguments["previous_code"] = previous_code
                    arguments["error_message"] = previous_error
                    logger.info(
                        f"Retrying with error feedback: {previous_error[:100]}..."
                    )

                # Generate code
                code_result = await self.call_tool(
                    self.creative_session, "generate_manim_code", arguments
                )

                if code_result["isError"]:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Code generation failed, retrying: {code_result['text']}"
                        )
                        previous_error = code_result["text"]
                        continue
                    else:
                        raise Exception(
                            f"Code generation failed: {code_result['text']}"
                        )

                # Extract Python code from response
                manim_code = self._extract_python_code(code_result["text"])

                # Validate Python syntax
                syntax_errors = self._validate_python_syntax(manim_code)
                if syntax_errors:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Syntax error detected, retrying: {syntax_errors}"
                        )
                        previous_error = f"Syntax Error:\n{syntax_errors}"
                        previous_code = manim_code
                        continue
                    else:
                        raise Exception(
                            f"Generated code has syntax errors after {max_retries} attempts:\n{syntax_errors}"
                        )

                # Success!
                logger.info(f"Valid code generated on attempt {attempt + 1}")
                return manim_code

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    previous_error = str(e)
                    continue
                else:
                    raise

        raise Exception("Failed to generate valid code after all retries")

    def _validate_python_syntax(self, code: str) -> Optional[str]:
        """Validate Python code syntax. Returns error message if invalid, None if valid."""
        try:
            ast.parse(code)
            return None
        except SyntaxError as e:
            error_msg = f"Line {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f"\n  {e.text.rstrip()}"
                if e.offset:
                    error_msg += f"\n  {' ' * (e.offset - 1)}^"
            return error_msg
        except Exception as e:
            return f"Unexpected error during syntax validation: {str(e)}"

    def _extract_scene_name(self, code: str) -> str:
        """Extract scene class name from Manim code."""
        import re

        # Look for class definition that inherits from Scene, MovingCameraScene, etc.
        match = re.search(r"class\s+(\w+)\s*\(\s*\w*Scene\s*\)", code)
        if match:
            return match.group(1)
        return "Scene"  # fallback

    def _find_output_file(
        self, directory: Path, scene_name: str, extension: str
    ) -> Optional[Path]:
        """Find output file with given scene name and extension."""
        for file in directory.glob(f"{scene_name}*.{extension}"):
            return file
        return None


async def main():
    """Main function for running the orchestrator."""
    import argparse

    parser = argparse.ArgumentParser(description="NeuroAnim STEM Animation Generator")
    parser.add_argument("topic", help="STEM topic for the animation")
    parser.add_argument(
        "--audience",
        choices=["elementary", "middle_school", "high_school", "college", "general"],
        default="general",
        help="Target audience",
    )
    parser.add_argument(
        "--duration", type=float, default=2.0, help="Animation duration in minutes"
    )
    parser.add_argument("--output", default="animation.mp4", help="Output filename")
    parser.add_argument(
        "--api-key", help="Hugging Face API key (or set HUGGINGFACE_API_KEY env var)"
    )
    parser.add_argument(
        "--elevenlabs-key",
        help="ElevenLabs API key (or set ELEVENLABS_API_KEY env var)",
    )

    args = parser.parse_args()

    # Initialize and run orchestrator
    orchestrator = NeuroAnimOrchestrator(
        hf_api_key=args.api_key, elevenlabs_api_key=args.elevenlabs_key
    )

    try:
        await orchestrator.initialize()

        results = await orchestrator.generate_animation(
            topic=args.topic,
            target_audience=args.audience,
            animation_length_minutes=args.duration,
            output_filename=args.output,
        )

        if results["success"]:
            print("\n🎉 Animation Generated Successfully!")
            print(f"📹 Output file: {results['output_file']}")
            print(f"🎯 Topic: {results['topic']}")
            print(f"👥 Audience: {results['target_audience']}")
            print(f"\n📝 Concept Plan:")
            print(
                results["concept_plan"][:500] + "..."
                if len(results["concept_plan"]) > 500
                else results["concept_plan"]
            )
            print(f"\n🎭 Narration:")
            print(
                results["narration"][:300] + "..."
                if len(results["narration"]) > 300
                else results["narration"]
            )
            print(f"\n📚 Quiz Questions:")
            print(results["quiz"])
        else:
            print(f"\n❌ Animation Generation Failed: {results['error']}")

    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
    finally:
        await orchestrator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
