import re

def detect_3d_object_type(topic: str = "", niche: str = "") -> str:
    combined = f" {topic} {niche} ".lower()

    def contains_any(keywords):
        for k in keywords:
            # Match whole words or phrases with word boundaries
            pattern = r"\b" + re.escape(k) + r"\b"
            if re.search(pattern, combined):
                return True
        return False

    # 1. Non-astrology niches first if specified in niche
    niche_lower = niche.lower()
    if any(k in niche_lower for k in ["crypto", "bitcoin", "finance", "money", "wealth", "investing", "trading", "stock"]):
        return "crypto_coin"
    if any(k in niche_lower for k in ["science", "biology", "dna", "fitness", "health", "workout", "biohack", "longevity"]):
        return "dna_helix"
    if any(k in niche_lower for k in ["ai", "tech", "coding", "software", "developer", "cyber", "machine learning"]):
        return "cyber_core"
    if any(k in niche_lower for k in ["mindset", "psychology", "motivation", "stoic", "discipline"]):
        return "prism_orb"

    # 2. Topic keywords for specific Vedic Astrological Bodies
    if contains_any(["saturn", "shani", "sade sati", "dhaiya", "neelam", "blue sapphire", "karma", "capricorn", "aquarius", "makar", "kumbh"]):
        return "saturn"
    if contains_any(["jupiter", "guru", "brihaspati", "pukhraj", "yellow sapphire", "sagittarius", "pisces", "dhanu", "meen"]):
        return "jupiter"
    if contains_any(["mars", "mangal", "manglik", "angarak", "coral", "moonga", "aries", "scorpio", "mesh", "vrishchik"]):
        return "mars"
    if contains_any(["sun", "surya", "aditya", "father", "authority", "ruby", "manik", "leo", "simha", "atmakaraka"]):
        return "sun"
    if contains_any(["moon", "chandra", "soma", "mind", "pearl", "moti", "mother", "cancer", "kark", "anxiety", "nakshatra"]):
        return "moon"
    if contains_any(["venus", "shukra", "luxury", "diamond", "heera", "taurus", "libra", "vrishabh", "tula", "romance", "marriage"]):
        return "venus"
    if contains_any(["mercury", "budh", "intellect", "emerald", "panna", "gemini", "virgo", "mithun", "kanya", "communication"]):
        return "mercury"
    if contains_any(["rahu", "north node", "eclipse", "illusion", "obsession", "maya", "gomed", "hessonite", "kal sarp"]):
        return "rahu"
    if contains_any(["ketu", "south node", "detachment", "moksha", "cat's eye", "cats eye", "lehsunia"]):
        return "ketu"

    # 3. Topic keywords for Modern Niches (when niche is generic or topic has clear cue)
    if contains_any(["crypto", "bitcoin", "btc", "eth", "ethereum", "web3", "defi", "trading", "stock", "investing", "finance", "money", "wealth", "rich", "passive income"]):
        return "crypto_coin"
    if contains_any(["science", "biology", "dna", "genetics", "health", "fitness", "body", "muscle", "workout", "nutrition", "medicine", "biohack", "longevity"]):
        return "dna_helix"
    if contains_any(["ai", "artificial intelligence", "tech", "coding", "software", "developer", "robot", "cyber", "machine learning", "cloud", "algorithm", "python"]):
        return "cyber_core"
    if contains_any(["mindset", "psychology", "motivation", "success", "discipline", "habits", "focus", "stoic", "stoicism"]):
        return "prism_orb"

    # 4. General Astrology / Zodiac
    if contains_any(["astrology", "vedic", "kundli", "horoscope", "zodiac", "rashi", "planet", "graha"]):
        return "earth"

    return "saturn"

test_cases = [
    ("Why Mangal Dosha delays marriage", "Vedic Astrology", "mars"),
    ("Shani Sade Sati 2026 Warning", "Vedic Astrology", "saturn"),
    ("Never wear Pukhraj gemstone without checking Guru", "Astrology", "jupiter"),
    ("Rahu Mahadasha can make you billionaire overnight", "Astrology", "rahu"),
    ("Chandra Moon affliction causes anxiety", "Vedic Astrology", "moon"),
    ("Surya Sun Mahadasha career boost", "Vedic Astrology", "sun"),
    ("Shukra Venus placement for luxury cars", "Astrology", "venus"),
    ("Ketu in 8th house spiritual awakening", "Vedic Astrology", "ketu"),
    ("Budh Mercury transit business profits", "Vedic Astrology", "mercury"),
    ("How to read your Kundli 1st House", "Vedic Astrology", "earth"),
    ("Bitcoin Bull Run 2026 Price Target", "Crypto & Finance", "crypto_coin"),
    ("Will AI Agents replace junior software engineers?", "Tech & AI", "cyber_core"),
    ("How to optimize sleep and DNA repair", "Biohacking & Fitness", "dna_helix"),
    ("Stoic Mindset rule to eliminate overthinking", "Psychology", "prism_orb"),
]

for topic, niche, expected in test_cases:
    res = detect_3d_object_type(topic, niche)
    print(f"[{res == expected}] Topic: \"{topic[:35]}...\" -> {res} (Expected: {expected})")
    assert res == expected, f"Failed for {topic}: got {res}, expected {expected}"
print("\nALL 14 TEST CASES MATCHED PRECISELY!")
