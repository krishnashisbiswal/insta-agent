import pytest
from pathlib import Path
from app.video.production_verifier import ProductionReelVerifier, ProductionVerificationReport

def test_production_verifier_nonexistent_video():
    """Verify that verifier returns FAIL when video file is missing."""
    fake_path = Path("output/does_not_exist.mp4")
    report = ProductionReelVerifier.verify_production(
        video_path=fake_path,
        script_data={"topic": "Test Topic", "scenes": []},
    )
    assert report.overall_status == "FAIL"
    assert report.checks["video_exists"] == "FAIL"

def test_production_verifier_scene_relevance_rules():
    """Verify scene relevance evaluation rules distinguish valid vs invalid visuals."""
    # 1. Reject temple for non-temple scene
    status, reason = ProductionReelVerifier._evaluate_scene_relevance(
        scene_idx=0,
        total_scenes=5,
        spoken="आज हम बात करेंगे शनि के गोचर के बारे में।",
        on_screen="SHANI GOCHAR",
        vis_desc="Saturn cosmic atmosphere",
        asset_name="temple_sanctum_golden_diyas.jpg",
    )
    assert status == "FAIL"
    assert "temple" in reason.lower()

    # 2. Reject gemstone for non-gemstone scene
    status, reason = ProductionReelVerifier._evaluate_scene_relevance(
        scene_idx=1,
        total_scenes=5,
        spoken="करियर में अचानक रुकावट आ रही है।",
        on_screen="CAREER OBSTACLE",
        vis_desc="Office desk and journal",
        asset_name="gemstone_blue_sapphire.jpg",
    )
    assert status == "FAIL"
    assert "gemstone" in reason.lower()

    # 3. Accept consultation desk for consultation CTA
    status, reason = ProductionReelVerifier._evaluate_scene_relevance(
        scene_idx=4,
        total_scenes=5,
        spoken="पर्सनल परामर्श के लिए हमें डीएम करें।",
        on_screen="DM FOR CONSULTATION",
        vis_desc="Astrologer study desk with parchment",
        asset_name="astrology_consultation_scroll.jpg",
    )
    assert status == "PASS"
    assert "consultation" in reason.lower()

def test_production_verifier_on_existing_rendered_video():
    """Verify against previously rendered reel production."""
    # Find a fully rendered production video
    prod_videos = [p for p in Path("output/productions").glob("*/final_video.mp4") if p.stat().st_size > 5 * 1024 * 1024]
    if prod_videos:
        vid_file = sorted(prod_videos, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        script_files = sorted(list(Path("output/scripts").glob("*.json")), key=lambda p: p.stat().st_mtime, reverse=True)
        if script_files:
            import json
            script_data = json.loads(script_files[0].read_text(encoding="utf-8"))
            
            report = ProductionReelVerifier.verify_production(
                video_path=vid_file,
                script_data=script_data,
                job_id="test_run",
            )
            assert report.video_summary["resolution"] == "1080x1920"
            assert report.checks["container_decodable"] == "PASS"
            assert report.checks["resolution_1080x1920"] == "PASS"
            assert report.checks["has_audio_stream"] == "PASS"
            
            # Formatted text report must contain standard verification sections
            txt_report = report.format_text_report()
            assert "[1. SCRIPT & SCENE SEGMENTATION]" in txt_report
            assert "[2. SCENE VISUALS & RELEVANCE INSPECTION]" in txt_report
            assert "[3. AUDIO & VOCAL VALIDATION]" in txt_report
            assert "[4. VIDEO TECHNICAL SPECIFICATIONS]" in txt_report
            assert "[5. FINAL END-TO-END VERIFICATION CHECKS]" in txt_report

def test_production_verifier_detects_corrupt_video():
    """Verify that a corrupted or truncated video is caught with FAIL container_decodable."""
    corrupt_candidates = [p for p in Path("output/productions").glob("*/final_video.mp4") if 0 < p.stat().st_size < 2 * 1024 * 1024]
    if corrupt_candidates:
        corrupt_vid = corrupt_candidates[0]
        report = ProductionReelVerifier.verify_production(
            video_path=corrupt_vid,
            script_data={"topic": "Corrupt Test", "scenes": []},
            job_id="test_corrupt",
        )
        assert report.overall_status == "FAIL"
        assert report.checks["container_decodable"] == "FAIL"
        assert len(report.errors) > 0
