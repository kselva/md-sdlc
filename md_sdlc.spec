# -*- mode: python ; coding: utf-8 -*-
# Build: python -m PyInstaller md_sdlc.spec
#
# --onefile via Analysis+EXE(onefile=...). Bundles plugins/new/templates/*.j2
# and CONVENTIONS.md as data (read as files at runtime, invisible to static
# analysis) and declares every plugin module as a hidden import, since
# plugins/__init__.py's frozen path imports them by string name.

a = Analysis(
    ['sdlc_tool.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('plugins/new/templates', 'plugins/new/templates'),
        ('CONVENTIONS.md', '.'),
    ],
    hiddenimports=[
        'plugins.init.plugin',
        'plugins.validate.plugin',
        'plugins.backlog.plugin',
        'plugins.query.plugin',
        'plugins.new.plugin',
        'plugins.promote.plugin',
        'plugins.archive.plugin',
        'plugins.conventions.plugin',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='md_sdlc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
