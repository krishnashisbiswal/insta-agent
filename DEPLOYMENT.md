# Live Server Deployment Guide (24/7 Autonomous Instagram Agent)

This guide walks you through deploying your autonomous Instagram AI agent onto a cloud server so it runs **24/7 automatically**, discovers trending topics, records studio human voiceovers via ElevenLabs, renders 8K cinematic reels with your `@neovibestore.in` watermark, and posts strictly once a day at peak Instagram algorithm velocity without keeping your computer on.

---

## Recommended Server Requirements

- **OS:** Ubuntu 22.04 LTS or 24.04 LTS (or Debian 12)
- **Specs:** 2 CPU Cores, 2GB or 4GB RAM, 25GB SSD
- **Cost:** ~$4 to $6 / month on:
  - [Hetzner Cloud](https://www.hetzner.com/cloud) (CX22 ~€3.80/mo)
  - [DigitalOcean Droplet](https://www.digitalocean.com) ($6/mo Basic Droplet)
  - [Hostinger VPS](https://www.hostinger.com/vps-hosting) ($5/mo)
  - [AWS EC2](https://aws.amazon.com/ec2/) (`t3.small` or `t4g.small`)

---

## Method 1: 1-Click Setup on Ubuntu/Debian Linux VPS (Recommended)

### Step 1: Connect to your server
Open your terminal (PowerShell or Git Bash) and connect to your server:
```bash
ssh root@YOUR_SERVER_IP
```

### Step 2: Upload your project files
From your local Windows computer, upload your agent folder to the server:
```powershell
# Run this from your local PowerShell:
scp -r "c:\Users\KRISHNA\Desktop\agent" root@YOUR_SERVER_IP:/opt/instagram_agent
```
*(Alternatively, push your code to a private GitHub repository and `git clone` it on the server).*

### Step 3: Run the 1-click installer
On the server, execute:
```bash
cd /opt/instagram_agent
chmod +x deploy/setup_server.sh
./deploy/setup_server.sh
```

The script will automatically:
- Install Python 3, pip, FFmpeg, and fonts.
- Create an isolated virtual environment (`.venv`).
- Install all required libraries (`moviepy`, `elevenlabs`, `google-genai`, `instagrapi`, etc.).
- Register the **`instagram_agent.service`** systemd background daemon.
- Enable automatic restarts so it stays running even if the server reboots.

### Step 4: Check that it is running live
```bash
# Check service status:
sudo systemctl status instagram_agent

# View real-time live logs:
tail -f /opt/instagram_agent/logs/systemd_daemon.log
```

---

## Method 2: Docker Compose (Zero Configuration)

If your server has Docker installed:

1. Copy your project to the server.
2. Ensure your `.env` file is present in the root directory.
3. Start the container in detached background mode:
   ```bash
   docker compose up -d --build
   ```
4. View live logs:
   ```bash
   docker compose logs -f
   ```
5. Stop or restart anytime:
   ```bash
   docker compose restart
   docker compose down
   ```

---

## Method 3: Lightweight Daily Cron Job

If you prefer running a single scheduled job every day at Instagram's peak evening algorithm window (`18:45 IST` = `13:15 UTC`):

1. On your server, open crontab:
   ```bash
   crontab -e
   ```
2. Add this single line:
   ```bash
   15 13 * * * cd /opt/instagram_agent && /opt/instagram_agent/.venv/bin/python app/autonomous/daily_algorithm_publisher.py >> /opt/instagram_agent/logs/cron_daily.log 2>&1
   ```
   This will wake up every day at 18:45 IST, generate the video, and post it.

---

## Important: Instagram Login & Session Persistence on Server

When your agent logs into Instagram for the first time from a new server IP address, Instagram may request a 2FA verification code.

To avoid repeated logins or verification flags:
1. Log in once on your local machine; the agent saves your session token in [`storage/instagram_session.json`](file:///c:/Users/KRISHNA/Desktop/agent/storage/instagram_session.json).
2. When copying your project to the server, make sure the `storage/` directory is copied over.
3. The server will reuse the verified session token, bypassing login challenges completely.
