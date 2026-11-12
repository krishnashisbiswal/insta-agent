import os
import re
from typing import Any, Dict, Tuple

# Phonetic dictionary mapping Roman astrological and English terms to exact Devanagari phonemes
ASTRO_DEVNAGARI_MAP = {
    # Grahas / Planets
    r"\bshani\s*dev\b": "शनि देव",
    r"\bshani\b": "शनि",
    r"\bsaturn\b": "शनि ग्रह",
    r"\brahu\b": "राहु",
    r"\bketu\b": "केतु",
    r"\bbudh\b": "बुध देव",
    r"\bmercury\b": "बुध ग्रह",
    r"\bbrihaspati\b": "बृहस्पति देव",
    r"\bjupiter\b": "गुरु ग्रह",
    r"\bmangal\b": "मंगल देव",
    r"\bmars\b": "मंगल ग्रह",
    r"\bsurya\b": "सूर्य देव",
    r"\bsun\b": "सूर्य देव",
    r"\bchandra\b": "चंद्र देव",
    r"\bmoon\b": "चंद्र देव",
    r"\bshukra\b": "शुक्र देव",
    r"\bvenus\b": "शुक्र देव",

    # Gemstones
    r"\bneelam\b": "नीलम",
    r"\bblue\s*sapphire\b": "नीलम",
    r"\bpanna\b": "पन्ना",
    r"\bemerald\b": "पन्ना",
    r"\bpukhraj\b": "पुखराज",
    r"\byellow\s*sapphire\b": "पुखराज",
    r"\bmanik\b": "माणिक",
    r"\bruby\b": "माणिक",
    r"\blehsuniya\b": "लहसुनिया",
    r"\bcat'?s?\s*eye\b": "लहसुनिया",
    r"\bgomed\b": "गोमेद",
    r"\bheera\b": "हीरा",
    r"\bdiamond\b": "हीरा",
    r"\bmoti\b": "मोती",
    r"\bpearl\b": "मोती",
    r"\bmoonga\b": "मूंगा",
    r"\bred\s*coral\b": "मूंगा",

    # Houses (Bhavas)
    r"\b1st\s*house\b": "प्रथम भाव",
    r"\b2nd\s*house\b": "दूसरे भाव",
    r"\b3rd\s*house\b": "तीसरे भाव",
    r"\b4th\s*house\b": "चौथे भाव",
    r"\b5th\s*house\b": "पांचवें भाव",
    r"\b6th\s*house\b": "छठे भाव",
    r"\b7th\s*house\b": "सातवें भाव",
    r"\b8th\s*house\b": "आठवें भाव",
    r"\b9th\s*house\b": "नौवें भाव",
    r"\b10th\s*house\b": "दसवें भाव",
    r"\b11th\s*house\b": "ग्यारहवें भाव",
    r"\b12th\s*house\b": "बारहवें भाव",

    # Lagnas / Signs
    r"\bmesha?\b": "मेष",
    r"\baries\b": "मेष",
    r"\bvrishchika?\b": "वृश्चिक",
    r"\bscorpio\b": "वृश्चिक",
    r"\bsimha?\b": "सिंह",
    r"\bleo\b": "सिंह",
    r"\bvrishabha?\b": "वृषभ",
    r"\btaurus\b": "वृषभ",
    r"\bmithuna?\b": "मिथुन",
    r"\bgemini\b": "मिथुन",
    r"\bkarka?\b": "कर्क",
    r"\bcancer\b": "कर्क",
    r"\bkanya\b": "कन्या",
    r"\bvirgo\b": "कन्या",
    r"\btula\b": "तुला",
    r"\blibra\b": "तुला",
    r"\bdhanu\b": "धनु",
    r"\bsagittarius\b": "धनु",
    r"\bmakara?\b": "मकर",
    r"\bcapricorn\b": "मकर",
    r"\bkumbha?\b": "कुंभ",
    r"\baquarius\b": "कुंभ",
    r"\bmeena?\b": "मीन",
    r"\bpisces\b": "मीन",
    r"\blagna\b": "लग्न",
    r"\bascendant\b": "लग्न",
    r"\bkundli\b": "कुंडली",
    r"\bhoroscope\b": "कुंडली",

    # Common Terms & Remedies
    r"\bpitru\s*dosh\b": "पितृ दोष",
    r"\bmanglik\s*dosh\b": "मांगलिक दोष",
    r"\bkaal\s*sarp\b": "कालसर्प दोष",
    r"\bsade\s*sati\b": "साढ़ेसाती",
    r"\bpeepal\b": "पीपल",
    r"\bsarson\s*ka\s*tel\b": "सरसों का तेल",
    r"\bspinach\b": "पालक",
    r"\bwednesday\b": "बुधवार",
    r"\bsaturday\b": "शनिवार",
    r"\btuesday\b": "मंगलवार",
    r"\bthursday\b": "गुरुवार",
}


def clean_pronunciation_for_hindi(text: str) -> str:
    """
    Substitutes Roman / English astrological keywords with precise Devanagari phonemes
    and cleans formatting symbols to guarantee zero slurring or pronunciation distortion.
    """
    if not text:
        return ""
    # Strip bracketed notes e.g. [Pause], (beat)
    res = re.sub(r"\[.*?\]", "", text)
    res = re.sub(r"\((?:pause|whisper|beat|dramatic|tone|sound)[^)]*\)", "", res, flags=re.IGNORECASE)
    # Strip markdown symbols and emojis
    res = re.sub(r"[*_~`#]", "", res)
    res = re.sub(r"[\U00010000-\U0010ffff]", "", res)
    res = re.sub(r"[\u2600-\u27BF]", "", res)

    for pattern, dewa in ASTRO_DEVNAGARI_MAP.items():
        res = re.sub(pattern, dewa, res, flags=re.IGNORECASE)

    # Clean generic pronouns if text refers to Moon / Chandra
    if any(k in res for k in ["चंद्र", "चन्द्र", "मोती"]):
        res = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+का\b", "चंद्रमा का", res)
        res = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+की\b", "चंद्रमा की", res)
        res = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+के\b", "चंद्रमा के", res)
        res = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+को\b", "चंद्र देव को", res)
        res = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+से\b", "चंद्र देव से", res)
        res = re.sub(r"\b(यह|इस|उस)\s+ग्रह\b", "चंद्र देव", res)

    res = re.sub(r"\s+", " ", res).strip()
    return res


def determine_smart_voice(
    topic: str,
    voice_mode: str = "smart",
    gender: str = "male",
) -> Tuple[str, str, str]:
    """
    Smart Voice Switch:
    Selects the optimal language mode, target voice ID, and scriptural prompt profile.

    Returns:
    - (selected_language, selected_voice_id, script_mode)
    """
    mode = voice_mode.lower().strip()

    if mode in ["hindi", "hi"]:
        voice_id = "hi-IN-MadhurNeural" if gender == "male" else "hi-IN-SwaraNeural"
        return "Hindi", voice_id, "pure_hindi"

    if mode in ["english", "en"]:
        voice_id = "en-IN-PrabhatNeural" if gender == "male" else "en-IN-NeerjaNeural"
        return "English", voice_id, "pure_english"

    # SMART AUTOMATIC MODE (Topic-based intelligence)
    traditional_markers = [
        "dosh", "pitru", "shani", "sade sati", "havan", "kundli", "rahu", "ketu",
        "puja", "mantra", "sanctum", "peepal", "bhairav", "moksha", "karma"
    ]
    t_lower = topic.lower()
    is_traditional = any(m in t_lower for m in traditional_markers)

    if is_traditional:
        voice_id = "hi-IN-MadhurNeural" if gender == "male" else "hi-IN-SwaraNeural"
        return "Hindi", voice_id, "pure_hindi"
    else:
        voice_id = "en-IN-PrabhatNeural" if gender == "male" else "en-IN-NeerjaNeural"
        return "English", voice_id, "pure_english"
