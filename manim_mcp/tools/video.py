"""
Video Processing Tools for Manim MCP Server

This module provides tools for video processing, merging, and file management using FFmpeg.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict

from mcp.types import CallToolResult, TextContent

logger = logging.getLogger(__name__)


async def process_video_with_ffmpeg(arguments: Dict[str, Any]) -> CallToolResult:
    """
    Process video files using FFmpeg.

    Provides flexible video processing capabilities including conversion,
    filtering, and combining multiple inputs.

    Args:
        arguments: Dictionary containing:
            - input_files (list): List of input video/audio file paths
            - output_file (str): Output file path
            - ffmpeg_args (list, optional): Additional FFmpeg command-line arguments

    Returns:
        CallToolResult indicating success or failure
    """
    input_files = arguments["input_files"]
    output_file = arguments["output_file"]
    ffmpeg_args = arguments.get("ffmpeg_args", [])

    try:
        # Ensure output directory exists
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        # Build FFmpeg command
        cmd = ["ffmpeg"]

        # Add input files
        for input_file in input_files:
            cmd.extend(["-i", input_file])

        # Add additional arguments
        cmd.extend(ffmpeg_args)

        # Add output file
        cmd.append(output_file)

        logger.info(f"Running FFmpeg command: {' '.join(cmd)}")

        # Execute FFmpeg
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = f"FFmpeg processing failed:\n{stderr.decode()}"
            logger.error(error_msg)
            return CallToolResult(
                content=[TextContent(type="text", text=error_msg)],
                isError=True,
            )

        result_msg = f"Successfully processed video with FFmpeg: {output_file}"
        logger.info(result_msg)

        return CallToolResult(content=[TextContent(type="text", text=result_msg)])

    except Exception as e:
        error_msg = f"Error during FFmpeg processing: {str(e)}"
        logger.error(error_msg)
        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)],
            isError=True,
        )


async def merge_video_audio(arguments: Dict[str, Any]) -> CallToolResult:
    """
    Merge video and audio files into a single output file.

    Combines a video file with an audio file using FFmpeg. The video stream
    is copied without re-encoding, while the audio is encoded to AAC.
    The output duration matches the shorter of the two inputs.

    Args:
        arguments: Dictionary containing:
            - video_file (str): Path to the input video file
            - audio_file (str): Path to the input audio file
            - output_file (str): Path to the output merged file

    Returns:
        CallToolResult indicating success or failure
    """
    video_file = arguments["video_file"]
    audio_file = arguments["audio_file"]
    output_file = arguments["output_file"]

    try:
        # Ensure output directory exists
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        # Build FFmpeg merge command
        cmd = [
            "ffmpeg",
            "-i",
            video_file,
            "-i",
            audio_file,
            "-c:v",
            "copy",  # Copy video stream without re-encoding
            "-c:a",
            "aac",  # Encode audio to AAC
            "-shortest",  # Match duration of shortest input
            "-y",  # Overwrite output file if it exists
            output_file,
        ]

        logger.info(f"Merging video and audio: {' '.join(cmd)}")

        # Execute FFmpeg
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = f"Video/audio merge failed:\n{stderr.decode()}"
            logger.error(error_msg)
            return CallToolResult(
                content=[TextContent(type="text", text=error_msg)],
                isError=True,
            )

        result_msg = f"Successfully merged video and audio: {output_file}"
        logger.info(result_msg)

        return CallToolResult(content=[TextContent(type="text", text=result_msg)])

    except Exception as e:
        error_msg = f"Error during video/audio merge: {str(e)}"
        logger.error(error_msg)
        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)],
            isError=True,
        )


async def check_file_exists(arguments: Dict[str, Any]) -> CallToolResult:
    """
    Check if a file exists and return its metadata.

    Provides information about file existence, type, size, and timestamps.
    Useful for verifying outputs before processing or debugging file issues.

    Args:
        arguments: Dictionary containing:
            - filepath (str): Path to the file to check

    Returns:
        CallToolResult with file metadata or error if file doesn't exist
    """
    filepath = arguments["filepath"]

    try:
        path = Path(filepath)

        if not path.exists():
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"File does not exist: {filepath}",
                    )
                ],
                isError=True,
            )

        stat = path.stat()

        metadata = {
            "filepath": str(path.absolute()),
            "exists": True,
            "is_file": path.is_file(),
            "is_directory": path.is_dir(),
            "size_bytes": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
        }

        logger.info(f"File exists: {filepath} ({stat.st_size} bytes)")

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"File metadata:\n{json.dumps(metadata, indent=2)}",
                )
            ]
        )

    except Exception as e:
        error_msg = f"Error checking file: {str(e)}"
        logger.error(error_msg)
        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)],
            isError=True,
        )
