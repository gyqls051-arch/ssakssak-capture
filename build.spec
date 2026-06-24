# PyInstaller spec for Ssak Kimchi Capture
# Build with: pyinstaller build.spec
#
# ffmpeg.exe 번들 (선택):
#   bin/ffmpeg.exe 를 두면 빌드 산출물에 같이 포함됨 (find_ffmpeg가 sys._MEIPASS에서 찾음).
#   없어도 빌드는 됨 — 그 경우 사용자가 PATH에 ffmpeg 두거나
#   ~/.ssakkimchi/bin/ffmpeg.exe 에 배치해야 녹화 가능.

import os

block_cipher = None

_spec_dir = os.path.dirname(os.path.abspath(SPEC))
_ffmpeg_local = os.path.join(_spec_dir, 'bin', 'ffmpeg.exe')
_ffmpeg_binaries = [(_ffmpeg_local, 'bin')] if os.path.isfile(_ffmpeg_local) else []

_assets_dir = os.path.join(_spec_dir, 'assets')
_asset_datas = [(_assets_dir, 'assets')] if os.path.isdir(_assets_dir) else []

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=_ffmpeg_binaries,
    datas=_asset_datas,
    hiddenimports=[
        'PySide6.QtSvg',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='싹싹김치 캡처',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='싹싹김치 캡처',
)
