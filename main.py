"""
PCPolish - Windows System Optimizer
Entry point: silences stdout/stderr for windowed builds, then launches the Qt GUI.
"""
import sys
import os
import ctypes

# ── Windowed-exe safety: PyInstaller console=False sets stdout/stderr to None.
# Redirect them to a log file so early print() calls don't crash the process.
def _redirect_streams():
    if sys.stdout is None or sys.stderr is None:
        log_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "PCPolish")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "PCPolish.log")
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
        ctypes.windll.user32.MessageBoxW(0, f"Failed to load PyQt6:\n\n{e}", "PCPolish Error", 0x10)
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("PCPolish")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("PCPolish")
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
