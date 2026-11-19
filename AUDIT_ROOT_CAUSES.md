# AUDIT ROOT CAUSES REPORT: INSTAGRAM AUTOMATION PIPELINE

**Repository:** `https://github.com/krishnashisbiswal/insta-agent`  
**Branch:** `feature/audit-repair-optimize`  
**Date:** 2026-11-16  
**Auditor:** Principal Python & Systems Architect  

---

## 1. Executive Summary

This audit investigates the persistent issues in the Instagram agent repository:
1. Recurring CI failures caused by import-time side effects and credential requirements.
2. Inaccurate, random, or repetitive visual selection where video scenes display imagery unrelated to spoken dialogue.

A line-by-line inspection of the codebase revealed that the visual pipeline suffered from **architectural fragmentation, topic contamination, uncalled fresh generation methods, and aggressive static fallbacks**.

---

## 2. Inventory of Visual Pipeline Components & Callers

| Module / Class | Primary Function | Implementations Identified | Callers | Critical Defects Found |
|---|---|---|---|---|
| `app/video/dynamic_visual_engine.py` (`DynamicVisualEngine`) | Sourcing and adapting scene images | - `get_or_generate_scene_image`<br>- `get_trait_visual_prompt`<br>- `get_scene_search_query`<br>- `generate_authentic_photographic_canvas` | `app/video/cinematic_composer.py` (`create_cinematic_reel_video`), `tests/test_visual_diversity.py` | 1. Topic concatenated into scene context.<br>2. Scene 0 hardcodes gemstone macro shot.<br>3. `scene_idx % len(queries)` modulo fallbacks.<br>4. Lacks connection to a live AI generation provider. |
| `app/video/semantic_visual_router.py` (`SemanticVisualRouter`) | Routing scenes to semantically matching images | - `resolve_scene_visual`<br>- `find_local_image_candidate`<br>- `generate_fresh_ai_visual` (Pollinations) | `tests/test_visual_router.py`, `app/video/cinematic_composer.py` (legacy) | 1. `generate_fresh_ai_visual` is **never called** by `resolve_scene_visual`.<br>2. Topic string is concatenated into `scene_corpus`.<br>3. Broad substring matching (`fire`, `love`, `wealth`, `peace`).<br>4. Hardcoded static fallback list (`2_kundli_chart.jpg`, `planet_saturn.jpg`, etc.). |
| `app/video/cinematic_composer.py` | Video composition, audio mixing, subtitles | - `create_cinematic_reel_video`<br>- `resolve_topic_visuals`<br>- `sanitize_and_spoof_camera_metadata` | `app/autonomous/daily_algorithm_publisher.py`, `app/autonomous/autonomous_agent.py` | 1. `resolve_topic_visuals` maps topics to fixed 5-image arrays.<br>2. Fake camera hardware spoofing (`iPhone 15 Pro Max`).<br>3. Did not enforce a verified scene-to-asset manifest. |
| `app/video/visual_generator.py` | Procedural frame generator | - `create_vertical_gradient`<br>- `add_geometric_rings`<br>- `add_ambient_glow` | `tests/test_visual_generator.py` (legacy) | Generates synthetic procedural wireframe orbit rings that violate photographic mandates. |
| `app/agents/script_agent.py` | Script & scene generation | - `generate_reel`<br>- `generate_hooks` | `app/autonomous/daily_algorithm_publisher.py`, `app/creative/creative_director.py` | Prompt examples contained generic visual descriptions like `"Ancient Vedic manuscript or cosmic celestial visual"`. |
| `app/storage/permanent_visual_memory.py` (`PermanentVisualMemory`) | Multi-hash fingerprinting & anti-repetition | - `compute_fingerprints`<br>- `check_duplicate`<br>- `record_used_visual` | `DynamicVisualEngine`, `AssetLifecycleManager`, `tests/test_permanent_visual_memory.py` | Thread and process locks are solid, but master assets were mistakenly registered into global blacklists in earlier revisions. |
| `app/storage/asset_lifecycle_manager.py` | State machine & asset cleanup | - `create_job`<br>- `update_job_state`<br>- `run_cleanup_job` | `daily_algorithm_publisher.py` | Must ensure permanent visual memory is never purged during disk reclamation. |

---

## 3. Detailed Root Causes of Visual Inaccuracies

### Root Cause A: Topic Contamination Across Scenes
In `DynamicVisualEngine.get_trait_visual_prompt` and `get_scene_search_query`:
```python
entity_context = f"{spoken} {on_screen} {vis_desc} {topic}".lower()
```
And in `SemanticVisualRouter.resolve_scene_visual`:
```python
scene_corpus = f"{spoken} {on_screen} {vis_desc} {topic.lower()}"
```
**Impact:** If the overall video topic mentions `"Five Mukhi Rudraksha"` or `"Saturn and Mars Opposition"`, the words `"rudraksha"`, `"saturn"`, or `"mars"` are injected into *every single scene's context*. When Scene 2 discusses neuroscience, the matcher sees `"rudraksha"` from the topic and selects a Rudraksha bead rather than a neuroscience visual.

### Root Cause B: First-Scene Override Hardcoded to Gemstone Macro
In `DynamicVisualEngine.get_trait_visual_prompt`:
```python
if scene_idx == 0:
    return (
        f"cinematic dramatic macro luxury shot of {gem_name} resting upon a clean dark reflective surface, "
        f"soft celestial aura of {planet_name} radiating around it, inspiring high-vibrational sacred lighting, {base_modifiers}"
    )
```
**Impact:** Scene 1 (the hook) was forcibly converted into a luxury gemstone macro shot even when the script discussed an astrologer's consultation, a historical event, or a personal birth chart.

### Root Cause C: Overly Broad Substring Matching
In `SemanticVisualRouter`:
```python
"mars": ["mars", "mangal", "मंगल", "manglik", "anger", "fire", "blood", "property", "bhaum", "courage"]
"venus": ["venus", "shukra", "शुक्र", "love", "marriage", "relationship", "7th house", "beauty", "luxury", "partner"]
"jupiter": [..., "wealth", "prosperity", "dhana yoga", "wisdom"]
"havan": ["havan", "yagya", "fire", "sacred fire", "homa", "remedy", "upay", "burning", "offering", "flame"]
```
**Impact:** A scene containing the word `"fire"` triggered either Mars or Havan. A scene containing `"wealth"` or `"prosperity"` triggered Jupiter. A scene mentioning `"love"` or `"partner"` triggered Venus. Ordinary spoken dialogue triggered planetary images instead of the scene's actual narrative subject.

### Root Cause D: Uncalled Fresh AI Generation Method
In `app/video/semantic_visual_router.py`:
- `generate_fresh_ai_visual(cls, prompt: str, filename_stem: str) -> Optional[Path]` was implemented using Pollinations AI.
- However, inside `resolve_scene_visual()`, `generate_fresh_ai_visual` was **never invoked**. Instead, the method fell back directly to `CINEMATIC_BROLL_DIR` static photos.

### Root Cause E: Fixed Fallback Lists and Modulo Reuse
In `DynamicVisualEngine.get_scene_search_query`:
```python
queries = ["pyrite crystal cluster", "raw golden pyrite mineral", ...]
return queries[scene_idx % len(queries)]
```
And in `SemanticVisualRouter.resolve_scene_visual`:
```python
fallback_order = [
    CINEMATIC_BROLL_DIR / "2_kundli_chart.jpg",
    CINEMATIC_BROLL_DIR / "planet_saturn.jpg",
    CINEMATIC_BROLL_DIR / "planet_jupiter.jpg",
    CINEMATIC_BROLL_DIR / "4_sacred_havan.jpg",
    CINEMATIC_BROLL_DIR / "5_temple_sanctum.jpg",
]
```
**Impact:** If a scene did not trigger an entity keyword, it silently fell back to Kundli charts, Saturn, Jupiter, Havan, or Temple Sanctum, producing repetitive and irrelevant visuals.

### Root Cause F: Lack of a Visual Quality Gate
The system previously had zero visual inspection of generated or retrieved assets. Once a file was obtained, it was accepted without verifying whether the image actually depicted the required subject, action, or setting.

### Root Cause G: Device Provenance Falsification
In `app/video/cinematic_composer.py`:
`sanitize_and_spoof_camera_metadata` injected false Apple iPhone 15 Pro Max hardware tags. Truthful media metadata should strip encoding artifacts without fabricating camera hardware models.

---

## 4. Remediation Architecture

1. **Centralized Scene Visual Planner (`SceneVisualPlanner`):**
   - Extracts explicit primary subject, secondary subject, action, environment, and required objects for each scene.
   - Strictly isolates the Reel topic as background context so it cannot contaminate scene entities.
   - Employs word-boundary regex matching with English, Devanagari Hindi, and Sanskrit aliases.
   - Eliminates generic word triggers (`fire`, `house`, `love`, `wealth`).

2. **Authoritative Scene-Level Image Generator (`AIImageGenerator`):**
   - Connects genuine AI image generation to each scene's specific prompt.
   - Generates dedicated 1080x1920 (9:16 vertical) images with unique seeds and job IDs.
   - Strictly raises errors on failure instead of substituting unrelated static fallbacks.

3. **Visual Quality Gate (`VisionQualityGate`):**
   - Inspects generated image dimensions, luminance, composition, and semantic relevance against expected criteria.
   - Rejects duplicates, near-duplicates, or mismatched images.
   - Returns structured validation reports.

4. **Verified Scene-to-Asset Manifest:**
   - Pre-composition manifest links Scene ID → Narration → Prompt → Verified Image → Hashes → Validation Report.
   - Video composer consumes ONLY verified manifest assets.
