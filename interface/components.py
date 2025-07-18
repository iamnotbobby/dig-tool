from utils.config_management import get_param
from utils.system_utils import get_cached_system_latency
import tkinter as tk
from tkinter import Label, Frame, ttk, Canvas
import win32gui, win32con
from PIL import Image, ImageTk
import cv2
from utils.debug_logger import logger
import math


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<Motion>", self.on_motion)

    def on_motion(self, event=None):
        if self.tooltip_window:
            self.update_position()

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        self.create_tooltip()

    def create_tooltip(self):
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_attributes("-topmost", True)

        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 9, "normal"),
            wraplength=300,
            padx=8,
            pady=6,
        )
        label.pack()

        self.update_position()

    def update_position(self):
        if not self.tooltip_window:
            return

        try:
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 25

            self.tooltip_window.wm_geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except tk.TclError:
                pass
            self.tooltip_window = None


class CollapsiblePane(Frame):
    def __init__(self, parent, text="", manager=None, bg_color="#ffffff", **kwargs):
        Frame.__init__(self, parent, **kwargs)
        self.configure(bg=parent.cget("bg"))
        self.text = text
        self.manager = manager
        self.bg_color = bg_color
        self.is_open = tk.BooleanVar(value=False)

        self.header_frame = Frame(self, bg="#dcdcdc")
        self.header_frame.pack(fill="x")

        self.toggle_button = ttk.Button(
            self.header_frame,
            text=f"+ {self.text}",
            command=self.toggle,
            style="Header.TButton",
        )
        self.toggle_button.pack(fill="x", pady=2, padx=2)

        self.sub_frame = Frame(self, relief="solid", borderwidth=1, bg=self.bg_color)

    def toggle(self):
        if self.manager:
            self.manager.toggle(self)

    def open(self):
        if not self.is_open.get():
            self.sub_frame.pack(fill="x", pady=1, padx=1)  
            self.toggle_button.configure(text=f"− {self.text}")
            self.is_open.set(True)

    def close(self):
        if self.is_open.get():
            self.sub_frame.pack_forget()
            self.toggle_button.configure(text=f"+ {self.text}")
            self.is_open.set(False)


class AccordionManager:
    def __init__(self, dig_tool_instance):
        self.panes = []
        self.dig_tool_instance = dig_tool_instance

    def add_pane(self, pane):
        self.panes.append(pane)

    def toggle(self, selected_pane):
        for pane in self.panes:
            if pane == selected_pane:
                if pane.is_open.get():
                    pane.close()
                else:
                    pane.open()
                    self.dig_tool_instance.root.after(50, lambda: self._auto_scroll_to_pane(pane))
            else:
                pane.close()
        from utils.ui_management import resize_for_content
        resize_for_content(self.dig_tool_instance)

    def _auto_scroll_to_pane(self, pane):
        try:
            canvas = None
            
            if hasattr(self.dig_tool_instance, 'root'):
                for child in self.dig_tool_instance.root.winfo_children():
                    canvas = self._find_canvas_widget(child)
                    if canvas:
                        break
            
            if not canvas:
                return
            
            pane.update_idletasks()
            self.dig_tool_instance.root.update_idletasks()
            
            pane_y = pane.winfo_y()
            pane_height = pane.winfo_height()
            
            canvas_height = canvas.winfo_height()
            
            scroll_top = pane_y - (canvas_height // 4) 
            
            canvas.configure(scrollregion=canvas.bbox("all"))
            scroll_region = canvas.cget("scrollregion")
            if scroll_region:
                _, _, _, total_height = map(int, scroll_region.split())
                
                if total_height > canvas_height:
                    scroll_top = max(0, scroll_top)
                    scroll_fraction = scroll_top / (total_height - canvas_height)
                    scroll_fraction = max(0.0, min(1.0, scroll_fraction))
                    
                    canvas.yview_moveto(scroll_fraction)
                    
        except Exception as e:
            pass
    
    def _find_canvas_widget(self, widget):
        if isinstance(widget, tk.Canvas):
            return widget
        
        try:
            for child in widget.winfo_children():
                result = self._find_canvas_widget(child)
                if result:
                    return result
        except:
            pass
        
        return None


class GameOverlay:
    def __init__(self, parent):
        self.parent = parent
        self.overlay = None
        self.visible = False
        self.preview_label_overlay = None

        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False

    def create_overlay(self):
        if self.overlay:
            return

        try:
            self.overlay = tk.Toplevel()
            self.overlay.withdraw()
            self.overlay.title("Dig Info")
            self.overlay.wm_overrideredirect(True)
            self.overlay.attributes("-topmost", True)
            self.overlay.attributes("-alpha", 0.9)
            self.overlay.configure(bg="black", bd=2, relief="solid")

            self.overlay.after_idle(self._setup_overlay_content)
        except Exception as e:
            logger.error(f"Error creating overlay: {e}")

    def _setup_overlay_content(self):
        try:
            icon = self.parent.settings_manager.load_icon("assets/icon.png", (16, 16))
            if icon:
                self.overlay.iconphoto(False, icon)

            self._create_overlay_widgets()
            self.position_overlay()

            self.overlay.after(50, self._apply_window_style)
            self.overlay.after(200, self._show_overlay)
        except Exception as e:
            logger.error(f"Error setting up overlay content: {e}")

    def _show_overlay(self):
        try:
            self.overlay.deiconify()
            self.visible = True
            logger.debug("Overlay shown successfully")
        except Exception as e:
            logger.error(f"Error showing overlay: {e}")

    def _apply_window_style(self):
        try:
            hwnd = self.overlay.winfo_id()

            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~win32con.WS_MINIMIZEBOX
            style &= ~win32con.WS_MAXIMIZEBOX
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

        except Exception as e:
            logger.debug(f"Could not apply window style: {e}")

    def _create_overlay_widgets(self):
        self.overlay.minsize(200, 0)

        self.title_frame = Frame(self.overlay, bg="black", cursor="fleur")
        self.title_frame.pack(fill="x", padx=2, pady=(2, 0))

        title_label = Label(
            self.title_frame,
            text="Dig Tool",
            fg="white",
            bg="black",
            font=("Consolas", 11, "bold"),
            cursor="fleur",
        )
        title_label.pack(pady=3)

        self.title_frame.bind("<Button-1>", self.start_drag)
        self.title_frame.bind("<B1-Motion>", self.on_drag)
        self.title_frame.bind("<ButtonRelease-1>", self.stop_drag)
        title_label.bind("<Button-1>", self.start_drag)
        title_label.bind("<B1-Motion>", self.on_drag)
        title_label.bind("<ButtonRelease-1>", self.stop_drag)

        self.status_label = Label(
            self.overlay,
            text="STATUS: STOPPED",
            fg="#ff4757",
            bg="black",
            font=("Consolas", 10, "bold"),
        )
        self.status_label.pack(pady=(5, 5), padx=10, fill="x")

        self.target_label = Label(
            self.overlay,
            text="TARGET: ---",
            fg="#ff4757",
            bg="black",
            font=("Consolas", 10, "bold"),
        )
        self.target_label.pack(pady=(0, 5), padx=10, fill="x")

        self.swatch_frame = Frame(self.overlay, bg="black")
        swatch_label = Label(
            self.swatch_frame,
            text="LOCK:",
            fg="white",
            bg="black",
            font=("Consolas", 9),
        )
        swatch_label.pack(side=tk.LEFT)

        self.color_swatch_overlay_label = Label(
            self.swatch_frame, text=" " * 10, bg="black", relief="solid", bd=1
        )
        self.color_swatch_overlay_label.pack(
            side=tk.LEFT, fill="x", expand=True, padx=5
        )
        self.swatch_frame.pack(pady=(0, 5), padx=10, fill="x")

        stats_frame = Frame(self.overlay, bg="black")
        stats_frame.pack(pady=2, padx=10, fill="x")

        stats_frame.grid_columnconfigure(0, weight=1, uniform="stats")
        stats_frame.grid_columnconfigure(1, weight=1, uniform="stats")

        self.dig_label = Label(
            stats_frame,
            text="DIGS: 0",
            fg="#00ff88",
            bg="black",
            font=("Consolas", 9, "bold"),
            anchor="center",
        )
        self.dig_label.grid(row=0, column=0, sticky="ew", padx=5, pady=1)

        self.clicks_label = Label(
            stats_frame,
            text="CLICKS: 0",
            fg="#ff6b47",
            bg="black",
            font=("Consolas", 9),
            anchor="center",
        )
        self.clicks_label.grid(row=0, column=1, sticky="ew", padx=5, pady=1)

        self.pred_label = Label(
            stats_frame,
            text="PRED: ON",
            fg="#4ecdc4",
            bg="black",
            font=("Consolas", 9),
            anchor="center",
        )
        self.pred_label.grid(row=1, column=0, sticky="ew", padx=5, pady=1)

        self.latency_label = Label(
            stats_frame,
            text=f"LAT: {get_cached_system_latency(self.parent)}ms",
            fg="#a78bfa",
            bg="black",
            font=("Consolas", 9),
            anchor="center",
        )
        self.latency_label.grid(row=1, column=1, sticky="ew", padx=5, pady=1)
        
        # self.benchmark_label = Label(stats_frame, text="BENCH: 0 FPS", fg='maroon1', bg='black', font=('Consolas', 9))
        # self.benchmark_label.grid(row=2, column=0, sticky='w')

        key_frame = Frame(self.overlay, bg="black", pady=5)
        key_frame.pack(padx=15, fill="x")

        self.toggle_bot_label = Label(
            key_frame,
            text=f"Bot: {self.parent.keybind_vars['toggle_bot'].get()}",
            fg="gray",
            bg="black",
            font=("Consolas", 8),
        )
        
        self.toggle_bot_label.pack(side=tk.LEFT, expand=True)

        self.toggle_gui_label = Label(
            key_frame,
            text=f"GUI: {self.parent.keybind_vars['toggle_gui'].get()}",
            fg="gray",
            bg="black",
            font=("Consolas", 8),
        )
        self.toggle_gui_label.pack(side=tk.LEFT, expand=True)

        self.toggle_overlay_label = Label(
            key_frame,
            text=f"Ovl: {self.parent.keybind_vars['toggle_overlay'].get()}",
            fg="gray",
            bg="black",
            font=("Consolas", 8),
        )
        self.toggle_overlay_label.pack(side=tk.LEFT, expand=True)

        self.preview_label_overlay = Label(self.overlay, bg="black")
        self.preview_label_overlay.pack(pady=(5, 5), padx=10, fill="both", expand=True)

        self.position_overlay()

    def start_drag(self, event):
        if not self.overlay:
            return
        self.is_dragging = True
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root

    def on_drag(self, event):
        if not self.is_dragging or not self.overlay:
            return
        try:
            dx = event.x_root - self.drag_start_x
            dy = event.y_root - self.drag_start_y

            if abs(dx) < 1 and abs(dy) < 1:
                return

            x = self.overlay.winfo_x() + dx
            y = self.overlay.winfo_y() + dy

            self.overlay.geometry(f"+{x}+{y}")

            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
        except tk.TclError:
            pass

    def stop_drag(self, event):
        self.is_dragging = False

    def position_overlay(self):
        if not self.overlay or not self.parent.game_area:
            return
        x1, y1, x2, y2 = self.parent.game_area
        self.overlay.geometry(
            f"+{x2 + 10}+{min(y1, self.parent.root.winfo_screenheight() - 400)}"
        )

    def update_info(self, **kwargs):
        if not self.visible or not self.overlay:
            return
        try:
            automation_status = kwargs.get("automation_status", "STOPPED")
            if automation_status == "AUTO SELLING":
                self.status_label.config(text="STATUS: AUTO SELLING", fg="#ffa726")
            elif automation_status == "WALKING":
                self.status_label.config(text="STATUS: WALKING", fg="#ffeb3b")
            elif automation_status.startswith("AUTO WALKING"):
                self.status_label.config(text="STATUS: AUTO WALKING", fg="#00ff88")
            elif automation_status == "ACTIVE":
                self.status_label.config(text="STATUS: ACTIVE", fg="#00ff88")
            elif automation_status.startswith("RECORDING"):
                self.status_label.config(text="STATUS: ACTIVE", fg="#00ff88")
            else:
                self.status_label.config(text="STATUS: STOPPED", fg="#ff4757")

            target_engaged = kwargs.get("target_engaged", False)
            self.target_label.config(
                text=f"TARGET: {'LOCKED' if target_engaged else '---'}",
                fg="#00ff88" if target_engaged else "#ff4757",
            )

            locked_color = kwargs.get("locked_color_hex")
            if locked_color:
                self.color_swatch_overlay_label.config(bg=locked_color)
                
            dig_count = kwargs.get("dig_count", 0)
            click_count = kwargs.get("click_count", 0)
            # self.benchmark_label.config(text=f"BENCH: {benchmark_fps:<5} FPS")

            self.dig_label.config(text=f"DIGS: {dig_count}")
            self.clicks_label.config(text=f"CLICKS: {click_count}")

            is_pred = get_param(self.parent, "prediction_enabled")
            self.pred_label.config(
                text=f"PRED: {'ON' if is_pred else 'OFF'}",
                fg="#4ecdc4" if is_pred else "#ff4757",
            )
            self.latency_label.config(
                text=f"LAT: {get_cached_system_latency(self.parent)}ms"
            )

            bot_key = self.parent.keybind_vars["toggle_bot"].get().upper()
            gui_key = self.parent.keybind_vars["toggle_gui"].get().upper()
            ovl_key = self.parent.keybind_vars["toggle_overlay"].get().upper()

            self.toggle_bot_label.config(text=f"Bot: {bot_key}")
            self.toggle_gui_label.config(text=f"GUI: {gui_key}")
            self.toggle_overlay_label.config(text=f"Ovl: {ovl_key}")

            preview_thumbnail = kwargs.get("preview_thumbnail")
            if preview_thumbnail is not None and self.preview_label_overlay:
                try:
                    img = Image.fromarray(
                        cv2.cvtColor(preview_thumbnail, cv2.COLOR_BGR2RGB)
                    )
                    photo = ImageTk.PhotoImage(image=img)
                    self.preview_label_overlay.configure(image=photo)
                    self.preview_label_overlay.image = photo
                except Exception as e:
                    logger.debug(f"Error updating preview thumbnail: {e}")
        except Exception as e:
            logger.error(f"Error updating game overlay: {e}")

    def destroy_overlay(self):
        self.visible = False
        if self.overlay:
            try:
                self.overlay.destroy()
            except Exception:
                pass
            self.overlay = None


class AutoWalkOverlay:
    def __init__(self, parent):
        self.parent = parent
        self.overlay = None
        self.visible = False

        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False

    def create_overlay(self):
        if self.overlay:
            return

        try:
            self.overlay = tk.Toplevel()
            self.overlay.withdraw()
            self.overlay.title("Auto Walk Info")
            self.overlay.wm_overrideredirect(True)
            self.overlay.attributes("-topmost", True)
            self.overlay.attributes("-alpha", 0.9)
            self.overlay.configure(bg="black", bd=2, relief="solid")

            self.overlay.after_idle(self._setup_overlay_content)
        except Exception as e:
            logger.error(f"Error creating auto walk overlay: {e}")

    def _setup_overlay_content(self):
        try:
            icon = self.parent.settings_manager.load_icon("assets/icon.png", (16, 16))
            if icon:
                self.overlay.iconphoto(False, icon)

            self._create_overlay_widgets()
            self.position_overlay()

            self.overlay.after(50, self._apply_window_style)
            self.overlay.after(200, self._show_overlay)
        except Exception as e:
            logger.error(f"Error setting up auto walk overlay content: {e}")

    def _show_overlay(self):
        try:
            self.overlay.deiconify()
            self.visible = True
            logger.debug("Auto Walk overlay shown successfully")
        except Exception as e:
            logger.error(f"Error showing auto walk overlay: {e}")

    def _apply_window_style(self):
        try:
            hwnd = self.overlay.winfo_id()

            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~win32con.WS_MINIMIZEBOX
            style &= ~win32con.WS_MAXIMIZEBOX
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

        except Exception as e:
            logger.debug(f"Could not apply auto walk window style: {e}")

    def _create_overlay_widgets(self):
        self.title_frame = Frame(self.overlay, bg="black", cursor="fleur")
        self.title_frame.pack(fill="x", padx=2, pady=(2, 0))

        title_label = Label(
            self.title_frame,
            text="Auto Walk",
            fg="white",
            bg="black",
            font=("Consolas", 11, "bold"),
            cursor="fleur",
        )
        title_label.pack(pady=3)

        self.title_frame.bind("<Button-1>", self.start_drag)
        self.title_frame.bind("<B1-Motion>", self.on_drag)
        self.title_frame.bind("<ButtonRelease-1>", self.stop_drag)
        title_label.bind("<Button-1>", self.start_drag)
        title_label.bind("<B1-Motion>", self.on_drag)
        title_label.bind("<ButtonRelease-1>", self.stop_drag)

        self.canvas_frame = Frame(self.overlay, bg="black", relief="solid", bd=1)
        self.canvas_frame.pack(pady=5, padx=5, fill="x")

        self.pattern_name_label = Label(
            self.canvas_frame,
            text="PATTERN: None",
            fg="#00ff88",
            bg="black",
            font=("Consolas", 9, "bold"),
        )
        self.pattern_name_label.pack(pady=2)

        self.path_canvas = Canvas(
            self.canvas_frame, width=180, height=140, bg="#1a1a1a", highlightthickness=0
        )
        self.path_canvas.pack(pady=2, padx=2)

        speed_frame = Frame(self.overlay, bg="black")
        speed_frame.pack(pady=(2, 2), padx=5, fill="x")

        self.walkspeed_decrease_label = Label(
            speed_frame,
            text="SLOWDOWN: 0.0%",
            fg="#ff6b47",
            bg="black",
            font=("Consolas", 9, "bold"),
        )
        self.walkspeed_decrease_label.pack(expand=True)

        duration_frame = Frame(self.overlay, bg="black")
        duration_frame.pack(pady=(2, 2), padx=5, fill="x")

        self.duration_label = Label(
            duration_frame,
            text="DURATION: 0.500s",
            fg="#4ecdc4",
            bg="black",
            font=("Consolas", 9, "bold"),
        )
        self.duration_label.pack(expand=True)

        sell_frame = Frame(self.overlay, bg="black")
        sell_frame.pack(pady=(2, 5), padx=5, fill="x")

        self.autosell_label = Label(
            sell_frame,
            text="AUTO SELL: OFF",
            fg="#ffa726",
            bg="black",
            font=("Consolas", 9, "bold"),
        )
        self.autosell_label.pack(expand=True)

        self.current_step_index = 0
        self.update_path_visualization()

        self.position_overlay()

    def start_drag(self, event):
        if not self.overlay:
            return
        self.is_dragging = True
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root

    def on_drag(self, event):
        if not self.is_dragging or not self.overlay:
            return
        try:
            dx = event.x_root - self.drag_start_x
            dy = event.y_root - self.drag_start_y

            if abs(dx) < 1 and abs(dy) < 1:
                return

            x = self.overlay.winfo_x() + dx
            y = self.overlay.winfo_y() + dy

            self.overlay.geometry(f"+{x}+{y}")

            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
        except tk.TclError:
            pass

    def stop_drag(self, event):
        self.is_dragging = False

    def position_overlay(self):
        if not self.overlay or not self.parent.game_area:
            return
        x1, y1, x2, y2 = self.parent.game_area
        self.overlay.geometry(
            f"+{max(10, x1 - 200)}+{min(y1, self.parent.root.winfo_screenheight() - 300)}"
        )

    def update_info(self, **kwargs):
        if not self.visible or not self.overlay:
            return
        try:
            dig_count = kwargs.get("dig_count", 0)
            initial_items = get_param(self.parent, "initial_item_count") or 0
            total_items = dig_count + initial_items

            if get_param(self.parent, "dynamic_walkspeed_enabled"):
                formula_reduction = (
                    self.parent.automation_manager.calculate_walkspeed_multiplier(
                        total_items
                    )
                )
                initial_decrease = (
                    get_param(self.parent, "initial_walkspeed_decrease") or 0.0
                )
                total_reduction = min(formula_reduction + initial_decrease, 0.99)

                decrease_percentage = total_reduction * 100
                self.walkspeed_decrease_label.config(
                    text=f"SLOWDOWN: {decrease_percentage:.1f}%"
                )

                duration_multiplier = 1.0 + total_reduction
                base_duration = get_param(self.parent, "walk_duration") / 1000.0
                actual_duration = base_duration * duration_multiplier
                self.duration_label.config(text=f"DURATION: {actual_duration:.3f}s")
            else:
                self.walkspeed_decrease_label.config(text="SLOWDOWN: 0.0%")
                base_duration = get_param(self.parent, "walk_duration") / 1000.0
                self.duration_label.config(text=f"DURATION: {base_duration:.3f}s")

            self.update_pattern_name()

            self.update_path_visualization()

            automation_status = kwargs.get("automation_status", "STOPPED")
            is_walking = automation_status in [
                "WALKING"
            ] or automation_status.startswith("AUTO WALKING")
            if is_walking and not getattr(self, "_animation_running", False):
                self._animation_running = True
                self.animate_path_step()
            elif not is_walking:
                self._animation_running = False

            auto_sell_enabled = get_param(self.parent, "auto_sell_enabled")
            if auto_sell_enabled:
                dig_count = kwargs.get("dig_count", 0)
                sell_interval = get_param(self.parent, "sell_every_x_digs")
                if sell_interval and sell_interval > 0:
                    current_progress = dig_count % sell_interval
                    self.autosell_label.config(
                        text=f"AUTO SELL: {current_progress} / {sell_interval}"
                    )
                else:
                    self.autosell_label.config(text="AUTO SELL: 0 / 0")
            else:
                self.autosell_label.config(text="AUTO SELL: OFF")

        except Exception as e:
            logger.debug(f"Error updating auto walk overlay: {e}")

    def destroy_overlay(self):
        self.visible = False
        self._animation_running = False
        if self.overlay:
            try:
                self.overlay.destroy()
            except Exception:
                pass
            self.overlay = None

    def animate_path_step(self):
        if not hasattr(self, "path_canvas") or not self.path_canvas or not self.visible:
            return

        current_pattern = None
        if (
            hasattr(self.parent, "automation_manager")
            and self.parent.automation_manager
        ):
            current_pattern_name = getattr(self.parent, "walk_pattern_var", None)
            if current_pattern_name:
                pattern_name = current_pattern_name.get()
                pattern_info = self.parent.automation_manager.get_pattern_list()
                if pattern_name in pattern_info:
                    current_pattern = pattern_info[pattern_name]["pattern"]

        if current_pattern and len(current_pattern) > 0:
            if hasattr(self.parent, "automation_manager"):
                self.current_step_index = getattr(
                    self.parent.automation_manager, "walk_pattern_index", 0
                )

            self.update_path_visualization(highlight_step=self.current_step_index)

            automation_status = getattr(
                self.parent.automation_manager, "current_status", "STOPPED"
            )
            is_walking = automation_status in [
                "WALKING"
            ] or automation_status.startswith("AUTO WALKING")
            if (
                is_walking
                and self.visible
                and getattr(self, "_animation_running", False)
            ):
                self.overlay.after(200, self.animate_path_step)
            else:
                self._animation_running = False
        else:
            self._animation_running = False

    def update_pattern_name(self):
        if (
            not self.visible
            or not self.overlay
            or not hasattr(self, "pattern_name_label")
        ):
            return

        try:
            current_pattern = getattr(self.parent, "walk_pattern_var", None)
            if current_pattern:
                pattern_name = current_pattern.get()
                if pattern_name:
                    self.pattern_name_label.config(text=f"PATTERN: {pattern_name}")
                else:
                    self.pattern_name_label.config(text="PATTERN: None")
            else:
                self.pattern_name_label.config(text="PATTERN: None")
        except Exception:
            pass

    def update_path_visualization(self, highlight_step=None):
        if not hasattr(self, "path_canvas") or not self.path_canvas:
            return

        try:
            self.path_canvas.delete("all")

            current_pattern = None
            pattern_name = "unknown"

            if (
                hasattr(self.parent, "automation_manager")
                and self.parent.automation_manager
            ):
                current_pattern_name = getattr(self.parent, "walk_pattern_var", None)
                if current_pattern_name:
                    pattern_name = current_pattern_name.get()
                    pattern_info = self.parent.automation_manager.get_pattern_list()
                    if pattern_name in pattern_info:
                        current_pattern = pattern_info[pattern_name]["pattern"]

            if not current_pattern:
                self.path_canvas.create_text(
                    90, 70, text="NO PATTERN", fill="#666666", font=("Consolas", 10)
                )
                return

            canvas_width = 180
            canvas_height = 140
            center_x = canvas_width // 2
            center_y = canvas_height // 2

            scale = 12.0

            raw_points = [(0, 0)]
            x, y = 0, 0

            for step in current_pattern:
                dx, dy = self.get_direction_vector(step)
                x += dx * scale
                y += dy * scale
                raw_points.append((x, y))

            if len(raw_points) > 1:
                all_x = [point[0] for point in raw_points]
                all_y = [point[1] for point in raw_points]
                min_x, max_x = min(all_x), max(all_x)
                min_y, max_y = min(all_y), max(all_y)

                pattern_center_x = (min_x + max_x) / 2
                pattern_center_y = (min_y + max_y) / 2

                offset_x = center_x - pattern_center_x
                offset_y = center_y - pattern_center_y
            else:
                offset_x = offset_y = 0

            path_points = []
            for raw_x, raw_y in raw_points:
                final_x = raw_x + offset_x
                final_y = raw_y + offset_y
                path_points.append((final_x, final_y))

            if len(path_points) > 1:
                for i in range(len(path_points) - 1):
                    x1, y1 = path_points[i]
                    x2, y2 = path_points[i + 1]

                    if highlight_step is not None and i == highlight_step:
                        color = "#ffff00"
                        width = 4
                    elif highlight_step is not None and i < highlight_step:
                        color = "#00aa00"
                        width = 3
                    else:
                        progress = i / (len(path_points) - 1)
                        red_component = int(progress * 180 + 75)
                        green_component = int((1 - progress) * 180 + 75)
                        color = f"#{red_component:02x}{green_component:02x}00"
                        width = 2

                    self.path_canvas.create_line(
                        x1, y1, x2, y2, fill=color, width=width
                    )

                end_x, end_y = path_points[-1]
                self.path_canvas.create_oval(
                    end_x - 4,
                    end_y - 4,
                    end_x + 4,
                    end_y + 4,
                    fill="#ff0000",
                    outline="#ffffff",
                    width=2,
                )

                if (
                    highlight_step is not None
                    and 0 <= highlight_step < len(path_points) - 1
                ):
                    curr_x, curr_y = path_points[highlight_step]

                    self.path_canvas.create_oval(
                        curr_x - 5,
                        curr_y - 5,
                        curr_x + 5,
                        curr_y + 5,
                        fill="#ffff00",
                        outline="#ffffff",
                        width=2,
                    )

                if len(path_points) >= 2:
                    prev_x, prev_y = path_points[-2]
                    arrow_dx = end_x - prev_x
                    arrow_dy = end_y - prev_y
                    if arrow_dx != 0 or arrow_dy != 0:

                        length = math.sqrt(arrow_dx * arrow_dx + arrow_dy * arrow_dy)
                        if length > 0:
                            arrow_dx = (arrow_dx / length) * 8
                            arrow_dy = (arrow_dy / length) * 8
                            self.path_canvas.create_line(
                                end_x,
                                end_y,
                                end_x + arrow_dx,
                                end_y + arrow_dy,
                                fill="#ffffff",
                                width=2,
                                arrow=tk.LAST,
                            )

        except Exception as e:
            logger.debug(f"Error updating path visualization: {e}")

            self.path_canvas.delete("all")
            self.path_canvas.create_text(
                90, 70, text="RENDER ERROR", fill="#ff4444", font=("Consolas", 10)
            )

    def get_direction_vector(self, key):

        def extract_movement_keys(key_str):
            key_str = str(key_str).lower()

            if "+" in key_str:
                parts = [k.strip() for k in key_str.split("+")]
            else:
                parts = [key_str]

            movement_keys = []
            for part in parts:
                part = part.lower()

                if part in ["w", "a", "s", "d", "up", "down", "left", "right"]:
                    movement_keys.append(part)

            return movement_keys

        if isinstance(key, dict):
            key_str = key.get("key", "")
        else:
            key_str = str(key)

        movement_keys = extract_movement_keys(key_str)

        if not movement_keys:
            return (0, 0)

        dx, dy = 0, 0
        for movement_key in movement_keys:
            direction_map = {
                "w": (0, -1),  # Up
                "a": (-1, 0),  # Left
                "s": (0, 1),  # Down
                "d": (1, 0),  # Right
                "up": (0, -1),
                "down": (0, 1),
                "left": (-1, 0),
                "right": (1, 0),
            }

            d = direction_map.get(movement_key, (0, 0))
            dx += d[0]
            dy += d[1]

        if dx != 0 and dy != 0:
            factor = math.sqrt(2) / 2
            dx *= factor
            dy *= factor

        return (dx, dy)
