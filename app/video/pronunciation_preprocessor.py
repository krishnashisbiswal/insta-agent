"""
Pronunciation Preprocessor for Indic TTS Engines (Sarvam AI & Neural Edge-TTS).

Features:
- Accurate phoneme mapping for key Vedic astrology terms:
  Shani, Rahu, Ketu, Kundali, Nakshatra, Dasha, Gochar, Graha, Lagna,
  Sade Sati, Mahadasha, Antardasha, Bhavas, and gemstones.
- Selective Devanagari transliteration of modern conversational Hinglish loanwords
  (e.g., career -> करियर, focus -> फोकस, stress -> स्ट्रेस, chart -> चार्ट)
  to eliminate robotic Latin-letter stumbles in neural Indian voice engines.
- Strict separation: original text preserved for captions/on-screen graphics;
  phonetically enhanced text used exclusively for TTS audio generation.
- Natural pause handling (prosodic breath punctuation).
"""

import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Core Astrological Pronunciation Lexicon
ASTRO_CORE_TERMS: Dict[str, str] = {
    # 1. Primary Grahas & Nodes
    r"\bshani\s*dev\b": "शनि देव",
    r"\bshani\b": "शनि",
    r"\bsaturn\b": "शनि ग्रह",
    r"\brahu\s*dev\b": "राहु देव",
    r"\brahu\b": "राहु",
    r"\bketu\s*dev\b": "केतु देव",
    r"\bketu\b": "केतु",
    r"\bbudh\s*dev\b": "बुध देव",
    r"\bbudh\b": "बुध",
    r"\bmercury\b": "बुध ग्रह",
    r"\bbrihaspati\s*dev\b": "बृहस्पति देव",
    r"\bbrihaspati\b": "बृहस्पति",
    r"\bguru\s*dev\b": "गुरु देव",
    r"\bjupiter\b": "गुरु ग्रह",
    r"\bmangal\s*dev\b": "मंगल देव",
    r"\bmangal\b": "मंगल",
    r"\bmars\b": "मंगल ग्रह",
    r"\bsurya\s*dev\b": "सूर्य देव",
    r"\bsurya\b": "सूर्य",
    r"\bsun\b": "सूर्य देव",
    r"\bchandra\s*dev\b": "चंद्र देव",
    r"\bchandra\b": "चंद्र देव",
    r"\bchandrama\b": "चंद्रमा",
    r"\bmoon\b": "चंद्र देव",
    r"\bshukra\s*dev\b": "शुक्र देव",
    r"\bshukra\b": "शुक्र",
    r"\bvenus\b": "शुक्र देव",

    # 2. Key Astrological Concepts & Calculations
    r"\bkund[a]?li\b": "कुंडली",
    r"\bhoroscope\b": "कुंडली",
    r"\bbirth\s*chart\b": "जन्म कुंडली",
    r"\bnakshatra[s]?\b": "नक्षत्र",
    r"\bconstellation[s]?\b": "नक्षत्र",
    r"\bmaha[\s\-]*dash?a\b": "महादशा",
    r"\bantar[\s\-]*dash?a\b": "अंतर्दशा",
    r"\bpratyantar[\s\-]*dash?a\b": "प्रत्यंतर्दशा",
    r"\bdash?a[s]?\b": "दशा",
    r"\bgochar\b": "गोचर",
    r"\btransit[s]?\b": "गोचर",
    r"\bgrah[a]?[s]?\b": "ग्रह",
    r"\bnavagrah[a]?[s]?\b": "नवग्रह",
    r"\blagn[a]?\b": "लग्न",
    r"\bascendant\b": "लग्न",
    r"\bsade[\s\-]*sati\b": "साढ़ेसाती",
    r"\bdhaiyya\b": "ढैया",
    r"\bdrishti\b": "दृष्टि",
    r"\bdristi\b": "दृष्टि",
    r"\byog[a]?[s]?\b": "योग",
    r"\brajyog[a]?\b": "राजयोग",
    r"\bvipreet\s*rajyog\b": "विपरीत राजयोग",

    # 3. Bhavas (Houses)
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
    r"\bbhav[a]?[s]?\b": "भाव",

    # 4. Rashis (Zodiac Signs)
    r"\bmesha?\b": "मेष",
    r"\baries\b": "मेष",
    r"\bvrishabha?\b": "वृषभ",
    r"\btaurus\b": "वृषभ",
    r"\bmithuna?\b": "मिथुन",
    r"\bgemini\b": "मिथुन",
    r"\bkarka?\b": "कर्क",
    r"\bcancer\b": "कर्क",
    r"\bsimha?\b": "सिंह",
    r"\bleo\b": "सिंह",
    r"\bkanya\b": "कन्या",
    r"\bvirgo\b": "कन्या",
    r"\btula\b": "तुला",
    r"\blibra\b": "तुला",
    r"\bvrishchika?\b": "वृश्चिक",
    r"\bscorpio\b": "वृश्चिक",
    r"\bdhanu\b": "धनु",
    r"\bsagittarius\b": "धनु",
    r"\bmakara?\b": "मकर",
    r"\bcapricorn\b": "मकर",
    r"\bkumbha?\b": "कुंभ",
    r"\baquarius\b": "कुंभ",
    r"\bmeena?\b": "मीन",
    r"\bpisces\b": "मीन",

    # 5. Doshas & Life Dynamics
    r"\bpitru\s*dosh\b": "पितृ दोष",
    r"\bmanglik\s*dosh\b": "मांगलिक दोष",
    r"\bkaal\s*sarp\s*dosh\b": "कालसर्प दोष",
    r"\bkaal\s*sarp\b": "कालसर्प",
    r"\bguru\s*chandal\b": "गुरु चांडाल योग",
    r"\bgrahan\s*dosh\b": "ग्रहण दोष",
    r"\bkarmic\b": "कार्मिक",
    r"\bkarma\b": "कर्म",

    # 6. Gemstones & Crystals
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
    r"\brudraksh[a]?\b": "रुद्राक्ष",
    r"\bpanchmukhi\b": "पंचमुखी",
    r"\b5[\s\-]*mukhi\b": "पंचमुखी",
    r"\b7[\s\-]*mukhi\b": "सप्तमुखी",
    r"\bpyrite\b": "पायराइट",
    r"\bamethyst\b": "अमेथिस्ट",
    r"\bcitrine\b": "सिट्रीन",
    r"\btourmaline\b": "टूरमैलीन",
    r"\bblack\s*tourmaline\b": "ब्लैक टूरमैलीन",
    r"\btiger[']?s?\s*eye\b": "टाइगर आई",
    r"\bclear\s*quartz\b": "स्फटिक",
    r"\bsphatik\b": "स्फटिक",
}

# Modern Conversational Hinglish Loanwords
# Transliterated to Devanagari only when mixed in Hindi/Hinglish speech
# to prevent neural Indian voices from awkwardly spelling or stumbling on Latin characters.
HINGLISH_LOANWORDS: Dict[str, str] = {
    r"\bcareer\b": "करियर",
    r"\bfocus\b": "फोकस",
    r"\bstress\b": "स्ट्रेस",
    r"\btension\b": "टेंशन",
    r"\benergy\b": "एनर्जी",
    r"\benergies\b": "एनर्जीज",
    r"\bpositive\b": "पॉजिटिव",
    r"\bnegative\b": "नेगेटिव",
    r"\bvibe[s]?\b": "वाइब्स",
    r"\bvibration[s]?\b": "वाइब्रेशन्स",
    r"\bfrequency\b": "फ्रीक्वेंसी",
    r"\bclient[s]?\b": "क्लाइंट्स",
    r"\bdecision[s]?\b": "डिसीजन्स",
    r"\bresult[s]?\b": "रिजल्ट्स",
    r"\bchart[s]?\b": "चार्ट",
    r"\bplacement[s]?\b": "प्लेसमेंट्स",
    r"\bdisrupt[s]?\b": "डिसरप्ट",
    r"\bblock[s]?\b": "ब्लॉक",
    r"\bclash\b": "क्लैश",
    r"\bclashing\b": "क्लैश",
    r"\bmatch\b": "मैच",
    r"\bbalance\b": "बैलेंस",
    r"\bbreakthrough\b": "ब्रेकथ्रू",
    r"\bgrowth\b": "ग्रोथ",
    r"\bsuccess\b": "सक्सेस",
    r"\bproblem[s]?\b": "प्रॉब्लम्स",
    r"\breel[s]?\b": "रील",
    r"\bcomment\b": "कमेंट",
    r"\bsave\b": "सेव",
    r"\bshare\b": "शेयर",
    r"\bconsultation\b": "कंसल्टेशन",
    r"\banalysis\b": "एनालिसिस",
    r"\bmental\s*peace\b": "मानसिक शांति",
    r"\bnervous\s*system\b": "नर्वस सिस्टम",
    r"\bpressure\b": "प्रेशर",
    r"\bdelay[s]?\b": "देरी",
    r"\bunexpected\b": "अचानक",
}


class PronunciationPreprocessor:
    """
    Dedicated pronunciation and prosodic preprocessor for Reel voiceovers.
    Guarantees:
    1. Difficult Vedic astrology terms are accurately articulated by neural TTS.
    2. Conversational Hinglish words blend seamlessly without robotic stumbles.
    3. The original script for captions and on-screen cards remains untouched.
    4. Meaningful punctuation inserts natural speech pauses.
    """

    @classmethod
    def clean_text_for_display(cls, text: str) -> str:
        """
        Cleans brackets, markdown, and meta-tags for on-screen caption display
        without altering the language or vocabulary.
        """
        if not text:
            return ""
        # Strip bracketed/parenthetical stage notes
        res = re.sub(r"\[.*?\]", "", text)
        res = re.sub(r"\([^)]*(?:pause|whisper|beat|dramatic|tone|sound|breath)[^)]*\)", "", res, flags=re.IGNORECASE)
        # Strip markdown symbols and emojis
        res = re.sub(r"[*_~`#]", "", res)
        res = re.sub(r"[\U00010000-\U0010ffff]", "", res)
        res = re.sub(r"[\u2600-\u27BF]", "", res)
        res = re.sub(r"\s+", " ", res).strip()
        return res

    @classmethod
    def is_devanagari_or_hinglish(cls, text: str) -> bool:
        """Check if text contains Devanagari or Hinglish context."""
        if re.search(r"[\u0900-\u097F]", text):
            return True
        hinglish_markers = {
            "hai", "hain", "kare", "karna", "hoti", "hote", "hota", "aap", "aapko",
            "kundli", "kundali", "shani", "graha", "grah", "rahu", "ketu", "dasha",
            "gochar", "nakshatra", "lekin", "isliye", "sabse", "bhi", "yeh", "woh",
            "kaise", "kyun", "kya", "dekho", "samjho", "pehnna", "chahiye"
        }
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
        matches = sum(1 for w in words if w in hinglish_markers)
        return matches >= 2

    @classmethod
    def preprocess_for_tts(
        cls,
        text: str,
        engine: str = "sarvam",
        voice: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        """
        Preprocesses text exclusively for the TTS synthesizer.
        Preserves original script for subtitles.
        """
        if not text:
            return ""

        # Step 1: Base clean of formatting and emojis
        clean = cls.clean_text_for_display(text)

        is_hindi_context = cls.is_devanagari_or_hinglish(clean)
        if language and any(k in language.lower() for k in ["hindi", "hinglish", "hi"]):
            is_hindi_context = True

        # Step 2: Apply Astrological Devanagari Terminology mapping in Hindi/Hinglish contexts
        if is_hindi_context:
            for pattern, dev_rep in ASTRO_CORE_TERMS.items():
                clean = re.sub(pattern, dev_rep, clean, flags=re.IGNORECASE)

            for pattern, dev_rep in HINGLISH_LOANWORDS.items():
                clean = re.sub(pattern, dev_rep, clean, flags=re.IGNORECASE)

            # Clean awkward mixed English phrases like "ki dristi" or "ka clash"
            clean = re.sub(r"\bki\s*dristi\b", "की दृष्टि", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\bki\s*drishti\b", "की दृष्टि", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\bka\s*clash\b", "का टकराव", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\bki\s*energy\b", "की ऊर्जा", clean, flags=re.IGNORECASE)

            # Step 3: Reverence normalization for celestial entities
            clean = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+का\b", "संबंधित ग्रह का", clean)
            clean = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+की\b", "संबंधित ग्रह की", clean)
            clean = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+के\b", "संबंधित ग्रह के", clean)
            clean = re.sub(r"\b(यह|इस|उस)\s+ग्रह\s+को\b", "ग्रह देव को", clean)
            clean = re.sub(r"\b(यह|इस|उस)\s+ग्रह\b", "ग्रह देव", clean)

        # Step 4: Prosodic Pause Formatting
        # Replace multiple dots or ellipses with single comma/pause mark
        clean = re.sub(r"\.{2,}", ", ", clean)
        clean = re.sub(r"[\-—–]", ", ", clean)

        # Ensure question marks have trailing breath space for vocal inflection
        clean = re.sub(r"\?\s*", "? ", clean)
        clean = re.sub(r"!\s*", "! ", clean)
        clean = re.sub(r"।\s*", "। ", clean)

        # Step 5: Normalize extra spaces
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean
