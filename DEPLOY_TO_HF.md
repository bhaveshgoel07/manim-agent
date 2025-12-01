# 🚀 Quick Deployment Guide for Hugging Face Spaces

This is a quick reference for deploying NeuroAnim to Hugging Face Spaces.

## Prerequisites

✅ You have created a Hugging Face Space
✅ You have your API keys ready

## Step-by-Step Deployment

### 1. Create Your Space

1. Go to https://huggingface.co/spaces
2. Click **"Create new Space"**
3. Fill in:
   - **Owner**: Your username
   - **Space name**: `neuroanim` (or your choice)
   - **License**: MIT
   - **Select the SDK**: Gradio
   - **Space hardware**: CPU basic (free) - can upgrade later
4. Click **"Create Space"**

### 2. Configure Secrets (IMPORTANT!)

1. Go to your Space → **Settings** → **Variables and secrets**
2. Add these secrets:

   ```
   HUGGINGFACE_API_KEY = your_huggingface_token_here
   ```
   
   Optional (but recommended):
   ```
   ELEVENLABS_API_KEY = your_elevenlabs_key_here
   BLAXEL_API_KEY = your_blaxel_key_here
   MANIM_SANDBOX_IMAGE = your_sandbox_image_here
   ```

3. Click **"Save"** for each secret

### 3. Push Your Code

You have two options:

#### Option A: Using Git (Recommended)

```bash
# Navigate to your project
cd "/media/bhaves/Volume 2/manim-agent"

# Add HF Space as remote (replace YOUR_USERNAME and YOUR_SPACE_NAME)
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME

# Create a deployment branch (optional but recommended)
git checkout -b hf-deploy

# Copy the HF-specific README
cp README_HF.md README.md

# Add and commit deployment files
git add requirements.txt README.md app.py orchestrator.py
git add mcp_servers/ utils/ neuroanim/ manim_mcp/
git add pyproject.toml .gitignore
git commit -m "Initial Hugging Face Space deployment"

# Push to HF Space
git push space hf-deploy:main
```

#### Option B: Web Upload (Easier but slower)

1. Go to your Space → **Files and versions** tab
2. Click **"Add file"** → **"Upload files"**
3. Upload these files/folders:
   - `app.py` ⭐ (main entry point)
   - `requirements.txt` ⭐ (dependencies)
   - `README_HF.md` → rename to `README.md` ⭐
   - `orchestrator.py`
   - `pyproject.toml`
   - Folders: `mcp_servers/`, `utils/`, `neuroanim/`, `manim_mcp/`
4. Click **"Commit changes to main"**

### 4. Monitor Build

1. Go to your Space → **App** tab
2. Watch the build logs (bottom of page)
3. Wait 5-10 minutes for first build
4. Look for: `Running on public URL: https://...`

### 5. Test Your Space

Once deployed:
1. Enter a topic: "Pythagorean Theorem"
2. Select audience: "high_school"
3. Duration: 2 minutes
4. Quality: "Medium"
5. Click **"Generate Animation"**
6. Wait for generation (may take 3-5 minutes)
7. Verify video plays and downloads work

## Troubleshooting

### Build Fails
- Check **Logs** tab for errors
- Verify `requirements.txt` is correct
- Ensure all files are uploaded

### "API Key Not Set" Error
- Go to Settings → Variables and secrets
- Add `HUGGINGFACE_API_KEY`
- Restart Space (Settings → Factory reboot)

### Slow or Timeout
- Upgrade hardware: Settings → Change hardware
- Try GPU T4 for faster rendering
- Reduce animation duration for testing

### Import Errors
- Check all folders are uploaded (`mcp_servers/`, `utils/`, etc.)
- Verify folder structure matches local

## Hardware Recommendations

| Hardware | Cost | Best For |
|----------|------|----------|
| CPU basic | Free | Testing, demos |
| CPU upgrade | $0.03/hr | Light usage |
| GPU T4 | $0.60/hr | Production, fast rendering |

## Next Steps

✅ Share your Space URL with others
✅ Enable community features (Settings → Visibility)
✅ Add example videos to README
✅ Monitor usage in Analytics tab

## Getting Your Space URL

Your Space will be available at:
```
https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
```

Share this link to let others use your animation generator!

---

Need help? Check the full deployment guide in `implementation_plan.md`
