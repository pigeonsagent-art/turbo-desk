"""
Tools Tab - Contains all tool-specific pages:
  RegistryTab, BrowserTab, StartupTab, UninstallerTab,
  DiskTab, DuplicateTab, WiperTab, UpdaterTab, RestoreTab,
  PerformanceTab, SchedulerTab, CookieTab
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFrame, QComboBox, QLineEdit, QCheckBox, QTreeWidget,
    QTreeWidgetItem, QListWidget, QListWidgetItem, QAbstractItemView,
    QScrollArea, QSplitter, QTextEdit, QFileDialog, QSpinBox,
    QGroupBox, QRadioButton, QSizePolicy, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont, QColor

from core.file_cleaner import FileCleaner


# ══════════════════════════════════════════════════════════════
# Shared helpers
# ══════════════════════════════════════════════════════════════
def _page_header(title: str, subtitle: str, btn_label: str = None) -> tuple:
    header = QWidget()
    header.setStyleSheet("background:#1a1d23; border-bottom:1px solid #2a2d35;")
    hl = QHBoxLayout(header)
    hl.setContentsMargins(24, 16, 24, 16)
    col = QVBoxLayout()
    t = QLabel(title)
    t.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
    t.setStyleSheet("color:white;")
    s = QLabel(subtitle)
    s.setStyleSheet("color:#6c7280; font-size:12px;")
    col.addWidget(t)
    col.addWidget(s)
    hl.addLayout(col, 1)
    btn = None
    if btn_label:
        btn = QPushButton(btn_label)
        btn.setObjectName("PrimaryButton")
        btn.setFixedHeight(38)
        hl.addWidget(btn)
    return header, btn


def _status_bar(parent_layout):
    bar = QProgressBar()
    bar.setRange(0, 100); bar.setValue(0)
    bar.setFixedHeight(5); bar.setTextVisible(False)
    bar.setStyleSheet("QProgressBar{border:none;background:#13151a;}"
                      "QProgressBar::chunk{background:#0d7aff;}")
    lbl = QLabel("  Ready.")
    lbl.setStyleSheet("color:#6c7280; font-size:12px; padding:3px 20px;")
    bottom = QWidget()
    bottom.setStyleSheet("background:#13151a; border-top:1px solid #2a2d35;")
    bl = QVBoxLayout(bottom)
    bl.setContentsMargins(0, 4, 0, 4)
    bl.setSpacing(2)
    bl.addWidget(bar)
    bl.addWidget(lbl)
    parent_layout.addWidget(bottom)
    return bar, lbl


# ══════════════════════════════════════════════════════════════
# Registry Tab
# ══════════════════════════════════════════════════════════════
class RegistryWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error    = pyqtSignal(str)

    def __init__(self, cleaner):
        super().__init__()
        self.cleaner = cleaner

    def run(self):
        try:
            issues = self.cleaner.scan(progress_cb=lambda name: self.progress.emit(name))
            self.finished.emit(issues)
        except Exception as e:
            self.error.emit(str(e))


class RegistryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.registry_cleaner import RegistryCleaner
        self.cleaner = RegistryCleaner()
        self._issues = []
        self._build()

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        header, self.btn_scan = _page_header(
            "Registry Cleaner",
            "Scan for and fix invalid, orphaned, and broken registry entries",
            "  🗂  Scan Registry"
        )
        self.btn_scan.clicked.connect(self._scan)
        vl.addWidget(header)

        # Toolbar
        tb = QWidget(); tb.setStyleSheet("background:#21242c; border-bottom:1px solid #2a2d35;")
        tbl = QHBoxLayout(tb); tbl.setContentsMargins(16, 8, 16, 8)
        self.btn_fix_all = QPushButton("  ✓  Fix All Selected")
        self.btn_fix_all.setObjectName("SuccessButton"); self.btn_fix_all.setEnabled(False)
        self.btn_fix_all.clicked.connect(self._fix_all)
        self.btn_backup = QPushButton("  💾  Backup Registry")
        self.btn_backup.clicked.connect(self._backup)
        self.lbl_count = QLabel("No scan run yet")
        self.lbl_count.setStyleSheet("color:#6c7280;")
        tbl.addWidget(self.btn_fix_all)
        tbl.addSpacing(8)
        tbl.addWidget(self.btn_backup)
        tbl.addStretch()
        tbl.addWidget(self.lbl_count)
        vl.addWidget(tb)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Category", "Key Path", "Value", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        vl.addWidget(self.table, 1)

        self.prog, self.status = _status_bar(vl)

    def _scan(self):
        self.btn_scan.setEnabled(False)
        self.btn_fix_all.setEnabled(False)
        self.table.setRowCount(0)
        self.prog.setRange(0, 0)
        self._thread = QThread()
        self._worker = RegistryWorker(self.cleaner)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(lambda n: self.status.setText(f"  Scanning: {n}…"))
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(lambda e: self.status.setText(f"  Error: {e}"))
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_done(self, issues):
        self._issues = issues
        self.prog.setRange(0, 100); self.prog.setValue(100)
        self.btn_scan.setEnabled(True)
        self.table.setRowCount(len(issues))
        for i, issue in enumerate(issues):
            self.table.setItem(i, 0, QTableWidgetItem(issue.category))
            self.table.setItem(i, 1, QTableWidgetItem(issue.key_path))
            self.table.setItem(i, 2, QTableWidgetItem(issue.value_name))
            self.table.setItem(i, 3, QTableWidgetItem(issue.description))
        self.lbl_count.setText(f"{len(issues)} issues found")
        if issues:
            self.btn_fix_all.setEnabled(True)
        self.status.setText(f"  Scan complete — {len(issues)} registry issues found.")

    def _fix_all(self):
        fixed, failed = self.cleaner.fix()
        self.table.setRowCount(0)
        self.status.setText(f"  Fixed {fixed} entries. {failed} could not be fixed.")
        self.btn_fix_all.setEnabled(False)

    def _backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Registry Backup", "registry_backup.reg", "REG Files (*.reg)")
        if path:
            import sys, winreg
            ok = self.cleaner.backup_key(winreg.HKEY_CURRENT_USER, "SOFTWARE", path)
            self.status.setText(f"  {'Backup saved to ' + path if ok else 'Backup failed.'}")


# ══════════════════════════════════════════════════════════════
# Browser Tools Tab
# ══════════════════════════════════════════════════════════════
class BrowserTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.browser_cleaner import BrowserCleaner, BROWSERS
        self.cleaner = BrowserCleaner()
        self.BROWSERS = BROWSERS
        self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        header, _ = _page_header("Browser Tools",
                                  "Clean browser cache, history, cookies and manage extensions")
        vl.addWidget(header)

        body = QWidget(); body.setStyleSheet("background:#1a1d23;")
        bl = QVBoxLayout(body); bl.setContentsMargins(24, 20, 24, 20); bl.setSpacing(16)

        # Browser selector
        row = QHBoxLayout()
        row.addWidget(QLabel("Browser:"))
        self.browser_combo = QComboBox()
        installed = self.cleaner.get_installed_browsers()
        for b in self.BROWSERS:
            self.browser_combo.addItem(b)
            if b not in installed:
                idx = self.browser_combo.count() - 1
                self.browser_combo.model().item(idx).setEnabled(False)
        row.addWidget(self.browser_combo)
        row.addStretch()

        self.btn_scan = QPushButton("  🔍  Scan")
        self.btn_scan.setObjectName("PrimaryButton"); self.btn_scan.setFixedHeight(36)
        self.btn_scan.clicked.connect(self._scan)
        row.addWidget(self.btn_scan)

        self.btn_clean_browser = QPushButton("  🧹  Clean Selected")
        self.btn_clean_browser.setObjectName("SuccessButton"); self.btn_clean_browser.setFixedHeight(36)
        self.btn_clean_browser.setEnabled(False)
        self.btn_clean_browser.clicked.connect(self._clean)
        row.addWidget(self.btn_clean_browser)
        bl.addLayout(row)

        # Clean type checkboxes
        types_row = QHBoxLayout()
        self.type_checks = {}
        for key, label in [("cache","Cache"),("history","History"),("cookies","Cookies"),("other","Other")]:
            cb = QCheckBox(label)
            cb.setChecked(key in ("cache","history"))
            self.type_checks[key] = cb
            types_row.addWidget(cb)
        types_row.addStretch()
        bl.addLayout(types_row)

        # Results table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Data Type", "Files", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        bl.addWidget(self.table, 1)

        # Auto-clean on close checkbox
        self.auto_clean_cb = QCheckBox("Auto-clean selected data types when browser closes")
        self.auto_clean_cb.stateChanged.connect(self._toggle_auto_clean)
        bl.addWidget(self.auto_clean_cb)

        vl.addWidget(body, 1)
        self.prog, self.status = _status_bar(vl)

    def _scan(self):
        self.btn_scan.setEnabled(False)
        self.prog.setRange(0, 0)
        self.status.setText("  Scanning browser data…")
        results = self.cleaner.scan()
        browser = self.browser_combo.currentText()
        data = results.get(browser, {})
        self.table.setRowCount(0)
        row = 0
        for dtype, ddata in data.items():
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(dtype.title()))
            self.table.setItem(row, 1, QTableWidgetItem(str(len(ddata["files"]))))
            sz_item = QTableWidgetItem(FileCleaner.format_size(ddata["size"]))
            sz_item.setForeground(QColor("#4fc3f7"))
            self.table.setItem(row, 2, sz_item)
            row += 1
        self.prog.setRange(0, 100); self.prog.setValue(100)
        self.btn_scan.setEnabled(True)
        self.btn_clean_browser.setEnabled(True)
        self.status.setText("  Scan complete.")

    def _clean(self):
        browser = self.browser_combo.currentText()
        types = [k for k, cb in self.type_checks.items() if cb.isChecked()]
        count, freed = self.cleaner.clean(browser, types)
        self.table.setRowCount(0)
        self.btn_clean_browser.setEnabled(False)
        self.status.setText(f"  Cleaned {count} files, freed {FileCleaner.format_size(freed)}.")

    def _toggle_auto_clean(self, state):
        if state:
            browser = self.browser_combo.currentText()
            types = [k for k, cb in self.type_checks.items() if cb.isChecked()]
            self.cleaner.clean_on_browser_close(browser, types)
            self.status.setText(f"  Auto-clean enabled for {browser}.")


# ══════════════════════════════════════════════════════════════
# Startup Manager Tab
# ══════════════════════════════════════════════════════════════
class StartupTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.startup_manager import StartupManager
        self.manager = StartupManager()
        self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        header, self.btn_refresh = _page_header(
            "Startup Manager",
            "Control which programs run automatically when Windows starts",
            "  🚀  Refresh"
        )
        self.btn_refresh.clicked.connect(self._load)
        vl.addWidget(header)

        tb = QWidget(); tb.setStyleSheet("background:#21242c; border-bottom:1px solid #2a2d35;")
        tbl = QHBoxLayout(tb); tbl.setContentsMargins(16, 8, 16, 8)
        self.btn_disable = QPushButton("  ⏸  Disable"); self.btn_disable.setEnabled(False)
        self.btn_enable  = QPushButton("  ▶  Enable");  self.btn_enable.setEnabled(False)
        self.btn_delete  = QPushButton("  🗑  Delete");
        self.btn_delete.setObjectName("DangerButton");  self.btn_delete.setEnabled(False)
        self.btn_disable.clicked.connect(self._disable)
        self.btn_enable.clicked.connect(self._enable)
        self.btn_delete.clicked.connect(self._delete)
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color:#6c7280;")
        tbl.addWidget(self.btn_disable); tbl.addWidget(self.btn_enable)
        tbl.addSpacing(8); tbl.addWidget(self.btn_delete)
        tbl.addStretch(); tbl.addWidget(self.lbl_count)
        vl.addWidget(tb)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Command", "Status", "Source", "Impact"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.selectionModel().selectionChanged.connect(self._on_select)
        vl.addWidget(self.table, 1)
        self.prog, self.status = _status_bar(vl)
        self._load()

    def _load(self):
        self.prog.setRange(0, 0)
        entries = self.manager.get_all()
        self.table.setRowCount(len(entries))
        for i, e in enumerate(entries):
            self.table.setItem(i, 0, QTableWidgetItem(e.name))
            self.table.setItem(i, 1, QTableWidgetItem(e.command))
            status_item = QTableWidgetItem("Enabled" if e.enabled else "Disabled")
            status_item.setForeground(QColor("#2ecc71" if e.enabled else "#e74c3c"))
            self.table.setItem(i, 2, status_item)
            self.table.setItem(i, 3, QTableWidgetItem(e.source))
            impact = "⚠ Missing" if not e.exe_exists else "Normal"
            self.table.setItem(i, 4, QTableWidgetItem(impact))
        self.lbl_count.setText(f"{len(entries)} startup items")
        self.prog.setRange(0, 100); self.prog.setValue(100)
        self.status.setText(f"  Loaded {len(entries)} startup entries.")

    def _on_select(self):
        rows = self.table.selectionModel().selectedRows()
        has = len(rows) > 0
        self.btn_disable.setEnabled(has)
        self.btn_enable.setEnabled(has)
        self.btn_delete.setEnabled(has)

    def _get_selected_entry(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None, -1
        idx = rows[0].row()
        return self.manager.entries[idx], idx

    def _disable(self):
        entry, _ = self._get_selected_entry()
        if entry and self.manager.disable(entry):
            self._load()
            self.status.setText(f"  Disabled: {entry.name}")

    def _enable(self):
        entry, _ = self._get_selected_entry()
        if entry and self.manager.enable(entry):
            self._load()
            self.status.setText(f"  Enabled: {entry.name}")

    def _delete(self):
        entry, _ = self._get_selected_entry()
        if entry and self.manager.delete(entry):
            self._load()
            self.status.setText(f"  Deleted: {entry.name}")


# ══════════════════════════════════════════════════════════════
# Uninstaller Tab
# ══════════════════════════════════════════════════════════════
class UninstallerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.uninstaller import Uninstaller
        self.uninstaller = Uninstaller()
        self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        header, self.btn_refresh = _page_header(
            "Uninstaller",
            "Remove installed programs and clean up their leftover files and registry entries",
            "  🔄  Refresh"
        )
        self.btn_refresh.clicked.connect(self._load)
        vl.addWidget(header)

        # Search bar + uninstall button
        tb = QWidget(); tb.setStyleSheet("background:#21242c; border-bottom:1px solid #2a2d35;")
        tbl = QHBoxLayout(tb); tbl.setContentsMargins(16, 8, 16, 8)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search programs…")
        self.search.setFixedHeight(32); self.search.textChanged.connect(self._filter)
        self.btn_uninstall = QPushButton("  🗑  Uninstall")
        self.btn_uninstall.setObjectName("DangerButton"); self.btn_uninstall.setEnabled(False)
        self.btn_uninstall.clicked.connect(self._uninstall)
        self.lbl_count = QLabel(""); self.lbl_count.setStyleSheet("color:#6c7280;")
        tbl.addWidget(self.search, 1); tbl.addSpacing(8)
        tbl.addWidget(self.btn_uninstall); tbl.addStretch(); tbl.addWidget(self.lbl_count)
        vl.addWidget(tb)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Publisher", "Version", "Installed", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.selectionModel().selectionChanged.connect(
            lambda: self.btn_uninstall.setEnabled(bool(self.table.selectionModel().selectedRows()))
        )
        vl.addWidget(self.table, 1)
        self.prog, self.status = _status_bar(vl)
        self._load()

    def _load(self):
        self.prog.setRange(0, 0)
        self.status.setText("  Loading installed programs…")
        programs = self.uninstaller.get_installed()
        self._populate(programs)
        self.prog.setRange(0, 100); self.prog.setValue(100)
        self.status.setText(f"  Loaded {len(programs)} installed programs.")

    def _populate(self, programs):
        self.table.setRowCount(len(programs))
        for i, p in enumerate(programs):
            self.table.setItem(i, 0, QTableWidgetItem(p.name))
            self.table.setItem(i, 1, QTableWidgetItem(p.publisher))
            self.table.setItem(i, 2, QTableWidgetItem(p.version))
            self.table.setItem(i, 3, QTableWidgetItem(p.install_date_formatted))
            self.table.setItem(i, 4, QTableWidgetItem(p.size_str))
        self.lbl_count.setText(f"{len(programs)} programs")

    def _filter(self, text):
        results = self.uninstaller.search(text) if text else self.uninstaller.programs
        self._populate(results)

    def _uninstall(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        prog = self.uninstaller.programs[rows[0].row()]
        self.prog.setRange(0, 0)
        self.status.setText(f"  Uninstalling {prog.name}…")
        ok = self.uninstaller.uninstall(
            prog, silent=True,
            progress_cb=lambda m: self.status.setText(f"  {m}")
        )
        self.prog.setRange(0, 100); self.prog.setValue(100)
        self.status.setText(f"  {'Uninstalled' if ok else 'Failed to uninstall'}: {prog.name}")
        if ok:
            self._load()


# ══════════════════════════════════════════════════════════════
# Disk Analyzer Tab
# ══════════════════════════════════════════════════════════════
class DiskTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.disk_analyzer import DiskAnalyzer
        self.analyzer = DiskAnalyzer()
        self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        header, _ = _page_header("Disk Analyzer",
                                  "Scan drives and directories to find what's consuming the most space")
        vl.addWidget(header)

        # Drive overview
        drives_widget = QWidget()
        drives_widget.setStyleSheet("background:#21242c; border-bottom:1px solid #2a2d35;")
        dl = QHBoxLayout(drives_widget); dl.setContentsMargins(20, 12, 20, 12)
        self.drive_cards = []
        for drive in self.analyzer.get_drives():
            card = self._drive_card(drive)
            dl.addWidget(card)
        dl.addStretch()

        self.scan_path = QLineEdit("C:\\")
        self.scan_path.setFixedWidth(200)
        self.btn_browse = QPushButton("Browse")
        self.btn_browse.clicked.connect(self._browse)
        self.btn_analyze = QPushButton("  💾  Analyze")
        self.btn_analyze.setObjectName("PrimaryButton"); self.btn_analyze.setFixedHeight(36)
        self.btn_analyze.clicked.connect(self._analyze)
        dl.addWidget(QLabel("Scan:")); dl.addWidget(self.scan_path)
        dl.addWidget(self.btn_browse); dl.addSpacing(8); dl.addWidget(self.btn_analyze)
        vl.addWidget(drives_widget)

        # Results split
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:#2a2d35;}")

        # Top files
        left = QWidget(); left.setStyleSheet("background:#1a1d23;")
        ll = QVBoxLayout(left); ll.setContentsMargins(16, 12, 8, 12)
        ll.addWidget(QLabel("  Top Files by Size"))
        self.files_table = QTableWidget(0, 3)
        self.files_table.setHorizontalHeaderLabels(["File", "Size", "Extension"])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        ll.addWidget(self.files_table, 1)

        # File type breakdown
        right = QWidget(); right.setStyleSheet("background:#1a1d23;")
        rl = QVBoxLayout(right); rl.setContentsMargins(8, 12, 16, 12)
        rl.addWidget(QLabel("  File Types"))
        self.types_table = QTableWidget(0, 2)
        self.types_table.setHorizontalHeaderLabels(["Type", "Size"])
        self.types_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.types_table.setAlternatingRowColors(True)
        self.types_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        rl.addWidget(self.types_table, 1)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setSizes([600, 300])
        vl.addWidget(splitter, 1)
        self.prog, self.status = _status_bar(vl)

    def _drive_card(self, drive: dict) -> QWidget:
        card = QFrame(); card.setStyleSheet("""
            QFrame{background:#1e2128;border:1px solid #2a2d35;border-radius:6px;padding:8px;}
        """); card.setFixedWidth(160)
        cl = QVBoxLayout(card); cl.setContentsMargins(10, 8, 10, 8); cl.setSpacing(4)
        cl.addWidget(QLabel(f"  {drive['letter']}:\\  Drive"))
        bar = QProgressBar(); bar.setRange(0, 100); bar.setValue(int(drive["pct"]))
        bar.setFixedHeight(6); bar.setTextVisible(False)
        color = "#2ecc71" if drive["pct"] < 75 else ("#f39c12" if drive["pct"] < 90 else "#e74c3c")
        bar.setStyleSheet(f"QProgressBar{{border:none;background:#2a2d35;border-radius:3px;}}"
                          f"QProgressBar::chunk{{background:{color};border-radius:3px;}}")
        cl.addWidget(bar)
        from core.disk_analyzer import DiskAnalyzer
        info = QLabel(f"{DiskAnalyzer.format_size(drive['free'])} free of {DiskAnalyzer.format_size(drive['total'])}")
        info.setStyleSheet("color:#6c7280; font-size:10px;")
        cl.addWidget(info)
        return card

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select directory to analyze")
        if folder:
            self.scan_path.setText(folder)

    def _analyze(self):
        path = self.scan_path.text()
        if not os.path.isdir(path):
            self.status.setText("  Invalid path."); return
        self.btn_analyze.setEnabled(False)
        self.prog.setRange(0, 0)
        self.status.setText("  Scanning… (this may take a moment)")
        self._thread = QThread()
        self._worker = _DiskWorker(self.analyzer, path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_done)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_done(self):
        from core.disk_analyzer import DiskAnalyzer
        self.prog.setRange(0, 100); self.prog.setValue(100)
        self.btn_analyze.setEnabled(True)
        top_files = self.analyzer.get_top_files(100)
        self.files_table.setRowCount(len(top_files))
        for i, item in enumerate(top_files):
            self.files_table.setItem(i, 0, QTableWidgetItem(item.path))
            sz = QTableWidgetItem(DiskAnalyzer.format_size(item.size))
            sz.setForeground(QColor("#4fc3f7"))
            self.files_table.setItem(i, 1, sz)
            ext = os.path.splitext(item.path)[1]
            self.files_table.setItem(i, 2, QTableWidgetItem(ext))

        types = self.analyzer.get_file_type_summary()
        self.types_table.setRowCount(len(types))
        for i, (cat, sz) in enumerate(sorted(types.items(), key=lambda x: x[1], reverse=True)):
            self.types_table.setItem(i, 0, QTableWidgetItem(cat))
            sz_item = QTableWidgetItem(DiskAnalyzer.format_size(sz))
            sz_item.setForeground(QColor("#4fc3f7"))
            self.types_table.setItem(i, 1, sz_item)

        self.status.setText(f"  Scan complete — {self.analyzer.total_scanned:,} files analyzed.")


class _DiskWorker(QObject):
    finished = pyqtSignal()
    def __init__(self, analyzer, path):
        super().__init__()
        self.analyzer = analyzer; self.path = path
    def run(self):
        self.analyzer.scan_directory(self.path, max_depth=5)
        self.finished.emit()


# ══════════════════════════════════════════════════════════════
# Duplicate Finder Tab
# ══════════════════════════════════════════════════════════════
class DuplicateTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.duplicate_finder import DuplicateFinder
        self.finder = DuplicateFinder()
        self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        header, _ = _page_header("Duplicate Finder",
                                  "Find and remove duplicate files to free up disk space")
        vl.addWidget(header)

        tb = QWidget(); tb.setStyleSheet("background:#21242c; border-bottom:1px solid #2a2d35;")
        tbl = QHBoxLayout(tb); tbl.setContentsMargins(16, 8, 16, 8)
        self.path_edit = QLineEdit(os.path.expanduser("~"))
        self.path_edit.setFixedHeight(32)
        btn_browse = QPushButton("Browse"); btn_browse.setFixedHeight(32)
        btn_browse.clicked.connect(self._browse)
        self.btn_scan = QPushButton("  🔍  Find Duplicates")
        self.btn_scan.setObjectName("PrimaryButton"); self.btn_scan.setFixedHeight(36)
        self.btn_scan.clicked.connect(self._scan)
        self.btn_delete_sel = QPushButton("  🗑  Delete Selected")
        self.btn_delete_sel.setObjectName("DangerButton"); self.btn_delete_sel.setEnabled(False)
        self.btn_delete_sel.clicked.connect(self._delete_selected)
        self.lbl_wasted = QLabel("")
        self.lbl_wasted.setStyleSheet("color:#f39c12; font-weight:bold;")
        tbl.addWidget(QLabel("Folder:")); tbl.addWidget(self.path_edit, 1)
        tbl.addWidget(btn_browse); tbl.addSpacing(8); tbl.addWidget(self.btn_scan)
        tbl.addSpacing(8); tbl.addWidget(self.btn_delete_sel)
        tbl.addStretch(); tbl.addWidget(self.lbl_wasted)
        vl.addWidget(tb)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["File Path", "Size"])
        self.tree.setColumnWidth(0, 600)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        vl.addWidget(self.tree, 1)
        self.prog, self.status = _status_bar(vl)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder to scan")
        if folder: self.path_edit.setText(folder)

    def _scan(self):
        from core.duplicate_finder import DuplicateFinder
        path = self.path_edit.text()
        if not os.path.isdir(path): return
        self.btn_scan.setEnabled(False); self.prog.setRange(0, 0)
        self.status.setText("  Scanning for duplicates…"); self.tree.clear()
        self._thread = QThread()
        self._worker = _DupWorker(self.finder, path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(lambda p, n: self.status.setText(f"  Hashing: {os.path.basename(p)}"))
        self._worker.finished.connect(self._on_done)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_done(self, groups):
        from core.duplicate_finder import DuplicateFinder
        self.prog.setRange(0, 100); self.prog.setValue(100)
        self.btn_scan.setEnabled(True)
        for grp in groups:
            parent = QTreeWidgetItem(self.tree, [
                f"  {grp.count} copies — {DuplicateFinder.format_size(grp.size)} each  "
                f"({DuplicateFinder.format_size(grp.wasted)} wasted)",
                DuplicateFinder.format_size(grp.wasted)
            ])
            parent.setFont(0, QFont("Segoe UI", 11, QFont.Weight.Bold))
            parent.setForeground(0, QColor("#f39c12"))
            for path in grp.paths:
                child = QTreeWidgetItem(parent, [path, ""])
                child.setCheckState(0, Qt.CheckState.Unchecked)
            parent.setExpanded(True)
        total_wasted = sum(g.wasted for g in groups)
        self.lbl_wasted.setText(f"Wasted: {DuplicateFinder.format_size(total_wasted)}")
        if groups: self.btn_delete_sel.setEnabled(True)
        self.status.setText(f"  Found {len(groups)} duplicate groups.")

    def _delete_selected(self):
        from core.duplicate_finder import DuplicateFinder
        paths = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group = root.child(i)
            for j in range(group.childCount()):
                child = group.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    paths.append(child.text(0))
        if not paths: return
        deleted, freed = self.finder.delete_duplicates(paths)
        self.status.setText(f"  Deleted {deleted} files, freed {DuplicateFinder.format_size(freed)}.")
        self._scan()


class _DupWorker(QObject):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(list)
    def __init__(self, finder, path):
        super().__init__()
        self.finder = finder; self.path = path
    def run(self):
        groups = self.finder.find([self.path], progress_cb=lambda p, n: self.progress.emit(p, n))
        self.finished.emit(groups)


# ══════════════════════════════════════════════════════════════
# Secure Wiper Tab
# ══════════════════════════════════════════════════════════════
class WiperTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.secure_wiper import SecureWiper
        self.wiper = SecureWiper(passes=3)
        self._files = []
        self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        header, _ = _page_header("Secure File Wiper",
                                  "Permanently erase files using multi-pass overwrite (DoD 5220.22-M)")
        vl.addWidget(header)

        body = QWidget(); body.setStyleSheet("background:#1a1d23;")
        bl = QVBoxLayout(body); bl.setContentsMargins(24, 20, 24, 20); bl.setSpacing(14)

        # Pass selector
        opts_row = QHBoxLayout()
        opts_row.addWidget(QLabel("Wipe method:"))
        self.pass_combo = QComboBox()
        from core.secure_wiper import SecureWiper
        for passes, desc in SecureWiper.get_pass_descriptions().items():
            self.pass_combo.addItem(desc, passes)
        self.pass_combo.setCurrentIndex(1)
        opts_row.addWidget(self.pass_combo); opts_row.addStretch()
        bl.addLayout(opts_row)

        # File list
        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        bl.addWidget(self.file_list, 1)

        btn_row = QHBoxLayout()
        btn_add_files = QPushButton("  ➕  Add Files")
        btn_add_files.clicked.connect(self._add_files)
        btn_add_folder = QPushButton("  📁  Add Folder")
        btn_add_folder.clicked.connect(self._add_folder)
        btn_remove = QPushButton("  ✖  Remove Selected")
        btn_remove.clicked.connect(self._remove_selected)
        self.btn_wipe = QPushButton("  🔒  Wipe Files")
        self.btn_wipe.setObjectName("DangerButton"); self.btn_wipe.setEnabled(False)
        self.btn_wipe.clicked.connect(self._wipe)
        self.btn_wipe_free = QPushButton("  💽  Wipe Free Space")
        self.btn_wipe_free.clicked.connect(self._wipe_free_space)
        btn_row.addWidget(btn_add_files); btn_row.addWidget(btn_add_folder)
        btn_row.addWidget(btn_remove); btn_row.addStretch()
        btn_row.addWidget(self.btn_wipe_free); btn_row.addWidget(self.btn_wipe)
        bl.addLayout(btn_row)
        vl.addWidget(body, 1)
        self.prog, self.status = _status_bar(vl)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select files to wipe")
        for f in files:
            if f not in self._files:
                self._files.append(f)
                self.file_list.addItem(f)
        self.btn_wipe.setEnabled(bool(self._files))

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder to wipe")
        if folder and folder not in self._files:
            self._files.append(folder)
            self.file_list.addItem(folder)
        self.btn_wipe.setEnabled(bool(self._files))

    def _remove_selected(self):
        for item in self.file_list.selectedItems():
            path = item.text()
            if path in self._files: self._files.remove(path)
            self.file_list.takeItem(self.file_list.row(item))
        self.btn_wipe.setEnabled(bool(self._files))

    def _wipe(self):
        passes = self.pass_combo.currentData()
        self.wiper.passes = passes
        self.btn_wipe.setEnabled(False); self.prog.setRange(0, 0)
        self._thread = QThread()
        self._worker = _WipeWorker(self.wiper, list(self._files))
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(lambda p: self.status.setText(f"  Wiping: {os.path.basename(p)}…"))
        self._worker.finished.connect(self._on_wipe_done)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_wipe_done(self, wiped, failed):
        self.prog.setRange(0, 100); self.prog.setValue(100)
        self._files.clear(); self.file_list.clear()
        self.status.setText(f"  Wiped {wiped} items. {failed} failed.")

    def _wipe_free_space(self):
        drive = "C:\\"
        self.status.setText(f"  Wiping free space on {drive}… (this may take minutes)")
        self.prog.setRange(0, 0)
        self._thread2 = QThread()
        self._wfworker = _WipeFreeWorker(self.wiper, drive)
        self._wfworker.moveToThread(self._thread2)
        self._thread2.started.connect(self._wfworker.run)
        self._wfworker.finished.connect(lambda ok: [
            self.prog.setRange(0, 100), self.prog.setValue(100),
            self.status.setText("  Free space wipe complete." if ok else "  Free space wipe failed.")
        ])
        self._wfworker.finished.connect(self._thread2.quit)
        self._thread2.start()


class _WipeWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(int, int)
    def __init__(self, wiper, files):
        super().__init__()
        self.wiper = wiper; self.files = files
    def run(self):
        w, f = self.wiper.wipe_files(self.files, lambda p, wc, fc: self.progress.emit(p))
        self.finished.emit(w, f)

class _WipeFreeWorker(QObject):
    finished = pyqtSignal(bool)
    def __init__(self, wiper, drive):
        super().__init__()
        self.wiper = wiper; self.drive = drive
    def run(self):
        ok = self.wiper.wipe_free_space(self.drive)
        self.finished.emit(ok)


# ══════════════════════════════════════════════════════════════
# Software Updater Tab
# ══════════════════════════════════════════════════════════════
class UpdaterTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.software_updater import SoftwareUpdater
        self.updater = SoftwareUpdater()
        self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        header, self.btn_check = _page_header(
            "Software Updater",
            "Check for outdated software and update everything in one click",
            "  ⬆  Check for Updates"
        )
        self.btn_check.clicked.connect(self._check)
        vl.addWidget(header)

        tb = QWidget(); tb.setStyleSheet("background:#21242c; border-bottom:1px solid #2a2d35;")
        tbl = QHBoxLayout(tb); tbl.setContentsMargins(16, 8, 16, 8)
        self.btn_update_all = QPushButton("  ⬆  Update All")
        self.btn_update_all.setObjectName("SuccessButton"); self.btn_update_all.setEnabled(False)
        self.btn_update_all.clicked.connect(self._update_all)
        self.btn_update_sel = QPushButton("  ⬆  Update Selected"); self.btn_update_sel.setEnabled(False)
        self.btn_update_sel.clicked.connect(self._update_selected)
        self.lbl_count = QLabel(""); self.lbl_count.setStyleSheet("color:#6c7280;")
        tbl.addWidget(self.btn_update_all); tbl.addSpacing(8)
        tbl.addWidget(self.btn_update_sel); tbl.addStretch(); tbl.addWidget(self.lbl_count)
        vl.addWidget(tb)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Application", "Current Version", "Latest Version", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.selectionModel().selectionChanged.connect(
            lambda: self.btn_update_sel.setEnabled(bool(self.table.selectionModel().selectedRows()) and bool(self.updater.updates))
        )
        vl.addWidget(self.table, 1)

        # Winget info banner
        if not self.updater.is_winget_installed():
            info = QLabel("  ℹ  Windows Package Manager (winget) not found. Install it from the Microsoft Store for full update support.")
            info.setStyleSheet("background:#2a1f00; color:#f39c12; padding:8px 16px; border-top:1px solid #3a2f00;")
            info.setWordWrap(True)
            vl.addWidget(info)

        self.prog, self.status = _status_bar(vl)

    def _check(self):
        self.btn_check.setEnabled(False); self.prog.setRange(0, 0)
        self.table.setRowCount(0)
        self._thread = QThread()
        self._worker = _UpdateWorker(self.updater)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(lambda m: self.status.setText(f"  {m}"))
        self._worker.finished.connect(self._on_done)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_done(self, updates):
        self.prog.setRange(0, 100); self.prog.setValue(100)
        self.btn_check.setEnabled(True)
        self.table.setRowCount(len(updates))
        for i, u in enumerate(updates):
            self.table.setItem(i, 0, QTableWidgetItem(u.name))
            self.table.setItem(i, 1, QTableWidgetItem(u.current_version))
            avail = QTableWidgetItem(u.available_version)
            avail.setForeground(QColor("#2ecc71")); self.table.setItem(i, 2, avail)
            self.table.setItem(i, 3, QTableWidgetItem("Update available"))
        self.lbl_count.setText(f"{len(updates)} updates available")
        if updates: self.btn_update_all.setEnabled(True)
        self.status.setText(f"  Found {len(updates)} updates.")

    def _update_all(self):
        self.btn_update_all.setEnabled(False); self.prog.setRange(0, 0)
        self._thread2 = QThread()
        self._worker2 = _InstallAllWorker(self.updater)
        self._worker2.moveToThread(self._thread2)
        self._thread2.started.connect(self._worker2.run)
        self._worker2.progress.connect(lambda m: self.status.setText(f"  {m}"))
        self._worker2.finished.connect(lambda: [self.prog.setRange(0, 100), self.prog.setValue(100),
                                                 self.status.setText("  All updates installed.")])
        self._worker2.finished.connect(self._thread2.quit)
        self._thread2.start()

    def _update_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows: return
        u = self.updater.updates[rows[0].row()]
        self.prog.setRange(0, 0); self.status.setText(f"  Updating {u.name}…")
        ok = self.updater.install_update(u, lambda m: self.status.setText(f"  {m}"))
        self.prog.setRange(0, 100); self.prog.setValue(100)
        self.status.setText(f"  {'Updated' if ok else 'Failed'}: {u.name}")


class _UpdateWorker(QObject):
    progress = pyqtSignal(str); finished = pyqtSignal(list)
    def __init__(self, updater): super().__init__(); self.updater = updater
    def run(self): self.finished.emit(self.updater.check(lambda m: self.progress.emit(m)))

class _InstallAllWorker(QObject):
    progress = pyqtSignal(str); finished = pyqtSignal()
    def __init__(self, updater): super().__init__(); self.updater = updater
    def run(self): self.updater.install_all(lambda m: self.progress.emit(m)); self.finished.emit()


# ══════════════════════════════════════════════════════════════
# System Restore Tab
# ══════════════════════════════════════════════════════════════
class RestoreTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.system_restore import SystemRestoreManager
        self.manager = SystemRestoreManager()
        self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        header, self.btn_refresh = _page_header(
            "System Restore Manager",
            "View, create, and delete Windows System Restore points",
            "  🔄  Refresh"
        )
        self.btn_refresh.clicked.connect(self._load)
        vl.addWidget(header)

        tb = QWidget(); tb.setStyleSheet("background:#21242c; border-bottom:1px solid #2a2d35;")
        tbl = QHBoxLayout(tb); tbl.setContentsMargins(16, 8, 16, 8)
        self.btn_create = QPushButton("  ➕  Create Restore Point")
        self.btn_create.setObjectName("SuccessButton")
        self.btn_create.clicked.connect(self._create)
        self.btn_delete_old = QPushButton("  🗑  Delete All But Last")
        self.btn_delete_old.setObjectName("DangerButton")
        self.btn_delete_old.clicked.connect(self._delete_all_but_last)
        self.btn_open_ui = QPushButton("  🔄  Open Windows Restore")
        self.btn_open_ui.clicked.connect(self.manager.open_system_restore_ui)
        self.lbl_storage = QLabel(""); self.lbl_storage.setStyleSheet("color:#6c7280;")
        tbl.addWidget(self.btn_create); tbl.addSpacing(8)
        tbl.addWidget(self.btn_delete_old); tbl.addSpacing(8)
        tbl.addWidget(self.btn_open_ui); tbl.addStretch(); tbl.addWidget(self.lbl_storage)
        vl.addWidget(tb)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Description", "Type", "Created", "Sequence"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        vl.addWidget(self.table, 1)
        self.prog, self.status = _status_bar(vl)
        self._load()

    def _load(self):
        self.prog.setRange(0, 0)
        points = self.manager.get_restore_points()
        self.table.setRowCount(len(points))
        for i, p in enumerate(points):
            self.table.setItem(i, 0, QTableWidgetItem(p.description))
            self.table.setItem(i, 1, QTableWidgetItem(p.restore_type))
            self.table.setItem(i, 2, QTableWidgetItem(p.creation_time))
            self.table.setItem(i, 3, QTableWidgetItem(str(p.sequence)))
        storage = self.manager.get_shadow_storage_info()
        self.lbl_storage.setText(f"Used: {storage.get('used', 'N/A')}")
        self.prog.setRange(0, 100); self.prog.setValue(100)
        self.status.setText(f"  {len(points)} restore points found.")

    def _create(self):
        self.status.setText("  Creating restore point…"); self.prog.setRange(0, 0)
        ok = self.manager.create("PCPolish - Manual Restore Point")
        self.prog.setRange(0, 100); self.prog.setValue(100)
        self.status.setText("  ✓ Restore point created." if ok else "  Failed to create restore point.")
        if ok: self._load()

    def _delete_all_but_last(self):
        ok = self.manager.delete_all_but_last()
        self.status.setText("  ✓ Old restore points deleted." if ok else "  Delete failed.")
        if ok: self._load()


# ══════════════════════════════════════════════════════════════
# Performance Tab
# ══════════════════════════════════════════════════════════════
class PerformanceTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.performance_optimizer import PerformanceOptimizer
        self.optimizer = PerformanceOptimizer()
        self._build()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_metrics)
        self._timer.start(3000)

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        header, self.btn_refresh = _page_header(
            "Performance Optimizer",
            "Monitor running processes, services, and system resource usage",
            "  ⚡  Refresh"
        )
        self.btn_refresh.clicked.connect(self._load_processes)
        vl.addWidget(header)

        # Metrics strip
        metrics_widget = QWidget()
        metrics_widget.setStyleSheet("background:#13151a; border-bottom:1px solid #2a2d35;")
        ml = QHBoxLayout(metrics_widget); ml.setContentsMargins(20, 10, 20, 10)
        self.cpu_lbl  = self._metric_widget("CPU",    "–", "#4fc3f7")
        self.ram_lbl  = self._metric_widget("RAM",    "–", "#2ecc71")
        self.disk_lbl = self._metric_widget("Disk R/W","–","#f39c12")
        self.up_lbl   = self._metric_widget("Uptime", "–", "#9b59b6")
        for w in [self.cpu_lbl, self.ram_lbl, self.disk_lbl, self.up_lbl]:
            ml.addWidget(w)
        ml.addStretch()
        vl.addWidget(metrics_widget)

        # Process table
        tb = QWidget(); tb.setStyleSheet("background:#21242c; border-bottom:1px solid #2a2d35;")
        tbl = QHBoxLayout(tb); tbl.setContentsMargins(16, 8, 16, 8)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Sort: Memory", "Sort: CPU", "Sort: Name"])
        self.sort_combo.currentIndexChanged.connect(self._load_processes)
        self.btn_end = QPushButton("  ✖  End Process")
        self.btn_end.setObjectName("DangerButton"); self.btn_end.setEnabled(False)
        self.btn_end.clicked.connect(self._end_process)
        self.lbl_proc_count = QLabel(""); self.lbl_proc_count.setStyleSheet("color:#6c7280;")
        tbl.addWidget(QLabel("Processes:")); tbl.addWidget(self.sort_combo)
        tbl.addSpacing(16); tbl.addWidget(self.btn_end)
        tbl.addStretch(); tbl.addWidget(self.lbl_proc_count)
        vl.addWidget(tb)

        self.proc_table = QTableWidget(0, 5)
        self.proc_table.setHorizontalHeaderLabels(["Process", "PID", "CPU %", "RAM (MB)", "Status"])
        self.proc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.proc_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.proc_table.setAlternatingRowColors(True)
        self.proc_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.proc_table.selectionModel().selectionChanged.connect(
            lambda: self.btn_end.setEnabled(bool(self.proc_table.selectionModel().selectedRows()))
        )
        vl.addWidget(self.proc_table, 1)
        self.prog, self.status = _status_bar(vl)
        self._load_processes()

    def _metric_widget(self, title, value, color):
        w = QFrame(); w.setStyleSheet(f"background:#1e2128; border-radius:6px; padding:8px;")
        w.setFixedWidth(150)
        wl = QVBoxLayout(w); wl.setContentsMargins(10, 8, 10, 8); wl.setSpacing(2)
        t = QLabel(title); t.setStyleSheet("color:#6c7280; font-size:10px;")
        v = QLabel(value); v.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        v.setStyleSheet(f"color:{color};")
        wl.addWidget(t); wl.addWidget(v)
        w._value_lbl = v
        return w

    def _update_metrics(self):
        metrics = self.optimizer.get_system_metrics()
        if not metrics: return
        self.cpu_lbl._value_lbl.setText(f"{metrics.get('cpu_percent', 0):.1f}%")
        self.ram_lbl._value_lbl.setText(f"{metrics.get('ram_percent', 0):.1f}%")
        rw = f"{metrics.get('disk_read_mb',0):.0f}/{metrics.get('disk_write_mb',0):.0f} MB"
        self.disk_lbl._value_lbl.setText(rw)
        self.up_lbl._value_lbl.setText(f"{metrics.get('uptime_hours', 0):.1f}h")

    def _load_processes(self):
        sort_idx = self.sort_combo.currentIndex() if hasattr(self, "sort_combo") else 0
        sort_map = {0: "memory", 1: "cpu", 2: "name"}
        sort_by = sort_map.get(sort_idx, "memory")
        procs = self.optimizer.get_processes(sort_by=sort_by)
        self.proc_table.setRowCount(len(procs))
        for i, p in enumerate(procs):
            self.proc_table.setItem(i, 0, QTableWidgetItem(p.name))
            self.proc_table.setItem(i, 1, QTableWidgetItem(str(p.pid)))
            cpu_item = QTableWidgetItem(f"{p.cpu_percent:.1f}")
            if p.cpu_percent > 20: cpu_item.setForeground(QColor("#e74c3c"))
            self.proc_table.setItem(i, 2, cpu_item)
            ram_item = QTableWidgetItem(f"{p.memory_mb:.1f}")
            if p.memory_mb > 500: ram_item.setForeground(QColor("#f39c12"))
            self.proc_table.setItem(i, 3, ram_item)
            self.proc_table.setItem(i, 4, QTableWidgetItem(p.status))
        self.lbl_proc_count.setText(f"{len(procs)} processes")
        self.status.setText(f"  {len(procs)} processes running.")

    def _end_process(self):
        rows = self.proc_table.selectionModel().selectedRows()
        if not rows: return
        pid = int(self.proc_table.item(rows[0].row(), 1).text())
        name = self.proc_table.item(rows[0].row(), 0).text()
        ok = self.optimizer.kill_process(pid)
        self.status.setText(f"  {'Terminated' if ok else 'Failed to terminate'}: {name} (PID {pid})")
        if ok: self._load_processes()


# ══════════════════════════════════════════════════════════════
# Scheduler Tab
# ══════════════════════════════════════════════════════════════
class SchedulerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.scheduler_manager import SchedulerManager
        self.scheduler = SchedulerManager()
        self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        header, _ = _page_header("Scheduled Cleaning",
                                  "Automatically clean your PC on a schedule without manual intervention")
        vl.addWidget(header)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none; background:#1a1d23;}")
        body = QWidget(); body.setStyleSheet("background:#1a1d23;")
        bl = QVBoxLayout(body); bl.setContentsMargins(32, 24, 32, 24); bl.setSpacing(20)

        # Enable toggle
        self.enable_cb = QCheckBox("Enable automatic scheduled cleaning")
        self.enable_cb.setFont(QFont("Segoe UI", 13))
        self.enable_cb.setChecked(self.scheduler.config.get("enabled", False))
        bl.addWidget(self.enable_cb)

        # Frequency group
        freq_group = QGroupBox("Frequency")
        fgl = QVBoxLayout(freq_group)
        self.rb_daily  = QRadioButton("Daily")
        self.rb_weekly = QRadioButton("Weekly")
        self.rb_idle   = QRadioButton("When computer is idle")
        freq = self.scheduler.config.get("frequency", "weekly")
        if freq == "daily": self.rb_daily.setChecked(True)
        elif freq == "weekly": self.rb_weekly.setChecked(True)
        else: self.rb_idle.setChecked(True)
        fgl.addWidget(self.rb_daily); fgl.addWidget(self.rb_weekly); fgl.addWidget(self.rb_idle)
        bl.addWidget(freq_group)

        # Day / time
        dt_row = QHBoxLayout()
        self.day_combo = QComboBox()
        self.day_combo.addItems(["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"])
        saved_day = self.scheduler.config.get("day_of_week", "Monday")
        self.day_combo.setCurrentText(saved_day)
        self.time_edit = QLineEdit(self.scheduler.config.get("time_of_day", "02:00"))
        self.time_edit.setFixedWidth(80)
        dt_row.addWidget(QLabel("Day:")); dt_row.addWidget(self.day_combo)
        dt_row.addSpacing(16); dt_row.addWidget(QLabel("Time (HH:MM):")); dt_row.addWidget(self.time_edit)
        dt_row.addStretch()
        bl.addLayout(dt_row)

        # What to clean
        clean_group = QGroupBox("What to Clean")
        cgl = QVBoxLayout(clean_group)
        self.clean_checks = {}
        for key, label in [("temp_files","Temp Files"),("browser_cache","Browser Cache"),
                            ("registry","Registry"),("recycle_bin","Recycle Bin")]:
            cb = QCheckBox(label)
            cb.setChecked(key in self.scheduler.config.get("clean_types", ["temp_files","browser_cache"]))
            self.clean_checks[key] = cb
            cgl.addWidget(cb)
        bl.addWidget(clean_group)

        # Status info
        info_group = QGroupBox("Schedule Status")
        igl = QVBoxLayout(info_group)
        self.next_run_lbl = QLabel(f"Next run:  {self.scheduler.get_next_run_str()}")
        self.last_run_lbl = QLabel(f"Last run:  {self.scheduler.get_last_run_str()}")
        igl.addWidget(self.next_run_lbl); igl.addWidget(self.last_run_lbl)
        bl.addWidget(info_group)

        # Save button
        btn_save = QPushButton("  💾  Save Schedule")
        btn_save.setObjectName("PrimaryButton"); btn_save.setFixedHeight(40)
        btn_save.clicked.connect(self._save)
        bl.addWidget(btn_save); bl.addStretch()

        scroll.setWidget(body)
        vl.addWidget(scroll, 1)
        self.prog, self.status = _status_bar(vl)

    def _save(self):
        freq = "daily" if self.rb_daily.isChecked() else ("on_idle" if self.rb_idle.isChecked() else "weekly")
        clean_types = [k for k, cb in self.clean_checks.items() if cb.isChecked()]
        config = {
            "enabled": self.enable_cb.isChecked(),
            "frequency": freq,
            "day_of_week": self.day_combo.currentText(),
            "time_of_day": self.time_edit.text(),
            "clean_types": clean_types,
        }
        self.scheduler.save_config(config)
        self.next_run_lbl.setText(f"Next run:  {self.scheduler.get_next_run_str()}")
        if self.enable_cb.isChecked():
            self.scheduler.start()
        else:
            self.scheduler.stop()
        self.status.setText("  ✓  Schedule saved.")


# ══════════════════════════════════════════════════════════════
# Cookie Manager Tab
# ══════════════════════════════════════════════════════════════
class CookieTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.cookie_manager import CookieManager
        self.manager = CookieManager()
        self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        header, _ = _page_header("Cookie Manager",
                                  "View, manage, and selectively delete browser cookies with domain whitelist")
        vl.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:#2a2d35;}")

        # Left: cookie list
        left = QWidget(); left.setStyleSheet("background:#1a1d23;")
        ll = QVBoxLayout(left); ll.setContentsMargins(16, 12, 8, 12)
        row = QHBoxLayout()
        self.browser_combo = QComboBox()
        from core.cookie_manager import CookieManager
        for b in CookieManager.BROWSER_COOKIE_PATHS:
            self.browser_combo.addItem(b)
        self.btn_load = QPushButton("  🍪  Load Cookies")
        self.btn_load.setObjectName("PrimaryButton"); self.btn_load.setFixedHeight(34)
        self.btn_load.clicked.connect(self._load_cookies)
        self.btn_del_all = QPushButton("  🗑  Delete All")
        self.btn_del_all.setObjectName("DangerButton"); self.btn_del_all.setEnabled(False)
        self.btn_del_all.clicked.connect(self._delete_all)
        row.addWidget(self.browser_combo); row.addWidget(self.btn_load)
        row.addWidget(self.btn_del_all)
        ll.addLayout(row)

        self.cookie_table = QTableWidget(0, 3)
        self.cookie_table.setHorizontalHeaderLabels(["Domain", "Name", "Expires"])
        self.cookie_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cookie_table.setAlternatingRowColors(True)
        self.cookie_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        ll.addWidget(self.cookie_table, 1)

        # Right: whitelist
        right = QWidget(); right.setStyleSheet("background:#1a1d23;")
        rl = QVBoxLayout(right); rl.setContentsMargins(8, 12, 16, 12)
        rl.addWidget(QLabel("  Cookie Whitelist (protected domains)"))
        self.whitelist_widget = QListWidget()
        for d in self.manager.get_whitelist():
            self.whitelist_widget.addItem(d)
        rl.addWidget(self.whitelist_widget, 1)

        add_row = QHBoxLayout()
        self.domain_edit = QLineEdit(); self.domain_edit.setPlaceholderText("e.g. google.com")
        btn_add = QPushButton("Add"); btn_add.clicked.connect(self._add_whitelist)
        btn_rem = QPushButton("Remove"); btn_rem.clicked.connect(self._remove_whitelist)
        add_row.addWidget(self.domain_edit); add_row.addWidget(btn_add); add_row.addWidget(btn_rem)
        rl.addLayout(add_row)

        splitter.addWidget(left); splitter.addWidget(right)
        splitter.setSizes([700, 300])
        vl.addWidget(splitter, 1)
        self.prog, self.status = _status_bar(vl)

    def _load_cookies(self):
        browser = self.browser_combo.currentText()
        self.prog.setRange(0, 0); self.status.setText("  Loading cookies…")
        cookies = self.manager.load_cookies(browser)
        self.cookie_table.setRowCount(len(cookies))
        for i, c in enumerate(cookies):
            self.cookie_table.setItem(i, 0, QTableWidgetItem(c.host))
            self.cookie_table.setItem(i, 1, QTableWidgetItem(c.name))
            self.cookie_table.setItem(i, 2, QTableWidgetItem(c.expires_str))
        self.prog.setRange(0, 100); self.prog.setValue(100)
        self.btn_del_all.setEnabled(True)
        self.status.setText(f"  Loaded {len(cookies)} cookies from {browser}.")

    def _delete_all(self):
        browser = self.browser_combo.currentText()
        deleted, _ = self.manager.delete_cookies(browser, preserve_whitelist=True)
        self.cookie_table.setRowCount(0)
        self.btn_del_all.setEnabled(False)
        self.status.setText(f"  Deleted {deleted} cookies (whitelist preserved).")

    def _add_whitelist(self):
        domain = self.domain_edit.text().strip()
        if domain and self.manager.add_to_whitelist(domain):
            self.whitelist_widget.addItem(domain)
            self.domain_edit.clear()

    def _remove_whitelist(self):
        for item in self.whitelist_widget.selectedItems():
            self.manager.remove_from_whitelist(item.text())
            self.whitelist_widget.takeItem(self.whitelist_widget.row(item))
