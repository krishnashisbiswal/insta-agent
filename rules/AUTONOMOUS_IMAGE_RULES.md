# STRICT AUTONOMOUS IMAGE RULES (ZERO REPETITION & ZERO OUT-OF-CONTEXT)

## RULE 1: MANDATORY PURGE OF ALL OLD IMAGES BEFORE GENERATION
1. Before producing any new Instagram Reel, all existing images in `assets/generated_broll/`, `output/frames/`, and temporary render directories MUST be completely deleted.
2. Every video production run must start with zero cached images on disk.
3. No old b-roll or intermediate frames from previous runs may ever be recycled or reused in a new video.

## RULE 2: ZERO IMAGE REPETITION EVER
1. Within a single Reel: **Every scene MUST have a 100% unique, distinct image file.**
   - If a Reel has 7 scenes, there MUST be 7 completely different, unique images.
   - Repeating an image across multiple scenes in the same video is strictly prohibited.
2. Across different Reels: Old generated images must never be recycled.
3. Every image assignment must be tracked in a strict session set `used_images`.
4. If an image path or URL has already been assigned in `used_images`, it is permanently blocked from being selected again in that Reel.
5. An automated verification assertion (`len(set(scene_images)) == total_scenes`) must run before video compilation. If any duplicate is detected, execution must fail immediately.

## RULE 3: 100% STRICT CONTEXTUAL RELEVANCE (ZERO OUT-OF-CONTEXT VISUALS)
1. **Topic Anchoring**: Every single visual in a Reel MUST visually feature or directly relate to the primary topic entity:
   - **Crystal Videos (Pyrite, Amethyst, Citrine, Tourmaline, Rose Quartz, etc.)**:
     - Every visual must feature natural raw/polished crystals, mineral specimens, meditative crystal setups, executive desk abundance, crystal aura shields, or consecrated temple altars.
     - **STRICT PROHIBITION**: NEVER display planetary photographs (Saturn, Mars, Jupiter, Rahu, Ketu, Sun, Moon) or astrological Kundli birth charts in a Crystal video unless that specific scene dialogue explicitly analyzes that planet.
   - **Rudraksha Videos (5 Mukhi, 7 Mukhi, Gauri Shankar, Rudraksha Mala)**:
     - Every visual must feature authentic Nepali Rudraksha beads, sacred mala beads, meditation with Rudraksha, sacred Gangajal water consecration, or Lord Shiva sanctum altars.
     - **STRICT PROHIBITION**: NEVER display Saturn or random astrology scrolls in a Rudraksha video unless that specific scene explicitly discusses that astrological combination.
   - **Astrology / Kundli / Sade Sati Videos**:
     - Planetary and Kundli chart visuals are permitted ONLY when the video topic specifically addresses those astrological placements.
2. **Scene Dialogue Alignment**: Each scene's image must specifically mirror the spoken insight or benefit of that scene:
   - Hook / Scene 1: Ultra-luxury macro shot of the authentic crystal / bead.
   - Nervous system / Calm / Stress relief: Mindful meditation hands or tranquil zen setting.
   - Abundance / Career / Wealth: Executive mahogany desk in warm golden morning light.
   - Aura Shield / EMF protection: Radiant energetic protective light field around the specimen.
   - Bio-electricity / Frequency / Science: Macro facet refraction with sacred geometric resonance.
   - Caution / Authenticity Test: Laboratory mineral inspection, natural raw crystal facets vs fake synthetic replicas.
   - CTA / Sanctum Sanctorum: Consecrated offering on pure silk cloth before warm glowing brass temple oil lamps (diyas).

## RULE 4: MULTI-TIER REPUTABLE SOURCING PIPELINE
1. **Tier 1 - Live Open Photographic Search (Wikimedia Commons & Openverse)**:
   - Sourced dynamically using targeted subject + scene benefit queries.
   - Downloaded in high resolution, smart-cropped to 1080x1920 (9:16 vertical), and rasterized clean with zero AI metadata headers.
2. **Tier 2 - Dynamic Macro Transformation of Curated Master Plates**:
   - If a curated 4K master plate of the subject exists, subsequent scenes apply unique non-repeating macro focal crops (e.g. 1.8x facet zoom, reflective base angle, warm light-leak optical grade) so no identical frame is ever displayed.
3. **Tier 3 - Procedural Luxury Studio Photographic Canvas**:
   - Custom synthesized canvas tailored to the exact mineral/bead color palette (e.g. Pyrite gold, Amethyst violet, Rudraksha terracotta) with randomized sacred geometry, bokeh particles, and vignette.
   - Guaranteed 100% unique per scene with distinct random seeds.

## RULE 5: PERMANENT BAN ON HARDCODED ENDING IMAGES (ZERO REPEATED ENDINGS)
1. **Scene 6 (Caution/Verification)**:
   - MUST NEVER use a hardcoded generic havan altar (`sacred_havan_flame_altar.jpg` / `4_sacred_havan.jpg`).
   - For Crystals: Must depict mineral authenticity verification, natural growth striations, or gemological inspection macro crops (testing genuine crystal vs fake glass).
   - For Rudraksha: Must depict authentic Nepali mukhi groove inspection (distinguishing real seeds from glued/carved replicas).
   - For Astrology: Must depict Vedic birth chart parchment inspection.
2. **Scene 7 (Call to Action / Consultation)**:
   - MUST NEVER use hardcoded generic temple lamps (`sacred_temple_oil_lamps.jpg` / `5_temple_sanctum.jpg`).
   - For Crystals & Rudraksha: Must feature the consecrated subject specimen resting on dark luxury silk / velvet ground with golden bokeh motes.
   - For Astrology: Must feature an antique consultation parchment scroll (`astrology_consultation_scroll.jpg`) or sacred yantra.
3. **Across Consecutive Videos**:
   - Scene 6 and Scene 7 must NEVER be identical between consecutive videos. Every video must have unique, topic-anchored ending visuals.

## RULE 6: AUTOMATED DISK HYGIENE
1. `DynamicVisualEngine.purge_old_generated_images()` must be called automatically at the start of video generation.
2. Post-upload auto-purge must remove heavy video files and intermediate temporary frames once confirmed live on Instagram.
