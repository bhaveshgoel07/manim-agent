# Blaxel Sandbox Dockerfile for Manim + FFmpeg
# This creates a custom sandbox image with all dependencies pre-installed

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy sandbox API (required for Blaxel sandboxes)
COPY --from=ghcr.io/blaxel-ai/sandbox:latest /sandbox-api /usr/local/bin/sandbox-api

# Install system dependencies including FFmpeg, LaTeX, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core utilities
    curl \
    ca-certificates \
    netcat-openbsd \
    git \
    build-essential \
    # FFmpeg and media processing
    ffmpeg \
    # LaTeX for Manim (optional but recommended)
    texlive \
    texlive-latex-extra \
    texlive-fonts-extra \
    texlive-latex-recommended \
    texlive-science \
    texlive-fonts-recommended \
    # Manim system dependencies
    libcairo2-dev \
    libpango1.0-dev \
    pkg-config \
    python3-dev \
    # Additional utilities
    sox \
    libsox-fmt-mp3 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install uv for faster package management
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir uv

# Install Manim and core Python dependencies
RUN pip install --no-cache-dir \
    manim>=0.18.1 \
    numpy>=1.24.0 \
    Pillow>=10.0.0 \
    scipy \
    && pip cache purge

# Verify installations
RUN python3 -c "import manim; print(f'Manim version: {manim.__version__}')" \
    && ffmpeg -version \
    && echo "All dependencies installed successfully!"

# Create media output directory
RUN mkdir -p /tmp/media

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose sandbox API port
EXPOSE 8080

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
