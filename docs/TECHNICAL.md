# 🔧 Dig Tool — Technical Options Guide

## Table of Contents

<!-- Run with: npx doctoc --maxlevel 3 docs/TECHNICAL.md -->

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Overview](#overview)
- [Detection](#detection)
  - [Line Detection](#line-detection)
  - [Zone Detection](#zone-detection)
  - [Movement Detection](#movement-detection)
  - [Advanced Detection](#advanced-detection)
- [Behavior](#behavior)
  - [Prediction](#prediction)
  - [Input & Timing](#input--timing)
  - [Custom Cursor](#custom-cursor)
- [Auto-Walk](#auto-walk)
  - [Auto-Walk Settings](#auto-walk-settings)
  - [Auto-Sell](#auto-sell)
  - [Auto-Shovel](#auto-shovel)
- [Discord](#discord)
  - [General Notifications](#general-notifications)
  - [Money Detection](#money-detection)
  - [Item Detection](#item-detection)
- [Window](#window)
  - [Window Controls](#window-controls)
- [Debug](#debug)
  - [Debug & Performance](#debug--performance)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

---

## Overview

This guide explains every setting and option available in the Dig Tool. Each setting is described in simple terms to help you understand what it does and how it affects the tool's behavior.

> [!TIP]
> You can hover over any setting in the tool to see a brief tooltip explanation. This guide provides more detailed information about each option.

---

## Detection

These settings control how the tool finds and tracks the sweet spot in the digging mini-game.

### Line Detection

**Line Sensitivity (1-1000)**  
Controls how sharp the contrast must be to detect the moving line. Higher values are less sensitive to weak edges (more selective), while lower values are more sensitive to faint lines (may detect false positives). It is HIGHLY recommended to leave this at default (100) unless you know what you're doing.

**Line Detection Offset (-∞ to +∞)**  
Moves the detected line position left or right by a specific number of pixels. Positive values shift right, negative values shift left. It is recommended to adjust until it's in the middle of the line.

In the example below, you can see the red line in the middle (to see this, open "Show Preview" panel).

![Line Detection Offset Example](/assets/docs/technical/line_detection_offset_example.png)

**Line Exclusion Radius (0-∞)**  
Creates a circular "dead zone" around the detected line where target zones are ignored. This prevents the moving line from interfering with zone detection. Adjust if the tool gets confused when the line passes through valid zones (basically, the target moves with the line). 

### Zone Detection

**Zone Min Width (0-∞)**  
Sets the minimum **PIXEL** width for a valid target zone to filter out unrelated objects that might appear during the minigame.

**Max Zone Width Percent (0-200)**  
Sets the maximum width of a target zone as a **PERCENTAGE** of the capture area (0-200%, values above 100% allow detecting zones wider than the capture area).

**Min Zone Height Percent (0-100)**  
Requires target zones to span at least this **PERCENTAGE** of the capture height (0-100%) to ensure zones are tall enough to be valid dig spots. It is HIGHLY recommended to leave this at default (100%) unless you know what you're doing.

**Target Width Percent (0-100)**  
Smaller values requires more precise clicking, however, in some cases it may be too strict. Larger values are more forgiving but may be less accurate. In most cases, it is recommended to increase this until it's more consistent rather than vice versa.

In the example below, you can see the target width percent setting visualized as the yellow box that appears in the preview window.

![Target Width Percent Example](/assets/docs/technical/target_width_percent_example.png)

### Movement Detection

**Saturation Threshold (0.0-1.0)**  
Controls how colorful a pixel must be to be part of the initial zone search (0.0-1.0, higher = more colorful required). This helps filter out dull background elements. Adjust if the tool detects unrelated elements to the minigame.

In the "Show Debug" panel, you can visualize if Dig Tool can see the minigame bar correctly (the white bar overlayed ontop of a black background).

![Saturation Threshold Example](/assets/docs/technical/saturation_threshold_example.png)

> [!IMPORTANT]
> Saturation Threshold is a detection method and CANNOT be used with other detection methods (e.g., Otsu and Color Picker)!

**Zone Smoothing Factor (0.0-2.0)**  
Controls how much the target zone movement is smoothed over time. 1.0 = no smoothing (zone jumps immediately), lower values = more smoothing (zone moves gradually), higher values = less smoothing. It is HIGHLY recommended to leave this at default (1) unless you know what you're doing.

**Velocity Based Width**  
Automatically adjusts target width percent based on how fast the line is moving. When enabled, faster line movement creates a wider target width percent for easier targeting. Enable if you have trouble hitting targets when the line moves quickly.

The data that is fed into Velocity Based Width can be found in the "Show Debug" panel.

![Velocity Based Width Info](/assets/docs/technical/velocity_based_width_info.png)

**Velocity Width Multiplier (0.0-5.0)**  
Controls how much line speed affects target width percent. Higher values create more dramatic width changes based on speed, lower values create more subtle adjustments. 

**Velocity Max Factor (0-∞)**  
Sets the maximum velocity for normalization (pixels per second). Velocities above this value are treated as maximum speed. 

### Advanced Detection

**Use Otsu Detection**  
Uses automatic threshold calculation instead of manual saturation settings. Can be more adaptive to different lighting conditions but cannot be used with Color Picker Detection or Saturation Threshold. Use if saturation threshold isn't working well.

**Otsu Min Area (0-∞)**  
Minimum area (in pixels) for detected regions when using Otsu detection. This filters out tiny regions that aren't valid zones.

**Otsu Max Area (0-∞)**  
Maximum area (in pixels) for detected regions when using Otsu detection. This prevents detection of huge areas that aren't dig zones. Leave empty for no upper limit. 

**Use Color Picker Detection**  
Uses a specific color you pick to detect target zones. Enable this, then click "Pick Color from Screen" to select your target color. Very precise when you know the exact color you want to detect, but cannot be used with Otsu Detection or Saturation Threshold. Will also not work in situations where environments may change (e.g., grass turns snowy).

**Color Tolerance (1-90)**  
How close colors need to be to your picked color to be detected. Higher values allow more lenient color matching, lower values require more precise matching. 

---

## Behavior

These settings control how the tool behaves during operation.

### Prediction

**Prediction**  
Predicts where the line will be and clicks earlier to compensate for delays. Can improve accuracy on fast systems but may cause issues if prediction is wrong. Disable if you're getting inconsistent hits or weird behavior.

**Prediction Confidence Threshold (0.0-1.0)**  
How confident the prediction must be before it's used. Higher values are more conservative (only predicts when very sure), lower values are more aggressive (predicts more often).

**Target FPS (Game FPS) (1-∞)**  
Sets the target frame rate of the game for prediction calculations. This helps the prediction algorithm understand the timing of game updates. Higher FPS games allow for more precise prediction timing. Set this to match your actual in-game frame rate for best prediction accuracy.

You can view your in-game FPS by pressing ``Shift+F5`` in-game. It is recommended you try and average it out and go a bit lower rather than higher.

![Game FPS Example](/assets/docs/technical/game_fps_example.png)

### Input & Timing

**Post Click Blindness (0-∞)**  
How long to wait after clicking before scanning for new targets. This prevents multiple rapid clicks on the same spot. Higher values mean slower clicking but more stability, lower values mean faster clicking but may cause double-clicks. Ironically, Dig Tool is very fast and that's why multiple clicks can occur.

### Custom Cursor

**Use Custom Cursor**  
Uses a custom cursor position instead of auto-detection. Cannot be used with Auto-Walk. For setups where you want to click a specific spot manually. Must set cursor position first.

**Cursor Position Setup**  
Click "Set Cursor Position" button to record a specific screen position for custom cursor mode. Use if you want consistent clicking at one exact spot.

---

## Auto-Walk

These settings control the automation features that work together to automate digging activities.

### Auto-Walk Settings

**Auto Walk Enabled**  
Automatically moves your character around while digging. Cannot be used with Custom Cursor. Covers more ground automatically using built-in patterns or custom ones you create.

**Walk Duration (0-∞)**  
How long to hold down movement keys in milliseconds. Higher values create longer movement steps, lower values create shorter, more precise movements.

**Max Wait Time (0-∞)**  
Maximum time to wait for target engagement after moving. If no target found, advances to next movement step.

**Dynamic Walkspeed**  
Increases walk duration based on how much items you collect to simulate the walkspeed decrease in-game. Uses a mathematical equation to calculate this.

The auto-walk overlay will also update accordingly.

![Dynamic Walkspeed Example](/assets/docs/technical/dynamic_walkspeed_example.png)

**Initial Item Count (0-∞)**  
Starting item count for walkspeed calculation. Useful if you already have items when starting the tool. This is factored in with the mathematical equation.

**Initial Walkspeed Decrease (0.0-1.0)**
Starting walkspeed decrease that must be expressed as a decimal rather than a percentage (19% -> 0.1). This is factored in with the mathematical equation.

### Auto-Sell

**Auto Sell**  
Automatically sells items after a certain number of digs. Must set up sell button position or use UI navigation. Keeps inventory from reaching the in-game item limit and potential auto-walk overlap.

**Sell Every X Digs (1-∞)**  
Number of digs before auto-selling.

**Sell Delay (0-∞)**  
Wait time in milliseconds before clicking the sell button. This gives the inventory time to open fully. 

**Auto Sell Method**  
Choose between "Button Click" (clicks on a specific position you set, requires "Set Sell Button") or "UI Navigation" (uses ROBLOX's UI navigation to navigate the in-game UIs). UI navigation is often more reliable and is recommended.

The default UI navigation sequence is not for everyone because of UI updates or ROBLOX being bipolar. You will need to change the sequence on your own if this is the case.

**Auto Sell UI Sequence**  
Keyboard sequence for UI navigation auto-sell. Format as comma-separated keys like "down,up,enter". Available keys: down, up, left, right, enter. Only used when Auto Sell Method is "UI Navigation". Enter should be your last step and this is when it will press the sell button.

**Auto Sell Target Engagement**  
Waits for target re-engagement after auto-sell completion to ensure the tool properly returns to digging after selling. This will press the ``g`` key once to close the inventory in the circumstances that the inventory may still open after auto-sell. Typically, there are no issues related to having this enabled and there may be an underlying issue.

**Auto Sell Target Engagement Timeout (0-∞)**  
How long to wait for target engagement after selling. If no engagement detected, applies the fallback (as mentioned above).

### Auto-Shovel

**Auto Shovel Enabled**  
Automatically re-equips your shovel when it breaks or gets unequipped. This was added to fix a game bug where your shovel is out but you can't move or dig.

**Shovel Slot (0-9)**  
Which inventory slot your shovel is in (0-9, where 0 = slot 1, 1 = slot 2, etc.). Must match your actual shovel location.

**Shovel Timeout (1-∞)**  
How long to wait before re-equipping after no dig activity.

**Shovel Equip Mode**  
Choose "Single" (presses the shovel key once) or "Double" (presses the shovel key twice quickly). Double mode is usually more reliable as it's the most intended.

---

## Discord

These settings control Discord notifications for milestones and rare items.

### General Notifications

**Webhook URL**  
Discord webhook URL for sending notifications. Required for any Discord notifications to work. C

**Server ID**  
Your Discord server's ID number. Optional - notifications work without this but it won't provide a message link to return back to live stats.

**User ID**  
Your Discord user ID for mentions. Optional - leave blank if you don't want mentions.

**Milestone Interval (1-∞)**  
How often to send dig count milestone notifications. Set to 100 to get notified every 100 digs, or set to 0 to disable milestone notifications.

**Include Screenshot in Discord**  
Attaches screenshots to Discord notifications. Shows what was happening when notification was sent.

### Money Detection

**Money Detection**  
Detects and tracks your in-game money amount. Must set up money area first. Includes money information in Discord notifications.

**Money Area Setup**  
Click "Select Money Area" button to set this up. Select the area of your screen showing your money amount. 

Ensure when you're selecting that you're selecting a rectangle of the area where your money is. There must be enough space when it may extend (for example, $100,000 to $1,000,000).

![Money Area Setup Example](/assets/docs/technical/set_money_area_example.png)

**Test Money OCR**  
Tests if money detection is working properly. Use after setting up money area to verify it works. Shows the detected money value or error message.

This will show the detected money value in the status box within the main window.

![Test Money OCR Example](/assets/docs/technical/test_money_ocr_example.png)

### Item Detection

**Item Detection**  
Detects rare items and sends Discord notifications. Must set up item area first. Get notified immediately when you find rare items.

**Item Area Setup**  
Click "Select Item Area" button to set this up. Select the area showing item information when you dig - the area where rarity and item names appear.

Ensure when you're selecting that you're selecting a wide rectangle of where item names pop up. Make sure there's enough space for bigger text pop ups like legendaries or divines.

![Item Detection Example](/assets/docs/technical/item_detection_example.png)

**Notification Rarities**  
Choose which item rarities trigger notifications: Scarce, Legendary, Mythical, Divine, Prismatic. All rare types are enabled by default. Uncheck rarities you don't want notifications for.

**Test Item OCR**  
Tests if item detection is working properly. Use after setting up item area to verify it works. Shows the detected item rarity and text or error message.

Similar to testing money OCR, it will also show the item rarity in the status box within te main window.

![test Item OCR](/assets/docs/technical/test_item_ocr_example.png)

---

## Window

These settings control window behavior and positioning.

### Window Controls

**Main Window On Top**  
Keeps the main tool window above all other windows. Provides easy access to controls but may cover other applications.

**Preview Window On Top**  
Keeps the preview window above all other windows. Always see what the tool is detecting. Enable if you want constant visual feedback.

**Debug Window On Top**  
Keeps the debug console above all other windows. Monitor debug messages without switching windows. Enable when actively debugging issues.

---

## Debug

These settings affect how the tool performs and uses system resources.

### Debug & Performance

**Screenshot FPS (1-∞)**  
Frame rate for screenshot capture. This is limited by your monitor's refresh rate and may significantly affect how Dig Tool operates during the minigame.

**Save Debug Screenshots**  
Saves screenshots and debug information for every click. Helps troubleshoot some issues. Only enable when investigating problems.

---

> [!NOTE]
> Many settings have dependencies on each other. The tool will automatically disable conflicting options and show tooltips explaining why certain settings are unavailable.

> [!TIP]
> Start with default settings and adjust gradually. Most users only need to modify a few settings to get optimal performance for their setup.