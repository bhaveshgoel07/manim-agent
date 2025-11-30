#!/usr/bin/env python3
"""
NeuroAnim Gradio Web Interface

A comprehensive web UI for generating educational STEM animations with:
- Topic input and configuration
- Real-time progress tracking
- Video preview and download
- Generated content display (narration, code, quiz)
- Error handling and logging
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import gradio as gr
from dotenv import load_dotenv

from orchestrator import NeuroAnimOrchestrator

load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def format_quiz_markdown(quiz_text: str) -> str:
    """Format quiz text into a nice markdown display."""
    if not quiz_text or quiz_text == "Not available":
        return "❓ No quiz generated yet."

    # If it's already formatted or looks good, return as is with some styling
    formatted = f"## 📝 Assessment Questions\n\n{quiz_text}"

    # Try to add some structure if it's plain text
    lines = quiz_text.split("\n")
    formatted_lines = []
    question_num = 0

    for line in lines:
        line = line.strip()
        if not line:
            formatted_lines.append("")
            continue

        # Detect question patterns
        if line.lower().startswith(("q:", "question", "q.", f"{question_num + 1}.")):
            question_num += 1
            formatted_lines.append(f"\n### Question {question_num}")
            # Remove the question prefix
            clean_line = line.split(":", 1)[-1].strip() if ":" in line else line
            formatted_lines.append(f"**{clean_line}**\n")
        elif line.lower().startswith(("a)", "b)", "c)", "d)", "a.", "b.", "c.", "d.")):
            # Format multiple choice options
            formatted_lines.append(f"- {line}")
        elif line.lower().startswith(("answer:", "a:", "correct:")):
            # Format answers
            formatted_lines.append(f"\n> ✅ {line}\n")
        else:
            formatted_lines.append(line)

    # If we detected structure, use the formatted version
    if question_num > 0:
        return "## 📝 Assessment Questions\n\n" + "\n".join(formatted_lines)

    # Otherwise return with basic formatting
    return formatted


class NeuroAnimApp:
    """Main application class for Gradio interface."""

    def __init__(self):
        self.orchestrator: Optional[NeuroAnimOrchestrator] = None
        self.current_task: Optional[asyncio.Task] = None
        self.is_generating = False
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        self.current_progress = None  # Store progress callback for dynamic updates

    async def initialize_orchestrator(self):
        """Initialize the orchestrator if not already done."""
        if self.orchestrator is None:
            self.orchestrator = NeuroAnimOrchestrator()
            await self.orchestrator.initialize()
            logger.info("Orchestrator initialized successfully")

    async def cleanup_orchestrator(self):
        """Clean up orchestrator resources."""
        if self.orchestrator is not None:
            await self.orchestrator.cleanup()
            self.orchestrator = None
            logger.info("Orchestrator cleaned up")
    
    def cleanup_event_loop(self):
        """Clean up the event loop on application shutdown."""
        if self.event_loop is not None and not self.event_loop.is_closed():
            self.event_loop.close()
            self.event_loop = None
            logger.info("Event loop closed")

    async def generate_animation_async(
        self, topic: str, audience: str, duration: float, quality: str, progress=gr.Progress()
    ) -> Dict[str, Any]:
        """
        Generate animation with progress tracking.

        Args:
            topic: STEM topic to animate
            audience: Target audience level
            duration: Animation duration in minutes
            quality: Video quality (low, medium, high, production_quality)
            progress: Gradio progress tracker

        Returns:
            Results dictionary with generated content
        """
        try:
            self.is_generating = True

            # Validate inputs
            if not topic or len(topic.strip()) < 3:
                return {
                    "success": False,
                    "error": "Please provide a valid topic (at least 3 characters)",
                }

            if duration < 0.5 or duration > 10:
                return {
                    "success": False,
                    "error": "Duration must be between 0.5 and 10 minutes",
                }

            # Initialize orchestrator
            progress(0.05, desc="Initializing system...")
            await self.initialize_orchestrator()

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_topic = "".join(c if c.isalnum() else "_" for c in topic)[:30]
            output_filename = f"{safe_topic}_{timestamp}.mp4"

            # Map quality from UI to orchestrator format
            quality_map = {
                "Low (480p, faster)": "low",
                "Medium (720p, balanced)": "medium",
                "High (1080p, slower)": "high",
                "Production (4K, slowest)": "production_quality",
            }
            quality_param = quality_map.get(quality, "medium")

            # Map audience from UI to orchestrator format
            audience_map = {
                "elementary": "elementary",
                "middle_school": "middle_school",
                "high_school": "high_school",
                "undergraduate": "college",  # Map to 'college' for LLM compatibility
                "phd": "graduate",  # Map to 'graduate' for LLM compatibility
                "general": "general",
            }
            audience_param = audience_map.get(audience, audience)

            # Dynamic progress tracking with step-based updates
            step_times = {}  # Track step start times
            step_index = [0]  # Current step index
            
            steps = [
                (0.1, "Planning concept"),
                (0.25, "Generating narration script"),
                (0.40, "Creating Manim animation code"),
                (0.55, "Rendering animation video"),
                (0.75, "Generating audio narration"),
                (0.90, "Merging video and audio"),
                (0.95, "Creating quiz questions"),
            ]
            
            import time
            
            def progress_callback(step_name: str, step_progress: float):
                """Callback for orchestrator to report progress."""
                # Find matching step
                for idx, (prog, desc) in enumerate(steps):
                    if desc.lower() in step_name.lower():
                        step_index[0] = idx
                        
                        # Track timing
                        current_time = time.time()
                        if step_name not in step_times:
                            step_times[step_name] = current_time
                        elapsed = current_time - step_times[step_name]
                        
                        # Add timing info for long steps
                        if elapsed > 30:  # Show message if step takes more than 30s
                            desc_with_time = f"{desc} (taking longer than usual, please wait...)"
                        else:
                            desc_with_time = f"{desc}..."
                        
                        progress(prog, desc=desc_with_time)
                        return
                
                # If no match, use the provided progress directly
                progress(step_progress, desc=f"{step_name}...")

            # Start generation with dynamic progress
            result = await self.orchestrator.generate_animation(
                topic=topic,
                target_audience=audience_param,
                animation_length_minutes=duration,
                output_filename=output_filename,
                quality=quality_param,
                progress_callback=progress_callback,
            )
            
            progress(1.0, desc="Complete!")
            logger.info("Async generation completed, returning result")

            return result

        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            self.is_generating = False

    def generate_animation_sync(
        self, topic: str, audience: str, duration: float, quality: str, progress=gr.Progress()
    ) -> Tuple[str, str, str, str, str, str]:
        """
        Synchronous wrapper for Gradio interface.

        Returns:
            Tuple of (video_path, status, narration, code, quiz, concept_plan)
        """
        try:
            # Reuse existing event loop or create a persistent one
            if self.event_loop is None or self.event_loop.is_closed():
                self.event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.event_loop)
                logger.info("Created new persistent event loop")
            else:
                asyncio.set_event_loop(self.event_loop)
                logger.info("Reusing existing event loop")

            logger.info("Starting event loop execution...")
            result = self.event_loop.run_until_complete(
                self.generate_animation_async(topic, audience, duration, quality, progress)
            )
            logger.info("Event loop execution completed")
            # DO NOT close the loop - keep it for subsequent generations

            if result["success"]:
                logger.info("Processing successful result...")
                video_path = result["output_file"]
                status = f"✅ **Animation Generated Successfully!**\n\n**Topic:** {result['topic']}\n**Audience:** {result['target_audience']}\n**Output:** {os.path.basename(video_path)}"
                narration = result.get("narration", "Not available")
                code = result.get("manim_code", "Not available")
                quiz_raw = result.get("quiz", "Not available")
                quiz = format_quiz_markdown(quiz_raw)
                concept = result.get("concept_plan", "Not available")

                logger.info(f"Returning result to Gradio: {video_path}")
                return video_path, video_path, status, narration, code, quiz, concept
            else:
                error_msg = result.get("error", "Unknown error")
                status = f"❌ **Generation Failed**\n\n{error_msg}"
                return None, None, status, "", "", "", ""

        except Exception as e:
            logger.error(f"Sync wrapper error: {e}", exc_info=True)
            status = f"💥 **Unexpected Error**\n\n{str(e)}"
            return None, None, status, "", "", "", ""


def create_interface() -> gr.Blocks:
    """Create the Gradio interface."""

    app = NeuroAnimApp()

    # Custom CSS for better styling
    custom_css = """
    .main-title {
        text-align: center;
        color: #2563eb;
        font-size: 2.5em;
        font-weight: bold;
        margin-bottom: 0.5em;
    }
    .subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1.2em;
        margin-bottom: 2em;
    }
    .status-box {
        padding: 1em;
        border-radius: 8px;
        margin: 1em 0;
    }
    .gradio-container {
        max-width: 1400px !important;
    }
    /* Video player styling */
    video {
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    /* Quiz and content styling */
    .markdown-text h2 {
        color: #1e40af;
        border-bottom: 2px solid #3b82f6;
        padding-bottom: 0.5em;
        margin-top: 1em;
    }
    .markdown-text h3 {
        color: #1e293b;
        margin-top: 1em;
    }
    .markdown-text blockquote {
        background-color: #f0fdf4;
        border-left: 4px solid #22c55e;
        padding: 0.5em 1em;
        margin: 1em 0;
    }
    /* Button styling */
    .primary {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    }
    /* Code block styling */
    .code-container {
        border-radius: 8px;
        margin: 1em 0;
    }
    """

    with gr.Blocks(title="NeuroAnim - STEM Animation Generator") as interface:
        # Apply custom CSS
        interface.css = custom_css
        # Header
        gr.HTML("""
        <div class="main-title">🧠 NeuroAnim</div>
        <div class="subtitle">AI-Powered Educational Animation Generator</div>
        """)

        with gr.Tabs() as tabs:
            # Main Generation Tab
            with gr.TabItem("🎬 Generate Animation", id=0):
                gr.Markdown("""
                ### Create Your Educational Animation
                Enter a mathematical or scientific concept, and NeuroAnim will generate a complete animated video with narration and quiz questions.
                """)

                with gr.Row():
                    with gr.Column(scale=1):
                        # Input Section
                        gr.Markdown("#### 📝 Animation Configuration")

                        topic_input = gr.Textbox(
                            label="Topic / Concept",
                            placeholder="e.g., Pythagorean Theorem, Photosynthesis, Newton's Laws, etc.",
                            lines=2,
                            info="Enter the STEM concept you want to explain",
                        )

                        with gr.Row():
                            audience_input = gr.Dropdown(
                                label="Target Audience",
                                choices=[
                                    "elementary",
                                    "middle_school",
                                    "high_school",
                                    "undergraduate",
                                    "phd",
                                    "general",
                                ],
                                value="high_school",
                                info="Select the appropriate education level",
                            )

                            duration_input = gr.Slider(
                                label="Duration (minutes)",
                                minimum=0.5,
                                maximum=10,
                                value=2.0,
                                step=0.5,
                                info="Animation length",
                            )

                        quality_input = gr.Dropdown(
                            label="Video Quality",
                            choices=[
                                "Low (480p, faster)",
                                "Medium (720p, balanced)",
                                "High (1080p, slower)",
                                "Production (4K, slowest)",
                            ],
                            value="Medium (720p, balanced)",
                            info="Higher quality takes longer to render",
                        )

                        generate_btn = gr.Button(
                            "🚀 Generate Animation", variant="primary", size="lg"
                        )

                        status_output = gr.Markdown(
                            label="Status",
                            value="Ready to generate...",
                            elem_classes=["status-box"],
                        )

                        # Example inputs
                        gr.Markdown("#### 💡 Example Topics")
                        gr.Examples(
                            examples=[
                                ["Pythagorean Theorem", "high_school", 2.0, "Medium (720p, balanced)"],
                                ["Laws of Motion", "middle_school", 2.5, "Low (480p, faster)"],
                                ["Binary Numbers", "middle_school", 1.5, "Medium (720p, balanced)"],
                                ["Photosynthesis Process", "elementary", 2.0, "Low (480p, faster)"],
                                ["Quadratic Formula", "high_school", 3.0, "Medium (720p, balanced)"],
                                ["Circle Area Derivation", "undergraduate", 2.5, "High (1080p, slower)"],
                            ],
                            inputs=[topic_input, audience_input, duration_input, quality_input],
                        )

                    with gr.Column(scale=1):
                        # Output Section
                        gr.Markdown("#### 🎥 Generated Animation")

                        video_output = gr.Video(
                            label="Animation Video", height=400, interactive=False
                        )

                        # Download button
                        download_file = gr.File(
                            label="📥 Download Animation",
                            interactive=False,
                            visible=True,
                        )

                        gr.Markdown(
                            "**Tip:** Click the download button above or use the ⋮ menu on the video player"
                        )

                # Additional outputs in accordion
                with gr.Accordion("📄 View Generated Content", open=True):
                    with gr.Tabs():
                        with gr.TabItem("📖 Narration Script"):
                            narration_output = gr.Textbox(
                                label="Narration Text",
                                lines=8,
                                interactive=False,
                            )

                        with gr.TabItem("💻 Manim Code"):
                            code_output = gr.Code(
                                label="Generated Python Code",
                                language="python",
                                interactive=False,
                                lines=15,
                            )

                        with gr.TabItem("❓ Quiz Questions"):
                            quiz_output = gr.Markdown(
                                label="Assessment Questions",
                                value="Quiz will appear here after generation...",
                            )

                        with gr.TabItem("📋 Concept Plan"):
                            concept_output = gr.Textbox(
                                label="Educational Plan",
                                lines=10,
                                interactive=False,
                            )

                # Connect the generate button
                generate_btn.click(
                    fn=app.generate_animation_sync,
                    inputs=[topic_input, audience_input, duration_input, quality_input],
                    outputs=[
                        video_output,
                        download_file,
                        status_output,
                        narration_output,
                        code_output,
                        quiz_output,
                        concept_output,
                    ],
                    api_name="generate",
                )

            # About Tab
            with gr.TabItem("ℹ️ About", id=1):
                gr.Markdown("""
                # About NeuroAnim

                NeuroAnim is an AI-powered educational animation generator that creates engaging STEM content automatically.

                ## 🎯 Features

                - **🎨 Automatic Animation Generation**: Creates professional Manim animations from topic descriptions
                - **🗣️ AI Narration**: Generates educational narration scripts tailored to your audience
                - **🔊 Text-to-Speech**: Converts narration to high-quality audio with ElevenLabs or Hugging Face
                - **📹 Video Production**: Renders and merges video with synchronized audio
                - **❓ Quiz Generation**: Creates assessment questions to test understanding
                - **🎓 Multi-Level Support**: Content appropriate for elementary through undergraduate levels

                ## 🔧 Technology Stack

                - **Manim Community Edition**: Mathematical animation engine
                - **Hugging Face Models**: AI-powered content generation
                - **ElevenLabs**: High-quality text-to-speech synthesis
                - **MCP (Model Context Protocol)**: Modular server architecture
                - **Gradio**: Interactive web interface

                ## 🚀 How It Works

                1. **Concept Planning**: AI analyzes your topic and creates an educational plan
                2. **Script Writing**: Generates age-appropriate narration aligned with learning objectives
                3. **Code Generation**: Creates Manim Python code for visual representation
                4. **Rendering**: Executes Manim to produce the base animation
                5. **Audio Synthesis**: Converts narration to speech using TTS
                6. **Final Production**: Merges video and audio into complete animation
                7. **Assessment**: Generates quiz questions for the content

                ## 📝 Tips for Best Results

                - **Be Specific**: Instead of "math", try "solving linear equations" or "area of a circle"
                - **Choose Right Audience**: Match the complexity level to your target viewers
                - **Optimal Duration**: 1.5-3 minutes works best for most concepts
                - **Review Generated Content**: Check the narration and code tabs to see what was created
                - **Iterate**: If results aren't perfect, try rewording your topic or adjusting parameters

                ## 🔑 Setup Requirements

                To use NeuroAnim, you need:
                - **Hugging Face API Key**: For AI content generation (required)
                - **ElevenLabs API Key**: For high-quality TTS (optional, falls back to HF TTS)

                Set these in your `.env` file:
                ```bash
                HUGGINGFACE_API_KEY=your_key_here
                ELEVENLABS_API_KEY=your_key_here  # Optional
                ```

                ## 📚 Example Use Cases

                - **Teachers**: Create engaging lesson materials
                - **Students**: Visualize complex concepts for better understanding
                - **Content Creators**: Produce educational YouTube/social media content
                - **Tutors**: Generate custom explanations for specific topics
                - **Course Developers**: Build comprehensive educational video libraries

                ## 🤝 Contributing

                NeuroAnim is open source! Contributions are welcome:
                - Report bugs or suggest features via GitHub Issues
                - Submit pull requests with improvements
                - Share your generated animations with the community

                ## 📄 License

                MIT License - Free to use for educational and commercial purposes

                ---

                Made with ❤️ for educational content creation
                """)

            # Settings Tab
            with gr.TabItem("⚙️ Settings", id=2):
                gr.Markdown("""
                # System Configuration

                Configure API keys and system settings here.
                """)

                with gr.Group():
                    gr.Markdown("### 🔑 API Keys")

                    hf_key_status = gr.Textbox(
                        label="Hugging Face API Key Status",
                        value="✅ Configured"
                        if os.getenv("HUGGINGFACE_API_KEY")
                        else "❌ Not Set",
                        interactive=False,
                    )

                    eleven_key_status = gr.Textbox(
                        label="ElevenLabs API Key Status",
                        value="✅ Configured"
                        if os.getenv("ELEVENLABS_API_KEY")
                        else "⚠️ Not Set (will use fallback TTS)",
                        interactive=False,
                    )

                    gr.Markdown("""
                    **To configure API keys:**
                    1. Create a `.env` file in the project root
                    2. Add your keys:
                       ```
                       HUGGINGFACE_API_KEY=your_hf_key
                       ELEVENLABS_API_KEY=your_elevenlabs_key
                       ```
                    3. Restart the application
                    """)

                with gr.Group():
                    gr.Markdown("### 📊 System Info")

                    system_info = gr.Textbox(
                        label="System Status",
                        value=f"""
Output Directory: {Path("outputs").absolute()}
Working Directory: Temporary (auto-created)
Manim Version: Community Edition
Default Quality: Medium (720p, 30fps)
                        """.strip(),
                        interactive=False,
                        lines=6,
                    )

    return interface


def main():
    """Launch the Gradio application."""

    # Check for API keys
    if not os.getenv("HUGGINGFACE_API_KEY"):
        logger.warning("HUGGINGFACE_API_KEY not set! Generation will fail.")
        print("\n⚠️  WARNING: HUGGINGFACE_API_KEY environment variable not set!")
        print("Please set it in your .env file or environment.\n")

    if not os.getenv("ELEVENLABS_API_KEY"):
        logger.info("ELEVENLABS_API_KEY not set, will use fallback TTS")
        print(
            "\nℹ️  Note: ELEVENLABS_API_KEY not set. Using fallback TTS (may have lower quality).\n"
        )

    # Create outputs directory
    Path("outputs").mkdir(exist_ok=True)

    # Build and launch interface
    interface = create_interface()

    logger.info("Launching Gradio interface...")

    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )


if __name__ == "__main__":
    main()
