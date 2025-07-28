import tkinter as tk
from tkinter import ttk

class UIComponentHelper:
    @staticmethod
    def create_widget_with_pack(parent, widget_type, pack_options=None, **widget_options):
        widget = widget_type(parent, **widget_options)
        if pack_options:
            widget.pack(**pack_options)
        else:
            widget.pack()
        return widget

    @staticmethod
    def create_button_group(parent, buttons_config):
        for config in buttons_config:
            UIComponentHelper.create_widget_with_pack(parent, ttk.Button, pack_options=config.get('pack', {'side': tk.LEFT, 'padx': (0, 5)}), **config.get('widget', {}))

    @staticmethod
    def create_checkbutton_group(parent, checkbuttons_config):
        for config in checkbuttons_config:
            UIComponentHelper.create_widget_with_pack(parent, ttk.Checkbutton, pack_options=config.get('pack', {'side': tk.LEFT, 'padx': (0, 10)}), **config.get('widget', {}))

    @staticmethod
    def create_labeled_frame(parent, title, padding="5", **pack_options):
        frame = ttk.LabelFrame(parent, text=title, padding=padding)
        frame.pack(**pack_options)
        return frame

    @staticmethod
    def create_toolbar_frame(parent, **pack_options):
        frame = ttk.Frame(parent)
        frame.pack(**pack_options)
        return frame
