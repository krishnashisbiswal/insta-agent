import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Windows UTF-8 console output
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.agents.caption_agent import optimize_caption
from app.agents.script_agent import generate_reel
from app.analytics.self_learning_engine import SelfLearningEngine
from app.analytics.instagram_algorithm_brain import InstagramAlgorithmBrain
from app.analytics.seo_optimizer import generate_seo_metadata, verify_seo_integrity
from app.video.tts_engine import generate_speech
from app.video.video_composer import create_reel_video
from config.settings import CONTENT_NICHE, TIMEZONE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SampleVideoGenerator")

TOPIC = "Never Wear Blue Sapphire (Neelam) Until You Check Your 8th House"
NICHE = "Vedic Astrology, Gemstone Energy, Psychic Karma & Spiritual Devotion"
LANGUAGE = "Hindi mixed with English"
VOICE = "en-IN-NeerjaExpressiveNeural" # Studio quality expressive neural voice

print("=" * 75)
print("  AUTONOMOUS AI GENERATION: SAMPLE HIGH-RETENTION 3D REEL")
print("=" * 75)
print(f"Topic:     {TOPIC}")
print(f"Niche:     {NICHE}")
print(f"Voice:     {VOICE}")
print(f"Theme:     3D Procedural Space & Rotating Planet Engine")
print("=" * 75)

# Step 1: Self-Learning Brain Evolution Check
print("\n[AI STEP 1/5] Agent brain executing autonomous self-training cycle...")
learning_engine = SelfLearningEngine()
playbook = learning_engine.run_daily_self_upgrade()
algo_brain = InstagramAlgorithmBrain()
algo_state = algo_brain.get_algorithm_state()
print(f" -> Agent Brain Level: {playbook.get('evolution_level', 1.0):.1f}")
print(f" -> Algorithm Phase:   {algo_state['active_phase']} (Score: {algo_state['algorithm_velocity_score']}/100)")

# Step 2: Generate High-Retention Script & Viral Hooks
print("\n[AI STEP 2/5] Writing 5-beat viral retention script with Gemini AI...")
script_data = generate_reel(
    topic=TOPIC,
    niche=NICHE,
    language=LANGUAGE,
    duration=25,
)
hook = script_data["selected_hook"]
print(f" -> Winning Hook: \"{hook['spoken']}\"")
print(f"    On-Screen:    \"{hook['on_screen']}\"")
print(f"    Score:        {hook.get('score', 'N/A')}/100 [{hook.get('verdict', 'OK')}]")

# Step 3: Studio Neural Voiceover Generation
print(f"\n[AI STEP 3/5] Generating studio neural voiceover ({VOICE})...")
audio_meta = generate_speech(text=script_data["full_script"], voice=VOICE)
audio_path = audio_meta["audio_path"]
print(f" -> Audio Path: {audio_path}")
print(f"    Duration:   {audio_meta['duration']:.2f} seconds")

# Step 4: Procedural 3D Video Composition
print("\n[AI STEP 4/5] Rendering 1080x1920 30FPS 3D Procedural Reel...")
output_filename = f"sample_neelam_3d_reel_{int(time.time())}.mp4"
video_path = create_reel_video(
    script_data=script_data,
    audio_path=audio_path,
    theme_name="3d_space",
    output_filename=output_filename,
)
print(f" -> Rendered MP4: {video_path}")

# Step 5: Explore Feed SEO Optimization & Package Delivery
print("\n[AI STEP 5/5] Optimizing Explore SEO caption, single-word comment CTA & hashtags...")
caption_res = optimize_caption(
    topic=TOPIC,
    script_hook=hook["spoken"],
    draft_caption=script_data["caption"],
    niche=NICHE,
)
final_caption = caption_res["full_caption"]
hashtags = caption_res["hashtags"]

seo_audit = verify_seo_integrity(script_data, final_caption, hashtags)
print(f" -> SEO Score:   {seo_audit['overall_seo_score']}/100 [{seo_audit['verdict']}]")

# Save outputs to "insta content/"
dest_dir = PROJECT_ROOT / "insta content"
dest_dir.mkdir(parents=True, exist_ok=True)

# Copy video as primary viral_reel_video.mp4
final_video_dest = dest_dir / "viral_reel_video.mp4"
shutil.copy2(video_path, final_video_dest)

# Copy audio
final_audio_dest = dest_dir / "voiceover_audio.mp3"
shutil.copy2(audio_path, final_audio_dest)

# Write caption & hashtags
caption_dest = dest_dir / "caption_and_hashtags.txt"
with open(caption_dest, "w", encoding="utf-8") as f:
    f.write(final_caption + "\n\n" + " ".join(hashtags) + "\n")

# Write metadata
overview_dest = dest_dir / "content_overview.json"
overview_data = {
    "topic": TOPIC,
    "niche": NICHE,
    "voice": VOICE,
    "agent_evolution_level": playbook.get("evolution_level", 1.0),
    "hook": hook,
    "seo_audit": seo_audit,
    "duration_seconds": audio_meta["duration"],
    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "algorithm_phase": algo_state["active_phase"],
}
with open(overview_dest, "w", encoding="utf-8") as f:
    json.dump(overview_data, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 75)
print("  SAMPLE REEL GENERATION COMPLETE!")
print(f"  Saved to: {final_video_dest}")
print(f"  Size:     {final_video_dest.stat().st_size / (1024 * 1024):.2f} MB")
print("=" * 75)
