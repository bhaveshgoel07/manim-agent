# Manim MCP Server

A comprehensive Model Context Protocol (MCP) server for creating educational STEM animations using Manim. This server combines AI-powered creative tools with rendering and video processing capabilities to streamline the animation creation workflow.

## Features

### 🎨 Creative Tools
- **Concept Planning**: AI-powered STEM concept planning with learning objectives and scene flow
- **Code Generation**: Intelligent Manim code generation with syntax validation
- **Code Refinement**: Automatic code improvement based on errors and feedback
- **Narration Generation**: Educational script writing tailored to target audiences
- **Quiz Generation**: Automated assessment question creation

### 🎬 Rendering & Processing
- **Manim Rendering**: Full Manim animation rendering with quality controls
- **Video Processing**: FFmpeg-based video manipulation and conversion
- **Audio/Video Merging**: Seamless integration of narration with animations
- **File Management**: Comprehensive file system operations

### 🤖 AI Integration
- **Vision Analysis**: Frame-by-frame quality assessment using vision models
- **Text-to-Speech**: Natural voice synthesis for narration
- **Multi-Model Support**: Flexible model selection for different tasks

## Installation

### Prerequisites

- Python 3.12+
- Manim Community Edition (`manim>=0.18.1`)
- FFmpeg (for video processing)
- HuggingFace API key (for AI features)

### Setup

1. Install the package and dependencies:

```bash
pip install mcp huggingface_hub manim pydantic aiohttp httpx numpy Pillow
```

2. Set up your environment variables:

```bash
export HUGGINGFACE_API_KEY="your_api_key_here"
```

3. Run the MCP server:

```bash
python manim_mcp/server.py
```

## Usage

### As an MCP Server

The server can be integrated into any MCP-compatible client (like Claude Desktop):

```json
{
  "mcpServers": {
    "manim": {
      "command": "python",
      "args": ["path/to/manim_mcp/server.py"],
      "env": {
        "HUGGINGFACE_API_KEY": "your_key"
      }
    }
  }
}
```

### Programmatic Usage

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Initialize MCP client
params = StdioServerParameters(
    command="python",
    args=["manim_mcp/server.py"],
    env={"HUGGINGFACE_API_KEY": "your_key"}
)

async with stdio_client(params) as (read, write):
    session = ClientSession(read, write)
    await session.initialize()
    
    # Plan a concept
    result = await session.call_tool("plan_concept", {
        "topic": "Pythagorean Theorem",
        "target_audience": "high_school",
        "animation_length_minutes": 2.0
    })
```

## Available Tools

### Planning & Creative

#### `plan_concept`
Plan a STEM concept for animation with learning objectives and scene flow.

**Parameters:**
- `topic` (string, required): The STEM topic to animate
- `target_audience` (enum, required): elementary | middle_school | high_school | college | general
- `animation_length_minutes` (number, optional): Desired length in minutes
- `model` (string, optional): HuggingFace model to use

#### `generate_manim_code`
Generate complete, runnable Manim Python code.

**Parameters:**
- `concept` (string, required): Animation concept
- `scene_description` (string, required): Detailed scene description
- `visual_elements` (array, optional): List of visual elements to include
- `previous_code` (string, optional): For retry attempts
- `error_message` (string, optional): Error from previous attempt

#### `refine_animation`
Refine existing Manim code based on feedback.

**Parameters:**
- `original_code` (string, required): Code to refine
- `feedback` (string, required): Feedback or error message
- `improvement_goals` (array, optional): Specific improvements to make

#### `generate_narration`
Generate educational narration scripts.

**Parameters:**
- `concept` (string, required): Animation concept
- `scene_description` (string, required): Scene details
- `target_audience` (string, required): Target audience level
- `duration_seconds` (integer, optional): Script duration

#### `generate_quiz`
Generate educational quiz questions.

**Parameters:**
- `concept` (string, required): STEM concept
- `difficulty` (enum, required): easy | medium | hard
- `num_questions` (integer, required): Number of questions
- `question_types` (array, optional): Types of questions

### Rendering & Processing

#### `write_manim_file`
Write Manim code to a file.

**Parameters:**
- `filepath` (string, required): Destination path
- `code` (string, required): Manim code to write

#### `render_manim_animation`
Render a Manim animation from a Python file.

**Parameters:**
- `scene_name` (string, required): Scene class name
- `file_path` (string, required): Path to Python file
- `output_dir` (string, required): Output directory
- `quality` (enum, optional): low | medium | high | production_quality
- `format` (enum, optional): mp4 | gif | png
- `frame_rate` (integer, optional): Frame rate (default: 30)

#### `merge_video_audio`
Merge video and audio files.

**Parameters:**
- `video_file` (string, required): Path to video
- `audio_file` (string, required): Path to audio
- `output_file` (string, required): Output path

#### `process_video_with_ffmpeg`
Process videos with custom FFmpeg arguments.

**Parameters:**
- `input_files` (array, required): Input file paths
- `output_file` (string, required): Output path
- `ffmpeg_args` (array, optional): Additional FFmpeg arguments

#### `check_file_exists`
Check file existence and get metadata.

**Parameters:**
- `filepath` (string, required): File path to check

### Analysis

#### `analyze_frame`
Analyze animation frames using vision models.

**Parameters:**
- `image_path` (string, required): Path to image
- `analysis_type` (string, required): Type of analysis
- `context` (string, optional): Additional context
- `model` (string, optional): Vision model to use

#### `generate_speech`
Convert text to speech audio.

**Parameters:**
- `text` (string, required): Text to convert
- `output_path` (string, required): Audio output path
- `voice` (string, optional): Voice to use
- `model` (string, optional): TTS model to use

## Complete Workflow Example

Here's a typical animation generation workflow:

1. **Plan** the concept
2. **Generate** narration script
3. **Generate** Manim code
4. **Write** code to file
5. **Render** the animation
6. **Generate** speech audio
7. **Merge** video and audio
8. **Generate** quiz questions

```python
# 1. Plan concept
plan = await session.call_tool("plan_concept", {
    "topic": "Newton's Laws of Motion",
    "target_audience": "high_school"
})

# 2. Generate narration
narration = await session.call_tool("generate_narration", {
    "concept": "Newton's Laws",
    "scene_description": plan["text"],
    "target_audience": "high_school",
    "duration_seconds": 120
})

# 3. Generate code
code = await session.call_tool("generate_manim_code", {
    "concept": "Newton's Laws",
    "scene_description": plan["text"],
    "visual_elements": ["text", "shapes", "arrows"]
})

# 4-7. Continue workflow...
```

## Configuration

### Environment Variables

- `HUGGINGFACE_API_KEY`: Required for AI-powered tools
- `ELEVENLABS_API_KEY`: Optional for premium TTS (falls back to free alternatives)

### Model Selection

By default, the server uses sensible model defaults, but you can specify custom models:

```python
await session.call_tool("generate_manim_code", {
    "concept": "topic",
    "scene_description": "description",
    "model": "Qwen/Qwen2.5-Coder-32B-Instruct"  # Custom model
})
```

## Quality Settings

Rendering quality options:
- **low**: 480p15 - Fast, good for testing
- **medium**: 720p30 - Balanced quality/speed (default)
- **high**: 1080p60 - High quality, slower
- **production_quality**: 2160p60 - 4K, very slow

## Error Handling

The server includes comprehensive error handling:
- Syntax validation for generated code
- Retry logic for code generation failures
- Graceful fallbacks for AI services
- Detailed error messages for debugging

## Architecture

The server is organized into modular tool categories:

```
manim_mcp/
├── server.py           # Main MCP server
├── tools/
│   ├── planning.py     # Concept planning
│   ├── code_generation.py  # Code generation & refinement
│   ├── rendering.py    # Manim rendering
│   ├── vision.py       # Frame analysis
│   ├── audio.py        # TTS & narration
│   ├── video.py        # Video processing
│   └── quiz.py         # Quiz generation
```

## Requirements

- Python >= 3.12
- mcp >= 1.0.0
- huggingface_hub >= 0.25.0
- manim >= 0.18.1
- pydantic >= 2.0.0
- aiohttp >= 3.8.0
- FFmpeg (system dependency)

## Contributing

Contributions are welcome! Areas for improvement:
- Additional AI model integrations
- More video processing tools
- Enhanced error recovery
- Performance optimizations

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or feature requests, please open an issue on the repository.

## Credits

Built with:
- [Manim Community Edition](https://www.manim.community/) - Mathematical animation engine
- [Model Context Protocol](https://modelcontextprotocol.io/) - AI integration framework
- [HuggingFace](https://huggingface.co/) - AI model hosting and inference

---

**Version**: 0.1.0  
**Author**: NeuroAnim Team  
**Status**: Beta - Ready for production use with active development