import tkinter as tk

class SearchOperations:
    def __init__(self, window_instance):
        self.window = window_instance
        self.logger = window_instance.logger

    def perform_search_operation(self, search_term=None, clear_only=False):
        if clear_only or not search_term:
            if self.window.console_text:
                self.window.console_text.tag_remove("search_highlight", "1.0", tk.END)
            if self.window.search_results_label:
                self.window.search_results_label.config(text="")
            return
        
        if not self.window.console_text:
            return
        
        self.window.console_text.tag_remove("search_highlight", "1.0", tk.END)
        
        case_sensitive = self.window.search_case_var.get()
        content = self.window.console_text.get("1.0", tk.END)
        search_content = content if case_sensitive else content.lower()
        search_term = search_term if case_sensitive else search_term.lower()
        
        matches = 0
        start_pos = 0
        
        while True:
            pos = search_content.find(search_term, start_pos)
            if pos == -1:
                break
            
            matches += 1
            line_start = content.rfind('\n', 0, pos) + 1
            line_num = content[:pos].count('\n') + 1
            char_num = pos - line_start
            
            start_index = f"{line_num}.{char_num}"
            end_index = f"{line_num}.{char_num + len(search_term)}"
            self.window.console_text.tag_add("search_highlight", start_index, end_index)
            start_pos = pos + 1
        
        if self.window.search_results_label:
            self.window.search_results_label.config(text=f"{matches} matches" if matches > 0 else "No matches")

    def clear_search_highlights(self):
        if self.window.console_text:
            self.window.console_text.tag_remove("search_highlight", "1.0", tk.END)

    def highlight_search_results(self, search_term):
        self.perform_search_operation(search_term)
