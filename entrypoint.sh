#!/bin/sh

# Entrypoint script for Blaxel Manim sandbox
# This script initializes the sandbox environment with Manim and FFmpeg

echo "Starting Blaxel Manim Sandbox..."

# Start the sandbox API (required by Blaxel)
/usr/local/bin/sandbox-api &

# Wait for sandbox API to be ready
echo "Waiting for sandbox API..."
while ! nc -z localhost 8080; do
  sleep 0.1
done

echo "Sandbox API ready"

# Initialize the environment
echo "Setting up Manim environment..."

# Create working directories
mkdir -p /app/animations
mkdir -p /app/outputs
mkdir -p /tmp/media

# Verify installations
echo "Verifying Python installation..."
python3 --version

echo "Verifying Manim installation..."
python3 -c "import manim; print(f'Manim version: {manim.__version__}')" || echo "WARNING: Manim import failed"

echo "Verifying FFmpeg installation..."
ffmpeg -version | head -n 1

echo "Environment setup complete!"
echo "Ready to render animations..."

# Keep the container running
wait
