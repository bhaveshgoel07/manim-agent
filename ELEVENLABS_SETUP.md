# ElevenLabs TTS Setup Guide

## Overview

ElevenLabs provides high-quality, natural-sounding text-to-speech (TTS) that significantly improves the audio quality of your animations compared to free alternatives.

## Why ElevenLabs?

- ✅ **Superior Quality**: Most natural-sounding AI voices available
- ✅ **Fast Generation**: Typically < 5 seconds for narration
- ✅ **Reliable**: Consistent output, no blank audio issues
- ✅ **Multiple Voices**: Wide selection of voices for different styles
- ✅ **Emotional Range**: Voices can convey emotion and emphasis

## Getting Started

### Step 1: Create an ElevenLabs Account

1. Go to [elevenlabs.io](https://elevenlabs.io)
2. Click "Sign Up" (top right)
3. Choose a plan:
   - **Free Tier**: 10,000 characters/month (~10 animations)
   - **Starter**: $5/month for 30,000 characters
   - **Creator**: $22/month for 100,000 characters
   - **Pro**: $99/month for 500,000 characters

### Step 2: Get Your API Key

1. Log in to your ElevenLabs account
2. Click your profile icon (top right)
3. Select "Profile"
4. Find the "API Key" section
5. Click "Copy" to copy your API key
   - It looks like: `sk_abc123def456...`

### Step 3: Configure the Project

#### Option A: Environment Variable (Recommended)

Create or edit `.env` file in the project root:

```bash
# ElevenLabs Configuration
ELEVENLABS_API_KEY=sk_your_actual_api_key_here

# Optional: Hugging Face as fallback
HUGGINGFACE_API_KEY=hf_your_huggingface_key_here
```

#### Option B: Command Line Argument

```bash
python orchestrator.py "photosynthesis" --elevenlabs-key sk_your_api_key_here
```

#### Option C: Programmatic

```python
from orchestrator import NeuroAnimOrchestrator

orchestrator = NeuroAnimOrchestrator(
    elevenlabs_api_key="sk_your_api_key_here",
    hf_api_key="hf_your_fallback_key_here"
)
```

### Step 4: Install Dependencies

```bash
# Activate your virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install required packages
pip install httpx gtts pydub
```

## Available Voices

The system comes with 9 pre-configured professional voices:

| Voice Name | ID | Description | Best For |
|-----------|-----|-------------|----------|
| **rachel** | `21m00Tcm4TlvDq8ikWAM` | Clear, neutral female | Educational content, narration |
| **adam** | `pNInz6obpgDQGcFmaJgB` | Deep, confident male | Documentary, serious topics |
| **antoni** | `ErXwobaYiN019PkySvjV` | Well-rounded male | General narration |
| **arnold** | `VR6AewLTigWG4xSOukaG` | Crisp, articulate male | Technical content |
| **bella** | `EXAVITQu4vr4xnSDxMaL` | Soft, gentle female | Children's content |
| **domi** | `AZnzlk1XvdvUeBnXmlld` | Strong female | Assertive narration |
| **elli** | `MF3mGyEYCl7XYWbV9V6O` | Emotional, expressive female | Storytelling |
| **josh** | `TxGEqnHWrfWFTfGW9XjX` | Young, energetic male | Youth content |
| **sam** | `yoZ06aMxZJJ28mfd3POQ` | Raspy male | Character voices |

### Using a Specific Voice

```python
# In your code
tts_result = await tts_generator.generate_speech(
    text="Your narration text",
    output_path=audio_file,
    voice="adam"  # Change to any voice name
)
```

### Using Custom Voices

If you've created custom voices in ElevenLabs:

```python
# Use the voice ID directly
tts_result = await tts_generator.generate_speech(
    text="Your narration text",
    output_path=audio_file,
    voice="your_custom_voice_id_here"
)
```

## Advanced Configuration

### Voice Settings

You can fine-tune voice characteristics:

```python
tts_result = await tts_generator.generate_speech(
    text="Your narration text",
    output_path=audio_file,
    voice="rachel",
    stability=0.5,           # 0.0-1.0: Lower = more expressive, Higher = more stable
    similarity_boost=0.75,   # 0.0-1.0: Higher = more similar to original voice
    style=0.0,              # 0.0-1.0: Style exaggeration
    use_speaker_boost=True  # Enhance clarity
)
```

#### Stability
- **Low (0.0-0.3)**: More expressive and variable, good for storytelling
- **Medium (0.4-0.6)**: Balanced, good for most content (default: 0.5)
- **High (0.7-1.0)**: Very consistent, good for audiobooks

#### Similarity Boost
- **Low (0.0-0.4)**: More creative interpretation
- **Medium (0.5-0.7)**: Balanced (default: 0.75)
- **High (0.8-1.0)**: Closest to the original voice

### Model Selection

ElevenLabs offers different models:

```python
tts_result = await tts_generator.generate_speech(
    text="Your narration text",
    output_path=audio_file,
    voice="rachel",
    model_id="eleven_monolingual_v1"  # Default, English only, fastest
    # model_id="eleven_multilingual_v2"  # Supports multiple languages
    # model_id="eleven_turbo_v2"  # Faster, slightly lower quality
)
```

## Testing Your Setup

### Quick Test Script

Create `test_tts.py`:

```python
import asyncio
from pathlib import Path
from utils.tts import generate_speech_elevenlabs

async def test_elevenlabs():
    """Test ElevenLabs TTS."""
    text = "Hello! This is a test of ElevenLabs text to speech."
    output = Path("test_audio.mp3")
    
    try:
        result = await generate_speech_elevenlabs(
            text=text,
            output_path=output,
            voice="rachel"
        )
        print(f"✅ Success! Audio saved to: {output}")
        print(f"Provider: {result['provider']}")
        print(f"File size: {result['file_size_bytes']} bytes")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_elevenlabs())
```

Run it:

```bash
python test_tts.py
```

### Test All Voices

```python
import asyncio
from pathlib import Path
from utils.tts import TTSGenerator

async def test_all_voices():
    """Generate samples of all available voices."""
    tts = TTSGenerator()
    voices = await tts.get_available_voices()
    
    text = "This is a sample of my voice for educational animations."
    
    for voice_name in ["rachel", "adam", "bella"]:
        output = Path(f"voice_sample_{voice_name}.mp3")
        print(f"Generating {voice_name}...")
        
        result = await tts.generate_speech(
            text=text,
            output_path=output,
            voice=voice_name
        )
        print(f"✅ {voice_name}: {output}")

if __name__ == "__main__":
    asyncio.run(test_all_voices())
```

## How the Fallback System Works

The TTS system has automatic fallback:

```
1. Try ElevenLabs (if API key available)
   ↓ (if fails)
2. Try Hugging Face TTS (if API key available)
   ↓ (if fails)
3. Try Google TTS (free, always available)
```

You can disable fallback:

```python
tts_generator = TTSGenerator(
    elevenlabs_api_key="your_key",
    fallback_enabled=False  # Fail immediately if ElevenLabs fails
)
```

## Monitoring Usage

### Check Your Usage

1. Go to [elevenlabs.io](https://elevenlabs.io)
2. Log in
3. Click "Usage" in the sidebar
4. View your character usage and remaining quota

### Estimate Costs

**Rule of thumb**: 1 minute of narration ≈ 150-200 words ≈ 900-1200 characters

**Free Tier** (10,000 chars/month):
- ~8-10 minutes of narration
- ~8-10 animations (assuming 1 min each)

**Starter** ($5/month, 30,000 chars):
- ~25-30 minutes of narration
- ~25-30 animations

**Creator** ($22/month, 100,000 chars):
- ~80-100 minutes of narration
- ~80-100 animations

## Troubleshooting

### Problem: "ElevenLabs API key not provided"

**Solution**: 
1. Check your `.env` file exists
2. Verify `ELEVENLABS_API_KEY=sk_...` is set correctly
3. No quotes around the key
4. No spaces around the `=`

### Problem: "401 Unauthorized"

**Solutions**:
1. API key is invalid
2. API key has expired
3. Account has been suspended
4. Check your key at elevenlabs.io/profile

### Problem: "429 Too Many Requests"

**Solutions**:
1. You've exceeded your quota
2. Wait for quota to reset (monthly)
3. Upgrade your plan
4. Enable fallback to HuggingFace/gTTS

### Problem: "Audio file is blank/silent"

**Solutions**:
1. Check the output file size (should be > 10KB)
2. Try a different voice
3. Check if text is too short (< 10 chars)
4. Verify audio format is compatible

### Problem: "Slow generation"

**Solutions**:
1. Use `eleven_turbo_v2` model
2. Check your internet connection
3. Reduce text length (split long narrations)
4. Consider caching commonly used phrases

### Problem: "Import Error: No module named 'httpx'"

**Solution**:
```bash
pip install httpx gtts pydub
```

## Best Practices

### 1. Text Preparation

- **Use proper punctuation**: Helps with natural pauses
- **Avoid special characters**: Stick to alphanumeric and basic punctuation
- **Break long text**: Split into shorter segments for better pacing
- **Add pauses**: Use `...` for longer pauses

Example:
```python
text = """
Photosynthesis is the process by which plants create energy.
It happens in the chloroplasts... using sunlight, water, and carbon dioxide.
The result? Glucose and oxygen!
"""
```

### 2. Voice Selection

- **Educational content**: Rachel, Arnold
- **Storytelling**: Elli, Antoni
- **Technical topics**: Adam, Arnold
- **Children's content**: Bella, Josh

### 3. Caching

For repeated phrases, cache the audio:

```python
import hashlib
from pathlib import Path

def get_cached_audio(text: str, voice: str) -> Path:
    """Get cached audio or generate if not exists."""
    text_hash = hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
    cache_path = Path(f"audio_cache/{text_hash}.mp3")
    
    if cache_path.exists():
        return cache_path
    
    # Generate and cache
    cache_path.parent.mkdir(exist_ok=True)
    # ... generate audio ...
    return cache_path
```

### 4. Error Handling

Always handle TTS errors gracefully:

```python
try:
    audio = await tts_generator.generate_speech(...)
except Exception as e:
    logger.error(f"TTS failed: {e}")
    # Use fallback or text overlay instead
    return None
```

## Security Best Practices

### ✅ DO:
- Store API keys in `.env` file
- Add `.env` to `.gitignore`
- Use environment variables in production
- Rotate keys periodically
- Use separate keys for dev/prod

### ❌ DON'T:
- Commit API keys to git
- Share keys in public forums
- Hard-code keys in source files
- Use production keys for testing
- Share keys between team members

## Cost Optimization Tips

1. **Use Free Tier First**: Test with 10k chars/month
2. **Enable Fallback**: Save quota by using free alternatives when needed
3. **Cache Audio**: Don't regenerate same narration
4. **Optimize Text**: Remove unnecessary words
5. **Batch Processing**: Generate multiple animations in one session
6. **Monitor Usage**: Set alerts in ElevenLabs dashboard

## Getting Help

### ElevenLabs Support
- Documentation: https://docs.elevenlabs.io
- Discord: https://discord.gg/elevenlabs
- Email: support@elevenlabs.io

### Project Issues
- GitHub Issues: [Your repo URL]
- Documentation: See `README.md`
- Examples: See `example.py`

## Alternative TTS Providers

If ElevenLabs doesn't work for you:

### Hugging Face (Free)
```bash
HUGGINGFACE_API_KEY=hf_your_key_here
```
- Pros: Free, open source
- Cons: Lower quality, slower

### Google TTS (Free)
```python
# No API key needed, automatic fallback
```
- Pros: Free, reliable, fast
- Cons: Robotic voice, limited customization

### AWS Polly
```python
# Requires AWS credentials
```
- Pros: Good quality, many voices
- Cons: AWS complexity, pay-per-use

### Azure TTS
```python
# Requires Azure subscription
```
- Pros: Good quality, multilingual
- Cons: Microsoft ecosystem, pricing

## Next Steps

1. ✅ Set up your API key
2. ✅ Test with `test_tts.py`
3. ✅ Generate your first animation
4. ✅ Experiment with different voices
5. ✅ Optimize settings for your content

Happy animating! 🎬🎙️