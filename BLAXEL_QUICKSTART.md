# Blaxel Sandbox Quick Start

Quick reference for deploying and using the custom Manim + FFmpeg sandbox.

## Prerequisites

```bash
# Install Blaxel CLI
npm install -g @blaxel/cli

# Login to Blaxel
bl login

# Set environment variables
export BLAXEL_API_KEY="your_api_key_here"
```

## One-Command Deployment

```bash
# Automated deployment (recommended)
./deploy_sandbox.sh
```

This will:
- ✅ Check prerequisites
- ✅ Build Docker image locally
- ✅ Test the image
- ✅ Deploy to Blaxel
- ✅ Update your .env file

## Manual Deployment Steps

### 1. Build & Test Locally

```bash
# Build the image
docker build -f Dockerfile.sandbox -t manim-sandbox .

# Run locally
docker run -d --name manim-sandbox-test -p 8080:8080 manim-sandbox

# Test the API
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{"command": "manim --version", "waitForCompletion": true}'

# Clean up
docker stop manim-sandbox-test && docker rm manim-sandbox-test
```

### 2. Deploy to Blaxel

```bash
# Deploy
bl deploy

# Check status
bl get sandboxes

# Get your image ID
bl get sandbox manim-sandbox -ojson | jq -r '.[0].spec.runtime.image'
```

### 3. Configure Your App

Add to `.env`:
```bash
MANIM_SANDBOX_IMAGE=blaxel/your-workspace/manim-sandbox:latest
BLAXEL_API_KEY=your_api_key_here
```

## Common Commands

### Managing Sandboxes

```bash
# List all sandboxes
bl get sandboxes

# Get specific sandbox
bl get sandbox <name>

# Delete a sandbox
bl delete sandbox <name>

# Connect to sandbox terminal
bl connect sandbox <name>
```

### Testing Your Deployment

```bash
# Test Manim in deployed sandbox
bl connect sandbox your-sandbox-name
# Then inside the sandbox:
manim --version
python3 -c "import manim; print(manim.__version__)"
```

### Viewing Logs

```bash
# View deployment logs
bl logs

# Watch sandbox status
bl get sandbox <name> --watch
```

## Usage in Python

```python
import os
from blaxel.core import SandboxInstance

# Get image from environment
MANIM_SANDBOX_IMAGE = os.getenv("MANIM_SANDBOX_IMAGE")

# Create sandbox
sandbox = await SandboxInstance.create({
    "name": "my-render-job",
    "image": MANIM_SANDBOX_IMAGE,
    "memory": 4096,
})

# Execute Manim render
result = await sandbox.process.exec({
    "command": "manim -qm scene.py MyScene",
    "wait_for_completion": True,
    "timeout": 600000,  # 10 minutes
})

# Clean up
await SandboxInstance.delete("my-render-job")
```

## Troubleshooting

### "Image not found"
```bash
# Verify deployment
bl get sandboxes

# Redeploy if needed
bl deploy
```

### "Authentication failed"
```bash
# Re-login
bl login

# Verify
bl whoami
```

### "Sandbox creation timeout"
```bash
# Increase timeout in code or try different region
sandbox = await SandboxInstance.create({
    "name": "my-render-job",
    "image": MANIM_SANDBOX_IMAGE,
    "memory": 4096,
    "region": "us-east-1",  # Try different region
})
```

### Local Docker issues
```bash
# Check Docker is running
docker info

# View build logs
docker build -f Dockerfile.sandbox -t manim-sandbox . 2>&1 | tee build.log

# Test entrypoint
docker run --rm manim-sandbox cat /entrypoint.sh
```

## Performance Tips

1. **Reuse sandboxes** for multiple renders
2. **Set TTL policies** to auto-cleanup
3. **Adjust memory** based on animation complexity
4. **Use lower quality** for testing

## Resource Limits

| Setting | Recommended | Maximum |
|---------|-------------|---------|
| Memory | 4096 MB | 8192 MB |
| Timeout | 600s (10min) | Varies |
| Quality | medium | production_quality |

## Next Steps

- Run your first animation: `python main_new.py`
- Launch Gradio UI: `python app.py`
- Read full guide: `BLAXEL_SANDBOX_SETUP.md`

## Support

- 📚 [Blaxel Docs](https://docs.blaxel.ai)
- 💬 [Blaxel Discord](https://discord.gg/blaxel)
- 🐛 [Report Issues](https://github.com/your-repo/issues)