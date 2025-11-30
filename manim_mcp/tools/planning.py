"""
Planning Tools for Manim MCP Server

This module provides tools for concept planning and ideation for STEM animations.
"""

import json
import logging
from typing import Any, Dict, Optional

from mcp.types import CallToolResult, TextContent

from utils.hf_wrapper import HFInferenceWrapper, ModelConfig

logger = logging.getLogger(__name__)


async def plan_concept(
    hf_wrapper: HFInferenceWrapper, arguments: Dict[str, Any]
) -> CallToolResult:
    """
    Plan a STEM concept for animation.

    Uses a text LLM to create a structured animation plan including:
    - Learning objectives
    - Visual metaphors
    - Scene flow with timestamps
    - Educational value assessment

    Args:
        hf_wrapper: HuggingFace inference wrapper instance
        arguments: Dictionary containing:
            - topic (str): The STEM topic to create an animation for
            - target_audience (str): Target audience level (elementary, middle_school, high_school, college, general)
            - animation_length_minutes (float, optional): Desired animation length in minutes
            - model (str, optional): Hugging Face model to use

    Returns:
        CallToolResult with the structured animation plan
    """
    topic = arguments["topic"]
    target_audience = arguments["target_audience"]
    animation_length = arguments.get("animation_length_minutes", 2.0)
    model = arguments.get("model")

    try:
        model_config = ModelConfig()
        selected_model = model or model_config.text_models[0]

        prompt = f"""
You are a STEM Curriculum Designer. Create a structured animation plan.

Topic: {topic}
Audience: {target_audience}
Length: {animation_length} min

Return a valid JSON object with exactly these keys:
{{
    "learning_objectives": ["string", "string"],
    "visual_metaphors": ["string", "string"],
    "scene_flow": [
        {{
            "timestamp": "0:00-0:30",
            "action": "description of visual action",
            "voiceover": "key narration points"
        }}
    ],
    "estimated_educational_value": "string"
}}

Do not include markdown formatting like ```json. Return raw JSON only.
"""

        response = await hf_wrapper.text_generation(
            model=selected_model,
            prompt=prompt,
            max_new_tokens=1024,
            temperature=0.7,
        )

        logger.info(f"Successfully planned concept for topic: {topic}")

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Animation Concept Plan:\n\n{response}",
                )
            ]
        )

    except Exception as e:
        logger.error(f"Concept planning failed: {str(e)}")
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Concept planning failed: {str(e)}",
                )
            ],
            isError=True,
        )
