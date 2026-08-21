"""
Settings Tab - App preferences, real-time monitoring toggle, theme, and about info.
"""
import os
import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QComboBox, QGroupBox, QScrollArea, QFrame,
    QSpinBox, QLineEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from core.monitor import RealTimeMonitor

SETTINGS_FILE = Path(os.environ.get("APPDATA", "")) / "PCPolish" / "settings.json"

DEFAULTS = {
    "monitor_enabled": True,
    "monitor_threshold_mb": 100,
    "auto_start_with_windows": False,
    "minimize_to_tray": True,
    "confirm_before_clean": True,
    "show_notifications": True,
    "scan_on_startup": False,
    "language": "English",
}


class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = self._load()
        self._monitor = RealTimeMonitor(
            threshold_mb=self.settings.get("monitor_threshold_mb", 100),
            alert_cb=self._on_monitor_alert,
        )
        self._build()
        if self.settings.get("monitor_enabled", True):
            try:
                self._monitor.start()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #
    def _build(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0); main.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet("background:#1a1d23; border-bottom:1px solid #2a2d35;")
        hl = QHBoxLayout(header); hl.setContentsMargins(24, 16, 24, 16)
        col = QVBoxLayout()
        t = QLabel("Settings"); t.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        t.setStyleSheet("color:white;")
        s = QLabel("Configure PCPolish preferences and monitoring options")
        s.setStyleSheet("color:#6c7280; font-size:12px;")
        col.addWidget(t); col.addWidget(s)
        hl.addLayout(col, 1)
        main.addWidget(header)

        # Scroll body
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none; background:#1a1d23;}")
        body = QWidget(); body.setStyleSheet("background:#1a1d23;")
        bl = QVBoxLayout(body); bl.setContentsMargins(32, 24, 32, 24); bl.setSpacing(20)

        # ── Monitoring ──
        mon_group = QGroupBox("Real-Time Monitoring")
        mgl = QVBoxLayout(mon_group)
        self.cb_monitor = QCheckBox("Enable real-time junk file monitoring")
        self.cb_monitor.setChecked(self.settings.get("monitor_enabled", True))
        self.cb_monitor.stateChanged.connect(self._toggle_monitor)
        mgl.addWidget(self.cb_monitor)

        thresh_row = QHBoxLayout()
        thresh_row.addWidget(QLabel("Alert threshold (MB):"))
        self.spin_thresh = QSpinBox(); self.spin_thresh.setRange(10, 10000)
        self.spin_thresh.setValue(self.settings.get("monitor_threshold_mb", 100))
        self.spin_thresh.setSuffix(" MB")
        thresh_row.addWidget(self.spin_thresh); thresh_row.addStretch()
        mgl.addLayout(thresh_row)

        self.monitor_status_lbl = QLabel(
            "● Monitoring ACTIVE" if self._monitor.is_running else "● Monitoring OFF"
        )
        self.monitor_status_lbl.setStyleSheet(
            f"color:{'#2ecc71' if self._monitor.is_running else '#e74c3c'}; font-weight:bold;"
        )
        mgl.addWidget(self.monitor_status_lbl)
        bl.addWidget(mon_group)

        # ── Behaviour ──
        behav_group = QGroupBox("Behaviour")
        bgl = QVBoxLayout(behav_group)
        self.cb_confirm = QCheckBox("Confirm before cleaning")
        self.cb_confirm.setChecked(self.settings.get("confirm_before_clean", True))
        self.cb_notif = QCheckBox("Show desktop notifications")
        self.cb_notif.setChecked(self.settings.get("show_notifications", True))
        self.cb_startup_scan = QCheckBox("Run health check on startup")
        self.cb_startup_scan.setChecked(self.settings.get("scan_on_startup", False))
        self.cb_tray = QCheckBox("Minimize to system tray on close")
        self.cb_tray.setChecked(self.settings.get("minimize_to_tray", True))
        for cb in [self.cb_confirm, self.cb_notif, self.cb_startup_scan, self.cb_tray]:
            bgl.addWidget(cb)
        bl.addWidget(behav_group)

        # ── Data ──
        data_group = QGroupBox("Data & Privacy")
        dgl = QVBoxLayout(data_group)
        btn_clear_history = QPushButton("  🗑  Clear PCPolish History")
        btn_clear_history.clicked.connect(self._clear_history)
        btn_reset = QPushButton("  ↺  Reset All Settings to Defaults")
        btn_reset.clicked.connect(self._reset)
        dgl.addWidget(btn_clear_history); dgl.addWidget(btn_reset)
        bl.addWidget(data_group)

        # ── Save ──
        btn_save = QPushButton("  💾  Save Settings")
        btn_save.setObjectName("PrimaryButton"); btn_save.setFixedHeight(42)
        btn_save.clicked.connect(self._save)
        bl.addWidget(btn_save)

        # ── About ──
        about_group = QGroupBox("About PCPolish")
        agl = QVBoxLayout(about_group)
        for line in [
            "Version: 1.0.0",
            "License: Commercial — lifetime, up to 3 devices",
            "Platform: Windows 10 / 11",
            "Built with: Python 3 + PyQt6",
            "",
            "A fast, ad-free PC cleaner for Windows.",
            "All cleaning is done locally — no data is sent anywhere.",
        ]:
            lbl = QLabel(line)
            lbl.setStyleSheet("color:#6c7280;" if line else "")
            agl.addWidget(lbl)
        bl.addWidget(about_group)
        bl.addStretch()

        scroll.setWidget(body)
        main.addWidget(scroll, 1)

        # Status strip
        self.status_lbl = QLabel("  Settings loaded.")
        self.status_lbl.setStyleSheet(
            "background:#13151a; color:#6c7280; font-size:12px; "
            "padding:6px 20px; border-top:1px solid #2a2d35;"
        )
        main.addWidget(self.status_lbl)

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def _toggle_monitor(self, state):
        if state:
            self._monitor.threshold_mb = self.spin_thresh.value()
            started = self._monitor.start()
            txt = "● Monitoring ACTIVE" if started else "● Monitoring unavailable (install watchdog)"
            color = "#2ecc71" if started else "#f39c12"
        else:
            self._monitor.stop()
            txt = "● Monitoring OFF"; color = "#e74c3c"
        self.monitor_status_lbl.setText(txt)
        self.monitor_status_lbl.setStyleSheet(f"color:{color}; font-weight:bold;")

    def _save(self):
        self.settings.update({
            "monitor_enabled": self.cb_monitor.isChecked(),
            "monitor_threshold_mb": self.spin_thresh.value(),
            "confirm_before_clean": self.cb_confirm.isChecked(),
            "show_notifications": self.cb_notif.isChecked(),
            "scan_on_startup": self.cb_startup_scan.isChecked(),
            "minimize_to_tray": self.cb_tray.isChecked(),
        })
        self._save_to_disk()
        self.status_lbl.setText("  ✓  Settings saved.")

    def _clear_history(self):
        state_file = Path(os.environ.get("APPDATA", "")) / "PCPolish" / "health_state.json"
        try:
            state_file.unlink(missing_ok=True)
            self.status_lbl.setText("  History cleared.")
        except Exception as e:
            self.status_lbl.setText(f"  Error: {e}")

    def _reset(self):
        self.settings = DEFAULTS.copy()
        self._save_to_disk()
        self.status_lbl.setText("  Settings reset to defaults. Restart PCPolish to apply.")

    def _on_monitor_alert(self, source: str, mb: float):
        self.status_lbl.setText(f"  ⚠  Junk accumulating in {source}: {mb:.1f} MB — consider running a clean.")

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def _load(self) -> dict:
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE) as f:
                    data = json.load(f)
                    merged = DEFAULTS.copy(); merged.update(data)
                    return merged
            except Exception:
                pass
        return DEFAULTS.copy()

    def _save_to_disk(self):
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=2)
