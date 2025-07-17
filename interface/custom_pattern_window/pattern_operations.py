import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import threading
from utils.debug_logger import logger
from utils.pattern_utils import (validate_pattern_data, is_single_pattern, clean_pattern_data, 
                                process_pattern_steps)


class PatternOperations:
    def __init__(self, main_window):
        self.main_window = main_window

    def _get_auto_walk_patterns_info(self):
        try:
            auto_walk_dir = self.main_window.automation_manager.dig_tool.settings_manager.get_auto_walk_directory()
            patterns_file = os.path.join(auto_walk_dir, "custom_patterns.json")
            
            if os.path.exists(patterns_file):
                with open(patterns_file, 'r') as f:
                    patterns = json.load(f)
                return {
                    'file_exists': True,
                    'file_path': patterns_file,
                    'pattern_count': len(patterns),
                    'patterns': patterns
                }
            else:
                return {
                    'file_exists': False,
                    'file_path': patterns_file,
                    'pattern_count': 0,
                    'patterns': {}
                }
        except Exception as e:
            logger.error(f"Error reading Auto Walk patterns: {e}")
            return {
                'file_exists': False,
                'file_path': 'Error',
                'pattern_count': 0,
                'patterns': {},
                'error': str(e)
            }

    def refresh_pattern_list(self):
        if not self.main_window._validate_ui_state('pattern_listbox'):
            return
            
        try:
            self.main_window.pattern_listbox.winfo_exists()
        except tk.TclError:
            return
            
        try:
            current_selection = None
            selection = self.main_window.pattern_listbox.curselection()
            if selection:
                current_selection = self.main_window.pattern_listbox.get(selection[0])

            self.main_window.pattern_listbox.delete(0, tk.END)
            pattern_info = self.main_window.automation_manager.get_pattern_list()

            for name, info in sorted(pattern_info.items()):
                pattern_type = info['type']
                length = info['length']
                display_text = f"{name} ({pattern_type}, {length} moves)"
                self.main_window.pattern_listbox.insert(tk.END, display_text)

                if current_selection == display_text:
                    self.main_window.pattern_listbox.selection_set(tk.END)

            if not self.main_window.pattern_listbox.curselection() and self.main_window.pattern_listbox.size() > 0:
                self.main_window.pattern_listbox.selection_set(0)
                self._on_pattern_select(None)

        except tk.TclError:
            return
        except Exception:
            pass

    def _on_pattern_select(self, event=None):
        if not self.main_window._validate_ui_state('pattern_listbox'):
            return
            
        try:
            self.main_window.pattern_listbox.winfo_exists()
        except tk.TclError:
            return
            
        try:
            selection = self.main_window.pattern_listbox.curselection()
            if not selection:
                if hasattr(self.main_window, 'preview_button'):
                    self.main_window.preview_button.config(state=tk.DISABLED)
                if hasattr(self.main_window, 'add_manual_key_button'):
                    self.main_window.add_manual_key_button.config(state=tk.DISABLED)
                if hasattr(self.main_window, 'pattern_info_label'):
                    self.main_window.pattern_info_label.config(text="Select a pattern to view details", fg="gray")
                self.main_window.pattern_display._show_preview_pattern_blocks([])
                return

            selected_text = self.main_window.pattern_listbox.get(selection[0])
            pattern_name = selected_text.split(' (')[0]

            pattern_info = self.main_window.automation_manager.get_pattern_list()
            if pattern_name not in pattern_info:
                if hasattr(self.main_window, 'preview_button'):
                    self.main_window.preview_button.config(state=tk.DISABLED)
                if hasattr(self.main_window, 'add_manual_key_button'):
                    self.main_window.add_manual_key_button.config(state=tk.DISABLED)
                return

            info = pattern_info[pattern_name]
            pattern = info['pattern']
            pattern_type = info['type']

            self.main_window._current_pattern_name = pattern_name
            self.main_window._current_pattern_type = pattern_type
            
            if pattern:
                converted_pattern = []
                for step in pattern:
                    if isinstance(step, dict):
                        if 'click' not in step:
                            step['click'] = True  
                        converted_pattern.append(step)
                    elif isinstance(step, str):
                        converted_pattern.append({'key': step, 'duration': None, 'click': True})
                    else:
                        converted_pattern.append({'key': str(step), 'duration': None, 'click': True})
                self.main_window._current_pattern = converted_pattern
            else:
                self.main_window._current_pattern = []

            if hasattr(self.main_window, 'preview_button'):
                self.main_window.preview_button.config(state=tk.NORMAL)
            
            if hasattr(self.main_window, 'add_manual_key_button'):
                if pattern_type == 'custom':
                    self.main_window.add_manual_key_button.config(state=tk.NORMAL)
                else:
                    self.main_window.add_manual_key_button.config(state=tk.DISABLED)

            if hasattr(self.main_window, 'pattern_info_label'):
                info_text = f"📁 {pattern_name} • {pattern_type.title()} • {len(pattern)} moves"
                if pattern_type == 'custom':
                    info_text += " (Editable)"
                self.main_window.pattern_info_label.config(text=info_text, fg="black")

            self.main_window.pattern_display._show_preview_pattern_blocks(pattern)

        except Exception:
            if hasattr(self.main_window, 'preview_button'):
                self.main_window.preview_button.config(state=tk.DISABLED)
            if hasattr(self.main_window, 'add_manual_key_button'):
                self.main_window.add_manual_key_button.config(state=tk.DISABLED)
            pass

    def _safe_delete_pattern(self):
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
                messagebox.showwarning("Warning", "Please select a pattern to delete.")
                return

            selected_text = self.main_window.pattern_listbox.get(selection[0])
            pattern_name = selected_text.split(' (')[0]

            if messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete the pattern '{pattern_name}'?"):
                success, message = self.main_window.automation_manager.delete_custom_pattern(pattern_name)

                if success:
                    messagebox.showinfo("Success", message)
                    self.refresh_pattern_list()
                    self._clear_preview()
                else:
                    messagebox.showerror("Error", message)

        except tk.TclError:
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete pattern: {str(e)}")

    def _clear_preview(self):
        if not self.main_window._validate_ui_state('preview_pattern_frame'):
            return
            
        try:
            if hasattr(self.main_window, 'pattern_info_label'):
                self.main_window.pattern_info_label.config(text="Select a pattern to view details", fg="gray")
            
            self.main_window.pattern_display._show_preview_pattern_blocks([])
        except tk.TclError:
            pass
        except Exception:
            pass

    def _safe_export_pattern(self, pattern_name):
        if not self.main_window._check_button_cooldown():
            return

        try:
            pattern_info = self.main_window.automation_manager.get_pattern_list()
            if pattern_name not in pattern_info:
                messagebox.showerror("Error", "Pattern not found.")
                return

            pattern_data = {
                pattern_name: pattern_info[pattern_name]['pattern']
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
            self.main_window._safe_schedule_ui_update(0, lambda msg=success_msg: messagebox.showinfo("Success", msg))

        except Exception as e:
            error_msg = f"Failed to export pattern: {str(e)}"
            self.main_window._safe_schedule_ui_update(0, lambda msg=error_msg: messagebox.showerror("Error", msg))

    def _safe_import_patterns(self):
        if not self.main_window._check_button_cooldown():
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

            if is_single_pattern(data):
                logger.debug(f"Importing single pattern with metadata format: {data.get('name', 'unknown')}")
                self._import_single_pattern(data)
            else:
                logger.debug(f"Importing multiple patterns format with {len(data)} patterns")
                self._import_multiple_patterns(data)

        except json.JSONDecodeError:
            self.main_window._safe_schedule_ui_update(0, lambda: messagebox.showerror("Error", "Invalid JSON file format."))
        except Exception as e:
            error_msg = f"Failed to import patterns: {str(e)}"
            self.main_window._safe_schedule_ui_update(0, lambda msg=error_msg: messagebox.showerror("Error", msg))

    def _import_single_pattern(self, pattern_data):
        try:
            clean_data = clean_pattern_data(pattern_data)
            
            if not self._validate_pattern_data(clean_data):
                return

            pattern_name = clean_data['name'].strip()
            raw_pattern = clean_data['pattern']
            
            success, result = process_pattern_steps(raw_pattern)
            if not success:
                self.main_window._safe_schedule_ui_update(0, lambda: messagebox.showerror("Error", result))
                return
            
            pattern = result

            existing_patterns = self.main_window.automation_manager.get_pattern_list()
            if pattern_name in existing_patterns:
                def ask_overwrite():
                    if self.main_window.window and self.main_window.window.winfo_exists():
                        return messagebox.askyesno("Pattern Exists",
                                                   f"Pattern '{pattern_name}' already exists. Overwrite it?")
                    return False

                if not ask_overwrite():
                    return

            success, message = self.main_window.automation_manager.save_pattern(pattern_name, pattern)

            def show_result():
                try:
                    if not self.main_window.window or not self.main_window.window.winfo_exists():
                        return
                    
                    if success:
                        messagebox.showinfo("Success", f"Pattern '{pattern_name}' imported successfully!")
                        self.refresh_pattern_list()
                    else:
                        messagebox.showerror("Error", f"Failed to import pattern: {message}")
                except Exception:
                    pass

            if self.main_window.window and self.main_window.window.winfo_exists():
                self.main_window.window.after(100, show_result)

        except Exception as e:
            def show_error():
                try:
                    if self.main_window.window and self.main_window.window.winfo_exists():
                        messagebox.showerror("Error", f"Failed to import pattern: {str(e)}")
                except Exception:
                    pass
            
            self.main_window._safe_schedule_ui_update(100, show_error)

    def _import_multiple_patterns(self, patterns_data):
        try:
            if not isinstance(patterns_data, dict):
                self.main_window._safe_schedule_ui_update(0, lambda: messagebox.showerror("Error", "Invalid patterns file format."))
                return

            loaded_count = 0
            errors = []

            for pattern_name, pattern in patterns_data.items():
                try:
                    if isinstance(pattern, list):
                        success, result = process_pattern_steps(pattern)
                        if not success:
                            errors.append(f"{pattern_name}: {result}")
                            continue
                        
                        cleaned_pattern = result
                        
                        existing_patterns = self.main_window.automation_manager.get_pattern_list()
                        if pattern_name in existing_patterns:
                            errors.append(f"{pattern_name}: Pattern already exists (skipped)")
                            continue
                        
                        if cleaned_pattern:  
                            success, message = self.main_window.automation_manager.save_pattern(pattern_name, cleaned_pattern)
                            if success:
                                loaded_count += 1
                            else:
                                errors.append(f"{pattern_name}: {message}")
                    elif isinstance(pattern, dict) and "pattern" in pattern:
                        if not self._validate_pattern_data(pattern, lambda msg: errors.append(f"{pattern_name}: {msg}")):
                            continue
                            
                        raw_pattern = pattern['pattern']
                        success, result = process_pattern_steps(raw_pattern)
                        if not success:
                            errors.append(f"{pattern_name}: {result}")
                            continue
                        
                        cleaned_pattern = result
                        
                        existing_patterns = self.main_window.automation_manager.get_pattern_list()
                        if pattern_name in existing_patterns:
                            errors.append(f"{pattern_name}: Pattern already exists (skipped)")
                            continue
                        
                        if cleaned_pattern:
                            success, message = self.main_window.automation_manager.save_pattern(pattern_name, cleaned_pattern)
                            if success:
                                loaded_count += 1
                            else:
                                errors.append(f"{pattern_name}: {message}")
                    else:
                        errors.append(f"{pattern_name}: Invalid pattern format")
                except Exception as e:
                    errors.append(f"{pattern_name}: {str(e)}")

            self.main_window._safe_schedule_ui_update(0, lambda: self._show_import_results(loaded_count, errors))

        except Exception as e:
            error_msg = f"Failed to import patterns: {str(e)}"
            self.main_window._safe_schedule_ui_update(0, lambda: messagebox.showerror("Error", error_msg))

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
        def show_error(message):
            self.main_window._safe_schedule_ui_update(0, lambda: messagebox.showerror("Error", message))
        
        return validate_pattern_data(pattern_data, show_error)

    def _show_context_menu(self, event):
        try:
            selection = self.main_window.pattern_listbox.curselection()
            if not selection:
                return

            selected_text = self.main_window.pattern_listbox.get(selection[0])
            pattern_name = selected_text.split(' (')[0]

            context_menu = tk.Menu(self.main_window.window, tearoff=0)
            context_menu.add_command(label="Preview Pattern", command=lambda: self.main_window._safe_preview_pattern())
            context_menu.add_separator()
            context_menu.add_command(label="Export Pattern", command=lambda: self._safe_export_pattern(pattern_name))
            context_menu.add_separator()
            context_menu.add_command(label="Delete Pattern", command=lambda: self._safe_delete_pattern())
            
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

        except Exception:
            pass
