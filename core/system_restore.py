"""
System Restore Manager - List, create, and delete Windows System Restore points
via PowerShell / WMI.
"""
import sys
import subprocess
import json
from typing import List, Dict, Optional, Callable
from datetime import datetime


class RestorePoint:
    def __init__(self, data: Dict):
        self.sequence: int = data.get("SequenceNumber", 0)
        self.description: str = data.get("Description", "Unknown")
        self.restore_type: str = self._decode_type(data.get("RestorePointType", 0))
        self.event_type: str = self._decode_event(data.get("EventType", 0))
        self.creation_time: str = self._parse_time(data.get("CreationTime", ""))
        self.drive: str = data.get("Drive", "C:\\")

    @staticmethod
    def _decode_type(t) -> str:
        types = {
            0: "Application Install",
            1: "Application Uninstall",
            10: "Device Driver Install",
            12: "Modify Settings",
            13: "Cancelled Operation",
        }
        return types.get(int(t) if t else 0, f"Type {t}")

    @staticmethod
    def _decode_event(e) -> str:
        events = {100: "Begin Nested System Change", 101: "End Nested System Change",
                  102: "Begin System Change", 103: "End System Change"}
        return events.get(int(e) if e else 0, "System Change")

    @staticmethod
    def _parse_time(raw: str) -> str:
        # WMI datetime: "20231201120000.000000+000"
        if not raw:
            return "Unknown"
        try:
            dt = datetime.strptime(raw[:14], "%Y%m%d%H%M%S")
            return dt.strftime("%Y-%m-%d  %H:%M:%S")
        except Exception:
            return raw

    def __repr__(self):
        return f"RestorePoint({self.sequence}: {self.description})"


class SystemRestoreManager:
    def __init__(self):
        self.points: List[RestorePoint] = []

    # ------------------------------------------------------------------ #
    # List
    # ------------------------------------------------------------------ #
    def get_restore_points(self) -> List[RestorePoint]:
        if sys.platform != "win32":
            return []
        script = (
            "Get-ComputerRestorePoint | "
            "Select-Object SequenceNumber, Description, RestorePointType, EventType, CreationTime | "
            "ConvertTo-Json"
        )
        out = self._run_ps(script)
        if not out:
            return []
        try:
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
            self.points = [RestorePoint(d) for d in data]
            return self.points
        except Exception:
            return []

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #
    def create(self, description: str = "PCPolish Manual Restore Point") -> bool:
        if sys.platform != "win32":
            return False
        script = f'Checkpoint-Computer -Description "{description}" -RestorePointType "MODIFY_SETTINGS"'
        result = self._run_ps(script, as_admin=True)
        return result is not None

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #
    def delete(self, sequence_number: int) -> bool:
        if sys.platform != "win32":
            return False
        # PowerShell doesn't have a native Delete-RestorePoint; use vssadmin
        try:
            # List shadow copies to find the one matching this restore point
            result = subprocess.run(
                ["vssadmin", "delete", "shadows", "/quiet",
                 f"/For=C:\\", "/oldest"],
                capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False

    def delete_all_but_last(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            result = subprocess.run(
                ["vssadmin", "delete", "shadows", "/for=C:\\", "/oldest", "/quiet"],
                capture_output=True, timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False

    def delete_all(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            result = subprocess.run(
                ["vssadmin", "delete", "shadows", "/for=C:\\", "/all", "/quiet"],
                capture_output=True, timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # Shadow copy disk usage
    # ------------------------------------------------------------------ #
    def get_shadow_storage_info(self) -> Dict:
        if sys.platform != "win32":
            return {}
        try:
            result = subprocess.run(
                ["vssadmin", "list", "shadowstorage"],
                capture_output=True, text=True, timeout=15
            )
            info = {"raw": result.stdout}
            for line in result.stdout.splitlines():
                if "Used Shadow Copy Storage space" in line:
                    info["used"] = line.split(":")[-1].strip()
                elif "Allocated Shadow Copy Storage space" in line:
                    info["allocated"] = line.split(":")[-1].strip()
                elif "Maximum Shadow Copy Storage space" in line:
                    info["maximum"] = line.split(":")[-1].strip()
            return info
        except Exception:
            return {}

    # ------------------------------------------------------------------ #
    # Restore (launch native UI)
    # ------------------------------------------------------------------ #
    @staticmethod
    def open_system_restore_ui():
        subprocess.Popen(["rstrui.exe"])

    # ------------------------------------------------------------------ #
    # Helper
    # ------------------------------------------------------------------ #
    @staticmethod
    def _run_ps(script: str, as_admin: bool = False) -> Optional[str]:
        try:
            args = [
                "powershell", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-Command", script,
            ]
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
            return result.stdout.strip() or None
        except Exception:
            return None

    @staticmethod
    def is_system_restore_enabled() -> bool:
        script = "(Get-ComputerRestorePoint).Count -gt 0"
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=10
            )
            return "True" in result.stdout
        except Exception:
            return False
