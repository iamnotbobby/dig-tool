> [!IMPORTANT]
> This documentation covers only a core subset of Dig Tool's functionality. Please consider reading the codebase to understand further.

# ⚙️ Dig Tool — Technical Documentation

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Technologies](#core-technologies)
- [Project Structure](#project-structure)
- [Detection System](#detection-system)
  - [Line Detection](#line-detection)
  - [Zone Detection](#zone-detection)
  - [Color Locking](#color-locking)
- [Visual Processing Pipeline](#visual-processing-pipeline)
  - [Screen Capture Workflow](#screen-capture-workflow)
  - [Processing Pipeline](#processing-pipeline)
- [Prediction System](#prediction-system)
  - [Velocity Calculation Process](#velocity-calculation-process)
  - [Compensation Algorithms](#compensation-algorithms)
- [Input Management System](#input-management-system)
  - [Click Execution Process](#click-execution-process)
- [Automation Framework](#automation-framework)
  - [State Machine Architecture](#state-machine-architecture)
  - [Movement Pattern System](#movement-pattern-system)
  - [Activity Monitoring System](#activity-monitoring-system)
- [OCR Integration](#ocr-integration)
  - [Windows OCR Engine Process](#windows-ocr-engine-process)


---

## Architecture Overview

Dig Tool is built on a modular Python architecture using computer vision libraries for real-time screen analysis, high-performance capture systems, and Windows OCR for text recognition. The application uses an event-driven design with multithreaded processing to handle detection, automation, and UI management concurrently.

---

## Core Technologies

**Computer Vision:**
- **OpenCV** (`opencv-python`) - Image processing, contour detection, morphological operations
- **NumPy** (`numpy`) - High-performance array operations and numerical computing

**Screen Capture:**
- **MSS** (`mss`) - Fast screen capture 
- **PIL** (`pillow`) - Image format conversion and enhancement

**Input Control:**
- **PyNput** (`pynput`) - Primary input automation and hotkey detection  
- **PyAutoIt** (`PyAutoIt`) - Primary input method for auto-sell functionality
- **PyAutoGUI** (`pyautogui`) - Fallback input methods
- **PyWin32** (`pywin32`) - Windows API integration for cursor positioning

**OCR & Text Recognition:**
- **WinRT Windows.Media.Ocr** (`winrt-Windows.Media.Ocr`) - Native Windows 10/11 OCR engine
- **WinRT Windows.Graphics.Imaging** (`winrt-Windows.Graphics.Imaging`) - Windows image processing
- **WinRT Windows.Storage.Streams** (`winrt-Windows.Storage.Streams`) - Windows stream handling
- **WinRT Windows.Foundation** (`winrt-Windows.Foundation`) - Windows Runtime foundation classes

**UI & Interface:**
- **Tkinter** - Main interface and real-time preview windows
- **TkinterDnD2** (`tkinterdnd2`) - Drag and drop functionality for Tkinter

**System Integration:**
- **PSUtil** (`psutil`) - System and process monitoring
- **Watchdog** (`watchdog`) - File system event monitoring

**Development & Deployment:**
- **PyInstaller** (`PyInstaller`) - Application packaging and executable creation

---

## Project Structure

### Root Files

**`main.py`** - Application entry point and main controller. Initializes the GUI, coordinates all system components, manages global state, and handles the primary event loop for detection and automation.

**`build.py`** - Build script for creating standalone executables. Uses PyInstaller to package the application with all dependencies into a single executable file for distribution.

### Core System (`core/`)

**`detection.py`** - Computer vision algorithms for target identification. Contains line detection, zone detection, color analysis, and target tracking functions using OpenCV.

**`initialization.py`** - Application startup procedures. Handles system compatibility checks, initial configuration loading, and core component initialization.

**`notifications.py`** - Discord webhook integration system. Manages real-time status updates, error reporting, and activity notifications to Discord channels.

**`ocr.py`** - Optical Character Recognition engine. Handles money detection and item identification.

#### Automation Subsystem (`core/automation/`)

**`automation_manager.py`** - Central automation coordinator. Manages all automation subsystems, state synchronization, and cross-module communication.

**`auto_sell.py`** - Automated selling functionality. Handles inventory management, selling sequences, and interaction with in-game market interfaces.

**`auto_shovel.py`** - Shovel re-equipment automation. Monitors tool status and automatically re-equips shovels when needed.

**`movement.py`** - Player movement control system (aka auto-walk). Executes movement patterns, handles directional input, and manages walking automation with velocity calculations.

**`pattern_manager.py`** - Custom walk pattern system. Records, stores, and replays user-defined movement patterns with timing accuracy and coordinate scaling.

**`roblox_status.py`** - Game state monitoring. Tracks Roblox window status, connection state, and game session continuity.

**`shift_manager.py`** - Shift key management. Handles shift state tracking and shift key automation during movement patterns.

### User Interface (`interface/`)

**`main_window.py`** - Primary application window and GUI controller. Contains the main interface layout, control panels, and user interaction handlers.

**`components.py`** - Reusable UI components library. Provides custom widgets, tooltips, collapsible panels, and specialized interface elements.

**`settings.py`** - Settings management interface. Handles configuration panels, parameter validation, and settings persistence across application sessions.

**`export_options_dialog.py`** - Configuration export/import interface. Provides dialogs for sharing settings, patterns, and configurations between users.

#### Custom Pattern Window (`interface/custom_pattern_window/`)

**`main_window.py`** - Pattern creation and management interface. Primary window for recording, editing, and managing walk patterns.

**`pattern_display.py`** - Visual pattern representation. Renders pattern previews, path visualizations, and movement trajectory displays.

**`pattern_operations.py`** - Pattern manipulation tools. Handles pattern editing, coordinate transformation, and pattern optimization functions.

**`preview_manager.py`** - Real-time pattern preview system. Provides live preview of patterns during recording and playback.

**`recording_manager.py`** - Pattern recording controller. Captures user movement, timing data, and input sequences for pattern creation.

**`ui_components.py`** - Pattern-specific interface elements. Custom widgets and controls designed specifically for pattern management.

#### Debug Logger Window (`interface/debug_logger_window/`)

**`main_window.py`** - Debug console interface. Provides real-time log viewing, error tracking, and system diagnostics display.

**`search_operations.py`** - Log search and filtering functionality. Enables searching through debug logs with filters and search criteria.

**`ui_components.py`** - Debug interface components. Specialized widgets for log display, filtering controls, and diagnostic information.

#### Settings Feedback Window (`interface/settings_feedback_window/`)

**`main_window.py`** - Settings testing and validation interface. Provides tools for testing configuration changes and validating settings.

**`progress_operations.py`** - Settings application progress tracking. Manages progress indicators during settings updates and system configuration changes.

### Utility Systems (`utils/`)

**`config_management.py`** - Configuration persistence and retrieval. Handles settings storage, parameter validation, and configuration file management.

**`debug_logger.py`** - Logging and debugging system. Provides structured logging, error tracking, and diagnostic information collection.

**`input_management.py`** - Input handling and hotkey system. Manages keyboard shortcuts, mouse input capture, and input event processing.

**`pattern_utils.py`** - Pattern processing utilities. Helper functions for pattern manipulation, coordinate calculations, and pattern file operations.

**`screen_capture.py`** - Screen capture and image processing. Handles screen capture operations, image format conversion, and capture region management.

**`system_utils.py`** - System integration and compatibility. Provides system-specific functions, compatibility checks, and OS integration features.

**`thread_utils.py`** - Threading and concurrency management. Thread-safe utilities, synchronization primitives, and background task coordination.

**`ui_management.py`** - Interface state management. Handles UI updates, window positioning, and interface synchronization across modules.

---

## Detection System

### Line Detection

The line detection process operates on a continuous cycle to track the moving vertical line during the minigame:

**1. Frame Preprocessing**  
Each captured frame is converted to grayscale for edge detection. The system processes the full frame height but can fall back to analyzing only the bottom 30% if the primary detection fails.

**2. Edge Detection Pipeline**  
The grayscale image undergoes Canny edge detection with user-configurable sensitivity. Higher sensitivity values make the detection more selective, filtering out weak edges while preserving strong vertical lines.

**3. Morphological Filtering**  
A vertical morphological kernel removes noise and ensures detected lines meet minimum height requirements. This prevents false positives from horizontal elements or small artifacts.

**4. Position Calculation**  
The system projects edge pixels horizontally to find the strongest vertical line. An optional offset parameter allows fine-tuning the detected position by shifting it left or right in pixel increments.

```python
# Core line detection algorithm using gradient-based edge detection
left_right_diff = np.abs(
    gray_array[:, 2:].astype(np.float32) - gray_array[:, :-2].astype(np.float32)
)
center_left_diff = np.abs(
    gray_array[:, 1:-1].astype(np.float32) - gray_array[:, :-2].astype(np.float32)
)
gradients = left_right_diff + center_left_diff
vertical_sum = np.sum(gradients, axis=0)

# Apply thresholds and find the strongest vertical line
valid_mask = (vertical_sum > thresh) & (strong_pixel_count >= min_pixels)
best_idx = np.argmax(vertical_sum * valid_mask)
detected_position = best_idx + 1
```

**5. Fallback Detection**  
If no line is found in the full frame, the algorithm automatically switches to analyzing the bottom portion of the screen, which often contains clearer line visibility.

### Zone Detection

Zone detection employs three mutually exclusive methods that can be switched based on environmental conditions:

**Saturation-Based Detection Process:**
1. Extract the HSV saturation channel from the top 80% of the frame
2. Apply binary thresholding based on user-defined saturation levels

```python
def detect_by_saturation(hsv, saturation_threshold):
    saturation = hsv[:, :, 1]
    _, mask = cv2.threshold(saturation, saturation_threshold, 255, cv2.THRESH_BINARY)
    return mask
```

**Otsu Automatic Detection Process:**
1. Calculate optimal threshold automatically using Otsu's algorithm
2. Apply morphological operations to clean up noise and fill gaps
3. Filter detected regions by area constraints (minimum/maximum pixel areas)

```python
# Otsu thresholding with morphological cleanup
saturation = hsv[:, :, 1]
threshold_value, otsu_mask = cv2.threshold(
    saturation, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
)

# Clean up the mask with morphological operations
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_kernel_size, morph_kernel_size))
otsu_mask = cv2.morphologyEx(otsu_mask, cv2.MORPH_CLOSE, kernel)  # Close gaps
otsu_mask = cv2.morphologyEx(otsu_mask, cv2.MORPH_OPEN, kernel)   # Remove noise
```

**Color Picker Detection Process:**
1. User samples a specific color by selecting a screen area
2. System calculates median color from the sampled region
3. Creates HSV tolerance ranges around the target color
4. Performs real-time matching within tolerance bounds

### Color Locking

Color locking prevents detection drift by establishing consistent target identification:

**Lock Establishment:**
1. When a valid zone is first detected, the system analyzes pixels within the zone contour
2. Calculates mean HSV values to establish a "locked" target color
3. Creates upper and lower HSV bounds with configurable tolerance
4. Stores the locked color as both HSV values and hex representation

**Lock Maintenance:**
1. Future detections use the locked HSV ranges instead of original thresholds
2. System maintains lock until no zones are detected for a timeout period
3. Lock automatically releases if detection fails for multiple consecutive frames
4. Otsu detection can optionally disable color lock for continuous adaptation

---

## Visual Processing Pipeline

### Screen Capture Workflow

The screen capture system operates on a high-performance pipeline designed for real-time processing:

**1. Capture Region Definition**  
Users define rectangular regions through a selection tool.

**2. Real-Time Frame Acquisition**  
The MSS library captures frames at user-defined intervals. Each frame is immediately converted to a NumPy array format compatible with OpenCV operations.

**3. Memory Management**  
Captured frames are processed in-memory without disk writes. Old frames are automatically garbage collected to prevent memory accumulation during extended operation periods. Pre-allocated arrays minimize memory allocations during processing.

### Processing Pipeline

**Color Space Conversion:**  
Raw BGR frames are converted to HSV for color-based detection operations. HSV provides better color separation and is less sensitive to lighting variations compared to RGB color spaces.

**Detection Processing:**  
Each frame undergoes parallel processing for line and zone detection. Line detection operates on grayscale conversions while zone detection uses HSV color channels. Both processes can run simultaneously without interference.

**Result Validation:**  
Detection results undergo validation checks including minimum area requirements, position sanity checks, and temporal consistency filtering to eliminate false positives and outliers.

**Output Generation:**  
Validated results are formatted for consumption by automation systems, UI displays, and notification handlers.

---

## Prediction System

### Velocity Calculation Process

The prediction system tracks line movement patterns to anticipate future positions:

**1. Position History Tracking**  
The system maintains a *rolling buffer* of recent line positions with timestamps. This creates a temporal dataset that reveals movement patterns and velocity changes over time.

**2. Velocity Analysis**  
By analyzing position changes between consecutive frames, the system calculates instantaneous velocity. Multiple velocity measurements are averaged to reduce noise and provide stable velocity estimates.

```python
class VelocityCalculator:
    def __init__(self, history_length=12):
        self.position_history = collections.deque(maxlen=history_length)
        self.velocity_history = collections.deque(maxlen=6)
        self._smoothing_weights = np.array([0.15, 0.25, 0.35, 0.25], dtype=np.float32)
```

**3. Acceleration Detection**  
Changes in velocity over time indicate acceleration or deceleration patterns. This information helps predict whether the line is speeding up, slowing down, or maintaining constant velocity.

**4. Predictive Calculation**  
Using current position, velocity, and acceleration data, the system extrapolates the line's future position. The prediction accounts for system latency and processing delays to improve click timing accuracy.

### Compensation Algorithms

**Latency Compensation:**  
The system measures and compensates for various delay sources including screen capture time, processing overhead, and input delivery delays. These measurements create a latency profile unique to each system configuration.

**Sweet Spot Targeting:**  
When a target "sweet spot" is defined, the prediction algorithm calculates when the moving line will intersect that position. 

**Error Correction:**  
The system continuously compares predicted positions with actual observed positions to refine its prediction accuracy. Persistent prediction errors trigger automatic calibration adjustments.

---

## Input Management System

### Click Execution Process

The input system manages precise timing and positioning for automated interactions:

**1. Target Validation**  
Before executing any click, the system validates that target conditions are met including line detection and zone presence.

**2. Position Calculation**  
Click coordinates are calculated based on detection results, user offsets, and prediction algorithms. The system can target exact line positions or use prediction to compensate for movement and latency.

---

## Automation Framework

### State Machine Architecture

The automation system operates through a hierarchical state machine that manages multiple concurrent processes:

**1. Master Controller**  
The top-level automation manager coordinates all automation modules. It maintains global state information including Roblox window status, user preferences, and emergency stop conditions.

**2. Master Controller**  
The top-level automation manager coordinates all automation modules. It maintains global state information including Roblox window status, user preferences, and emergency stop conditions.

```python
class AutomationManager:
    def __init__(self, dig_tool_instance):
        self.dig_tool = dig_tool_instance
        self.keyboard_controller = KeyboardController()
        
        # Initialize all automation subsystems
        self.shift_manager = ShiftManager(self.keyboard_controller)
        self.movement_manager = MovementManager(dig_tool_instance, self.keyboard_controller, self.shift_manager)
        self.auto_shovel_manager = AutoShovelManager(dig_tool_instance, self.keyboard_controller)
        self.pattern_manager = PatternManager(dig_tool_instance, self.keyboard_controller, self.shift_manager)
        self.auto_sell_manager = AutoSellManager(dig_tool_instance, self.keyboard_controller, self.shift_manager)
```

**3. Auto-Walk State Management**  
The auto-walk feature implements a three-state machine:
- **MOVE State**: Actively following movement patterns or seeking new targets
- **WAIT_FOR_TARGET State**: Monitoring for detection conditions with timeout handling  
- **DIGGING State**: Engaged with a target and performing click actions

**4. State Transition Logic**  
States transition based on detection results, timing constraints, and user configurations. Emergency conditions can force immediate transitions to safe states regardless of current operation.

### Movement Pattern System

**Pattern Execution Process:**
1. Patterns replay with configurable speed multipliers allowing faster or slower execution
2. Coordinate scaling adapts patterns to different screen resolutions automatically
3. Randomization can be applied to timing and positions to create more natural movement

```python
class MovementManager:
    def __init__(self, dig_tool, keyboard_controller, shift_manager):
        self.dig_tool = dig_tool
        self.keyboard_controller = keyboard_controller
        self.shift_manager = shift_manager
        self.walking_lock = threading.Lock()
        
        # Key mapping for cross-platform movement controls
        self.key_mapping = {
            "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
            "shift": Key.shift, "space": Key.space, "enter": Key.enter,
            # ... additional mappings
        }
```

### Activity Monitoring System

**User Activity Tracking:**  
The system monitors multiple indicators of user activity including manual clicks, dig actions, and target lock events.

```python
class AutoShovelManager:
    def update_dig_activity(self):
        self.last_dig_time = time.time()
        self.shovel_re_equipped = False
        self.shovel_re_equipped_time = None
        
    def should_re_equip_shovel(self):
        current_time = time.time()
        shovel_timeout = get_param(self.dig_tool, "shovel_timeout") * 60
        time_since_last_dig = current_time - self.last_dig_time if self.last_dig_time else 0
        return time_since_last_dig > shovel_timeout
```

**Auto-Rejoin Functionality:**  
When inactivity is detected, the system can automatically perform game rejoin sequences to maintain session continuity. This feature helps prevent disconnection during extended automation periods.

---

## OCR Integration

### Windows OCR Engine Process

The OCR system leverages Windows Runtime OCR capabilities for text recognition:

**1. Engine Initialization**  
On startup, the system attempts to create an OCR engine using the user's installed language profiles. The engine initialization is performed asynchronously to avoid blocking the main application thread.

```python
class BaseOCR:
    def initialize_ocr(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.ocr_engine = OcrEngine.try_create_from_user_profile_languages()
            self.initialized = bool(self.ocr_engine)
            return self.initialized
        except Exception as e:
            logger.error(f"OCR initialization failed: {e}")
            return False
```

**2. Image Preprocessing**  
Screenshots are converted to formats compatible with Windows OCR engine. This includes format conversion, resolution optimization, and color space adjustments for improved recognition accuracy.

**3. Text Recognition Pipeline**  
The OCR process operates asynchronously to prevent UI freezing during text recognition. Images are decoded and processed through the Windows Runtime bitmap decoder before OCR analysis.

```python
async def _ocr_single_image(self, image, image_name="unknown"):
    # Convert image to PNG format for Windows OCR
    img_byte_arr = io.BytesIO()
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image.save(img_byte_arr, format='PNG', optimize=False)
    
    # Process through Windows Runtime
    stream = InMemoryRandomAccessStream()
    data_writer = DataWriter(stream.get_output_stream_at(0))
    data_writer.write_bytes(img_byte_arr.getvalue())
    
    await data_writer.store_async()
    decoder = await BitmapDecoder.create_async(stream)
    software_bitmap = await decoder.get_software_bitmap_async()
    ocr_result = await self.ocr_engine.recognize_async(software_bitmap)
    
    return ocr_result.text if ocr_result.text else ""
```

**4. Result Processing**  
Recognized text undergoes validation and parsing to extract numeric values, filter out unwanted characters, and format results for consumption by automation systems.
