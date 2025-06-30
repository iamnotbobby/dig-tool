import PyInstaller.__main__

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
    '--add-data=assets/AutoHotkey64.exe;assets',
    '--distpath=dist',
    '--workpath=build',
    '--specpath=.',
    '--collect-all=autoit',
    '--add-binary=assets/AutoHotkey64.exe;assets',
    '--clean',
    '--hidden-import=ahk'
])