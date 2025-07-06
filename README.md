
<div align="center">
  
<h1>Dig Tool</h1>
  
</div>

![header](assets/header.jpg)

A highly configurable automation tool specifically for the ROBLOX game ["Dig"](https://www.roblox.com/games/126244816328678) where several algorithms are used in order achieve accuracy during the minigame.

> [!NOTE]
> If in any circumstances tools like these become *banned* by Dig staff, this repository and its contents will be archived.

## Installation 

### Option 1: Quick Start (Recommended)
- Download the pre-compiled executable from the releases page
- No Python installation required - just run the application

> [!WARNING]
> Antiviruses will flag the compiled executable as a virus! These are FALSE POSITIVES. Everything leading up to the compiled executable is open source.

### Option 2: Run from Source
- Download the zip unzip it and then run compile.py from terminal and run ""/Users/(YOUR USERNAME)/Desktop/dig-tool-main mac/.venv/bin/python" "/Users/(YOUR USERNAME)/Desktop/dig-tool-main mac/compile.py""
  
If you wish to also compile from source you can run: ``python -m nuitka --onefile --enable-plugin=tk-inter --include-package=ahk --include-package-data=ahk --include-package-data=jinja2 --lto=yes --windows-console-mode=disable --windows-icon-from-ico=assets/icon.ico main.py``

> [!NOTE]
> Option 1 is recommended for most users as it requires no technical setup and comes with a performance boost due to it's compilation nature. Choose Option 2 if you want to modify the code or prefer running from source.

## Usage

You just need to select an area where it is not being interfered by text or other icons. See the example picture below. 
![example](assets/example.png)
This is different for other resolutions as the UI elements in-game will be scaled differently! That also means you may have to change detection parameters like Zone Min. Width since it measures by pixels.

## Technical Overview


### How It Works

The tool captures the screen continuously and analyzes each frame to find moving lines and colored zones. When it detects a line moving toward the target area, it calculates where the line will be in the future and attempts to click precisely in the middle of the colored zone.

### Detection Process

1. **Setup**: The user selects an area on the screen, in this case, it would be the minigame's bar itself
2. **Zone Finding**: Automatically detects colored target zones within the bar. The color found is then used to "lock" the color for better tracking
3. **Line Tracking**: Continuously scans for vertical lines using edge detection
4. **Speed Calculation**: Tracks how fast and in which direction the line is moving in order to perform predictive clicking

This tool is meant to perform its detection tasks with minimal delay and minimal resource usage.

# macOS Porting Changes for DigTool

This document outlines the modifications made to the DigTool application to enable its functionality on macOS, replacing Windows-specific dependencies and addressing platform-specific behaviors.

## Summary of Key Changes

The primary goal was to replace Windows-only libraries and API calls with cross-platform alternatives, ensuring core features like screen capture, mouse control, and hotkey handling work correctly on macOS.

### 1. Dependency Replacements

The following Windows-specific libraries and their functionalities were replaced:

*   **Original (Windows-only):**
    *   `pywin32` (for `win32gui`, `win32ui`, `win32con`, `win32api`): Used for screen capture, window manipulation, and low-level input.
    *   `ahk` (AutoHotkey Python wrapper): Used for advanced automation tasks.
    *   Direct `ctypes.windll` calls: Used for Windows-specific API interactions like DPI awareness and cursor positioning.

*   **Cross-Platform Replacements:**
    *   **`mss`**: Replaced `win32gui` for efficient screen capturing.
    *   **`pynput`**: Replaced `win32api` for mouse clicks and `keyboard` (which was causing issues) for hotkey listening and keyboard control.
    *   **Tkinter's native methods**: Used for window manipulation and basic hotkey binding.

### 2. Code Modifications

#### `requirements.txt`

*   Removed `pywin32` and `ahk`.
*   Added `mss`.
*   Ensured `pynput` was listed.

#### `compile.py`

*   Removed `--collect-all=autoit` as `ahk` was no longer used.
*   Corrected `--add-data` syntax for macOS (changed `;` to `:`).
*   Added `--noconfirm` to allow overwriting existing build directories during recompilation.

#### `utils/screen_capture.py`

*   Replaced `win32gui`, `win32ui`, `win32con` imports with `mss`.
*   Rewrote the `ScreenCapture` class to use `mss` for screen grabbing, adapting the bounding box (bbox) format.

#### `utils/system_utils.py`

*   Removed all `win32gui`, `win32ui`, `win32con`, `win32api`, and `ctypes` imports related to Windows APIs.
*   Removed the `check_display_scale()` function, as it was Windows-specific.
*   Modified `send_click()` to use `pynput.mouse.Controller` for cross-platform mouse clicks.
*   Updated `get_screen_resolution()` to use `mss` for accurate screen dimensions.
*   Updated `check_dependencies()` to reflect the new package requirements (`mss`, `pynput`).
*   Removed Windows-specific window management functions (`get_window_list`, `focus_window`, `get_window_info`, `find_window_by_title`, `capture_window`).

#### `main.py`

*   Removed Windows-specific DPI awareness code.
*   Updated `start_area_selection()` to use Tkinter's `overrideredirect(True)` and `geometry()` for fullscreen overlay instead of `attributes('-fullscreen', True)` for better macOS compatibility.
*   Modified `perform_click()` to use `pynput.mouse.Controller` for setting cursor position when `use_custom_cursor` is enabled.
*   **Hotkey Handling Refactor:**
    *   Removed `pynput.keyboard.GlobalHotKeys` and `Listener` imports from `main.py` to avoid threading conflicts with macOS UI.
    *   Removed the `hotkey_listener` method and its associated thread.
    *   The `apply_keybinds()` method was refactored to use Tkinter's `root.bind()` method. This means hotkeys are now active only when the application window is in focus.
    *   Added a `_format_key_for_tkinter` helper function to correctly format key strings (e.g., "f1" to "<F1>") for Tkinter's `bind` method.
*   Added extensive `print` statements for debugging directory creation and screenshot saving.

#### `interface/components.py`

*   Removed `win32gui` and `win32con` imports.
*   Removed Windows-specific code for setting window styles in `GameOverlay`.
*   Ensured `self.overlay.attributes('-topmost', True)` is correctly set for the overlay.

## How to Run the Compiled Application

1.  **Navigate to the `dist` directory:**
    ```bash
    cd /Users/username/Desktop/dig-tool-main mac/dist
    ```
2.  **Run the application:**
    ```bash
    ./DigTool.app/Contents/MacOS/DigTool
    ```
    (You can also double-click the `DigTool.app` bundle in Finder).

## macOS Permissions Setup

For the application to function correctly (especially for screen capture, mouse control, and hotkeys), you **must** grant it the necessary permissions in macOS System Settings:

1.  Go to **System Settings** (or System Preferences on older macOS versions).
2.  Navigate to **Privacy & Security**.
3.  Click on **Screen Recording**.
4.  Click the `+` button and add `/Users/username/Desktop/dig-tool-main mac/dist/DigTool.app` to the list. Ensure its checkbox is **checked**.
5.  Go back to **Privacy & Security**.
6.  Click on **Accessibility**.
7.  Click the `+` button and add `/Users/username/Desktop/dig-tool-main mac/dist/DigTool.app` to the list. Ensure its checkbox is **checked**.

If you encounter persistent permission prompts, sometimes unchecking and re-checking the application in these lists, or even a system restart, can resolve the issue.

## Troubleshooting

*   **Clicking Misses:**
    *   Experiment with the `target_fps` in `main.py` (e.g., reduce it to 30 or 60).
    *   Adjust `sweet_spot_width_percent` and `system_latency` in the application settings.
*   **Hotkeys Not Working (or Crashing):**
    *   Ensure the application window is **in focus** for the hotkeys to work, as they are now bound to the Tkinter window.
    *   Verify `DigTool.app` has **Accessibility** permissions.
    *   If crashes persist, ensure you have the latest compiled version and that all previous `pynput.keyboard.Listener` and `GlobalHotKeys` setups have been removed from the source code.


## Footnotes

Feel free to contribute by opening a PR! For issues or questions, you can join the [discord](https://discord.com/invite/mxE7dzXMGf).
