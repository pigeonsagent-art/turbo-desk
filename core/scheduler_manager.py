"""
Scheduler Manager - Runs background scheduled cleaning tasks.
Supports daily, weekly, and on-idle triggers.
"""
import os
import sys
import json
import time
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional
from datetime import datetime, timedelta

try:
    import schedule
    SCHEDULE_OK = True
except ImportError:
    SCHEDULE_OK = False


CONFIG_FILE = Path(os.environ.get("APPDATA", "")) / "PCPolish" / "schedule.json"

DEFAULT_CONFIG = {
    "enabled": False,
    "frequency": "weekly",   # daily / weekly / on_idle
    "day_of_week": "Monday",
    "time_of_day": "02:00",
    "clean_types": ["temp_files", "browser_cache"],
    "last_run": None,
    "next_run": None,
}


class SchedulerManager:
    def __init__(self, clean_callback: Optional[Callable[[], None]] = None):
        self.config: Dict = self._load_config()
        self.clean_callback = clean_callback
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

    # ------------------------------------------------------------------ #
    # Config
    # ------------------------------------------------------------------ #
    def get_config(self) -> Dict:
        return self.config.copy()

    def save_config(self, config: Dict):
        self.config.update(config)
        self.config["next_run"] = self._compute_next_run()
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)

    def _load_config(self) -> Dict:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    data = json.load(f)
                    merged = DEFAULT_CONFIG.copy()
                    merged.update(data)
                    return merged
            except Exception:
                pass
        return DEFAULT_CONFIG.copy()

    def _compute_next_run(self) -> Optional[str]:
        freq = self.config.get("frequency", "weekly")
        t_str = self.config.get("time_of_day", "02:00")
        try:
            h, m = map(int, t_str.split(":"))
        except Exception:
            h, m = 2, 0
        now = datetime.now()
        if freq == "daily":
            next_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if next_dt <= now:
                next_dt += timedelta(days=1)
        elif freq == "weekly":
            day_map = {
                "Monday": 0, "Tuesday": 1, "Wednesday": 2,
                "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6,
            }
            target_day = day_map.get(self.config.get("day_of_week", "Monday"), 0)
            days_ahead = (target_day - now.weekday()) % 7
            if days_ahead == 0:
                next_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if next_dt <= now:
                    next_dt += timedelta(weeks=1)
            else:
                next_dt = (now + timedelta(days=days_ahead)).replace(hour=h, minute=m, second=0, microsecond=0)
        else:
            return None
        return next_dt.isoformat()

    # ------------------------------------------------------------------ #
    # Start / Stop
    # ------------------------------------------------------------------ #
    def start(self) -> bool:
        if self._running or not self.config.get("enabled"):
            return False
        if not SCHEDULE_OK:
            # Fallback thread-based scheduler
            self._start_fallback()
            return True
        self._setup_schedule()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._running = True
        return True

    def stop(self):
        self._stop_event.set()
        self._running = False
        if SCHEDULE_OK:
            schedule.clear("pcpolish")

    def _setup_schedule(self):
        if not SCHEDULE_OK:
            return
        schedule.clear("pcpolish")
        freq = self.config.get("frequency", "weekly")
        t_str = self.config.get("time_of_day", "02:00")

        if freq == "daily":
            schedule.every().day.at(t_str).do(self._execute).tag("pcpolish")
        elif freq == "weekly":
            day = self.config.get("day_of_week", "Monday").lower()
            getattr(schedule.every(), day).at(t_str).do(self._execute).tag("pcpolish")

    def _run_loop(self):
        while not self._stop_event.is_set():
            if SCHEDULE_OK:
                schedule.run_pending()
            time.sleep(60)

    def _start_fallback(self):
        """Simple thread-based scheduler without the schedule library."""
        def _loop():
            while not self._stop_event.is_set():
                if self._should_run_now():
                    self._execute()
                time.sleep(60)
        self._stop_event.clear()
        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()
        self._running = True

    def _should_run_now(self) -> bool:
        next_run = self.config.get("next_run")
        if not next_run:
            return False
        try:
            dt = datetime.fromisoformat(next_run)
            return datetime.now() >= dt
        except Exception:
            return False

    def _execute(self):
        """Run the scheduled clean."""
        self.config["last_run"] = datetime.now().isoformat()
        self.config["next_run"] = self._compute_next_run()
        self._save_config_silent()
        if self.clean_callback:
            try:
                self.clean_callback()
            except Exception:
                pass

    def _save_config_silent(self):
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Status
    # ------------------------------------------------------------------ #
    @property
    def is_running(self) -> bool:
        return self._running

    def get_next_run_str(self) -> str:
        nr = self.config.get("next_run")
        if not nr:
            return "Not scheduled"
        try:
            dt = datetime.fromisoformat(nr)
            return dt.strftime("%A, %Y-%m-%d at %H:%M")
        except Exception:
            return "Unknown"

    def get_last_run_str(self) -> str:
        lr = self.config.get("last_run")
        if not lr:
            return "Never"
        try:
            dt = datetime.fromisoformat(lr)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return "Unknown"
