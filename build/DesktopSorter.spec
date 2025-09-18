# -*- mode: python ; coding: utf-8 -*-
"""
Desktop Sorter PyInstaller Specification
Builds a Windows executable with all required resources and dependencies
"""

import os
import pathlib
from PyInstaller.utils.hooks import collect_data_files

# Project root directory
ROOT = pathlib.Path(SPECPATH).parent

# Get tkdnd path from environment (set by package.py script)
TKDND_PATH = os.environ.get('TKDND_PATH')
if not TKDND_PATH:
    raise RuntimeError("TKDND_PATH environment variable not set. Run via build/package.py")

# Data files to bundle
datas = [
    # Bundle entire resources directory
    (str(ROOT / 'resources'), 'resources'),

    # Bundle tkinterdnd2 native libraries for Windows
    (TKDND_PATH, 'tkdnd2.9'),
]

# Collect additional data files from dependencies
try:
    # Collect Pillow data files if needed
    datas.extend(collect_data_files('PIL'))
except Exception:
    pass

# Hidden imports for modules loaded dynamically
hiddenimports = [
    # Windows timezone support
    'win32timezone',

    # PIL/Pillow imports that may not be auto-detected
    'PIL._tkinter_finder',
    'PIL._imagingft',
    'PIL._imaging',

    # pywin32 modules
    'win32api',
    'win32gui',
    'win32con',
    'pywintypes',
    'pythoncom',

    # tkinterdnd2 dependencies
    'tkinterdnd2',

    # Standard library modules that might be missed
    'ctypes.wintypes',
    'email.mime.text',
    'email.mime.multipart',
]

# Exclude unnecessary modules to reduce bundle size
excludes = [
    'matplotlib',
    'numpy',
    'scipy',
    'pandas',
    'jupyter',
    'IPython',
    'tornado',
    'zmq',
]

# PyInstaller Analysis
a = Analysis(
    [str(ROOT / 'src' / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate entries and optimize
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Executable configuration
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DesktopSorter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed mode
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'resources' / 'icon.ico'),
    version_file=None,
)

# Collect all files into distribution directory
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DesktopSorter',
)