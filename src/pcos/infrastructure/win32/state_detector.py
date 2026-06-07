"""pcos/state/detector.py — merged state detector.

Classification engine from your original StateDetector (keyword lists,
app categories, hysteresis, override file). DEPLETED detection and focus
block tracking from the PRD spec. SessionStateLabel maps to PRD states.

State mapping (your labels → PRD labels):
  coding/terminal/work_browsing/writing/morning_focus → DEEP_WORK
  distraction/distracted                              → DISTRACTED
  away (idle > 15 min)                               → IDLE
  communication/reactive                             → FREE  (interruption mode)
  post_lunch_dip/neutral/evening                     → FREE
  wind_down                                          → WIND_DOWN
  [PRD DEPLETED criteria override all above]         → DEPLETED
  [explicit meeting flag]                            → MEETING
"""
from __future__ import annotations
import json
import time
from collections import deque
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pcos import config
from pcos.state import session as sess_mod
from pcos.models import SessionStateLabel

# ── keyword lists (from your original) ──────────────────────────────────────

WORK_KEYWORDS = [
    "stackoverflow", "github", "docs", "documentation", "api",
    "mdn", "w3schools", "gitlab", "jira", "confluence",
    "notion", "figma", "code", "python", "javascript", "react",
    "tutorial", "guide", "reference",
]
DISTRACTION_KEYWORDS = [
    "youtube", "reddit", "twitter", "facebook", "instagram",
    "twitch", "netflix", "hacker news", "9gag", "imgur",
    "news", "bbc", "cnn", "wikipedia", "amazon", "shopping",
]
COMMUNICATION_KEYWORDS = [
    "gmail", "outlook", "teams", "slack", "discord", "whatsapp",
    "mail", "inbox", "calendar", "zoom",
]

CODING_EXES = {
    "code.exe", "pycharm64.exe", "devenv.exe", "idea64.exe",
    "sublime_text.exe", "atom.exe", "cursor.exe", "windsurf.exe",
}
TERMINAL_EXES = {"cmd.exe", "powershell.exe", "wt.exe", "alacritty.exe", "windowsterminal.exe"}
COMMS_EXES = {"outlook.exe", "thunderbird.exe", "slack.exe", "teams.exe", "zoom.exe", "discord.exe"}
WRITING_EXES = {"winword.exe", "notepad.exe", "notepad++.exe", "obsidian.exe", "typora.exe", "logseq.exe"}

# ── internal state ───────────────────────────────────────────────────────────

_state_history: deque = deque(maxlen=5)
_current_raw: str = "neutral"
_current_confidence: float = 0.5
_last_change_time: float = time.time()
_last_signals: dict = {}

MIN_DWELL_SECONDS = 120   # hysteresis dwell time


# ── public API ───────────────────────────────────────────────────────────────

def compute_state(
    in_meeting: bool = False,
    wind_down_triggered: bool = False,
) -> SessionStateLabel:
    """Main entry point. Returns PRD SessionStateLabel."""
    global _last_signals

    s = sess_mod.current()

    # Explicit overrides first
    if wind_down_triggered:
        return "WIND_DOWN"
    if in_meeting:
        return "MEETING"

    # Manual override file
    override = _check_override()
    if override:
        return _map_to_prd(override)

    # Read signals
    signals = _collect_signals()
    _last_signals = signals

    if signals["idle_minutes"] > config.get("state", "idle_threshold_minutes", 10):
        sess_mod.touch()  # don't touch — just let it be idle
        return "IDLE"

    # Touch session with current app
    sess_mod.touch(app=signals["process_name"])

    # DEPLETED check (PRD spec — overrides classification)
    if _is_depleted(s):
        return "DEPLETED"

    # Classify via your category engine
    raw, _conf, _reason = _classify(signals)
    _apply_hysteresis(raw, _conf, _reason)

    return _map_to_prd(_current_raw)


def last_signals() -> dict:
    return _last_signals


# ── classification (your logic) ──────────────────────────────────────────────

def _collect_signals() -> dict:
    now = datetime.now()
    idle_mins = _get_idle_minutes()
    title, exe, _ = _get_active_window()
    category = _get_app_category(exe, title)
    return {
        "hour": now.hour,
        "idle_minutes": idle_mins,
        "window_title": title[:100],
        "process_name": exe,
        "category": category,
    }


def _get_idle_minutes() -> float:
    try:
        import win32api
        idle_ticks = win32api.GetLastInputInfo()
        now_ticks = win32api.GetTickCount()
        return (now_ticks - idle_ticks) / 60000.0
    except Exception:
        # Fallback: use session last_activity
        s = sess_mod.current()
        if s is None:
            return 999.0
        return (time.time() - s.last_activity) / 60.0


def _get_active_window() -> tuple[str, str, int]:
    try:
        import win32gui, win32process, psutil
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) if hwnd else ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        exe = psutil.Process(pid).name()
        return title, exe, hwnd
    except Exception:
        return "", "unknown", 0


def _classify_browser(title: str, exe: str) -> str | None:
    exe_l = exe.lower()
    if not any(b in exe_l for b in ("chrome", "edge", "firefox", "brave", "msedge")):
        return None
    tl = title.lower()
    for kw in COMMUNICATION_KEYWORDS:
        if kw in tl:
            return "communication"
    for kw in WORK_KEYWORDS:
        if kw in tl:
            return "work_browsing"
    for kw in DISTRACTION_KEYWORDS:
        if kw in tl:
            return "distraction"
    return "neutral_browsing"


def _get_app_category(exe: str, title: str) -> str:
    browser_cat = _classify_browser(title, exe)
    if browser_cat:
        return browser_cat
    exe_l = exe.lower()
    if exe_l in CODING_EXES:
        return "coding"
    if exe_l in TERMINAL_EXES:
        return "terminal"
    if exe_l in COMMS_EXES:
        return "communication"
    if exe_l in WRITING_EXES:
        return "writing"
    if exe_l == "explorer.exe":
        return "file_management"
    return "other"


def _classify(signals: dict) -> tuple[str, float, str]:
    """Your compute_raw_state logic, unchanged."""
    hour = signals["hour"]
    idle = signals["idle_minutes"]
    cat  = signals["category"]

    if idle > 15:
        return "away", 0.95, f"idle_{idle:.0f}min"
    if idle > 5 and cat not in ("coding", "terminal"):
        return "distracted", 0.75, f"idle_{idle:.0f}min"

    if cat == "communication":
        return "reactive", 0.8, "communication_app"
    if cat == "distraction":
        return "distracted", 0.85, "browser_distraction"
    if cat == "work_browsing":
        return ("deep_work", 0.7, "work_browsing") if hour < 18 else ("wind_down", 0.6, "work_browsing_evening")
    if cat == "coding":
        return ("wind_down", 0.7, "coding_late") if hour >= 22 else ("deep_work", 0.85, "coding")
    if cat == "terminal":
        return "deep_work", 0.7, "terminal"
    if cat == "writing":
        if hour < 12:
            return "morning_focus", 0.8, "writing"
        if 12 <= hour < 14:
            return "post_lunch_dip", 0.6, "writing"
        return "deep_work", 0.65, "writing"

    # time-of-day fallback
    if 6 <= hour < 11:   return "morning_focus", 0.6, "time_of_day"
    if 11 <= hour < 14:  return "neutral", 0.5, "time_of_day"
    if 14 <= hour < 17:  return "post_lunch_dip", 0.6, "time_of_day"
    if 17 <= hour < 21:  return "evening", 0.5, "time_of_day"
    return "wind_down", 0.7, "time_of_day"


# ── hysteresis (your logic) ──────────────────────────────────────────────────

def _apply_hysteresis(new_state: str, new_conf: float, reason: str):
    global _current_raw, _current_confidence, _last_change_time

    now = time.time()
    elapsed = now - _last_change_time

    if new_state == _current_raw:
        _current_confidence = _current_confidence * 0.7 + new_conf * 0.3
        _state_history.append(new_state)
        return

    urgent = new_state == "away" or (new_state == "deep_work" and _current_raw == "distracted")
    if elapsed < MIN_DWELL_SECONDS and not urgent:
        return  # reject transient change

    _state_history.append(new_state)
    if _state_history.count(new_state) >= 3 or urgent:
        _current_raw = new_state
        _current_confidence = new_conf
        _last_change_time = now


# ── PRD DEPLETED criteria ────────────────────────────────────────────────────

def _is_depleted(s) -> bool:
    if s is None:
        return False
    dur_hours = sess_mod.focus_duration_minutes() / 60.0
    dep_hours = config.get("state", "depletion_hours", 2.5)
    if dur_hours < dep_hours:
        return False

    dep_thresh = config.get("state", "depletion_focus_threshold", 0.5)
    dep_break  = config.get("state", "depletion_break_minutes", 8)

    recent_avg = sess_mod.recent_focus_blocks_avg(3600)
    peak = s.peak_focus_block if s.peak_focus_block > 0 else 1.0
    last_gap_min = (time.time() - s.last_activity) / 60.0
    no_recent_break = last_gap_min < dep_break

    return recent_avg < peak * dep_thresh and no_recent_break


# ── state mapping ─────────────────────────────────────────────────────────────

_RAW_TO_PRD: dict[str, SessionStateLabel] = {
    "deep_work":      "DEEP_WORK",
    "morning_focus":  "DEEP_WORK",
    "coding":         "DEEP_WORK",
    "terminal":       "DEEP_WORK",
    "work_browsing":  "DEEP_WORK",
    "writing":        "DEEP_WORK",
    "distracted":     "DISTRACTED",
    "distraction":    "DISTRACTED",
    "away":           "IDLE",
    "reactive":       "FREE",
    "communication":  "FREE",
    "neutral":        "FREE",
    "neutral_browsing": "FREE",
    "post_lunch_dip": "FREE",
    "evening":        "FREE",
    "file_management":"FREE",
    "other":          "FREE",
    "wind_down":      "WIND_DOWN",
}


def _map_to_prd(raw: str) -> SessionStateLabel:
    return _RAW_TO_PRD.get(raw, "FREE")


# ── override file ─────────────────────────────────────────────────────────────

def _check_override() -> str | None:
    try:
        override_file = config.data_dir() / "state_override.json"
        if override_file.exists():
            data = json.loads(override_file.read_text())
            if data.get("expires", 0) > time.time():
                return data.get("state")
    except Exception:
        pass
    return None