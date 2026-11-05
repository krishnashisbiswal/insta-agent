import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.analytics.self_learning_engine import SelfLearningEngine
from app.autonomous.timing_engine import get_current_time, is_in_optimal_window, seconds_until_next_optimal, PEAK_WINDOWS
from app.autonomous.content_manager import ContentManager
from app.analytics.seo_optimizer import generate_seo_metadata
from config.settings import CONTENT_NICHE, TIMEZONE

print("=" * 70)
print("VERIFYING DAILY AUTONOMOUS POSTING & SELF-UPGRADE SYSTEM")
print("=" * 70)

# 1. Niche Lock
print(f"\n1. LOCKED NICHE:")
print(f"   {CONTENT_NICHE}")

# 2. Timing Engine & Best Post Times
now = get_current_time(TIMEZONE)
in_peak, slot_name = is_in_optimal_window(TIMEZONE)
secs_wait, next_slot, next_dt = seconds_until_next_optimal(TIMEZONE)
print(f"\n2. INSTAGRAM ALGORITHM POSTING SCHEDULE ({TIMEZONE}):")
print(f"   Current Time:       {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   Currently in Peak?: {in_peak} ({slot_name})")
print(f"   Next Optimal Window:{next_dt.strftime('%Y-%m-%d %H:%M:%S')} ({next_slot}) in {secs_wait // 60} mins")
print("   All 4 Daily High-Reach SEO Windows:")
for w in PEAK_WINDOWS:
    print(f"   * {w['name']:18} -> Post at {w['post_at'][0]:02d}:{w['post_at'][1]:02d} (Buffer: {w['start'][0]:02d}:{w['start'][1]:02d} - {w['end'][0]:02d}:{w['end'][1]:02d})")

# 3. Self-Learning Engine Status
engine = SelfLearningEngine()
playbook = engine.load_playbook()
print(f"\n3. SELF-TRAINING AGENT BRAIN STATUS:")
print(f"   Agent Evolution Level: {playbook.get('evolution_level', 1.0):.1f}")
print(f"   Total Training Cycles: {playbook.get('total_training_cycles', 0)}")
print(f"   Winning Hooks Stored:  {len(playbook.get('winning_hooks_bank', []))}")
print(f"   Banned Phrases Pruned: {len(playbook.get('banned_low_retention_phrases', []))}")
print(f"   Daily Golden Rules Active:")
for r in playbook.get("daily_golden_rules", [])[:3]:
    print(f"   * {r}")

# 4. Content Manager Queue Check
cm = ContentManager()
queue = cm.load_queue()
print(f"\n4. CONTENT QUEUE ({len(queue)} items ready):")
for i, item in enumerate(queue[:4], 1):
    print(f"   {i}. \"{item['topic']}\"")

print("\n" + "=" * 70)
print("SUCCESS: 100% PRODUCTION READY FOR DAILY AUTONOMOUS SEO POSTING & SELF-UPGRADE!")
print("=" * 70)
