#!/usr/bin/env bash
# ==============================================================================
# Autonomous Instagram Agent - 1-Click Ubuntu / Debian Server Setup Script
# ==============================================================================
set -e

echo "=== [1/5] Updating system packages ==="
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv ffmpeg git curl fonts-dejavu fonts-freefont-ttf

PROJECT_DIR="/opt/instagram_agent"

echo "=== [2/5] Creating application directory at $PROJECT_DIR ==="
sudo mkdir -p "$PROJECT_DIR"
sudo cp -r . "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo "=== [3/5] Setting up Python virtual environment ==="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [4/5] Preparing directories ==="
mkdir -p storage logs output/reels output/audio output/scripts output/frames "insta content"

echo "=== [5/5] Configuring systemd 24/7 background service ==="
sudo cp deploy/instagram_agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable instagram_agent
sudo systemctl restart instagram_agent

echo ""
echo "======================================================================"
echo "  SUCCESS! Autonomous Instagram Agent is now LIVE in the background!"
echo "======================================================================"
echo "To check live service status:"
echo "  sudo systemctl status instagram_agent"
echo ""
echo "To view live real-time logs:"
echo "  tail -f /opt/instagram_agent/logs/systemd_daemon.log"
echo ""
echo "To stop or restart:"
echo "  sudo systemctl stop instagram_agent"
echo "  sudo systemctl restart instagram_agent"
echo "======================================================================"
