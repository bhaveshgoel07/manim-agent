# Changelog

All notable changes to the NeuroAnim project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2024-01-20

### 🎉 Added

- **Gradio Web Interface** (`app.py`)
  - Beautiful, user-friendly web UI for generating animations
  - Real-time progress tracking with visual indicators
  - Video preview and download capabilities
  - Tabbed interface with Generate, About, and Settings sections
  - Example topics for quick start
  - Comprehensive status messages and error handling
  - Built-in documentation and tips
  - API endpoint for programmatic access

- **Comprehensive Documentation**
  - `GRADIO_GUIDE.md` - Complete quickstart and user guide for web interface
  - `IMPROVEMENTS.md` - Detailed technical improvement recommendations
  - `CHANGELOG.md` - Version history tracking

- **Narration Text Cleaning**
  - New `_clean_narration_text()` method in `orchestrator.py`
  - Removes prefixes like "Narration Script:", "Script:", etc.
  - Strips markdown code blocks and formatting artifacts
  - Ensures only pure spoken text is sent to TTS

### 🐛 Fixed

- **Critical Audio Generation Bug**
  - Problem: Narration text contained title prefixes ("Narration Script:\n\n") that were being sent to TTS
  - Impact: Caused poor audio quality, robotic speech, or complete TTS failures
  - Solution: Implemented text cleaning pipeline in orchestrator before TTS generation
  - Location: `orchestrator.py` lines 353-389

- **Narration Script Quality**
  - Problem: AI models were adding unwanted prefixes and formatting to narration text
  - Solution: Rewritten prompt with explicit instructions to output only spoken text
  - Added post-processing cleanup in `mcp_servers/creative.py`
  - Now returns clean text ready for TTS without manual intervention

### 🔧 Changed

- **Enhanced Narration Generation Prompts**
  - Completely rewritten prompt structure in `mcp_servers/creative.py`
  - Now includes word count guidance based on duration (WPM calculation)
  - Explicit instructions for educational content quality
  - Clear formatting requirements
  - More engaging, audience-appropriate output
  - Better alignment with target duration

- **Improved Manim Code Generation**
  - Enhanced prompts with explicit syntax requirements
  - Added comprehensive list of valid Manim color constants
  - Specified correct animation method capitalization
  - Included guidance on common pitfalls
  - Better error feedback for retry attempts
  - Use of `MovingCameraScene` for enhanced capabilities

- **Updated Dependencies**
  - Added `gradio>=4.0.0` for web interface
  - Added `textstat>=0.7.0` for narration analysis (future use)
  - Updated `pyproject.toml` with new requirements

### 📝 Documentation

- Added inline code documentation for new methods
- Improved logging messages for better debugging
- Added progress tracking indicators
- Created comprehensive user guides

---

## [0.1.0] - 2024-01-15

### Initial Release

- **Core Architecture**
  - MCP (Model Context Protocol) server implementation
  - Renderer server for Manim execution and video processing
  - Creative server for AI-powered content generation
  - Orchestrator for pipeline coordination

- **Features**
  - Concept planning with AI
  - Educational narration script generation
  - Automatic Manim code generation
  - Video rendering with Manim
  - Text-to-speech with ElevenLabs and HuggingFace fallback
  - Video-audio merging with FFmpeg
  - Quiz question generation
  - Multi-audience support (elementary to undergraduate)

- **Infrastructure**
  - Hugging Face Inference API wrapper with rate limiting
  - TTS generator with multi-provider support
  - Secure code execution with Blaxel sandboxing
  - Configurable model selection
  - Error handling and retry logic

- **Documentation**
  - README.md with installation and usage instructions
  - QUICKSTART.md for rapid setup
  - ELEVENLABS_SETUP.md for TTS configuration

---

## Known Issues

### High Priority
- [ ] Occasional syntax errors in generated Manim code (retry logic helps)
- [ ] Some AI models may timeout on complex topics
- [ ] Duration estimation not always accurate

### Medium Priority  
- [ ] No caching mechanism (regenerates everything each time)
- [ ] Limited validation of generated code before rendering
- [ ] Quiz quality varies by topic complexity

### Low Priority
- [ ] No preview mode (must wait for full generation)
- [ ] Cannot pause/resume generation
- [ ] No batch processing support

See `IMPROVEMENTS.md` for detailed recommendations and solutions.

---

## Upgrade Guide

### From 0.1.0 to 0.2.0

1. **Update Dependencies**
   ```bash
   pip install -e .
   ```
   This will install Gradio and other new dependencies.

2. **No Breaking Changes**
   - All existing command-line functionality preserved
   - `orchestrator.py` API remains compatible
   - Environment variables unchanged

3. **New Features Available**
   - Launch web interface: `python app.py`
   - Access at http://localhost:7860
   - Old CLI still works: `python orchestrator.py "topic"`

4. **Migration Notes**
   - Generated animations now include timestamps in filenames
   - Output directory remains `outputs/`
   - No changes to `.env` configuration required

---

## Future Roadmap

### Version 0.3.0 (Planned)
- [ ] Code validator with post-processing
- [ ] Syntax validation before rendering
- [ ] Narration quality analyzer
- [ ] Caching layer for generated content
- [ ] Preview mode (concept + script without rendering)

### Version 0.4.0 (Planned)
- [ ] Multi-language support
- [ ] Custom voice cloning integration
- [ ] Template library for common patterns
- [ ] Metrics dashboard
- [ ] User feedback system

### Version 1.0.0 (Future)
- [ ] Stable API
- [ ] Comprehensive test coverage
- [ ] Production-ready deployment
- [ ] Advanced customization options
- [ ] Community template sharing

---

## Contributing

Contributions are welcome! Please:
1. Check existing issues before creating new ones
2. Follow the existing code style
3. Add tests for new features
4. Update documentation as needed
5. Submit PRs with clear descriptions

---

## Acknowledgments

Special thanks to:
- **Manim Community** for the amazing animation framework
- **Hugging Face** for accessible AI models
- **ElevenLabs** for high-quality TTS
- **Gradio** for easy-to-use interface framework
- **Contributors** and early testers

---

**Project Links:**
- Repository: [GitHub Link]
- Documentation: See README.md
- Issues: [GitHub Issues]
- Discussions: [GitHub Discussions]

**Maintained by:** NeuroAnim Development Team  
**License:** MIT