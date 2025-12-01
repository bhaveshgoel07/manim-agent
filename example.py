#!/usr/bin/env python3
"""
Example script demonstrating NeuroAnim usage.

This script shows how to use the NeuroAnim orchestrator to generate
educational animations for various STEM topics.
"""

import asyncio
import os

from orchestrator import NeuroAnimOrchestrator


async def generate_example_animations():
    """Generate several example animations."""

    # Make sure we have API keys
    hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

    if not hf_api_key:
        print("⚠️  Please set HUGGINGFACE_API_KEY environment variable")
        print("   You can get one from: https://huggingface.co/settings/tokens")
        return

    if not elevenlabs_api_key:
        print("⚠️  Warning: ELEVENLABS_API_KEY not set")
        print("   Audio will use Hugging Face TTS (lower quality)")
        print("   Get an API key from: https://elevenlabs.io")
        print("   Continuing with Hugging Face TTS...")

    orchestrator = NeuroAnimOrchestrator(
        hf_api_key=hf_api_key, elevenlabs_api_key=elevenlabs_api_key
    )

    try:
        await orchestrator.initialize()

        examples = [
            {
                "topic": "Photosynthesis",
                "audience": "college",
                "duration": 1.0,
                "output": "photosynthesis_animation.mp4",
            }
            # {
            #     "topic": "Pythagorean Theorem",
            #     "audience": "high_school",
            #     "duration": 1.5,
            #     "output": "pythagorean_animation.mp4",
            # },
            # {
            #     "topic": "Newton's Laws of Motion",
            #     "audience": "college",
            #     "duration": 3.0,
            #     "output": "newton_laws_animation.mp4",
            # },
        ]

        for example in examples:
            print(f"\n🎬 Generating animation for: {example['topic']}")

            results = await orchestrator.generate_animation(
                topic=example["topic"],
                target_audience=example["audience"],
                animation_length_minutes=example["duration"],
                output_filename=example["output"],
            )

            if results["success"]:
                print(f"✅ Successfully generated: {results['output_file']}")
            else:
                print(f"❌ Failed: {results['error']}")

    except Exception as e:
        print(f"💥 Error in example generation: {str(e)}")
    finally:
        await orchestrator.cleanup()


if __name__ == "__main__":
    asyncio.run(generate_example_animations())
