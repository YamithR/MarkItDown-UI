# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the headless JSONL server binary (onedir).
# Output: backend/dist/backend/  -> electron-builder copies it to
#                                   resources/backend/ (extraResources)
# Entry: entrypoint.py           -> markitdown_ui.server.run_server()
#
# Build:
#   python -m PyInstaller --noconfirm --clean backend/backend.spec
# (SPECPATH makes dist/build land in backend/, paths are CWD-independent)
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

ROOT = os.path.dirname(SPECPATH)  # repo root (spec sits in backend/)

# magika embeds its ML models + content-type config as package data;
# PyInstaller does NOT pick these up automatically -> collect them.
magika_datas = collect_data_files('magika')
magika_hiddenimports = collect_submodules('magika')
markitdown_datas = collect_data_files('markitdown')

# easyocr/torch are only bundled when present in the build environment
# (CI installs them when bundle_easyocr != 'false'); dev machines skip them.
try:
    import easyocr  # noqa: F401
    easyocr_datas = collect_data_files('easyocr')
    easyocr_hiddenimports = ['easyocr', 'torch', 'torchvision'] + \
        collect_submodules('easyocr')
except Exception:
    easyocr_datas = []
    easyocr_hiddenimports = []

a = Analysis(
    [os.path.join(ROOT, 'entrypoint.py')],
    pathex=[SPECPATH],
    binaries=[],
    datas=magika_datas + markitdown_datas + easyocr_datas,
    hiddenimports=[
        'markitdown',
        'markitdown_ui',
        'markitdown_ui.cli',
        'markitdown_ui.server',
        'markitdown_ui.ocr_backends',
        'markitdown_ui.ocr_manager',
        'fitz',
        'PIL',
        'pytesseract',
        'onnxruntime',
    ] + magika_hiddenimports + easyocr_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'pytest',
        'numpy.testing',
        'torch.testing',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='markitdown-ui-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # server speaks JSONL on stdin/stdout
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='backend',
)