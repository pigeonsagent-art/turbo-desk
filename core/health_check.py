"""
PC Health Check - Aggregates system health metrics: disk health, RAM usage,
CPU temp, startup count, junk size, last clean date, Windows update status.
"""
import os
import sys
import subprocess
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False


HEALTH_STATE_FILE = Path(os.environ.get("APPDATA", "")) / "PCPolish" / "health_state.json"


class HealthMetric:
    def __init__(self, name: str, value, unit: str, status: str, detail: str = ""):
        self.name = name
        self.value = value
        self.unit = unit
        self.status = status    # 'good', 'warning', 'critical'
        self.detail = detail

    @property
    def color(self) -> str:
        return {"good": "#2ecc71", "warning": "#f39c12", "critical": "#e74c3c"}.get(self.status, "#aaa")


class HealthCheckResult:
    def __init__(self):
        self.metrics: List[HealthMetric] = []
        self.score: int = 100
        self.issues: List[str] = []
        self.timestamp = datetime.now()

    def add(self, metric: HealthMetric):
        self.metrics.append(metric)
        if metric.status == "warning":
            self.score = max(0, self.score - 10)
            self.issues.append(f"⚠  {metric.name}: {metric.detail or metric.value}")
        elif metric.status == "critical":
            self.score = max(0, self.score - 25)
            self.issues.append(f"✖  {metric.name}: {metric.detail or metric.value}")

    @property
    def grade(self) -> str:
        if self.score >= 90: return "Excellent"
        if self.score >= 70: return "Good"
        if self.score >= 50: return "Fair"
        return "Poor"


class HealthCheck:
    def __init__(self):
        self.last_result: Optional[HealthCheckResult] = None

    def run(self, progress_cb=None) -> HealthCheckResult:
        result = HealthCheckResult()
        checks = [
            ("Disk Space", self._check_disk_space),
            ("RAM Usage", self._check_ram),
            ("CPU Load", self._check_cpu),
            ("Startup Programs", self._check_startup_count),
            ("Junk Files", self._check_junk_estimate),
            ("Last Cleaned", self._check_last_clean),
            ("Windows Updates", self._check_windows_updates),
            ("Browser Junk", self._check_browser_junk),
            ("Temp Files", self._check_temp_files),
            ("Registry Issues", self._check_registry_health),
        ]
        for name, fn in checks:
            if progress_cb:
                progress_cb(name)
            try:
                metric = fn()
                if metric:
                    result.add(metric)
            except Exception as e:
                result.add(HealthMetric(name, "Error", "", "warning", str(e)))

        self.last_result = result
        self._save_state(result)
        return result

    # ------------------------------------------------------------------ #
    # Individual checks
    # ------------------------------------------------------------------ #
    def _check_disk_space(self) -> HealthMetric:
        if not PSUTIL_OK:
            return HealthMetric("Disk Space", "N/A", "", "warning", "psutil not installed")
        usage = psutil.disk_usage("C:\\")
        pct = usage.percent
        free_gb = usage.free / 1024**3
        status = "good" if pct < 75 else ("warning" if pct < 90 else "critical")
        return HealthMetric(
            "Disk Space (C:)", f"{pct:.1f}", "%",
            status, f"{free_gb:.1f} GB free"
        )

    def _check_ram(self) -> HealthMetric:
        if not PSUTIL_OK:
            return HealthMetric("RAM Usage", "N/A", "", "warning")
        vm = psutil.virtual_memory()
        pct = vm.percent
        status = "good" if pct < 70 else ("warning" if pct < 85 else "critical")
        return HealthMetric(
            "RAM Usage", f"{pct:.1f}", "%",
            status, f"{vm.used/1024**3:.1f}/{vm.total/1024**3:.1f} GB used"
        )

    def _check_cpu(self) -> HealthMetric:
        if not PSUTIL_OK:
            return HealthMetric("CPU Load", "N/A", "", "warning")
        import time
        pct = psutil.cpu_percent(interval=1)
        status = "good" if pct < 60 else ("warning" if pct < 85 else "critical")
        return HealthMetric("CPU Load", f"{pct:.1f}", "%", status)

    def _check_startup_count(self) -> HealthMetric:
        count = 0
        if sys.platform == "win32":
            try:
                import winreg
                for is_hklm, kp in [
                    (True, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
                    (False, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
                ]:
                    hive = winreg.HKEY_LOCAL_MACHINE if is_hklm else winreg.HKEY_CURRENT_USER
                    try:
                        key = winreg.OpenKey(hive, kp)
                        i = 0
                        while True:
                            try:
                                winreg.EnumValue(key, i)
                                count += 1
                                i += 1
                            except OSError:
                                break
                        winreg.CloseKey(key)
                    except Exception:
                        pass
            except Exception:
                pass
        status = "good" if count <= 10 else ("warning" if count <= 20 else "critical")
        return HealthMetric("Startup Programs", str(count), "items", status,
                            "Many startup items slow boot time" if count > 10 else "")

    def _check_junk_estimate(self) -> HealthMetric:
        junk_mb = self._fast_junk_scan()
        status = "good" if junk_mb < 500 else ("warning" if junk_mb < 2000 else "critical")
        return HealthMetric(
            "Junk Files", f"{junk_mb:.0f}", "MB", status,
            "Run Custom Cleaner to free space" if junk_mb > 500 else ""
        )

    def _fast_junk_scan(self) -> float:
        total = 0
        paths = [
            os.environ.get("TEMP", ""),
            r"C:\Windows\Temp",
        ]
        for p in paths:
            if not p or not os.path.isdir(p):
                continue
            for root, _, files in os.walk(p):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except Exception:
                        pass
        return total / 1024**2

    def _check_last_clean(self) -> HealthMetric:
        state = self._load_state()
        last = state.get("last_clean")
        if not last:
            return HealthMetric("Last Cleaned", "Never", "", "warning", "Run a clean to improve performance")
        try:
            dt = datetime.fromisoformat(last)
            days = (datetime.now() - dt).days
            status = "good" if days < 7 else ("warning" if days < 30 else "critical")
            return HealthMetric("Last Cleaned", f"{days}", "days ago", status)
        except Exception:
            return HealthMetric("Last Cleaned", "Unknown", "", "warning")

    def _check_windows_updates(self) -> HealthMetric:
        if sys.platform != "win32":
            return HealthMetric("Windows Updates", "N/A", "", "good")
        try:
            script = "(New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher().Search('IsInstalled=0 and Type=\\'Software\\'').Updates.Count"
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=20
            )
            count = int(result.stdout.strip())
            status = "good" if count == 0 else ("warning" if count < 5 else "critical")
            return HealthMetric("Pending Updates", str(count), "updates", status,
                                "Windows updates improve security" if count > 0 else "")
        except Exception:
            return HealthMetric("Windows Updates", "Unknown", "", "warning")

    def _check_browser_junk(self) -> HealthMetric:
        size = 0
        appdata = os.environ.get("LOCALAPPDATA", "")
        browser_cache_paths = [
            os.path.join(appdata, "Google", "Chrome", "User Data", "Default", "Cache"),
            os.path.join(appdata, "Microsoft", "Edge", "User Data", "Default", "Cache"),
        ]
        for p in browser_cache_paths:
            if os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for f in files:
                        try:
                            size += os.path.getsize(os.path.join(root, f))
                        except Exception:
                            pass
        mb = size / 1024**2
        status = "good" if mb < 200 else ("warning" if mb < 1000 else "critical")
        return HealthMetric("Browser Junk", f"{mb:.0f}", "MB", status)

    def _check_temp_files(self) -> HealthMetric:
        temp = os.environ.get("TEMP", "")
        count = 0
        if temp and os.path.isdir(temp):
            try:
                count = len(os.listdir(temp))
            except Exception:
                pass
        status = "good" if count < 50 else ("warning" if count < 200 else "critical")
        return HealthMetric("Temp File Count", str(count), "files", status)

    def _check_registry_health(self) -> HealthMetric:
        """Quick scan — counts invalid startup Run entries (same logic as RegistryCleaner)."""
        from core.registry_cleaner import RegistryCleaner
        bad = 0
        if sys.platform == "win32":
            try:
                import winreg
                kp = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
                for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                    try:
                        key = winreg.OpenKey(hive, kp)
                        i = 0
                        while True:
                            try:
                                _, val, _ = winreg.EnumValue(key, i)
                                exe = RegistryCleaner._parse_exe_path(str(val))
                                if exe and not os.path.exists(exe):
                                    bad += 1
                                i += 1
                            except OSError:
                                break
                        winreg.CloseKey(key)
                    except Exception:
                        pass
            except Exception:
                pass
        status = "good" if bad == 0 else ("warning" if bad < 5 else "critical")
        return HealthMetric("Registry Issues", str(bad), "invalid entries", status)

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def record_clean(self):
        state = self._load_state()
        state["last_clean"] = datetime.now().isoformat()
        self._save_state_dict(state)

    def _save_state(self, result: HealthCheckResult):
        state = self._load_state()
        state["last_check"] = result.timestamp.isoformat()
        state["last_score"] = result.score
        self._save_state_dict(state)

    @staticmethod
    def _load_state() -> Dict:
        if HEALTH_STATE_FILE.exists():
            try:
                with open(HEALTH_STATE_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @staticmethod
    def _save_state_dict(state: Dict):
        HEALTH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HEALTH_STATE_FILE, "w") as f:
            json.dump(state, f)
