import tkinter as tk
from tkinter import ttk, messagebox
from utils.debug_logger import logger
from utils.pattern_utils import (get_step_colors, format_step_text, validate_step_input, 
                                safe_schedule_ui_update)


class PatternDisplay:
    def __init__(self, main_window):
        self.main_window = main_window

    def _on_recorded_canvas_resize(self, event):
        if event.widget == self.main_window.recorded_pattern_canvas:
            canvas_width = self.main_window.recorded_pattern_canvas.winfo_width()
            if canvas_width > 1:
                self.main_window.recorded_pattern_canvas.itemconfig(self.main_window.recorded_canvas_window, width=canvas_width)

    def _on_preview_canvas_resize(self, event):
        if event.widget == self.main_window.preview_canvas:
            canvas_width = self.main_window.preview_canvas.winfo_width()
            if canvas_width > 1:
                self.main_window.preview_canvas.itemconfig(self.main_window.preview_canvas_window, width=canvas_width)
        elif event.widget == self.main_window.preview_pattern_frame:
            self._update_preview_canvas_scroll_region()

    def _update_preview_canvas_scroll_region(self):
        try:
            self.main_window.preview_canvas.configure(scrollregion=self.main_window.preview_canvas.bbox("all"))
        except Exception:
            pass

    def _show_preview_pattern_blocks(self, pattern, force_refresh=False):
        try:
            for widget in self.main_window.preview_pattern_frame.winfo_children():
                widget.destroy()
            
            if not pattern:
                self.main_window.preview_empty_label = tk.Label(self.main_window.preview_pattern_frame, 
                                                  text="No pattern data available", 
                                                  font=("Segoe UI", 10, "italic"),
                                                  fg="gray", bg="#f8f9fa")
                self.main_window.preview_empty_label.pack(pady=50)
                self._update_preview_canvas_scroll_region()
                return
            
            self.main_window.preview_pattern_frame.update_idletasks()
            frame_width = self.main_window.preview_pattern_frame.winfo_width()
            if frame_width < 100:
                frame_width = 600
            
            blocks_per_row = 6
            for i, step in enumerate(pattern):
                row = i // blocks_per_row
                col = i % blocks_per_row
                block = self._create_pattern_block(step, i, self.main_window.preview_pattern_frame, animate=False, preview=True, pattern_type=getattr(self.main_window, '_current_pattern_type', 'custom'))
                if block:
                    block.grid(row=row, column=col, padx=5, pady=8, sticky="nsew")
            
            for c in range(blocks_per_row):
                self.main_window.preview_pattern_frame.grid_columnconfigure(c, weight=1, minsize=60)
            for r in range((len(pattern) + blocks_per_row - 1) // blocks_per_row):
                self.main_window.preview_pattern_frame.grid_rowconfigure(r, weight=0, minsize=60)
            
            self._update_preview_canvas_scroll_region()
            
            if force_refresh:
                self.main_window.preview_pattern_frame.update()
                self.main_window.preview_canvas.update()
            
        except Exception as e:
            for widget in self.main_window.preview_pattern_frame.winfo_children():
                widget.destroy()
            error_label = tk.Label(self.main_window.preview_pattern_frame, 
                                 text=f"Error displaying pattern: {str(e)}", 
                                 font=("Segoe UI", 10, "italic"),
                                 fg="red", bg="#f8f9fa")
            error_label.pack(pady=50)
            self._update_preview_canvas_scroll_region()

    def _create_pattern_block(self, step, index, parent, animate=False, preview=False, pattern_type='custom'):
        if isinstance(step, dict):
            key = step.get('key', '')
            duration = step.get('duration', None)
            click_enabled = step.get('click', True)
        else:
            key = str(step)
            duration = None
            click_enabled = True

        formatted_step = format_step_text(key)
        step_number = f"#{index+1}"
        is_combination = '+' in key
        text_length = len(formatted_step)

        if preview:
            if is_combination:
                step_width = max(95, text_length * 8 + 25)
            elif text_length > 4:
                step_width = max(85, text_length * 9 + 20)
            elif text_length > 2:
                step_width = 75
            else:
                step_width = 70
            step_height = 80
            main_font = ("Segoe UI", 11, "bold")
            number_font = ("Segoe UI", 7, "bold")
            duration_font = ("Segoe UI", 7)
        else:
            if is_combination:
                step_width = max(95, text_length * 8 + 25)
                main_font = ("Segoe UI", 7, "bold")
                duration_font = ("Segoe UI", 6)
            elif text_length > 4:
                step_width = max(85, text_length * 9 + 20)
                main_font = ("Segoe UI", 8, "bold")
                duration_font = ("Segoe UI", 6)
            elif text_length > 2:
                step_width = 75
                main_font = ("Segoe UI", 9, "bold")
                duration_font = ("Segoe UI", 6)
            else:
                step_width = 70
                main_font = ("Segoe UI", 10, "bold")
                duration_font = ("Segoe UI", 6)
            step_height = 75
            number_font = ("Segoe UI", 7)

        if preview:
            bg, border_color, hover_bg, text_shadow = get_step_colors(key)
        else:
            bg, fg, border_color, hover_bg = get_step_colors(key)

        if preview:
            f = tk.Frame(parent, bg=bg, width=step_width, height=step_height, relief="solid", bd=2, highlightbackground=border_color, highlightthickness=1)
            f.pack_propagate(False)
            inner_frame = tk.Frame(f, bg=bg, highlightbackground=text_shadow, highlightthickness=1, relief="raised", bd=1)
            inner_frame.pack(fill="both", expand=True, padx=1, pady=1)
            number_label = tk.Label(inner_frame, text=step_number, font=number_font, bg=bg, fg="#333333", justify="center")
            number_label.pack(pady=(3, 0))
            key_label = tk.Label(inner_frame, text=formatted_step, font=main_font, bg=bg, fg="#000000", justify="center")
            key_label.pack()
        else:
            f = tk.Frame(parent, width=step_width, height=step_height, bg=bg, relief="solid", borderwidth=1, highlightbackground=border_color, highlightthickness=1)
            f.pack_propagate(False)
            key_label = tk.Label(f, text=formatted_step, font=main_font, bg=bg, fg=fg, justify="center")
            key_label.pack(pady=(5, 0))
            number_label = tk.Label(f, text=step_number, font=number_font, bg=bg, fg=fg, justify="center")
            number_label.pack()

        info_parts = []
        if preview and pattern_type == 'built-in':
            info_text = "(default)"
            info_color = "#777777"
        else:
            if duration is not None:
                info_parts.append(f"{duration}ms")
            else:
                info_parts.append("default")
            if not click_enabled:
                info_parts.append("no-click")
            info_text = " | ".join(info_parts)
            if not click_enabled:
                info_color = "#cc0000"
            elif duration is not None:
                info_color = "#555555"
            else:
                info_color = "#777777" if preview else "#999999"

        if preview:
            info_label = tk.Label(inner_frame, text=info_text, font=duration_font, bg=bg, fg=info_color, justify="center")
            info_label.pack(pady=(0, 2))
        else:
            info_label = tk.Label(f, text=info_text, font=duration_font, bg=bg, fg=info_color, justify="center")
            info_label.pack(pady=(0, 2))

        if preview:
            if pattern_type == 'custom':
                def on_click(e):
                    self._edit_step_dialog(index, step, is_preview=True)
                def on_right_click(e):
                    self._show_preview_step_context_menu(e, index, step)
            else:
                def on_click(e):
                    self._show_pattern_info_dialog(step)
                def on_right_click(e):
                    pass
            def on_enter(e):
                f.config(bg=hover_bg, highlightbackground=text_shadow)
                inner_frame.config(bg=hover_bg)
                for child in inner_frame.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(bg=hover_bg)
            def on_leave(e):
                f.config(bg=bg, highlightbackground=border_color)
                inner_frame.config(bg=bg)
                for child in inner_frame.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(bg=bg)
            f.bind("<Button-1>", on_click)
            f.bind("<Button-3>", on_right_click)
            f.bind("<Enter>", on_enter)
            f.bind("<Leave>", on_leave)
            for child in [inner_frame] + list(inner_frame.winfo_children()):
                child.bind("<Button-1>", on_click)
                child.bind("<Button-3>", on_right_click)
                child.bind("<Enter>", on_enter)
                child.bind("<Leave>", on_leave)
        else:
            def on_click(e):
                current_pattern_name = getattr(self.main_window, '_current_pattern_name', None)
                if current_pattern_name:
                    self.main_window._pre_edit_pattern_name = current_pattern_name
                    self.main_window._pre_edit_pattern = self.main_window._current_pattern.copy() if hasattr(self.main_window, '_current_pattern') else []
                    self._show_preview_pattern_blocks(self.main_window._current_pattern)
                self._edit_step_dialog(index, step)
            def on_right_click(e):
                self._show_step_context_menu(e, index, step)
            def on_enter(e):
                f.config(bg=hover_bg)
                for child in f.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(bg=hover_bg)
            def on_leave(e):
                f.config(bg=bg)
                for child in f.winfo_children():
                    if isinstance(child, tk.Label):
                        child.config(bg=bg)
            f.bind("<Button-1>", on_click)
            f.bind("<Button-3>", on_right_click)
            f.bind("<Enter>", on_enter)
            f.bind("<Leave>", on_leave)
            for child in f.winfo_children():
                child.bind("<Button-1>", on_click)
                child.bind("<Button-3>", on_right_click)
                child.bind("<Enter>", on_enter)
                child.bind("<Leave>", on_leave)

        if animate:
            f.config(width=int(step_width * 0.7), height=int(step_height * 0.7))
            self._animate_block_entrance(f, step_width, step_height)
        return f

    def _animate_block_entrance(self, frame, target_width, target_height):
        try:
            current_width = frame.winfo_width()
            current_height = frame.winfo_height()
            
            if current_width >= target_width and current_height >= target_height:
                return
            
            step_width = max(1, (target_width - current_width) // 10)
            step_height = max(1, (target_height - current_height) // 10)
            
            new_width = min(target_width, current_width + step_width)
            new_height = min(target_height, current_height + step_height)
            
            frame.config(width=new_width, height=new_height)
            
            if new_width < target_width or new_height < target_height:
                self.main_window.window.after(20, lambda: self._animate_block_entrance(frame, target_width, target_height))
        except Exception:
            pass

    def _display_recorded_pattern_blocks(self, pattern, is_recording=False):
        try:
            for widget in self.main_window.recorded_pattern_frame.winfo_children():
                widget.destroy()
            
            if not pattern:
                self._show_empty_pattern_state()
                return
            
            animate_new_blocks = is_recording and (len(pattern) > getattr(self.main_window, '_previous_pattern_length', 0))
            
            for i, step in enumerate(pattern):
                animate_this_block = animate_new_blocks and i >= getattr(self.main_window, '_previous_pattern_length', 0)
                block = self._create_pattern_block(step, i, self.main_window.recorded_pattern_frame, animate=animate_this_block, preview=False)
                if block:
                    block.pack(side=tk.LEFT, padx=3, pady=8)
            
            self.main_window._previous_pattern_length = len(pattern)
            
            self.main_window.recorded_pattern_frame.update_idletasks()
            self._update_recorded_canvas_scroll_region()
            
            if is_recording:
                safe_schedule_ui_update(self.main_window.window, self._auto_scroll_to_latest, 10)
            else:
                safe_schedule_ui_update(self.main_window.window, lambda: self.main_window.recorded_pattern_canvas.yview_moveto(0.0), 10)

        except Exception as e:
            logger.error(f"Error displaying recorded pattern blocks: {e}")
            self._show_empty_pattern_state()

    def _update_recorded_canvas_scroll_region(self):
        self.main_window.recorded_pattern_frame.update_idletasks()

        canvas_width = max(self.main_window.recorded_pattern_canvas.winfo_width(), 400)
        if canvas_width > 1:
            self.main_window.recorded_pattern_canvas.itemconfig(self.main_window.recorded_canvas_window, width=canvas_width)
        
        self.main_window.recorded_pattern_frame.update_idletasks()
   
        frame_width = self.main_window.recorded_pattern_frame.winfo_reqwidth()
        frame_height = self.main_window.recorded_pattern_frame.winfo_reqheight()
        
        if frame_width > 0 and frame_height > 0:
            self.main_window.recorded_pattern_canvas.configure(scrollregion=(0, 0, frame_width + 20, frame_height + 20))
        else:
            self.main_window.recorded_pattern_canvas.configure(scrollregion=(0, 0, 0, 0))

    def _show_empty_pattern_state(self):
        for widget in self.main_window.recorded_pattern_frame.winfo_children():
            widget.destroy()
        
        empty_label = tk.Label(self.main_window.recorded_pattern_frame, 
                             text="No recorded steps yet\nStart recording to add pattern steps", 
                             font=("Segoe UI", 11),
                             fg="gray",
                             bg="#f8f9fa",
                             justify=tk.CENTER)
        empty_label.pack(expand=True, pady=20)
    
        self.main_window.recorded_pattern_frame.update_idletasks()
        self.main_window.recorded_pattern_canvas.configure(scrollregion=(0, 0, 0, 0))

    def _auto_scroll_to_latest(self):
        self.main_window.recorded_pattern_canvas.update_idletasks()
        self.main_window.recorded_pattern_canvas.yview_moveto(1.0)

    def _edit_step_dialog(self, index, current_step, is_preview=False):
        current_pattern_name = getattr(self.main_window, '_current_pattern_name', None)
        current_pattern = getattr(self.main_window, '_current_pattern', [])
        
        if is_preview and getattr(self.main_window, '_current_pattern_type', 'custom') != 'custom':
            return
        
        dialog = tk.Toplevel(self.main_window.window)
        dialog.title(f"Edit Step #{index+1}")
        dialog.geometry("450x600")
        dialog.resizable(False, False)
        dialog.transient(self.main_window.window)
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (600 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        def restore_display():
            if current_pattern_name and current_pattern:
                self.main_window._ensure_pattern_selected(current_pattern_name)
                if is_preview:
                    self._show_preview_pattern_blocks(current_pattern)
                else:
                    self._show_preview_pattern_blocks(current_pattern)
                self.main_window.window.update_idletasks()
        
        restore_display()
        
        def delayed_grab():
            try:
                dialog.grab_set()
            except:
                pass
        
        self.main_window.window.after(50, delayed_grab)
        
        self.main_window.window.after(100, lambda: restore_display() if current_pattern_name and current_pattern else None)
        
        def on_dialog_close():
            self._restore_pattern_selection_and_preview()
            dialog.destroy()
            
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        main_frame = ttk.Frame(dialog, padding="25")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(main_frame, text=f"Editing Step #{index+1}", font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=(0, 25))
        
        if isinstance(current_step, dict):
            current_key = current_step.get('key', '')
            current_duration = current_step.get('duration', None)
            current_click_enabled = current_step.get('click', True)
        else:
            current_key = str(current_step)
            current_duration = None
            current_click_enabled = True
        
        key_frame = ttk.LabelFrame(main_frame, text="Key/Combination", padding="15")
        key_frame.pack(fill=tk.X, pady=(0, 20))
        
        key_entry = ttk.Entry(key_frame, font=("Segoe UI", 12))
        key_entry.pack(fill=tk.X, pady=(5, 10))
        key_entry.insert(0, current_key)
        key_entry.focus()
        
        examples_label = ttk.Label(key_frame, text="Examples: w, a+d, shift+w, ctrl+space", 
                                  font=("Segoe UI", 9), foreground="#666666")
        examples_label.pack()
        
        duration_frame = ttk.LabelFrame(main_frame, text="Key Duration (ms)", padding="15")
        duration_frame.pack(fill=tk.X, pady=(0, 20))
        
        duration_entry = ttk.Entry(duration_frame, font=("Segoe UI", 12))
        duration_entry.pack(fill=tk.X, pady=(5, 10))
        if current_duration is not None:
            duration_entry.insert(0, str(current_duration))
        
        duration_help = ttk.Label(duration_frame, text="Leave empty to use default Key Duration setting", 
                                 font=("Segoe UI", 9), foreground="#666666")
        duration_help.pack()
        
        click_frame = ttk.LabelFrame(main_frame, text="Click Behavior", padding="15")
        click_frame.pack(fill=tk.X, pady=(0, 25))
        
        click_enabled_var = tk.BooleanVar(value=current_click_enabled)
        click_checkbox = ttk.Checkbutton(click_frame, text="Enable clicking for this step", 
                                        variable=click_enabled_var, 
                                        onvalue=True, offvalue=False)
        click_checkbox.pack(anchor="w", pady=(5, 10))
        
        click_help = ttk.Label(click_frame, text="When disabled, this step will only move without clicking", 
                              font=("Segoe UI", 9), foreground="#666666")
        click_help.pack(anchor="w")
        
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(15, 10))
        
        def save_changes():
            new_key = key_entry.get().strip().upper()
            duration_text = duration_entry.get().strip()
            
            if not new_key or not validate_step_input(new_key):
                messagebox.showerror("Invalid Input", "Please enter a valid key (W, A, S, D, or combinations like W+A)")
                return
            
            new_duration = None
            if duration_text:
                try:
                    new_duration = int(duration_text)
                    if new_duration <= 0:
                        messagebox.showerror("Invalid Duration", "Duration must be a positive number")
                        return
                except ValueError:
                    messagebox.showerror("Invalid Duration", "Duration must be a number")
                    return
            
            new_step = {'key': new_key, 'duration': new_duration, 'click': click_enabled_var.get()}
            
            if is_preview:
                self.main_window._current_pattern[index] = new_step
                success, message = self.main_window.automation_manager.save_pattern(self.main_window._current_pattern_name, self.main_window._current_pattern)
                if success:
                    self._show_preview_pattern_blocks(self.main_window._current_pattern)
                    safe_schedule_ui_update(self.main_window.window, lambda: self.main_window._ensure_pattern_selected(self.main_window._current_pattern_name), 10)
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", f"Failed to save pattern: {message}")
            else:
                self._update_step_with_selection_restore(index, new_step)
                dialog.destroy()
        
        def delete_step():
            if is_preview and len(self.main_window._current_pattern) <= 1:
                messagebox.showwarning("Cannot Delete", "Cannot delete the last step. Pattern must have at least one step.")
                return
            
            if messagebox.askyesno("Confirm Delete", f"Delete step #{index+1}?"):
                if is_preview:
                    self.main_window._current_pattern.pop(index)
                    success, message = self.main_window.automation_manager.save_pattern(self.main_window._current_pattern_name, self.main_window._current_pattern)
                    if success:
                        self._show_preview_pattern_blocks(self.main_window._current_pattern)
                        safe_schedule_ui_update(self.main_window.window, lambda: self.main_window._ensure_pattern_selected(self.main_window._current_pattern_name), 10)
                        dialog.destroy()
                    else:
                        messagebox.showerror("Error", f"Failed to save pattern: {message}")
                else:
                    self._delete_step_with_selection_restore(index)
                    dialog.destroy()
        
        def cancel_edit():
            self._restore_pattern_selection_and_preview()
            dialog.destroy()
        
        button_container = ttk.Frame(buttons_frame)
        button_container.pack(anchor=tk.CENTER, pady=(10, 0))
        
        save_btn = ttk.Button(button_container, text="Save Changes", command=save_changes, width=15)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        delete_btn = ttk.Button(button_container, text="Delete Step", command=delete_step, width=15)
        delete_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_btn = ttk.Button(button_container, text="Cancel", command=cancel_edit, width=12)
        cancel_btn.pack(side=tk.LEFT)
        
        dialog.bind('<Return>', lambda e: save_changes())
        dialog.bind('<Escape>', lambda e: cancel_edit())
        
        dialog.update_idletasks()

    def _show_step_context_menu(self, event, index, step):
        context_menu = tk.Menu(self.main_window.window, tearoff=0)
        context_menu.add_command(label="Edit Step", command=lambda: self._edit_step_dialog(index, step))
        context_menu.add_command(label="Delete Step", command=lambda: self._delete_step(index))
        context_menu.add_separator()
        context_menu.add_command(label="Insert Before", command=lambda: self._insert_step_dialog(index))
        context_menu.add_command(label="Insert After", command=lambda: self._insert_step_dialog(index + 1))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def _show_preview_step_context_menu(self, event, index, step):
        if self.main_window._current_pattern_type != 'custom':
            return
            
        context_menu = tk.Menu(self.main_window.window, tearoff=0)
        context_menu.add_command(label=f"Edit Step #{index + 1}", 
                               command=lambda: self._edit_step_dialog(index, step, is_preview=True))
        context_menu.add_separator()
        context_menu.add_command(label=f"Delete Step #{index + 1}", 
                               command=lambda: self._delete_preview_step(index))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def _delete_preview_step(self, index):
        if self.main_window._current_pattern_type != 'custom' or len(self.main_window._current_pattern) <= 1:
            return
            
        self.main_window._current_pattern.pop(index)
        self.main_window.automation_manager.save_pattern(self.main_window._current_pattern_name, self.main_window._current_pattern)
        self._show_preview_pattern_blocks(self.main_window._current_pattern)
        self.main_window.refresh_pattern_list()

    def _show_pattern_info_dialog(self, step):
        if isinstance(step, dict):
            key = step.get('key', '')
            duration = step.get('duration', None)
        else:
            key = str(step)
            duration = None
            
        info_text = f"Key: {key.upper()}\n"
        if duration is not None:
            info_text += f"Duration: {duration}ms\n"
        else:
            info_text += "Duration: Default Key Duration\n"
        info_text += f"Pattern: {self.main_window._current_pattern_name} (Built-in)\n"
        info_text += "Built-in patterns cannot be edited."
        
        dialog = tk.Toplevel(self.main_window.window)
        dialog.title("Step Information")
        dialog.geometry("300x200")
        dialog.transient(self.main_window.window)
        dialog.grab_set()
         
        dialog.geometry("+%d+%d" % (self.main_window.window.winfo_rootx() + 100, self.main_window.window.winfo_rooty() + 100))
        
        info_label = tk.Label(dialog, text=info_text, font=("Segoe UI", 10), justify=tk.LEFT)
        info_label.pack(padx=20, pady=20)
        
        ttk.Button(dialog, text="OK", command=dialog.destroy).pack(pady=(0, 20))

    def _update_step_with_selection_restore(self, index, new_step):
        if hasattr(self.main_window, '_current_pattern') and 0 <= index < len(self.main_window._current_pattern):
            self.main_window._current_pattern[index] = new_step
            if hasattr(self.main_window.automation_manager, 'recorded_pattern'):
                if 0 <= index < len(self.main_window.automation_manager.recorded_pattern):
                    self.main_window.automation_manager.recorded_pattern[index] = new_step
            self.main_window._unsaved_changes = True
            self._display_recorded_pattern_blocks(self.main_window._current_pattern, is_recording=False)

    def _delete_step_with_selection_restore(self, index):
        if hasattr(self.main_window, '_current_pattern') and 0 <= index < len(self.main_window._current_pattern):
            self.main_window._current_pattern.pop(index)
            if hasattr(self.main_window.automation_manager, 'recorded_pattern'):
                if 0 <= index < len(self.main_window.automation_manager.recorded_pattern):
                    self.main_window.automation_manager.recorded_pattern.pop(index)
            self.main_window._unsaved_changes = True
            self._display_recorded_pattern_blocks(self.main_window._current_pattern, is_recording=False)

    def _restore_pattern_selection_and_preview(self):
        try:
            current_pattern_name = getattr(self.main_window, '_current_pattern_name', None)
            if current_pattern_name:
                self.main_window._ensure_pattern_selected(current_pattern_name)
                if hasattr(self.main_window, '_current_pattern') and self.main_window._current_pattern:
                    self._show_preview_pattern_blocks(self.main_window._current_pattern)
        except Exception as e:
            logger.debug(f"Error restoring pattern selection and preview: {e}")

    def _delete_step(self, index):
        if hasattr(self.main_window, '_current_pattern') and 0 <= index < len(self.main_window._current_pattern):
            self.main_window._current_pattern.pop(index)
            if hasattr(self.main_window.automation_manager, 'recorded_pattern'):
                if 0 <= index < len(self.main_window.automation_manager.recorded_pattern):
                    self.main_window.automation_manager.recorded_pattern.pop(index)
            self.main_window._unsaved_changes = True
            self._display_recorded_pattern_blocks(self.main_window._current_pattern, is_recording=False)

    def _insert_step_dialog(self, index):
        pass

    def _refresh_pattern_display(self, pattern):
        if hasattr(self.main_window, '_current_pattern'):
            self.main_window._current_pattern = pattern
        self._display_recorded_pattern_blocks(pattern, is_recording=False)

    def _update_unsaved_changes_indicator(self, has_changes=True):
        self.main_window._has_unsaved_changes = has_changes
        if hasattr(self.main_window, 'unsaved_changes_label') and self.main_window.unsaved_changes_label:
            if has_changes:
                self.main_window.unsaved_changes_label.config(text="⚠ Unsaved changes", foreground="orange")
            else:
                self.main_window.unsaved_changes_label.config(text="✓ Saved", foreground="green")
                safe_schedule_ui_update(self.main_window.window, lambda: self.main_window.unsaved_changes_label.config(text=""), 2000)
