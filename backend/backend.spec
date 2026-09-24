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

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

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
    # torchvision 0.29 renamed its C extension to _C_stable.so/image_stable.so
    # (hook-torchvision still references the old torchvision._C name, which is
    # a no-op). Without these .so the ops (nms, etc.) are never registered and
    # runtime fails with "operator torchvision::nms does not exist".
    torchvision_binaries = collect_dynamic_libs('torchvision')
    torchvision_hiddenimports = ['torchvision._C_stable', 'torchvision.image_stable']
except Exception:
    easyocr_datas = []
    easyocr_hiddenimports = []
    torchvision_binaries = []
    torchvision_hiddenimports = []

a = Analysis(
    [os.path.join(ROOT, 'entrypoint.py')],
    pathex=[SPECPATH],
    binaries=torchvision_binaries,
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
    ] + magika_hiddenimports + easyocr_hiddenimports + torchvision_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # NOTE: do NOT exclude torch.distributed.* or torch.testing here.
    #   torch/_jit_internal.py eagerly imports torch.distributed.rpc, and
    #   torch/distributed/__init__.py eagerly imports remote_device, so
    #   excluding them breaks plain `import torch`. torch/autograd/gradcheck.py
    #   imports torch.testing, which is pulled in transitively via
    #   torch.distributed.rpc -> server_process_global_profiler -> autograd.
    #   The original GradBucket/RpcBackendOptions "generic_type: cannot
    #   initialize type" crash was NOT caused by these modules but by the
    #   embedded-EXE mode: the bootloader re-extracts the embedded binaries on
    #   every start, loading libtorch_python.so twice (two DSO instances ->
    #   double pybind11 registration). Fixed with exclude_binaries=True below.
    #   numpy.testing must also stay: scipy/_external/array_api_compat does
    #   clone_module(np) on import, which pulls numpy.testing at runtime.
    excludes=[
        'matplotlib',
        'pytest',
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