# Existing Feature Matrix & Capability Gap Analysis

**Audit Date**: November 10, 2026  
**Baseline Commit**: `e001e1473d27edaf0894226ae69230f488f11915`  

---

## 1. Feature Status Assessment

| Feature Category | Claimed Feature | Implementation Reality in Code | Status | Required Action for Production |
|---|---|---|---|---|
| **Niche Support** | Multi-niche support | Core code hardcodes Vedic astrology, gemstones, Shani, Kundli across 8 files | **NOT IMPLEMENTED** | Build `NicheProfile` architecture; remove hardcoded astrology defaults |
| **Account Management** | Multiple Instagram accounts | Single account via local `.env` variables (`INSTAGRAM_USERNAME`, etc.) | **NOT IMPLEMENTED** | Multi-tenant database models; account isolation; encrypted tokens |
| **Content Formats** | Reels, Stories, Carousels, Single Images | Code only supports 1080x1920 9:16 vertical Reels | **NOT IMPLEMENTED** | AI Creative Director format selection; Carousel/Story builders |
| **AI Script Generation** | 5-beat viral scriptwriting | Gemini prompt produces 5 scenes with hooks and score | **PASS** (Single format) | Generalize prompts for arbitrary niches and multi-format content |
| **AI Hook Scoring** | Hook retention scoring | Implemented via `hookscore.py` checking speed, curiosity, and friction | **PASS** | Decouple from astrology lexicon |
| **Video Production** | Photorealistic b-roll generation | Procedural Pillow layers + online image search | **PASS** (Partial) | Add AI video provider abstraction (Runway, Luma, CogVideo) |
| **3D Rendering** | Genuine 3D planetary rendering | 2D circle with trigonometric shadow and rotation cache | **NOT VERIFIED** (Fake 3D) | True 3D geometry engine / optional Blender headless pipeline |
| **Neural Voiceover** | Studio audio with natural pacing | Edge-TTS with `hi-IN-MadhurNeural` and ElevenLabs option | **PASS** | Language-matched voice router, sync verification |
| **Explore SEO** | Real-time Explore SEO optimization | Checks hashtag count (3-5) and caption length | **PASS** (Heuristic) | Dynamic keyword validation without rigid fixed rules |
| **Official Publishing** | Meta Graph API Resumable Container | Basic post requests to Graph API endpoints | **NOT VERIFIED** (Incomplete) | Add container status polling, media ID verification, token refresh |
| **Unofficial Publishing** | Direct mobile upload via instagrapi | Functional with session caching | **PASS** (Unstable) | Move to optional fallback; isolate from commercial core |
| **Autonomous Scheduling**| Peak-time scheduling | Evaluates peak hours in IST via `timing_engine.py` | **FAIL** (Flawed) | Add persistent scheduler, job locks, daily caps, timezone support |
| **Self-Learning Engine** | Reinforcement learning content optimization| Deterministic increment of `evolution_level` | **NOT IMPLEMENTED** | True analytics-driven scoring using real Meta Graph API Insights |
| **Multi-Tenant SaaS** | Users, Orgs, Billing, Dashboard | Completely missing from codebase | **NOT IMPLEMENTED** | Build SQLAlchemy models, FastAPI REST API, SaaS dashboard |
| **Security & Privacy** | Encrypted credential storage | Plaintext in `.env` and unencrypted JSON in `storage/` | **FAIL** | Encrypt tokens with AES-GCM / Fernet, sanitize logging |

---

## 2. Summary Gap Metrics

- **Verified Working Core**: Script generation with Gemini, Edge-TTS audio synthesis, 1080x1920 MoviePy compositing with kinetic text.
- **Critical Missing Pillars**:
  1. Multi-tenant SaaS infrastructure (Auth, Orgs, Accounts, Quotas, Billing).
  2. Niche independence (Astrology dominates 8 core modules).
  3. Multi-format content (Carousels, Stories, Single-Image).
  4. Real AI Video / Blender 3D provider registry.
  5. Durable state machine and reliable job scheduler.
  6. Official Meta Graph API end-to-end publishing lifecycle with container status verification.
