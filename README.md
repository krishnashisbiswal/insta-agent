# Instagram Autonomous Video Generation & Direct Upload Agent (Gemini AI Powered)

An autonomous AI agent that generates high-retention faceless Instagram Reels (1080x1920 MP4) and publishes them directly to Instagram, powered completely by the **Google Gemini API** (`google-genai` SDK).

---

## 🌟 Autonomous Highlights

- **100% Autonomous Pipeline:** Self-ideates viral topics using Gemini, generates scored scripts, synthesizes neural voiceover audio, renders 1080x1920 MP4 vertical videos, writes optimized captions, and publishes directly to Instagram.
- **Smart Memory (No Duplicate Topics):** Tracks published reels in `storage/published_history.json` and keeps a dynamic content buffer in `storage/content_queue.json`.
- **Two Direct Upload Methods:**
  1. **Direct Account Login (`instagrapi`):** Direct upload using your Instagram username & password—no Meta Developer App or Facebook Page required!
  2. **Official Meta Graph API:** Resumable video container upload for Meta Business/Creator accounts.
  3. **Safe Dry-Run Mode:** If no credentials are provided, validates video specs and saves files locally without failing.
- **Continuous Daemon Scheduler:** Runs in the background (e.g. every 6 or 12 hours) producing and uploading Reels automatically.

---

## 📁 Project Architecture

```
agent/
├── app/
│   ├── autonomous/
│   │   ├── autonomous_agent.py  # 1-Click autonomous reel production cycle
│   │   └── content_manager.py   # Topic buffer & published history memory
│   ├── agents/
│   │   ├── gemini_client.py     # Resilient Gemini client with fallback & retries
│   │   ├── script_agent.py      # Hook formulas (26 templates), scoring & beats
│   │   └── caption_agent.py     # Caption optimizer & feed-cut linter
│   ├── video/
│   │   ├── tts_engine.py        # Neural TTS (Hindi/Hinglish/English) with timestamps
│   │   ├── visual_generator.py  # 1080x1920 aesthetic scene generator
│   │   └── video_composer.py    # MoviePy 2 + FFmpeg MP4 composer
│   ├── instagram/
│   │   └── uploader.py          # Direct Instagram + Meta Graph API publisher
│   ├── research/
│   │   └── trend_agent.py       # Viral topic & swipe file research
│   └── analytics/
│   │   └── audit_agent.py       # 100-point profile & bio auditor
│   └── main.py                  # CLI pipeline runner
├── config/
│   └── settings.py              # Centralized environment configuration
├── storage/
│   ├── content_queue.json       # Queued upcoming topics
│   ├── published_history.json   # History of all published reels
│   └── instagram_session.json   # Cached login session
├── output/
│   ├── reels/                   # Generated 1080x1920 MP4 video files
│   ├── audio/                   # Generated voiceover MP3 files
│   ├── frames/                  # Scene visual background images
│   └── scripts/                 # JSON script manifests
├── scheduler.py                 # Autonomous background daemon
├── run_agent.py                 # Master interactive & CLI runner
├── requirements.txt             # Python dependencies
└── .env                         # API credentials
```

---

## 🚀 Quick Setup

### 1. Environment Configuration

Edit your `.env` file in the root folder:

```env
# 1. Gemini AI (Required)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash

# 2. Instagram Direct Upload - Choose ONE of the following:

# OPTION A: Direct Account Login (Easiest - Works for any account)
INSTAGRAM_USERNAME=your_instagram_handle
INSTAGRAM_PASSWORD=your_instagram_password

# OPTION B: Official Meta Graph API (For Business/Creator Accounts)
INSTAGRAM_USER_ID=your_instagram_business_account_id
INSTAGRAM_ACCESS_TOKEN=your_meta_access_token

# 3. Autonomous Scheduling
AUTO_POST_INTERVAL_HOURS=12
CONTENT_NICHE=Vedic astrology
CONTENT_LANGUAGE=Hindi mixed with English
CONTENT_THEME=cosmic
```

---

## 💻 How to Run

### 1. Master Interactive Launcher

```bash
python run_agent.py
```

Presents an interactive menu:
1. **[AUTONOMOUS]** 1-Click Autonomous Reel (Topic -> Video -> Upload)
2. **[SCHEDULER]** Start Background Posting Daemon
3. **[CUSTOM]** Create Video for Specific Topic
4. **[RESEARCH]** Find Viral Reel Angles with Gemini
5. **[QUEUE]** View / Refill Autonomous Content Queue
6. **[AUDIT]** Audit Profile against 100-Point Rubric
7. **[TEST]** Check Gemini API & Instagram Credentials

---

### 2. Autonomous One-Shot CLI

Run a single autonomous cycle (ideates fresh topic, generates script, audio, video, and uploads directly):

```bash
python run_agent.py auto
```

Or run via scheduler:
```bash
python scheduler.py --once
```

---

### 3. Background Continuous Scheduler (Daemon)

Run the autonomous agent in the background to automatically create and publish a new Reel every 12 hours:

```bash
python scheduler.py --interval 12
```

To run in dry-run mode (generates video and validates without live posting):
```bash
python scheduler.py --interval 12 --dry-run
```

---

### 4. Custom Single Topic Generation

```bash
# Generate Reel locally (saved to output/reels/)
python run_agent.py run --topic "Secret of Shani Sade Sati" --theme cosmic

# Generate and automatically publish to Instagram
python run_agent.py run --topic "Karma and Shani Dev" --upload
```

---

## 🎬 Video Output Specifications

- **Format:** MP4 (H.264 video, AAC audio, YUV420p)
- **Resolution:** 1080 x 1920 (9:16 vertical)
- **Framerate:** 30 FPS
- **Audio Quality:** 192 kbps stereo
- **On-Screen Captions:** Safe-zone pill boxes with drop shadows and keyword emphasis
- **Compliance:** 100% compliant with Instagram Reels feed specifications
