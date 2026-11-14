# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the macOS universal2 build (SnakeGame.app).
#
# The source folder defaults to the project root (the parent of this file).
# To build from a snapshot copy instead, set SNAKE_SRC, e.g.
#   SNAKE_SRC=/private/tmp/SnakeGameMacBuild/src-v2.8
# The version is read from APP_VERSION in theme.py, so there is nothing to edit
# here when releasing a new version.
#
# Build (from any directory, with a venv that has pyinstaller + pygame-ce built
# from python.org's universal2 Python so the result runs on x86_64 and arm64):
#   python -m PyInstaller -y --clean --distpath <dist> --workpath <work> packaging/SnakeGame-mac.spec
import os
import re

SRC = os.path.abspath(os.environ.get('SNAKE_SRC') or os.path.join(SPECPATH, '..'))
with open(os.path.join(SRC, 'theme.py'), encoding='utf-8') as f:
    VERSION = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', f.read(), re.M).group(1)

a = Analysis(
    [os.path.join(SRC, 'snakegame.py')],
    pathex=[SRC],
    binaries=[],
    datas=[(os.path.join(SRC, 'assets', 'icon_64.png'), 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SnakeGame',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='universal2',
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(SRC, 'assets', 'icon.icns')],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SnakeGame',
)
app = BUNDLE(
    coll,
    name='SnakeGame.app',
    icon=os.path.join(SRC, 'assets', 'icon.icns'),
    bundle_identifier='com.mhiroshijsg.snakegame',
    version=VERSION,
    info_plist={
        'CFBundleDisplayName': 'Snake Game',
        'CFBundleShortVersionString': VERSION,
        'CFBundleVersion': VERSION,
        'LSMinimumSystemVersion': '10.13.0',
        'NSHighResolutionCapable': True,
    },
)
