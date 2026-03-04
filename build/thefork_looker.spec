# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None
app_dir = os.path.abspath(os.path.join(os.path.dirname(SPEC), '..', 'app'))

a = Analysis(
    [os.path.join(app_dir, 'main.py')],
    pathex=[os.path.abspath(os.path.join(os.path.dirname(SPEC), '..'))],
    binaries=[],
    datas=[
        (os.path.join(app_dir, 'assets', 'thefork_monitor.py'), os.path.join('assets')),
        (os.path.join(app_dir, 'assets', 'icon.ico'), os.path.join('assets')),
        (os.path.join(app_dir, 'assets', 'icon.png'), os.path.join('assets')),
    ],
    hiddenimports=['paramiko', 'nacl', 'bcrypt', 'cryptography'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['playwright', 'numpy', 'pandas', 'matplotlib'],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TheForkLooker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=os.path.join(app_dir, 'assets', 'icon.ico') if os.path.exists(os.path.join(app_dir, 'assets', 'icon.ico')) else None,
)
