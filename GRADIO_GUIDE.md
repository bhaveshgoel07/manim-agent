# NeuroAnim Gradio Interface - Quick Start Guide

Welcome to the NeuroAnim web interface! This guide will help you get started with generating educational STEM animations through an intuitive web UI.

---

## 🚀 Quick Start

### 1. Installation

First, ensure you have all dependencies installed:

```bash
cd /path/to/manim-agent
pip install -e .
```

This will install all required packages including Gradio.

### 2. Configure API Keys

Create or edit your `.env` file in the project root:

```bash
# Required
HUGGINGFACE_API_KEY=your_huggingface_api_key_here

# Optional but recommended for better audio quality
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Optional for secure sandboxed execution
BLAXEL_API_KEY=your_blaxel_api_key_here
```

**Get API Keys:**
- **Hugging Face**: Sign up at [huggingface.co](https://huggingface.co) → Settings → Access Tokens
- **ElevenLabs**: Sign up at [elevenlabs.io](https://elevenlabs.io) → Profile → API Key
- **Blaxel**: Sign up at [blaxel.ai](https://blaxel.ai) (optional)

### 3. Launch the Interface

```bash
python app.py
```

You should see output like:
```
✓ Running on local URL:  http://127.0.0.1:7860
✓ Running on public URL: https://xxxxx.gradio.live (if sharing enabled)
```

### 4. Access the Web Interface

Open your browser and navigate to: **http://localhost:7860**

---

## 🎬 Using the Interface

### Main Tab: Generate Animation

#### Step 1: Enter Your Topic
In the "Topic / Concept" field, enter a mathematical or scientific concept you want to explain.

**Good Examples:**
- "Pythagorean Theorem"
- "How photosynthesis works"
- "Newton's Second Law of Motion"
- "Solving quadratic equations"
- "Binary number system"

**Tips:**
- Be specific rather than vague
- Include the key concept name
- Avoid overly broad topics (e.g., "all of calculus")

#### Step 2: Choose Target Audience
Select the appropriate education level:
- **Elementary**: Ages 6-11 (simple language, basic concepts)
- **Middle School**: Ages 11-14 (moderate complexity)
- **High School**: Ages 14-18 (standard academic level)
- **Undergraduate**: College level (technical depth)
- **General**: Mixed audience (accessible but informative)

#### Step 3: Set Duration
Use the slider to choose animation length:
- **0.5-1.5 minutes**: Quick concept introduction
- **2-3 minutes**: Standard explanation (recommended)
- **3-5 minutes**: Detailed walkthrough
- **5-10 minutes**: Comprehensive lesson

**Note:** Longer animations take more time to generate and may be harder to follow.

#### Step 4: Generate!
Click the **"🚀 Generate Animation"** button and wait for the magic to happen!

**Generation typically takes 2-5 minutes** depending on:
- Animation duration
- System resources
- API response times
- Rendering complexity

### Progress Tracking

Watch the progress bar to see what's happening:
1. **Planning concept...** - AI analyzes your topic
2. **Generating narration script...** - Creating the story
3. **Creating Manim animation code...** - Writing Python code
4. **Rendering animation video...** - Manim creates the video
5. **Generating audio narration...** - Text-to-speech conversion
6. **Merging video and audio...** - Final production
7. **Creating quiz questions...** - Assessment generation

### Results

Once complete, you'll see:

1. **Video Player**: Watch your generated animation
   - Use the download button to save the video
   - Videos are saved in the `outputs/` directory

2. **Status Message**: Confirmation with details
   - Topic, audience, output filename
   - Success or error information

3. **Additional Content** (expandable accordion):
   - **Narration Script**: The spoken text
   - **Manim Code**: Python code used to create the animation
   - **Quiz Questions**: Assessment questions about the topic
   - **Concept Plan**: Educational planning details

---

## 💡 Tips for Best Results

### Topic Selection

✅ **Good Topics:**
- "Explain the Pythagorean theorem with a proof"
- "Visualize the quadratic formula"
- "Show how binary addition works"
- "Demonstrate Newton's laws with examples"

❌ **Avoid:**
- Overly vague: "math stuff"
- Too broad: "all of physics"
- Non-visual: "history of mathematics"
- Too niche: "Riemann hypothesis proof"

### Audience Matching

- **Elementary**: Use for basic arithmetic, simple science, introductory concepts
- **Middle School**: Algebra basics, pre-algebra, earth science, basic chemistry
- **High School**: Advanced algebra, geometry, trigonometry, physics, chemistry
- **Undergraduate**: Calculus, linear algebra, advanced physics, computer science
- **General**: When unsure or for mixed audiences

### Duration Guidelines

| Duration | Best For | Typical Content |
|----------|----------|-----------------|
| 0.5-1 min | Single formula/concept | Definition + example |
| 1.5-2 min | Standard lesson | Concept + explanation + example |
| 2-3 min | Detailed explanation | Theory + multiple examples + applications |
| 3-5 min | Comprehensive topic | Multiple concepts + derivations + practice |

### Common Issues & Solutions

**Problem:** "Generation Failed" error
- **Check** your API keys are correctly set in `.env`
- **Verify** you have internet connection
- **Try** a simpler topic or shorter duration
- **Look** at the status message for specific error details

**Problem:** Audio sounds wrong or missing
- **Check** ELEVENLABS_API_KEY is set (for best quality)
- **Verify** the narration script looks correct (in the accordion)
- **Note** that HF fallback TTS has lower quality but should work

**Problem:** Video doesn't render
- **Ensure** Manim is properly installed: `manim --version`
- **Check** FFmpeg is installed: `ffmpeg -version`
- **Look** at the generated code tab for syntax errors
- **Try** regenerating - AI can sometimes produce invalid code

**Problem:** "Topic too vague" or poor quality output
- **Be more specific** in your topic description
- **Include keywords** like "explain", "prove", "demonstrate"
- **Try different phrasing** if results aren't good

---

## ⚙️ Settings Tab

### Check API Key Status
View which API keys are configured:
- ✅ Green checkmark = configured
- ❌ Red X = not set (required)
- ⚠️ Warning = not set (optional, will use fallback)

### System Information
View system configuration:
- Output directory location
- Default rendering settings
- Manim version

### Reconfiguring Keys
If you need to change API keys:
1. Edit the `.env` file in the project root
2. Restart the Gradio application
3. Check the Settings tab to verify new keys are detected

---

## ℹ️ About Tab

Learn more about:
- NeuroAnim features
- Technology stack
- How the system works
- Example use cases
- Tips for best results

---

## 📁 Output Files

Generated animations are saved in the `outputs/` directory with filenames like:
```
Pythagorean_Theorem_20240120_143022.mp4
```

The filename includes:
- Sanitized topic name (alphanumeric + underscores)
- Timestamp (YYYYMMDD_HHMMSS)
- .mp4 extension

**Downloading:**
- Click the download button in the video player
- Or navigate to `outputs/` and copy files directly

**File Management:**
- Old files are NOT automatically deleted
- Clean up the `outputs/` directory periodically
- Each generation creates a new file with unique timestamp

---

## 🔧 Advanced Usage

### Using Example Topics

Click any example to auto-fill the form:
1. Find "💡 Example Topics" section
2. Click on any row
3. Topic, audience, and duration will populate
4. Click "Generate Animation"

### Batch Generation

To generate multiple animations:
1. Generate first animation
2. While it's processing, you can prepare the next one
3. Wait for completion before starting the next
4. Note: Concurrent generation is not supported

### Custom Prompts

For more control, you can:
1. Generate an animation
2. Review the narration and code
3. If not satisfied, regenerate with different parameters
4. Try varying the topic phrasing for different results

### API Access

The Gradio interface also provides an API endpoint:

```python
from gradio_client import Client

client = Client("http://localhost:7860")
result = client.predict(
    topic="Pythagorean Theorem",
    audience="high_school", 
    duration=2.0,
    api_name="/generate"
)
```

---

## 🐛 Troubleshooting

### Port Already in Use

If port 7860 is occupied, edit `app.py` line 522:
```python
interface.launch(
    server_port=7861,  # Change to different port
    ...
)
```

### Slow Generation

Generation speed depends on:
- **API rate limits**: HuggingFace may throttle requests
- **Model availability**: Some models load slower
- **Rendering complexity**: More objects = longer render
- **System resources**: CPU, RAM, disk speed

**To speed up:**
- Use shorter durations (1-2 min instead of 5-10)
- Choose simpler topics
- Ensure good internet connection
- Use local GPU if available (advanced)

### Memory Issues

If you encounter out-of-memory errors:
- Close other applications
- Restart the Gradio app
- Use shorter animation durations
- Reduce rendering quality (requires code changes)

### Connection Timeout

If API calls timeout:
- Check internet connection
- Verify API keys are valid
- Try again in a few minutes (may be temporary API issue)
- Check HuggingFace status page

---

## 📚 Learning Resources

### Understanding Generated Code

The Manim code uses these key components:

```python
from manim import *  # Import Manim library

class MyScene(MovingCameraScene):  # Scene class
    def construct(self):  # Main animation method
        # Create objects
        circle = Circle(radius=1, color=BLUE)
        
        # Animate them
        self.play(Create(circle))
        self.wait(1)
```

**Learn More:**
- [Manim Documentation](https://docs.manim.community/)
- [Manim Tutorial](https://docs.manim.community/en/stable/tutorials.html)
- [Example Gallery](https://docs.manim.community/en/stable/examples.html)

### Improving Narration

Good narration:
- Starts with context ("Today we'll explore...")
- Explains step-by-step
- Uses analogies and examples
- Ends with summary or takeaway

Review the generated narration script and note what works well for future reference.

---

## 🎓 Educational Best Practices

### For Teachers

- **Preview First**: Generate and review before showing to students
- **Customize**: Use generated content as a starting point
- **Supplement**: Combine with traditional teaching methods
- **Assess**: Use the quiz questions for homework or tests
- **Iterate**: Regenerate if the first attempt isn't perfect

### For Students

- **Active Learning**: Pause and try problems yourself
- **Take Notes**: Write down key points from narration
- **Rewatch**: Complex topics benefit from multiple viewings
- **Practice**: Do the quiz questions to test understanding
- **Ask Questions**: Use as supplementary material, not replacement for asking teachers

### For Content Creators

- **Brand Consistency**: Edit narration/code for your style
- **Quality Control**: Always review before publishing
- **Add Value**: Enhance with your own insights
- **Credit**: Mention AI-generated if appropriate
- **Engage**: Ask viewers questions, encourage comments

---

## 🔐 Privacy & Security

### Data Handling
- Topics and generated content are sent to external APIs (HuggingFace, ElevenLabs)
- No content is stored by NeuroAnim except locally on your machine
- API providers have their own privacy policies
- Generated videos are saved only to your local `outputs/` directory

### API Key Security
- Never share your `.env` file
- Don't commit API keys to version control
- Keep keys confidential
- Rotate keys periodically
- Use read-only or limited scopes when available

### Sharing Generated Content
- Videos are yours to use as you see fit
- Be aware AI-generated content may have limitations
- Verify accuracy before using in critical contexts
- Consider licensing if publishing commercially

---

## 🆘 Getting Help

### Check Logs
The console where you ran `python app.py` shows detailed logs:
```
2024-01-20 14:30:22 - INFO - Generating speech with elevenlabs...
2024-01-20 14:30:25 - ERROR - TTS failed: API key invalid
```

### Common Error Messages

**"HUGGINGFACE_API_KEY not set"**
- Add key to `.env` file and restart

**"Rendering failed"**
- Check Manim code tab for syntax errors
- Verify Manim and FFmpeg are installed

**"TTS generation failed"**
- Check ElevenLabs API key or rely on fallback
- Verify narration text is valid

**"All TTS providers failed"**
- Check both API keys
- Install gtts: `pip install gtts`

### Contact & Support
- Check the GitHub repository Issues page
- Review IMPROVEMENTS.md for known issues
- Consult Manim Community forums for rendering issues
- Check HuggingFace/ElevenLabs documentation for API issues

---

## 🎉 Success Stories

Once you've mastered the basics, you can:
- Create a library of math explainer videos
- Build a YouTube channel with AI-assisted content
- Develop course materials for online classes
- Generate study aids for exams
- Prototype animation ideas before manual creation

**Happy animating! 🚀**

---

*Last updated: 2024*  
*For more information, see README.md and IMPROVEMENTS.md*