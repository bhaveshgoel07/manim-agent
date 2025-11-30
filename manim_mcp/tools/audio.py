"""
Audio Tools for Manim MCP Server

This module provides tools for generating narration scripts and speech audio.
"""

import json
import logging
from typing import Any, Dict, Optional

from mcp.types import CallToolResult, TextContent

from utils.hf_wrapper import HFInferenceWrapper, ModelConfig

logger = logging.getLogger(__name__)


async def generate_narration(
    hf_wrapper: HFInferenceWrapper, arguments: Dict[str, Any]
) -> CallToolResult:
    """
    Generate a narration script for an educational animation.

    Uses a text LLM to create an engaging, age-appropriate narration script
    that aligns with the animation concept and scene description.

    Args:
        hf_wrapper: HuggingFace inference wrapper instance
        arguments: Dictionary containing:
            - concept (str): The animation concept
            - scene_description (str): Description of the scene/animation
            - target_audience (str): Target audience level
            - duration_seconds (int, optional): Duration in seconds (default: 30)
            - model (str, optional): Hugging Face model to use

    Returns:
        CallToolResult with the narration script
    """
    concept = arguments["concept"]
    scene_description = arguments["scene_description"]
    target_audience = arguments["target_audience"]
    duration = arguments.get("duration_seconds", 30)
    model = arguments.get("model")

    try:
        model_config = ModelConfig()
        selected_model = model or model_config.text_models[0]

        prompt = f"""
Generate a narration script for an educational animation:

Concept: {concept}
Scene: {scene_description}
Target Audience: {target_audience}
Duration: {duration} seconds

Requirements:
1. Clear, engaging, and age-appropriate language
2. Educational value aligned with learning objectives
3. Natural speaking pace (approximately {duration / 150} words for {duration} seconds)
4. Include pauses and emphasis markers where appropriate
5. Make it interesting and memorable

Format as a clean script ready for text-to-speech.
"""

        response = await hf_wrapper.text_generation(
            model=selected_model,
            prompt=prompt,
            max_new_tokens=512,
            temperature=0.6,
        )

        logger.info(f"Successfully generated narration for concept: {concept}")

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Narration Script:\n\n{response}",
                )
            ]
        )

    except Exception as e:
        logger.error(f"Narration generation failed: {str(e)}")
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Narration generation failed: {str(e)}",
                )
            ],
            isError=True,
        )


async def generate_speech(
    hf_wrapper: HFInferenceWrapper, arguments: Dict[str, Any]
) -> CallToolResult:
    """
    Convert text to speech audio file.

    Uses a TTS model to generate speech audio from text and saves it to a file.

    Args:
        hf_wrapper: HuggingFace inference wrapper instance
        arguments: Dictionary containing:
            - text (str): Text to convert to speech
            - output_path (str): Path where to save the audio file
            - voice (str, optional): Voice to use for TTS
            - model (str, optional): Hugging Face TTS model to use

    Returns:
        CallToolResult with audio generation info
    """
    text = arguments["text"]
    output_path = arguments["output_path"]
    voice = arguments.get("voice")
    model = arguments.get("model")

    try:
        model_config = ModelConfig()
        selected_model = model or model_config.tts_models[0]

        # Generate audio
        audio_bytes = await hf_wrapper.text_to_speech(
            model=selected_model,
            text=text,
            voice=voice,
        )

        # Save to file
        success = await hf_wrapper.save_audio_to_file(audio_bytes, output_path)

        if not success:
            raise Exception("Failed to save audio file")

        # Return audio info
        audio_info = {
            "output_path": output_path,
            "text_length": len(text),
            "estimated_duration": len(text) / 150,  # Rough estimate
            "model_used": selected_model,
        }

        logger.info(f"Successfully generated speech audio at: {output_path}")

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Speech generated successfully!\n\n{json.dumps(audio_info, indent=2)}",
                )
            ]
        )

    except Exception as e:
        logger.error(f"Speech generation failed: {str(e)}")
        return CallToolResult(
            content=[
                TextContent(type="text", text=f"Speech generation failed: {str(e)}")
            ],
            isError=True,
        )
