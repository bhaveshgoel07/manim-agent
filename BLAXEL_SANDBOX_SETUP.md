# Blaxel Sandbox Setup for Manim + FFmpeg

This guide walks you through creating and deploying a custom Blaxel sandbox with Manim and FFmpeg pre-installed for rendering animations in the cloud.

## Overview

Instead of installing Manim and FFmpeg at runtime (which is slow and unreliable), we create a custom Docker image with all dependencies pre-installed. This image is then deployed to Blaxel as a sandbox template that can be instantiated on-demand for rendering.

## Why Custom Image?

- **Faster**: No installation overhead at runtime
- **Reliable**: Pre-tested environment with all dependencies
- **FFmpeg Support**: System-level dependencies properly configured
- **LaTeX Support**: Optional but recommended for mathematical animations

## Prerequisites

1. **Docker** installed locally (for testing)
2. **Blaxel CLI** installed: `npm install -g @blaxel/cli`
3. **Blaxel Account** with API key from [blaxel.ai](https://blaxel.ai)
4. **Environment Variables** set:
   ```bash
   export BLAXEL_API_KEY="your_api_key_here"
   export BL_WORKSPACE="your_workspace_id"  # Optional
   ```

## Step 1: Build and Test Locally

Before deploying to Blaxel, test the image locally:

```bash
# Build the Docker image
make -f Makefile.sandbox build

# Run the container locally
make -f Makefile.sandbox run

# Test the sandbox API (in another terminal)
make -f Makefile.sandbox test

# View logs
make -f Makefile.sandbox logs

# Stop the container
make -f Makefile.sandbox stop
```

### Manual Testing

You can also test manually:

```bash
# 1. Check Manim installation
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{
    "command": "python3 -c \"import manim; print(manim.__version__)\"",
    "waitForCompletion": true
  }'

# 2. Check FFmpeg installation
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{
    "command": "ffmpeg -version",
    "waitForCompletion": true
  }'

# 3. Test a simple Manim render
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{
    "command": "python3 -c \"from manim import *; print(\\\"Manim import successful\\\")\"",
    "waitForCompletion": true
  }'
```

## Step 2: Deploy to Blaxel

Once local testing is successful, deploy to Blaxel:

```bash
# Login to Blaxel (if not already logged in)
bl login

# Deploy the sandbox template
make -f Makefile.sandbox deploy

# Or manually:
bl deploy
```

This will:
1. Build your Docker image
2. Push it to Blaxel's registry
3. Create a sandbox template named based on your project

## Step 3: Get the Image ID

After deployment, retrieve your custom image ID:

```bash
# List your sandboxes
bl get sandboxes

# Get specific sandbox details with image ID
bl get sandbox manim-sandbox -ojson | jq -r '.[0].spec.runtime.image'
```

The output will look something like:
```
blaxel/your-workspace/manim-sandbox:latest
```

**Save this image ID** - you'll need it in the next step.

## Step 4: Update Renderer Code

Update the renderer to use your custom image instead of the generic one.

Open `mcp_servers/renderer.py` and find the line around line 440:

```python
sandbox = await SandboxInstance.create(
    {
        "name": f"manim-render-{sanitized_scene_name}",
        "image": "blaxel/py-app:latest",  # Change this line
        "memory": 4096,
    }
)
```

Replace `"blaxel/py-app:latest"` with your custom image ID:

```python
sandbox = await SandboxInstance.create(
    {
        "name": f"manim-render-{sanitized_scene_name}",
        "image": "blaxel/your-workspace/manim-sandbox:latest",  # Your custom image
        "memory": 4096,
    }
)
```

**Better approach**: Use an environment variable:

```python
import os

MANIM_SANDBOX_IMAGE = os.getenv(
    "MANIM_SANDBOX_IMAGE", 
    "blaxel/your-workspace/manim-sandbox:latest"
)

sandbox = await SandboxInstance.create(
    {
        "name": f"manim-render-{sanitized_scene_name}",
        "image": MANIM_SANDBOX_IMAGE,
        "memory": 4096,
    }
)
```

Then add to your `.env`:
```bash
MANIM_SANDBOX_IMAGE=blaxel/your-workspace/manim-sandbox:latest
```

## Step 5: Test End-to-End

Now test the complete pipeline:

```bash
# Run your animation generation
python main_new.py
```

Or if using Gradio:
```bash
python app.py
```

The system should now:
1. Create a sandbox using your custom image
2. Upload the Manim code
3. Execute the render command (Manim and FFmpeg already available)
4. Download the rendered video

## Configuration Options

### Memory Allocation

For complex animations, you may need more memory:

```python
sandbox = await SandboxInstance.create(
    {
        "name": f"manim-render-{sanitized_scene_name}",
        "image": MANIM_SANDBOX_IMAGE,
        "memory": 8192,  # Increased from 4096
    }
)
```

### Timeout Settings

Adjust timeouts for longer renders:

```python
render_result = await sandbox.process.exec({
    "name": "render-manim",
    "command": cmd,
    "wait_for_completion": True,
    "timeout": 600000,  # 10 minutes (in milliseconds)
})
```

### Custom LaTeX Packages

If you need additional LaTeX packages, update the Dockerfile:

```dockerfile
RUN apt-get install -y \
    texlive-full \  # Install full LaTeX distribution
    && rm -rf /var/lib/apt/lists/*
```

Then rebuild and redeploy:
```bash
make -f Makefile.sandbox rebuild
make -f Makefile.sandbox deploy
```

## Troubleshooting

### Issue: "Sandbox creation failed"

**Solution**: Check your API key and workspace:
```bash
echo $BLAXEL_API_KEY
echo $BL_WORKSPACE
```

Re-login if needed:
```bash
bl login
```

### Issue: "Image not found"

**Solution**: Verify the image was deployed:
```bash
bl get sandboxes
```

If not listed, redeploy:
```bash
bl deploy
```

### Issue: "Manim not found in sandbox"

**Solution**: Verify the image has Manim:
```bash
# Connect to a running sandbox
bl connect sandbox your-sandbox-name

# Inside the sandbox, test:
python3 -c "import manim; print(manim.__version__)"
```

### Issue: "FFmpeg not found"

**Solution**: Similar to above, verify FFmpeg:
```bash
bl connect sandbox your-sandbox-name
ffmpeg -version
```

### Issue: "Render timeout"

**Solutions**:
1. Increase memory allocation (try 8192 MB)
2. Increase timeout value
3. Simplify the animation
4. Use lower quality settings

### Issue: "Build fails locally"

**Solution**: Check Docker logs:
```bash
docker logs manim-sandbox-test
```

Common issues:
- Missing entrypoint.sh file (copy it first)
- Permissions on entrypoint.sh (should be executable)
- Docker daemon not running

## Cost Optimization

To minimize costs:

1. **Use TTL policies**: Sandboxes auto-delete when idle
   ```python
   sandbox = await SandboxInstance.create({
       "name": f"manim-render-{sanitized_scene_name}",
       "image": MANIM_SANDBOX_IMAGE,
       "memory": 4096,
       "lifecycle": {
           "expiration_policies": [
               {"type": "ttl-idle", "value": "5m", "action": "delete"}
           ]
       }
   })
   ```

2. **Delete after use**: Explicitly delete sandboxes when done
   ```python
   try:
       # Render animation
       pass
   finally:
       await SandboxInstance.delete(sandbox.metadata.name)
   ```

3. **Reuse sandboxes**: For batch processing, reuse the same sandbox

## Advanced: Multiple Sandbox Versions

You can maintain multiple versions:

```bash
# Tag with version
docker build -f Dockerfile.sandbox -t manim-sandbox:v1.0 .

# Deploy specific version
bl deploy --tag v1.0
```

Then specify in code:
```python
"image": "blaxel/your-workspace/manim-sandbox:v1.0"
```

## Next Steps

1. ✅ Build and test locally
2. ✅ Deploy to Blaxel
3. ✅ Update renderer code with image ID
4. ✅ Test end-to-end rendering
5. ✅ Configure cost optimization
6. 🎉 Start generating animations!

## Resources

- [Blaxel Sandboxes Documentation](https://docs.blaxel.ai/sandboxes)
- [Blaxel CLI Reference](https://docs.blaxel.ai/cli)
- [Manim Documentation](https://docs.manim.community/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)

## Support

If you encounter issues:
1. Check the Blaxel dashboard for sandbox logs
2. Review the deployment logs: `bl logs`
3. Join Blaxel Discord/Support channels
4. Check GitHub issues for similar problems