"""
PCPolish — AAA Professional Dark Theme
Color palette inspired by modern security/system tools (Malwarebytes, GitHub dark, Windows 11)
"""

# ── Palette constants (used in Python code for QPainter etc.) ──────────
BG_DEEP       = "#0a0d12"
BG_SURFACE    = "#0f1419"
BG_CARD       = "#161c24"
BG_CARD_HOVER = "#1c2430"
BG_INPUT      = "#1c2430"
BORDER        = "#21262d"
BORDER_ACTIVE = "#388bfd"
BORDER_HOVER  = "#30363d"

TEXT_PRIMARY   = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
TEXT_MUTED     = "#484f58"

ACCENT_BLUE    = "#388bfd"
ACCENT_BLUE_LT = "#58a6ff"
ACCENT_GREEN   = "#3fb950"
ACCENT_YELLOW  = "#d29922"
ACCENT_RED     = "#f85149"
ACCENT_PURPLE  = "#bc8cff"
ACCENT_TEAL    = "#39d353"

DARK_STYLESHEET = f"""
/* ═══════════════════════════════════════════════
   BASE
═══════════════════════════════════════════════ */
* {{
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
    outline: none;
}}

QWidget {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    border: none;
}}

QMainWindow {{
    background-color: {BG_DEEP};
}}

/* ═══════════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════════ */
#Sidebar {{
    background-color: {BG_DEEP};
    border-right: 1px solid {BORDER};
    min-width: 220px;
    max-width: 220px;
}}

#LogoArea {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0f1923, stop:1 {BG_DEEP});
    border-bottom: 1px solid {BORDER};
    padding: 20px 16px 16px 16px;
}}

#AppName {{
    font-size: 20px;
    font-weight: 700;
    color: {ACCENT_BLUE_LT};
    letter-spacing: 1px;
}}

#AppTagline {{
    font-size: 9px;
    color: {TEXT_MUTED};
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 2px;
}}

#SectionLabel {{
    font-size: 9px;
    font-weight: 700;
    color: {TEXT_MUTED};
    letter-spacing: 2.5px;
    padding: 14px 16px 4px 20px;
    text-transform: uppercase;
}}

QPushButton#NavButton {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    border-radius: 6px;
    text-align: left;
    padding: 9px 12px 9px 20px;
    font-size: 13px;
    margin: 1px 8px;
}}

QPushButton#NavButton:hover {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
}}

QPushButton#NavButton[active="true"] {{
    background-color: rgba(56, 139, 253, 0.15);
    color: {ACCENT_BLUE_LT};
    font-weight: 600;
    border-left: 3px solid {ACCENT_BLUE};
    padding-left: 17px;
}}

#SidebarFooter {{
    background-color: {BG_DEEP};
    border-top: 1px solid {BORDER};
    padding: 12px 16px;
}}

#FooterMetricLabel {{
    font-size: 10px;
    color: {TEXT_MUTED};
    letter-spacing: 0.5px;
}}

/* ═══════════════════════════════════════════════
   CONTENT AREA
═══════════════════════════════════════════════ */
#ContentArea {{
    background-color: {BG_SURFACE};
}}

#PageHeader {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #131a22, stop:1 {BG_SURFACE});
    border-bottom: 1px solid {BORDER};
    padding: 18px 28px;
}}

#PageTitle {{
    font-size: 22px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}

#PageSubtitle {{
    font-size: 12px;
    color: {TEXT_SECONDARY};
    margin-top: 3px;
}}

/* ═══════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════ */
QPushButton {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_HOVER};
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {BG_CARD_HOVER};
    border-color: {BORDER_ACTIVE};
    color: {TEXT_PRIMARY};
}}

QPushButton:pressed {{
    background-color: #0d1117;
    border-color: {ACCENT_BLUE};
}}

QPushButton:disabled {{
    color: {TEXT_MUTED};
    background-color: {BG_DEEP};
    border-color: {BORDER};
}}

QPushButton#PrimaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #1f6feb, stop:1 #1158c7);
    color: #ffffff;
    border: 1px solid #388bfd;
    border-radius: 6px;
    font-weight: 600;
    padding: 8px 20px;
}}

QPushButton#PrimaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #388bfd, stop:1 #1f6feb);
    border-color: {ACCENT_BLUE_LT};
}}

QPushButton#PrimaryButton:pressed {{
    background: #1158c7;
}}

QPushButton#SuccessButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #238636, stop:1 #1a6129);
    color: #ffffff;
    border: 1px solid #3fb950;
    border-radius: 6px;
    font-weight: 600;
    padding: 8px 20px;
}}

QPushButton#SuccessButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2ea043, stop:1 #238636);
    border-color: #56d364;
}}

QPushButton#DangerButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #b91c1c, stop:1 #991b1b);
    color: #ffffff;
    border: 1px solid #f85149;
    border-radius: 6px;
    font-weight: 600;
    padding: 8px 20px;
}}

QPushButton#DangerButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #dc2626, stop:1 #b91c1c);
    border-color: #ff7b72;
}}

/* ═══════════════════════════════════════════════
   CARDS
═══════════════════════════════════════════════ */
QFrame#Card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QFrame#Card:hover {{
    border-color: {BORDER_HOVER};
}}

/* ═══════════════════════════════════════════════
   TABLES
═══════════════════════════════════════════════ */
QTableWidget, QTreeWidget, QListWidget {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    gridline-color: {BORDER};
    alternate-background-color: rgba(22, 28, 36, 0.6);
    selection-background-color: rgba(56, 139, 253, 0.25);
    selection-color: {TEXT_PRIMARY};
    outline: none;
}}

QTableWidget::item, QTreeWidget::item, QListWidget::item {{
    padding: 8px 6px;
    border: none;
    border-bottom: 1px solid {BORDER};
}}

QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: rgba(56, 139, 253, 0.2);
    color: {ACCENT_BLUE_LT};
}}

QTableWidget::item:hover, QTreeWidget::item:hover, QListWidget::item:hover {{
    background-color: {BG_CARD_HOVER};
}}

QHeaderView {{
    background-color: {BG_DEEP};
}}

QHeaderView::section {{
    background-color: {BG_DEEP};
    color: {TEXT_MUTED};
    padding: 10px 8px;
    border: none;
    border-bottom: 1px solid {BORDER};
    border-right: 1px solid {BORDER};
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

QHeaderView::section:last {{
    border-right: none;
}}

QHeaderView::section:hover {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
}}

/* ═══════════════════════════════════════════════
   PROGRESS BARS
═══════════════════════════════════════════════ */
QProgressBar {{
    border: none;
    border-radius: 4px;
    background-color: {BORDER};
    text-align: center;
    color: transparent;
    height: 6px;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1f6feb, stop:1 {ACCENT_BLUE_LT});
    border-radius: 4px;
}}

QProgressBar#GreenBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #238636, stop:1 {ACCENT_GREEN});
}}

QProgressBar#YellowBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #9e6a03, stop:1 {ACCENT_YELLOW});
}}

QProgressBar#RedBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #b91c1c, stop:1 {ACCENT_RED});
}}

/* ═══════════════════════════════════════════════
   INPUTS
═══════════════════════════════════════════════ */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_HOVER};
    border-radius: 6px;
    padding: 7px 12px;
    selection-background-color: rgba(56, 139, 253, 0.4);
}}

QLineEdit:focus, QTextEdit:focus {{
    border-color: {ACCENT_BLUE};
    background-color: #1c2430;
}}

QLineEdit::placeholder {{
    color: {TEXT_MUTED};
}}

QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_HOVER};
    border-radius: 6px;
    padding: 7px 12px;
    min-width: 120px;
}}

QComboBox:hover {{
    border-color: {ACCENT_BLUE};
}}

QComboBox:focus {{
    border-color: {ACCENT_BLUE};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_ACTIVE};
    border-radius: 6px;
    selection-background-color: rgba(56, 139, 253, 0.25);
    selection-color: {TEXT_PRIMARY};
    padding: 4px;
}}

QSpinBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_HOVER};
    border-radius: 6px;
    padding: 6px 10px;
}}

QSpinBox:focus {{
    border-color: {ACCENT_BLUE};
}}

/* ═══════════════════════════════════════════════
   CHECKBOXES
═══════════════════════════════════════════════ */
QCheckBox {{
    spacing: 10px;
    color: {TEXT_PRIMARY};
    padding: 3px 0;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {BORDER_HOVER};
    border-radius: 4px;
    background-color: {BG_INPUT};
}}

QCheckBox::indicator:hover {{
    border-color: {ACCENT_BLUE};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT_BLUE};
    border-color: {ACCENT_BLUE};
}}

QRadioButton {{
    spacing: 10px;
    color: {TEXT_PRIMARY};
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {BORDER_HOVER};
    border-radius: 8px;
    background-color: {BG_INPUT};
}}

QRadioButton::indicator:checked {{
    background-color: {ACCENT_BLUE};
    border-color: {ACCENT_BLUE};
}}

/* ═══════════════════════════════════════════════
   SCROLL BARS
═══════════════════════════════════════════════ */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {BORDER_HOVER};
    border-radius: 3px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {TEXT_MUTED};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
}}

QScrollBar::handle:horizontal {{
    background: {BORDER_HOVER};
    border-radius: 3px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {TEXT_MUTED};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ═══════════════════════════════════════════════
   TABS
═══════════════════════════════════════════════ */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {BG_CARD};
    border-radius: 8px;
    top: -1px;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    padding: 9px 18px;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    color: {ACCENT_BLUE_LT};
    border-bottom: 2px solid {ACCENT_BLUE};
    font-weight: 600;
}}

QTabBar::tab:hover:!selected {{
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {BORDER_HOVER};
}}

/* ═══════════════════════════════════════════════
   GROUP BOX
═══════════════════════════════════════════════ */
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 16px;
    padding: 12px 16px 16px 16px;
    font-size: 12px;
    font-weight: 600;
    color: {TEXT_SECONDARY};
    background-color: {BG_CARD};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: -1px;
    padding: 0 6px;
    background-color: {BG_CARD};
    color: {TEXT_SECONDARY};
    letter-spacing: 1px;
    text-transform: uppercase;
    font-size: 10px;
}}

/* ═══════════════════════════════════════════════
   SPLITTER
═══════════════════════════════════════════════ */
QSplitter::handle {{
    background-color: {BORDER};
    width: 1px;
    height: 1px;
}}

/* ═══════════════════════════════════════════════
   STATUS BAR
═══════════════════════════════════════════════ */
QStatusBar {{
    background-color: {BG_DEEP};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
    font-size: 11px;
    padding: 0 8px;
}}

QStatusBar::item {{
    border: none;
}}

/* ═══════════════════════════════════════════════
   TOOLTIP
═══════════════════════════════════════════════ */
QToolTip {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_HOVER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ═══════════════════════════════════════════════
   LABELS
═══════════════════════════════════════════════ */
QLabel#StatusGood   {{ color: {ACCENT_GREEN};  font-weight: 700; }}
QLabel#StatusWarn   {{ color: {ACCENT_YELLOW}; font-weight: 700; }}
QLabel#StatusBad    {{ color: {ACCENT_RED};    font-weight: 700; }}
QLabel#Muted        {{ color: {TEXT_MUTED};    font-size: 11px; }}
QLabel#Accent       {{ color: {ACCENT_BLUE_LT}; font-weight: 600; }}

/* ═══════════════════════════════════════════════
   FRAME SEPARATORS
═══════════════════════════════════════════════ */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {BORDER};
    max-height: 1px;
}}

/* ═══════════════════════════════════════════════
   SLIDER
═══════════════════════════════════════════════ */
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {ACCENT_BLUE};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    border: 2px solid {ACCENT_BLUE_LT};
}}

QSlider::sub-page:horizontal {{
    background: {ACCENT_BLUE};
    border-radius: 2px;
}}

/* ═══════════════════════════════════════════════
   SCROLL AREA
═══════════════════════════════════════════════ */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}
"""

# ── Python-accessible color constants ─────────────────────────────────
NAV_SECTIONS = [
    ("OVERVIEW", [
        ("PC Health Check", "health",      "❤"),
        ("Custom Cleaner",  "cleaner",     "🧹"),
    ]),
    ("TOOLS", [
        ("Registry",        "registry",    "🗂"),
        ("Browser Tools",   "browser",     "🌐"),
        ("Startup Manager", "startup",     "🚀"),
        ("Uninstaller",     "uninstaller", "🗑"),
    ]),
    ("ANALYSIS", [
        ("Disk Analyzer",   "disk",        "💾"),
        ("Duplicate Finder","duplicate",   "🔍"),
        ("Secure Wiper",    "wiper",       "🔒"),
    ]),
    ("SYSTEM", [
        ("Software Updater","updater",     "⬆"),
        ("System Restore",  "restore",     "🔄"),
        ("Performance",     "performance", "⚡"),
    ]),
    ("CONFIG", [
        ("Scheduler",       "scheduler",   "📅"),
        ("Cookie Manager",  "cookie",      "🍪"),
        ("Settings",        "settings",    "⚙"),
    ]),
]

STATUS_COLORS = {
    "good":     ACCENT_GREEN,
    "warning":  ACCENT_YELLOW,
    "critical": ACCENT_RED,
}
