# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

# 1. Force PyInstaller to physically grab pykakasi's hidden kanwadict4.db
kakasi_data = collect_data_files('pykakasi')

# 2. Tell PyInstaller exactly where our new Bungo database is
app_data = [
    ('data/bungo_dictionary.db', 'data')
]

# Combine the data arrays
all_datas = kakasi_data + app_data

a = Analysis(
    ['src/ui.py'], 
    pathex=['src'],
    binaries=[],
    datas=all_datas,
    hiddenimports=['sudachipy', 'sudachidict_core', 'pykakasi', 'sqlite3'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Bungo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # <--- Set to True ONLY if you want to see the terminal for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Bungo',
)