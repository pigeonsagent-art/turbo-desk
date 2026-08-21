"""
PC Health Check Tab — AAA redesign with circular score gauge,
premium metric cards, and per-issue action buttons.
"""
import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QScrollArea, QGridLayout, QSizePolicy,
    QFrame, QSpacerItem,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QRectF, QSize
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush,
    QLinearGradient, QConicalGradient, QPainterPath,
)

from core.health_check import HealthCheck, HealthCheckResult, HealthMetric
from core.file_cleaner import FileCleaner
from core.browser_cleaner import BrowserCleaner
from core.registry_cleaner import RegistryCleaner
from ui.styles import (
    BG_DEEP, BG_SURFACE, BG_CARD, BG_CARD_HOVER,
    BORDER, BORDER_HOVER, ACCENT_BLUE, ACCENT_BLUE_LT,
    ACCENT_GREEN, ACCENT_YELLOW, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    STATUS_COLORS,
)


# ══════════════════════════════════════════════════════════════════════
# Circular score gauge (custom QPainter widget)
# ══════════════════════════════════════════════════════════════════════
class CircularGauge(QWidget):
    """Draws an arc-based score gauge with animated fill."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value  = 0
        self._grade  = "—"
        self._color  = ACCENT_BLUE_LT
        self.setFixedSize(180, 180)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setScore(self, value: int, grade: str):
        self._value = max(0, min(100, value))
        self._grade = grade
        self._color = (
            ACCENT_GREEN  if value >= 80 else
            ACCENT_YELLOW if value >= 50 else
            ACCENT_RED
        )
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h   = self.width(), self.height()
        margin = 18
        rect   = QRectF(margin, margin, w - margin * 2, h - margin * 2)

        # ── Track (background arc) ──
        pen = QPen(QColor(BORDER), 14)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(rect, 225 * 16, -270 * 16)

        # ── Value arc ──
        if self._value > 0:
            span = int(-270 * 16 * self._value / 100)
            pen2 = QPen(QColor(self._color), 14)
            pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen2)
            painter.drawArc(rect, 225 * 16, span)

            # Glow dot at tip
            tip_angle = math.radians(225 - 270 * self._value / 100)
            cx = w / 2 + (rect.width() / 2) * math.cos(tip_angle)
            cy = h / 2 - (rect.height() / 2) * math.sin(tip_angle)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(self._color)))
            painter.drawEllipse(QRectF(cx - 5, cy - 5, 10, 10))

        # ── Center score number ──
        painter.setPen(QColor(TEXT_PRIMARY))
        painter.setFont(QFont("Segoe UI", 34, QFont.Weight.Bold))
        painter.drawText(
            QRectF(0, 10, w, h - 20),
            Qt.AlignmentFlag.AlignCenter,
            str(self._value) if self._value > 0 else "—"
        )

        # ── Grade label below number ──
        painter.setPen(QColor(self._color))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(
            QRectF(0, h // 2 + 20, w, 30),
            Qt.AlignmentFlag.AlignCenter,
            self._grade
        )

        painter.end()


# ══════════════════════════════════════════════════════════════════════
# Premium Metric Card
# ══════════════════════════════════════════════════════════════════════
METRIC_ICONS = {
    "Disk Space (C:)":   "💾",
    "RAM Usage":         "🧠",
    "CPU Load":          "⚡",
    "Startup Programs":  "🚀",
    "Junk Files":        "🗑",
    "Last Cleaned":      "🕐",
    "Pending Updates":   "⬆",
    "Browser Junk":      "🌐",
    "Temp File Count":   "📁",
    "Registry Issues":   "🗂",
}


class MetricCard(QFrame):
    def __init__(self, metric: HealthMetric, parent=None):
        super().__init__(parent)
        color  = STATUS_COLORS.get(metric.status, ACCENT_BLUE_LT)
        icon   = METRIC_ICONS.get(metric.name, "•")
        self.setFixedHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-top: 3px solid {color};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        # Top row: icon + name
        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 14))
        icon_lbl.setFixedWidth(26)
        name_lbl = QLabel(metric.name.upper())
        name_lbl.setStyleSheet(
            f"color:{TEXT_MUTED}; font-size:9px; font-weight:700; letter-spacing:1.5px;"
        )
        top.addWidget(icon_lbl)
        top.addWidget(name_lbl, 1)

        # Status badge
        badge_map = {"good": "✓ GOOD", "warning": "⚠ WARN", "critical": "✖ CRITICAL"}
        badge = QLabel(badge_map.get(metric.status, metric.status.upper()))
        badge.setStyleSheet(f"""
            color: {color};
            background-color: rgba({self._hex_to_rgba(color, 0.15)});
            border: 1px solid rgba({self._hex_to_rgba(color, 0.4)});
            border-radius: 4px;
            padding: 1px 6px;
            font-size: 9px;
            font-weight: 700;
        """)
        top.addWidget(badge)
        layout.addLayout(top)

        # Value
        val_row = QHBoxLayout()
        val_lbl = QLabel(str(metric.value))
        val_lbl.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        val_lbl.setStyleSheet(f"color:{color};")
        val_row.addWidget(val_lbl)

        unit_lbl = QLabel(metric.unit)
        unit_lbl.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:12px; padding-top:8px;")
        val_row.addWidget(unit_lbl)
        val_row.addStretch()
        layout.addLayout(val_row)

        # Detail
        if metric.detail:
            detail = QLabel(metric.detail)
            detail.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px;")
            detail.setWordWrap(True)
            layout.addWidget(detail)

    @staticmethod
    def _hex_to_rgba(hex_color: str, alpha: float) -> str:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"{r}, {g}, {b}, {alpha}"


# ══════════════════════════════════════════════════════════════════════
# Workers
# ══════════════════════════════════════════════════════════════════════
class HealthWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)
    error    = pyqtSignal(str)

    def __init__(self, checker):
        super().__init__()
        self.checker = checker

    def run(self):
        try:
            result = self.checker.run(progress_cb=lambda n: self.progress.emit(n))
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class FixWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(int, int, int, int)   # files, bytes, reg_fixed, reg_failed
    error    = pyqtSignal(str)

    def __init__(self, result: HealthCheckResult):
        super().__init__()
        self.result = result

    def run(self):
        files_removed = bytes_freed = reg_fixed = reg_failed = 0
        issue_names = {m.name for m in self.result.metrics if m.status in ("warning", "critical")}
        try:
            if any(k in issue_names for k in ("Junk Files", "Temp File Count", "Last Cleaned")):
                self.progress.emit("Removing junk and temp files…")
                fc = FileCleaner()
                fc.scan()
                n, freed = fc.clean()
                files_removed += n
                bytes_freed   += freed

            if "Browser Junk" in issue_names:
                self.progress.emit("Clearing browser cache…")
                bc = BrowserCleaner()
                bc.scan()
                for browser in BrowserCleaner.get_installed_browsers():
                    n, freed = bc.clean(browser, ["cache"])
                    files_removed += n
                    bytes_freed   += freed

            if "Registry Issues" in issue_names:
                self.progress.emit("Fixing registry issues…")
                rc = RegistryCleaner()
                rc.scan()
                fixed, failed = rc.fix()
                reg_fixed  += fixed
                reg_failed += failed

            self.progress.emit("Recording clean…")
            HealthCheck().record_clean()
            self.finished.emit(files_removed, bytes_freed, reg_fixed, reg_failed)
        except Exception as e:
            self.error.emit(str(e))


# ══════════════════════════════════════════════════════════════════════
# Health Tab
# ══════════════════════════════════════════════════════════════════════
class HealthTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._checker     = HealthCheck()
        self._thread      = None
        self._fix_thread  = None
        self._last_result = None
        self.setStyleSheet(f"background:{BG_SURFACE};")
        self._build_ui()

    # ------------------------------------------------------------------ #
    # Build
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_score_panel())

        # Progress strip
        self._prog = QProgressBar()
        self._prog.setRange(0, 100)
        self._prog.setValue(0)
        self._prog.setFixedHeight(3)
        self._prog.setTextVisible(False)
        self._prog.setStyleSheet(f"""
            QProgressBar {{ border:none; background:{BG_DEEP}; }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ACCENT_BLUE}, stop:1 {ACCENT_BLUE_LT});
            }}
        """)
        root.addWidget(self._prog)

        self._status = QLabel("  Click  ❤  Run Health Check  to analyse your PC.")
        self._status.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px; padding:5px 28px;")
        root.addWidget(self._status)

        # Metric grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea{{border:none; background:{BG_SURFACE};}}")
        self._grid_host = QWidget()
        self._grid_host.setStyleSheet(f"background:{BG_SURFACE};")
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(24, 16, 24, 16)
        self._grid.setSpacing(12)
        scroll.setWidget(self._grid_host)
        root.addWidget(scroll, 1)

        root.addWidget(self._build_issues_panel())

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("PageHeader")
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #131a22, stop:1 {BG_SURFACE});
            border-bottom: 1px solid {BORDER};
        """)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(28, 18, 28, 18)

        col = QVBoxLayout()
        col.setSpacing(3)
        t = QLabel("PC Health Check")
        t.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        t.setStyleSheet(f"color:{TEXT_PRIMARY};")
        s = QLabel("Comprehensive system health analysis across 10 key metrics")
        s.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:12px;")
        col.addWidget(t)
        col.addWidget(s)
        hl.addLayout(col, 1)

        self.btn_run = QPushButton("  ❤  Run Health Check")
        self.btn_run.setObjectName("PrimaryButton")
        self.btn_run.setFixedHeight(40)
        self.btn_run.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.btn_run.clicked.connect(self._run_check)
        hl.addWidget(self.btn_run)
        return header

    def _build_score_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedHeight(160)
        panel.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #0d1520, stop:1 {BG_SURFACE});
            border-bottom: 1px solid {BORDER};
        """)
        hl = QHBoxLayout(panel)
        hl.setContentsMargins(32, 0, 32, 0)
        hl.setSpacing(0)

        # Circular gauge
        self._gauge = CircularGauge()
        hl.addWidget(self._gauge)
        hl.addSpacing(28)

        # Score info column
        info_col = QVBoxLayout()
        info_col.setSpacing(8)
        info_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._grade_lbl = QLabel("Run a health check to see your PC score")
        self._grade_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self._grade_lbl.setStyleSheet(f"color:{TEXT_PRIMARY};")

        self._sub_lbl = QLabel("PCPolish will scan 10 metrics and give you an overall health score.")
        self._sub_lbl.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:12px;")
        self._sub_lbl.setWordWrap(True)

        # Score bar
        self._score_bar = QProgressBar()
        self._score_bar.setRange(0, 100)
        self._score_bar.setValue(0)
        self._score_bar.setFixedHeight(8)
        self._score_bar.setFixedWidth(380)
        self._score_bar.setTextVisible(False)
        self._score_bar.setStyleSheet(f"""
            QProgressBar {{ border:none; border-radius:4px; background:{BORDER}; }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ACCENT_BLUE}, stop:1 {ACCENT_GREEN});
                border-radius: 4px;
            }}
        """)

        info_col.addWidget(self._grade_lbl)
        info_col.addWidget(self._score_bar)
        info_col.addWidget(self._sub_lbl)
        hl.addLayout(info_col, 1)
        hl.addSpacing(24)

        # Fix button
        self.btn_fix = QPushButton("  ⚡  Fix All Issues")
        self.btn_fix.setObjectName("SuccessButton")
        self.btn_fix.setFixedHeight(44)
        self.btn_fix.setFixedWidth(170)
        self.btn_fix.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.btn_fix.setVisible(False)
        self.btn_fix.clicked.connect(self._fix_all_issues)
        hl.addWidget(self.btn_fix)

        return panel

    def _build_issues_panel(self) -> QWidget:
        self._issues_panel = QWidget()
        self._issues_panel.setFixedHeight(52)
        self._issues_panel.setStyleSheet(f"""
            background:{BG_DEEP};
            border-top: 1px solid {BORDER};
        """)
        il = QHBoxLayout(self._issues_panel)
        il.setContentsMargins(28, 0, 28, 0)

        self._issues_icon = QLabel("ℹ")
        self._issues_icon.setStyleSheet(f"color:{TEXT_MUTED}; font-size:16px;")
        il.addWidget(self._issues_icon)
        il.addSpacing(8)

        self._issues_lbl = QLabel("Run a health check to detect issues.")
        self._issues_lbl.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:12px;")
        self._issues_lbl.setWordWrap(True)
        il.addWidget(self._issues_lbl, 1)
        return self._issues_panel

    # ------------------------------------------------------------------ #
    # Run
    # ------------------------------------------------------------------ #
    def _run_check(self):
        self.btn_run.setEnabled(False)
        self.btn_fix.setVisible(False)
        self._prog.setRange(0, 0)
        self._status.setText("  Running health check…")
        self._clear_grid()

        self._thread = QThread()
        self._worker = HealthWorker(self._checker)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(lambda n: self._status.setText(f"  Checking: {n}…"))
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_done(self, result: HealthCheckResult):
        self._last_result = result
        self._prog.setRange(0, 100)
        self._prog.setValue(100)
        self.btn_run.setEnabled(True)

        # Gauge + score bar
        self._gauge.setScore(result.score, result.grade)
        self._score_bar.setValue(result.score)

        color = ACCENT_GREEN if result.score >= 80 else (ACCENT_YELLOW if result.score >= 50 else ACCENT_RED)
        self._grade_lbl.setText(f"{result.grade}  —  {result.score}/100")
        self._grade_lbl.setStyleSheet(f"color:{color}; font-size:16px; font-weight:700;")
        self._sub_lbl.setText(
            f"Health check completed — {len(result.issues)} issue(s) found. "
            + ("No action required." if not result.issues else "Click  ⚡ Fix All Issues  to auto-repair.")
        )

        # Colour score bar dynamically
        self._score_bar.setStyleSheet(f"""
            QProgressBar {{ border:none; border-radius:4px; background:{BORDER}; }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ACCENT_BLUE}, stop:1 {color});
                border-radius: 4px;
            }}
        """)

        # Metric cards — 3 column grid
        self._clear_grid()
        for i, metric in enumerate(result.metrics):
            card = MetricCard(metric)
            self._grid.addWidget(card, i // 3, i % 3)

        # Issues bar
        if result.issues:
            self._issues_icon.setText("⚠")
            self._issues_icon.setStyleSheet(f"color:{ACCENT_YELLOW}; font-size:16px;")
            issues_text = "   •   ".join(result.issues[:4])
            if len(result.issues) > 4:
                issues_text += f"   •   +{len(result.issues)-4} more…"
            self._issues_lbl.setText(issues_text)
            self._issues_lbl.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:11px;")
            self.btn_fix.setVisible(True)
        else:
            self._issues_icon.setText("✓")
            self._issues_icon.setStyleSheet(f"color:{ACCENT_GREEN}; font-size:16px;")
            self._issues_lbl.setText("No issues detected — your PC is in great shape!")
            self._issues_lbl.setStyleSheet(f"color:{ACCENT_GREEN}; font-size:12px;")
            self.btn_fix.setVisible(False)

        self._status.setText(f"  Health check complete — score {result.score}/100 ({result.grade})")

    def _on_error(self, msg: str):
        self._prog.setRange(0, 100)
        self._prog.setValue(0)
        self.btn_run.setEnabled(True)
        self._status.setText(f"  Error: {msg}")

    # ------------------------------------------------------------------ #
    # Fix All Issues
    # ------------------------------------------------------------------ #
    def _fix_all_issues(self):
        if not self._last_result:
            return
        self.btn_fix.setEnabled(False)
        self.btn_run.setEnabled(False)
        self._prog.setRange(0, 0)
        self._status.setText("  ⚡  Fixing issues automatically…")

        self._fix_thread = QThread()
        self._fix_worker = FixWorker(self._last_result)
        self._fix_worker.moveToThread(self._fix_thread)
        self._fix_thread.started.connect(self._fix_worker.run)
        self._fix_worker.progress.connect(lambda m: self._status.setText(f"  ⚡  {m}"))
        self._fix_worker.finished.connect(self._on_fix_done)  # (files, bytes, reg_fixed, reg_failed)
        self._fix_worker.error.connect(self._on_fix_error)
        self._fix_worker.finished.connect(self._fix_thread.quit)
        self._fix_thread.start()

    def _on_fix_done(self, files_removed: int, bytes_freed: int, reg_fixed: int, reg_failed: int):
        self._prog.setRange(0, 100)
        self._prog.setValue(100)
        self.btn_fix.setVisible(False)
        self.btn_run.setEnabled(True)

        parts = []
        if files_removed:
            parts.append(f"{files_removed:,} files removed ({FileCleaner.format_size(bytes_freed)} freed)")
        if reg_fixed:
            parts.append(f"{reg_fixed} registry entr{'y' if reg_fixed == 1 else 'ies'} fixed")
        if reg_failed:
            parts.append(
                f"{reg_failed} registry issue{'s' if reg_failed > 1 else ''} require admin rights — "
                "relaunch as Administrator to fix"
            )

        summary = " • ".join(parts) if parts else "No auto-fixable issues found."

        icon_color = ACCENT_YELLOW if reg_failed and not reg_fixed and not files_removed else ACCENT_GREEN
        self._issues_icon.setText("⚠" if reg_failed else "✓")
        self._issues_icon.setStyleSheet(f"color:{icon_color}; font-size:16px;")
        self._issues_lbl.setText(f"{summary}  —  Re-running health check…")
        self._issues_lbl.setStyleSheet(f"color:{icon_color}; font-size:12px;")
        self._status.setText(f"  {'⚠' if reg_failed else '✓'}  {summary}")
        self._run_check()

    def _on_fix_error(self, msg: str):
        self._prog.setRange(0, 100)
        self._prog.setValue(0)
        self.btn_fix.setEnabled(True)
        self.btn_run.setEnabled(True)
        self._status.setText(f"  Fix error: {msg}")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _clear_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
