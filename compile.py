import PyInstaller.__main__
import os

PyInstaller.__main__.run([
    'main.py',
    '--onefile',
    '--windowed',
    '--name=DigTool',
    '--icon=assets/icon.ico',
    '--add-data=assets;assets',
    '--add-data=ui_components.py;.',
    '--add-data=utils.py;.',
    '--add-data=settings.py;.',
    '--distpath=dist',
    '--workpath=build',
    '--specpath=.',
    '--clean'
])