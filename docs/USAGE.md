# 🥄 Dig Tool — Usage Guide

## 🔧 Table of Contents

<!-- Run with: npx doctoc --maxlevel 3 USAGE.md -->

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [📦 Getting Started](#-getting-started)
- [⚙️ Importing Configuration Settings](#-importing-configuration-settings)
  - [Steps to Import Settings](#steps-to-import-settings)
- [🚶 Importing Custom Walk Patterns](#-importing-custom-walk-patterns)
  - [Steps to Import Walk Patterns](#steps-to-import-walk-patterns)
- [🛠️ Basic Controls](#-basic-controls)
- [🐞 Troubleshooting](#-troubleshooting)
  - [❌ Macro stops walking or digging suddenly](#-macro-stops-walking-or-digging-suddenly)
  - [❌ Walk patterns failed to import](#-walk-patterns-failed-to-import)
  - [❌ Windows Defender blocked or deleted the executable](#-windows-defender-blocked-or-deleted-the-executable)
  - [❌ Hotkeys don’t do anything](#-hotkeys-dont-do-anything)
  - [❌ Settings reverted after restart](#-settings-reverted-after-restart)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

---

## 📦 Getting Started

1. **Launch the Macro**

   * Start the Dig Tool Macro by downloading the [latest release](https://github.com/iamnotbobby/dig-tool/releases/latest) and double-clicking the executable file from your Downloads folder.

> [!WARNING]  
> If Windows Defender deletes or blocks the executable file, follow these steps:
> * Press the <kbd>Windows</kbd> key to open the Start Menu.
> * Type <kbd>Win</kbd> + <kbd>R</kbd> to open the **Run** dialog.
> * Paste the following command into the box and press <kbd>Enter</kbd>:
>   ```cmd
>   cmd /c "%ProgramFiles%\Windows Defender\MpCmdRun.exe" -SignatureUpdate
>   ```
>
> This will update Defender's virus definitions. After it's done, try downloading the macro again.

2. **Select an area**

   - Click the `Select Area` button on the main GUI.  
   ![Select Area Button](/assets/select_area_button.png)

   - Your screen will darken — click and drag to highlight your target dig area.  
   ![Select Area Example](/assets/selection_area.png)

> [!IMPORTANT]
> You must select the bottom half of the minigame bar.
> Selecting the wrong region may cause the macro to miss hits or fail to detect movement properly.

3. **Start Automation**

   - Press <kbd>F1</kbd> or your assigned hotkey to start the macro.
   - You can pause or stop at any time by pressing the hotkey again.
  
---

## ⚙️ Importing Configuration Settings

Settings control your macro behavior such as detection, behavior, input delay, and sweet spot area.

### Steps to Import Settings

1. Open the `Settings` dropdown menu at the bottom of the main GUI.  
![Settings Dropdown](/assets/settings_dropdown.png)
2. Click `Load Settings`.  
![Load Settings Button](/assets/load_settings_button.png)
3. Choose a `.json` configuration file.  
![Load File Dialog](/assets/load_filedialog.png)

---

## 🚶 Importing Custom Walk Patterns

You can import `.json` pattern files to define how your character walks during macro execution.

### Steps to Import Walk Patterns

1. Open the `Behavior` dropdown menu on the main GUI.  
![Behavior Dropdown](/assets/behavior_dropdown.png)
2. Open the `Auto-Walk Settings` dropdown menu under that.  
![Auto-Walk Settings Dropdown](/assets/autowalk_dropdown.png)
3. Click `Manage Custom Patterns`.  
![Manage Custom Patterns Button](/assets/manage_patterns_button.png)
4. In the window that appears, click `Import Pattern`.  
![Import Pattern](/assets/import_pattern_button.png)
5. Choose a `.json` configuration file.  
![Load File Dialog](/assets/load_filedialog.png)

---

## 🛠️ Basic Controls

| Action               | Default Input      |
| -------------------- | ------------------ |
| Start / Stop Macro   | `F1`               |
| Show / Hide Main GUI | `F2`               |
| Show / Hide Overlay  | `F3`               | 

---

## 🐞 Troubleshooting

### ❌ Macro stops walking or digging suddenly

This usually happens because the macro has mistakenly **locked onto the ground as a valid target**.

#### ✅ How to confirm:

1. Press <kbd>F3</kbd> (or your assigned hotkey) to open the **overlay**.
2. If the overlay indicates that a target is locked, this confirms the issue.

#### 🛠️ How to fix:

* Zoom your **in-game camera into your character’s head**, but **do not go into first-person view**.
* This is usually enough to prevent the macro from detecting the ground as a valid target.

### ❌ Walk patterns failed to import

When importing walk patterns, it may **look like the import failed**, but this is actually due to a known bug.

#### 🧩 What’s happening:

* After you select and open a `.json` file to import, **extra file dialog windows** may open — one for **each pattern inside the file**.
* An error message may appear at the end.

#### ✅ What to do:

1. Simply **click `Cancel`** on each dialog that pops up.
2. After the last one, **ignore the final error message**.
3. Press the `Refresh List` button.
4. The imported walk patterns should now appear as expected.

### ❌ Windows Defender blocked or deleted the executable

Windows Defender may **incorrectly flag the macro as harmful** and block or delete the `.exe` file immediately after download.

#### 🛠️ How to fix:

1. Press the <kbd>Windows</kbd> key to open the **Start Menu**.
2. Type <kbd>Win</kbd> + <kbd>R</kbd> to open the **Run** dialog.
3. Paste the following command into the box and press <kbd>Enter</kbd>:

   ```cmd
   cmd /c "%ProgramFiles%\Windows Defender\MpCmdRun.exe" -SignatureUpdate
   ```
4. Wait for Windows Defender to finish updating its virus definitions.
5. Re-download the macro from the [latest release](https://github.com/iamnotbobby/dig-tool/releases/latest) and try running it again.

> [!IMPORTANT]
> This issue is a **false positive**. The macro does not contain any malicious code.

### ❌ Hotkeys don’t do anything

Sometimes the macro’s hotkeys (e.g., <kbd>F1</kbd>, <kbd>F2</kbd>, <kbd>F3</kbd>) may stop responding or appear to do nothing.

#### ✅ How to fix:

* Simply **close and restart the program**.
  This usually restores full hotkey functionality.

### ❌ Settings reverted after restart

Settings **do not persist automatically** between sessions.

#### ✅ What to do:

* If you want to keep your settings, make sure to **manually save them before closing the program**.
* Alternatively, you can **load your saved settings file** each time you start the macro.

