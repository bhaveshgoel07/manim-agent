# Migration Guide: Local to Blaxel Cloud Rendering

This document explains how the Manim rendering has been migrated from local execution to Blaxel cloud sandboxes with pre-installed dependencies.

## Table of Contents

- [Overview](#overview)
- [Why Migrate?](#why-migrate)
- [What Changed](#what-changed)
- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Migration Steps](#migration-steps)
- [Architecture Comparison](#architecture-comparison)
- [Configuration Changes](#configuration-changes)
- [Testing](#testing)
- [Rollback Plan](#rollback-plan)
- [FAQ](#faq)

## Overview

**Before**: Manim code execution and video rendering happened on your local machine.

**After**: Rendering happens in Blaxel cloud sandboxes with Manim and FFmpeg pre-installed.

**Why**: Better security, scalability, and no local dependency management.

## Why Migrate?

### Benefits of Blaxel Cloud Rendering

1. **Security** 🔒
   - Isolated execution environment
   - No risk of malicious code affecting your system
   - AI-generated code runs in sandboxed containers

2. **No Local Dependencies** 📦
   - Don't need to install Manim locally
   - Don't need FFmpeg on your machine
   - Don't need LaTeX packages
   - Works on any OS without configuration

3. **Scalability** 📈
   - Parallel rendering of multiple animations
   - No resource constraints from local machine
   - Auto-scaling based on workload

4. **Consistency** ✅
   - Same environment every time
   - No "works on my machine" issues
   - Reproducible builds

5. **Resource Management** 💪
   - Heavy rendering doesn't slow down your computer
   - Can allocate more memory (4GB-8GB) as needed
   - Automatic cleanup of temporary files

## What Changed

### New Files Added

```
manim-agent/
├── Dockerfile.sandbox          # Custom Docker image definition
├── entrypoint.sh               # Sandbox initialization script
├── Makefile.sandbox            # Build automation
├── deploy_sandbox.sh           # Automated deployment script
├── BLAXEL_SANDBOX_SETUP.md     # Detailed setup guide
├── BLAXEL_QUICKSTART.md        # Quick reference
└── MIGRATION_TO_BLAXEL.md      # This file
```

### Modified Files

1. **mcp_servers/renderer.py**
   - Added `MANIM_SANDBOX_IMAGE` environment variable
   - Uses custom image instead of `blaxel/py-app:latest`
   - No more runtime installation of Manim/FFmpeg

2. **.gitignore**
   - Added Docker build artifacts
   - Added backup files from scripts

### Environment Variables

New required variable:
```bash
MANIM_SANDBOX_IMAGE=blaxel/your-workspace/manim-sandbox:latest
```

Existing variables:
```bash
BLAXEL_API_KEY=your_api_key_here
BL_WORKSPACE=your_workspace_id  # Optional
```

## The Problem

### Old Approach: Runtime Installation

```python
# Old code in renderer.py
sandbox = await SandboxInstance.create({
    "name": f"manim-render-{scene_name}",
    "image": "blaxel/py-app:latest",  # Generic Python image
    "memory": 4096,
})

# Then install dependencies at runtime (slow and unreliable)
await sandbox.process.exec({
    "command": "pip install manim",
    "wait_for_completion": True,
})
```

### Issues with Runtime Installation

1. **Slow** ⏱️
   - Installing Manim takes 2-3 minutes every time
   - FFmpeg installation requires apt-get
   - LaTeX packages are huge downloads

2. **Unreliable** ❌
   - Network failures during pip install
   - Version conflicts
   - Missing system dependencies
   - Race conditions with process management

3. **No FFmpeg** 🚫
   - Generic images don't have FFmpeg
   - Installing FFmpeg requires root access
   - System dependencies complex to manage

4. **Wasteful** 💸
   - Pay for installation time every render
   - Same packages downloaded repeatedly
   - No caching between renders

## The Solution

### Custom Docker Image with Pre-installed Dependencies

```dockerfile
# Dockerfile.sandbox
FROM python:3.12-slim

# Install FFmpeg, LaTeX, and system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    texlive \
    libcairo2-dev \
    # ... other dependencies

# Pre-install Manim
RUN pip install manim>=0.18.1

# Copy Blaxel sandbox API
COPY --from=ghcr.io/blaxel-ai/sandbox:latest /sandbox-api /usr/local/bin/sandbox-api

ENTRYPOINT ["/entrypoint.sh"]
```

### Advantages

1. **Fast** ⚡
   - Dependencies already installed
   - Sandbox ready in seconds
   - Start rendering immediately

2. **Reliable** ✅
   - Pre-tested environment
   - Consistent versions
   - No installation failures

3. **Complete** 🎯
   - FFmpeg included
   - LaTeX support
   - All system dependencies

4. **Cost-effective** 💰
   - Pay only for rendering time
   - No repeated installations
   - Efficient resource usage

## Migration Steps

### Step 1: Prerequisites

Ensure you have:
- Docker installed locally
- Blaxel CLI: `npm install -g @blaxel/cli`
- Blaxel API key from [blaxel.ai](https://blaxel.ai)

### Step 2: Set Environment Variables

```bash
# Add to your .env or shell profile
export BLAXEL_API_KEY="your_api_key_here"
export BL_WORKSPACE="your_workspace_id"  # Optional
```

### Step 3: Deploy Custom Sandbox (Automated)

```bash
# Run the automated deployment script
./deploy_sandbox.sh
```

This script will:
1. ✅ Check all prerequisites
2. ✅ Build Docker image locally
3. ✅ Test the image
4. ✅ Deploy to Blaxel
5. ✅ Retrieve your image ID
6. ✅ Update your .env file

### Step 4: Deploy Custom Sandbox (Manual)

If you prefer manual steps:

```bash
# 1. Build the image
docker build -f Dockerfile.sandbox -t manim-sandbox .

# 2. Test locally
docker run -d --name test -p 8080:8080 manim-sandbox
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{"command": "manim --version", "waitForCompletion": true}'
docker stop test && docker rm test

# 3. Login to Blaxel
bl login

# 4. Deploy
bl deploy

# 5. Get your image ID
bl get sandboxes -ojson | jq -r '.[0].spec.runtime.image'
```

### Step 5: Configure Your Application

Add to your `.env` file:
```bash
MANIM_SANDBOX_IMAGE=blaxel/your-workspace/manim-sandbox:latest
```

The renderer code automatically reads this variable:
```python
# This is already in renderer.py
MANIM_SANDBOX_IMAGE = os.getenv(
    "MANIM_SANDBOX_IMAGE",
    "blaxel/py-app:latest",  # Fallback
)
```

### Step 6: Test End-to-End

```bash
# Run your animation pipeline
python main_new.py

# Or launch Gradio UI
python app.py
```

### Step 7: Verify Success

Check that:
- [ ] Sandbox creates quickly (< 10 seconds)
- [ ] No "Installing Manim..." messages in logs
- [ ] Rendering completes successfully
- [ ] Video output is correct
- [ ] FFmpeg processing works

## Architecture Comparison

### Before: Local + Runtime Installation

```
┌─────────────────────────────────────────────────────────┐
│  Your Machine                                           │
│                                                         │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────┐  │
│  │   Python    │───▶│  MCP Server  │───▶│  Manim   │  │
│  │   Script    │    │  (renderer)  │    │  Local   │  │
│  └─────────────┘    └──────────────┘    └──────────┘  │
│                            │                            │
│                            ▼                            │
│                     ┌──────────────┐                    │
│                     │   Blaxel     │                    │
│                     │  Sandbox API │                    │
│                     └──────────────┘                    │
│                            │                            │
└────────────────────────────┼────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  Blaxel Cloud                │
              │                              │
              │  ┌────────────────────────┐  │
              │  │  Generic Python Image  │  │
              │  │  (No Manim/FFmpeg)     │  │
              │  └────────────────────────┘  │
              │           │                  │
              │           ▼                  │
              │  ⏱️ Install Manim (3 min)    │
              │  ⏱️ Install FFmpeg (fail)    │
              │  ❌ Render (error)           │
              └──────────────────────────────┘
```

### After: Cloud with Pre-installed Dependencies

```
┌─────────────────────────────────────────────────────────┐
│  Your Machine                                           │
│                                                         │
│  ┌─────────────┐    ┌──────────────┐                   │
│  │   Python    │───▶│  MCP Server  │                   │
│  │   Script    │    │  (renderer)  │                   │
│  └─────────────┘    └──────────────┘                   │
│                            │                            │
│                            ▼                            │
│                     ┌──────────────┐                    │
│                     │   Blaxel     │                    │
│                     │  Sandbox API │                    │
│                     └──────────────┘                    │
│                            │                            │
└────────────────────────────┼────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  Blaxel Cloud                │
              │                              │
              │  ┌────────────────────────┐  │
              │  │ Custom Manim Image     │  │
              │  │ ✅ Manim pre-installed  │  │
              │  │ ✅ FFmpeg ready         │  │
              │  │ ✅ LaTeX included       │  │
              │  └────────────────────────┘  │
              │           │                  │
              │           ▼                  │
              │  ⚡ Start (< 10 sec)        │
              │  🎬 Render (works!)         │
              │  ✅ Output video            │
              └──────────────────────────────┘
```

## Configuration Changes

### Environment Variables

| Variable | Before | After | Required |
|----------|--------|-------|----------|
| `BLAXEL_API_KEY` | Optional | **Required** | Yes |
| `BL_WORKSPACE` | N/A | Optional | No |
| `MANIM_SANDBOX_IMAGE` | N/A | **Required** | Yes |

### Code Changes

The renderer code now uses the custom image:

```python
# Before
sandbox = await SandboxInstance.create({
    "name": f"manim-render-{scene_name}",
    "image": "blaxel/py-app:latest",
    "memory": 4096,
})

# After
MANIM_SANDBOX_IMAGE = os.getenv("MANIM_SANDBOX_IMAGE")

sandbox = await SandboxInstance.create({
    "name": f"manim-render-{scene_name}",
    "image": MANIM_SANDBOX_IMAGE,  # Your custom image
    "memory": 4096,
})
```

### Render Flow

```python
# Before: Install then render
1. Create generic sandbox
2. ⏱️ Install Manim (3 minutes)
3. ⏱️ Try to install FFmpeg (fails)
4. Upload code
5. ❌ Render (error - no FFmpeg)

# After: Just render
1. Create custom sandbox (Manim + FFmpeg ready)
2. Upload code
3. ✅ Render (works immediately)
4. Download result
```

## Testing

### Test Local Build

```bash
# Build and test locally
make -f Makefile.sandbox build
make -f Makefile.sandbox run
make -f Makefile.sandbox test
```

Expected output:
```
✓ Manim is installed and working
✓ FFmpeg is installed and working
```

### Test Blaxel Deployment

```bash
# Deploy to Blaxel
bl deploy

# Check deployment
bl get sandboxes

# Test in cloud
bl connect sandbox manim-sandbox
# Inside sandbox:
manim --version
ffmpeg -version
```

### Test Full Pipeline

```bash
# Generate an animation
python main_new.py

# Check logs for:
# - "Creating Blaxel sandbox"
# - No "Installing Manim" messages
# - "Successfully rendered animation"
```

## Rollback Plan

If you need to rollback to local rendering:

### Option 1: Keep Using Cloud but Fallback Image

Remove from `.env`:
```bash
# MANIM_SANDBOX_IMAGE=...  # Comment out
```

The code will fallback to `blaxel/py-app:latest` (but slower).

### Option 2: Complete Rollback to Local

In `mcp_servers/renderer.py`, find the `render_manim_animation` function around line 374:

```python
# Change from:
return await _render_manim_with_sandbox(...)

# To:
return await _render_manim_locally(...)
```

This completely disables Blaxel and uses local Manim.

### Option 3: Environment Flag

You could add a flag to toggle between local and cloud:

```python
USE_CLOUD_RENDERING = os.getenv("USE_CLOUD_RENDERING", "true").lower() == "true"

if USE_CLOUD_RENDERING and BLAXEL_API_KEY:
    return await _render_manim_with_sandbox(...)
else:
    return await _render_manim_locally(...)
```

## FAQ

### Q: Do I need Manim installed locally anymore?

**A:** No! That's the beauty of this approach. Your local machine only needs Python and the Blaxel SDK. All rendering happens in the cloud.

### Q: How much does this cost?

**A:** You pay for sandbox usage time. With pre-installed dependencies, rendering is much faster, so costs are actually lower than the runtime-installation approach.

### Q: Can I still render locally?

**A:** Yes. The local rendering code is still in `_render_manim_locally()`. You can switch back anytime.

### Q: What if Blaxel is down?

**A:** Implement the rollback to local rendering as described above.

### Q: How do I update the sandbox image?

**A:** Rebuild and redeploy:
```bash
# Make changes to Dockerfile.sandbox
# Then:
./deploy_sandbox.sh
```

### Q: Can I use a different base image?

**A:** Yes. Edit `Dockerfile.sandbox` to use any base image. Just ensure the Blaxel sandbox API is included.

### Q: How do I add more LaTeX packages?

**A:** Update `Dockerfile.sandbox`:
```dockerfile
RUN apt-get install -y \
    texlive-full \  # Complete LaTeX distribution
    && rm -rf /var/lib/apt/lists/*
```

Then rebuild and redeploy.

### Q: What about Python package versions?

**A:** They're pinned in the Dockerfile. To update:
```dockerfile
RUN pip install manim==0.18.2  # Specific version
```

### Q: Can I test without deploying?

**A:** Yes! Use the local Docker testing:
```bash
make -f Makefile.sandbox build
make -f Makefile.sandbox run
make -f Makefile.sandbox test
```

### Q: How do I debug render failures?

**A:**
1. Check sandbox logs: `bl logs`
2. Connect to sandbox: `bl connect sandbox <name>`
3. Check process logs in the renderer code
4. Test Manim command manually in sandbox

### Q: Can I run multiple renders in parallel?

**A:** Yes! Each render creates a unique sandbox, so they run in parallel automatically.

## Resources

- **Setup Guide**: `BLAXEL_SANDBOX_SETUP.md` - Detailed setup instructions
- **Quick Start**: `BLAXEL_QUICKSTART.md` - Command reference
- **Blaxel Docs**: https://docs.blaxel.ai
- **Manim Docs**: https://docs.manim.community/

## Support

If you encounter issues:

1. Check this migration guide
2. Review `BLAXEL_SANDBOX_SETUP.md` troubleshooting section
3. Test locally first: `make -f Makefile.sandbox test`
4. Verify environment variables: `echo $MANIM_SANDBOX_IMAGE`
5. Check Blaxel status: `bl get sandboxes`

## Next Steps

After successful migration:

1. ✅ Remove local Manim installation (optional)
2. ✅ Update your documentation
3. ✅ Train team on new workflow
4. ✅ Set up CI/CD with Blaxel
5. ✅ Monitor usage and costs
6. ✅ Optimize sandbox memory/timeout settings

---

**Migration Complete!** 🎉

You're now rendering animations in the cloud with Blaxel sandboxes. Enjoy faster, more reliable, and more secure animation generation!