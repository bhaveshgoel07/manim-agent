#!/bin/bash

# NeuroAnim Hugging Face Spaces Deployment Script
# This script helps you deploy your application to HF Spaces

set -e

echo "🚀 NeuroAnim - Hugging Face Spaces Deployment"
echo "=============================================="
echo ""

# Check if git is initialized
if [ ! -d .git ]; then
    echo "❌ Error: Not a git repository. Please run 'git init' first."
    exit 1
fi

# Get HF Space details
echo "📝 Please provide your Hugging Face Space details:"
echo ""
read -p "Enter your HF username: " HF_USERNAME
read -p "Enter your Space name (e.g., neuroanim): " SPACE_NAME

if [ -z "$HF_USERNAME" ] || [ -z "$SPACE_NAME" ]; then
    echo "❌ Error: Username and Space name are required."
    exit 1
fi

SPACE_URL="https://huggingface.co/spaces/${HF_USERNAME}/${SPACE_NAME}"
echo ""
echo "📍 Your Space URL will be: $SPACE_URL"
echo ""

# Check if remote already exists
if git remote get-url space &> /dev/null; then
    echo "⚠️  Remote 'space' already exists. Removing it..."
    git remote remove space
fi

# Add HF Space as remote
echo "🔗 Adding Hugging Face Space as git remote..."
git remote add space "https://huggingface.co/spaces/${HF_USERNAME}/${SPACE_NAME}"

# Create deployment branch
echo "🌿 Creating deployment branch..."
git checkout -b hf-deploy 2>/dev/null || git checkout hf-deploy

# Copy HF-specific README
echo "📄 Preparing README for Hugging Face..."
cp README_HF.md README.md

# Stage deployment files
echo "📦 Staging files for deployment..."
git add requirements.txt README.md app.py orchestrator.py pyproject.toml .gitignore
git add mcp_servers/ utils/ neuroanim/ manim_mcp/ 2>/dev/null || true

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "ℹ️  No changes to commit. Files may already be staged."
else
    # Commit changes
    echo "💾 Committing changes..."
    git commit -m "Deploy to Hugging Face Spaces

- Add requirements.txt for HF Spaces
- Add HF-specific README with YAML frontmatter
- Include all necessary source files and modules
"
fi

# Push to HF Space
echo ""
echo "🚀 Ready to push to Hugging Face Spaces!"
echo ""
echo "⚠️  IMPORTANT: Before pushing, make sure you have:"
echo "   1. Created the Space at: https://huggingface.co/spaces"
echo "   2. Added HUGGINGFACE_API_KEY in Space Settings → Secrets"
echo ""
read -p "Have you completed the above steps? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo ""
    echo "📋 Next steps:"
    echo "   1. Go to https://huggingface.co/spaces"
    echo "   2. Click 'Create new Space'"
    echo "   3. Set Space name to: $SPACE_NAME"
    echo "   4. Select SDK: Gradio"
    echo "   5. Go to Settings → Variables and secrets"
    echo "   6. Add HUGGINGFACE_API_KEY secret"
    echo "   7. Run this script again"
    echo ""
    exit 0
fi

echo ""
echo "🚀 Pushing to Hugging Face Spaces..."
echo ""

# Push to HF Space
if git push space hf-deploy:main; then
    echo ""
    echo "✅ Successfully deployed to Hugging Face Spaces!"
    echo ""
    echo "🌐 Your Space URL: $SPACE_URL"
    echo ""
    echo "📊 Next steps:"
    echo "   1. Visit your Space URL to see the build progress"
    echo "   2. Check the Logs tab for any errors"
    echo "   3. Wait 5-10 minutes for the first build"
    echo "   4. Test your animation generator!"
    echo ""
    echo "💡 Tip: You can upgrade hardware in Settings if rendering is slow"
    echo ""
else
    echo ""
    echo "❌ Push failed. This might be because:"
    echo "   1. The Space doesn't exist yet - create it at https://huggingface.co/spaces"
    echo "   2. You need to authenticate with HF CLI: huggingface-cli login"
    echo "   3. The Space name or username is incorrect"
    echo ""
    echo "🔧 To authenticate with Hugging Face:"
    echo "   pip install huggingface_hub"
    echo "   huggingface-cli login"
    echo ""
    exit 1
fi

# Return to original branch
echo "🔄 Returning to main branch..."
git checkout main 2>/dev/null || git checkout master 2>/dev/null || true

echo ""
echo "✨ Deployment complete! Happy animating! 🎬"
