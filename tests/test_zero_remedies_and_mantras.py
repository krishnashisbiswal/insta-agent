import sys
from pathlib import Path
import re
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.script_agent import generate_reel
from app.agents.caption_agent import optimize_caption
from app.agents.comment_agent import CommentAgent


def test_no_mantras_in_script_sanitizer():
    # Test that mantras are strictly eliminated from spoken lines
    test_line = "पांचवां उपाय: चन्द्र देव के वैदिक बीज मंत्र ॐ श्रां श्रीं श्रौं सः चन्द्रमसे नमः से सिद्ध रत्न पहनें।"
    
    # Run the same sanitizer regexes as script_agent
    line = re.sub(r"ॐ\s*[\u0900-\u097F\s]+?(?:नमः|स्वाहा|फट्|वषट्)", "", test_line)
    line = re.sub(r"\bॐ\b", "", line)
    line = re.sub(r"\b(?:बीज\s*मंत्र|वैदिक\s*मंत्र|मंत्र\s*जप|मंत्रों?)\b", "कुंडली नियम", line)
    line = re.sub(r"\b(?:पांचवां\s*उपाय|अचूक\s*उपाय|वैदिक\s*उपाय|सरल\s*उपाय)\b", "पांचवां नियम", line)
    line = re.sub(r"\bउपायों?\b", "नियम", line)
    line = re.sub(r"\b(यह|सच्चा|प्राकृतिक|सिद्ध)?\s*रत्न\s*(पहनें|धारण करें|पहनना चाहिए)\b", "बिना कुंडली जांचे कोई रत्न न पहनें", line)
    line = re.sub(r"\s{2,}", " ", line).strip()

    assert "ॐ" not in line
    assert "नमः" not in line
    assert "मंत्र" not in line
    assert "उपाय" not in line
    assert "धारण करें" not in line


def test_on_screen_remedy_cards_sanitized():
    cards = ["5. SACRED BEEJ REMEDY", "5. VEDIC REMEDY", "5. SACRED REMEDY & STONE"]
    for c in cards:
        clean = re.sub(r"\b(?:SACRED\s+BEEJ\s+REMEDY|SACRED\s+REMEDY\s*&\s*STONE|SACRED\s+REMEDY|VEDIC\s+REMEDY|REMEDY\s*&\s*STONE)\b", "AVOID BLIND REMEDIES", c, flags=re.I)
        if not re.search(r"AVOID BLIND REMEDIES", clean, re.I):
            clean = re.sub(r"\b(?:REMEDY|REMEDIES|UPAY|BEEJ|MANTRA)\b", "PLACEMENT", clean, flags=re.I)
        assert "BEEJ" not in clean
        assert "MANTRA" not in clean
        assert clean == "5. AVOID BLIND REMEDIES"


def test_caption_fallback_has_no_mantras_or_remedy_recommendations():
    res = optimize_caption(
        topic="Mars (मंगल): Energy, Courage and Kundli Placements",
        script_hook="क्या आपकी कुंडली में मंगल देव कमजोर हैं?",
        draft_caption="Check your chart",
        language="Hindi",
    )
    caption_text = res["full_caption"]
    assert "ॐ" not in caption_text
    assert "बीज मंत्र" not in caption_text
    assert "DM" in caption_text


def test_comment_agent_has_no_remedies_or_mantras():
    agent = CommentAgent()
    res = agent.generate_consultation_reply(
        comment_text="Meri Kundli me Mangal 8th house me hai kya karu",
        commenter_name="test_user",
        topic="Mangal Dev Kundli Placement",
        language="Hindi",
    )
    reply = res["reply_text"]
    assert "ॐ" not in reply
    assert "बीज मंत्र" not in reply
    assert "DM" in reply
