"""
Creative MCP Server

This MCP server provides tools for creative tasks using Hugging Face models:
- Concept Planning (Text LLM)
- Code Generation (Coder LLM)
- Vision Analysis (Vision-Language LLM)
- Text-to-Speech (Audio model)
"""

import asyncio
import base64
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root (which contains the `utils` package) is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)

from utils.hf_wrapper import HFInferenceWrapper, ModelConfig, get_hf_wrapper

logger = logging.getLogger(__name__)

# Create MCP server
server = Server("neuroanim-creative")

# Global HF wrapper instance
hf_wrapper: Optional[HFInferenceWrapper] = None


class CreativeTool:
    """Base class for creative tools."""

    @staticmethod
    def get_hf_wrapper() -> HFInferenceWrapper:
        """Get or create the HF wrapper instance."""
        global hf_wrapper
        if hf_wrapper is None:
            api_key = os.getenv("HUGGINGFACE_API_KEY")
            hf_wrapper = get_hf_wrapper(api_key=api_key)
        return hf_wrapper


@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List available creative tools."""
    tools = [
        Tool(
            name="plan_concept",
            description="Plan a STEM concept for animation using text LLM",
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
                        "description": "Desired animation length in minutes",
                    },
                    "model": {
                        "type": "string",
                        "description": "Hugging Face model to use (optional, will use default if not provided)",
                    },
                },
                "required": ["topic", "target_audience"],
            },
        ),
        Tool(
            name="generate_manim_code",
            description="Generate Manim Python code for an animation concept",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": "The animation concept description",
                    },
                    "scene_description": {
                        "type": "string",
                        "description": "Detailed description of what should happen in the scene",
                    },
                    "visual_elements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of visual elements to include",
                    },
                    "model": {
                        "type": "string",
                        "description": "Code model to use (optional, will use default if not provided)",
                    },
                },
                "required": ["concept", "scene_description"],
            },
        ),
        Tool(
            name="analyze_frame",
            description="Analyze an animation frame using vision model for quality assessment",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image file to analyze",
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": [
                            "quality",
                            "content",
                            "educational_value",
                            "clarity",
                        ],
                        "description": "Type of analysis to perform",
                    },
                    "context": {
                        "type": "string",
                        "description": "Context about what should be in the image",
                    },
                    "model": {
                        "type": "string",
                        "description": "Vision model to use (optional, will use default if not provided)",
                    },
                },
                "required": ["image_path", "analysis_type"],
            },
        ),
        Tool(
            name="generate_narration",
            description="Generate narration script for an animation",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": "The animation concept",
                    },
                    "scene_description": {
                        "type": "string",
                        "description": "Description of the scene to narrate",
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
                        "description": "Target audience",
                    },
                    "duration_seconds": {
                        "type": "number",
                        "description": "Desired narration duration in seconds",
                    },
                    "model": {
                        "type": "string",
                        "description": "Text model to use (optional, will use default if not provided)",
                    },
                },
                "required": ["concept", "scene_description", "target_audience"],
            },
        ),
        Tool(
            name="generate_speech",
            description="Convert text narration to speech audio",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to convert to speech",
                    },
                    "voice": {
                        "type": "string",
                        "description": "Voice preference (optional)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save the audio file",
                    },
                    "model": {
                        "type": "string",
                        "description": "TTS model to use (optional, will use default if not provided)",
                    },
                },
                "required": ["text", "output_path"],
            },
        ),
        Tool(
            name="refine_animation",
            description="Refine and improve animation based on feedback",
            inputSchema={
                "type": "object",
                "properties": {
                    "original_code": {
                        "type": "string",
                        "description": "Original Manim code",
                    },
                    "feedback": {
                        "type": "string",
                        "description": "Feedback or issues to address",
                    },
                    "improvement_goals": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of improvement goals",
                    },
                    "model": {
                        "type": "string",
                        "description": "Code model to use (optional, will use default if not provided)",
                    },
                },
                "required": ["original_code", "feedback"],
            },
        ),
        Tool(
            name="generate_quiz",
            description="Generate quiz questions based on animation content",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": "The STEM concept covered in the animation",
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard"],
                        "description": "Quiz difficulty level",
                    },
                    "num_questions": {
                        "type": "number",
                        "description": "Number of questions to generate",
                    },
                    "question_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["multiple_choice", "true_false", "short_answer"],
                        },
                        "description": "Types of questions to include",
                    },
                    "model": {
                        "type": "string",
                        "description": "Text model to use (optional, will use default if not provided)",
                    },
                },
                "required": ["concept", "difficulty", "num_questions"],
            },
        ),
    ]

    return ListToolsResult(tools=tools)


@server.call_tool()
async def call_tool(tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Dispatch creative tool calls.

    The low-level MCP server passes `(tool_name, arguments)` into this
    handler, so we accept two positional arguments rather than a
    `CallToolRequest` instance.
    """

    try:
        if tool_name == "plan_concept":
            return await plan_concept(arguments)
        elif tool_name == "generate_manim_code":
            return await generate_manim_code(arguments)
        elif tool_name == "analyze_frame":
            return await analyze_frame(arguments)
        elif tool_name == "generate_narration":
            return await generate_narration(arguments)
        elif tool_name == "generate_speech":
            return await generate_speech(arguments)
        elif tool_name == "refine_animation":
            return await refine_animation(arguments)
        elif tool_name == "generate_quiz":
            return await generate_quiz(arguments)
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


async def plan_concept(arguments: Dict[str, Any]) -> CallToolResult:
    """Plan a STEM concept for animation."""
    topic = arguments["topic"]
    target_audience = arguments["target_audience"]
    animation_length = arguments.get("animation_length_minutes", 2.0)
    model = arguments.get("model")

    try:
        wrapper = CreativeTool.get_hf_wrapper()
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

        response = await wrapper.text_generation(
            model=selected_model,
            prompt=prompt,
            max_new_tokens=1024,
            temperature=0.7,
        )

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Animation Concept Plan:\n\n{response}",
                )
            ]
        )

    except Exception as e:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Concept planning failed: {str(e)}",
                )
            ],
            isError=True,
        )


async def generate_manim_code(arguments: Dict[str, Any]) -> CallToolResult:
    """Generate Manim Python code."""
    concept = arguments["concept"]
    scene_description = arguments["scene_description"]
    visual_elements = arguments.get("visual_elements", [])
    model = arguments.get("model")
    previous_code = arguments.get("previous_code")
    error_message = arguments.get("error_message")

    try:
        wrapper = CreativeTool.get_hf_wrapper()
        model_config = ModelConfig()
        selected_model = model or model_config.code_models[0]

        # Build base prompt
        if previous_code and error_message:
            # This is a retry - include error feedback
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
            # First attempt - generate fresh code
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

        response = await wrapper.text_generation(
            model=selected_model,
            prompt=prompt,
            max_new_tokens=2048,
            temperature=0.3,
        )

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Generated Manim Code:\n\n```python\n{response}\n```",
                )
            ]
        )

    except Exception as e:
        return CallToolResult(
            content=[
                TextContent(type="text", text=f"Code generation failed: {str(e)}")
            ],
            isError=True,
        )


async def analyze_frame(arguments: Dict[str, Any]) -> CallToolResult:
    """Analyze an animation frame."""
    image_path = arguments["image_path"]
    analysis_type = arguments["analysis_type"]
    context = arguments.get("context", "")
    model = arguments.get("model")

    try:
        wrapper = CreativeTool.get_hf_wrapper()
        model_config = ModelConfig()
        selected_model = model or model_config.vision_models[0]

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        prompt = f"""
        Analyze this {analysis_type} for an educational animation frame.
        Context: {context}

        Provide specific feedback on:
        {analysis_type.replace("_", " ").title()} assessment
        Educational effectiveness
        Visual clarity
        Suggestions for improvement
        """

        response = await wrapper.vision_analysis(
            model=selected_model,
            image=image_bytes,
            text=prompt,
        )

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Frame Analysis ({analysis_type}):\n\n{response}",
                )
            ]
        )

    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Frame analysis failed: {str(e)}")],
            isError=True,
        )


async def generate_narration(arguments: Dict[str, Any]) -> CallToolResult:
    """Generate narration script."""
    concept = arguments["concept"]
    scene_description = arguments["scene_description"]
    target_audience = arguments["target_audience"]
    duration = arguments.get("duration_seconds", 30)
    model = arguments.get("model")

    try:
        wrapper = CreativeTool.get_hf_wrapper()
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

        response = await wrapper.text_generation(
            model=selected_model,
            prompt=prompt,
            max_new_tokens=512,
            temperature=0.6,
        )

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Narration Script:\n\n{response}",
                )
            ]
        )

    except Exception as e:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Narration generation failed: {str(e)}",
                )
            ],
            isError=True,
        )


async def generate_speech(arguments: Dict[str, Any]) -> CallToolResult:
    """Convert text to speech."""
    text = arguments["text"]
    voice = arguments.get("voice")
    output_path = arguments["output_path"]
    model = arguments.get("model")

    try:
        wrapper = CreativeTool.get_hf_wrapper()
        model_config = ModelConfig()
        selected_model = model or model_config.tts_models[0]

        # Generate audio
        audio_bytes = await wrapper.text_to_speech(
            model=selected_model,
            text=text,
            voice=voice,
        )

        # Save to file
        success = await wrapper.save_audio_to_file(audio_bytes, output_path)

        if not success:
            raise Exception("Failed to save audio file")

        # Return audio info
        audio_info = {
            "output_path": output_path,
            "text_length": len(text),
            "estimated_duration": len(text) / 150,  # Rough estimate
            "model_used": selected_model,
        }

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Speech generated successfully!\n\n{json.dumps(audio_info, indent=2)}",
                )
            ]
        )

    except Exception as e:
        return CallToolResult(
            content=[
                TextContent(type="text", text=f"Speech generation failed: {str(e)}")
            ],
            isError=True,
        )


async def refine_animation(arguments: Dict[str, Any]) -> CallToolResult:
    """Refine animation code based on feedback."""
    original_code = arguments["original_code"]
    feedback = arguments["feedback"]
    improvement_goals = arguments.get("improvement_goals", [])
    model = arguments.get("model")

    try:
        wrapper = CreativeTool.get_hf_wrapper()
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

        response = await wrapper.text_generation(
            model=selected_model,
            prompt=prompt,
            max_new_tokens=2048,
            temperature=0.3,
        )

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Refined Manim Code:\n\n```python\n{response}\n```",
                )
            ]
        )

    except Exception as e:
        return CallToolResult(
            content=[
                TextContent(type="text", text=f"Code refinement failed: {str(e)}")
            ],
            isError=True,
        )


async def generate_quiz(arguments: Dict[str, Any]) -> CallToolResult:
    """Generate quiz questions."""
    concept = arguments["concept"]
    difficulty = arguments["difficulty"]
    num_questions = arguments["num_questions"]
    question_types = arguments.get("question_types", ["multiple_choice"])
    model = arguments.get("model")

    try:
        wrapper = CreativeTool.get_hf_wrapper()
        model_config = ModelConfig()
        selected_model = model or model_config.text_models[0]

        prompt = f"""
        Generate {num_questions} quiz questions for the following STEM concept:

        Concept: {concept}
        Difficulty: {difficulty}
        Question Types: {", ".join(question_types)}

        For each question provide:
        1. The question
        2. Possible answers (for multiple choice)
        3. Correct answer
        4. Brief explanation

        Format as JSON array of question objects.
        """

        response = await wrapper.text_generation(
            model=selected_model,
            prompt=prompt,
            max_new_tokens=1024,
            temperature=0.5,
        )

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Generated Quiz Questions:\n\n{response}",
                )
            ]
        )

    except Exception as e:
        return CallToolResult(
            content=[
                TextContent(type="text", text=f"Quiz generation failed: {str(e)}")
            ],
            isError=True,
        )


async def main():
    """Main entry point for the creative MCP server."""
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
                server_name="neuroanim-creative",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
