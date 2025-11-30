"""
Hugging Face Inference API Wrapper

This module provides a robust wrapper around the Hugging Face Inference API
with rate limiting, error handling, and support for various model types.
"""

import asyncio
import base64
import io
import logging
import time
from typing import Any, BinaryIO, Dict, List, Optional, Union

import aiohttp
from huggingface_hub import AsyncInferenceClient, InferenceClient
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, max_calls: int = 60, time_window: int = 60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []

    async def acquire(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()
        # Remove calls outside the time window
        self.calls = [
            call_time for call_time in self.calls if now - call_time < self.time_window
        ]

        if len(self.calls) >= self.max_calls:
            # Calculate wait time
            oldest_call = min(self.calls)
            wait_time = self.time_window - (now - oldest_call)
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)

        self.calls.append(now)


class HFInferenceWrapper:
    """
    Wrapper for Hugging Face Inference API with rate limiting and error handling.
    """

    def __init__(self, api_key: Optional[str] = None, max_calls_per_minute: int = 60):
        self.client = AsyncInferenceClient(token=api_key)
        self.rate_limiter = RateLimiter(max_calls=max_calls_per_minute, time_window=60)

    async def text_generation(
        self,
        model: str,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Generate text using a language model.

        Notes:
        - Uses AsyncInferenceClient by default.
        - Works around a known issue where `AsyncInferenceClient.text_generation`
          may raise `StopIteration` ("coroutine raised StopIteration") by
          falling back to the synchronous `InferenceClient` inside a thread.
        - Automatically detects if a model supports conversational tasks and
          uses chat_completion instead of text_generation.
        - Always normalizes the result to a plain string, extracting
          `generated_text` when the client returns a `TextGenerationOutput`
          object.
        """
        await self.rate_limiter.acquire()

        try:
            # Check if this is a conversational model that doesn't support text_generation
            if self._is_conversational_model(model):
                logger.info(f"Using chat_completion for conversational model: {model}")
                return await self._chat_completion_fallback(
                    model, prompt, max_new_tokens, temperature, **kwargs
                )

            # Primary path: async client with text_generation
            response = await self.client.text_generation(
                prompt=prompt,
                model=model,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                **kwargs,
            )
        except Exception as e:
            # Check if this is a model capability issue
            if "not supported for task text-generation" in str(e):
                logger.info(f"Falling back to chat_completion for model: {model}")
                return await self._chat_completion_fallback(
                    model, prompt, max_new_tokens, temperature, **kwargs
                )

            # Newer versions of `huggingface_hub` sometimes surface a
            # `RuntimeError` with message "coroutine raised StopIteration" from
            # the async client. Detect that pattern (or a raw StopIteration)
            # and fall back to the sync client in a background thread.
            is_stop_iteration_like = isinstance(
                e, StopIteration
            ) or "StopIteration" in str(e)

            if is_stop_iteration_like:  # pragma: no cover - defensive against HF bug
                logger.warning(
                    "Async text_generation raised/contained StopIteration for "
                    "model %s; falling back to sync InferenceClient: %s",
                    model,
                    e,
                )

                def _call_sync() -> str:
                    """Synchronous text-generation call for asyncio.to_thread."""
                    sync_client = InferenceClient(token=self.client.token)
                    # Check if this is a conversational model
                    if self._is_conversational_model(model):
                        messages = [{"role": "user", "content": prompt}]
                        chat_response = sync_client.chat.completions.create(
                            model=model,
                            messages=messages,
                            max_tokens=max_new_tokens,
                            temperature=temperature,
                            **kwargs,
                        )
                        return chat_response.choices[0].message.content
                    else:
                        return sync_client.text_generation(
                            prompt=prompt,
                            model=model,
                            max_new_tokens=max_new_tokens,
                            temperature=temperature,
                            **kwargs,
                        )

                response = await asyncio.to_thread(_call_sync)
            else:
                logger.error(f"Text generation failed with model {model}: {e}")
                raise

        # Normalize various possible return types to a plain string
        try:
            from huggingface_hub.inference._generated.types.text_generation import (
                TextGenerationOutput,
            )
        except Exception:  # pragma: no cover - type import fallback
            TextGenerationOutput = None  # type: ignore

        if TextGenerationOutput is not None and isinstance(
            response, TextGenerationOutput
        ):
            return response.generated_text

        if isinstance(response, str):
            return response

        # Fallback: best-effort stringification
        return str(response)

    def _is_conversational_model(self, model: str) -> bool:
        """Check if a model is primarily conversational (doesn't support text_generation)."""
        conversational_models = [
            "zai-org/GLM-4.6",
            # Add other known conversational-only models here
        ]
        return model in conversational_models

    async def _chat_completion_fallback(
        self,
        model: str,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Fallback method using chat.completions for conversational models."""
        messages = [{"role": "user", "content": prompt}]

        try:
            # Try async first
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_new_tokens,
                temperature=temperature,
                **kwargs,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Async chat_completion failed, falling back to sync: {e}")

            # Fall back to sync if async fails
            def _sync_chat_completion():
                sync_client = InferenceClient(token=self.client.token)
                response = sync_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_new_tokens,
                    temperature=temperature,
                    **kwargs,
                )
                return response.choices[0].message.content

            return await asyncio.to_thread(_sync_chat_completion)

    async def conversation(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Generate response in a conversation format."""
        await self.rate_limiter.acquire()

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Conversation failed with model {model}: {e}")
            raise

    async def image_generation(
        self,
        model: str,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        **kwargs,
    ) -> bytes:
        """Generate an image and return as bytes."""
        await self.rate_limiter.acquire()

        try:
            image_bytes = await self.client.text_to_image(
                model=model,
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                **kwargs,
            )
            return image_bytes
        except Exception as e:
            logger.error(f"Image generation failed with model {model}: {e}")
            raise

    async def text_to_speech(
        self, model: str, text: str, voice: Optional[str] = None, **kwargs
    ) -> bytes:
        """Convert text to speech and return audio bytes.

        Note: The voice parameter is kept for backwards compatibility but is not used
        as the HuggingFace API doesn't support it.
        """
        await self.rate_limiter.acquire()

        try:
            # HuggingFace text_to_speech API: text as first arg, model as kwarg
            audio_bytes = await self.client.text_to_speech(text, model=model)
            return audio_bytes
        except Exception as e:
            logger.error(f"TTS failed with model {model}: {e}")
            raise

    async def vision_analysis(
        self, model: str, image: Union[bytes, BinaryIO], text: str, **kwargs
    ) -> str:
        """Analyze an image with a vision model."""
        await self.rate_limiter.acquire()

        try:
            response = await self.client.image_to_text(
                model=model, image=image, text=text, **kwargs
            )
            return response
        except Exception as e:
            logger.error(f"Vision analysis failed with model {model}: {e}")
            raise

    async def save_audio_to_file(self, audio_bytes: bytes, output_path: str) -> bool:
        """Save audio bytes to a file."""
        try:
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            logger.info(f"Audio saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save audio to {output_path}: {e}")
            return False

    def audio_bytes_to_base64(self, audio_bytes: bytes) -> str:
        """Convert audio bytes to base64 string for transmission."""
        return base64.b64encode(audio_bytes).decode("utf-8")

    def base64_to_audio_bytes(self, base64_str: str) -> bytes:
        """Convert base64 string back to audio bytes."""
        return base64.b64decode(base64_str.encode("utf-8"))


class ModelConfig(BaseModel):
    """Configuration for different model types."""

    text_models: List[str] = Field(
        default_factory=lambda: [
            # Primary general/text models
            "zai-org/GLM-4.6",
            "mistralai/Mistral-Nemo-Instruct-2407",
            "Qwen/Qwen2.5-7B-Instruct",
            "meta-llama/Llama-3.1-8B-Instruct",
        ]
    )

    code_models: List[str] = Field(
        default_factory=lambda: [
            # Primary code-capable models
            "zai-org/GLM-4.6",
            "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
            "meta-llama/CodeLlama-70b-Instruct-hf",
            # Kept last because it has caused auth issues in practice
            "ZhipuAI/glm-4-9b-chat",
        ]
    )

    vision_models: List[str] = Field(
        default_factory=lambda: [
            "llava-hf/llava-v1.6-mistral-7b-hf",
            "Salesforce/blip2-flan-t5-xxl",
            "google/paligemma-3b-mix-448",
        ]
    )

    tts_models: List[str] = Field(
        default_factory=lambda: [
            "ResembleAI/chatterbox",
            "suno/bark",
            "facebook/mms-tts-all",
        ]
    )

    image_models: List[str] = Field(
        default_factory=lambda: [
            "stabilityai/stable-diffusion-3-medium",
            "black-forest-labs/FLUX.1-dev",
            "prompthero/openjourney",
        ]
    )


# Global instance factory
def get_hf_wrapper(api_key: Optional[str] = None) -> HFInferenceWrapper:
    """Get a configured HFInferenceWrapper instance."""
    return HFInferenceWrapper(api_key=api_key)
