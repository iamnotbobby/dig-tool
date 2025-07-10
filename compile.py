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
    '--distpath=dist',
    '--workpath=build',
    '--specpath=.',
    '--collect-all=autoit',
    '--clean',
])