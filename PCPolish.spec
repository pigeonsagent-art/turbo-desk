# -*- mode: python ; coding: utf-8 -*-
PyInstaller spec for PCPolish.
Produces a single-folder dist with run.exe as the launcher.
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['C:\\PCPolish'],
    binaries=[],
    datas=[
        # Include all Python source packages so imports work at runtime
        ('core',  'core'),
        ('ui',    'ui'),
    ],
    hiddenimports=[
        # PyQt6 internals
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.sip',
        # Optional runtime deps — swallowed gracefully if missing
        'psutil',
        'watchdog',
        'watchdog.observers',
        'watchdog.observers.winapi',
        'watchdog.events',
        'schedule',
        'winreg',
        # Core modules
        'core.file_cleaner',
        'core.browser_cleaner',
        'core.registry_cleaner',
        'core.startup_manager',
        'core.disk_analyzer',
        'core.duplicate_finder',
        'core.secure_wiper',
        'core.uninstaller',
        'core.software_updater',
        'core.system_restore',
        'core.performance_optimizer',
        'core.health_check',
        'core.monitor',
        'core.scheduler_manager',
        'core.cookie_manager',
        # UI modules
        'ui.main_window',
        'ui.health_tab',
        'ui.cleaner_tab',
        'ui.tools_tab',
        'ui.settings_tab',
        'ui.styles',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'pandas',
        'scipy', 'PIL', 'cv2', 'test', 'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='run',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # No black console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets\\icon.ico',  # Uncomment and add icon.ico if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PCPolish',
)
