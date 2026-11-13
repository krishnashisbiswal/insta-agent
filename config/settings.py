import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Project root directory (agent/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Storage and output directories
OUTPUT_DIR = BASE_DIR / "output"
REELS_DIR = OUTPUT_DIR / "reels"
AUDIO_DIR = OUTPUT_DIR / "audio"
SCRIPTS_DIR = OUTPUT_DIR / "scripts"
FRAMES_DIR = OUTPUT_DIR / "frames"
LOGS_DIR = BASE_DIR / "logs"
STORAGE_DIR = BASE_DIR / "storage"

# Vendor skills
VENDOR_DIR = BASE_DIR / "vendor" / "instagram-agent-skill"
VENDOR_SKILLS_DIR = VENDOR_DIR / "skills"

# Ensure all output directories exist
for path in (OUTPUT_DIR, REELS_DIR, AUDIO_DIR, SCRIPTS_DIR, FRAMES_DIR, LOGS_DIR, STORAGE_DIR):
    path.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# GEMINI AI CONFIGURATION
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Primary and fallback Gemini models
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-3.5-flash-lite").strip()
GEMINI_FALLBACK_MODELS = [
    "models/gemini-3.5-flash",
    "models/gemini-3-flash-preview",
]

# Generation parameters
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "3"))

# ---------------------------------------------------------------------------
# INSTAGRAM PUBLISHING CONFIGURATION
# Supports both:
# 1. Direct Instagram Account Login (via instagrapi - no Meta developer app needed)
# 2. Official Meta Graph API (requires Facebook Developer App & Business Account)
# ---------------------------------------------------------------------------
INSTAGRAM_UPLOAD_METHOD = os.getenv("INSTAGRAM_UPLOAD_METHOD", "auto").strip().lower()

# Direct Instagram Login Credentials (instagrapi)
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "").strip()
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "").strip()
INSTAGRAM_SESSION_ID = os.getenv("INSTAGRAM_SESSION_ID", "").strip()
INSTAGRAM_SESSION_DATA = os.getenv("INSTAGRAM_SESSION_DATA", "").strip()
IG_SESSION_FILE = STORAGE_DIR / "instagram_session.json"

# Official Meta Graph API Credentials
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "").strip()
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()
META_APP_ID = os.getenv("META_APP_ID", "").strip()
META_APP_SECRET = os.getenv("META_APP_SECRET", "").strip()
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v21.0").strip()
GRAPH_API_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# ---------------------------------------------------------------------------
# AUTONOMOUS AGENT SETTINGS
# ---------------------------------------------------------------------------
AUTO_POST_INTERVAL_HOURS = int(os.getenv("AUTO_POST_INTERVAL_HOURS", "12"))
CONTENT_NICHE = os.getenv("CONTENT_NICHE", "Vedic Astrology, Gemstone Energy, Psychic Karma & Spiritual Devotion").strip()
CONTENT_LANGUAGE = os.getenv("CONTENT_LANGUAGE", "Hindi mixed with English").strip()
CONTENT_THEME = os.getenv("CONTENT_THEME", "3d_space").strip()
PUBLISHED_LOG_FILE = STORAGE_DIR / "published_history.json"
CONTENT_QUEUE_FILE = STORAGE_DIR / "content_queue.json"

# ---------------------------------------------------------------------------
# VIDEO RENDERING SETTINGS
# ---------------------------------------------------------------------------
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 24
VIDEO_ASPECT_RATIO = "9:16"

# Fonts: bold high-visibility fonts for viral Instagram captions
DEFAULT_FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"
FALLBACK_FONT_PATH = "C:/Windows/Fonts/arial.ttf"
IMPACT_FONT_PATH = "C:/Windows/Fonts/impact.ttf"

# Voice settings (edge-tts & Sarvam AI)
# Ultra-realistic neural voices with expressive Indian human intonation
VOICE_MAP = {
    "hindi": "hi-IN-MadhurNeural",              # Deep, authoritative, native Indian Vedic male voice
    "hindi_male": "hi-IN-MadhurNeural",
    "hindi_female": "hi-IN-SwaraNeural",
    "english": "en-US-BrianMultilingualNeural", # Deep, warm, smooth natural documentary narrator
    "english_male": "en-US-BrianMultilingualNeural",
    "english_female": "en-IN-NeerjaExpressiveNeural",
    "indian_english_male": "en-IN-PrabhatNeural",
    "indian_english_female": "en-IN-NeerjaExpressiveNeural",
    "hinglish": "hi-IN-MadhurNeural",            # Native Indian male with spiritual gravitas
    "cinematic_documentary": "en-US-BrianMultilingualNeural",
}
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "hi-IN-MadhurNeural")

# Voice engine selector: "sarvam" (Sarvam AI Arjun) with automatic fallback to "edge_neural"
VOICE_ENGINE = os.getenv("VOICE_ENGINE", "sarvam").strip().lower()

# Sarvam AI - Indian Native Expressive Voice Engine (Arjun speaker)
# Sign up at dashboard.sarvam.ai for ₹100 free developer credits (zero monthly subscription)
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
SARVAM_SPEAKER = os.getenv("SARVAM_SPEAKER", "arjun").strip()
SARVAM_MODEL = os.getenv("SARVAM_MODEL", "bulbul:v4-flash").strip()
SARVAM_PACE = float(os.getenv("SARVAM_PACE", "1.20"))

# Brand watermark for Instagram reels
BRAND_WATERMARK = os.getenv("BRAND_WATERMARK", "@neovibestore.in").strip()

# ---------------------------------------------------------------------------
# APP ENVIRONMENT
# ---------------------------------------------------------------------------
APP_ENV = os.getenv("APP_ENV", "development")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
