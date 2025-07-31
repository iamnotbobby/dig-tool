import PyInstaller.__main__
import os
import tempfile
from pathlib import Path

def get_version_info():
    pyproject_path = Path("pyproject.toml")
    version = "1.5.4"
    version_beta = None
    
    if pyproject_path.exists():
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('version = '):
                version = line.split('=')[1].strip().strip('"\'')
                break
        
        in_dig_tool_section = False
        for line in content.split('\n'):
            line = line.strip()
            if line == '[tool.dig-tool]':
                in_dig_tool_section = True
                continue
            elif line.startswith('[') and in_dig_tool_section:
                break
            elif in_dig_tool_section and line.startswith('version-beta = '):
                beta_value = line.split('=')[1].strip()
                if beta_value and beta_value not in ['null', 'none', '']:
                    version_beta = beta_value
                break
    
    return version, version_beta

version, version_beta = get_version_info()
print(f"Detected version: {version}")
print(f"Detected beta: {version_beta}")

temp_dir = tempfile.gettempdir()
version_info_file = os.path.join(temp_dir, 'version_info.txt')

with open(version_info_file, 'w') as f:
    f.write(f"{version}\n{version_beta if version_beta else 'none'}")

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
    f'--add-data={version_info_file};.',
    '--exclude-module=scripts',
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

try:
    os.remove(version_info_file)
except Exception:
    pass