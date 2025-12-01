---
title: NeuroAnim - STEM Animation Generator
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 6.0.1
app_file: app.py
pinned: false
license: mit
---

# 🧠 NeuroAnim - AI-Powered Educational Animation Generator

NeuroAnim is an AI-powered system that automatically generates educational STEM animations with narration and quiz questions. Simply enter a topic, and watch as AI creates a complete animated video!

## 🎯 Features

- **🎨 Automatic Animation Generation**: Creates professional Manim animations from topic descriptions
- **🗣️ AI Narration**: Generates educational narration scripts tailored to your audience
- **🔊 Text-to-Speech**: Converts narration to high-quality audio
- **📹 Video Production**: Renders and merges video with synchronized audio
- **❓ Quiz Generation**: Creates assessment questions to test understanding
- **🎓 Multi-Level Support**: Content appropriate for elementary through PhD levels

## 🚀 How to Use

1. **Enter a Topic**: Type any STEM concept (e.g., "Pythagorean Theorem", "Photosynthesis", "Newton's Laws")
2. **Select Audience**: Choose the appropriate education level
3. **Set Duration**: Pick animation length (0.5-10 minutes)
4. **Choose Quality**: Select video quality (higher = slower but better)
5. **Generate**: Click the button and wait for your animation!

## 💡 Example Topics

- **Mathematics**: Pythagorean Theorem, Quadratic Formula, Circle Area Derivation
- **Physics**: Newton's Laws, Laws of Motion, Wave Properties
- **Biology**: Photosynthesis, Cell Division, DNA Structure
- **Computer Science**: Binary Numbers, Sorting Algorithms, Data Structures

## 🔧 Technology Stack

- **Manim Community Edition**: Mathematical animation engine
- **Hugging Face Models**: AI-powered content generation
- **ElevenLabs**: High-quality text-to-speech synthesis
- **Blaxel**: Cloud-based secure rendering
- **Gradio**: Interactive web interface

## 🔑 Setup Requirements

To run this space, you need:

1. **Hugging Face API Key**: For AI content generation (required)
2. **ElevenLabs API Key**: For high-quality TTS (optional, falls back to HF TTS)
3. **Blaxel API Key**: For cloud rendering (optional, can use local rendering)

Set these as **Secrets** in your Hugging Face Space settings:
- `HUGGINGFACE_API_KEY`
- `ELEVENLABS_API_KEY` (optional)
- `BLAXEL_API_KEY` (optional)
- `MANIM_SANDBOX_IMAGE` (optional, for Blaxel cloud rendering)

## 📝 Tips for Best Results

- **Be Specific**: Instead of "math", try "solving linear equations" or "area of a circle"
- **Choose Right Audience**: Match the complexity level to your target viewers
- **Optimal Duration**: 1.5-3 minutes works best for most concepts
- **Review Generated Content**: Check the narration and code tabs to see what was created

## 🎬 How It Works

1. **Concept Planning**: AI analyzes your topic and creates an educational plan
2. **Script Writing**: Generates age-appropriate narration aligned with learning objectives
3. **Code Generation**: Creates Manim Python code for visual representation
4. **Rendering**: Executes Manim to produce the base animation
5. **Audio Synthesis**: Converts narration to speech using TTS
6. **Final Production**: Merges video and audio into complete animation
7. **Assessment**: Generates quiz questions for the content

## 📚 Use Cases

- **Teachers**: Create engaging lesson materials
- **Students**: Visualize complex concepts for better understanding
- **Content Creators**: Produce educational YouTube/social media content
- **Tutors**: Generate custom explanations for specific topics
- **Course Developers**: Build comprehensive educational video libraries

## 🤝 Contributing

NeuroAnim is open source! Visit the [GitHub repository](https://github.com/yourusername/manim-agent) to:
- Report bugs or suggest features
- Submit pull requests with improvements
- Share your generated animations

## 📄 License

MIT License - Free to use for educational and commercial purposes

---

Made with ❤️ for educational content creation
