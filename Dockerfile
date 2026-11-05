# ------------------------------------------------------------------------------
# Autonomous Instagram Reels AI Agent - Production Dockerfile
# ------------------------------------------------------------------------------
FROM python:3.11-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies (FFmpeg for video encoding, fonts for subtitles)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-freefont-ttf \
    fonts-dejavu \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure storage and output directories exist
RUN mkdir -p storage output/reels output/audio output/scripts output/frames "insta content" logs

# Default command: Run 24/7 continuous autonomous publishing daemon
CMD ["python", "app/autonomous/daily_algorithm_publisher.py", "--daemon"]
