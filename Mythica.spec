# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Mythica Pipeline."""

import sys
from pathlib import Path

block_cipher = None
src = str(Path(SPECPATH) / "src")

a = Analysis(
    [str(Path(SPECPATH) / "src" / "main.py")],
    pathex=[src],
    binaries=[],
    datas=[],
    hiddenimports=[
        # keyring backends
        "keyring.backends",
        "keyring.backends.macOS",
        "keyring.backends.fail",
        "keyring.backends.null",
        # tkinterdnd2
        "tkinterdnd2",
        # PIL image formats
        "PIL._imagingtk",
        "PIL.ImageTk",
        "PIL.Image",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="Mythica Pipeline",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No Terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Mythica Pipeline",
)

app = BUNDLE(
    coll,
    name="Mythica Pipeline.app",
    icon=None,
    bundle_identifier="com.mythica.pipeline",
    info_plist={
        "CFBundleName": "Mythica Pipeline",
        "CFBundleDisplayName": "Mythica Pipeline",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0",
        "NSHighResolutionCapable": True,
        "LSUIElement": False,
    },
)
