# Neodivine Instagram Automation Project Rules

## 1. Content & Topic Intelligence
- **Niche Focus**: Sacred Rudraksha, Healing Crystals, and Vedic Astrology.
- **Tone**: Authentic, informational, and educational. NO fear-mongering, NO fake curses, NO blind internet remedies.
- **Structure**: Exactly 5 educational benefit points with curiosity badges. Zero numbered badges (NO `1 of 5`, NO `1 to 5`).
- **Language & Voice**: Pure Devanagari Hindi vocalized via Sarvam AI (`bulbul:v4-flash`, speaker `arjun`) at exactly 1.20x pace.

## 2. Autonomous Image Rules (STRICT MANDATES)
- **Rule IMG-1: Mandatory Pre-Generation Purge**:
  - Before rendering any Reel, all old temporary images in `assets/generated_broll/`, `output/frames/`, and temporary directories MUST be deleted.
  - Every Reel starts with zero cached image files on disk.
- **Rule IMG-2: Zero Image Repetition**:
  - Every scene in a Reel MUST have a 100% unique, distinct image file.
  - No two scenes in the same video may ever share or display the same image.
  - Scene 6 and Scene 7 MUST NEVER repeat the same generic Havan altar and Temple oil lamps across videos.
  - An automated verification assertion (`len(set(scene_images)) == len(scene_images)`) strictly halts composition if any duplicate is detected.
- **Rule IMG-3: 100% Contextual Relevance (Zero Out-of-Context Images)**:
  - Every visual MUST feature the specific crystal, rudraksha, or gemstone being discussed.
  - NEVER insert planetary images (Saturn, Mars, Jupiter, Moon, Sun, Rahu, Ketu) or ancient Kundli parchment charts into Crystal or Rudraksha videos unless explicitly named in that specific scene's spoken dialogue.
  - Each scene's visual must match that scene's spoken benefit (e.g. calm meditation, executive desk wealth, aura protection, sacred altar).
- **Rule IMG-4: Multi-Tier Sourcing**:
  - Tier 1: Live Wikimedia & Openverse photo search for authentic mineral/bead specimens.
  - Tier 2: Dynamic macro focal crops of curated 4K master plates.
  - Tier 3: Procedural luxury studio photographic canvases with randomized sacred geometry and golden bokeh.

## 3. Metadata & Publishing
- **Metadata Sanitization**: All MP4 video outputs have synthetic tags stripped and are stamped with authentic Apple iPhone 15 Pro Max QuickTime metadata.
- **Cloud Independence**: GitHub Actions runs the entire pipeline autonomously 5x daily. No local PC power is required.
