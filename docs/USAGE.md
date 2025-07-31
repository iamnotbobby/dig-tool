> [!NOTE]  
> This guide is meant for versions v1.5.4 and higher. Some parts of the guide may be applicable on earlier versions.

# 🥄 Dig Tool — Usage Guide

## Table of Contents

<!-- Run with: npx doctoc --maxlevel 3 docs/USAGE.md -->

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [🚀 Getting Started](#-getting-started)
- [🎮 Basic Controls](#-basic-controls)
- [📚 How To](#-how-to)
  - [How to import configuration settings](#how-to-import-configuration-settings)
  - [How to import custom walk patterns](#how-to-import-custom-walk-patterns)
  - [How to create your own custom walk pattern](#how-to-create-your-own-custom-walk-pattern)
  - [How to set up Discord notifications](#how-to-set-up-discord-notifications)
  - [How to set up money detection](#how-to-set-up-money-detection)
  - [How to set up item detection](#how-to-set-up-item-detection)
  - [How to use color picker detection](#how-to-use-color-picker-detection)
- [⚙️ Settings Overview](#️-settings-overview)
- [🔧 Troubleshooting](#-troubleshooting)
  - [❌ Dig Tool fails to hit strong hits consistently](#-dig-tool-fails-to-hit-strong-hits-consistently)
  - [❌ Dig Tool does not detect anything](#-dig-tool-does-not-detect-anything)
  - [❌ Dig Tool stops walking during auto-walk](#-dig-tool-stops-walking-during-auto-walk)
  - [❌ Auto-sell does not open the inventory](#-auto-sell-does-not-open-the-inventory)
  - [❌ Auto-sell does not use UI navigation correctly](#-auto-sell-does-not-use-ui-navigation-correctly)
  - [❌ Windows Defender blocked or deleted the executable](#-windows-defender-blocked-or-deleted-the-executable)
- [💬 Get Help & Report Bugs](#-get-help--report-bugs)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

---

## 🚀 Getting Started

1. **Launch Dig Tool**

   * Start Dig Tool by downloading the [latest release](https://github.com/iamnotbobby/dig-tool/releases/latest) and double-clicking the executable file from your Downloads folder.

> [!WARNING]  
> If Windows Defender deletes or blocks the executable file, follow these steps:
> * Press <kbd>Win</kbd> + <kbd>R</kbd> to open the **Run** dialog.
> * Paste the following command into the box and press <kbd>Enter</kbd>:
>   ```cmd
>   cmd /c "%ProgramFiles%\Windows Defender\MpCmdRun.exe" -SignatureUpdate
>   ```
>
> This will update Defender's virus definitions. After it's done, try downloading Dig Tool again.

2. **Select an area**

   - Click the `Select Area` button on the main GUI.  
   ![Select Area Button](/assets/docs/select_area_button.png)

   - Your screen will darken — click and drag to highlight your target dig area.  
   ![Select Area Example](/assets/docs/selection_area.png)

> [!IMPORTANT]
> You must select the bottom half of the minigame bar.
> Selecting the wrong region may cause Dig Tool to miss hits or fail to detect movement properly.

3. **Disable Notifications Viewport in Game Settings**

   Before starting Dig Tool, you'll need to make sure `Notifications Viewport` is disabled in the in-game settings menu. 

   - Open your in-game settings menu.  
   ![Game Settings Button](/assets/docs/game_settings_button.png)
   - Look for the **"Notifications Viewport"** setting.  
   ![Notifications Viewport Slider](/assets/docs/notifications_viewport_slider.png)
   - Make sure it is **disabled** (the slider should be to the **left** and appear **grey**).  
   ![Notifications Viewport Example](/assets/docs/notifications_viewport_disabled.png)

> \[!IMPORTANT]
> Leaving this setting enabled may cause Dig Tool to miss hits or improperly detect the zone.

4. **Start Automation**

   - Press <kbd>F1</kbd> or your assigned hotkey to start Dig Tool.
   - You can pause or stop at any time by pressing the hotkey again.
  
---

## 🎮 Basic Controls

| Action               | Default Input      |
| -------------------- | ------------------ |
| Start / Stop Dig Tool| `F1`               |
| Show / Hide Main GUI | `F2`               |
| Show / Hide Overlay  | `F3`               | 
| Show / Hide Auto-Walk Overlay  | `F4`               | 

---

## 📚 How To

### How to import configuration settings

Settings control your Dig Tool behavior such as detection, behavior, input delay, and sweet spot area. You can find settings within the Discord.

#### Steps:

1. Open the `Settings` dropdown menu at the bottom of the main GUI.  
   ![Settings Dropdown](/assets/docs/settings_dropdown.png)
2. Click `Load Settings`.  
   ![Load Settings Button](/assets/docs/load_settings_button.png)
3. Choose a `.json` configuration file.  
   ![Load File Dialog](/assets/docs/load_filedialog.png)

Alternatively, you can also just drag and drop the `.json` configuration file onto Dig Tool.

If you want other community-made settings join the [Discord](https://discord.com/invite/mxE7dzXMGf).

### How to import custom walk patterns

You can import `.json` pattern files to define how your character walks during Dig Tool execution.

#### Steps:

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

If you want other community-made patterns join the [Discord](https://discord.com/invite/mxE7dzXMGf).

### How to create your own custom walk pattern

You can create and record your own custom walk patterns to define exactly how your character moves during auto-walk.

#### Steps:

1. Navigate to `Auto-Walk > Manage Custom Patterns > Record New Pattern`.  
   ![Custom Walk Pattern Tab Example](/assets/docs/custom_walk_pattern_tab_example.png)

2. **Start recording:**
   
   - Press `Start` to begin recording.
   - Use WASD keys to move your character as desired. Make sure you're in-game if you want to see how you're moving.
  - You can create key combinations by pressing multiple keys at the same time.

3. **Enable additional keys (optional):**
   
   - Click `Allow custom keys (beyond WASD)` to use additional keys like Shift Lock and other controls.

4. **Edit recorded steps:**
   
   - Click on individual steps to edit them.
   - Disable certain actions like clicking.
   - Set custom key hold durations.
   - Create manual combinations using formats like `A+W` for simultaneous key presses.  
     ![Custom Walk Pattern Edit](/assets/docs/custom_walk_pattern_edit.png)

5. **Preview and save:**
   
   - When finished recording, click `Stop`.
   - Click `Preview Pattern` to test your recorded pattern.
   - Enter a pattern name and click `Save Pattern`.

6. **Use your new pattern:**
   
   - Return to `Available Patterns` and you will see your new custom pattern listed.  
     ![Custom Walk Pattern New Pattern](/assets/docs/custom_walk_pattern_new_pattern.png)

### How to set up Discord notifications

Configure Dig Tool to send notifications to your Discord server via a webhook.

#### Steps:

1. **Create a Discord webhook:**
   
   - Open your Discord server and go to a channel and view its settings.  
     ![Discord Channel Settings Example](/assets/docs/discord_channel_settings.png)
   - Go to `Integrations > Webhooks > New Webhook`.
   - You will see a new webhook appear and you will need to grab the webhook URL.  
     ![Discord Webhook URL Example](/assets/docs/discord_webhook_url.png)

2. **Configure in Dig Tool:**
   
   - Under `Discord` section, enable Discord.
   - Paste your webhook URL in the Discord webhook URL field.
   - Additionally, if you wish to provide a live stats message link on subsequent messages, you can also provide the server ID. See [Discord's guide](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID) for details.
   - The same applies for mentions on Discord notifications.

3. **Test the connection:**
   
   - Click "Test Discord Notification" to verify it's working.

### How to set up money detection

Enable automatic money tracking.

#### Steps:

1. **Enable money detection:**
   
   - Under `Discord > Money Detection` section, enable `Money Detection`.
   - Select the area where your money counter appears in-game.
   - Ensure when you're selecting that you're selecting a rectangle of the area where your money is. There must be enough space when it may extend (for example, $100,000 to $1,000,000).

   ![Money Area Setup Example](/assets/docs/settings/set_money_area_example.png)

2. **Calibrate OCR:**
   
   - Test by clicking `Test Money OCR` to ensure it works. You will see it appear in the status box.  
     ![Test Money OCR Example](/assets/docs/settings/test_money_ocr_example.png)
   - Decrease the color tolerance if nothing appears.

### How to set up item detection

Track rare items and get notified when you dig up valuable loot.

#### Steps:

1. **Enable item detection:**
   
   - Under `Discord > Item Detection` section, enable `Item Detection`.
   - Select the area of where dig notifications appear in-game.
   - Ensure when you're selecting that you're selecting a wide rectangle of where item names pop up. Make sure there's enough space for bigger text pop ups like legendaries or divines.

   ![Item Detection Example](/assets/docs/settings/item_detection_example.png)

2. **Test detection:**
   
   - Test by clicking `Test Item OCR` to ensure it works. You will see it appear in the status box.  
     ![Test Item OCR](/assets/docs/settings/test_item_ocr_example.png)

### How to use color picker detection

Use color picker detection for more precise zone detection.

#### Steps:

1. **Enable color picker detection:**
   
   - Under `Detection > Color Picker Detection (Simple Method)`, enable color picker detection.

2. **Sample Area:**
   
   - Click the sample area button to begin color sampling.

3. **Select an area of the zone:**
   
   - Select an area of the zone that you want to pick by dragging and holding your mouse.  
     ![Color Picker Sample Area](/assets/docs/color_picker_sample_area.png)

4. **Adjust tolerance if needed:**
   
   - Done! Adjust color tolerance accordingly if the detection is too sensitive or not sensitive enough.

---

## ⚙️ Settings Overview

For a comprehensive guide to all available settings and their detailed explanations, please refer to the [Settings Documentation](/docs/SETTINGS.md).

---

## 🔧 Troubleshooting

### ❌ Dig Tool fails to hit strong hits consistently

If your Dig Tool **fails to get strong hits**, or **only gets them randomly**, this is usually due to a **visual detection issue** or **hardware performance limitation**.

#### How to troubleshoot:

1. Open Dig Tool's main GUI and click the `Show Preview` button.
2. This displays what Dig Tool sees during gameplay.

#### What to check:

* **First**, make sure **Notifications Viewport** is **disabled** in the game’s settings:

  * Open the **in-game settings menu**.  
    ![Game Settings Button](/assets/docs/game_settings_button.png)

  * Find the **"Notifications Viewport"** setting.  
    ![Notifications Viewport Slider](/assets/docs/notifications_viewport_slider.png)

  * The slider should be to the **left** and appear **grey**.  
    ![Notifications Viewport Example](/assets/docs/notifications_viewport_disabled.png)

* If Notifications Viewport is **enabled**, disable it and test again.

2. **Check the preview:**

   - Open Dig Tool's main GUI and click the `Show Preview` button.
   - This displays what Dig Tool sees during gameplay.

   **What to look for:**

   - **Is the bounding box (green box with yellow box) shown?**

     - **Bounding box is on top of the minigame zone:**  
       ![Bounding Box Example](/assets/docs/bounding_box.png)  
       If so, you are doing everything correctly. This is a settings issue and you will need to update accordingly.
     
     - **Bounding box is shown elsewhere (not the minigame):**  
       ![Bounding Box Example 2](/assets/docs/bounding_box_incorrect.png)  
       This can be caused by Dig Tool believing that an area of the minigame itself is the zone. Under `Detection`, you will need to reduce `Zone Max Width %` and increase `Zone Min Width`. Adjust these values until it's perfect.

     - **Bounding box is not shown:**  
       Refer to "Dig Tool does not detect anything" section below.

   - **Preview is black and shows no parts of the game:**  
     This is a critical issue with Dig Tool. Report this to the developer.

3. **Check your FPS:**

   - **Running below 60 FPS:**
     
     You will need to adjust settings to work with your FPS:
     - `Behavior > Enable Prediction`: You may want to disable prediction. The lower amount of FPS you get, the less data Dig Tool can read.
     - `Behavior > Prediction Settings > Game FPS`: Change this to the average FPS you get.
     - `Behavior > Target Width %`: You may want to increase this so it's less strict.
     - `Behavior > Enable Velocity-Based Width`: This can help with prediction accuracy by making the target width % higher based on the line's velocity.

     If none of these settings work, you may want to try and increase your FPS through various ways such as using a custom bootstrapper like Voidstrap which applies optimizations to achieve more FPS.

   - **FPS does not go above a certain number:**
     
     Your FPS is capped. In **Roblox settings**, set **`Maximum Frame Rate` to 240**.

4. **Review your settings:**

   Your settings can cause Dig Tool to perform poorly. Review [settings](/docs/SETTINGS.md) for an overview on all of the settings.

### ❌ Dig Tool does not detect anything

This is an issue related to the detection method you're using.

#### How to fix:

1. **Check your detection method:**
   
   - Click `Show Debug` and view the window to see the detection method you're currently using.
   - By default it is Saturation Threshold.

2. **Adjust the Saturation Threshold:**
   
   - You will need to adjust the `Saturation Threshold` setting under `Detection` section.
   - Usually, `0.5` works for most but for others it may not due to your color settings such as HDR.

3. **Try a different detection method:**
   
   - If adjusting the threshold doesn't work, you will need to adjust your color settings or use a different detection method such as Otsu's Detection.

### ❌ Dig Tool stops walking during auto-walk

This usually happens for several reasons.

#### How to fix:

1. **Check if Dig Tool is running:**
   
   - Make sure you have Dig Tool running by clicking the start button.

2. **Check if auto-walk is enabled:**
   
   - Under `Auto-Walk` section, make sure it is enabled.

3. **Check for inventory issues:**
   
   - Your in-game inventory may be left open due to auto-sell.
   - Under `Auto-Walk`, go to `Auto-Sell Settings` and enable `Post-Sell Engagement Timeout` with a reasonable timeout (e.g., 120).

4. **Check shovel management:**
   
   - If you can move around in-game with your camera, but moving with WASD does not work and you cannot dig:
   - Under `Auto-Walk` section, go to `Shovel Management` and enable `Auto-Shovel`.

### ❌ Auto-sell does not open the inventory

This happens when using a different keyboard layout.

#### How to fix:

- If you are using a different keyboard layout (not QWERTY), you will need to change the inventory key under `Auto-Walk > Auto-Sell Settings > Inventory Key`.

### ❌ Auto-sell does not use UI navigation correctly

This happens because UI navigation sequences are different for every user.

#### How to fix:

1. **Change the UI navigation sequence:**
   
   - You will need to change the UI navigation sequence under `Auto-Walk > Auto-Sell Settings > UI Navigation Sequence`.
   - Depending on your ROBLOX, this sequence is **different** for everybody and you will need to do some testing on your own.
   - Navigate through UIs by using your keyboard's arrow keys.
   - Once you find a sequence, enter it as `down,up,enter` where enter is the last step of pressing the sell inventory button.

2. **Check the UI navigation key:**
   
   - If auto-sell does not enable UI navigation at all (as indicated by a ROBLOX notification in the bottom right of the screen) and you're not using QWERTY, you will need to change the UI navigation key at `Auto-Walk > Auto-Sell Settings > UI Navigation Key`.

### ❌ Windows Defender blocked or deleted the executable

Windows Defender may **incorrectly flag Dig Tool as harmful** and block or delete the `.exe` file immediately after download.

#### How to fix:

1. Press <kbd>Win</kbd> + <kbd>R</kbd> to open the **Run** dialog.
2. Paste the following command into the box and press <kbd>Enter</kbd>:

   ```cmd
   cmd /c "%ProgramFiles%\Windows Defender\MpCmdRun.exe" -SignatureUpdate
   ```
3. Wait for Windows Defender to finish updating its virus definitions.
4. Re-download Dig Tool from the [latest release](https://github.com/iamnotbobby/dig-tool/releases/latest) and try running it again.

> [!IMPORTANT]
> This issue is a **false positive**. Dig Tool does not contain any malicious code.

---

## 💬 Get Help & Report Bugs

If you're experiencing issues that aren't covered in the troubleshooting section, or if you need additional help with Dig Tool, this section can help you.

### Reporting Bugs

Found a bug? Help me improve Dig Tool by reporting it:

1. **Join our Discord server:** [https://discord.com/invite/mxE7dzXMGf](https://discord.com/invite/mxE7dzXMGf)
2. **Provide detailed information:**
   - What were you trying to do when the bug occurred?
   - What actually happened vs. what you expected?
   - Steps to reproduce the issue
   - Your Dig Tool version
   - Screenshots or videos
   - Under `Debug > Show Debug Console` this will show debug messages. Include this.
   Note: You will need to send me a message on Discord rather than in the official channels.

### Getting Additional Help

Need help setting up Dig Tool or have questions about specific features?

- **Join our Discord community:** [https://discord.com/invite/mxE7dzXMGf](https://discord.com/invite/mxE7dzXMGf)
- **Browse community resources:**
  - Shared configuration settings
  - Custom walk patterns
- **Get support from the community via a dedicated support channel**

### Before Asking for Help

To get the fastest and most accurate help, please:

1. **Check this documentation first** - especially the [Troubleshooting](#troubleshooting) section
2. **Review the [Settings Documentation](/docs/SETTINGS.md)** for detailed explanations on settings
3. **Try the basic troubleshooting steps:**
   - Restart Dig Tool
   - Check that your area selection is correct
   - Verify that Notifications Viewport is disabled in-game
   - Test with default settings
