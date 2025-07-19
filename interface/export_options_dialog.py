import tkinter as tk
from tkinter import ttk

class ExportOptionsDialog:
    def __init__(self, parent):
        self.parent = parent
        self.result = None
        self.dialog = None
        
        self.options = {
            'parameters': True,       
            'keybinds': False,          
            'discord': False,        
            'configuration': False      
        }
        
    def show_dialog(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Export Options")
        self.dialog.geometry("450x280")
        self.dialog.resizable(False, False)
        
        try:
            import sys
            import os
            self.dialog.wm_iconbitmap(os.path.join(getattr(sys, '_MEIPASS', '.'), "assets/icon.ico") if hasattr(sys, '_MEIPASS') else "assets/icon.ico")
        except:
            pass  
        
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        self._create_widgets()
        
        self.dialog.wait_window()
        
        return self.result
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(main_frame, text="Choose what to include in the export:", 
                               font=("Segoe UI", 12, "bold"))
        title_label.pack(pady=(0, 20))
        
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=(0, 20))

   
        self.vars = {}

      
        self.vars['parameters'] = tk.BooleanVar(value=True)
        params_frame = ttk.Frame(options_frame)
        params_frame.pack(fill=tk.X, pady=5)
        params_check = ttk.Checkbutton(params_frame, text="Parameters", 
                                      variable=self.vars['parameters'], state='disabled')
        params_check.pack(side=tk.LEFT)
        ttk.Label(params_frame, text="(Always included)", 
                 font=("Segoe UI", 9), foreground="gray").pack(side=tk.LEFT, padx=(10, 0))
        
        self.vars['keybinds'] = tk.BooleanVar(value=self.options['keybinds'])
        keybinds_frame = ttk.Frame(options_frame)
        keybinds_frame.pack(fill=tk.X, pady=5)
        keybinds_check = ttk.Checkbutton(keybinds_frame, text="Keybinds", 
                                        variable=self.vars['keybinds'])
        keybinds_check.pack(side=tk.LEFT)
        ttk.Label(keybinds_frame, text="(F1, F2, F3, F4 hotkeys)", 
                 font=("Segoe UI", 9), foreground="gray").pack(side=tk.LEFT, padx=(10, 0))
        
     
        self.vars['discord'] = tk.BooleanVar(value=self.options['discord'])
        discord_frame = ttk.Frame(options_frame)
        discord_frame.pack(fill=tk.X, pady=5)
        discord_check = ttk.Checkbutton(discord_frame, text="Discord Information", 
                                       variable=self.vars['discord'])
        discord_check.pack(side=tk.LEFT)
        ttk.Label(discord_frame, text="(Webhook URL, User ID, Money Area)", 
                 font=("Segoe UI", 9), foreground="gray").pack(side=tk.LEFT, padx=(10, 0))
        
      
        self.vars['configuration'] = tk.BooleanVar(value=self.options['configuration'])
        config_frame = ttk.Frame(options_frame)
        config_frame.pack(fill=tk.X, pady=5)
        config_check = ttk.Checkbutton(config_frame, text="Configuration", 
                                      variable=self.vars['configuration'])
        config_check.pack(side=tk.LEFT)
        ttk.Label(config_frame, text="(Game area, sell button, cursor position, walk pattern)", 
                 font=("Segoe UI", 9), foreground="gray").pack(side=tk.LEFT, padx=(10, 0))
        
     
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X)
     
        export_btn = ttk.Button(buttons_frame, text="Export", command=self._export_clicked)
        export_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
     
        cancel_btn = ttk.Button(buttons_frame, text="Cancel", command=self._cancel_clicked)
        cancel_btn.pack(side=tk.RIGHT)
        
        
        export_btn.focus_set()
        
      
        self.dialog.bind('<Return>', lambda e: self._export_clicked())
        self.dialog.bind('<Escape>', lambda e: self._cancel_clicked())
    
    def _export_clicked(self):
        self.result = {
            'parameters': self.vars['parameters'].get(),
            'keybinds': self.vars['keybinds'].get(),
            'discord': self.vars['discord'].get(),
            'configuration': self.vars['configuration'].get()
        }
        
        self.dialog.destroy()
    
    def _cancel_clicked(self):
        self.result = None
        self.dialog.destroy()
