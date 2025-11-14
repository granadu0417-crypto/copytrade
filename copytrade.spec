# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 설정 파일
바이낸스 카피트레이딩 시스템을 실행 파일로 빌드
"""

block_cipher = None

# 추가할 데이터 파일들 (소스 경로, 대상 경로)
added_files = [
    ('config.yaml', '.'),
    ('.env.example', '.'),
    ('frontend', 'frontend'),
    ('src/database/schema.sql', 'src/database'),
]

# 숨겨진 import (동적으로 import되는 모듈)
hidden_imports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'playwright',
    'playwright._impl._api_types',
    'telegram',
    'telegram.ext',
    'binance',
    'loguru',
    'yaml',
    'dotenv',
    'fastapi',
    'pydantic',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BinanceCopyTrading',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # True: 콘솔 창 표시, False: 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 파일이 있다면 경로 지정 (예: 'icon.ico')
)
