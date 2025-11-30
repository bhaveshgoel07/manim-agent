"""
Manim MCP Server

A unified MCP server providing tools for STEM animation creation with Manim.
Combines creative AI tools (planning, code generation, narration) with
rendering and video processing capabilities.

This server is designed to be used standalone or integrated into larger
animation generation pipelines.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

from manim_mcp.tools import (
    analyze_frame,
    check_file_exists,
    generate_manim_code,
    generate_narration,
    generate_quiz,
    generate_speech,
    merge_video_audio,
    plan_concept,
    process_video_with_ffmpeg,
    refine_animation,
    render_manim_animation,
    write_manim_file,
)
from utils.hf_wrapper import HFInferenceWrapper, get_hf_wrapper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create MCP server
server = Server("manim-mcp")

# Global HF wrapper instance
hf_wrapper: Optional[HFInferenceWrapper] = None


def get_hf_wrapper_instance() -> HFInferenceWrapper:
    """Get or create the HuggingFace wrapper instance."""
    global hf_wrapper
    if hf_wrapper is None:
        api_key = os.getenv("HUGGINGFACE_API_KEY")
        hf_wrapper = get_hf_wrapper(api_key=api_key)
        logger.info("Initialized HuggingFace wrapper")
    return hf_wrapper


@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List all available tools in the Manim MCP server."""
    tools = [
        # Planning Tools
        Tool(
            name="plan_concept",
            description="Plan a STEM concept for animation. Creates a structured plan with learning objectives, visual metaphors, scene flow, and educational value assessment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The STEM topic to create an animation for",
                    },
                    "target_audience": {
                        "type": "string",
                        "enum": [
                            "elementary",
                            "middle_school",
                            "high_school",
                            "college",
                            "general",
                        ],
                        "description": "Target audience level",
                    },
                    "animation_length_minutes": {
                        "type": "number",
                        "description": "Desired animation length in minutes (default: 2.0)",
                    },
                    "model": {
                        "type": "string",
                        "description": "Hugging Face model to use (optional)",
                    },
                },
                "required": ["topic", "target_audience"],
            },
        ),
        # Code Generation Tools
        Tool(
            name="generate_manim_code",
            description="Generate Manim Python code for an animation concept. Produces complete, runnable code with proper syntax and Manim best practices.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": "The animation concept",
                    },
                    "scene_description": {
                        "type": "string",
                        "description": "Detailed scene description",
                    },
                    "visual_elements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of visual elements to include",
                    },
                    "model": {
                        "type": "string",
                        "description": "Hugging Face code model to use (optional)",
                    },
                    "previous_code": {
                        "type": "string",
                        "description": "Previous code attempt (for retries)",
                    },
                    "error_message": {
                        "type": "string",
                        "description": "Error from previous attempt (for retries)",
                    },
                },
                "required": ["concept", "scene_description"],
            },
        ),
        Tool(
            name="refine_animation",
            description="Refine and improve existing Manim code based on feedback or errors. Outputs complete corrected code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "original_code": {
                        "type": "string",
                        "description": "The original Manim code to refine",
                    },
                    "feedback": {
                        "type": "string",
                        "description": "Feedback or error message about the code",
                    },
                    "improvement_goals": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of specific improvement goals",
                    },
                    "model": {
                        "type": "string",
                        "description": "Hugging Face code model to use (optional)",
                    },
                },
                "required": ["original_code", "feedback"],
            },
        ),
        # Rendering Tools
        Tool(
            name="write_manim_file",
            description="Write Manim Python code to a file on the filesystem.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path where to write the Manim file",
                    },
                    "code": {
                        "type": "string",
                        "description": "Manim Python code to write",
                    },
                },
                "required": ["filepath", "code"],
            },
        ),
        Tool(
            name="render_manim_animation",
            description="Render a Manim animation from a Python file. Uses local Manim installation with quality and format options.",
            inputSchema={
                "type": "object",
                "properties": {
                    "scene_name": {
                        "type": "string",
                        "description": "Name of the Manim scene class to render",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the Manim Python file",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory to save the output animation",
                    },
                    "quality": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "production_quality"],
                        "description": "Rendering quality (default: medium)",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["mp4", "gif", "png"],
                        "description": "Output format (default: mp4)",
                    },
                    "frame_rate": {
                        "type": "integer",
                        "description": "Frame rate (default: 30)",
                    },
                },
                "required": ["scene_name", "file_path", "output_dir"],
            },
        ),
        # Vision Tools
        Tool(
            name="analyze_frame",
            description="Analyze an animation frame using vision models. Provides feedback on visual quality, clarity, and educational effectiveness.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image file to analyze",
                    },
                    "analysis_type": {
                        "type": "string",
                        "description": "Type of analysis (e.g., quality, educational_value, clarity)",
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context about the animation",
                    },
                    "model": {
                        "type": "string",
                        "description": "Hugging Face vision model to use (optional)",
                    },
                },
                "required": ["image_path", "analysis_type"],
            },
        ),
        # Audio Tools
        Tool(
            name="generate_narration",
            description="Generate an educational narration script for an animation. Creates age-appropriate, engaging content aligned with learning objectives.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": "The animation concept",
                    },
                    "scene_description": {
                        "type": "string",
                        "description": "Description of the scene/animation",
                    },
                    "target_audience": {
                        "type": "string",
                        "description": "Target audience level",
                    },
                    "duration_seconds": {
                        "type": "integer",
                        "description": "Duration in seconds (default: 30)",
                    },
                    "model": {
                        "type": "string",
                        "description": "Hugging Face model to use (optional)",
                    },
                },
                "required": ["concept", "scene_description", "target_audience"],
            },
        ),
        Tool(
            name="generate_speech",
            description="Convert text to speech audio file using TTS models.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to convert to speech",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path where to save the audio file",
                    },
                    "voice": {
                        "type": "string",
                        "description": "Voice to use for TTS (optional)",
                    },
                    "model": {
                        "type": "string",
                        "description": "Hugging Face TTS model to use (optional)",
                    },
                },
                "required": ["text", "output_path"],
            },
        ),
        # Video Processing Tools
        Tool(
            name="process_video_with_ffmpeg",
            description="Process video files using FFmpeg with custom arguments for conversion, filtering, and combining.",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of input video/audio file paths",
                    },
                    "output_file": {
                        "type": "string",
                        "description": "Output file path",
                    },
                    "ffmpeg_args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional FFmpeg command-line arguments",
                    },
                },
                "required": ["input_files", "output_file"],
            },
        ),
        Tool(
            name="merge_video_audio",
            description="Merge a video file and an audio file into a single output file using FFmpeg.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_file": {
                        "type": "string",
                        "description": "Path to the input video file",
                    },
                    "audio_file": {
                        "type": "string",
                        "description": "Path to the input audio file",
                    },
                    "output_file": {
                        "type": "string",
                        "description": "Path to the output merged file",
                    },
                },
                "required": ["video_file", "audio_file", "output_file"],
            },
        ),
        Tool(
            name="check_file_exists",
            description="Check if a file exists and return its metadata (size, timestamps, type).",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to check",
                    }
                },
                "required": ["filepath"],
            },
        ),
        # Quiz Tools
        Tool(
            name="generate_quiz",
            description="Generate educational quiz questions based on a STEM concept. Creates questions with answers and explanations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": "The STEM concept to create quiz questions for",
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard"],
                        "description": "Difficulty level",
                    },
                    "num_questions": {
                        "type": "integer",
                        "description": "Number of questions to generate",
                    },
                    "question_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Types of questions (e.g., multiple_choice, true_false)",
                    },
                    "model": {
                        "type": "string",
                        "description": "Hugging Face model to use (optional)",
                    },
                },
                "required": ["concept", "difficulty", "num_questions"],
            },
        ),
    ]

    return ListToolsResult(tools=tools)


@server.call_tool()
async def call_tool(tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """
    Dispatch tool calls to the appropriate handler functions.

    Routes requests to the correct tool implementation based on tool name.
    Handles errors gracefully and returns appropriate error responses.
    """
    try:
        # Get HF wrapper for AI-powered tools
        wrapper = get_hf_wrapper_instance()

        # Route to appropriate tool handler
        if tool_name == "plan_concept":
            return await plan_concept(wrapper, arguments)
        elif tool_name == "generate_manim_code":
            return await generate_manim_code(wrapper, arguments)
        elif tool_name == "refine_animation":
            return await refine_animation(wrapper, arguments)
        elif tool_name == "write_manim_file":
            return await write_manim_file(arguments)
        elif tool_name == "render_manim_animation":
            return await render_manim_animation(arguments)
        elif tool_name == "analyze_frame":
            return await analyze_frame(wrapper, arguments)
        elif tool_name == "generate_narration":
            return await generate_narration(wrapper, arguments)
        elif tool_name == "generate_speech":
            return await generate_speech(wrapper, arguments)
        elif tool_name == "process_video_with_ffmpeg":
            return await process_video_with_ffmpeg(arguments)
        elif tool_name == "merge_video_audio":
            return await merge_video_audio(arguments)
        elif tool_name == "check_file_exists":
            return await check_file_exists(arguments)
        elif tool_name == "generate_quiz":
            return await generate_quiz(wrapper, arguments)
        else:
            logger.error(f"Unknown tool requested: {tool_name}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {tool_name}")],
                isError=True,
            )

    except Exception as e:
        logger.error(f"Error in tool {tool_name}: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def main():
    """Main entry point for the Manim MCP server."""
    logger.info("Starting Manim MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="manim-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
