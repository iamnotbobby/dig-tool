import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import threading
import time

import sys


class CustomPatternWindow:
    def __init__(self, parent, automation_manager):
        self.parent = parent
        self.automation_manager = automation_manager
        self.window = None
        self.pattern_listbox = None
        self.preview_text = None
        self.recording_frame = None
        self.record_button = None
        self.azerty_record = None
        self.azerty_var = tk.BooleanVar(value=False)
        self.record_status = None
        self.recorded_display = None
        self.recorded_name_entry = None
        self.save_recorded_button = None
        self._update_running = False
        self._last_button_click = 0
        self._button_cooldown = 0.5

    def _check_button_cooldown(self):
        current_time = time.time()
        if current_time - self._last_button_click < self._button_cooldown:
            return False
        self._last_button_click = current_time
        return True

    def show_window(self):
        if self.window is not None:
            self.window.lift()
            return
        self.window = tk.Toplevel(self.parent)
        self.window.title("Custom Movement Patterns")
        self.window.geometry("900x700")
        self.window.resizable(True, True)

        self.window.wm_iconbitmap(os.path.join(sys._MEIPASS, "assets/icon.ico") if hasattr(sys, '_MEIPASS') else "assets/icon.ico")

        if hasattr(self.parent, 'attributes') and self.parent.attributes('-topmost'):
            self.window.attributes('-topmost', True)

        self.window.protocol("WM_DELETE_WINDOW", self.close_window)

        self.create_ui()
        self.refresh_pattern_list()

    def create_ui(self):
        style = ttk.Style()
        style.configure("Heading.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Title.TLabel", font=("Segoe UI", 12, "bold"))

        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="Custom Movement Patterns", style="Heading.TLabel")
        title_label.pack(pady=(0, 25))

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        left_pane = ttk.Frame(content_frame)
        left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))

        right_pane = ttk.Frame(content_frame)
        right_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._create_pattern_list(left_pane)
        self._create_preview_section(right_pane)
        self._create_recording_section(right_pane)

    def _create_pattern_list(self, parent):
        list_frame = ttk.LabelFrame(parent, text="Available Patterns", padding="15")
        list_frame.pack(fill=tk.BOTH, expand=True)

        listbox_container = ttk.Frame(list_frame)
        listbox_container.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        self.pattern_listbox = tk.Listbox(listbox_container, selectmode=tk.SINGLE,
                                          font=("Segoe UI", 11), activestyle='none')
        self.pattern_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.pattern_listbox.bind('<<ListboxSelect>>', self._on_pattern_select)
        self.pattern_listbox.bind('<Button-3>', self._show_context_menu)

        scrollbar = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL,
                                  command=self.pattern_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pattern_listbox.configure(yscrollcommand=scrollbar.set)

        buttons_frame = ttk.Frame(list_frame)
        buttons_frame.pack(fill=tk.X)

        button_width = 12
        ttk.Button(buttons_frame, text="Delete Selected", width=button_width,
                   command=self._safe_delete_pattern).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons_frame, text="Import Patterns", width=button_width,
                   command=self._safe_import_patterns).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons_frame, text="Refresh List", width=button_width,
                   command=self._safe_refresh).pack(side=tk.LEFT, padx=(8, 0))

    def _create_preview_section(self, parent):
        preview_frame = ttk.LabelFrame(parent, text="Pattern Preview", padding="15")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        preview_container = ttk.Frame(preview_frame)
        preview_container.pack(fill=tk.BOTH, expand=True)

        self.preview_text = tk.Text(preview_container, height=8, wrap=tk.WORD,
                                    state=tk.DISABLED, font=("Segoe UI", 10))
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        preview_scroll = ttk.Scrollbar(preview_container, orient=tk.VERTICAL,
                                       command=self.preview_text.yview)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_text.configure(yscrollcommand=preview_scroll.set)

    def _create_recording_section(self, parent):
        self.recording_frame = ttk.LabelFrame(parent, text="Record Live Pattern", padding="15")
        self.recording_frame.pack(fill=tk.BOTH, expand=True)

        instructions_text = tk.Text(self.recording_frame, height=5, wrap=tk.WORD,
                                    state=tk.DISABLED, font=("Segoe UI", 10))
        instructions_text.pack(fill=tk.X, pady=(0, 15))

        instructions_text.config(state=tk.NORMAL)
        instructions_text.insert(tk.END, "Recording Instructions:\n\n")
        instructions_text.insert(tk.END, "1. Click 'Start Recording'\n")
        instructions_text.insert(tk.END, "2. Use WASD keys to move your character (ZQSD keys if Azerty Mode is checked)\n")
        instructions_text.insert(tk.END, "3. Click 'Stop Recording' and save the pattern")
        instructions_text.config(state=tk.DISABLED)

        controls_frame = ttk.Frame(self.recording_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 15))

        self.record_button = ttk.Button(controls_frame, text="Start Recording",
                                        command=self._safe_toggle_recording)
        self.record_button.pack(side=tk.LEFT, padx=(0, 15))
        

        self.azerty_record = ttk.Checkbutton(controls_frame, variable=self.azerty_var, text="Azerty Mode")
        self.azerty_record.pack(side=tk.LEFT, padx=(0, 15))
        
        self.record_status = ttk.Label(controls_frame, text="Ready to record",
                                       font=("Segoe UI", 10))
        self.record_status.pack(side=tk.LEFT)

        ttk.Label(self.recording_frame, text="Recorded Pattern:",
                  style="Title.TLabel").pack(anchor=tk.W, pady=(15, 5))

        self.recorded_display = tk.Text(self.recording_frame, height=3, wrap=tk.WORD,
                                        state=tk.DISABLED, font=("Segoe UI", 10))
        self.recorded_display.pack(fill=tk.X, pady=(0, 15))

        save_frame = ttk.Frame(self.recording_frame)
        save_frame.pack(fill=tk.X)

        ttk.Label(save_frame, text="Pattern Name:", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 10))

        self.recorded_name_entry = ttk.Entry(save_frame, font=("Segoe UI", 10))
        self.recorded_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.save_recorded_button = ttk.Button(save_frame, text="Save Pattern",
                                               command=self._safe_save_pattern, state=tk.DISABLED)
        self.save_recorded_button.pack(side=tk.RIGHT)

    def _show_context_menu(self, event):
        try:
            selection = self.pattern_listbox.curselection()
            if not selection:
                return

            selected_text = self.pattern_listbox.get(selection[0])
            pattern_name = selected_text.split(' (')[0]

            pattern_info = self.automation_manager.get_pattern_list()
            if pattern_name not in pattern_info or pattern_info[pattern_name]['type'] == 'built-in':
                return

            context_menu = tk.Menu(self.window, tearoff=0)
            context_menu.add_command(label="Export Pattern",
                                     command=lambda name=pattern_name: self._safe_export_pattern(name))

            context_menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass
        finally:
            try:
                context_menu.grab_release()
            except:
                pass

    def _safe_export_pattern(self, pattern_name):
        if not self._check_button_cooldown():
            return

        try:
            pattern_info = self.automation_manager.get_pattern_list()
            if pattern_name not in pattern_info:
                messagebox.showerror("Error", "Pattern not found.")
                return

            pattern_data = {
                'name': pattern_name,
                'pattern': pattern_info[pattern_name]['pattern'],
                'type': 'custom',
                'exported_from': 'Dig Tool Custom Patterns',
                'version': '1.0'
            }

            filepath = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                title=f"Export Pattern: {pattern_name}"
            )

            if filepath:
                threading.Thread(target=self._export_pattern, args=(pattern_name, pattern_data, filepath), daemon=True).start()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export pattern: {str(e)}")

    def _export_pattern(self, pattern_name, pattern_data, filepath):
        try:
            if not filepath.lower().endswith('.json'):
                filepath += '.json'

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(pattern_data, f, indent=2, ensure_ascii=False)
            
            success_msg = f"Pattern '{pattern_name}' exported successfully!"
            self.window.after(0, lambda msg=success_msg: messagebox.showinfo("Success", msg))

        except Exception as e:
            error_msg = f"Failed to export pattern: {str(e)}"
            self.window.after(0, lambda msg=error_msg: messagebox.showerror("Error", msg))

    def _safe_import_patterns(self):
        if not self._check_button_cooldown():
            return

        filepath = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Import Pattern(s)"
        )

        if not filepath:
            return

        threading.Thread(target=self._import_patterns, args=(filepath,), daemon=True).start()

    def _import_patterns(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if self._is_single_pattern(data):
                self._import_single_pattern(data)
            else:
                self._import_multiple_patterns(data)

        except json.JSONDecodeError:
            self.window.after(0, lambda: messagebox.showerror("Error", "Invalid JSON file format."))
        except Exception as e:
            error_msg = f"Failed to import patterns: {str(e)}"
            self.window.after(0, lambda msg=error_msg: messagebox.showerror("Error", msg))

    def _is_single_pattern(self, data):
        return isinstance(data, dict) and 'name' in data and 'pattern' in data

    def _import_single_pattern(self, pattern_data):
        try:
            if not self._validate_pattern_data(pattern_data):
                return

            pattern_name = pattern_data['name'].strip()
            pattern = [move.lower().strip() for move in pattern_data['pattern']]

            existing_patterns = self.automation_manager.get_pattern_list()
            if pattern_name in existing_patterns:
                def ask_overwrite():
                    return messagebox.askyesno("Pattern Exists",
                                               f"Pattern '{pattern_name}' already exists. Overwrite it?")

                result = self.window.after_idle(ask_overwrite)
                if not result:
                    return

            success, message = self.automation_manager.add_custom_pattern(pattern_name, pattern)

            if success:
                success_msg = f"Pattern '{pattern_name}' imported successfully!"
                self.window.after(0, lambda: [
                    messagebox.showinfo("Success", success_msg),
                    self.refresh_pattern_list()
                ])
            else:
                error_msg = f"Failed to import pattern: {message}"
                self.window.after(0, lambda: messagebox.showerror("Error", error_msg))

        except Exception as e:
            error_msg = f"Failed to import pattern: {str(e)}"
            self.window.after(0, lambda: messagebox.showerror("Error", error_msg))

    def _import_multiple_patterns(self, patterns_data):
        try:
            if not isinstance(patterns_data, dict):
                self.window.after(0, lambda: messagebox.showerror("Error", "Invalid patterns file format."))
                return

            loaded_count = 0
            errors = []

            for pattern_name, pattern in patterns_data.items():
                try:
                    if isinstance(pattern, list):
                        valid_moves = {'w', 'a', 's', 'd'}
                        if all(move.lower().strip() in valid_moves for move in pattern):
                            cleaned_pattern = [move.lower().strip() for move in pattern]
                            success, message = self.automation_manager.add_custom_pattern(pattern_name, cleaned_pattern)
                            if success:
                                loaded_count += 1
                            else:
                                errors.append(f"{pattern_name}: {message}")
                        else:
                            errors.append(f"{pattern_name}: Invalid moves (only W, A, S, D allowed)")
                    else:
                        errors.append(f"{pattern_name}: Invalid pattern format")
                except Exception as e:
                    errors.append(f"{pattern_name}: {str(e)}")

            self.window.after(0, lambda: self._show_import_results(loaded_count, errors))

        except Exception as e:
            error_msg = f"Failed to import patterns: {str(e)}"
            self.window.after(0, lambda: messagebox.showerror("Error", error_msg))

    def _show_import_results(self, loaded_count, errors):
        try:
            if loaded_count > 0:
                self.refresh_pattern_list()

            if errors:
                error_message = f"Imported {loaded_count} patterns successfully.\n\nErrors:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    error_message += f"\n... and {len(errors) - 10} more errors"
                messagebox.showwarning("Import Complete with Errors", error_message)
            else:
                messagebox.showinfo("Success", f"Successfully imported {loaded_count} patterns!")

        except Exception:
            pass

    def _validate_pattern_data(self, pattern_data):
        if not isinstance(pattern_data, dict):
            self.window.after(0, lambda: messagebox.showerror("Error", "Invalid pattern file format."))
            return False

        required_fields = ['name', 'pattern']
        missing_fields = [field for field in required_fields if field not in pattern_data]
        if missing_fields:
            missing_str = ', '.join(missing_fields)
            self.window.after(0, lambda: messagebox.showerror("Error", f"Missing required fields: {missing_str}"))
            return False

        pattern = pattern_data['pattern']
        if not isinstance(pattern, list) or not pattern:
            self.window.after(0, lambda: messagebox.showerror("Error", "Invalid pattern data."))
            return False

        valid_moves = {'w', 'a', 's', 'd'}
        invalid_moves = [move for move in pattern if move.lower().strip() not in valid_moves]
        if invalid_moves:
            invalid_str = ', '.join(invalid_moves)
            self.window.after(0, lambda: messagebox.showerror("Error",
                                                              f"Invalid moves found: {invalid_str}. Only W, A, S, D are allowed."))
            return False

        return True

    def _safe_refresh(self):
        if not self._check_button_cooldown():
            return
        self.refresh_pattern_list()

    def refresh_pattern_list(self):
        try:
            if not self.pattern_listbox:
                return

            current_selection = None
            selection = self.pattern_listbox.curselection()
            if selection:
                current_selection = self.pattern_listbox.get(selection[0])

            self.pattern_listbox.delete(0, tk.END)
            pattern_info = self.automation_manager.get_pattern_list()

            for name, info in sorted(pattern_info.items()):
                pattern_type = info['type']
                length = info['length']
                display_text = f"{name} ({pattern_type}, {length} moves)"
                self.pattern_listbox.insert(tk.END, display_text)

                if current_selection == display_text:
                    self.pattern_listbox.selection_set(tk.END)

        except Exception:
            pass

    def _on_pattern_select(self, event):
        try:
            selection = self.pattern_listbox.curselection()
            if not selection:
                return

            selected_text = self.pattern_listbox.get(selection[0])
            pattern_name = selected_text.split(' (')[0]

            pattern_info = self.automation_manager.get_pattern_list()
            if pattern_name not in pattern_info:
                return

            info = pattern_info[pattern_name]
            pattern = info['pattern']
            pattern_type = info['type']

            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)

            self.preview_text.insert(tk.END, f"Pattern Name: {pattern_name}\n")
            self.preview_text.insert(tk.END, f"Type: {pattern_type.title()}\n")
            self.preview_text.insert(tk.END, f"Total Moves: {len(pattern)}\n\n")
            self.preview_text.insert(tk.END, f"Movement Sequence:\n{' → '.join(pattern).upper()}\n\n")

            if pattern_type == 'custom':
                self.preview_text.insert(tk.END, "Right-click to export this pattern")
            else:
                self.preview_text.insert(tk.END, "Built-in pattern (cannot be exported)")

            self.preview_text.config(state=tk.DISABLED)

        except Exception:
            pass

    def _safe_delete_pattern(self):
        if not self._check_button_cooldown():
            return

        try:
            selection = self.pattern_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a pattern to delete.")
                return

            selected_text = self.pattern_listbox.get(selection[0])
            pattern_name = selected_text.split(' (')[0]

            if messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete the pattern '{pattern_name}'?"):
                success, message = self.automation_manager.delete_custom_pattern(pattern_name)

                if success:
                    messagebox.showinfo("Success", message)
                    self.refresh_pattern_list()
                    self._clear_preview()
                else:
                    messagebox.showerror("Error", message)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete pattern: {str(e)}")

    def _clear_preview(self):
        try:
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.config(state=tk.DISABLED)
        except Exception:
            pass

    def _safe_toggle_recording(self):
        if not self._check_button_cooldown():
            return

        try:
            if not self.automation_manager.is_recording:
                self._start_recording()
            else:
                self._stop_recording()
        except Exception as e:
            messagebox.showerror("Error", f"Recording error: {str(e)}")

    def _start_recording(self):

        self.automation_manager.start_recording_pattern(azerty_mode=self.azerty_var.get())
        self.record_button.config(text="Stop Recording")
        keys = "WASD" if not self.azerty_var.get() else "ZQSD"            
        self.record_status.config(text=f"Recording... Use {keys} to move")
        self._update_running = True
        self._update_recorded_display()

    def _stop_recording(self):
        self._update_running = False
        recorded_pattern = self.automation_manager.stop_recording_pattern()
        self.record_button.config(text="Start Recording")
        self.record_status.config(text="Recording stopped")

        if recorded_pattern:
            self.save_recorded_button.config(state=tk.NORMAL)
            self._display_recorded_pattern(recorded_pattern)
        else:
            messagebox.showinfo("Info", "No movements were recorded.")

    def _update_recorded_display(self):
        if not self._update_running or not self.automation_manager.is_recording:
            return

        try:
            pattern = self.automation_manager.recorded_pattern
            move_count = len(pattern)

            self.recorded_display.config(state=tk.NORMAL)
            self.recorded_display.delete(1.0, tk.END)

            if pattern:
                self.recorded_display.insert(tk.END, ' → '.join(pattern).upper())
            else:
                self.recorded_display.insert(tk.END, "No moves recorded yet...")

            self.recorded_display.config(state=tk.DISABLED)
            self.record_status.config(text=f"Recording... {move_count} moves")

            if self._update_running:
                self.window.after(300, self._update_recorded_display)

        except Exception:
            pass

    def _display_recorded_pattern(self, pattern):
        try:
            self.recorded_display.config(state=tk.NORMAL)
            self.recorded_display.delete(1.0, tk.END)
            self.recorded_display.insert(tk.END, ' → '.join(pattern).upper())
            self.recorded_display.config(state=tk.DISABLED)
        except Exception:
            pass

    def _safe_save_pattern(self):
        if not self._check_button_cooldown():
            return

        try:
            name = self.recorded_name_entry.get().strip()

            if not name:
                messagebox.showerror("Error", "Please enter a name for the recorded pattern.")
                return

            if not self._validate_pattern_name(name):
                return

            recorded_text = self.recorded_display.get(1.0, tk.END).strip()
            if not recorded_text or recorded_text == "No moves recorded yet...":
                messagebox.showerror("Error", "No pattern recorded.")
                return

            pattern = [move.lower() for move in recorded_text.split(' → ')]

            success, message = self.automation_manager.add_custom_pattern(name, pattern)

            if success:
                messagebox.showinfo("Success", message)
                self._clear_recording_ui()
                self.refresh_pattern_list()
            else:
                messagebox.showerror("Error", message)

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
        try:
            self.recorded_name_entry.delete(0, tk.END)
            self.recorded_display.config(state=tk.NORMAL)
            self.recorded_display.delete(1.0, tk.END)
            self.recorded_display.config(state=tk.DISABLED)
            self.save_recorded_button.config(state=tk.DISABLED)
            self.record_status.config(text="Ready to record")
        except Exception:
            pass

    def close_window(self):
        try:
            self._update_running = False

            if hasattr(self.automation_manager, 'is_recording') and self.automation_manager.is_recording:
                self.automation_manager.stop_recording_pattern()

            if self.window:
                self.window.destroy()
                self.window = None

        except Exception:
            pass