#!/usr/bin/env python3
"""
NeuroAnim - STEM Animation Generator with LangGraph

Main entry point for the NeuroAnim system using LangGraph for workflow orchestration.
This version uses a single unified Manim MCP server and LangGraph for better modularity.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from neuroanim import run_animation_pipeline
from utils.tts import TTSGenerator

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class NeuroAnimApp:
    """Main application for NeuroAnim animation generation."""

    def __init__(
        self,
        hf_api_key: str = None,
        elevenlabs_api_key: str = None,
    ):
        """
        Initialize the NeuroAnim application.

        Args:
            hf_api_key: HuggingFace API key (optional, falls back to env var)
            elevenlabs_api_key: ElevenLabs API key (optional, falls back to env var)
        """
        self.hf_api_key = hf_api_key or os.getenv("HUGGINGFACE_API_KEY")
        self.elevenlabs_api_key = elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")

        # Initialize TTS generator
        self.tts_generator = TTSGenerator(
            elevenlabs_api_key=self.elevenlabs_api_key,
            hf_api_key=self.hf_api_key,
            fallback_enabled=True,
        )

        # MCP session components
        self.mcp_session = None
        self._mcp_cm = None
        self._mcp_streams = None

    async def initialize(self):
        """Initialize the MCP server connection."""
        logger.info("🚀 Initializing NeuroAnim...")

        # Initialize Manim MCP server
        mcp_params = StdioServerParameters(
            command="python",
            args=["manim_mcp/server.py"],
            env=({"HUGGINGFACE_API_KEY": self.hf_api_key} if self.hf_api_key else None),
        )

        self._mcp_cm = stdio_client(mcp_params)
        self._mcp_streams = await self._mcp_cm.__aenter__()
        read_stream, write_stream = self._mcp_streams
        self.mcp_session = ClientSession(read_stream, write_stream)
        await self.mcp_session.__aenter__()
        await self.mcp_session.initialize()

        logger.info("✅ Manim MCP server connected")

    async def cleanup(self):
        """Clean up resources."""
        logger.info("🧹 Cleaning up...")

        # Close MCP session
        if self.mcp_session:
            try:
                await self.mcp_session.__aexit__(None, None, None)
            except (Exception, asyncio.CancelledError) as e:
                logger.debug(f"Error closing MCP session: {e}")

        # Close stdio client context manager
        if self._mcp_cm:
            try:
                async with asyncio.timeout(2):
                    await self._mcp_cm.__aexit__(None, None, None)
            except (Exception, asyncio.CancelledError, TimeoutError) as e:
                logger.debug(f"Error closing MCP context manager: {e}")

        logger.info("✅ Cleanup complete")

    async def generate_animation(
        self,
        topic: str,
        target_audience: str = "general",
        animation_length_minutes: float = 2.0,
        output_filename: str = "animation.mp4",
        rendering_quality: str = "medium",
        max_retries: int = 3,
    ):
        """
        Generate an educational animation.

        Args:
            topic: STEM topic to animate
            target_audience: Target audience level (elementary, middle_school, high_school, college, general)
            animation_length_minutes: Desired animation length in minutes
            output_filename: Name for the output file
            rendering_quality: Manim rendering quality (low, medium, high, production_quality)
            max_retries: Maximum retry attempts per step

        Returns:
            Dictionary with pipeline results
        """
        logger.info(f"🎬 Generating animation for topic: '{topic}'")

        # Run the LangGraph pipeline
        result = await run_animation_pipeline(
            mcp_session=self.mcp_session,
            tts_generator=self.tts_generator,
            topic=topic,
            target_audience=target_audience,
            animation_length_minutes=animation_length_minutes,
            output_filename=output_filename,
            rendering_quality=rendering_quality,
            max_retries=max_retries,
        )

        return result


async def main():
    """Main entry point for the application."""
    print("🎨 NeuroAnim - STEM Animation Generator")
    print("=" * 50)
    print()

    # Get user input
    topic = input("📚 Enter a STEM topic to animate: ").strip()
    if not topic:
        print("❌ Topic cannot be empty")
        return

    # Optional: Get target audience
    print("\n🎯 Target Audience:")
    print("  1. Elementary")
    print("  2. Middle School")
    print("  3. High School")
    print("  4. College")
    print("  5. General")
    audience_choice = input("Select (1-5) [default: 5]: ").strip() or "5"

    audience_map = {
        "1": "elementary",
        "2": "middle_school",
        "3": "high_school",
        "4": "college",
        "5": "general",
    }
    target_audience = audience_map.get(audience_choice, "general")

    # Optional: Get animation length
    length_input = input("\n⏱️  Animation length in minutes [default: 2.0]: ").strip()
    try:
        animation_length = float(length_input) if length_input else 2.0
    except ValueError:
        animation_length = 2.0

    # Optional: Get quality
    print("\n🎬 Rendering Quality:")
    print("  1. Low (fast, 480p)")
    print("  2. Medium (balanced, 720p)")
    print("  3. High (slow, 1080p)")
    print("  4. Production (very slow, 4K)")
    quality_choice = input("Select (1-4) [default: 2]: ").strip() or "2"

    quality_map = {
        "1": "low",
        "2": "medium",
        "3": "high",
        "4": "production_quality",
    }
    rendering_quality = quality_map.get(quality_choice, "medium")

    print()
    print("=" * 50)
    print(f"📝 Configuration:")
    print(f"  Topic: {topic}")
    print(f"  Audience: {target_audience}")
    print(f"  Length: {animation_length} minutes")
    print(f"  Quality: {rendering_quality}")
    print("=" * 50)
    print()

    # Initialize the app
    app = NeuroAnimApp()

    try:
        # Initialize MCP connection
        await app.initialize()

        # Generate animation
        result = await app.generate_animation(
            topic=topic,
            target_audience=target_audience,
            animation_length_minutes=animation_length,
            rendering_quality=rendering_quality,
        )

        # Display results
        print()
        print("=" * 50)
        if result["success"]:
            print("✅ ANIMATION GENERATION SUCCESSFUL!")
            print(f"📹 Output: {result['final_output_path']}")
            print(f"⏱️  Time: {result.get('total_duration', 0):.2f}s")
            print(f"✓ Steps completed: {len(result['completed_steps'])}")

            if result.get("warnings"):
                print(f"\n⚠️  Warnings ({len(result['warnings'])}):")
                for warning in result["warnings"]:
                    print(f"  - {warning}")

            if result.get("quiz"):
                print("\n❓ Quiz Questions:")
                print(result["quiz"][:500])  # Print first 500 chars

        else:
            print("❌ ANIMATION GENERATION FAILED")
            print(f"Errors: {len(result.get('errors', []))}")
            for error in result.get("errors", []):
                print(f"  - {error}")

        print("=" * 50)

    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

    finally:
        # Clean up
        await app.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
