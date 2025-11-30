"""
Quiz Tools for Manim MCP Server

This module provides tools for generating educational quiz questions based on STEM concepts.
"""

import logging
from typing import Any, Dict, Optional

from mcp.types import CallToolResult, TextContent

from utils.hf_wrapper import HFInferenceWrapper, ModelConfig

logger = logging.getLogger(__name__)


async def generate_quiz(
    hf_wrapper: HFInferenceWrapper, arguments: Dict[str, Any]
) -> CallToolResult:
    """
    Generate quiz questions for a STEM concept.

    Uses a text LLM to create educational quiz questions that assess
    understanding of the animation concept. Questions can be multiple choice,
    true/false, or short answer format.

    Args:
        hf_wrapper: HuggingFace inference wrapper instance
        arguments: Dictionary containing:
            - concept (str): The STEM concept to create quiz questions for
            - difficulty (str): Difficulty level (easy, medium, hard)
            - num_questions (int): Number of questions to generate
            - question_types (list, optional): Types of questions (default: ["multiple_choice"])
            - model (str, optional): Hugging Face model to use

    Returns:
        CallToolResult with the generated quiz questions in JSON format
    """
    concept = arguments["concept"]
    difficulty = arguments["difficulty"]
    num_questions = arguments["num_questions"]
    question_types = arguments.get("question_types", ["multiple_choice"])
    model = arguments.get("model")

    try:
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

Format as JSON array of question objects with this structure:
[
  {{
    "question": "question text",
    "options": ["A", "B", "C", "D"],
    "correct_answer": "A",
    "explanation": "why this is correct"
  }}
]

Return only valid JSON without markdown formatting.
"""

        response = await hf_wrapper.text_generation(
            model=selected_model,
            prompt=prompt,
            max_new_tokens=1024,
            temperature=0.5,
        )

        logger.info(
            f"Successfully generated {num_questions} quiz questions for concept: {concept}"
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
        logger.error(f"Quiz generation failed: {str(e)}")
        return CallToolResult(
            content=[
                TextContent(type="text", text=f"Quiz generation failed: {str(e)}")
            ],
            isError=True,
        )
