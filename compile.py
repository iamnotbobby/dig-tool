import PyInstaller.__main__

ONEFILE_MODE = True  # Set to True for single executable, False for directory mode

hiddenimports = [
    'winrt.windows.foundation',
    'winrt.windows.media.ocr',
    'winrt.windows.graphics.imaging',
    'winrt.windows.storage.streams',
]

hidden_imports_args = []
for imp in hiddenimports:
    hidden_imports_args.extend(['--hidden-import', imp])

base_args = [
    'main.py',
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
]

if ONEFILE_MODE:
    base_args.insert(1, '--onefile')
    print("Building in ONEFILE mode (single executable)")
else:
    base_args.insert(1, '--onedir')
    print("Building in ONEDIR mode (multiple files in directory)")

all_args = base_args + hidden_imports_args

print(f"PyInstaller arguments: {' '.join(all_args)}")
PyInstaller.__main__.run(all_args)