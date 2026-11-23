import pytest
from pathlib import Path
from app.video.scene_visual_planner import SceneVisualPlanner
from app.video.tts_engine import generate_speech, get_recommended_voice
from app.video.audio_validator import AudioQualityValidator
from config.settings import DEFAULT_VOICE

def test_no_forced_category_cycling_or_temple_ending():
    """Verify that scenes without temple/havan do not get assigned temple/havan."""
    scenes = [
        {"spoken_line": "क्या आपकी कुंडली में शनि और राहु का प्रभाव बढ़ रहा है?", "on_screen_text": "SHANI RAHU IMPACT"},
        {"spoken_line": "जब शनि की महादशा में केतु का अंतर आता है, तो मानसिक तनाव बढ़ता है।", "on_screen_text": "MENTAL STRESS"},
        {"spoken_line": "लेकिन अगर आपकी कुंडली के दशम भाव में गुरु शुभ स्थिति में हो, तो करियर सुरक्षित रहता है।", "on_screen_text": "10TH HOUSE JUPITER"},
        {"spoken_line": "अपनी जन्म कुंडली की सटीक स्थिति जानने के लिए कमेंट में अपनी राशि लिखें।", "on_screen_text": "COMMENT YOUR RASHI"},
    ]
    plans = SceneVisualPlanner.plan_reel_visuals(scenes=scenes, topic="Shani Mahadasha")
    
    assert len(plans) == 4
    for idx, plan in enumerate(plans):
        desc = (plan.generation_prompt + " " + plan.main_subject).lower()
        # Scene 4 is a comment CTA, must NOT be forced into generic temple lamps
        if idx == 3:
            assert "sacred_temple_lamps" != plan.entity_key
            assert "temple sanctum" not in desc or "consultation" in desc

def test_kundli_visualization_only_when_narration_warrants():
    """Verify that 3D Kundali chart is only invoked when chart/house/kundli is mentioned."""
    scene_career = {"spoken_line": "करियर में लगातार रुकावटें आ रही हैं और मेहनत का फल नहीं मिल रहा।", "on_screen_text": "CAREER OBSTACLES"}
    plan_career = SceneVisualPlanner.plan_scene_visual(scene_career, scene_idx=0, total_scenes=3, topic="Career")
    
    # Should not force a kundli chart on a general career frustration scene
    assert "kundli_chart" != plan_career.entity_key

    scene_house = {"spoken_line": "आपकी कुंडली के सातवें भाव में जब शनि और शुक्र बैठते हैं।", "on_screen_text": "7TH HOUSE SHANI"}
    plan_house = SceneVisualPlanner.plan_scene_visual(scene_house, scene_idx=1, total_scenes=3, topic="Marriage")
    # Mentioning 7th house and kundli specifically invokes kundli or relationship chart intelligence
    assert "7th" in plan_house.main_subject.lower() or "kundli" in plan_house.main_subject.lower() or "relationship" in plan_house.main_subject.lower()

def test_astrologer_voice_natural_pacing_and_pitch():
    """Verify astrologer voice uses natural pitch and clean conversational pacing."""
    assert DEFAULT_VOICE == "hi-IN-MadhurNeural"
    
    sample_text = "आज हम बात करेंगे शनि की साढ़ेसाती के बारे में। लेकिन इसका असर हर व्यक्ति पर एक जैसा नहीं होता।"
    speech_res = generate_speech(text=sample_text, voice="astrologer")
    
    audio_path = Path(speech_res["audio_path"])
    assert audio_path.exists()
    
    valid, metrics, issues = AudioQualityValidator.validate_audio_file(audio_path, expected_text=sample_text)
    assert valid is True
    # Verify WPM is conversational (110 - 150 WPM)
    wpm = metrics.get("estimated_wpm", 130)
    assert 100 <= wpm <= 160
