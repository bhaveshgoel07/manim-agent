---
title: NeuroAnim - STEM Animation Generator
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 5.0.0
app_file: app.py
pinned: false
license: mit
tags:
  - building-mcp-track-creative
  - mcp-in-action-track-creative
  - agent-course
  - agents
  - manim
  - education
  - mcp
---

# 🧠 NeuroAnim - AI-Powered Educational Animation Generator

**NeuroAnim** is an autonomous AI agent that generates professional-quality educational STEM animations. It orchestrates multiple AI models and tools using the **Model Context Protocol (MCP)** to plan, script, code, render, and narrate educational videos automatically.

---

## 🏆 Hackathon Submission

This project is submitted to the **MCP Hackathon** under the following tracks:

### 🔧 Track 1: Building MCP (Creative)
**Tag:** `building-mcp-track-creative`
We built two custom MCP servers that extend LLM capabilities:
1.  **`mcp-renderer`**: A specialized server for Manim code generation, validation, and secure sandboxed rendering using **Blaxel**.
2.  **`mcp-creative`**: A creative server for educational concept planning, scriptwriting, and quiz generation using **Hugging Face** models.

### 🤖 Track 2: MCP in Action (Creative)
**Tag:** `mcp-in-action-track-creative`
NeuroAnim is a complete autonomous agent that:
- **Plans**: Deconstructs complex STEM topics into teachable concepts.
- **Reasons**: Decides on the best visual metaphors and analogies for the target audience.
- **Executes**: Writes Python code, renders video, generates audio, and merges assets into a final product.

### 🏢 Sponsor Integrations
- **Blaxel**: Used for secure, scalable cloud rendering of Manim animations (Blaxel Choice Award).
- **ElevenLabs**: Used for high-quality, life-like narration (ElevenLabs Category Award).
- **Hugging Face**: Hosted on Spaces, utilizing HF Inference API for reasoning and generation.

---

## 🔗 Submission Links

- **Social Media Post**: [X (Twitter) Post](https://x.com/trashdeployer/status/1995281046594834458)
- **Demo Video**: [Watch Demo](https://docs.google.com/document/d/1pCK3H0_wr4_Tbg2JwFNtipWaHERc2y_0lv7H_4QUhz0/edit?usp=sharing)

---

## 👥 Team Members

- **[Your_HF_Username]**
- *[Add other team members here]*

---

## 🎯 Features

- **🎨 Automatic Animation Generation**: Creates professional Manim animations from topic descriptions.
- **🗣️ AI Narration**: Generates educational narration scripts tailored to your audience.
- **🔊 Text-to-Speech**: Converts narration to high-quality audio using **ElevenLabs** (or HF fallback).
- **☁️ Cloud Rendering**: Uses **Blaxel** sandboxes for secure and fast video rendering.
- **❓ Quiz Generation**: Creates assessment questions to test understanding.
- **🎓 Multi-Level Support**: Content appropriate for elementary through PhD levels.

## 🚀 How to Use

1.  **Enter a Topic**: Type any STEM concept (e.g., "Pythagorean Theorem", "Photosynthesis", "Newton's Laws").
2.  **Select Audience**: Choose the appropriate education level.
3.  **Set Duration**: Pick animation length (0.5-10 minutes).
4.  **Generate**: Click the button and watch the agent work!

## 🔧 Technology Stack & Architecture

NeuroAnim uses a modular agentic architecture built on **MCP**:

### 1. The Orchestrator (Agent)
The central brain that coordinates the workflow. It connects to MCP servers to execute tasks.

### 2. Renderer MCP Server (`mcp-servers/renderer.py`)
- **Tools**: `write_manim_file`, `render_manim_animation`, `merge_video_audio`
- **Tech**: **Blaxel** (Sandboxed Execution), **FFmpeg**, **Manim Community**
- **Innovation**: Solves the "arbitrary code execution" risk by running generated Python code in secure Blaxel sandboxes.

### 3. Creative MCP Server (`mcp-servers/creative.py`)
- **Tools**: `plan_concept`, `generate_narration`, `generate_manim_code`, `generate_quiz`
- **Tech**: **Hugging Face Inference API** (Qwen/Llama models), **ElevenLabs API**
- **Innovation**: Uses chain-of-thought prompting to ensure educational accuracy and visual creativity.

## 🔑 Setup Requirements

To run this space, you need to configure the following **Secrets** in your Space settings:

1.  `HUGGINGFACE_API_KEY` (Required): For AI content generation.
2.  `ELEVENLABS_API_KEY` (Optional): For high-quality narration (highly recommended).
3.  `BLAXEL_API_KEY` (Optional): For cloud rendering (recommended for speed/security).
4.  `MANIM_SANDBOX_IMAGE` (Optional): Custom Blaxel image for Manim.

## 📝 Tips for Best Results

- **Be Specific**: Instead of "math", try "solving linear equations" or "area of a circle".
- **Choose Right Audience**: Match the complexity level to your target viewers.
- **Optimal Duration**: 1.5-3 minutes works best for most concepts.

## 📚 Use Cases

- **Teachers**: Create engaging lesson materials.
- **Students**: Visualize complex concepts for better understanding.
- **Content Creators**: Produce educational YouTube/social media content.

## 🤝 Contributing

NeuroAnim is open source! We welcome contributions to extend the MCP capabilities or add new visualization styles.

## 📄 License

MIT License - Free to use for educational and commercial purposes.

---

*Made with ❤️ for the MCP Hackathon*
