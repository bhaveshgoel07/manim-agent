"""
Renderer MCP Server

This MCP server provides tools for rendering animations using Manim and
processing videos with FFmpeg.
"""

import asyncio
import base64
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from blaxel.core.sandbox import SandboxInstance
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Create MCP server
server = Server("neuroanim-renderer")


class AnimationConfig(BaseModel):
    """Configuration for Manim animations."""

    scene_name: str
    code: str
    output_file: Optional[str] = None
    quality: str = "medium"  # low, medium, high, production_quality
    format: str = "mp4"  # mp4, gif, png
    resolution: Optional[str] = None
    frame_rate: int = 30


class RendererTool:
    """Base class for renderer tools."""

    @staticmethod
    def create_temp_dir() -> Path:
        """Create a temporary directory for rendering."""
        return Path(tempfile.mkdtemp(prefix="neuroanim_"))

    @staticmethod
    def cleanup_temp_dir(temp_dir: Path):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    async def execute_sandbox_process(
        sandbox, process_config: dict, logger, operation_name: str
    ):
        """Execute a sandbox process with retry logic for connection timeouts and process conflicts."""
        import uuid

        # Store original name for retries
        original_name = process_config.get("name", "unnamed-process")

        # Check for existing processes with the same name and clean them up
        try:
            existing_processes = await sandbox.process.list()
            for proc in existing_processes:
                if proc.name == original_name:
                    logger.warning(
                        f"Found existing process '{original_name}' (status: {proc.status}), terminating it..."
                    )
                    try:
                        await sandbox.process.kill(original_name)
                        logger.info(
                            f"Successfully terminated process '{original_name}'"
                        )
                        # Wait a moment for cleanup
                        await asyncio.sleep(1)
                    except Exception as kill_error:
                        logger.warning(
                            f"Failed to kill process '{original_name}': {kill_error}"
                        )
                        # Continue anyway, might still work
        except Exception as list_error:
            logger.debug(f"Could not list existing processes: {list_error}")

        # For the first attempt, use the original name
        try:
            result = await sandbox.process.exec(process_config)
            return result
        except Exception as exec_error:
            error_str = str(exec_error).lower()
            # Check if it's a duplicate process error
            if "already exists" in error_str or "already running" in error_str:
                logger.warning(
                    f"Process {original_name} already exists, creating unique variant..."
                )
                # Create a unique name and retry
                unique_name = f"{original_name}-{uuid.uuid4().hex[:8]}"
                process_config["name"] = unique_name
                try:
                    result = await sandbox.process.exec(process_config)
                    return result
                except Exception as unique_error:
                    logger.error(
                        f"Unique process {unique_name} also failed: {unique_error}"
                    )
                    raise exec_error  # Raise original error
            elif "timeout" in error_str or "connecttimeout" in error_str:
                logger.warning(
                    f"{operation_name} connection timed out, retrying after delay..."
                )
                await asyncio.sleep(3)  # Wait before retry
                # For timeout, also try with a unique name to avoid conflicts
                unique_name = f"{original_name}-{uuid.uuid4().hex[:8]}-retry"
                process_config["name"] = unique_name
                try:
                    result = await sandbox.process.exec(process_config)
                    logger.info(f"Retry successful for {operation_name}")
                    return result
                except Exception as retry_error:
                    logger.error(f"Retry failed for {operation_name}: {retry_error}")
                    raise exec_error  # Raise original error
            else:
                logger.error(
                    f"{operation_name} failed with non-timeout error: {exec_error}"
                )
                raise exec_error

    @staticmethod
    async def read_sandbox_file(sandbox, file_path: str, logger):
        """Read a file from sandbox with retry logic for connection timeouts."""
        try:
            content = await sandbox.fs.read(file_path)
            return content
        except Exception as read_error:
            error_str = str(read_error).lower()
            if "timeout" in error_str or "connecttimeout" in error_str:
                logger.warning(
                    f"File read from sandbox timed out, retrying after delay..."
                )
                await asyncio.sleep(3)  # Wait before retry
                try:
                    content = await sandbox.fs.read(file_path)
                    logger.info(f"Retry successful for file read: {file_path}")
                    return content
                except Exception as retry_error:
                    logger.error(f"Retry failed for file read: {retry_error}")
                    raise read_error  # Raise original error
            else:
                logger.error(f"File read failed with non-timeout error: {read_error}")
                raise read_error

    @staticmethod
    async def write_sandbox_file(sandbox, file_path: str, content: str, logger):
        """Write a file to sandbox with retry logic for connection timeouts."""
        try:
            await sandbox.fs.write(file_path, content)
            return
        except Exception as write_error:
            error_str = str(write_error).lower()
            if "timeout" in error_str or "connecttimeout" in error_str:
                logger.warning(
                    f"File write to sandbox timed out, retrying after delay..."
                )
                await asyncio.sleep(3)  # Wait before retry
                try:
                    await sandbox.fs.write(file_path, content)
                    logger.info(f"Retry successful for file write: {file_path}")
                    return
                except Exception as retry_error:
                    logger.error(f"Retry failed for file write: {retry_error}")
                    raise write_error  # Raise original error
            else:
                logger.error(f"File write failed with non-timeout error: {write_error}")
                raise write_error


@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List available renderer tools."""
    tools = [
        Tool(
            name="write_manim_file",
            description="Write a Manim Python file to the filesystem",
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
            description="Render a Manim animation using subprocess",
            inputSchema={
                "type": "object",
                "properties": {
                    "scene_name": {
                        "type": "string",
                        "description": "Name of the Manim scene to render",
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
        Tool(
            name="process_video_with_ffmpeg",
            description="Process video using FFmpeg for merging, conversion, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of input video/audio files",
                    },
                    "output_file": {
                        "type": "string",
                        "description": "Output file path",
                    },
                    "ffmpeg_args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional FFmpeg arguments",
                    },
                },
                "required": ["input_files", "output_file"],
            },
        ),
        Tool(
            name="merge_video_audio",
            description="Merge video and audio files using FFmpeg",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_file": {
                        "type": "string",
                        "description": "Path to the video file",
                    },
                    "audio_file": {
                        "type": "string",
                        "description": "Path to the audio file",
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
            description="Check if a file exists and return its metadata",
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
    ]

    return ListToolsResult(tools=tools)


@server.call_tool()
async def call_tool(tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Dispatch renderer tool calls.

    As with the creative server, the low-level MCP server passes
    `(tool_name, arguments)` into this handler.
    """

    try:
        if tool_name == "write_manim_file":
            return await write_manim_file(arguments)
        elif tool_name == "render_manim_animation":
            return await render_manim_animation(arguments)
        elif tool_name == "process_video_with_ffmpeg":
            return await process_video_with_ffmpeg(arguments)
        elif tool_name == "merge_video_audio":
            return await merge_video_audio(arguments)
        elif tool_name == "check_file_exists":
            return await check_file_exists(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {tool_name}")],
                isError=True,
            )
    except Exception as e:
        logger.error(f"Error in tool {tool_name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def write_manim_file(arguments: Dict[str, Any]) -> CallToolResult:
    """Write a Manim Python file."""
    filepath = arguments["filepath"]
    code = arguments["code"]

    try:
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(filepath, "w") as f:
            f.write(code)

        logger.info(f"Manim file written to: {filepath}")

        return CallToolResult(
            content=[
                TextContent(
                    type="text", text=f"Successfully wrote Manim file to {filepath}"
                )
            ]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Failed to write file: {str(e)}")],
            isError=True,
        )


async def render_manim_animation(arguments: Dict[str, Any]) -> CallToolResult:
    """Render a Manim animation using Blaxel sandbox execution with local fallback."""
    scene_name = arguments["scene_name"]
    file_path = arguments["file_path"]
    output_dir = arguments["output_dir"]
    quality = arguments.get("quality", "medium")
    format_type = arguments.get("format", "mp4")
    frame_rate = arguments.get("frame_rate", 30)

    # Try Blaxel sandbox rendering first
    logger.info("Attempting to render using Blaxel sandbox...")
    
    try:
        sandbox_result = await _render_manim_with_sandbox(
            scene_name, file_path, output_dir, quality, format_type, frame_rate
        )
        
        if not sandbox_result.get("isError", False):
            return CallToolResult(
                content=[TextContent(type="text", text=sandbox_result["text"])],
                isError=False,
            )
        
        logger.warning(f"Blaxel sandbox rendering failed: {sandbox_result.get('text')}")
        logger.info("Falling back to local rendering...")
        
    except Exception as e:
        logger.warning(f"Blaxel sandbox rendering error: {str(e)}")
        logger.info("Falling back to local rendering...")
    
    # Fallback to local rendering
    logger.info("Using local Manim rendering...")
    local_result = await _render_manim_locally(
        scene_name, file_path, output_dir, quality, format_type, frame_rate
    )

    return CallToolResult(
        content=[TextContent(type="text", text=local_result["text"])],
        isError=local_result.get("isError", False),
    )


async def _render_manim_with_sandbox(
    scene_name: str,
    file_path: str,
    output_dir: str,
    quality: str,
    format_type: str,
    frame_rate: int,
) -> Dict[str, Any]:
    """Render a Manim animation using Blaxel sandbox execution."""
    # Map quality to manim flags
    quality_flags = {
        "low": "-ql",
        "medium": "-qm",
        "high": "-qh",
        "production_quality": "-qp",
    }
    quality_flag = quality_flags.get(quality, "-qm")

    try:
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Read the Manim code file
        with open(file_path, "r") as f:
            manim_code = f.read()

        logger.info(f"Creating Blaxel sandbox for scene: {scene_name}")

        # Sanitize scene name for valid sandbox name
        sanitized_scene_name = scene_name.lower().replace(" ", "-").replace("_", "-")
        # Ensure name is not too long and only contains valid characters
        import re

        sanitized_scene_name = re.sub(r"[^a-z0-9\-]", "", sanitized_scene_name)[:20]
        if not sanitized_scene_name:
            sanitized_scene_name = "default"

        try:
            # Create or get sandbox using Blaxel SDK
            # Uses BL_WORKSPACE and BL_API_KEY from environment or .env file
            logger.info(f"Creating Blaxel sandbox: manim-render-{sanitized_scene_name}")
            try:
                # Create sandbox with proper virtual environment
                sandbox = await SandboxInstance.create(
                    {
                        "name": f"manim-render-{sanitized_scene_name}",
                        "image": "blaxel/py-app:latest",
                        "memory": 4096,
                        # Use virtual environment instead of system
                        "virtual": True,
                    }
                )
                logger.info(f"Successfully created sandbox: {sandbox.metadata.name}")

                # Wait a moment for sandbox to fully initialize
                logger.info("Waiting for sandbox to initialize...")
                await asyncio.sleep(2)

            except Exception as create_error:
                # Handle connection timeouts by retrying
                error_str = str(create_error).lower()
                if "timeout" in error_str or "connecttimeout" in error_str:
                    logger.warning(
                        "Sandbox creation connection timed out, retrying after delay..."
                    )
                    await asyncio.sleep(5)  # Wait longer before retry
                    try:
                        # Retry once
                        sandbox = await SandboxInstance.create(
                            {
                                "name": f"manim-render-{sanitized_scene_name}",
                                "image": "blaxel/py-app:latest",
                                "memory": 4096,
                            }
                        )
                        logger.info(
                            f"Retry successful: Created sandbox: {sandbox.metadata.name}"
                        )

                        # Wait for sandbox to initialize
                        logger.info("Waiting for sandbox to initialize after retry...")
                        await asyncio.sleep(3)

                    except Exception as retry_error:
                        logger.error(f"Retry failed: {retry_error}")
                        raise create_error  # Raise original error
                else:
                    logger.error(
                        f"Sandbox creation failed with non-timeout error: {create_error}"
                    )
                    raise create_error
        except Exception as sandbox_error:
            error_msg = f"Failed to create Blaxel sandbox: {str(sandbox_error)}"
            logger.error(error_msg)
            return {"text": error_msg, "isError": True}

        try:
            # Write the Manim code to the sandbox
            sandbox_file_path = f"/tmp/{scene_name}.py"
            logger.info(f"Writing Manim code to sandbox: {sandbox_file_path}")
            await RendererTool.write_sandbox_file(
                sandbox, sandbox_file_path, manim_code, logger
            )
            logger.info(
                f"Successfully wrote Manim code to sandbox: {sandbox_file_path}"
            )

            # Initialize flag for Manim installation check
            manim_already_installed = False

            # Test what's available in the sandbox
            logger.info("Testing sandbox environment...")
            try:
                test_result = await RendererTool.execute_sandbox_process(
                    sandbox,
                    {
                        "name": "test-environment",
                        "command": "which python3 && python3 --version && which pip && pip --version",
                        "wait_for_completion": True,
                    },
                    logger,
                    "Environment test",
                )
                logger.info(f"Environment test result: {test_result}")

                # Get test logs
                try:
                    test_logs = await sandbox.process.logs("test-environment", "all")
                    logger.info(f"Environment test logs: {test_logs}")
                except Exception as log_error:
                    logger.warning(f"Could not retrieve test logs: {log_error}")
            except Exception as test_error:
                logger.warning(f"Environment test failed: {test_error}")

            # Test if apt-get is available
            logger.info("Testing if apt-get is available...")
            try:
                apt_test_result = await RendererTool.execute_sandbox_process(
                    sandbox,
                    {
                        "name": "test-apt",
                        "command": "which apt-get || echo 'apt-get not found'",
                        "wait_for_completion": True,
                    },
                    logger,
                    "Apt availability test",
                )
                logger.info(f"Apt test result: {apt_test_result}")

                # Get apt test logs
                try:
                    apt_test_logs = await sandbox.process.logs("test-apt", "all")
                    logger.info(f"Apt test logs: {apt_test_logs}")
                except Exception as log_error:
                    logger.warning(f"Could not retrieve apt test logs: {log_error}")
            except Exception as apt_test_error:
                logger.warning(f"Apt test failed: {apt_test_error}")

            # Try a simple pip install first to see if it works
            logger.info("Testing pip install...")
            try:
                pip_test_result = await RendererTool.execute_sandbox_process(
                    sandbox,
                    {
                        "name": "test-pip",
                        "command": "pip install --dry-run manim",
                        "wait_for_completion": True,
                    },
                    logger,
                    "Pip test",
                )
                logger.info(f"Pip test result: {pip_test_result}")

                # Get pip test logs
                try:
                    pip_test_logs = await sandbox.process.logs("test-pip", "all")
                    logger.info(f"Pip test logs: {pip_test_logs}")
                except Exception as log_error:
                    logger.warning(f"Could not retrieve pip test logs: {log_error}")
            except Exception as pip_test_error:
                logger.warning(f"Pip test failed: {pip_test_error}")

            # Check if Manim is already installed
            logger.info("Checking if Manim is already installed...")
            try:
                manim_check_result = await RendererTool.execute_sandbox_process(
                    sandbox,
                    {
                        "name": "check-manim",
                        "command": "python3 -c \"import manim; print('Manim version:', manim.__version__)\" || echo 'Manim not found'",
                        "wait_for_completion": True,
                    },
                    logger,
                    "Manim check",
                )
                logger.info(f"Manim check result: {manim_check_result}")

                # Get manim check logs
                try:
                    manim_check_logs = await sandbox.process.logs("check-manim", "all")
                    logger.info(f"Manim check logs: {manim_check_logs}")

                    # Check if Manim is installed
                    if "Manim version:" in str(manim_check_logs):
                        logger.info("Manim is already installed, skipping installation")
                        manim_already_installed = True
                    else:
                        logger.info(
                            "Manim is not installed, proceeding with installation"
                        )
                        manim_already_installed = False
                except Exception as log_error:
                    logger.warning(f"Could not retrieve manim check logs: {log_error}")
                    manim_already_installed = False
            except Exception as manim_check_error:
                logger.warning(f"Manim check failed: {manim_check_error}")
                manim_already_installed = False

            # Install manim and its dependencies in the sandbox
            logger.info("Installing manim and dependencies in the sandbox...")

            # Check if ffmpeg is already available
            logger.info("Checking if ffmpeg is available...")
            try:
                ffmpeg_check_result = await RendererTool.execute_sandbox_process(
                    sandbox,
                    {
                        "name": "check-ffmpeg",
                        "command": "which ffmpeg || echo 'ffmpeg not found'",
                        "wait_for_completion": True,
                    },
                    logger,
                    "FFmpeg availability check",
                )
                logger.info(f"Ffmpeg check result: {ffmpeg_check_result}")

                # Get ffmpeg check logs
                try:
                    ffmpeg_check_logs = await sandbox.process.logs(
                        "check-ffmpeg", "all"
                    )
                    logger.info(f"Ffmpeg check logs: {ffmpeg_check_logs}")
                except Exception as log_error:
                    logger.warning(f"Could not retrieve ffmpeg check logs: {log_error}")
            except Exception as ffmpeg_check_error:
                logger.warning(f"Ffmpeg check failed: {ffmpeg_check_error}")

            # Skip installation if Manim is already installed
            if manim_already_installed:
                logger.info(
                    "Skipping dependencies installation as Manim is already installed"
                )
                manim_installed = True
            else:
                # Try to install system dependencies step-by-step for better reliability
                logger.info("Installing system dependencies step-by-step...")

                # First update package lists
                try:
                    logger.info("Updating package lists...")
                    update_result = await RendererTool.execute_sandbox_process(
                        sandbox,
                        {
                            "name": "apt-update",
                            "command": "apt-get update",
                            "wait_for_completion": True,
                            "timeout": 120,
                        },
                        logger,
                        "Package list update",
                    )
                    logger.info(f"Package update result: {update_result}")

                    if update_result.status != "exited" or (
                        hasattr(update_result, "exit_code")
                        and update_result.exit_code != 0
                    ):
                        logger.warning("Package update failed, but continuing...")
                except Exception as update_error:
                    logger.warning(
                        f"Package update failed: {update_error}, continuing..."
                    )

                # Install ffmpeg
                try:
                    logger.info("Installing ffmpeg...")
                    ffmpeg_result = await RendererTool.execute_sandbox_process(
                        sandbox,
                        {
                            "name": "install-ffmpeg",
                            "command": "apt-get install -y ffmpeg",
                            "wait_for_completion": True,
                            "timeout": 180,
                        },
                        logger,
                        "FFmpeg installation",
                    )
                    logger.info(f"FFmpeg installation result: {ffmpeg_result}")

                    if ffmpeg_result.status != "exited" or (
                        hasattr(ffmpeg_result, "exit_code")
                        and ffmpeg_result.exit_code != 0
                    ):
                        logger.warning("FFmpeg installation failed, but continuing...")
                except Exception as ffmpeg_error:
                    logger.warning(
                        f"FFmpeg installation failed: {ffmpeg_error}, continuing..."
                    )

                # Install libcairo2-dev
                try:
                    logger.info("Installing libcairo2-dev...")
                    cairo_result = await RendererTool.execute_sandbox_process(
                        sandbox,
                        {
                            "name": "install-cairo",
                            "command": "apt-get install -y libcairo2-dev",
                            "wait_for_completion": True,
                            "timeout": 180,
                        },
                        logger,
                        "Cairo installation",
                    )
                    logger.info(f"Cairo installation result: {cairo_result}")

                    if cairo_result.status != "exited" or (
                        hasattr(cairo_result, "exit_code")
                        and cairo_result.exit_code != 0
                    ):
                        logger.warning("Cairo installation failed, but continuing...")
                except Exception as cairo_error:
                    logger.warning(
                        f"Cairo installation failed: {cairo_error}, continuing..."
                    )

                # Install Python dependencies - try lighter alternatives first
                logger.info("Installing Python dependencies...")
                manim_installed = False

                # Try installing manim Community Edition (lighter than full manim)
                install_commands = [
                    ("pip install manimlib", "manimlib installation"),
                    ("pip install manim", "full manim installation"),
                    (
                        "pip install --no-deps manim && pip install numpy scipy matplotlib",
                        "minimal manim with deps",
                    ),
                ]

                for install_cmd, description in install_commands:
                    if manim_installed:
                        break

                    try:
                        logger.info(f"Trying {description}: {install_cmd}")
                        install_result = await RendererTool.execute_sandbox_process(
                            sandbox,
                            {
                                "name": "install-manim-attempt",
                                "command": install_cmd,
                                "wait_for_completion": True,
                                "timeout": 600,  # 10 minute timeout
                            },
                            logger,
                            description,
                        )
                        logger.info(f"{description} result: {install_result}")

                        if install_result.status == "exited" and (
                            not hasattr(install_result, "exit_code")
                            or install_result.exit_code == 0
                        ):
                            logger.info(f"Successfully installed with: {install_cmd}")
                            manim_installed = True

                            # Verify installation
                            try:
                                verify_result = await RendererTool.execute_sandbox_process(
                                    sandbox,
                                    {
                                        "name": "verify-manim",
                                        "command": "python3 -c \"import manim; print('Manim version:', getattr(manim, '__version__', 'unknown'))\"",
                                        "wait_for_completion": True,
                                        "timeout": 30,
                                    },
                                    logger,
                                    "Manim verification",
                                )
                                logger.info(
                                    f"Manim verification result: {verify_result}"
                                )
                            except Exception as verify_error:
                                logger.warning(
                                    f"Manim verification failed: {verify_error}"
                                )
                        else:
                            logger.warning(
                                f"{description} failed, trying next option..."
                            )

                        # Get installation logs for debugging (for the last attempt)
                        try:
                            install_logs = await sandbox.process.logs(
                                "install-manim-attempt", "all"
                            )
                            logger.info(f"Manim installation logs: {install_logs}")
                        except Exception as log_error:
                            logger.warning(
                                f"Could not retrieve installation logs: {log_error}"
                            )

                        # Check if the last installation attempt was successful
                        if install_result.status != "exited" or (
                            hasattr(install_result, "exit_code")
                            and install_result.exit_code != 0
                        ):
                            error_msg = f"Manim installation failed with status: {install_result.status}"
                            if hasattr(install_result, "exit_code"):
                                error_msg += f", exit code: {install_result.exit_code}"

                            # Try to get more detailed logs
                            try:
                                install_logs = await sandbox.process.logs(
                                    "install-manim-attempt", "all"
                                )
                                error_msg += f"\nLogs: {install_logs}"
                            except Exception as log_error:
                                error_msg += f"\nCould not retrieve logs: {log_error}"

                            logger.error(error_msg)
                            # Don't return error here, continue to check if any installation worked

                    except Exception as install_error:
                        # Handle timeout specifically
                        error_str = str(install_error).lower()
                        if "timeout" in error_str or "readtimeout" in error_str:
                            logger.warning(
                                "Pip install manim timed out - this might be OK if packages were already installed or partially installed"
                            )
                            # Try to check if manim was actually installed despite timeout
                            try:
                                manim_check_after = await RendererTool.execute_sandbox_process(
                                    sandbox,
                                    {
                                        "name": "check-manim-after-install",
                                        "command": "python3 -c \"import manim; print('Manim available after install timeout')\" || echo 'Manim not available after install timeout'",
                                        "wait_for_completion": True,
                                    },
                                    logger,
                                    "Post-install Manim check",
                                )
                                logger.info(
                                    f"Post-install Manim check result: {manim_check_after}"
                                )

                                # Get logs
                                try:
                                    check_logs = await sandbox.process.logs(
                                        "check-manim-after-install", "all"
                                    )
                                    logger.info(
                                        f"Post-install check logs: {check_logs}"
                                    )

                                    if "manim available" in str(check_logs).lower():
                                        logger.info(
                                            "Manim appears to be installed despite timeout, continuing..."
                                        )
                                        manim_installed = True
                                    else:
                                        logger.warning(
                                            "Manim not available after install timeout, may cause render failure"
                                        )
                                except Exception as log_error:
                                    logger.warning(
                                        f"Could not check post-install logs: {log_error}"
                                    )
                            except Exception as check_error:
                                logger.warning(
                                    f"Could not verify Manim installation after timeout: {check_error}"
                                )
                        else:
                            import traceback

                            error_details = traceback.format_exc()
                            error_msg = f"Error during pip install manim: {str(install_error)}\nDetails: {error_details}"

                            # Try to get installation logs for debugging
                            try:
                                install_logs = await sandbox.process.logs(
                                    "install-manim-attempt", "all"
                                )
                                error_msg += f"\nInstallation logs: {install_logs}"
                            except Exception as log_error:
                                error_msg += f"\nCould not retrieve installation logs: {log_error}"

                            logger.error(error_msg)
                            # Don't return error here, continue to try other installation methods

                        logger.warning(f"{description} failed: {install_error}")
                        continue

            # Final check: ensure Manim is actually installed before proceeding to render
            if not manim_already_installed and not manim_installed:
                logger.warning(
                    "Manim installation appears to have failed, attempting final verification..."
                )

                # Final verification attempt
                try:
                    final_check = await RendererTool.execute_sandbox_process(
                        sandbox,
                        {
                            "name": "final-manim-check",
                            "command": "python3 -c \"import manim; print('SUCCESS: Manim is available')\" || echo 'FAILED: Manim not available'",
                            "wait_for_completion": True,
                            "timeout": 30,
                        },
                        logger,
                        "Final Manim availability check",
                    )

                    # Get logs to check result
                    try:
                        check_logs = await sandbox.process.logs(
                            "final-manim-check", "all"
                        )
                        if "SUCCESS" in str(check_logs):
                            logger.info(
                                "Final check confirms Manim is available, proceeding with render"
                            )
                            manim_installed = True
                        else:
                            error_msg = f"Final verification shows Manim is not available. Installation appears to have failed.\nCheck logs: {check_logs}"
                            logger.error(error_msg)
                            return {"text": error_msg, "isError": True}
                    except Exception as log_error:
                        logger.warning(
                            f"Could not retrieve final check logs: {log_error}"
                        )

                except Exception as final_check_error:
                    error_msg = f"Cannot verify Manim installation: {final_check_error}"
                    logger.error(error_msg)
                    return {"text": error_msg, "isError": True}

            # Run the Manim render command - try different possible commands
            render_commands = [
                f"manim {quality_flag} --fps {frame_rate} -o {scene_name}.{format_type} {sandbox_file_path} {scene_name}",
                f"python3 -m manim {quality_flag} --fps {frame_rate} -o {scene_name}.{format_type} {sandbox_file_path} {scene_name}",
                f"manimce {quality_flag} --fps {frame_rate} -o {scene_name}.{format_type} {sandbox_file_path} {scene_name}",
            ]

            render_success = False
            render_result = None

            for cmd in render_commands:
                if render_success:
                    break

                logger.info(f"Trying render command: {cmd}")
                try:
                    render_result = await RendererTool.execute_sandbox_process(
                        sandbox,
                        {
                            "name": "render-manim",
                            "command": cmd,
                            "wait_for_completion": True,
                            "timeout": 600,  # 10 minute timeout for rendering
                        },
                        logger,
                        f"Manim rendering with '{cmd}'",
                    )
                    logger.info(f"Render result: {render_result}")

                    if render_result.status == "exited" and (
                        not hasattr(render_result, "exit_code")
                        or render_result.exit_code == 0
                    ):
                        logger.info(f"Successfully rendered with: {cmd}")
                        render_success = True
                    else:
                        logger.warning(
                            f"Render failed with command '{cmd}', trying next option..."
                        )

                except Exception as render_error:
                    logger.warning(f"Render failed with '{cmd}': {render_error}")
                    continue
                # Check if rendering was successful
                if not render_success:
                    error_msg = "All render command attempts failed."

                    # Try to get logs for debugging from the last attempt
                    try:
                        logs = await sandbox.process.logs("render-manim", "all")
                        error_msg += f"\nLast render logs: {logs}"
                    except Exception as log_error:
                        error_msg += f"\nCould not retrieve logs: {log_error}"

                    logger.error(error_msg)
                    return {"text": error_msg, "isError": True}
            # If we get here and render wasn't successful, it's an error
            if not render_success:
                error_msg = "Manim rendering failed - no working render command found"
                logger.error(error_msg)
                return {"text": error_msg, "isError": True}

        except Exception as render_error:
            # Handle timeout specifically
            error_str = str(render_error).lower()
            if "timeout" in error_str or "readtimeout" in error_str:
                logger.warning(
                    "Manim render timed out - this indicates a long-running render process"
                )
                # Try to continue and check if output was generated
            else:
                error_msg = f"Error during manim rendering: {str(render_error)}"
                logger.error(error_msg)
                return {"text": error_msg, "isError": True}

            # Find the output file in the sandbox
            # Manim typically outputs to media/videos/{scene_name}/{quality}/
            possible_paths = [
                f"/tmp/media/videos/{scene_name}/{quality}/{scene_name}.{format_type}",
                f"/tmp/media/videos/{scene_name.lower()}/{quality}/{scene_name}.{format_type}",
                f"/tmp/{scene_name}.{format_type}",
                f"/root/media/videos/{scene_name}/{quality}/{scene_name}.{format_type}",
            ]

            output_content = None
            found_path = None

            for sandbox_path in possible_paths:
                try:
                    output_content = await RendererTool.read_sandbox_file(
                        sandbox, sandbox_path, logger
                    )
                    found_path = sandbox_path
                    logger.info(f"Found output at: {sandbox_path}")
                    break
                except Exception:
                    continue

            if not output_content:
                # List files to debug
                try:
                    ls_result = await RendererTool.execute_sandbox_process(
                        sandbox,
                        {
                            "name": "find-output",
                            "command": "find /tmp -name '*.mp4' -o -name '*.gif' 2>/dev/null || true",
                            "wait_for_completion": True,
                        },
                        logger,
                        "Find output files",
                    )
                    find_logs = await sandbox.process.logs("find-output", "stdout")
                    logger.info(f"Found video files: {find_logs}")
                except Exception:
                    pass

                error_msg = f"Could not find rendered output file. Searched paths: {possible_paths}"
                logger.error(error_msg)
                return {"text": error_msg, "isError": True}

            # Write the output to local filesystem
            output_path = Path(output_dir) / f"{scene_name}.{format_type}"

            # Handle the content - it may be base64 encoded or bytes
            if isinstance(output_content, str):
                try:
                    decoded_content = base64.b64decode(output_content)
                    with open(output_path, "wb") as f:
                        f.write(decoded_content)
                except Exception:
                    with open(output_path, "w") as f:
                        f.write(output_content)
            elif isinstance(output_content, (bytes, bytearray)):
                with open(output_path, "wb") as f:
                    f.write(output_content)
            else:
                with open(output_path, "wb") as f:
                    f.write(output_content)

            result_msg = (
                f"Successfully rendered animation using Blaxel sandbox!\n"
                f"Scene: {scene_name}\n"
                f"Output file: {output_path}\n"
                f"Quality: {quality}\n"
                f"Format: {format_type}\n"
                f"File size: {output_path.stat().st_size if output_path.exists() else 'Unknown'} bytes"
            )

            logger.info(result_msg)
            return {"text": result_msg, "isError": False}

        finally:
            # Clean up sandbox
            try:
                await SandboxInstance.delete(sandbox.metadata.name)
                logger.info(f"Deleted sandbox: {sandbox.metadata.name}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to delete sandbox: {cleanup_error}")

    except asyncio.TimeoutError:
        error_msg = "Blaxel sandbox execution timed out"
        logger.error(error_msg)
        return {"text": error_msg, "isError": True}
    except Exception as e:
        # Get detailed exception information
        import traceback

        error_details = traceback.format_exc()
        error_msg = (
            f"Error during Blaxel sandbox rendering: {str(e)}\nDetails: {error_details}"
        )
        logger.error(error_msg)
        return {"text": error_msg, "isError": True}


async def _render_manim_locally(
    scene_name: str,
    file_path: str,
    output_dir: str,
    quality: str,
    format_type: str,
    frame_rate: int,
) -> Dict[str, Any]:
    """Render a Manim animation using local Manim installation."""
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
        # Assume the project root contains .venv directory
        project_root = Path(__file__).resolve().parent.parent
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

        logger.info(f"Running local Manim command: {' '.join(cmd)}")

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
            cwd=output_dir,  # Run in output directory
            env=env,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = f"Local Manim rendering failed:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"
            logger.error(error_msg)
            return {"text": error_msg, "isError": True}

        # Log the stdout for debugging
        logger.info(f"Manim stdout: {stdout.decode()}")
        logger.info(f"Manim stderr: {stderr.decode()}")

        # Find the output file
        # Manim typically outputs to media/videos/{filename}/{quality}/
        import glob

        # First, let's see what files actually exist in the output directory
        logger.info(f"Listing all files in output directory: {output_dir}")
        try:
            all_files = list(Path(output_dir).rglob("*"))
            logger.info(f"Found {len(all_files)} files/dirs:")
            for f in all_files[:50]:  # Log first 50 to avoid spam
                logger.info(f"  - {f}")
        except Exception as list_error:
            logger.warning(f"Could not list files: {list_error}")

        # Manim outputs to paths like: media/videos/{filename}/{resolution}/SceneName.mp4
        # where resolution is like: 720p30, 480p15, 1080p60, 2160p60
        # Quality flags map to resolutions:
        # -ql (low): 480p15
        # -qm (medium): 720p30
        # -qh (high): 1080p60
        # -qp (production): 2160p60

        # Map quality to likely resolution folder names
        quality_to_resolution = {
            "low": ["480p15", "854x480", "480p"],
            "medium": ["720p30", "1280x720", "720p"],
            "high": ["1080p60", "1920x1080", "1080p"],
            "production_quality": ["2160p60", "3840x2160", "2160p"],
        }

        resolutions = quality_to_resolution.get(quality, ["720p30"])

        output_patterns = []

        # Search with specific resolutions
        for res in resolutions:
            output_patterns.extend(
                [
                    f"{output_dir}/media/videos/*/{res}/{scene_name}.{format_type}",
                    f"{output_dir}/media/videos/**/{res}/{scene_name}.{format_type}",
                ]
            )

        # Fallback: search all resolution patterns
        output_patterns.extend(
            [
                f"{output_dir}/media/videos/*/*/{scene_name}.{format_type}",
                f"{output_dir}/media/videos/**/{scene_name}.{format_type}",
                f"{output_dir}/videos/*/*/{scene_name}.{format_type}",
                f"{output_dir}/**/{scene_name}.{format_type}",
                f"{output_dir}/{scene_name}.{format_type}",
            ]
        )

        output_files = []
        for pattern in output_patterns:
            logger.info(f"Trying pattern: {pattern}")
            matches = glob.glob(pattern, recursive=True)
            if matches:
                logger.info(f"  Found matches: {matches}")
                output_files.extend(matches)
                break

        if not output_files:
            error_msg = f"Could not find rendered output file.\nSearched patterns: {output_patterns}\nStdout: {stdout.decode()}\nStderr: {stderr.decode()}"
            logger.error(error_msg)
            return {"text": error_msg, "isError": True}

        output_file = output_files[0]  # Take the first match
        final_output = Path(output_dir) / f"{scene_name}.{format_type}"

        # Move the output file to the expected location
        import shutil

        shutil.move(output_file, final_output)

        result_msg = (
            f"Successfully rendered animation locally!\n"
            f"Scene: {scene_name}\n"
            f"Output file: {final_output}\n"
            f"Quality: {quality}\n"
            f"Format: {format_type}\n"
            f"File size: {final_output.stat().st_size if final_output.exists() else 'Unknown'} bytes"
        )

        logger.info(result_msg)
        return {"text": result_msg, "isError": False}

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        error_msg = (
            f"Error during local Manim rendering: {str(e)}\nDetails: {error_details}"
        )
        logger.error(error_msg)
        return {"text": error_msg, "isError": True}


async def process_video_with_ffmpeg(arguments: Dict[str, Any]) -> CallToolResult:
    """Process video using FFmpeg."""
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

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = f"FFmpeg processing failed: {stderr.decode()}"
            logger.error(error_msg)
            return CallToolResult(
                content=[TextContent(type="text", text=error_msg)], isError=True
            )

        result_msg = f"Successfully processed video with FFmpeg: {output_file}"
        logger.info(result_msg)

        return CallToolResult(content=[TextContent(type="text", text=result_msg)])

    except Exception as e:
        error_msg = f"Error during FFmpeg processing: {str(e)}"
        logger.error(error_msg)
        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)], isError=True
        )


async def merge_video_audio(arguments: Dict[str, Any]) -> CallToolResult:
    """Merge video and audio files."""
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
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            "-y",  # Overwrite output file
            output_file,
        ]

        logger.info(f"Merging video and audio: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = f"Video/audio merge failed: {stderr.decode()}"
            logger.error(error_msg)
            return CallToolResult(
                content=[TextContent(type="text", text=error_msg)], isError=True
            )

        result_msg = f"Successfully merged video and audio: {output_file}"
        logger.info(result_msg)

        return CallToolResult(content=[TextContent(type="text", text=result_msg)])

    except Exception as e:
        error_msg = f"Error during video/audio merge: {str(e)}"
        logger.error(error_msg)
        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)], isError=True
        )


async def check_file_exists(arguments: Dict[str, Any]) -> CallToolResult:
    """Check if a file exists and return its metadata."""
    filepath = arguments["filepath"]

    try:
        path = Path(filepath)

        if not path.exists():
            return CallToolResult(
                content=[
                    TextContent(type="text", text=f"File does not exist: {filepath}")
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

        return CallToolResult(
            content=[
                TextContent(
                    type="text", text=f"File metadata: {json.dumps(metadata, indent=2)}"
                )
            ]
        )

    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error checking file: {str(e)}")],
            isError=True,
        )


async def main():
    """Main entry point for the renderer MCP server."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="neuroanim-renderer",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
