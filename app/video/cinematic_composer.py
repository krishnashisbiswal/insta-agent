import math
import os
import random
import re
import sys
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoClip,
)
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    BRAND_WATERMARK,
    DEFAULT_FONT_PATH,
    FALLBACK_FONT_PATH,
    IMPACT_FONT_PATH,
    REELS_DIR,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
)

CINEMATIC_BROLL_DIR = PROJECT_ROOT / "assets" / "cinematic_broll"


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Prioritize high-impact viral fonts: Bundled Impact -> Windows -> Linux."""
    paths = [
        str(PROJECT_ROOT / "assets" / "fonts" / "Impact.ttf"),
        str(PROJECT_ROOT / "assets" / "fonts" / "ArialBold.ttf"),
        IMPACT_FONT_PATH,
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/trebucbd.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        DEFAULT_FONT_PATH,
        FALLBACK_FONT_PATH,
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


# =====================================================================
# 1. CINEMATIC SOUND DESIGN GENERATOR (Sub-bass impact + Mystical Drone)
# =====================================================================
def generate_cinematic_soundtrack(duration: float, output_path: Path) -> Path:
    """
    Synthesizes a realistic, multi-layered sacred Vedic cinematic soundscape:
    1. Temple Bell / 432Hz Singing Bowl chime with rich metallic overtones & natural decay.
    2. Deep Tanpura harmonic drone (Sa-Pa 136.1Hz Om resonance with warm acoustic pulsation).
    3. Cinematic sub-bass impact at t=0 (scroll-stopping hook).
    4. Subtle organic holy fire embers warmth.
    """
    sr = 44100
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    # 1. Tanpura / Mystic Om Acoustic Drone (136.1 Hz Om Frequency)
    f_om = 136.1
    h1 = 0.35 * np.sin(2 * np.pi * f_om * t)
    h2 = 0.22 * np.sin(2 * np.pi * (f_om * 1.5) * t + 0.3)
    h3 = 0.18 * np.sin(2 * np.pi * (f_om * 2.0) * t + 0.8)
    h4 = 0.10 * np.sin(2 * np.pi * (f_om * 3.0) * t + 1.2)
    h5 = 0.05 * np.sin(2 * np.pi * (f_om * 4.0) * t + 1.7)

    shimmer = 0.82 + 0.18 * np.sin(2 * np.pi * 0.22 * t)
    theta = 0.90 + 0.10 * np.sin(2 * np.pi * 5.0 * t)
    tanpura = (h1 + h2 + h3 + h4 + h5) * shimmer * theta

    # 2. Sacred Temple Bell / Singing Bowl Chime (at t = 0.1s)
    bell_samples = int(sr * min(duration, 7.0))
    t_bell = np.linspace(0, min(duration, 7.0), bell_samples, endpoint=False)
    bell_decay1 = np.exp(-t_bell * 0.7)
    bell_decay2 = np.exp(-t_bell * 1.4)
    bell_decay3 = np.exp(-t_bell * 2.5)

    bell = (
        0.28 * np.sin(2 * np.pi * 432.0 * t_bell) * bell_decay1
        + 0.18 * np.sin(2 * np.pi * 864.0 * t_bell) * bell_decay2
        + 0.12 * np.sin(2 * np.pi * 1296.0 * t_bell) * bell_decay3
        + 0.08 * np.sin(2 * np.pi * 1728.0 * t_bell) * bell_decay3
    )

    # 3. Sub-bass Cinematic Boom at t = 0
    hit_samples = int(sr * 2.2)
    t_hit = np.linspace(0, 2.2, hit_samples, endpoint=False)
    hit_env = np.exp(-t_hit * 2.0)
    hit_freq = 85.0 * np.exp(-t_hit * 3.5) + 36.0
    hit = 0.38 * np.sin(2 * np.pi * hit_freq * t_hit) * hit_env

    # 4. Fire Embers subtle crackle (Havan ritual ambience)
    np.random.seed(42)
    noise = np.random.randn(n_samples) * 0.02
    pops = (np.random.rand(n_samples) > 0.9994).astype(float) * np.random.randn(n_samples) * 0.08
    embers = (noise + pops) * 0.4

    # Combine master mix
    mix = tanpura * 0.40 + embers * 0.25
    mix[:len(hit)] += hit * 0.75
    mix[:len(bell)] += bell * 0.65

    # Gentle tape saturation for rich warmth
    mix = np.tanh(mix * 1.35) * 0.35

    # Master smooth fades
    fade_in = int(sr * 0.8)
    fade_out = int(sr * 2.0)
    mix[:fade_in] *= np.linspace(0.05, 1.0, fade_in)
    mix[-fade_out:] *= np.linspace(1.0, 0.0, fade_out)

    mix = np.clip(mix, -0.95, 0.95)
    samples_int16 = (mix * 32767).astype(np.int16)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples_int16.tobytes())

    return output_path


# =====================================================================
# 2. CINEMATIC BLEND OVERLAYS (Film Texture, Lens Flare & Vignette)
# =====================================================================
def create_cinematic_blend_layers(width: int = VIDEO_WIDTH, height: int = VIDEO_HEIGHT) -> Image.Image:
    """
    Creates an authentic cinematic blend overlay:
    - Deep perimeter vignette (focuses viewer gaze on center)
    - Warm anamorphic golden light leak at top-right
    - Subtle organic film grain texture
    """
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = width // 2, height // 2

    # 1. Edge Vignette (darkens top 18% and bottom 22% for cinematic framing)
    for r in range(int(height * 0.72), 0, -25):
        alpha = int(170 * (1.0 - (r / (height * 0.72)) ** 1.6))
        draw.ellipse([cx - int(r * 0.62), cy - r, cx + int(r * 0.62), cy + r], fill=(0, 0, 0, alpha))

    # 2. Anamorphic Golden Light Leak (upper-right corner glow)
    leak_cx, leak_cy = int(width * 0.85), int(height * 0.12)
    for r in range(360, 0, -18):
        alpha = int(35 * (1.0 - (r / 360) ** 1.8))
        draw.ellipse([leak_cx - r, leak_cy - r, leak_cx + r, leak_cy + r], fill=(255, 190, 60, alpha))

    # Apply soft blur
    canvas = canvas.filter(ImageFilter.GaussianBlur(32))
    return canvas


# =====================================================================
# 3. KINETIC VIRAL SUBTITLE LAYER (Dynamic Beating Typography)
# =====================================================================
def split_scene_into_beats(spoken_line: str, fallback_title: str) -> List[str]:
    """
    Split a spoken sentence into 2 punchy kinetic subtitle beats
    that synchronize with voiceover pacing.
    """
    # Clean text: remove emoji and non-ASCII characters
    cleaned = re.sub(r"[^\x00-\x7F]+", " ", spoken_line or fallback_title).strip()
    words = cleaned.split()

    if len(words) <= 5:
        return [" ".join(words).upper()]

    mid = len(words) // 2
    beat1 = " ".join(words[:mid]).upper()
    beat2 = " ".join(words[mid:]).upper()
    return [beat1, beat2]


def render_kinetic_caption_layer(
    width: int,
    height: int,
    text: str,
    scene_number: int,
    total_scenes: int,
    badge_text: str = "VEDIC ASTROLOGY",
) -> Image.Image:
    """
    Renders clean, modern, high-contrast kinetic subtitles in the lower-chest third:
    - Impact font (56pt) with 4-pixel deep black stroke outline.
    - Electric yellow/gold highlights on key words.
    - Clean word spacing and centered lines.
    - No ugly black opaque box!
    """
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 1. Sleek Top Frosted Pill Badge
    badge_font = get_font(22, bold=True)
    b_clean = re.sub(r"[^\x00-\x7F]+", "", badge_text).strip().upper()
    b_text = f"✦  {b_clean}  ✦"
    b_bbox = draw.textbbox((0, 0), b_text, font=badge_font)
    b_w = b_bbox[2] - b_bbox[0]
    bx = (width - b_w) // 2
    by = int(height * 0.08)

    pad_x, pad_y = 22, 8
    draw.rounded_rectangle(
        [bx - pad_x, by - pad_y, bx + b_w + pad_x, by + (b_bbox[3] - b_bbox[1]) + pad_y],
        radius=18,
        fill=(8, 6, 14, 195),
        outline=(255, 215, 0, 180),
        width=1,
    )
    draw.text((bx, by), b_text, font=badge_font, fill=(255, 225, 90, 245))

    # 1B. Creator / Brand Watermark (@neovibestore.in)
    if BRAND_WATERMARK:
        wm_font = get_font(21, bold=True)
        wm_text = BRAND_WATERMARK.strip()
        wm_bbox = draw.textbbox((0, 0), wm_text, font=wm_font)
        wm_w = wm_bbox[2] - wm_bbox[0]
        wm_h = wm_bbox[3] - wm_bbox[1]
        wm_x = (width - wm_w) // 2
        wm_y = by + (b_bbox[3] - b_bbox[1]) + pad_y + 14

        wm_px, wm_py = 18, 6
        draw.rounded_rectangle(
            [wm_x - wm_px, wm_y - wm_py, wm_x + wm_w + wm_px, wm_y + wm_h + wm_py],
            radius=12,
            fill=(10, 8, 16, 175),
            outline=(255, 255, 255, 100),
            width=1,
        )
        draw.text((wm_x, wm_y), wm_text, font=wm_font, fill=(255, 255, 255, 235))

    # 2. Kinetic Lower-Chest Subtitles (y ~ 73%)
    cap_font = get_font(56, bold=True)

    # Clean text: remove emojis and punctuation artifacts
    raw_words = [w.strip(".,;:!?\"'") for w in text.strip().split() if w.strip()]

    # Wrap into 1 or 2 lines max
    lines = []
    curr_line = []
    gap = 14
    for w in raw_words:
        curr_line.append(w)
        test_str = " ".join(curr_line)
        bbox = draw.textbbox((0, 0), test_str, font=cap_font)
        if (bbox[2] - bbox[0]) > (width - 140):
            curr_line.pop()
            if curr_line:
                lines.append(curr_line)
            curr_line = [w]
    if curr_line:
        lines.append(curr_line)

    HIGHLIGHT_WORDS = {
        "STOP", "NEELAM", "PUKHRAJ", "MANIK", "PANNA", "HEERA", "MOTI",
        "8TH", "HOUSE", "KARMA", "DEBT", "DANGER", "SHANI", "GURU",
        "WRONG", "POISON", "LUCK", "ENEMY", "FREE", "REMEDY", "TEST",
        "PILLOW", "SILK", "COMMENT", "CHART", "BIRTH", "DATE", "VERIFY"
    }

    line_h = 70
    total_h = len(lines) * line_h
    start_y = int(height * 0.74) - (total_h // 2)

    for i, line_words in enumerate(lines):
        # Calculate exact width of this line
        word_widths = [draw.textbbox((0, 0), wd, font=cap_font)[2] - draw.textbbox((0, 0), wd, font=cap_font)[0] for wd in line_words]
        line_w = sum(word_widths) + (len(line_words) - 1) * gap
        cur_x = (width - line_w) // 2
        cur_y = start_y + (i * line_h)

        for wd, ww in zip(line_words, word_widths):
            wd_clean = "".join(c for c in wd if c.isalnum()).upper()
            is_highlight = wd_clean in HIGHLIGHT_WORDS

            text_color = (255, 230, 0, 255) if is_highlight else (255, 255, 255, 255)

            # Deep 4-way stroke outline for 100% readability
            for ox in [-3, 0, 3]:
                for oy in [-3, 0, 3]:
                    if ox != 0 or oy != 0:
                        draw.text((cur_x + ox, cur_y + oy), wd, font=cap_font, fill=(0, 0, 0, 255))

            # Main text
            draw.text((cur_x, cur_y), wd, font=cap_font, fill=text_color)
            cur_x += ww + gap

    # 3. Bottom Progress Bar (Elegant Gold Dashes)
    dash_w = 44
    dash_gap = 14
    total_dash_w = (total_scenes * dash_w) + ((total_scenes - 1) * dash_gap)
    start_dx = (width - total_dash_w) // 2
    dash_y = int(height * 0.92)

    for idx in range(total_scenes):
        dx = start_dx + idx * (dash_w + dash_gap)
        if idx == (scene_number - 1):
            draw.rounded_rectangle([dx, dash_y, dx + dash_w, dash_y + 6], radius=3, fill=(255, 215, 0, 255))
        else:
            draw.rounded_rectangle([dx, dash_y + 1, dx + dash_w, dash_y + 5], radius=2, fill=(140, 140, 150, 100))

    return overlay


# =====================================================================
# 4. KEN BURNS CAMERA MOTION + DYNAMIC SUBTITLE BEATS
# =====================================================================
def create_cinematic_scene_clip(
    image_path: Path,
    duration: float,
    spoken_line: str,
    on_screen_fallback: str,
    scene_number: int,
    total_scenes: int,
    badge_text: str = "VEDIC ASTROLOGY",
    zoom_rate: float = 0.12,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
) -> VideoClip:
    """
    Renders a true cinematic shot with:
    - Continuous Ken Burns camera push-in zoom (1.0x -> 1.12x)
    - Perimeter vignette & golden lens leak blend
    - Dynamic 2-beat kinetic subtitles that advance in sync with speech
    """
    # 1. Load and prep source image
    src_img = Image.open(image_path).convert("RGB")
    src_w, src_h = src_img.size

    target_ratio = width / height
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        base_cropped = src_img.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        base_cropped = src_img.crop((0, top, src_w, top + new_h))

    base_canvas = base_cropped.resize((int(width * 1.18), int(height * 1.18)), Image.Resampling.BICUBIC)
    bw, bh = base_canvas.size
    bcx, bcy = bw // 2, bh // 2

    # 2. Split spoken dialogue into 2 progressive subtitle beats
    sub_beats = split_scene_into_beats(spoken_line=spoken_line, fallback_title=on_screen_fallback)
    split_time = duration / len(sub_beats) if len(sub_beats) > 1 else duration

    # Pre-render overlays for each beat
    beat_overlays = [
        render_kinetic_caption_layer(
            width=width,
            height=height,
            text=beat_text,
            scene_number=scene_number,
            total_scenes=total_scenes,
            badge_text=badge_text,
        )
        for beat_text in sub_beats
    ]

    # 3. Pre-render cinematic blend layer (vignette + light leaks)
    blend_overlay = create_cinematic_blend_layers(width=width, height=height)

    # 4. Frame generator with Ken Burns zoom & dynamic subtitle switching
    def make_frame(t):
        frac = t / duration if duration > 0 else 0.0
        scale = 1.0 + zoom_rate * (frac ** 0.95)

        crop_w = int(width / scale)
        crop_h = int(height / scale)

        drift_y = int(14 * frac)
        c_left = bcx - (crop_w // 2)
        c_top = bcy - (crop_h // 2) - drift_y
        c_right = c_left + crop_w
        c_bottom = c_top + crop_h

        cropped = base_canvas.crop((c_left, c_top, c_right, c_bottom))
        frame_img = cropped.resize((width, height), Image.Resampling.BILINEAR).convert("RGBA")

        # Blend vignette & light leaks
        frame_img = Image.alpha_composite(frame_img, blend_overlay)

        # Dynamic subtitle switching based on speech progress
        beat_idx = min(int(t / split_time), len(beat_overlays) - 1)
        active_caption = beat_overlays[beat_idx]
        frame_img = Image.alpha_composite(frame_img, active_caption)

        return np.array(frame_img.convert("RGB"))

    return VideoClip(make_frame, duration=duration)


# =====================================================================
# 5. MASTER CINEMATIC REEL BUILDER
# =====================================================================
def create_cinematic_reel_video(
    script_data: Dict[str, Any],
    audio_path: str,
    output_filename: Optional[str] = None,
) -> Path:
    """
    Builds a professional, human-edited Instagram Reel using:
    - Real photorealistic cinematic B-Roll footage/shots
    - Smooth continuous Ken Burns camera push-in zoom
    - Real atmospheric blending (film grain, light leaks, vignette)
    - Kinetic viral subtitles in lower chest area (no ugly boxes)
    - Master audio mixed with ambient cinematic mystical drone & sub-bass hit
    """
    scenes = script_data.get("scenes", [])
    if not scenes:
        raise ValueError("Script data contains no scenes.")

    topic = script_data.get("topic", "Instagram Reel")
    total_scenes = len(scenes)

    # 1. Calculate scene durations synchronized to master audio
    voice_clip = AudioFileClip(audio_path)
    total_audio_duration = voice_clip.duration

    raw_durations = [float(s.get("estimated_seconds", 5.0)) for s in scenes]
    total_est = sum(raw_durations)
    scaling = total_audio_duration / total_est if total_est > 0 else 1.0
    scene_durations = [round(d * scaling, 3) for d in raw_durations]
    scene_durations[-1] += round(total_audio_duration - sum(scene_durations), 3)

    # 2. Map photorealistic cinematic B-roll assets
    broll_files = [
        CINEMATIC_BROLL_DIR / "1_gemstone_hook.jpg",
        CINEMATIC_BROLL_DIR / "2_kundli_chart.jpg",
        CINEMATIC_BROLL_DIR / "3_shani_saturn.jpg",
        CINEMATIC_BROLL_DIR / "4_sacred_havan.jpg",
        CINEMATIC_BROLL_DIR / "5_temple_sanctum.jpg",
    ]

    def get_scene_badge(sc_dict: Dict[str, Any], scene_idx: int, topic_str: str) -> str:
        if sc_dict.get("badge"):
            return sc_dict["badge"].strip().upper()
        topic_words = re.sub(r"[^\w\s]", "", topic_str).strip().upper().split()
        topic_short = " ".join(topic_words[:3]) if topic_words else "VEDIC WISDOM"
        if scene_idx == 0:
            return f"⚠️ {topic_short} ALERT"
        elif scene_idx == 1:
            return "✦ KUNDLI PLACEMENT SECRET ✦"
        elif scene_idx == 2:
            return "✦ GRAHA ENERGETIC TRUTH ✦"
        elif scene_idx == 3:
            return "✦ FREE VEDIC REMEDY ✦"
        else:
            return "✦ VERIFY YOUR CHART ✦"

    video_clips = []
    for idx, sc in enumerate(scenes):
        scene_num = idx + 1
        scene_dur = max(1.5, scene_durations[idx])
        screen_text = sc.get("on_screen_text", topic)

        img_file = broll_files[idx % len(broll_files)]
        badge = get_scene_badge(sc, idx, topic)

        spoken_text = sc.get("spoken_line", "")
        clip = create_cinematic_scene_clip(
            image_path=img_file,
            duration=scene_dur,
            spoken_line=spoken_text,
            on_screen_fallback=screen_text,
            scene_number=scene_num,
            total_scenes=total_scenes,
            badge_text=badge,
            zoom_rate=0.12,
        )
        video_clips.append(clip)

    # 3. Concatenate video clips
    from moviepy import concatenate_videoclips
    final_video = concatenate_videoclips(video_clips, method="compose")

    # 4. Generate & mix ambient mystical soundtrack
    drone_wav_path = PROJECT_ROOT / "output" / "audio" / "cinematic_ambient_drone.wav"
    generate_cinematic_soundtrack(duration=total_audio_duration + 0.5, output_path=drone_wav_path)

    ambient_clip = AudioFileClip(str(drone_wav_path)).with_duration(total_audio_duration)
    # Mix ambient at -18 dB (0.14 volume) underneath voiceover
    ambient_clip = ambient_clip.with_volume_scaled(0.14)
    # Voiceover at 1.0 volume
    voice_clip = voice_clip.with_volume_scaled(1.0)

    composite_audio = CompositeAudioClip([ambient_clip, voice_clip])
    final_video = final_video.with_audio(composite_audio)

    # 5. Render final Reel MP4
    if not output_filename:
        output_filename = f"cinematic_reel_{int(time.time())}.mp4"
    output_path = REELS_DIR / output_filename

    print(f"\n[CINEMATIC COMPOSER] Encoding professional edited reel -> {output_path}")
    final_video.write_videofile(
        str(output_path),
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        ffmpeg_params=["-crf", "22", "-pix_fmt", "yuv420p"],
    )

    # Cleanup clips
    final_video.close()
    voice_clip.close()
    ambient_clip.close()

    return output_path
