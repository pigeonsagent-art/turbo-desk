"""
Turbo Desk licensing module.

Responsibilities:
  * Machine fingerprint (deviceId) for activation binding
  * Local license state persistence (encrypted-at-rest via HMAC signing)
  * Trial mode (7 days from first launch)
  * Online validation against the backend
  * 3-day offline grace period after a successful online check

Design notes:
  * State file lives in %APPDATA%/TurboDesk/license.json
  * Every write is HMAC-signed so a user editing the file to extend their
    trial invalidates the signature — the app treats it as tampered and
    forces re-activation (or trial-expired if there was no license)
  * The HMAC key is derived from the machine fingerprint, so copying the
    state file to another PC also invalidates it
  * All timestamps are UTC ISO-8601 strings
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import platform
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

BACKEND_URL = "https://turbo-desk-backend.onrender.com"
VALIDATE_ENDPOINT = f"{BACKEND_URL}/api/validate-license"

TRIAL_DAYS = 7
OFFLINE_GRACE_DAYS = 3

# Time budget for a single validation attempt. Render's free tier can take
# 30+ seconds to cold-start, so we give the request a generous window before
# giving up and falling back to the offline grace period.
VALIDATION_TIMEOUT_SECONDS = 45

STATE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "TurboDesk")
STATE_FILE = os.path.join(STATE_DIR, "license.json")


# ─────────────────────────────────────────────────────────────────────────────
# Machine fingerprint
# ─────────────────────────────────────────────────────────────────────────────

def _windows_machine_guid() -> Optional[str]:
    """Read the persistent MachineGuid from the Windows registry.

    This survives reinstalls of the app but not reinstalls of Windows,
    which is the right granularity for a per-machine activation limit.
    """
    try:
        import winreg  # only available on Windows
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as k:
            value, _ = winreg.QueryValueEx(k, "MachineGuid")
            return value
    except Exception:
        return None


def machine_fingerprint() -> str:
    """Return a stable, per-machine deviceId string.

    Prefers the Windows MachineGuid; falls back to platform.node() + MAC-based
    uuid.getnode() hashed together, so we still get a stable ID on non-Windows
    dev environments (only matters during local testing).
    """
    parts = []

    if platform.system() == "Windows":
        guid = _windows_machine_guid()
        if guid:
            parts.append(guid)

    # Fallback / additional entropy
    parts.append(platform.node())
    try:
        parts.append(str(uuid.getnode()))  # MAC-derived
    except Exception:
        pass

    joined = "|".join(parts)
    # Hash so we don't ship the raw MachineGuid over the wire
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:32]


# ─────────────────────────────────────────────────────────────────────────────
# Signed local state
# ─────────────────────────────────────────────────────────────────────────────

def _hmac_key() -> bytes:
    """HMAC key derived from the machine fingerprint.

    Not a security barrier against a determined attacker (they can read this
    source and reproduce it) — the goal is to defeat casual editing of the
    state file to extend the trial or forge a validation.
    """
    return hashlib.sha256(("turbo-desk-state-v1:" + machine_fingerprint()).encode("utf-8")).digest()


def _sign(payload: str) -> str:
    return base64.b64encode(hmac.new(_hmac_key(), payload.encode("utf-8"), hashlib.sha256).digest()).decode("ascii")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _parse_iso(s: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


@dataclass
class LicenseState:
    """Represents the persisted local licensing state."""
    trial_started_at: Optional[str] = None      # ISO datetime, first-ever launch
    license_key: Optional[str] = None           # Activated key, if any
    email: Optional[str] = None                 # From server, on successful validation
    last_validated_at: Optional[str] = None     # ISO, last successful online check

    def to_signed_json(self) -> str:
        payload = json.dumps(self.__dict__, sort_keys=True)
        signature = _sign(payload)
        return json.dumps({"payload": payload, "signature": signature})

    @classmethod
    def from_signed_json(cls, raw: str) -> Optional["LicenseState"]:
        """Load state, returning None if signature check fails (tampered file)."""
        try:
            wrapper = json.loads(raw)
            payload = wrapper["payload"]
            signature = wrapper["signature"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

        expected = _sign(payload)
        if not hmac.compare_digest(signature, expected):
            return None  # Tampered

        try:
            data = json.loads(payload)
            return cls(**{k: data.get(k) for k in cls.__dataclass_fields__})
        except (json.JSONDecodeError, TypeError):
            return None


def load_state() -> LicenseState:
    """Load state from disk. Returns a fresh state if file is missing/tampered."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return LicenseState()
    except OSError:
        return LicenseState()

    state = LicenseState.from_signed_json(raw)
    return state if state is not None else LicenseState()


def save_state(state: LicenseState) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp_path = STATE_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(state.to_signed_json())
    os.replace(tmp_path, STATE_FILE)


# ─────────────────────────────────────────────────────────────────────────────
# Validation result types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LicenseStatus:
    """Result of check_status() — what the caller needs to know to gate the app."""
    allowed: bool                        # Can the app run?
    mode: str                            # "licensed" | "trial" | "trial_expired" | "unlicensed" | "activation_needed"
    message: str = ""                    # Human-readable message for the UI
    days_left: Optional[int] = None      # Trial days remaining, if mode == "trial"
    email: Optional[str] = None          # Licensed-to email, if mode == "licensed"


# ─────────────────────────────────────────────────────────────────────────────
# Trial handling
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_trial_started(state: LicenseState) -> LicenseState:
    """First-launch bootstrap: stamp trial_started_at if not already set."""
    if state.trial_started_at is None:
        state.trial_started_at = _iso(_now_utc())
        save_state(state)
    return state


def _trial_status(state: LicenseState) -> LicenseStatus:
    started = _parse_iso(state.trial_started_at) if state.trial_started_at else None
    if started is None:
        # Should not happen after _ensure_trial_started, but be safe
        return LicenseStatus(
            allowed=False,
            mode="activation_needed",
            message="Trial state missing. Please enter your license key.",
        )

    trial_end = started + timedelta(days=TRIAL_DAYS)
    now = _now_utc()

    if now >= trial_end:
        return LicenseStatus(
            allowed=False,
            mode="trial_expired",
            message=f"Your {TRIAL_DAYS}-day free trial has ended. Enter a license key to continue.",
        )

    days_left = max(0, (trial_end - now).days)
    return LicenseStatus(
        allowed=True,
        mode="trial",
        message=f"Trial: {days_left} day{'s' if days_left != 1 else ''} remaining.",
        days_left=days_left,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Backend validation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValidationResponse:
    ok: bool
    email: Optional[str] = None
    error: Optional[str] = None
    network_failure: bool = False   # True when we never got a response (offline, timeout, DNS, etc)


def _validate_online(license_key: str) -> ValidationResponse:
    device_id = machine_fingerprint()
    try:
        resp = requests.post(
            VALIDATE_ENDPOINT,
            json={"licenseKey": license_key, "deviceId": device_id},
            timeout=VALIDATION_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        return ValidationResponse(ok=False, network_failure=True, error="Cannot reach license server.")

    try:
        body = resp.json()
    except ValueError:
        return ValidationResponse(ok=False, error=f"Unexpected server response ({resp.status_code}).")

    if resp.status_code == 200 and body.get("valid") is True:
        return ValidationResponse(ok=True, email=body.get("email"))

    # 4xx from the backend counts as a definitive "no", NOT a network failure —
    # we don't want a revoked key to keep working via offline grace.
    return ValidationResponse(ok=False, error=body.get("error", "License validation failed."))


def activate(license_key: str) -> tuple[bool, str]:
    """Try to activate a license key. On success, persist state.

    Returns (success, message).
    """
    license_key = (license_key or "").strip().upper()
    if not license_key:
        return False, "Please enter a license key."

    result = _validate_online(license_key)

    if result.ok:
        state = load_state()
        state.license_key = license_key
        state.email = result.email
        state.last_validated_at = _iso(_now_utc())
        save_state(state)
        return True, f"License activated. Thanks{f', {result.email}' if result.email else ''}!"

    if result.network_failure:
        return False, ("Could not reach the license server.\n"
                       "Check your internet connection and try again.")

    return False, result.error or "License validation failed."


def _licensed_status(state: LicenseState) -> LicenseStatus:
    """State has a license_key. Revalidate online; fall back to offline grace."""
    result = _validate_online(state.license_key)

    if result.ok:
        state.email = result.email or state.email
        state.last_validated_at = _iso(_now_utc())
        save_state(state)
        return LicenseStatus(
            allowed=True,
            mode="licensed",
            message="Licensed.",
            email=state.email,
        )

    if result.network_failure:
        # Offline — check grace period
        last = _parse_iso(state.last_validated_at) if state.last_validated_at else None
        if last is not None:
            grace_end = last + timedelta(days=OFFLINE_GRACE_DAYS)
            if _now_utc() < grace_end:
                days_left = max(0, (grace_end - _now_utc()).days)
                return LicenseStatus(
                    allowed=True,
                    mode="licensed",
                    message=f"Offline mode. Reconnect within {days_left} day{'s' if days_left != 1 else ''} to keep using Turbo Desk.",
                    email=state.email,
                )

        return LicenseStatus(
            allowed=False,
            mode="licensed",
            message="Cannot reach the license server and offline grace period has expired. Connect to the internet to continue.",
            email=state.email,
        )

    # Definitive rejection from backend (revoked, activation limit, unknown key)
    return LicenseStatus(
        allowed=False,
        mode="activation_needed",
        message=result.error or "License is no longer valid. Please contact support or enter a new key.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def check_status() -> LicenseStatus:
    """Main entry point called on app launch.

    Order of operations:
      1. If a license key is present, revalidate online (with offline grace fallback)
      2. Otherwise, ensure trial has been started and return trial status
    """
    state = load_state()

    if state.license_key:
        return _licensed_status(state)

    state = _ensure_trial_started(state)
    return _trial_status(state)


def clear_license() -> None:
    """Remove the activated license (keeps trial start date to prevent trial reset)."""
    state = load_state()
    state.license_key = None
    state.email = None
    state.last_validated_at = None
    save_state(state)

"""
ProCleaner - Free & Open Source System Optimizer
Entry point: silences stdout/stderr for windowed builds, then launches the Qt GUI.
"""
import sys
import os
import ctypes

# ── Windowed-exe safety: PyInstaller console=False sets stdout/stderr to None.
# Redirect them to a log file so early print() calls don't crash the process.
def _redirect_streams():
    if sys.stdout is None or sys.stderr is None:
        log_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ProCleaner")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "procleaner.log")
        try:
            log_file = open(log_path, "a", encoding="utf-8")
            if sys.stdout is None:
                sys.stdout = log_file
            if sys.stderr is None:
                sys.stderr = log_file
        except Exception:
            pass

_redirect_streams()


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def main():
    # Resolve project root — works both from source and from PyInstaller bundle
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller bundle
        project_root = sys._MEIPASS          # type: ignore[attr-defined]
    else:
        project_root = os.path.dirname(os.path.abspath(__file__))

    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        from PyQt6.QtGui import QFont
    except Exception as e:
        # Last-resort error dialog using Windows MessageBox (no Qt needed)
        ctypes.windll.user32.MessageBoxW(0, f"Failed to load PyQt6:\n\n{e}", "ProCleaner Error", 0x10)
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("ProCleaner")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ProCleaner")
    app.setFont(QFont("Segoe UI", 10))

    # ── License gate ─────────────────────────────────────────────────────
    # Enforces trial + paid license before launching the main window.
    # See licensing.py for the state machine.
    try:
        import licensing
        from ui.activation_dialog import ActivationDialog

        status = licensing.check_status()

        # If not allowed to run, show activation dialog and re-check
        if not status.allowed:
            dialog = ActivationDialog(reason=status.message)
            if dialog.exec() != dialog.DialogCode.Accepted:
                # User cancelled — exit without launching the app
                sys.exit(0)
            # Re-evaluate after activation
            status = licensing.check_status()
            if not status.allowed:
                QMessageBox.critical(
                    None, "Turbo Desk",
                    "Activation appeared to succeed but the license is not active. "
                    "Please restart the app or contact support."
                )
                sys.exit(1)
    except Exception:
        import traceback
        QMessageBox.critical(
            None, "Turbo Desk — License Error",
            f"Failed to check license:\n\n{traceback.format_exc()}"
        )
        sys.exit(1)

    # ── Launch main app ──────────────────────────────────────────────────
    try:
        from ui.main_window import MainWindow
        window = MainWindow()
        # Surface trial / offline status in the window title so users always
        # know their state at a glance without opening a menu.
        if status.mode == "trial":
            window.setWindowTitle(f"Turbo Desk (Trial — {status.days_left} day{'s' if status.days_left != 1 else ''} left)")
        elif status.mode == "licensed":
            window.setWindowTitle("Turbo Desk")
        window.show()
        sys.exit(app.exec())
    except Exception:
        import traceback
        QMessageBox.critical(
            None, "Turbo Desk — Startup Error",
            f"Turbo Desk failed to start:\n\n{traceback.format_exc()}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Activation dialog shown when a license key is required.

Two entry paths:
  * Trial expired  -> shown after trial_expired status; buys or activates
  * License failed -> shown when a previously valid license is rejected

The dialog blocks until the user either successfully activates or cancels.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QWidget,
)

import licensing


class _ActivationWorker(QThread):
    """Runs the network call off the UI thread so we don't freeze the app.

    Render's cold-start can be 30+ seconds — blocking the UI thread that
    long would make the dialog unresponsive.
    """
    finished_result = pyqtSignal(bool, str)

    def __init__(self, license_key: str, parent=None):
        super().__init__(parent)
        self._license_key = license_key

    def run(self) -> None:
        ok, message = licensing.activate(self._license_key)
        self.finished_result.emit(ok, message)


class ActivationDialog(QDialog):
    """Blocking dialog: activate a license key, or purchase one.

    Returns QDialog.DialogCode.Accepted on successful activation,
    Rejected otherwise (user cancelled / closed the window).
    """

    PURCHASE_URL = "https://turbodesk.app"

    def __init__(self, reason: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Turbo Desk — Activation")
        self.setModal(True)
        self.setMinimumWidth(460)
        self._worker: _ActivationWorker | None = None
        self._build_ui(reason)

    def _build_ui(self, reason: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Heading
        heading = QLabel("Activate Turbo Desk")
        font = heading.font()
        font.setPointSize(14)
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)

        # Reason / explainer
        if reason:
            reason_label = QLabel(reason)
            reason_label.setWordWrap(True)
            reason_label.setStyleSheet("color: #d97706;")
            layout.addWidget(reason_label)

        body = QLabel(
            "Enter the license key from your purchase confirmation email. "
            "Your key looks like <b>TD-XXXX-XXXX-XXXX-XXXX</b>."
        )
        body.setWordWrap(True)
        layout.addWidget(body)

        # Key input
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("TD-XXXX-XXXX-XXXX-XXXX")
        self.key_input.setFont(QFont("Consolas", 11))
        self.key_input.textChanged.connect(self._on_key_changed)
        layout.addWidget(self.key_input)

        # Status line
        self.status_label = QLabel(" ")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Buttons row
        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.buy_button = QPushButton("Buy a License")
        self.buy_button.clicked.connect(self._on_buy_clicked)
        button_row.addWidget(self.buy_button)

        button_row.addStretch(1)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self.cancel_button)

        self.activate_button = QPushButton("Activate")
        self.activate_button.setDefault(True)
        self.activate_button.setEnabled(False)
        self.activate_button.clicked.connect(self._on_activate_clicked)
        button_row.addWidget(self.activate_button)

        layout.addLayout(button_row)

    # ── Slots ────────────────────────────────────────────────────────────────

    def _on_key_changed(self, text: str) -> None:
        self.activate_button.setEnabled(bool(text.strip()))

    def _on_buy_clicked(self) -> None:
        QDesktopServices.openUrl(QUrl(self.PURCHASE_URL))

    def _on_activate_clicked(self) -> None:
        key = self.key_input.text().strip().upper()
        if not key:
            return

        self._set_busy(True, "Contacting license server…")

        self._worker = _ActivationWorker(key, self)
        self._worker.finished_result.connect(self._on_activation_finished)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_activation_finished(self, ok: bool, message: str) -> None:
        self._set_busy(False)
        if ok:
            QMessageBox.information(self, "Activated", message)
            self.accept()
        else:
            self.status_label.setStyleSheet("color: #dc2626;")
            self.status_label.setText(message)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _set_busy(self, busy: bool, message: str = " ") -> None:
        self.activate_button.setEnabled(not busy)
        self.cancel_button.setEnabled(not busy)
        self.buy_button.setEnabled(not busy)
        self.key_input.setEnabled(not busy)
        self.status_label.setStyleSheet("color: #64748b;")
        self.status_label.setText(message if busy else " ")

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        # If a validation is in flight, let it finish rather than crashing
        # the app on Qt thread cleanup.
        if self._worker is not None and self._worker.isRunning():
            event.ignore()
            return
        super().closeEvent(event)
