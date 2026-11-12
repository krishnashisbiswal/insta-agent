import logging
from datetime import datetime, time as dtime, timedelta
import zoneinfo
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Instagram algorithm peak engagement windows (Local time)
# Posting 15-30 minutes before the peak allows initial indexing and test impressions.
PEAK_WINDOWS = [
    {"name": "Morning Commute", "start": (8, 30), "post_at": (8, 45), "end": (9, 30)},
    {"name": "Lunch Break", "start": (12, 30), "post_at": (12, 45), "end": (13, 30)},
    {"name": "Evening Prime", "start": (18, 30), "post_at": (18, 45), "end": (20, 30)},
    {"name": "Late Night Relax", "start": (21, 30), "post_at": (22, 0), "end": (22, 45)},
]


def get_tz(timezone_str: str = "Asia/Kolkata"):
    """Robust timezone resolver with universal UTC+5:30 fallback for IST."""
    try:
        import zoneinfo
        return zoneinfo.ZoneInfo(timezone_str)
    except Exception:
        from datetime import timezone, timedelta
        if timezone_str == "Asia/Kolkata":
            return timezone(timedelta(hours=5, minutes=30), name="IST")
        return timezone.utc


def get_current_time(timezone_str: str = "Asia/Kolkata") -> datetime:
    """Get timezone-aware current datetime."""
    try:
        tz = get_tz(timezone_str)
        return datetime.now(tz)
    except Exception:
        return datetime.now()


def get_next_optimal_post_time(timezone_str: str = "Asia/Kolkata") -> Tuple[datetime, str]:
    """
    Find the upcoming peak posting time and window name.
    Returns:
    - (datetime of next post, window_name)
    """
    now = get_current_time(timezone_str)
    today = now.date()

    candidates = []

    # Check remaining windows today
    for w in PEAK_WINDOWS:
        hour, minute = w["post_at"]
        post_time = datetime(today.year, today.month, today.day, hour, minute, tzinfo=now.tzinfo)
        if post_time > now:
            candidates.append((post_time, w["name"]))

    # If no windows remain today, look at tomorrow's first window
    if not candidates:
        tomorrow = today + timedelta(days=1)
        first_w = PEAK_WINDOWS[0]
        hour, minute = first_w["post_at"]
        post_time = datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour, minute, tzinfo=now.tzinfo)
        candidates.append((post_time, first_w["name"]))

    candidates.sort(key=lambda x: x[0])
    return candidates[0]


def is_in_optimal_window(timezone_str: str = "Asia/Kolkata") -> Tuple[bool, str]:
    """Check if current time falls within one of the peak engagement zones."""
    now = get_current_time(timezone_str)
    current_time_val = now.time()

    for w in PEAK_WINDOWS:
        sh, sm = w["start"]
        eh, em = w["end"]
        start_time = dtime(sh, sm)
        end_time = dtime(eh, em)

        if start_time <= current_time_val <= end_time:
            return True, w["name"]

    return False, "Off-Peak"


def seconds_until_next_optimal(timezone_str: str = "Asia/Kolkata") -> Tuple[int, str, datetime]:
    """Calculate exact seconds until next optimal posting window."""
    now = get_current_time(timezone_str)
    next_time, window_name = get_next_optimal_post_time(timezone_str)
    delta = (next_time - now).total_seconds()
    return max(0, int(delta)), window_name, next_time


if __name__ == "__main__":
    now = get_current_time("Asia/Kolkata")
    print(f"Current Time ({now.tzinfo}):", now.strftime("%Y-%m-%d %H:%M:%S"))
    in_peak, peak_name = is_in_optimal_window("Asia/Kolkata")
    print("Is Currently in Peak Window?:", in_peak, f"({peak_name})")
    secs, win_name, nxt = seconds_until_next_optimal("Asia/Kolkata")
    print(f"Next Optimal Post: {nxt.strftime('%Y-%m-%d %H:%M:%S')} ({win_name}) in {secs // 60} mins")
