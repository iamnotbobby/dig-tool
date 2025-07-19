hiddenimports = [
    'winrt.windows.foundation',
    'winrt.windows.media.ocr',
    'winrt.windows.graphics.imaging',
    'winrt.windows.storage.streams',
]

import PyInstaller.__main__

hidden_imports_args = []
for imp in hiddenimports:
    hidden_imports_args.extend(['--hidden-import', imp])

PyInstaller.__main__.run([
    'main.py',
    '--onefile',
    '--windowed',
    '--name=DigTool',
    '--icon=assets/icon.ico',
    '--add-data=assets;assets',
    '--add-data=core;core',
    '--add-data=interface;interface',
    '--add-data=utils;utils',
    '--distpath=dist',
    '--workpath=build',
    '--specpath=.',
    '--collect-all=autoit',
    '--clean',
] + hidden_imports_args)