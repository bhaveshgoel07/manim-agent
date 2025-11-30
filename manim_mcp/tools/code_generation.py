"""
Code Generation Tools for Manim MCP Server

This module provides tools for generating and refining Manim animation code.
"""

import logging
from typing import Any, Dict, Optional

from mcp.types import CallToolResult, TextContent

from utils.hf_wrapper import HFInferenceWrapper, ModelConfig

logger = logging.getLogger(__name__)


async def generate_manim_code(
    hf_wrapper: HFInferenceWrapper, arguments: Dict[str, Any]
) -> CallToolResult:
    """
    Generate Manim Python code for an animation concept.

    Uses a code LLM to generate complete, runnable Manim code based on:
    - A concept description
    - Scene details
    - Desired visual elements
    - Optional error feedback for retries

    Args:
        hf_wrapper: HuggingFace inference wrapper instance
        arguments: Dictionary containing:
            - concept (str): The animation concept
            - scene_description (str): Detailed scene description
            - visual_elements (list, optional): List of visual elements to include
            - model (str, optional): Hugging Face model to use
            - previous_code (str, optional): Previous code attempt (for retries)
            - error_message (str, optional): Error from previous attempt (for retries)

    Returns:
        CallToolResult with the generated Manim code
    """
    concept = arguments["concept"]
    scene_description = arguments["scene_description"]
    visual_elements = arguments.get("visual_elements", [])
    model = arguments.get("model")
    previous_code = arguments.get("previous_code")
    error_message = arguments.get("error_message")

    try:
        model_config = ModelConfig()
        selected_model = model or model_config.code_models[0]

        # Build prompt based on whether this is a retry
        if previous_code and error_message:
            prompt = f"""
You are an expert animation engineer using Manim Community Edition (v0.18.0+).

The previous code attempt had an error. Your task is to FIX the code.

PREVIOUS CODE:
```python
{previous_code}
```

ERROR ENCOUNTERED:
{error_message}

TASK: Fix the error in the code above. Pay special attention to:
- Closing all parentheses, brackets, and braces
- Completing all function calls
- Proper indentation
- Valid Python syntax

Concept: {concept}
Scene Description: {scene_description}
Visual Elements: {", ".join(visual_elements)}

STRICT CODE REQUIREMENTS:
1. Header: MUST start with `from manim import *`
2. Class Structure: Define a class inheriting from `MovingCameraScene` (use this instead of `Scene` to enable camera zoom/pan with `self.camera.frame`)
3. Method: All logic must be inside the `def construct(self):` method
4. SYNTAX: Ensure ALL parentheses, brackets, and function calls are properly closed
5. Colors: Use ONLY valid Manim colors (WHITE, BLACK, RED, GREEN, BLUE, YELLOW, ORANGE, PINK, PURPLE, TEAL, GOLD, etc.)
6. Text: Use `Text()` objects for strings
7. Positioning: Use `.next_to()`, `.move_to()`, or `.shift()`
8. Animations: Use Write(), Create(), FadeIn(), FadeOut(), Transform(), Flash(), Indicate() - capitalize properly!
9. Pacing: Include `self.wait(1)` between animations

OUTPUT FORMAT:
Provide ONLY the complete, corrected Python code. No markdown blocks. No explanations.
"""
        else:
            prompt = f"""
You are an expert animation engineer using Manim Community Edition (v0.18.0+).
Generate a complete, runnable Python script for the following request.

Concept: {concept}
Scene Description: {scene_description}
Visual Elements: {", ".join(visual_elements)}

STRICT CODE REQUIREMENTS:
1. Header: MUST start with `from manim import *`
2. Class Structure: Define a class inheriting from `MovingCameraScene` (e.g., `class GenScene(MovingCameraScene):`) - this enables camera operations like zoom/pan via `self.camera.frame`
3. Method: All logic must be inside the `def construct(self):` method
4. SYNTAX: Ensure ALL parentheses, brackets, and function calls are properly closed
5. Colors: Use ONLY these valid Manim color constants:
   - Basic: WHITE, BLACK, GRAY, GREY, LIGHT_GRAY, DARK_GRAY
   - Primary: RED, GREEN, BLUE, YELLOW, ORANGE, PINK, PURPLE, TEAL, GOLD, MAROON
   - Variants: RED_A, RED_B, RED_C, RED_D, RED_E, GREEN_A, GREEN_B, GREEN_C, GREEN_D, GREEN_E,
     BLUE_A, BLUE_B, BLUE_C, BLUE_D, BLUE_E, YELLOW_A, YELLOW_B, YELLOW_C, YELLOW_D, YELLOW_E
   - NEVER use: DARK_GREEN, LIGHT_GREEN, DARK_BLUE, LIGHT_BLUE, DARK_RED, LIGHT_RED (these don't exist!)
6. Text: Use `Text()` objects for strings. Avoid `Tex()` or `MathTex()` unless necessary
7. Positioning: Use `.next_to()`, `.move_to()`, or `.shift()` to arrange elements
8. Animations: Use ONLY these valid animations:
   - Write(), Create(), FadeIn(), FadeOut(), GrowFromCenter(), ShrinkToCenter()
   - Transform(), ReplacementTransform(), MoveToTarget(), ApplyMethod()
   - Rotate(), Indicate(), Flash(), ShowCreation() - DO NOT use lowercase like 'flash'
   - For custom effects use .animate.method() (e.g., obj.animate.scale(2), obj.animate.shift(UP))
9. Pacing: Include `self.wait(1)` between major animation groups

OUTPUT FORMAT:
Provide ONLY the raw Python code. Do not wrap in markdown blocks (no ```python). Do not include conversational text.
"""

        response = await hf_wrapper.text_generation(
            model=selected_model,
            prompt=prompt,
            max_new_tokens=2048,
            temperature=0.3,
        )

        logger.info(f"Successfully generated Manim code for concept: {concept}")

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Generated Manim Code:\n\n```python\n{response}\n```",
                )
            ]
        )

    except Exception as e:
        logger.error(f"Code generation failed: {str(e)}")
        return CallToolResult(
            content=[
                TextContent(type="text", text=f"Code generation failed: {str(e)}")
            ],
            isError=True,
        )


async def refine_animation(
    hf_wrapper: HFInferenceWrapper, arguments: Dict[str, Any]
) -> CallToolResult:
    """
    Refine animation code based on feedback.

    Uses a code LLM to improve existing Manim code based on:
    - User feedback or error messages
    - Specific improvement goals
    - Visual or educational quality issues

    Args:
        hf_wrapper: HuggingFace inference wrapper instance
        arguments: Dictionary containing:
            - original_code (str): The original Manim code to refine
            - feedback (str): Feedback or error message about the code
            - improvement_goals (list, optional): List of specific improvement goals
            - model (str, optional): Hugging Face model to use

    Returns:
        CallToolResult with the refined Manim code
    """
    original_code = arguments["original_code"]
    feedback = arguments["feedback"]
    improvement_goals = arguments.get("improvement_goals", [])
    model = arguments.get("model")

    try:
        model_config = ModelConfig()
        selected_model = model or model_config.code_models[0]

        prompt = f"""
You are a Manim Code Repair Agent. Your task is to rewrite the FULL Python script to fix issues or apply improvements.

Previous Code:
{original_code}

User Feedback/Error:
{feedback}

Improvement Goals:
{", ".join(improvement_goals)}

INSTRUCTIONS:
1. Output the COMPLETE corrected script, including `from manim import *`.
2. Do not output diffs or partial snippets.
3. Ensure the class inherits from `MovingCameraScene` and uses `def construct(self):`.
4. Fix logic errors based on the feedback.
5. Animations: Use ONLY valid animations like Write(), FadeIn(), FadeOut(), Create(), Flash(), Transform() - NEVER lowercase!
6. Colors: Use ONLY these valid Manim color constants:
   - Basic: WHITE, BLACK, GRAY, GREY, LIGHT_GRAY, DARK_GRAY
   - Primary: RED, GREEN, BLUE, YELLOW, ORANGE, PINK, PURPLE, TEAL, GOLD, MAROON
   - Variants: RED_A, RED_B, RED_C, RED_D, RED_E, GREEN_A, GREEN_B, GREEN_C, GREEN_D, GREEN_E,
     BLUE_A, BLUE_B, BLUE_C, BLUE_D, BLUE_E, YELLOW_A, YELLOW_B, YELLOW_C, YELLOW_D, YELLOW_E
   - NEVER use: DARK_GREEN, LIGHT_GREEN, DARK_BLUE, LIGHT_BLUE, DARK_RED, LIGHT_RED (these don't exist!)
   - For darker/lighter variants, use the letter suffixes (e.g., GREEN_E for dark green, GREEN_A for light green).

OUTPUT:
Return ONLY the raw Python code. No markdown backticks. No explanation.
"""

        response = await hf_wrapper.text_generation(
            model=selected_model,
            prompt=prompt,
            max_new_tokens=2048,
            temperature=0.3,
        )

        logger.info("Successfully refined animation code")

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Refined Manim Code:\n\n```python\n{response}\n```",
                )
            ]
        )

    except Exception as e:
        logger.error(f"Code refinement failed: {str(e)}")
        return CallToolResult(
            content=[
                TextContent(type="text", text=f"Code refinement failed: {str(e)}")
            ],
            isError=True,
        )
