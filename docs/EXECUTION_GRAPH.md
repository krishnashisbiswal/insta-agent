# System Execution Graph & Control Flows

**Audit Date**: November 10, 2026  
**Baseline Commit**: `e001e1473d27edaf0894226ae69230f488f11915`  

---

## 1. Primary Entry Points & Execution Paths

```mermaid
flowchart TD
    subgraph Entrypoints["CLI & Scheduled Entry Points"]
        CLI1["run_autonomous.py"]
        CLI2["run_agent.py (Interactive)"]
        CLI3["publish_now.py (Direct)"]
        CLI4["scheduler.py (Loop)"]
        GH["GitHub Actions (daily_reel.yml)"]
    end

    subgraph Orchestration["Autonomous Orchestrators"]
        AA["autonomous_agent.py\n(run_autonomous_reel_cycle)"]
        DAP["daily_algorithm_publisher.py\n(produce_trending_reel)"]
        AP["autopilot.py\n(run_autopilot)"]
    end

    subgraph Intelligence["AI & Intelligence Layer"]
        CM["content_manager.py\n(pop_next_topic)"]
        TDE["trend_discovery_engine.py\n(discover_next_viral_trend)"]
        SA["script_agent.py\n(generate_reel)"]
        CA["caption_agent.py\n(optimize_caption)"]
        SEO["seo_optimizer.py\n(verify_seo_integrity)"]
        GEM["gemini_client.py\n(Google Gemini API)"]
    end

    subgraph Media["Media Production Pipeline"]
        CC["cinematic_composer.py\n(create_cinematic_reel_video)"]
        TTS["tts_engine.py\n(generate_speech / edge_tts)"]
        DVE["dynamic_visual_engine.py\n(get_or_generate_scene_image)"]
        E3D["engine_3d.py\n(procedural 3D / backdrop)"]
    end

    subgraph Publishing["Publishing & Persistence Layer"]
        IU["uploader.py\n(InstagramUploader)"]
        META["Meta Graph API\n(Official Container Upload)"]
        SCRAPE["instagrapi Client\n(Unofficial Mobile Scraping)"]
        DRY["Dry-Run Output\n(latest_upload_manifest.json)"]
        HIST["Storage JSONs\n(published_history.json)"]
    end

    CLI1 --> AA
    CLI2 --> AA
    CLI2 --> AP
    CLI3 --> IU
    CLI4 --> AA
    GH --> DAP

    AA --> CM
    CM --> TDE
    TDE --> GEM
    AA --> SA
    SA --> GEM
    AA --> CC
    CC --> TTS
    CC --> DVE
    DVE --> E3D
    AA --> CA
    CA --> GEM
    CA --> SEO
    AA --> IU

    DAP --> CM
    DAP --> SA
    DAP --> CC
    DAP --> CA
    DAP --> IU

    IU --> META
    IU --> SCRAPE
    IU --> DRY
    IU --> HIST
```

---

## 2. Identified Breakage Points in Current Graph

1. **Dual Orchestration Paths**: `autonomous_agent.py` and `daily_algorithm_publisher.py` duplicate ~80% of orchestration logic but with slight variations in error handling and metadata schemas.
2. **Fatal Failure in DAP**: In `daily_algorithm_publisher.py`, line 230 throws `NameError: playbook is not defined`. This stops the flow before `IU.upload_reel()` is invoked.
3. **Unprotected Publishing Entry**: `publish_now.py` bypasses `content_manager.py` and `published_history.json`, causing untracked external uploads.
4. **No Retry Queue**: If `CC` fails due to FFmpeg or memory issues, the topic in `CM` has already been popped and is lost from the queue.
5. **No Graph API Status Polling**: In `uploader.py`, `upload_reel_resumable()` uploads the video bytes to Meta's container but fails to implement a status polling loop (`status_code == 'FINISHED'`), prematurely declaring success before Meta processes the video.
