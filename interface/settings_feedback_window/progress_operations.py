import tkinter as tk


class ProgressOperations:
    def __init__(self, main_window):
        self.main_window = main_window

    def update_progress(self, value, text=None):
        if self.main_window._is_closed or not self.main_window._is_valid():
            return
        try:
            self.main_window.progress_var.set(min(100, max(0, value)))
            if text:
                self.add_text(text, "info")
            self.main_window._safe_update()
        except Exception:
            pass

    def add_text(self, text, tag="info"):
        if self.main_window._is_closed or not self.main_window._is_valid():
            return
        try:
            self.main_window.text_area.insert(tk.END, f"{text}\n", tag)
            self.main_window.text_area.see(tk.END)
            self.main_window._safe_update()
        except Exception:
            pass

    def add_section(self, title):
        if self.main_window._is_closed or not self.main_window._is_valid():
            return
        try:
            separator = "=" * 60
            self.main_window.text_area.insert(tk.END, f"\n{separator}\n", "header")
            self.main_window.text_area.insert(tk.END, f"{title.upper()}\n", "header")
            self.main_window.text_area.insert(tk.END, f"{separator}\n", "header")
            self.main_window.text_area.see(tk.END)
            self.main_window._safe_update()
        except Exception:
            pass

    def add_summary_stats(self, loaded_count, failed_count, total_count):
        if self.main_window._is_closed or not self.main_window._is_valid():
            return
        try:
            self.add_section("OPERATION SUMMARY")
            self.add_text(
                f"✓ Successfully processed: {loaded_count}/{total_count}", "success"
            )
            if failed_count > 0:
                self.add_text(f"✗ Failed items: {failed_count}", "error")
            else:
                self.add_text("✓ No failures detected", "success")
        except Exception:
            pass

    def operation_complete(self, success=True):
        if self.main_window._is_closed or not self.main_window._is_valid():
            return
        try:
            self.main_window.progress_var.set(100)
            if self.main_window.close_button:
                self.main_window.close_button.config(state="normal")
            self.main_window._safe_update()
        except Exception:
            pass

    def show_error(self, title, message):
        if self.main_window._is_closed:
            return
        try:
            self.add_section(f"ERROR: {title}")
            self.add_text(message, "error")
            self.operation_complete(success=False)
        except Exception:
            pass

    def add_change_entry(self, item_name, old_value, new_value, status="success"):
        if self.main_window._is_closed or not self.main_window._is_valid():
            return
        try:
            if old_value == new_value:
                self.add_text(f"─ {item_name}: {new_value} (unchanged)", "unchanged")
            else:
                symbol = "✓" if status == "success" else "✗"
                self.add_text(
                    f"{symbol} {item_name}: {old_value} → {new_value}", status
                )
        except Exception:
            pass
