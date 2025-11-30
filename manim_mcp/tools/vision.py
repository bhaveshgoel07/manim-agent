"""
Vision Tools for Manim MCP Server

This module provides tools for analyzing animation frames using vision models.
"""

import logging
from typing import Any, Dict, Optional

from mcp.types import CallToolResult, TextContent

from utils.hf_wrapper import HFInferenceWrapper, ModelConfig

logger = logging.getLogger(__name__)


async def analyze_frame(
    hf_wrapper: HFInferenceWrapper, arguments: Dict[str, Any]
) -> CallToolResult:
    """
    Analyze an animation frame using vision-language models.

    Uses a vision model to provide feedback on:
    - Visual clarity and composition
    - Educational effectiveness
    - Technical quality
    - Suggestions for improvement

    Args:
        hf_wrapper: HuggingFace inference wrapper instance
        arguments: Dictionary containing:
            - image_path (str): Path to the image file to analyze
            - analysis_type (str): Type of analysis (e.g., "quality", "educational_value", "clarity")
            - context (str, optional): Additional context about the animation
            - model (str, optional): Hugging Face vision model to use

    Returns:
        CallToolResult with the frame analysis feedback
    """
    image_path = arguments["image_path"]
    analysis_type = arguments["analysis_type"]
    context = arguments.get("context", "")
    model = arguments.get("model")

    try:
        model_config = ModelConfig()
        selected_model = model or model_config.vision_models[0]

        # Read the image file
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # Build analysis prompt
        prompt = f"""
Analyze this {analysis_type} for an educational animation frame.
Context: {context}

Provide specific feedback on:
- {analysis_type.replace("_", " ").title()} assessment
- Educational effectiveness
- Visual clarity
- Suggestions for improvement
"""

        # Call vision model
        response = await hf_wrapper.vision_analysis(
            model=selected_model,
            image=image_bytes,
            text=prompt,
        )

        logger.info(f"Successfully analyzed frame: {image_path} ({analysis_type})")

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Frame Analysis ({analysis_type}):\n\n{response}",
                )
            ]
        )

    except Exception as e:
        logger.error(f"Frame analysis failed: {str(e)}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Frame analysis failed: {str(e)}")],
            isError=True,
        )
