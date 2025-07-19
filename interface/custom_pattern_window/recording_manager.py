import tkinter as tk
from tkinter import ttk, messagebox
from utils.debug_logger import logger
from utils.pattern_utils import validate_step_input


class RecordingManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def _safe_toggle_recording(self):
        if not self.main_window._check_button_cooldown():
            return

        try:
            if not self.main_window.automation_manager.is_recording:
                self._start_recording()
            else:
                self._stop_recording()
        except Exception as e:
            messagebox.showerror("Error", f"Recording error: {str(e)}")

    def _start_recording(self):
        allow_custom_keys = False
        if hasattr(self.main_window, 'custom_keys_var') and self.main_window.custom_keys_var:
            try:
                allow_custom_keys = self.main_window.custom_keys_var.get()
            except:
                allow_custom_keys = False
                
        click_enabled = True
                
        self.main_window.automation_manager.start_recording_pattern(allow_custom_keys=allow_custom_keys, 
                                                       click_enabled=click_enabled)
        
        if hasattr(self.main_window, 'record_button') and self.main_window.record_button:
            self.main_window.record_button.config(text="⏹ Stop")
        if hasattr(self.main_window, 'record_status') and self.main_window.record_status:
            if allow_custom_keys:
                self.main_window.record_status.config(text="● Recording... Use any keys to move & click", foreground="red")
            else:
                self.main_window.record_status.config(text="● Recording... Use WASD to move & click", foreground="red")
        self.main_window._update_running = True
        self._update_recorded_display()

    def _stop_recording(self):
        self.main_window._update_running = False
        recorded_pattern = self.main_window.automation_manager.stop_recording_pattern()
        if hasattr(self.main_window, 'record_button') and self.main_window.record_button:
            self.main_window.record_button.config(text="● Start")
        if hasattr(self.main_window, 'record_status') and self.main_window.record_status:
            self.main_window.record_status.config(text="✓ Recording stopped", foreground="green")

        if recorded_pattern:
            self.main_window._current_pattern = recorded_pattern.copy()
            self.main_window.automation_manager.recorded_pattern = recorded_pattern.copy()
            
            if hasattr(self.main_window, 'save_recorded_button') and self.main_window.save_recorded_button:
                self.main_window.save_recorded_button.config(state=tk.NORMAL)
            if hasattr(self.main_window, 'preview_recorded_button') and self.main_window.preview_recorded_button:
                self.main_window.preview_recorded_button.config(state=tk.NORMAL)
            if hasattr(self.main_window, 'clear_button') and self.main_window.clear_button:
                self.main_window.clear_button.config(state=tk.NORMAL)
            self.main_window.pattern_display._display_recorded_pattern_blocks(recorded_pattern, is_recording=False)
        
            if hasattr(self.main_window, 'record_status') and self.main_window.record_status:
                self.main_window.record_status.config(text="✓ Pattern ready to save!", foreground="blue")
        else:
            messagebox.showinfo("Info", "No movements were recorded.")

    def _clear_pattern(self):
        if not self.main_window._check_button_cooldown():
            return
        
        try:
            self.main_window.automation_manager.recorded_pattern = []
            self.main_window._current_pattern = []
            
            self.main_window.pattern_display._show_empty_pattern_state()
            
            if hasattr(self.main_window, 'save_recorded_button') and self.main_window.save_recorded_button:
                self.main_window.save_recorded_button.config(state=tk.DISABLED)
            
            if hasattr(self.main_window, 'preview_recorded_button') and self.main_window.preview_recorded_button:
                self.main_window.preview_recorded_button.config(state=tk.DISABLED)
            
            if hasattr(self.main_window, 'clear_button') and self.main_window.clear_button:
                self.main_window.clear_button.config(state=tk.DISABLED)
            
            if hasattr(self.main_window, 'recorded_name_entry') and self.main_window.recorded_name_entry:
                self.main_window.recorded_name_entry.delete(0, tk.END)
            
            self.main_window._previous_pattern_length = 0
            self.main_window._last_displayed_length = 0
            
            if hasattr(self.main_window, 'record_status') and self.main_window.record_status:
                self.main_window.record_status.config(text="✕ Pattern cleared - Ready to record", foreground="black")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear pattern: {str(e)}")

    def _update_recorded_display(self):
        if not self.main_window._update_running or not self.main_window.automation_manager.is_recording:
            return

        pattern = self.main_window.automation_manager.recorded_pattern
        move_count = len(pattern)
        
        self.main_window._current_pattern = pattern.copy()
        
        current_length = len(pattern)
        if current_length != getattr(self.main_window, '_last_displayed_length', 0):
            if pattern:
                self.main_window.pattern_display._display_recorded_pattern_blocks(pattern, is_recording=True)
            else:
                self.main_window.pattern_display._show_empty_pattern_state()
            
            self.main_window._last_displayed_length = current_length
        
        if hasattr(self.main_window, 'record_status') and self.main_window.record_status:
            self.main_window.record_status.config(text=f"● Recording... {move_count} moves", foreground="red")

        if self.main_window._update_running:
            self.main_window.window.after(200, self._update_recorded_display)

    def _safe_save_pattern(self):
        if not self.main_window._check_button_cooldown():
            return

        if not self.main_window._validate_ui_state('recorded_name_entry'):
            return
            
        try:
            self.main_window.recorded_name_entry.winfo_exists()
        except tk.TclError:
            return

        try:
            name = self.main_window.recorded_name_entry.get().strip()

            if not name:
                messagebox.showerror("Error", "Please enter a name for the recorded pattern.")
                return

            if not self._validate_pattern_name(name):
                return

            pattern = self.main_window._current_pattern.copy()
            if not pattern:
                messagebox.showerror("Error", "No pattern recorded.")
                return

            success, message = self.main_window.automation_manager.save_pattern(name, pattern)

            if success:
                messagebox.showinfo("Success", message)
                self._clear_recording_ui()
                self.main_window.refresh_pattern_list()
                self.main_window.switch_to_patterns_tab()
            else:
                messagebox.showerror("Error", message)

        except tk.TclError:
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save pattern: {str(e)}")

    def _validate_pattern_name(self, name):
        if len(name) > 50:
            messagebox.showerror("Error", "Pattern name too long (max 50 characters).")
            return False

        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in name for char in invalid_chars):
            invalid_chars_str = ', '.join(invalid_chars)
            messagebox.showerror("Error", f"Pattern name contains invalid characters: {invalid_chars_str}")
            return False

        return True

    def _clear_recording_ui(self):
        if hasattr(self.main_window, 'recorded_name_entry') and self.main_window.recorded_name_entry:
            self.main_window.recorded_name_entry.delete(0, tk.END)
        self.main_window.pattern_display._show_empty_pattern_state()
        if hasattr(self.main_window, 'save_recorded_button') and self.main_window.save_recorded_button:
            self.main_window.save_recorded_button.config(state=tk.DISABLED)
        if hasattr(self.main_window, 'clear_button') and self.main_window.clear_button:
            self.main_window.clear_button.config(state=tk.DISABLED)
        if hasattr(self.main_window, 'record_status') and self.main_window.record_status:
            self.main_window.record_status.config(text="Ready to record", foreground="black")

    def _on_custom_keys_changed(self):
        if hasattr(self.main_window, 'custom_keys_var') and self.main_window.custom_keys_var:
            allow_custom_keys = self.main_window.custom_keys_var.get()
            
            if hasattr(self.main_window.automation_manager, 'update_custom_keys_setting'):
                self.main_window.automation_manager.update_custom_keys_setting(allow_custom_keys)
            
            if (hasattr(self.main_window, 'record_status') and self.main_window.record_status and 
                hasattr(self.main_window.automation_manager, 'is_recording') and self.main_window.automation_manager.is_recording):
                
                if allow_custom_keys:
                    self.main_window.record_status.config(text="● Recording... Use any keys to move & click", foreground="red")
                else:
                    self.main_window.record_status.config(text="● Recording... Use WASD to move & click", foreground="red")

    def _safe_add_manual_key(self):
        if not self.main_window._check_button_cooldown():
            return

        if not self.main_window._validate_ui_state('pattern_listbox'):
            return

        try:
            self.main_window.pattern_listbox.winfo_exists()
        except tk.TclError:
            return

        try:
            selection = self.main_window.pattern_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a pattern to add a manual key to.")
                return

            selected_text = self.main_window.pattern_listbox.get(selection[0])
            pattern_name = selected_text.split(' (')[0]

            pattern_info = self.main_window.automation_manager.get_pattern_list()
            if pattern_name not in pattern_info:
                messagebox.showerror("Error", "Pattern not found.")
                return

            info = pattern_info[pattern_name]
            if info['type'] != 'custom':
                messagebox.showerror("Error", "Can only add manual keys to custom patterns.")
                return

            self._show_add_manual_key_dialog(pattern_name)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to add manual key: {str(e)}")

    def _show_add_manual_key_dialog(self, pattern_name):
        dialog = tk.Toplevel(self.main_window.window)
        dialog.title("Add Manual Key")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.transient(self.main_window.window)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="Add Manual Key to Pattern", font=("Segoe UI", 12, "bold"))
        title_label.pack(pady=(0, 20))

        pattern_label = ttk.Label(main_frame, text=f"Pattern: {pattern_name}", font=("Segoe UI", 10))
        pattern_label.pack(pady=(0, 15))

        key_frame = ttk.LabelFrame(main_frame, text="Key/Combination", padding="10")
        key_frame.pack(fill=tk.X, pady=(0, 15))

        key_entry = ttk.Entry(key_frame, font=("Segoe UI", 11))
        key_entry.pack(fill=tk.X, pady=(5, 10))
        key_entry.focus()

        examples_label = ttk.Label(key_frame, text="Examples: W, A+D, SHIFT+W, CTRL+SPACE", 
                                  font=("Segoe UI", 9), foreground="#666666")
        examples_label.pack()

        duration_frame = ttk.LabelFrame(main_frame, text="Duration (ms)", padding="10")
        duration_frame.pack(fill=tk.X, pady=(0, 15))

        duration_entry = ttk.Entry(duration_frame, font=("Segoe UI", 11))
        duration_entry.pack(fill=tk.X, pady=(5, 10))

        duration_help = ttk.Label(duration_frame, text="Leave empty for default duration", 
                                 font=("Segoe UI", 9), foreground="#666666")
        duration_help.pack()

        click_frame = ttk.LabelFrame(main_frame, text="Click Behavior", padding="10")
        click_frame.pack(fill=tk.X, pady=(0, 20))

        click_var = tk.BooleanVar(value=True)
        click_checkbox = ttk.Checkbutton(click_frame, text="Enable clicking for this step", 
                                        variable=click_var)
        click_checkbox.pack(anchor="w", pady=(5, 10))

        click_help = ttk.Label(click_frame, text="When disabled, only key press without clicking", 
                              font=("Segoe UI", 9), foreground="#666666")
        click_help.pack(anchor="w")

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X)

        def add_key():
            key = key_entry.get().strip().upper()
            duration_text = duration_entry.get().strip()

            if not key or not validate_step_input(key):
                messagebox.showerror("Invalid Input", "Please enter a valid key (W, A, S, D, or combinations like W+A)")
                return

            duration = None
            if duration_text:
                try:
                    duration = int(duration_text)
                    if duration <= 0:
                        messagebox.showerror("Invalid Duration", "Duration must be a positive number")
                        return
                except ValueError:
                    messagebox.showerror("Invalid Duration", "Duration must be a number")
                    return

            new_step = {'key': key, 'duration': duration, 'click': click_var.get()}

            pattern_info = self.main_window.automation_manager.get_pattern_list()
            if pattern_name in pattern_info:
                current_pattern = pattern_info[pattern_name]['pattern'].copy()
                current_pattern.append(new_step)
                
                success, message = self.main_window.automation_manager.save_pattern(pattern_name, current_pattern)
                if success:
                    messagebox.showinfo("Success", f"Key '{key}' added to pattern '{pattern_name}'")
                    self.main_window.refresh_pattern_list()
                    self.main_window._refresh_pattern_list_with_selection()
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", f"Failed to add key: {message}")
            else:
                messagebox.showerror("Error", "Pattern not found")

        def cancel():
            dialog.destroy()

        button_container = ttk.Frame(buttons_frame)
        button_container.pack(anchor=tk.CENTER)

        add_btn = ttk.Button(button_container, text="Add Key", command=add_key, width=12)
        add_btn.pack(side=tk.LEFT, padx=(0, 10))

        cancel_btn = ttk.Button(button_container, text="Cancel", command=cancel, width=12)
        cancel_btn.pack(side=tk.LEFT)

        dialog.bind('<Return>', lambda e: add_key())
        dialog.bind('<Escape>', lambda e: cancel())
