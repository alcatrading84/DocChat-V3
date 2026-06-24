# -*- mode: python ; coding: utf-8 -*-
"""DocChat v3 — PyInstaller spec con todos los módulos."""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Módulos ocultos (necesarios para PyInstaller)
hiddenimports = [
    # DocChat
    'docchat', 'docchat.engine', 'docchat.ui', 'docchat.lang',
    'docchat.local_model', 'docchat.ocr', 'docchat.formats',
    'docchat.web_ui', 'docchat.metrics', 'docchat.updater',
    # Dependencias
    'docx', 'pypdf', 'llama_cpp',
]
hiddenimports += collect_submodules('docchat')
hiddenimports += collect_submodules('llama_cpp')

# Datos adicionales
datas = [
    ('favicon.ico', '.'),
    ('docchat_icon.png', '.'),
]

# Excluir librerías pesadas innecesarias
excludes = [
    'matplotlib', 'scipy', 'pandas', 'PIL', 'cv2', 'torch',
    'tensorflow', 'notebook', 'ipython', 'jupyter',
]

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DocChat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['favicon.ico'],
)
