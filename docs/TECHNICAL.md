# 🔧 Dig Tool — Technical Options Guide

## Table of Contents

<!-- Run with: npx doctoc --maxlevel 3 docs/TECHNICAL.md -->

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Overview](#overview)
- [Detection Settings](#detection-settings)
  - [Line Detection](#line-detection)
  - [Zone Detection](#zone-detection)
  - [Movement Detection](#movement-detection)
  - [Advanced Detection](#advanced-detection)
- [Behavior Settings](#behavior-settings)
  - [Prediction](#prediction)
  - [Input & Timing](#input--timing)
  - [Auto-Sell](#auto-sell)
  - [Auto-Walk](#auto-walk)
  - [Auto-Shovel](#auto-shovel)
- [Discord Settings](#discord-settings)
  - [General Notifications](#general-notifications)
  - [Money Detection](#money-detection)
  - [Item Detection](#item-detection)
- [Performance Settings](#performance-settings)
  - [System & Performance](#system--performance)
  - [Debug & Overlay](#debug--overlay)
- [Input Controls](#input-controls)
  - [Hotkeys](#hotkeys)
  - [Custom Cursor](#custom-cursor)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

---

## Overview

This guide explains every setting and option available in the Dig Tool. Each setting is described in simple terms to help you understand what it does and how it affects the tool's behavior.

> [!TIP]
> You can hover over any setting in the tool to see a brief tooltip explanation. This guide provides more detailed information about each option.

---

## Detection Settings

These settings control how the tool finds and tracks the sweet spot in the digging mini-game.

### Line Detection

**Line Sensitivity**
- **What it does**: Controls how sharp the contrast must be to detect the moving line
- **Higher values**: Less sensitive to weak edges (more selective)
- **Lower values**: More sensitive to faint lines (may detect false positives)
- **Typical range**: 50-150
- **When to adjust**: If the tool isn't detecting the line consistently, try lowering this value

**Line Detection Offset**
- **What it does**: Moves the detected line position left or right by a specific number of pixels
- **Positive values**: Shifts the line detection to the right
- **Negative values**: Shifts the line detection to the left
- **Decimals allowed**: You can use precise values like 2.5 or -1.2
- **When to adjust**: If clicks seem slightly off-target, fine-tune this value

**Line Exclusion Radius**
- **What it does**: Creates a circular "dead zone" around the detected line where target zones are ignored
- **Purpose**: Prevents the moving line from interfering with zone detection
- **Typical range**: 5-20 pixels
- **When to adjust**: If the tool gets confused when the line passes through valid zones

### Zone Detection

**Zone Min Width**
- **What it does**: Sets the minimum pixel width for a valid target zone
- **Purpose**: Filters out tiny zones that aren't worth clicking
- **Typical range**: 50-200 pixels
- **When to adjust**: If the tool clicks on very small, insignificant zones

**Max Zone Width Percent**
- **What it does**: Sets the maximum width of a target zone as a percentage of the capture area
- **Range**: 0-200% (values above 100% allow detecting zones wider than the capture area)
- **Purpose**: Prevents detection of massive zones that might be background elements
- **When to adjust**: If the tool incorrectly selects very large areas

**Min Zone Height Percent**
- **What it does**: Requires target zones to span at least this percentage of the capture height
- **Range**: 0-100%
- **Purpose**: Ensures zones are tall enough to be valid dig spots
- **When to adjust**: If the tool selects thin horizontal lines that aren't dig zones

**Sweet Spot Width Percent**
- **What it does**: Controls the width of the clickable area in the center of detected zones
- **Range**: 5-50%
- **Smaller values**: More precise clicking required
- **Larger values**: More forgiving, but less accurate
- **When to adjust**: If you're missing hits frequently, try increasing this value

### Movement Detection

**Saturation Threshold**
- **What it does**: Controls how colorful a pixel must be to be part of the initial zone search
- **Range**: 0.0-1.0 (higher = more colorful required)
- **Purpose**: Helps filter out dull background elements
- **When to adjust**: If the tool detects too much background or misses colorful dig zones

**Zone Smoothing Factor**
- **What it does**: Controls how much the target zone movement is smoothed over time
- **Range**: 0.0-2.0
- **1.0**: No smoothing (zone jumps immediately)
- **Lower values**: More smoothing (zone moves more gradually)
- **Higher values**: Less smoothing (zone follows detection more directly)
- **When to adjust**: If zone tracking is too jittery or too slow to respond

**Velocity Based Width Enabled**
- **What it does**: Automatically adjusts sweet spot width based on how fast the line is moving
- **When enabled**: Faster line movement = wider sweet spot for easier targeting
- **Purpose**: Makes it easier to hit fast-moving targets
- **When to use**: Enable if you have trouble hitting targets when the line moves quickly

**Velocity Width Multiplier**
- **What it does**: Controls how much line speed affects sweet spot width
- **Range**: 0.5-5.0
- **Higher values**: More dramatic width changes based on speed
- **Lower values**: More subtle width adjustments
- **Only works**: When "Velocity Based Width Enabled" is on

**Velocity Max Factor**
- **What it does**: Sets the maximum velocity for normalization (pixels per second)
- **Purpose**: Velocities above this value are treated as maximum speed
- **Typical range**: 1000-5000 px/s
- **When to adjust**: If velocity-based width isn't working correctly

### Advanced Detection

**Use Otsu Detection**
- **What it does**: Uses automatic threshold calculation instead of manual saturation settings
- **Benefits**: Can be more adaptive to different lighting conditions
- **Cannot be used with**: Color Picker Detection (they conflict)
- **When to use**: If manual saturation threshold isn't working well

**Otsu Min Area**
- **What it does**: Minimum area (in pixels) for detected regions when using Otsu
- **Purpose**: Filters out tiny regions that aren't valid zones
- **Only works**: When "Use Otsu Detection" is enabled

**Otsu Max Area**
- **What it does**: Maximum area (in pixels) for detected regions when using Otsu
- **Purpose**: Prevents detection of huge areas that aren't dig zones
- **Leave empty**: For no upper limit
- **Only works**: When "Use Otsu Detection" is enabled

**Use Color Picker Detection**
- **What it does**: Uses a specific color you pick to detect target zones
- **How to use**: Enable this, then click "Pick Color from Screen" to select your target color
- **Benefits**: Very precise when you know the exact color you want to detect
- **Cannot be used with**: Otsu Detection (they conflict)

**Color Tolerance**
- **What it does**: How close colors need to be to your picked color to be detected
- **Range**: 1-90
- **Higher values**: More lenient color matching
- **Lower values**: More precise color matching
- **Only works**: When "Use Color Picker Detection" is enabled

---

## Behavior Settings

These settings control how the tool behaves during operation.

### Prediction

**Prediction Enabled**
- **What it does**: Predicts where the line will be and clicks earlier to compensate for delays
- **Benefits**: Can improve accuracy on fast systems
- **Drawbacks**: May cause issues if prediction is wrong
- **When to disable**: If you're getting inconsistent hits or weird behavior

**Prediction Confidence Threshold**
- **What it does**: How confident the prediction must be before it's used
- **Range**: 0.0-1.0
- **Higher values**: More conservative prediction (only predicts when very sure)
- **Lower values**: More aggressive prediction (predicts more often)
- **Only works**: When "Prediction Enabled" is on

### Input & Timing

**Post Click Blindness**
- **What it does**: How long to wait after clicking before scanning for new targets
- **Purpose**: Prevents multiple rapid clicks on the same spot
- **Range**: 10-500 milliseconds
- **Higher values**: Slower clicking but more stable
- **Lower values**: Faster clicking but may double-click

**System Latency**
- **What it does**: Compensates for delays between detection and clicking
- **"Auto" setting**: Automatically calculates based on your system
- **Manual values**: You can set a specific delay in milliseconds
- **When to adjust**: If clicks seem to lag behind the detection

### Auto-Sell

**Auto Sell Enabled**
- **What it does**: Automatically sells items after a certain number of digs
- **Requirements**: Must set up sell button position or use UI navigation
- **Benefits**: Keeps inventory from getting full

**Sell Every X Digs**
- **What it does**: Number of successful digs before auto-selling
- **Typical range**: 5-50 digs
- **Lower values**: Sell more frequently
- **Higher values**: Sell less frequently

**Sell Delay**
- **What it does**: Wait time in milliseconds before clicking the sell button
- **Purpose**: Gives the inventory time to open fully
- **Typical range**: 500-2000 milliseconds
- **Increase if**: The sell button isn't clicked properly

**Auto Sell Method**
- **"Button Click"**: Clicks on a specific position you set (requires "Set Sell Button")
- **"UI Navigation"**: Uses keyboard shortcuts to navigate the interface
- **Button Click**: More reliable but requires setup
- **UI Navigation**: No position setup needed but may be less reliable

**Auto Sell UI Sequence**
- **What it does**: Keyboard sequence for UI navigation auto-sell
- **Format**: Comma-separated keys like "down,up,enter"
- **Available keys**: down, up, left, right, enter
- **Only used**: When Auto Sell Method is "UI Navigation"

**Auto Sell Target Engagement**
- **What it does**: Waits for target re-engagement after auto-sell completion
- **Purpose**: Ensures the tool properly returns to digging after selling
- **Disable if**: Your inventory stays open after selling

**Auto Sell Target Engagement Timeout**
- **What it does**: How long to wait for target engagement after selling
- **Range**: 5-300 seconds
- **Purpose**: If no engagement detected, applies fallback actions
- **Only works**: When "Auto Sell Target Engagement" is enabled

### Auto-Walk

**Auto Walk Enabled**
- **What it does**: Automatically moves your character around while digging
- **Cannot be used with**: Custom Cursor (they conflict)
- **Benefits**: Covers more ground automatically
- **Patterns**: Choose from built-in patterns or create custom ones

**Walk Duration**
- **What it does**: How long to hold down movement keys (in milliseconds)
- **Typical range**: 100-1000 milliseconds
- **Higher values**: Longer movement steps
- **Lower values**: Shorter, more precise movements

**Max Wait Time**
- **What it does**: Maximum time to wait for target engagement after moving
- **Purpose**: If no target found, advances to next movement step
- **Range**: 1000-10000 milliseconds

**Dynamic Walkspeed Enabled**
- **What it does**: Slows down movement as you collect more items
- **Purpose**: Simulates realistic fatigue effects
- **Formula**: Uses mathematical calculation based on item count

**Initial Item Count**
- **What it does**: Starting item count for walkspeed calculation
- **Purpose**: Useful if you already have items when starting the tool
- **Only works**: When "Dynamic Walkspeed Enabled" is on

### Auto-Shovel

**Auto Shovel Enabled**
- **What it does**: Automatically re-equips your shovel when it breaks or gets unequipped
- **Benefits**: Reduces manual intervention
- **Requirements**: Must set the correct shovel slot number

**Shovel Slot**
- **What it does**: Which inventory slot your shovel is in
- **Range**: 0-9 (0 = slot 1, 1 = slot 2, etc.)
- **Important**: Must match your actual shovel location

**Shovel Timeout**
- **What it does**: How long to wait before re-equipping after no dig activity
- **Range**: 1-60 seconds
- **Purpose**: Prevents constantly re-equipping during normal pauses

**Shovel Equip Mode**
- **"Single"**: Presses the shovel key once
- **"Double"**: Presses the shovel key twice quickly
- **Double mode**: Usually more reliable for re-equipping

---

## Discord Settings

These settings control Discord notifications for milestones and rare items.

### General Notifications

**Webhook URL**
- **What it does**: Discord webhook URL for sending notifications
- **Required**: For any Discord notifications to work
- **How to get**: Create a webhook in your Discord server settings

**Server ID**
- **What it does**: Your Discord server's ID number
- **Purpose**: Used for mention formatting in notifications
- **Optional**: Notifications work without this but mentions won't

**User ID**
- **What it does**: Your Discord user ID for mentions
- **Purpose**: Tool can mention you in notifications
- **Optional**: Leave blank if you don't want mentions

**Milestone Interval**
- **What it does**: How often to send dig count milestone notifications
- **Example**: Set to 100 to get notified every 100 digs
- **Set to 0**: Disables milestone notifications

**Include Screenshot in Discord**
- **What it does**: Attaches screenshots to Discord notifications
- **Benefits**: Shows what was happening when notification was sent
- **Drawbacks**: Makes notifications larger and slower to send

### Money Detection

**Enable Money Detection**
- **What it does**: Detects and tracks your in-game money amount
- **Requirements**: Must set up money area first
- **Purpose**: Includes money information in Discord notifications

**Money Area Setup**
- **How to set**: Click "Select Money Area" button
- **What to select**: The area of your screen showing your money amount
- **Tips**: Select just the number, not labels or decorations

**Test Money OCR**
- **What it does**: Tests if money detection is working properly
- **When to use**: After setting up money area to verify it works
- **Shows**: The detected money value or error message

### Item Detection

**Enable Item Detection**
- **What it does**: Detects rare items and sends Discord notifications
- **Requirements**: Must set up item area first
- **Benefits**: Get notified immediately when you find rare items

**Item Area Setup**
- **How to set**: Click "Select Item Area" button
- **What to select**: The area showing item information when you dig
- **Tips**: Select the area where rarity and item names appear

**Notification Rarities**
- **What it does**: Choose which item rarities trigger notifications
- **Options**: Scarce, Legendary, Mythical, Divine, Prismatic
- **Default**: All rare types are enabled
- **Customize**: Uncheck rarities you don't want notifications for

**Test Item OCR**
- **What it does**: Tests if item detection is working properly
- **When to use**: After setting up item area to verify it works
- **Shows**: The detected item rarity and text or error message

---

## Performance Settings

These settings affect how the tool performs and uses system resources.

### System & Performance

**Target FPS**
- **What it does**: How many screenshots per second the tool takes
- **Range**: 30-500 FPS
- **Higher values**: Lower latency but more CPU usage
- **Lower values**: Less CPU usage but higher latency
- **Recommended**: 120-240 FPS for best balance

**Screenshot FPS**
- **What it does**: Frame rate for screenshot capture specifically
- **Range**: 30-500 FPS
- **Purpose**: Can be different from target FPS for optimization
- **When to adjust**: If you need different capture vs processing rates

### Debug & Overlay

**Debug Enabled**
- **What it does**: Saves screenshots and debug information for every click
- **Purpose**: Helps troubleshoot detection issues
- **Warning**: Uses lots of disk space over time
- **When to enable**: Only when investigating problems

**Main Window On Top**
- **What it does**: Keeps the main tool window above all other windows
- **Benefits**: Easy access to controls
- **Drawbacks**: May cover other applications

**Preview Window On Top**
- **What it does**: Keeps the preview window above all other windows
- **Purpose**: Always see what the tool is detecting
- **When to enable**: If you want constant visual feedback

**Debug Window On Top**
- **What it does**: Keeps the debug console above all other windows
- **Purpose**: Monitor debug messages without switching windows
- **When to enable**: When actively debugging issues

---

## Input Controls

These settings control how you interact with the tool and game.

### Hotkeys

**Start/Stop Macro** (Default: F1)
- **What it does**: Toggles the main automation on and off
- **Important**: Primary control for the tool
- **Can customize**: Change to any key you prefer

**Show/Hide Main GUI** (Default: F2)
- **What it does**: Shows or hides the main tool window
- **Benefits**: Reduces screen clutter while keeping tool running
- **Quick access**: Easy to bring back when needed

**Show/Hide Overlay** (Default: F3)
- **What it does**: Shows or hides the detection overlay
- **Purpose**: See real-time detection without the full preview window
- **Visual feedback**: Shows what zones are being detected

**Toggle Auto-Walk Overlay** (Default: F4)
- **What it does**: Shows or hides the auto-walk pattern overlay
- **Purpose**: See the current walking pattern and progress
- **Only visible**: When auto-walk is enabled

### Custom Cursor

**Use Custom Cursor**
- **What it does**: Uses a custom cursor position instead of auto-detection
- **Cannot be used with**: Auto-Walk (they conflict)
- **Purpose**: For setups where you want to click a specific spot manually
- **Setup required**: Must set cursor position first

**Cursor Position Setup**
- **How to set**: Click "Set Cursor Position" button
- **What it does**: Records a specific screen position for custom cursor mode
- **When to use**: If you want consistent clicking at one exact spot

---

> [!NOTE]
> Many settings have dependencies on each other. The tool will automatically disable conflicting options and show tooltips explaining why certain settings are unavailable.

> [!TIP]
> Start with default settings and adjust gradually. Most users only need to modify a few settings to get optimal performance for their setup.

> [!WARNING]
> Some settings like Debug Mode can use significant system resources. Only enable resource-intensive options when necessary.
