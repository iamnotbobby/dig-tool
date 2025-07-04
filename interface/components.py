import tkinter as tk
from tkinter import Label, Frame, ttk
import win32gui, win32con
from PIL import Image, ImageTk
import cv2
from utils.debug_logger import logger


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
        self.tooltip_window.wm_attributes('-topmost', True)

        label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("Segoe UI", 9, "normal"), wraplength=300, padx=8, pady=6)
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
        self.configure(bg=parent.cget('bg'))
        self.text = text
        self.manager = manager
        self.bg_color = bg_color
        self.is_open = tk.BooleanVar(value=False)

        self.header_frame = Frame(self, bg="#dcdcdc")
        self.header_frame.pack(fill="x")

        self.toggle_button = ttk.Button(self.header_frame, text=f'+ {self.text}', command=self.toggle,
                                        style="Header.TButton")
        self.toggle_button.pack(fill="x", pady=2, padx=2)

        self.sub_frame = Frame(self, relief="solid", borderwidth=1, bg=self.bg_color)

    def toggle(self):
        if self.manager:
            self.manager.toggle(self)

    def open(self):
        if not self.is_open.get():
            self.sub_frame.pack(fill="x", pady=2, padx=2)
            self.toggle_button.configure(text=f'− {self.text}')
            self.is_open.set(True)

    def close(self):
        if self.is_open.get():
            self.sub_frame.pack_forget()
            self.toggle_button.configure(text=f'+ {self.text}')
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
            else:
                pane.close()
        self.dig_tool_instance.resize_for_content()


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
        if self.overlay: return
        
        try:
            self.overlay = tk.Toplevel()
            self.overlay.withdraw()
            self.overlay.title("Dig Info")
            self.overlay.wm_overrideredirect(True)
            self.overlay.attributes('-topmost', True)
            self.overlay.attributes('-alpha', 0.9)
            self.overlay.configure(bg='black', bd=2, relief='solid')

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
            
            # Delay applying window style to ensure window is ready
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
        self.title_frame = Frame(self.overlay, bg='#333333', cursor='fleur')
        self.title_frame.pack(fill='x', padx=2, pady=(2, 0))

        title_label = Label(self.title_frame, text="Dig Tool", fg='white', bg='#333333',
                            font=('Consolas', 11, 'bold'), cursor='fleur')
        title_label.pack(pady=3)

        self.title_frame.bind('<Button-1>', self.start_drag)
        self.title_frame.bind('<B1-Motion>', self.on_drag)
        self.title_frame.bind('<ButtonRelease-1>', self.stop_drag)
        title_label.bind('<Button-1>', self.start_drag)
        title_label.bind('<B1-Motion>', self.on_drag)
        title_label.bind('<ButtonRelease-1>', self.stop_drag)

        self.status_label = Label(self.overlay, text="STATUS: STOPPED", fg='red', bg='black',
                                  font=('Consolas', 10, 'bold'))
        self.status_label.pack(pady=(5, 5), padx=5, fill='x')

        self.target_label = Label(self.overlay, text="TARGET: ---", fg='red', bg='black', font=('Consolas', 10, 'bold'))
        self.target_label.pack(pady=(0, 5), padx=5, fill='x')

        self.swatch_frame = Frame(self.overlay, bg='black')
        swatch_label = Label(self.swatch_frame, text="LOCK:", fg='white', bg='black', font=('Consolas', 9))
        swatch_label.pack(side=tk.LEFT)
        
        self.color_swatch_overlay_label = Label(self.swatch_frame, text=" " * 10, bg='black', relief='solid', bd=1)
        self.color_swatch_overlay_label.pack(side=tk.LEFT, fill='x', expand=True, padx=5)
        self.swatch_frame.pack(pady=(0, 5), padx=5, fill='x')

        stats_frame = Frame(self.overlay, bg='black')
        stats_frame.pack(pady=2, padx=10, fill='x')

        self.spd_label = Label(stats_frame, text="SPD: 0", fg='cyan', bg='black', font=('Consolas', 9))
        self.spd_label.grid(row=0, column=0, sticky='w')
        
        self.clicks_label = Label(stats_frame, text="CLICKS: 0", fg='orange', bg='black', font=('Consolas', 9))
        self.clicks_label.grid(row=0, column=1, sticky='w', padx=10)

        self.pred_label = Label(stats_frame, text="PRED: ON", fg='cyan', bg='black', font=('Consolas', 9))
        self.pred_label.grid(row=1, column=0, sticky='w')
        
        self.latency_label = Label(stats_frame, text=f"LAT: {self.parent.get_cached_system_latency()}ms", fg='cyan',
                                   bg='black', font=('Consolas', 9))
        self.latency_label.grid(row=1, column=1, sticky='w', padx=10)

        key_frame = Frame(self.overlay, bg='black', pady=5)
        key_frame.pack(padx=10, fill='x')
        
        self.toggle_bot_label = Label(key_frame, text=f"Bot: {self.parent.keybind_vars['toggle_bot'].get()}", fg='gray',
                                      bg='black', font=('Consolas', 8))
        self.toggle_bot_label.pack(side=tk.LEFT, expand=True)
        
        self.toggle_gui_label = Label(key_frame, text=f"GUI: {self.parent.keybind_vars['toggle_gui'].get()}", fg='gray',
                                      bg='black', font=('Consolas', 8))
        self.toggle_gui_label.pack(side=tk.LEFT, expand=True)
        
        self.toggle_overlay_label = Label(key_frame, text=f"Ovl: {self.parent.keybind_vars['toggle_overlay'].get()}",
                                          fg='gray', bg='black', font=('Consolas', 8))
        self.toggle_overlay_label.pack(side=tk.LEFT, expand=True)

        self.preview_label_overlay = Label(self.overlay, bg='black')
        self.preview_label_overlay.pack(pady=(5, 5), padx=5, fill='both', expand=True)

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
            
            # Reduce threshold for better responsiveness
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
        if not self.overlay or not self.parent.game_area: return
        x1, y1, x2, y2 = self.parent.game_area
        self.overlay.geometry(f"+{x2 + 10}+{min(y1, self.parent.root.winfo_screenheight() - 400)}")

    def update_info(self, **kwargs):
        if not self.visible or not self.overlay: 
            return
        try:
            automation_status = kwargs.get('automation_status', 'STOPPED')
            if automation_status == "AUTO SELLING":
                self.status_label.config(text="STATUS: AUTO SELLING", fg='orange')
            elif automation_status == "WALKING":
                self.status_label.config(text="STATUS: WALKING", fg='yellow')
            elif automation_status == "AUTO WALKING":
                self.status_label.config(text="STATUS: AUTO WALKING", fg='lime')
            elif automation_status == "ACTIVE":
                self.status_label.config(text="STATUS: ACTIVE", fg='lime')
            else:
                self.status_label.config(text="STATUS: STOPPED", fg='red')

            target_engaged = kwargs.get('target_engaged', False)
            self.target_label.config(text=f"TARGET: {'LOCKED' if target_engaged else '---'}",
                                     fg='lime' if target_engaged else 'red')

            locked_color = kwargs.get('locked_color_hex')
            if locked_color:
                self.color_swatch_overlay_label.config(bg=locked_color)

            velocity = kwargs.get('velocity', 0)
            click_count = kwargs.get('click_count', 0)
            self.spd_label.config(text=f"SPD: {velocity:>5.0f}")
            self.clicks_label.config(text=f"CLICKS: {click_count:<5}")

            is_pred = self.parent.get_param('prediction_enabled')
            self.pred_label.config(text=f"PRED: {'ON' if is_pred else 'OFF'}", fg='lime' if is_pred else 'red')
            self.latency_label.config(text=f"LAT: {self.parent.get_cached_system_latency()}ms")

            bot_key = self.parent.keybind_vars['toggle_bot'].get().upper()
            gui_key = self.parent.keybind_vars['toggle_gui'].get().upper()
            ovl_key = self.parent.keybind_vars['toggle_overlay'].get().upper()
            
            self.toggle_bot_label.config(text=f"Bot: {bot_key}")
            self.toggle_gui_label.config(text=f"GUI: {gui_key}")
            self.toggle_overlay_label.config(text=f"Ovl: {ovl_key}")

            preview_thumbnail = kwargs.get('preview_thumbnail')
            if preview_thumbnail is not None and self.preview_label_overlay:
                try:
                    img = Image.fromarray(cv2.cvtColor(preview_thumbnail, cv2.COLOR_BGR2RGB))
                    photo = ImageTk.PhotoImage(image=img)
                    self.preview_label_overlay.configure(image=photo)
                    self.preview_label_overlay.image = photo
                except:
                    pass
        except:
            pass

    def destroy_overlay(self):
        self.visible = False
        if self.overlay:
            try:
                self.overlay.destroy()
            except Exception:
                pass
            self.overlay = None