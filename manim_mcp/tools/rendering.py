"""
Rendering Tools for Manim MCP Server

This module provides tools for writing and rendering Manim animations.
"""

import asyncio
import glob
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict

from mcp.types import CallToolResult, TextContent

logger = logging.getLogger(__name__)


async def write_manim_file(arguments: Dict[str, Any]) -> CallToolResult:
    """
    Write a Manim Python file to the filesystem.

    Takes Manim code and writes it to a specified file path, creating
    directories as needed.

    Args:
        arguments: Dictionary containing:
            - filepath (str): Path where to write the Manim file
            - code (str): Manim Python code to write

    Returns:
        CallToolResult indicating success or failure
    """
    filepath = arguments["filepath"]
    code = arguments["code"]

    try:
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(filepath, "w") as f:
            f.write(code)

        logger.info(f"Successfully wrote Manim file to: {filepath}")

        return CallToolResult(
            content=[
                TextContent(
                    type="text", text=f"Successfully wrote Manim file to {filepath}"
                )
            ]
        )

    except Exception as e:
        logger.error(f"Failed to write file: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Failed to write file: {str(e)}")],
            isError=True,
        )


async def render_manim_animation(arguments: Dict[str, Any]) -> CallToolResult:
    """
    Render a Manim animation using local Manim installation.

    Executes the Manim CLI to render an animation scene from a Python file.
    Uses the project's .venv if available, otherwise falls back to system Manim.

    Args:
        arguments: Dictionary containing:
            - scene_name (str): Name of the Manim scene class to render
            - file_path (str): Path to the Manim Python file
            - output_dir (str): Directory to save the output animation
            - quality (str, optional): Rendering quality (low, medium, high, production_quality)
            - format (str, optional): Output format (mp4, gif, png)
            - frame_rate (int, optional): Frame rate (default: 30)

    Returns:
        CallToolResult with rendering status and output file location
    """
    scene_name = arguments["scene_name"]
    file_path = arguments["file_path"]
    output_dir = arguments["output_dir"]
    quality = arguments.get("quality", "medium")
    format_type = arguments.get("format", "mp4")
    frame_rate = arguments.get("frame_rate", 30)

    try:
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Map quality to manim flags
        quality_flags = {
            "low": "-ql",
            "medium": "-qm",
            "high": "-qh",
            "production_quality": "-qp",
        }
        quality_flag = quality_flags.get(quality, "-qm")

        # Find the project root and .venv
        project_root = Path(__file__).resolve().parent.parent.parent
        venv_python = project_root / ".venv" / "bin" / "python"
        venv_manim = project_root / ".venv" / "bin" / "manim"

        # Use venv manim if it exists, otherwise fall back to system manim
        if venv_manim.exists():
            manim_cmd = str(venv_manim)
            logger.info(f"Using .venv manim at: {manim_cmd}")
        else:
            manim_cmd = "manim"
            logger.warning(f".venv manim not found at {venv_manim}, using system manim")

        # Build the manim command
        cmd = [
            manim_cmd,
            quality_flag,
            "--fps",
            str(frame_rate),
            "-o",
            f"{scene_name}.{format_type}",
            file_path,
            scene_name,
        ]

        logger.info(f"Running Manim command: {' '.join(cmd)}")

        # Execute the command with .venv in PATH
        env = os.environ.copy()
        if venv_manim.exists():
            venv_bin = project_root / ".venv" / "bin"
            env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
            env["VIRTUAL_ENV"] = str(project_root / ".venv")

        # Execute the command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=output_dir,
            env=env,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = f"Manim rendering failed:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"
            logger.error(error_msg)
            return CallToolResult(
                content=[TextContent(type="text", text=error_msg)], isError=True
            )

        # Log output for debugging
        logger.info(f"Manim stdout: {stdout.decode()}")
        if stderr:
            logger.info(f"Manim stderr: {stderr.decode()}")

        # Find the output file
        # Manim outputs to paths like: media/videos/{filename}/{resolution}/SceneName.mp4
        quality_to_resolution = {
            "low": ["480p15", "854x480", "480p"],
            "medium": ["720p30", "1280x720", "720p"],
            "high": ["1080p60", "1920x1080", "1080p"],
            "production_quality": ["2160p60", "3840x2160", "2160p"],
        }

        resolutions = quality_to_resolution.get(quality, ["720p30"])

        # Build search patterns
        output_patterns = []
        for res in resolutions:
            output_patterns.extend(
                [
                    f"{output_dir}/media/videos/*/{res}/{scene_name}.{format_type}",
                    f"{output_dir}/media/videos/**/{res}/{scene_name}.{format_type}",
                ]
            )

        # Fallback patterns
        output_patterns.extend(
            [
                f"{output_dir}/media/videos/*/*/{scene_name}.{format_type}",
                f"{output_dir}/media/videos/**/{scene_name}.{format_type}",
                f"{output_dir}/**/{scene_name}.{format_type}",
                f"{output_dir}/{scene_name}.{format_type}",
            ]
        )

        # Search for output file
        output_files = []
        for pattern in output_patterns:
            matches = glob.glob(pattern, recursive=True)
            if matches:
                logger.info(f"Found output files: {matches}")
                output_files.extend(matches)
                break

        if not output_files:
            error_msg = f"Could not find rendered output file.\nSearched in: {output_dir}\nStdout: {stdout.decode()}"
            logger.error(error_msg)
            return CallToolResult(
                content=[TextContent(type="text", text=error_msg)], isError=True
            )

        # Move output to expected location
        output_file = output_files[0]
        final_output = Path(output_dir) / f"{scene_name}.{format_type}"

        shutil.move(output_file, final_output)

        # Build success message
        file_size = final_output.stat().st_size if final_output.exists() else 0
        result_msg = (
            f"Successfully rendered animation!\n"
            f"Scene: {scene_name}\n"
            f"Output: {final_output}\n"
            f"Quality: {quality}\n"
            f"Format: {format_type}\n"
            f"Size: {file_size} bytes"
        )

        logger.info(result_msg)

        return CallToolResult(content=[TextContent(type="text", text=result_msg)])

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        error_msg = f"Error during rendering: {str(e)}\nDetails: {error_details}"
        logger.error(error_msg)
        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)], isError=True
        )
