import hashlib
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure TESTING is NOT set so we use real neural Edge-TTS voice
if "TESTING" in os.environ:
    del os.environ["TESTING"]
if "MOCK_AI" in os.environ:
    del os.environ["MOCK_AI"]

from PIL import Image
from app.storage.permanent_visual_memory import PermanentVisualMemory
from app.video.cinematic_composer import create_cinematic_reel_video
from app.video.video_qc import VideoQualityControl

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CinematicReelCreator")

def main():
    print("=" * 70)
    print("GENERATING AUTHENTIC CINEMATIC ASTROLOGY PRODUCTION REEL")
    print("=" * 70)

    topic = "Shani Dev and Surya: The Karmic Balance of Sun and Saturn"
    scenes = [
        {
            "scene_number": 1,
            "spoken_line": "क्या आप जानते हैं कि जब सूर्य और शनि आमने-सामने होते हैं, तो आपके जीवन में क्या बदलता है?",
            "on_screen_text": "SURYA & SHANI SECRET",
            "badge": "VEDIC KARMA CODE",
        },
        {
            "scene_number": 2,
            "spoken_line": "सूर्य देव आपकी आत्मा, आत्म-विश्वास और तेज का प्रतीक हैं।",
            "on_screen_text": "SURYA DEV • SOUL ENERGY",
            "badge": "SOLAR AUTHORITY",
        },
        {
            "scene_number": 3,
            "spoken_line": "वहीं शनि देव न्याय, अनुशासन और कर्म फल के स्वामी हैं।",
            "on_screen_text": "SHANI DEV • KARMA LORD",
            "badge": "DISCIPLINE & JUSTICE",
        },
        {
            "scene_number": 4,
            "spoken_line": "जब यह ऊर्जा दशम भाव यानी कर्म स्थान पर असर डालती है, तो करियर में बड़ा बदलाव आता है।",
            "on_screen_text": "10TH HOUSE TRANSFORMATION",
            "badge": "KARMA KSHETRA",
        },
        {
            "scene_number": 5,
            "spoken_line": "कर्म शुद्ध रखें और अपनी मेहनत पर भरोसा करें, यही सबसे बड़ा उपाय है।",
            "on_screen_text": "PURIFY YOUR ACTIONS",
            "badge": "SACRED TRUTH",
        },
        {
            "scene_number": 6,
            "spoken_line": "अपनी कुंडली की सटीक दिशा जानने के लिए कमेंट में शनि लिखें।",
            "on_screen_text": "SAVE REEL • COMMENT SHANI",
            "badge": "VEDIC GUIDANCE",
        },
    ]

    cinematic_dir = PROJECT_ROOT / "assets" / "cinematic_broll"
    curated_visuals = [
        cinematic_dir / "planet_sun.jpg",
        cinematic_dir / "gemstone_ruby.jpg",
        cinematic_dir / "planet_saturn.jpg",
        cinematic_dir / "authentic_vedic_kundli_parchment.jpg",
        cinematic_dir / "temple_sanctum_golden_diyas.jpg",
        cinematic_dir / "astrology_consultation_scroll.jpg",
    ]

    for p in curated_visuals:
        if not p.exists():
            raise FileNotFoundError(f"Missing required curated asset: {p}")

    print("\n[STEP 1] Validating Visual Asset Uniqueness & Quality...")
    for idx, p in enumerate(curated_visuals):
        print(f" -> Scene {idx + 1}: {p.name} ({p.stat().st_size:,} bytes)")

    # Check unique SHA256 and perceptual hashes
    sha_hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in curated_visuals]
    assert len(set(sha_hashes)) == len(curated_visuals), "Duplicate SHA-256 detected!"
    print(f"Unique SHA-256 hashes: {len(set(sha_hashes))}/{len(curated_visuals)}")

    phashes = []
    for p in curated_visuals:
        with Image.open(p) as im:
            phashes.append(PermanentVisualMemory.compute_fingerprints(im)["phash"])

    min_p_dist = 64
    for i in range(len(phashes)):
        for j in range(i + 1, len(phashes)):
            d = PermanentVisualMemory.hamming_distance(phashes[i], phashes[j])
            min_p_dist = min(min_p_dist, d)
            print(f"  Dist Scene {i+1} vs Scene {j+1}: {d}/64")

    print(f"Minimum pairwise pHash distance: {min_p_dist}/64 (strictly > 5 required)")
    assert min_p_dist > 5, "Perceptual near-duplicate detected!"

    print("\n[STEP 2] Rendering Cinematic Reel with Real Neural Hindi Voiceover...")
    script_data = {
        "topic": topic,
        "selected_hook": "Surya & Shani Cosmic Karmic Balance",
        "scenes": scenes,
        "language": "Hindi",
    }

    output_filename = "cinematic_astrology_surya_shani_reel.mp4"
    rendered_path = create_cinematic_reel_video(
        script_data=script_data,
        voice="hi-IN-MadhurNeural",
        output_filename=output_filename,
        scene_image_paths=curated_visuals,
    )

    print(f"\n[STEP 3] Video Successfully Rendered: {rendered_path} ({rendered_path.stat().st_size:,} bytes)")

    print("\n[STEP 4] Running Automated Video Quality Control...")
    qc_report = VideoQualityControl.audit_video(
        video_path=rendered_path,
        expected_scenes=len(scenes),
        generate_contact_sheet=False,
    )
    print(f"Video QC Passed: {qc_report.passed}")
    print(f"Duration: {qc_report.duration:.2f}s")
    print(f"Dimensions: {qc_report.dimensions}")
    print(f"Audio synced: {qc_report.audio_synced}")
    assert qc_report.passed is True, f"Video QC failed: {qc_report.errors}"

    print("\n[STEP 5] Copying Video Artifact to Brain Artifact Directory...")
    artifact_dir = Path(r"C:\Users\KRISHNA\.gemini\antigravity\brain\d9179029-ca97-4c92-bf81-012bf8248fe6")
    target_art_path = artifact_dir / output_filename
    shutil.copy2(rendered_path, target_art_path)
    print(f"Artifact ready at: {target_art_path}")

    # Generate 6-frame contact sheet for quick inspection
    from app.utils.ffmpeg_resolver import get_ffmpeg_binary
    ffmpeg_exe = get_ffmpeg_binary() or "ffmpeg"
    import subprocess
    from PIL import ImageDraw

    frames_dir = PROJECT_ROOT / "output" / "surya_shani_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    dur = qc_report.duration
    step = dur / len(scenes)

    for i in range(len(scenes)):
        t_pos = i * step + 0.6
        f_p = frames_dir / f"frame_scene_{i+1}.jpg"
        subprocess.run(
            [str(ffmpeg_exe), "-y", "-ss", str(t_pos), "-i", str(rendered_path), "-vframes", "1", "-q:v", "2", str(f_p)],
            capture_output=True,
            check=True,
        )
        extracted.append(f_p)

    pw, ph = 400, 711
    cs = Image.new("RGB", (pw * len(scenes), ph + 80), (12, 10, 16))
    draw = ImageDraw.Draw(cs)
    draw.text((25, 25), "SURYA & SHANI: CINEMATIC REEL (STRICT AESTHETICS & ZERO ARTIFACTS)", fill=(240, 210, 130))

    labels = [
        "1. Surya Hook",
        "2. Soul Ruby",
        "3. Cassini Saturn",
        "4. 10th Kundli",
        "5. Temple Diyas",
        "6. Sacred CTA",
    ]

    for idx, f_p in enumerate(extracted):
        with Image.open(f_p) as im:
            thumb = im.resize((pw - 10, ph - 10), Image.Resampling.LANCZOS)
            x = idx * pw + 5
            y = 65
            cs.paste(thumb, (x, y))
            draw.text((x + 10, y + 10), labels[idx], fill=(255, 235, 160))

    cs_path = artifact_dir / "surya_shani_contact_sheet.jpg"
    cs.save(cs_path, "JPEG", quality=92)
    print(f"Contact sheet saved to: {cs_path}")

    print("\n" + "=" * 70)
    print("ALL DONE: CINEMATIC REEL READY FOR VIEWING")
    print("=" * 70)

if __name__ == "__main__":
    main()
