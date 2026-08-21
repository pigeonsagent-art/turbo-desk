"""
Main Window — AAA professional sidebar layout with grouped nav,
live CPU/RAM footer, and polished content area.
"""
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame,
    QStatusBar, QSizePolicy, QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QLinearGradient, QColor, QPainter, QBrush, QPen

from ui.styles import DARK_STYLESHEET, NAV_SECTIONS, BG_DEEP, ACCENT_BLUE, ACCENT_GREEN, TEXT_MUTED
from ui.cleaner_tab import CustomCleanerTab
from ui.health_tab import HealthTab
from ui.tools_tab import (
    RegistryTab, BrowserTab, StartupTab, UninstallerTab,
    DiskTab, DuplicateTab, WiperTab, UpdaterTab, RestoreTab,
    PerformanceTab, SchedulerTab, CookieTab,
)
from ui.settings_tab import SettingsTab

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False


# ── Sidebar mini progress bar ─────────────────────────────────────────
class MiniBar(QWidget):
    """Tiny labeled progress bar for CPU/RAM in sidebar footer."""
    def __init__(self, label: str, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        lbl = QLabel(label)
        lbl.setFixedWidth(32)
        lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px; font-weight:600;")
        layout.addWidget(lbl)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(4)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet(f"""
            QProgressBar {{ border:none; border-radius:2px; background:#21262d; }}
            QProgressBar::chunk {{ background:{color}; border-radius:2px; }}
        """)
        layout.addWidget(self._bar, 1)

        self._pct = QLabel("0%")
        self._pct.setFixedWidth(30)
        self._pct.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._pct.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px;")
        layout.addWidget(self._pct)

    def setValue(self, val: int):
        self._bar.setValue(val)
        self._pct.setText(f"{val}%")


# ── Main window ───────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PCPolish  —  System Optimizer")
        self.setMinimumSize(1140, 720)
        self.resize(1340, 820)
        self.setStyleSheet(DARK_STYLESHEET)

        self._nav_buttons: dict = {}
        self._active_page: str  = None
        self._cpu_bar: MiniBar  = None
        self._ram_bar: MiniBar  = None

        self._build_ui()
        self._navigate("health")
        self._start_metrics_timer()

    # ------------------------------------------------------------------ #
    # Build
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet(f"background:{BG_DEEP};")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        # Thin separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color:#21262d; max-width:1px;")
        root.addWidget(sep)

        root.addWidget(self._build_content(), 1)

        self.status_bar = QStatusBar()
        self.status_bar.showMessage("PCPolish  •  Ready")
        self.setStatusBar(self.status_bar)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Logo ──
        logo_area = QWidget()
        logo_area.setObjectName("LogoArea")
        logo_area.setFixedHeight(78)
        ll = QVBoxLayout(logo_area)
        ll.setContentsMargins(20, 16, 16, 12)
        ll.setSpacing(3)

        name_row = QHBoxLayout()
        shield = QLabel("🛡")
        shield.setFont(QFont("Segoe UI Emoji", 16))
        shield.setStyleSheet("color:#388bfd;")
        name_lbl = QLabel("PCPolish")
        name_lbl.setObjectName("AppName")
        name_lbl.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        name_row.addWidget(shield)
        name_row.addSpacing(6)
        name_row.addWidget(name_lbl)
        name_row.addStretch()
        ll.addLayout(name_row)

        tagline = QLabel("SYSTEM OPTIMIZER")
        tagline.setObjectName("AppTagline")
        tagline.setFont(QFont("Segoe UI", 8))
        ll.addWidget(tagline)
        layout.addWidget(logo_area)

        # ── Navigation sections ──
        nav_scroll_area = QWidget()
        nav_scroll_area.setStyleSheet(f"background:{BG_DEEP};")
        nav_vl = QVBoxLayout(nav_scroll_area)
        nav_vl.setContentsMargins(0, 8, 0, 8)
        nav_vl.setSpacing(0)

        for section_name, pages in NAV_SECTIONS:
            # Section label
            sec_lbl = QLabel(section_name)
            sec_lbl.setObjectName("SectionLabel")
            sec_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            nav_vl.addWidget(sec_lbl)

            for label, page_id, icon in pages:
                btn = QPushButton(f"  {icon}   {label}")
                btn.setObjectName("NavButton")
                btn.setFont(QFont("Segoe UI", 12))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFixedHeight(38)
                btn.setToolTip(label)
                btn.clicked.connect(lambda checked, pid=page_id: self._navigate(pid))
                self._nav_buttons[page_id] = btn
                nav_vl.addWidget(btn)

        nav_vl.addStretch()
        layout.addWidget(nav_scroll_area, 1)

        # ── Footer: live metrics ──
        footer = QWidget()
        footer.setObjectName("SidebarFooter")
        footer.setFixedHeight(82)
        fl = QVBoxLayout(footer)
        fl.setContentsMargins(16, 10, 16, 10)
        fl.setSpacing(6)

        sys_lbl = QLabel("SYSTEM")
        sys_lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px; font-weight:700; letter-spacing:2px;")
        fl.addWidget(sys_lbl)

        self._cpu_bar = MiniBar("CPU", "#388bfd")
        self._ram_bar = MiniBar("RAM", "#3fb950")
        fl.addWidget(self._cpu_bar)
        fl.addWidget(self._ram_bar)
        layout.addWidget(footer)

        return sidebar

    def _build_content(self) -> QWidget:
        self._stack = QStackedWidget()
        self._stack.setObjectName("ContentArea")
        self._stack.setStyleSheet("background:#0f1419;")

        self._pages = {
            "health":      HealthTab(self),
            "cleaner":     CustomCleanerTab(self),
            "registry":    RegistryTab(self),
            "browser":     BrowserTab(self),
            "startup":     StartupTab(self),
            "uninstaller": UninstallerTab(self),
            "disk":        DiskTab(self),
            "duplicate":   DuplicateTab(self),
            "wiper":       WiperTab(self),
            "updater":     UpdaterTab(self),
            "restore":     RestoreTab(self),
            "performance": PerformanceTab(self),
            "scheduler":   SchedulerTab(self),
            "cookie":      CookieTab(self),
            "settings":    SettingsTab(self),
        }
        for widget in self._pages.values():
            self._stack.addWidget(widget)
        return self._stack

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #
    def _navigate(self, page_id: str):
        if self._active_page == page_id:
            return
        for pid, btn in self._nav_buttons.items():
            active = (pid == page_id)
            btn.setProperty("active", active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        page = self._pages.get(page_id)
        if page:
            self._stack.setCurrentWidget(page)
            self._active_page = page_id

    def navigate_to(self, page_id: str):
        self._navigate(page_id)

    # ------------------------------------------------------------------ #
    # Live metrics timer
    # ------------------------------------------------------------------ #
    def _start_metrics_timer(self):
        if not PSUTIL_OK:
            return
        self._metrics_timer = QTimer(self)
        self._metrics_timer.timeout.connect(self._update_metrics)
        self._metrics_timer.start(2000)
        self._update_metrics()

    def _update_metrics(self):
        if not PSUTIL_OK:
            return
        try:
            cpu = int(psutil.cpu_percent(interval=None))
            ram = int(psutil.virtual_memory().percent)
            self._cpu_bar.setValue(cpu)
            self._ram_bar.setValue(ram)
            self.status_bar.showMessage(
                f"PCPolish  •  CPU {cpu}%  •  RAM {ram}%  •  Ready"
            )
        except Exception:
            pass

    def set_status(self, message: str):
        self.status_bar.showMessage(message)
