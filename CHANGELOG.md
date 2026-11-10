# Changelog

All notable changes to the Insta-Agent platform are documented in this file.

## [2.0.0] - 2026-11-10

### Added
- **Publishing State Machine (`app/publishing/state_machine.py`)**: 13-state authoritative state lifecycle with transition validation and durable JSON/SQLite audit trails.
- **Idempotency Control**: Deterministic SHA-256 content keying preventing duplicate jobs and race conditions.
- **Official Meta Instagram Graph API Client (`app/instagram/meta_graph_api.py`)**: Resumable binary upload streaming, container polling loops with exponential backoff, and verified permalink retrieval.
- **Multi-Format Creative Director (`app/creative/`)**:
  - `CreativeDirector`: AI-driven format routing for Reels, Carousels, Stories, and Single Posts.
  - `CarouselBuilder`: 1080x1350 (4:5) and 1080x1080 (1:1) slide deck generation with branded headers, slide counters, and swipe cues.
  - `StoryBuilder`: 1080x1920 (9:16) story card generation with interactive poll mockup zones.
- **Niche Independence Architecture (`app/niche/`)**:
  - `NicheProfile` schema supporting Technology, AI, Fitness, Personal Finance, History, Vedic Astrology, and arbitrary custom niches.
  - AI-assisted and heuristic niche detection (`detect_niche_from_prompt`).
- **Multi-Tenant SaaS Infrastructure (`app/models/`, `app/api/`)**:
  - SQLAlchemy 2.0 ORM models for `Organization`, `User`, `InstagramAccount`, `NicheProfileModel`, `PublishingJobModel`.
  - AES-128-CBC token encryption at rest via `cryptography.fernet`.
  - FastAPI REST API endpoints (`/api/accounts`, `/api/content/generate`, `/api/jobs`, `/api/health`, `/api/analytics`).
- **Empirical Analytics Tracker (`app/analytics/meta_insights.py`)**: Real statistical tracking of reach, impressions, saves, shares, and engagement rates.
- **Blender Headless Renderer & AI Video Providers (`app/video/blender_renderer.py`, `app/video/providers/`)**:
  - Automated detection of system Blender installation with fallback to procedural 3D.
  - Standard provider interfaces for Runway Gen-3 and Luma Dream Machine.
- **CI Workflow (`.github/workflows/ci.yml`)**: Safe automated testing on push and pull requests with zero live publishing risk.
- **Comprehensive Documentation Suite (`docs/`)**:
  - `BASELINE_AUDIT.md`
  - `REPOSITORY_INVENTORY.md`
  - `EXECUTION_GRAPH.md`
  - `EXISTING_FEATURE_MATRIX.md`
  - `SYSTEM_ARCHITECTURE.md`
  - `DATABASE_DESIGN.md`
  - `PROVIDER_INTEGRATION.md`
  - `SECURITY_THREAT_MODEL.md`
  - `SECURITY_REPORT.md`
  - `TEST_REPORT.md`
  - `DEPLOYMENT_GUIDE.md`
  - `ENVIRONMENT_SETUP.md`
  - `PRODUCTION_READINESS.md`
  - `KNOWN_LIMITATIONS.md`
  - `COMMERCIAL_READINESS.md`

### Changed
- **Dependencies (`requirements.txt`)**:
  - Removed conflicting `instagrapi` from core production dependencies.
  - Pinned `moviepy==2.2.1` and `Pillow==11.3.0`.
  - Moved legacy unofficial scraping tools to optional `requirements-legacy.txt`.
- **Gemini Model Routing**:
  - Configured high-capacity, active models (`models/gemini-3.5-flash-lite`, `models/gemini-3.5-flash`, `models/gemini-3-flash-preview`).
  - Added explicit HTTP request timeouts to prevent socket hangs.
- **Badge and Watermark Layout (`app/video/video_composer.py`, `app/video/cinematic_composer.py`)**:
  - Anchored creator watermark at the top safe margin (`y = int(h * 0.07)`).
  - Enforced a minimum 35px separation between watermark and category badges, eliminating all visual overlap.
- **MoviePy Resource Management**:
  - Encapsulated clip generation in `try/finally` blocks with explicit `.close()` calls to prevent Windows file locks.
- **GitHub Workflow (`.github/workflows/daily_reel.yml`)**:
  - Removed rogue `push:` trigger to eliminate accidental publishing during code pushes.

### Fixed
- **P0**: Pip dependency resolution failure in GitHub Actions runners.
- **P0**: NameError `name 'playbook' is not defined` in `daily_algorithm_publisher.py`.
- **P0**: Pytest test collection hangs caused by top-level script renders in `test_animated_3d_clip.py`.
- **P1**: Hardcoded astrological domain bleed across general scriptwriting and visual engines.
- **P1**: Watermark overlapping category badge boxes in video compositions.
