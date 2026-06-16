# -*- mode: python ; coding: utf-8 -*-
import os
import pykakasi
from PyInstaller.utils.hooks import collect_data_files

# Dynamically find pykakasi's internal data directory
pykakasi_data = collect_data_files('pykakasi')

a = Analysis(
    ['src/ui.py'],
    pathex=['src'],
    binaries=[],
    # Bundle our 'data' folder AND the pykakasi data folder
    datas=[('data', 'data')] + pykakasi_data,
    hiddenimports=['engine', 'rules', 'pykakasi'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Bungo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    icon='/Users/a2macpro/Desktop/Coding Projects/Bungo/bungo_icon.icns',
    console=False,
    disable_windowed_traceback=False,
)