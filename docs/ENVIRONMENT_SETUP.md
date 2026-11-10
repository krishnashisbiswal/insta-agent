# Insta-Agent: Environment Configuration Specification

## 1. Environment Variables Reference

Create a `.env` file in the root directory:

```env
# ---------------------------------------------------------------------------
# GEMINI AI CONFIGURATION (MANDATORY)
# ---------------------------------------------------------------------------
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=models/gemini-3.5-flash-lite
GEMINI_TEMPERATURE=0.7
GEMINI_MAX_RETRIES=3

# ---------------------------------------------------------------------------
# SECURITY & DATABASE (MANDATORY FOR PRODUCTION SAAS)
# ---------------------------------------------------------------------------
# Secret Fernet key for token encryption at rest
TOKEN_ENCRYPTION_KEY=gAAAAAB...
# PostgreSQL connection string (defaults to local SQLite if empty)
DATABASE_URL=postgresql://user:pass@localhost:5432/insta_agent

# ---------------------------------------------------------------------------
# PUBLISHING GUARDS (CRITICAL)
# ---------------------------------------------------------------------------
# Safety master switch: MUST be explicitly set to 'true' to publish live to Meta
AUTO_PUBLISH=false

# ---------------------------------------------------------------------------
# OFFICIAL META INSTAGRAM GRAPH API (FOR DEFAULT ACCOUNT)
# ---------------------------------------------------------------------------
INSTAGRAM_USER_ID=17841400000000000
INSTAGRAM_ACCESS_TOKEN=EAAB...

# ---------------------------------------------------------------------------
# BRANDING & NICHE DEFAULTS
# ---------------------------------------------------------------------------
CONTENT_NICHE=tech_ai
BRAND_WATERMARK=@yourbrand
TIMEZONE=Asia/Kolkata

# ---------------------------------------------------------------------------
# OPTIONAL 3D & AI VIDEO PROVIDERS
# ---------------------------------------------------------------------------
BLENDER_PATH=C:/Program Files/Blender Foundation/Blender 4.0/blender.exe
RUNWAY_API_KEY=
LUMA_API_KEY=
```

---

## 2. Python Virtual Environment Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install production dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run test suite
pytest -v
```
