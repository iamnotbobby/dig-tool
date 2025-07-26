import tkinter as tk
from tkinter import ttk, messagebox
import threading
from utils.debug_logger import logger


class PreviewManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def _safe_preview_pattern(self):
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
                messagebox.showwarning("No Selection", "Please select a pattern to preview.")
                return

            selected_text = self.main_window.pattern_listbox.get(selection[0])
            pattern_name = selected_text.split(' (')[0]
            
            self._preview_pattern_by_name(pattern_name)

        except Exception as e:
            self._update_preview_button_states(False)
            messagebox.showerror("Error", f"Failed to preview pattern: {str(e)}")

    def _preview_pattern_by_name(self, pattern_name):
        try:
            message = (f"Preview pattern '{pattern_name}'?\n\n"
                      f"This will:\n"
                      f"• Focus the Roblox window\n"
                      f"• Execute the pattern once\n"
                      f"• Each step will be performed with brief pauses\n\n"
                      f"Make sure you're ready to move in Roblox!")
            
            if not messagebox.askyesno("Preview Pattern", message):
                return

            self._update_preview_button_states(True)

            def run_preview():
                try:
                    success, message = self.main_window.automation_manager.preview_pattern(pattern_name)
                    
                    def update_ui():
                        self._update_preview_button_states(False)
                        if success:
                            messagebox.showinfo("Preview Complete", message)
                        else:
                            messagebox.showerror("Preview Failed", message)
                    
                    self.main_window._safe_schedule_ui_update(0, update_ui)
                    
                except Exception as e:
                    def show_error():
                        self._update_preview_button_states(False)
                        messagebox.showerror("Preview Error", f"Unexpected error during preview: {str(e)}")
                    self.main_window._safe_schedule_ui_update(0, show_error)

            self.main_window._preview_thread = threading.Thread(target=run_preview, daemon=True)
            self.main_window._preview_thread.start()

        except Exception as e:
            self._update_preview_button_states(False)
            messagebox.showerror("Error", f"Failed to preview pattern: {str(e)}")

    def _safe_preview_recorded_pattern(self):
        if not self.main_window._check_button_cooldown():
            return

        try:
            if not hasattr(self.main_window, 'automation_manager') or not self.main_window.automation_manager:
                messagebox.showerror("Error", "Automation manager not available")
                return
                
            recorded_pattern = getattr(self.main_window.automation_manager, 'recorded_pattern', [])
            if not recorded_pattern:
                messagebox.showwarning("No Pattern", "No recorded pattern to preview. Record some steps first.")
                return

            pattern_keys = []
            for step in recorded_pattern:
                if isinstance(step, dict):
                    pattern_keys.append(step.get('key', ''))
                else:
                    pattern_keys.append(str(step))

            if not pattern_keys:
                messagebox.showwarning("No Pattern", "Recorded pattern is empty.")
                return

            message = (f"Preview Recorded Pattern\n\n"
                      f"Pattern: {' → '.join(pattern_keys[:10])}"
                      f"{'...' if len(pattern_keys) > 10 else ''}\n"
                      f"Steps: {len(pattern_keys)}\n\n"
                      f"This will:\n"
                      f"• Focus the Roblox window\n"
                      f"• Execute the recorded pattern once\n"
                      f"• Each step will be performed with brief pauses\n\n"
                      f"Make sure you're ready to move in Roblox!")
            
            if not messagebox.askyesno("Preview Recorded Pattern", message):
                return

            self._update_preview_button_states(True)

            def run_preview():
                try:
                    success, message = self.main_window.automation_manager.preview_recorded_pattern(recorded_pattern)
                    
                    def update_ui():
                        self._update_preview_button_states(False)
                        if success:
                            messagebox.showinfo("Preview Complete", message)
                        else:
                            messagebox.showerror("Preview Failed", message)
                    
                    self.main_window._safe_schedule_ui_update(0, update_ui)
                    
                except Exception as e:
                    def show_error():
                        self._update_preview_button_states(False)
                        messagebox.showerror("Preview Error", f"Unexpected error during preview: {str(e)}")
                    self.main_window._safe_schedule_ui_update(0, show_error)

            self.main_window._preview_thread = threading.Thread(target=run_preview, daemon=True)
            self.main_window._preview_thread.start()

        except Exception as e:
            self._update_preview_button_states(False)
            messagebox.showerror("Error", f"Failed to preview recorded pattern: {str(e)}")

    def _stop_preview(self):
        if not self.main_window._check_button_cooldown():
            return
            
        try:
            if hasattr(self.main_window.automation_manager, 'stop_preview'):
                success, message = self.main_window.automation_manager.stop_preview()
                if success:
                    self._update_preview_button_states(False)
                    messagebox.showinfo("Preview Stopped", message)
                else:
                    messagebox.showerror("Error", f"Failed to stop preview: {message}")
            else:
                messagebox.showwarning("Not Available", "Stop preview functionality not available")
        except Exception as e:
            messagebox.showerror("Error", f"Error stopping preview: {str(e)}")

    def _update_preview_button_states(self, is_preview_running):
        try:
            if hasattr(self.main_window, 'preview_button') and self.main_window.preview_button:
                self.main_window.preview_button.configure(state=tk.DISABLED if is_preview_running else tk.NORMAL)
            if hasattr(self.main_window, 'stop_preview_button') and self.main_window.stop_preview_button:
                self.main_window.stop_preview_button.configure(state=tk.NORMAL if is_preview_running else tk.DISABLED)
                
            if hasattr(self.main_window, 'preview_recorded_button') and self.main_window.preview_recorded_button:
                current_state = str(self.main_window.preview_recorded_button['state'])
                if not is_preview_running and current_state != 'disabled':
                    self.main_window.preview_recorded_button.configure(state=tk.NORMAL)
                elif is_preview_running:
                    self.main_window.preview_recorded_button.configure(state=tk.DISABLED)
                    
            if hasattr(self.main_window, 'stop_recorded_preview_button') and self.main_window.stop_recorded_preview_button:
                self.main_window.stop_recorded_preview_button.configure(state=tk.NORMAL if is_preview_running else tk.DISABLED)
                
        except tk.TclError:
            return
        except Exception as e:
            logger.error(f"Error updating preview button states: {e}")
