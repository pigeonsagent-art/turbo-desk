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
