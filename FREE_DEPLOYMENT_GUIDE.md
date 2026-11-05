# 100% Free Live Server Hosting Guide (No Credit Card Required)

You do **NOT** need to pay for any cloud hosting. You can host and run this autonomous AI agent **100% free forever** in the cloud.

---

## Method 1: GitHub Actions (100% Free Forever — Recommended)

GitHub gives every user **2,000 free runner minutes every month** for private repositories.
- Each reel takes ~4 minutes to generate.
- Running 1 reel daily = 4 minutes × 30 days = **120 minutes per month**.
- You use only **6% of your free allowance** (1,880 free minutes left over).
- Runs on GitHub's enterprise cloud servers (2 vCPUs, 7 GB RAM, Fast SSD).
- **No credit card required.**

### Step 1: Create a Private GitHub Repository
1. Go to [github.com/new](https://github.com/new).
2. Name your repository (e.g. `instagram-ai-agent`).
3. Set visibility to **Private** (to protect your settings).
4. Click **Create repository**.

### Step 2: Push Your Code to GitHub
From PowerShell on your computer, run:
```powershell
cd "c:\Users\KRISHNA\Desktop\agent"
git init
git add .
git commit -m "Autonomous Instagram AI Agent initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/instagram-ai-agent.git
git push -u origin main
```

### Step 3: Add Your Secrets in GitHub
1. In your GitHub repository, click **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret** and add:
   - `GEMINI_API_KEY`: Your Gemini API key
   - `INSTAGRAM_USERNAME`: Your Instagram username (e.g. `neodivinestore.in`)
   - `INSTAGRAM_PASSWORD`: Your Instagram password
3. Click **Add secret**.

### That's It!
- The workflow file [`.github/workflows/daily_reel.yml`](file:///.github/workflows/daily_reel.yml) is already configured in your repo!
- **Automatic Schedule:** It will automatically wake up every single day at **18:45 IST** (Instagram's peak algorithm velocity), generate the reel, and upload/save it.
- **Manual Trigger Anytime:** Go to your repo's **Actions** tab -> click **Daily Autonomous Instagram Reel Publisher** -> click **Run workflow**.
- **Download Videos Anytime:** Each run saves the rendered video package as a downloadable zip file under the **Artifacts** section!

---

## Method 2: Oracle Cloud Always Free Tier (Free Dedicated VPS)

If you prefer a full dedicated Linux server running 24/7 with a persistent terminal:

1. Sign up at [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/).
2. Create an **Always Free Compute Instance** (Ampere ARM, 4 vCPUs, 24 GB RAM, 200 GB SSD).
3. Connect via SSH and run our automated installer:
   ```bash
   git clone https://github.com/YOUR_USERNAME/instagram-ai-agent.git /opt/instagram_agent
   cd /opt/instagram_agent
   chmod +x deploy/setup_server.sh
   ./deploy/setup_server.sh
   ```
4. The agent will run as a 24/7 background systemd daemon with zero monthly bills.
