"""
Text-to-Speech (TTS) Utility Module

Supports multiple TTS providers:
- ElevenLabs (primary, high quality)
- Hugging Face (fallback)
- Google TTS (optional fallback)
"""

import asyncio
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

# Try to import ElevenLabs SDK
try:
    from elevenlabs.client import ElevenLabs

    ELEVENLABS_SDK_AVAILABLE = True
except ImportError:
    ELEVENLABS_SDK_AVAILABLE = False
    ElevenLabs = None

load_dotenv()

logger = logging.getLogger(__name__)


class TTSProvider(Enum):
    """Available TTS providers."""

    ELEVENLABS = "elevenlabs"
    HUGGINGFACE = "huggingface"
    GTTS = "gtts"


class TTSConfig:
    """Configuration for TTS generation."""

    # ElevenLabs voices
    ELEVENLABS_VOICES = {
        "rachel": "21m00Tcm4TlvDq8ikWAM",  # Clear, neutral female
        "adam": "pNInz6obpgDQGcFmaJgB",  # Deep, confident male
        "antoni": "ErXwobaYiN019PkySvjV",  # Well-rounded male
        "arnold": "VR6AewLTigWG4xSOukaG",  # Crisp, articulate male
        "bella": "EXAVITQu4vr4xnSDxMaL",  # Soft, gentle female
        "domi": "AZnzlk1XvdvUeBnXmlld",  # Strong female
        "elli": "MF3mGyEYCl7XYWbV9V6O",  # Emotional, expressive female
        "josh": "TxGEqnHWrfWFTfGW9XjX",  # Young, energetic male
        "sam": "yoZ06aMxZJJ28mfd3POQ",  # Raspy male
    }

    # Default settings
    ELEVENLABS_MODEL = "eleven_turbo_v2_5"
    ELEVENLABS_STABILITY = 0.5
    ELEVENLABS_SIMILARITY_BOOST = 0.75
    ELEVENLABS_STYLE = 0.0
    ELEVENLABS_USE_SPEAKER_BOOST = True

    # Hugging Face models
    HF_TTS_MODELS = [
        "facebook/mms-tts-eng",
        "microsoft/speecht5_tts",
        "suno/bark",
    ]

    # Timeouts
    ELEVENLABS_TIMEOUT = 60.0
    HF_TIMEOUT = 120.0


class TTSGenerator:
    """Main TTS generation class with multi-provider support."""

    def __init__(
        self,
        elevenlabs_api_key: Optional[str] = None,
        hf_api_key: Optional[str] = None,
        default_voice: str = "rachel",
        fallback_enabled: bool = True,
    ):
        """
        Initialize TTS generator.

        Args:
            elevenlabs_api_key: ElevenLabs API key
            hf_api_key: Hugging Face API key
            default_voice: Default voice to use
            fallback_enabled: Whether to fall back to other providers on failure
        """
        self.elevenlabs_api_key = elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")
        self.hf_api_key = hf_api_key or os.getenv("HUGGINGFACE_API_KEY")
        self.default_voice = default_voice
        self.fallback_enabled = fallback_enabled

    async def generate_speech(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        provider: Optional[TTSProvider] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate speech from text and save to file.

        Args:
            text: Text to convert to speech
            output_path: Path to save audio file
            voice: Voice ID or name
            provider: Specific provider to use (if None, auto-select)
            **kwargs: Provider-specific options

        Returns:
            Dict with generation info (provider, duration, etc.)
        """
        voice = voice or self.default_voice

        # Auto-select provider if not specified
        if provider is None:
            if self.elevenlabs_api_key:
                provider = TTSProvider.ELEVENLABS
            elif self.hf_api_key:
                provider = TTSProvider.HUGGINGFACE
            else:
                provider = TTSProvider.GTTS

        # Try primary provider
        try:
            logger.info(f"Generating speech with {provider.value}...")

            if provider == TTSProvider.ELEVENLABS:
                result = await self._generate_elevenlabs(
                    text, output_path, voice, **kwargs
                )
            elif provider == TTSProvider.HUGGINGFACE:
                result = await self._generate_huggingface(text, output_path, **kwargs)
            else:
                result = await self._generate_gtts(text, output_path, **kwargs)

            logger.info(f"Successfully generated speech with {provider.value}")
            return result

        except Exception as e:
            logger.error(f"{provider.value} TTS failed: {e}")

            # Try fallback if enabled
            if self.fallback_enabled:
                return await self._fallback_generation(
                    text, output_path, provider, voice, **kwargs
                )
            else:
                raise

    async def _fallback_generation(
        self,
        text: str,
        output_path: Path,
        failed_provider: TTSProvider,
        voice: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Try alternative providers as fallback."""
        logger.warning(f"Attempting fallback from {failed_provider.value}...")

        # Define fallback order
        if failed_provider == TTSProvider.ELEVENLABS:
            fallback_order = [TTSProvider.HUGGINGFACE, TTSProvider.GTTS]
        elif failed_provider == TTSProvider.HUGGINGFACE:
            fallback_order = [TTSProvider.GTTS]
        else:
            raise Exception("All TTS providers failed")

        for provider in fallback_order:
            try:
                logger.info(f"Trying fallback provider: {provider.value}")

                if provider == TTSProvider.HUGGINGFACE and self.hf_api_key:
                    return await self._generate_huggingface(text, output_path, **kwargs)
                elif provider == TTSProvider.GTTS:
                    return await self._generate_gtts(text, output_path, **kwargs)

            except Exception as e:
                logger.error(f"Fallback {provider.value} failed: {e}")
                continue

        raise Exception("All TTS providers failed")

    async def _generate_elevenlabs(
        self, text: str, output_path: Path, voice: str, **kwargs
    ) -> Dict[str, Any]:
        """Generate speech using ElevenLabs API."""
        if not self.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key not provided")

        if not ELEVENLABS_SDK_AVAILABLE:
            raise ImportError(
                "elevenlabs SDK not installed. Run: pip install elevenlabs"
            )

        # Get voice ID
        voice_id = TTSConfig.ELEVENLABS_VOICES.get(voice.lower(), voice)

        # Create client
        client = ElevenLabs(api_key=self.elevenlabs_api_key)

        # Generate audio using new SDK
        def _generate():
            return client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id=kwargs.get("model_id", TTSConfig.ELEVENLABS_MODEL),
                output_format="mp3_44100_128",
            )

        # Run in thread pool since SDK is synchronous
        loop = asyncio.get_event_loop()
        audio_generator = await loop.run_in_executor(None, _generate)

        # Save audio
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio_bytes = b"".join(audio_generator)

        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        # Get audio info
        file_size = len(audio_bytes)

        return {
            "provider": "elevenlabs",
            "voice": voice,
            "voice_id": voice_id,
            "output_path": str(output_path),
            "file_size_bytes": file_size,
            "text_length": len(text),
        }

    async def _generate_huggingface(
        self, text: str, output_path: Path, **kwargs
    ) -> Dict[str, Any]:
        """Generate speech using Hugging Face API."""
        if not self.hf_api_key:
            raise ValueError("Hugging Face API key not provided")

        # Import HF wrapper
        from utils.hf_wrapper import HuggingFaceWrapper

        wrapper = HuggingFaceWrapper(api_key=self.hf_api_key)
        model = kwargs.get("model", TTSConfig.HF_TTS_MODELS[0])

        # Generate speech
        result = await wrapper.text_to_speech(
            text=text, model=model, output_path=str(output_path)
        )

        return {
            "provider": "huggingface",
            "model": model,
            "output_path": str(output_path),
            "text_length": len(text),
        }

    async def _generate_gtts(
        self, text: str, output_path: Path, **kwargs
    ) -> Dict[str, Any]:
        """Generate speech using gTTS (Google Text-to-Speech) as last resort."""
        try:
            from gtts import gTTS
        except ImportError:
            raise ImportError("gTTS not installed. Run: pip install gtts")

        # Generate speech
        tts = gTTS(
            text=text, lang=kwargs.get("lang", "en"), slow=kwargs.get("slow", False)
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        tts.save(str(output_path))

        return {
            "provider": "gtts",
            "output_path": str(output_path),
            "text_length": len(text),
        }

    async def get_available_voices(
        self, provider: TTSProvider = TTSProvider.ELEVENLABS
    ) -> Dict[str, str]:
        """
        Get list of available voices for a provider.

        Args:
            provider: TTS provider

        Returns:
            Dict mapping voice names to IDs
        """
        if provider == TTSProvider.ELEVENLABS:
            if not self.elevenlabs_api_key:
                return TTSConfig.ELEVENLABS_VOICES

            # Fetch from API for custom voices
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        "https://api.elevenlabs.io/v1/voices",
                        headers={"xi-api-key": self.elevenlabs_api_key},
                    )
                    response.raise_for_status()
                    voices_data = response.json()

                    voices = {}
                    for voice in voices_data.get("voices", []):
                        voices[voice["name"].lower()] = voice["voice_id"]

                    return voices
            except Exception as e:
                logger.warning(f"Failed to fetch ElevenLabs voices: {e}")
                return TTSConfig.ELEVENLABS_VOICES

        return {}

    def validate_audio_file(self, audio_path: Path) -> Dict[str, Any]:
        """
        Validate that audio file was generated correctly.

        Args:
            audio_path: Path to audio file

        Returns:
            Dict with validation results
        """
        if not audio_path.exists():
            return {"valid": False, "error": "File does not exist"}

        file_size = audio_path.stat().st_size

        if file_size == 0:
            return {"valid": False, "error": "File is empty"}

        if file_size < 1000:  # Less than 1KB is suspicious
            return {
                "valid": False,
                "error": "File suspiciously small",
                "size": file_size,
            }

        # Try to check if it's valid audio (optional, requires pydub)
        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_file(str(audio_path))
            duration = len(audio) / 1000.0  # Convert to seconds

            if duration < 0.1:
                return {
                    "valid": False,
                    "error": "Audio duration too short",
                    "duration": duration,
                }

            return {
                "valid": True,
                "size": file_size,
                "duration": duration,
                "format": audio_path.suffix,
            }
        except ImportError:
            # pydub not available, just check size
            return {"valid": True, "size": file_size, "format": audio_path.suffix}
        except Exception as e:
            return {"valid": False, "error": f"Audio validation failed: {e}"}


# Convenience functions
async def generate_speech_elevenlabs(
    text: str,
    output_path: Path,
    api_key: Optional[str] = None,
    voice: str = "rachel",
    **kwargs,
) -> Dict[str, Any]:
    """
    Quick function to generate speech with ElevenLabs.

    Args:
        text: Text to convert
        output_path: Output file path
        api_key: ElevenLabs API key
        voice: Voice name or ID
        **kwargs: Additional options

    Returns:
        Generation info dict
    """
    generator = TTSGenerator(elevenlabs_api_key=api_key, fallback_enabled=False)
    return await generator.generate_speech(
        text=text,
        output_path=output_path,
        voice=voice,
        provider=TTSProvider.ELEVENLABS,
        **kwargs,
    )


async def generate_speech_auto(
    text: str,
    output_path: Path,
    elevenlabs_key: Optional[str] = None,
    hf_key: Optional[str] = None,
    voice: str = "rachel",
    **kwargs,
) -> Dict[str, Any]:
    """
    Auto-select best available TTS provider.

    Args:
        text: Text to convert
        output_path: Output file path
        elevenlabs_key: ElevenLabs API key
        hf_key: Hugging Face API key
        voice: Voice name
        **kwargs: Additional options

    Returns:
        Generation info dict
    """
    generator = TTSGenerator(
        elevenlabs_api_key=elevenlabs_key,
        hf_api_key=hf_key,
        default_voice=voice,
        fallback_enabled=True,
    )
    return await generator.generate_speech(text=text, output_path=output_path, **kwargs)
