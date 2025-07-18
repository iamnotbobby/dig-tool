# 🥄 Dig Tool — Usage Guide

## Table of Contents

<!-- Run with: npx doctoc --maxlevel 3 docs/USAGE.md -->

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [Getting Started](#getting-started)
- [Importing Configuration Settings](#importing-configuration-settings)
  - [Steps to Import Settings](#steps-to-import-settings)
- [Importing Custom Walk Patterns](#importing-custom-walk-patterns)
  - [Steps to Import Walk Patterns](#steps-to-import-walk-patterns)
- [Basic Controls](#basic-controls)
- [Troubleshooting](#troubleshooting)
  - [❌ Macro stops walking or digging suddenly](#-macro-stops-walking-or-digging-suddenly)
  - [❌ Macro fails to hit strong hits consistently](#-macro-fails-to-hit-strong-hits-consistently)
  - [❌ Windows Defender blocked or deleted the executable](#-windows-defender-blocked-or-deleted-the-executable)
  - [❌ Hotkeys don’t do anything](#-hotkeys-dont-do-anything)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

---

## Getting Started

1. **Launch the Macro**

   * Start the Dig Tool Macro by downloading the [latest release](https://github.com/iamnotbobby/dig-tool/releases/latest) and double-clicking the executable file from your Downloads folder.

> [!WARNING]  
> If Windows Defender deletes or blocks the executable file, follow these steps:
> * Press <kbd>Win</kbd> + <kbd>R</kbd> to open the **Run** dialog.
> * Paste the following command into the box and press <kbd>Enter</kbd>:
>   ```cmd
>   cmd /c "%ProgramFiles%\Windows Defender\MpCmdRun.exe" -SignatureUpdate
>   ```
>
> This will update Defender's virus definitions. After it's done, try downloading the macro again.

2. **Select an area**

   - Click the `Select Area` button on the main GUI.  
   ![Select Area Button](/assets/docs/select_area_button.png)

   - Your screen will darken — click and drag to highlight your target dig area.  
   ![Select Area Example](/assets/docs/selection_area.png)

> [!IMPORTANT]
> You must select the bottom half of the minigame bar.
> Selecting the wrong region may cause the macro to miss hits or fail to detect movement properly.

3. **Disable Notifications Viewport in Game Settings**

   Before starting the macro, you'll need to make sure `Notifications Viewport` is disabled in the in-game settings menu.

   - Open your in-game settings menu.  
   ![Game Settings Button](/assets/docs/game_settings_button.png)
   - Look for the **"Notifications Viewport"** setting.  
   ![Notifications Viewport Slider](/assets/docs/notifications_viewport_slider.png)
   - Make sure it is **disabled** (the slider should be to the **left** and appear **grey**).  
   ![Notifications Viewport Example](/assets/docs/notifications_viewport_disabled.png)

> \[!IMPORTANT]
> Leaving this setting enabled may cause the macro to miss hits or improperly detect the zone.

4. **Start Automation**

   - Press <kbd>F1</kbd> or your assigned hotkey to start the macro.
   - You can pause or stop at any time by pressing the hotkey again.
  
---

## Importing Configuration Settings

Settings control your macro behavior such as detection, behavior, input delay, and sweet spot area.

### Steps to Import Settings

1. Open the `Settings` dropdown menu at the bottom of the main GUI.  
![Settings Dropdown](/assets/docs/settings_dropdown.png)
2. Click `Load Settings`.  
![Load Settings Button](/assets/docs/load_settings_button.png)
3. Choose a `.json` configuration file.  
![Load File Dialog](/assets/docs/load_filedialog.png)

---

## Importing Custom Walk Patterns

You can import `.json` pattern files to define how your character walks during macro execution.

### Steps to Import Walk Patterns

1. Open the `Behavior` dropdown menu on the main GUI.  
![Behavior Dropdown](/assets/docs/behavior_dropdown.png)
2. Open the `Auto-Walk Settings` dropdown menu under that.  
![Auto-Walk Settings Dropdown](/assets/docs/autowalk_dropdown.png)
3. Click `Manage Custom Patterns`.  
![Manage Custom Patterns Button](/assets/docs/manage_patterns_button.png)
4. In the window that appears, click `Import Pattern`.  
![Import Pattern](/assets/docs/import_pattern_button.png)
5. Choose a `.json` configuration file.  
![Load File Dialog](/assets/docs/load_filedialog.png)

---

## Basic Controls

| Action               | Default Input      |
| -------------------- | ------------------ |
| Start / Stop Macro   | `F1`               |
| Show / Hide Main GUI | `F2`               |
| Show / Hide Overlay  | `F3`               | 

---

## Troubleshooting

### ❌ Macro stops walking or digging suddenly

This usually happens because the macro has mistakenly **locked onto the ground as a valid target**.

#### How to confirm:

1. Press <kbd>F3</kbd> (or your assigned hotkey) to open the **overlay**.
2. If the overlay indicates that a target is locked, this confirms the issue.

#### How to fix:

* Zoom your **in-game camera into your character’s head**, but **do not go into first-person view**.
* This is usually enough to prevent the macro from detecting the ground as a valid target.

### ❌ Macro fails to hit strong hits consistently

If your macro walks correctly but **fails to get strong hits**, or **only gets them randomly**, this is usually due to a **visual detection issue** or **hardware performance limitation**.

#### How to troubleshoot:

1. Open the macro’s main GUI and click the `Show Preview` button.
2. This displays what the macro sees during gameplay.

#### What to check:

* **First**, make sure **Notifications Viewport** is **disabled** in the game’s settings:

  * Open the **in-game settings menu**.  
    ![Game Settings Button](/assets/docs/game_settings_button.png)

  * Find the **"Notifications Viewport"** setting.  
    ![Notifications Viewport Slider](/assets/docs/notifications_viewport_slider.png)

  * The slider should be to the **left** and appear **grey**.  
    ![Notifications Viewport Example](/assets/docs/notifications_viewport_disabled.png)

* If Notifications Viewport is **enabled**, disable it and test again.

* If Notifications Viewport is **already disabled**, and you're still having issues, then:

  * **Open the macro’s settings** and check if **Prediction** is turned on by navigating to `Behavior Settings` > `Prediction Settings`.
    * Optionally press <kbd>F3</kbd> or the overlay hotkey to show the overlay. An indicator will appear as `PRED: ON` or `PRED: OFF`.
  * If Prediction is on, **turn it off** and test again, as it can interfere with accuracy.

* If both Notifications Viewport is disabled **and** Prediction is off, but you're still having issues:

  * Check the preview:

    * If the preview shows the **entire black area as the bounding box** instead of the dig zone:

      * This is a **known bug** with no current fix.
      * The macro cannot locate the sweet spot in this case.

    * If the bounding box **is correct** and follows the dig zone/sweet spot:

      * Make sure your **FPS is uncapped** in Roblox.
      * In **Roblox settings**, set **`Maximum Frame Rate` to 240**.
      * Try to reach **at least 150 FPS**, and ideally **200+ FPS**.

#### Final step:

* If your FPS is already high but strong hits still fail, your **CPU may be too slow** to keep up with the visual processing.

  * Consider upgrading to a **faster CPU** if possible.

### ❌ Windows Defender blocked or deleted the executable

Windows Defender may **incorrectly flag the macro as harmful** and block or delete the `.exe` file immediately after download.

#### How to fix:

1. Press <kbd>Win</kbd> + <kbd>R</kbd> to open the **Run** dialog.
2. Paste the following command into the box and press <kbd>Enter</kbd>:

   ```cmd
   cmd /c "%ProgramFiles%\Windows Defender\MpCmdRun.exe" -SignatureUpdate
   ```
3. Wait for Windows Defender to finish updating its virus definitions.
4. Re-download the macro from the [latest release](https://github.com/iamnotbobby/dig-tool/releases/latest) and try running it again.

> [!IMPORTANT]
> This issue is a **false positive**. The macro does not contain any malicious code.

### ❌ Hotkeys don’t do anything

Sometimes the macro’s hotkeys (e.g., <kbd>F1</kbd>, <kbd>F2</kbd>, <kbd>F3</kbd>) may stop responding or appear to do nothing.

#### How to fix:

* Simply **close and restart the program**.
  This usually restores full hotkey functionality.