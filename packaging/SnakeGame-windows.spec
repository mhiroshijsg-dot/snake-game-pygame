# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Windows x64 build (dist/SnakeGame/SnakeGame.exe).
#
# Like the macOS spec, the version is read from APP_VERSION in theme.py and the
# exe's version resource is generated from it, so there is nothing to edit here
# (and no version_info.txt to keep in sync) when releasing a new version.
#
# Build on Windows from the project root:
#   python -m PyInstaller -y --clean packaging/SnakeGame-windows.spec
import os
import re

SRC = os.path.abspath(os.environ.get('SNAKE_SRC') or os.path.join(SPECPATH, '..'))
with open(os.path.join(SRC, 'theme.py'), encoding='utf-8') as f:
    VERSION = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', f.read(), re.M).group(1)

# "2.8" -> (2, 8, 0, 0)
_parts = [int(p) for p in VERSION.split('.')][:4]
VERSION_TUPLE = tuple(_parts + [0] * (4 - len(_parts)))
VERSION_STR = '.'.join(str(p) for p in VERSION_TUPLE)

os.makedirs(workpath, exist_ok=True)
VERSION_FILE = os.path.join(workpath, 'version_info.txt')
with open(VERSION_FILE, 'w', encoding='utf-8') as f:
    f.write(f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={VERSION_TUPLE},
    prodvers={VERSION_TUPLE},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'SnakeGame'),
          StringStruct('FileDescription', 'SnakeGame'),
          StringStruct('FileVersion', '{VERSION_STR}'),
          StringStruct('InternalName', 'SnakeGame'),
          StringStruct('OriginalFilename', 'SnakeGame.exe'),
          StringStruct('ProductName', 'SnakeGame'),
          StringStruct('ProductVersion', '{VERSION_STR}'),
        ],
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ],
)
""")

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
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=VERSION_FILE,
    icon=os.path.join(SRC, 'assets', 'icon.ico'),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SnakeGame',
)
