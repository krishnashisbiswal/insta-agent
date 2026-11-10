# Complete Repository Source Code Inventory

**Baseline Commit**: `e001e1473d27edaf0894226ae69230f488f11915`  
**Total Tracked Python Modules**: 43  
**Audit Date**: November 10, 2026  

---

## 1. Module-by-Module Technical Inventory

| Path | Primary Purpose | Classes | Key Functions | Key Dependencies | Defects Identified |
|---|---|---|---|---|---|
| `app/agents/caption_agent.py` | Optimizes captions with hashtags, readability lints & CTAs | None | `lint_caption`, `optimize_caption` | `gemini_client`, `caption` | Hardcoded astrology keywords (12 references) |
| `app/agents/comment_agent.py` | Handles incoming comments and auto-replies | `CommentAgent` | `process_reel_comments`, `generate_consultation_reply` | `gemini_client` | Hardcoded astrology consultation persona, silent excepts |
| `app/agents/gemini_client.py` | Unified client wrapper for Google Gemini API | None | `generate_text`, `generate_json`, `check_health` | `google.genai`, `requests` | Missing rate-limit backoff on 429 quota exhaustion |
| `app/agents/script_agent.py` | Generates 5-scene viral scripts with hook scoring | None | `generate_reel`, `score_hooks`, `generate_hooks` | `gemini_client`, `hookscore` | 43 hardcoded astrology assumptions, rigid 5-scene format |
| `app/analytics/audit_agent.py` | Evaluates Instagram profile bio and presentation | None | `audit_profile`, `load_profile_rubric` | `gemini_client` | Astrology bio assumptions |
| `app/analytics/instagram_algorithm_brain.py` | Calculates peak posting slots and engagement tactics | `InstagramAlgorithmBrain` | `get_algorithm_state`, `generate_prompt_boost_snippet` | `timing_engine` | Fake "velocity score", hardcoded 3.2x reach multipliers |
| `app/analytics/reinforcement_engine.py` | Q-learning table for content topic parameters | `ReinforcementEvolutionEngine` | `select_action`, `record_feedback_and_update_q` | None | Updates Q-table without real API feedback |
| `app/analytics/self_learning_engine.py` | Persists daily golden rules and evolution playbook | `SelfLearningEngine` | `run_daily_self_upgrade`, `get_prompt_injection` | `gemini_client` | Artificial "evolution level" counter, astrology-biased rules |
| `app/analytics/seo_optimizer.py` | Validates caption keywords and hashtag counts | None | `generate_seo_metadata`, `verify_seo_integrity` | `gemini_client` | Fixed hashtag rules, heuristic scoring |
| `app/analytics/trend_discovery_engine.py` | Brainstorms topic ideas across 5 sub-niches | `TrendDiscoveryEngine` | `discover_next_viral_trend`, `record_generated_topic` | `gemini_client` | Over 80 hardcoded astrology keywords, claims LLM ideas are trends |
| `app/autonomous/autonomous_agent.py` | 1-click autonomous reel generation cycle | None | `run_autonomous_reel_cycle` | `script_agent`, `composer`, `uploader` | Incomplete error recovery, records dry-run as published |
| `app/autonomous/autopilot.py` | Autopilot loop orchestrator | None | `run_autopilot` | `autonomous_agent` | Unbounded polling, single-niche default |
| `app/autonomous/content_manager.py` | Manages topic queues and publication history | `ContentManager` | `pop_next_topic`, `refill_queue_with_gemini` | `gemini_client` | Unsynchronized JSON file writes, no race condition protection |
| `app/autonomous/daily_algorithm_publisher.py` | Timed 1-video-per-day publishing daemon | `DailyAlgorithmPublisher` | `produce_trending_reel`, `run_daily_algorithm_cycle` | `script_agent`, `uploader` | **P0 NameError: `playbook` undefined at line 230** |
| `app/autonomous/timing_engine.py` | Peak posting time calculator | None | `is_in_optimal_window`, `seconds_until_next_optimal` | `datetime` | Rigid hardcoded time windows, no per-account timezone |
| `app/instagram/uploader.py` | Instagram upload dispatcher | `InstagramUploader` | `upload_reel`, `upload_reel_direct`, `upload_reel_resumable` | `instagrapi`, `requests` | Relies on unofficial API by default, lacks Graph API polling loop |
| `app/main.py` | CLI demonstration entry point | None | `main` | All agents | Outdated interactive menu |
| `app/research/trend_agent.py` | Trend agent placeholder | None | `search_trends` | `gemini_client` | LLM hallucination of trends without real web sources |
| `app/video/cinematic_composer.py` | 1080x1920 video compositor with kinetic typography | None | `create_cinematic_reel_video`, `render_kinetic_caption_layer` | `moviepy`, `PIL`, `edge_tts` | Resource leaks (VideoClip not closed in try/finally), astro badges |
| `app/video/dynamic_visual_engine.py` | Sourced and generated b-roll image engine | `DynamicVisualEngine` | `get_or_generate_scene_image`, `search_online_photographic_asset` | `PIL`, `urllib` | Hardcoded astrology search queries |
| `app/video/engine_3d.py` | Procedural 3D planetary and celestial renderer | `Engine3D` | `preload_3d_rotation_cache`, `render_full_3d_scene_frame` | `numpy`, `PIL` | 2D projection labeled as full 3D, no real Blender pipeline |
| `app/video/semantic_visual_router.py` | Maps topic keywords to local asset candidates | `SemanticVisualRouter` | `resolve_scene_visual` | `PIL`, `urllib` | Astrology gemstone candidate tables |
| `app/video/smart_voice_router.py` | Voice selection and text pronunciation cleaner | None | `clean_pronunciation_for_hindi`, `determine_smart_voice` | `re`, `os` | Astrology-only pronunciation dictionary |
| `app/video/tts_engine.py` | Edge-TTS and ElevenLabs audio generator | None | `generate_speech`, `generate_speech_async` | `edge_tts`, `httpx` | Synchronous audio alignment drift |
| `app/video/video_composer.py` | Legacy video composer | None | `create_reel_video`, `render_scene_overlay` | `moviepy`, `PIL` | Late-bound variable bug in frame generator lambda |
| `app/video/visual_generator.py` | Procedural space gradient generator | None | `generate_scene_frame` | `PIL` | Starry void fallbacks |
| `config/settings.py` | Central configuration variables | None | None | `dotenv`, `os` | Hardcoded astrology defaults, credentials in single .env |
| `publish_now.py` | Manual immediate publish CLI script | None | `main` | `uploader` | Skips queue and state tracking |
| `run_agent.py` | Interactive CLI menu | None | `interactive_menu` | Multiple | Bypasses centralized publishing policy |
| `run_autonomous.py` | Autonomous 1-click execution script | None | None | `autonomous_agent` | Dry-run flag override confusion |
| `scheduler.py` | Standalone scheduler process | None | `run_scheduler`, `main` | `autonomous_agent` | No process daemonization, no job locking |
| `tests/generate_3d_previews.py` | Script generating 3D asset previews | None | None | `engine_3d` | Top-level execution on import |
| `tests/test_3d_detect.py` | Test for 3D keyword detection | None | `test_detect` | `engine_3d` | Astrology-specific keyword tests |
| `tests/test_agent.py` | Unit test suite | None | 8 test functions | Multiple | Relies on active Gemini API key |
| `tests/test_animated_3d_clip.py` | 3D rendering test script | None | None | `moviepy`, `engine_3d` | **Pollutes test collection with 20s render** |
| `tests/test_autopilot_flow.py` | Autopilot diagnostic script | None | None | Multiple | Top-level execution on import |
| `vendor/instagram-agent-skill/**` | Vendored agent skill components | None | Multiple | None | Unused standalone scripts |

---

## 2. Directory Tree Structure
```text
insta-agent/
├── .github/workflows/
│   └── daily_reel.yml              # CI/CD & Scheduled Publisher workflow
├── app/
│   ├── agents/                     # Gemini script, caption & comment agents
│   ├── analytics/                  # Trend, SEO, Q-learning, & Algorithm modules
│   ├── autonomous/                 # Autonomous agents, content manager, timing
│   ├── instagram/                  # Instagram upload dispatcher
│   ├── research/                   # Trend research agent
│   └── video/                      # MoviePy, TTS, 3D, and visual compositor
├── assets/
│   ├── cinematic_broll/            # Curated background photographs
│   ├── fonts/                      # ArialBold.ttf, Impact.ttf
│   └── generated_broll/            # Dynamically generated scene imagery
├── config/                         # Settings and persistent history
├── deploy/                         # Systemd service and bash deployment scripts
├── docs/                           # Architecture, audit, security & setup docs
├── insta content/                  # Master generated deliverables
├── storage/                        # Persistent queues, session JSONs, brains
├── tests/                          # Test suite scripts
└── vendor/                         # Vendored Instagram skill definitions
```
