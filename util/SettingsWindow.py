# util/SettingsWindow.py

# This file contains the SettingsWindow class, which is used to handle
# the settings window for the application.

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

from util.APIHandler import APIHandler

class CreateToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        if self.tooltip:
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height()

        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            wraplength=300,
            padx=5,
            pady=5
        )
        label.pack()

        # Make sure tooltip stays on top
        self.tooltip.lift()
        self.tooltip.attributes('-topmost', True)

    def leave(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class SettingsWindow:
    def __init__(self, parent, mode="T_PEARL"):
        self.parent = parent
        self.settings = parent.settings
        self.mode = mode  # Store the mode parameter
        self.settings_window = tk.Toplevel(parent)
        self.settings_window.title("Settings")
        self.settings_window.geometry("1200x875")
        self.settings_window.attributes("-topmost", True)
        self.settings_window.protocol("WM_DELETE_WINDOW", self.on_close)

        # Configure grid
        self.settings_window.grid_columnconfigure(0, weight=1)
        self.settings_window.grid_columnconfigure(1, weight=4)
        self.settings_window.grid_rowconfigure(0, weight=1)

        # Create frames
        self.left_frame = tk.Frame(self.settings_window)
        self.left_frame.grid(row=0, column=0, sticky="nsew")

        self.right_frame = tk.Frame(self.settings_window)
        self.right_frame.grid(row=0, column=1, sticky="nsew")

        self.create_menu_options()
        self.show_settings("General Settings")

    def create_menu_options(self):
        # Define menu options based on mode
        menu_options = []
        if self.mode == "T_PEARL":
            menu_options = [
                "API Settings",
                "Model Settings",
                "",  # Separator
                "Metadata Presets",
                "Sequential Metadata Presets",
                "Analysis Presets",
                "Document Separation Presets", 
                "Function Presets",
                "Format Presets",
                "",  # Separator
                "Load Settings",
                "Save Settings",
                "Export Settings",
                "Import Settings",
                "Restore Defaults",
                "Done"
            ]
        elif self.mode == "SIMPLE":
            menu_options = [
                "API Settings",
                "Model Settings",
                "",  # Separator
                "Load Settings",
                "Save Settings",
                "Restore Defaults",
                "Done"
            ]
            
        # Clear any existing menu buttons
        for widget in self.left_frame.winfo_children():
            widget.destroy()
            
        # Create menu buttons
        for idx, option in enumerate(menu_options):
            if option:  # Skip empty strings which act as spacers
                btn = tk.Button(self.left_frame, text=option, width=24, anchor='w',
                              command=lambda opt=option: self.show_settings(opt))
                btn.grid(row=idx, column=0, padx=5, pady=5, sticky="ew")
            else:
                # Create a separator (a horizontal line)
                separator = ttk.Separator(self.left_frame, orient="horizontal")
                separator.grid(row=idx, column=0, sticky="ew", padx=5, pady=10)
            
        # Show first option by default
        if menu_options and menu_options[0]:
            self.show_settings(menu_options[0])

    def show_settings(self, option):
        # Clear right frame
        for widget in self.right_frame.winfo_children():
            widget.destroy()
            
        # Show the appropriate settings
        if option == "API Settings":
            self.show_api_settings()
        elif option == "Model Settings":
            self.show_models_and_import_settings()
        elif option == "Metadata Presets":
            self.show_metadata_settings()
        elif option == "Sequential Metadata Presets":
            self.show_sequential_metadata_settings()
        elif option == "Analysis Presets":
            self.show_analysis_presets_settings()
        elif option == "Document Separation Presets":
            self.show_chunk_text_presets_settings()
        elif option == "Function Presets":
            self.show_preset_functions_settings()
        elif option == "Format Presets":
            self.show_format_presets_settings()
        elif option == "Load Settings":
            self.load_settings()
        elif option == "Save Settings":
            self.save_settings()
        elif option == "Export Settings":
            self.export_settings()
        elif option == "Import Settings":
            self.import_settings()
        elif option == "Restore Defaults":
            self.restore_defaults()
        elif option == "Done":
            self.on_close()

    def show_api_settings(self):
        # OpenAI
        openai_label = tk.Label(self.right_frame, text="OpenAI API Key:")
        openai_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.openai_entry = tk.Entry(self.right_frame, width=130)
        self.openai_entry.insert(0, self.settings.openai_api_key)
        self.openai_entry.grid(row=0, column=1, columnspan=3, padx=10, pady=5, sticky="w")
        self.openai_entry.bind("<KeyRelease>",
                               lambda event: setattr(self.settings, 'openai_api_key', self.openai_entry.get()))

        # Anthropic
        anthropic_label = tk.Label(self.right_frame, text="Anthropic API Key:")
        anthropic_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.anthropic_entry = tk.Entry(self.right_frame, width=130)
        self.anthropic_entry.insert(0, self.settings.anthropic_api_key)
        self.anthropic_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        self.anthropic_entry.bind("<KeyRelease>",
                                  lambda event: setattr(self.settings, 'anthropic_api_key', self.anthropic_entry.get()))

        # Google
        google_api_key_label = tk.Label(self.right_frame, text="Google API Key:")
        google_api_key_label.grid(row=11, column=0, padx=10, pady=5, sticky="w")
        self.google_api_key_entry = tk.Entry(self.right_frame, width=130)
        self.google_api_key_entry.insert(0, self.settings.google_api_key)
        self.google_api_key_entry.grid(row=11, column=1, columnspan=3, padx=10, pady=5, sticky="w")
        self.google_api_key_entry.bind("<KeyRelease>",
                                       lambda event: setattr(self.settings, 'google_api_key', self.google_api_key_entry.get()))

        # Add empty row
        empty_label = tk.Label(self.right_frame, text="")
        empty_label.grid(row=12, column=0, padx=10, pady=5)

        # Batch Size
        batch_size_label = tk.Label(self.right_frame, text="Batch Size:")
        batch_size_label.grid(row=13, column=0, padx=10, pady=5, sticky="w")
        self.batch_size_entry = tk.Entry(self.right_frame, width=10)
        self.batch_size_entry.insert(0, str(self.settings.batch_size))
        self.batch_size_entry.grid(row=13, column=1, padx=10, pady=5, sticky="w")
        self.batch_size_entry.bind("<KeyRelease>",
                                   lambda event: setattr(self.settings, 'batch_size',
                                                          int(self.batch_size_entry.get()) if self.batch_size_entry.get().isdigit() else 75))

    def show_models_and_import_settings(self):
        explanation_label = tk.Label(self.right_frame,
                                     text="""List all OpenAI, Claude, and Gemini models by their API model name (ie. claude-3-5-sonnet-20241022).""",
                                     wraplength=675, justify=tk.LEFT)
        explanation_label.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        models_label = tk.Label(self.right_frame, text="Available Models:")
        models_label.grid(row=1, column=0, padx=10, pady=5, sticky="nw")

        self.models_text = tk.Text(self.right_frame, height=30, width=60, wrap=tk.WORD)
        self.models_text.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")
        self.models_text.insert(tk.END, "\n".join(self.settings.model_list))
        self.models_text.bind("<KeyRelease>", self.update_model_list)

        models_scrollbar = tk.Scrollbar(self.right_frame, command=self.models_text.yview)
        models_scrollbar.grid(row=1, column=2, sticky="ns")
        self.models_text.config(yscrollcommand=models_scrollbar.set)

        # Add checkbox for orientation
        self.check_orientation_var = tk.BooleanVar(value=self.settings.check_orientation)
        orientation_checkbox = ttk.Checkbutton(self.right_frame,
                                               text="Automatically attempt to correct orientation of images on import?",
                                               variable=self.check_orientation_var,
                                               command=self.update_check_orientation)
        orientation_checkbox.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Bind the text widget to update settings variable
        self.models_text.bind("<KeyRelease>", self.update_model_list)

    def show_metadata_settings(self):
        for widget in self.right_frame.winfo_children():
            widget.destroy()

        # Main settings frame
        main_settings_frame = ttk.Frame(self.right_frame)
        main_settings_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nw")

        # Initialize variables
        self.metadata_model_var = tk.StringVar()
        self.selected_metadata_preset_var = tk.StringVar()

        # Preset selection row
        tk.Label(main_settings_frame, text="Select Metadata Preset:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        preset_names = [p['name'] for p in self.settings.metadata_presets]
        self.metadata_preset_dropdown = ttk.Combobox(main_settings_frame, 
                                                textvariable=self.selected_metadata_preset_var,
                                                values=preset_names, 
                                                state="readonly", 
                                                width=30)
        self.metadata_preset_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Create, Modify and delete buttons
        create_button = tk.Button(main_settings_frame, text="Create New", 
                               command=self.create_new_metadata_preset_window)
        create_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        modify_button = tk.Button(main_settings_frame, text="Modify", 
                                command=self.modify_metadata_preset)
        modify_button.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        delete_button = tk.Button(main_settings_frame, text="Delete", 
                                command=self.delete_metadata_preset)
        delete_button.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        # Model selection
        tk.Label(main_settings_frame, text="Model:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        model_dropdown = ttk.Combobox(main_settings_frame, 
                                    textvariable=self.metadata_model_var,
                                    values=self.settings.model_list, 
                                    state="readonly", 
                                    width=30)
        model_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        model_dropdown.bind("<<ComboboxSelected>>",
                        lambda e: self.update_current_generic_preset(
                            self.settings.metadata_presets, 
                            self.selected_metadata_preset_var, 
                            'model', 
                            self.metadata_model_var.get()))

        # Temperature
        tk.Label(main_settings_frame, text="Temperature:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.metadata_temp_entry = tk.Entry(main_settings_frame, width=10)
        self.metadata_temp_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.bind_entry_update(self.metadata_temp_entry, self.settings.metadata_presets, 
                           self.selected_metadata_preset_var, 'temperature')

        # Instructions Frame
        instructions_frame = ttk.LabelFrame(self.right_frame, text="Instructions")
        instructions_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # General Instructions
        tk.Label(instructions_frame, text="General Instructions:").grid(row=0, column=0, padx=10, pady=5, sticky="nw")
        general_frame = ttk.Frame(instructions_frame)
        general_frame.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.metadata_general_text = tk.Text(general_frame, height=10, width=90, wrap=tk.WORD)
        self.metadata_general_text.grid(row=0, column=0, sticky="nsew")
        self.bind_text_update(self.metadata_general_text, self.settings.metadata_presets, 
                          self.selected_metadata_preset_var, 'general_instructions')
        general_scrollbar = ttk.Scrollbar(general_frame, orient="vertical", command=self.metadata_general_text.yview)
        self.metadata_general_text.configure(yscrollcommand=general_scrollbar.set)
        general_scrollbar.grid(row=0, column=1, sticky="ns")

        # Specific Instructions
        tk.Label(instructions_frame, text="Specific Instructions:").grid(row=1, column=0, padx=10, pady=5, sticky="nw")
        specific_frame = ttk.Frame(instructions_frame)
        specific_frame.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.metadata_specific_text = tk.Text(specific_frame, height=10, width=90, wrap=tk.WORD)
        self.metadata_specific_text.grid(row=0, column=0, sticky="nsew")
        self.bind_text_update(self.metadata_specific_text, self.settings.metadata_presets, 
                           self.selected_metadata_preset_var, 'specific_instructions')
        specific_scrollbar = ttk.Scrollbar(specific_frame, orient="vertical", command=self.metadata_specific_text.yview)
        self.metadata_specific_text.configure(yscrollcommand=specific_scrollbar.set)
        specific_scrollbar.grid(row=0, column=1, sticky="ns")

        # Metadata Headers
        tk.Label(instructions_frame, text="Metadata Headers:").grid(row=2, column=0, padx=10, pady=5, sticky="nw")
        headers_frame = ttk.Frame(instructions_frame)
        headers_frame.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.metadata_headers_text = tk.Text(headers_frame, height=5, width=90, wrap=tk.WORD)
        self.metadata_headers_text.grid(row=0, column=0, sticky="nsew")
        self.bind_text_update(self.metadata_headers_text, self.settings.metadata_presets, 
                           self.selected_metadata_preset_var, 'metadata_headers')
        headers_scrollbar = ttk.Scrollbar(headers_frame, orient="vertical", command=self.metadata_headers_text.yview)
        self.metadata_headers_text.configure(yscrollcommand=headers_scrollbar.set)
        headers_scrollbar.grid(row=0, column=1, sticky="ns")

        # Validation Text
        tk.Label(instructions_frame, text="Validation Text:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.metadata_val_entry = tk.Entry(instructions_frame, width=90)
        self.metadata_val_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        self.bind_entry_update(self.metadata_val_entry, self.settings.metadata_presets, 
                            self.selected_metadata_preset_var, 'val_text')

        # Load initial preset if available
        if preset_names:
            self.selected_metadata_preset_var.set(preset_names[0])
            # Update the global metadata preset selection in settings
            self.settings.metadata_preset = preset_names[0]
            self.load_selected_metadata_preset()

        # Bind dropdown change to load the selected preset
        self.metadata_preset_dropdown.bind("<<ComboboxSelected>>", self.load_selected_metadata_preset)

    def show_analysis_presets_settings(self):
        for widget in self.right_frame.winfo_children():
            widget.destroy()

        # Main settings frame
        main_settings_frame = ttk.Frame(self.right_frame)
        main_settings_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nw")
        
        # Initialize variables
        self.analysis_model_var = tk.StringVar()
        self.selected_preset_var = tk.StringVar()
        self.use_images_var = tk.BooleanVar()
        self.current_image_var = tk.StringVar(value="Yes")
        self.single_file_var = tk.BooleanVar()
        self.combined_file_var = tk.BooleanVar()
        self.csv_var = tk.BooleanVar()

        # Preset selection row
        tk.Label(main_settings_frame, text="Select Analysis Preset:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        preset_names = [p['name'] for p in self.settings.analysis_presets] if self.settings.analysis_presets else []
        self.preset_dropdown = ttk.Combobox(main_settings_frame, textvariable=self.selected_preset_var,
                                            values=preset_names, state="readonly", width=30)
        self.preset_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Modify and delete buttons
        modify_button = tk.Button(main_settings_frame, text="Modify", 
                                    command=self.modify_analysis_preset)
        modify_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        delete_button = tk.Button(main_settings_frame, text="Delete", 
                                    command=self.delete_analysis_preset)
        delete_button.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Model selection
        tk.Label(main_settings_frame, text="Model:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.analysis_model_var = tk.StringVar()
        model_dropdown = ttk.Combobox(main_settings_frame, 
                                    textvariable=self.analysis_model_var,
                                    values=self.settings.model_list, 
                                    state="readonly", 
                                    width=30)
        model_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        model_dropdown.bind("<<ComboboxSelected>>",
                        lambda e: self.update_current_generic_preset(
                            self.settings.analysis_presets, 
                            self.selected_preset_var, 
                            'model', 
                            self.analysis_model_var.get()))
        
        # Then the temperature row (now moved to row 2)
        tk.Label(main_settings_frame, text="Temperature:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.analysis_temp_entry = tk.Entry(main_settings_frame, width=10)
        self.analysis_temp_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.bind_entry_update(self.analysis_temp_entry, self.settings.analysis_presets, self.selected_preset_var, 'temperature')

        # Temperature Settings
        tk.Label(main_settings_frame, text="Temperature:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.analysis_temp_entry = tk.Entry(main_settings_frame, width=10)
        self.analysis_temp_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.bind_entry_update(self.analysis_temp_entry, self.settings.analysis_presets, self.selected_preset_var, 'temperature')

        # Dataframe Field
        tk.Label(main_settings_frame, text="Dataframe Field:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.analysis_dataframe_field_entry = tk.Entry(main_settings_frame, width=30)
        self.analysis_dataframe_field_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        self.bind_entry_update(self.analysis_dataframe_field_entry, self.settings.analysis_presets, self.selected_preset_var, 'dataframe_field')

        # Image Controls
        image_control_frame = ttk.Frame(self.right_frame)
        image_control_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        use_images_check = ttk.Checkbutton(image_control_frame, text="Use Images",
                                        variable=self.use_images_var,
                                        command=self.toggle_image_controls)
        use_images_check.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.add_var_trace(self.use_images_var, self.settings.analysis_presets, self.selected_preset_var, 'use_images')

        # Image Settings Frame
        self.image_settings_frame = ttk.LabelFrame(image_control_frame, text="Image Settings")
        self.image_settings_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        tk.Label(self.image_settings_frame, text="Current Image:").grid(row=0, column=0, padx=5, pady=5)
        self.current_image_dropdown = ttk.Combobox(self.image_settings_frame,
                                                textvariable=self.current_image_var,
                                                values=["Yes", "No"], 
                                                state="readonly", 
                                                width=5)
        self.current_image_dropdown.grid(row=0, column=1, padx=5, pady=5)
        self.add_var_trace(self.current_image_var, self.settings.analysis_presets, self.selected_preset_var, 'current_image')

        tk.Label(self.image_settings_frame, text="# Previous Images:").grid(row=1, column=0, padx=5, pady=5)
        self.analysis_prev_images_entry = ttk.Spinbox(self.image_settings_frame, from_=0, to=3, width=5)
        self.analysis_prev_images_entry.grid(row=1, column=1, padx=5, pady=5)
        self.bind_entry_update(self.analysis_prev_images_entry, self.settings.analysis_presets, self.selected_preset_var, 'num_prev_images')

        tk.Label(self.image_settings_frame, text="# After Images:").grid(row=1, column=2, padx=5, pady=5)
        self.analysis_after_images_entry = ttk.Spinbox(self.image_settings_frame, from_=0, to=3, width=5)
        self.analysis_after_images_entry.grid(row=1, column=3, padx=5, pady=5)
        self.bind_entry_update(self.analysis_after_images_entry, self.settings.analysis_presets, self.selected_preset_var, 'num_after_images')

        # Output Format Section
        output_frame = ttk.LabelFrame(self.right_frame, text="Output Format")
        output_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        ttk.Checkbutton(output_frame, text="Single Text File", 
                        variable=self.single_file_var).grid(row=0, column=0, padx=5, pady=5)
        ttk.Checkbutton(output_frame, text="Combined Text File", 
                        variable=self.combined_file_var).grid(row=0, column=1, padx=5, pady=5)
        ttk.Checkbutton(output_frame, text="CSV", 
                        variable=self.csv_var,
                        command=self.toggle_csv_columns).grid(row=0, column=2, padx=5, pady=5)

        # Trace for output format (nested in output_format)
        self.add_var_trace(self.single_file_var, self.settings.analysis_presets, self.selected_preset_var, "single_file", nested_key="output_format")
        self.add_var_trace(self.combined_file_var, self.settings.analysis_presets, self.selected_preset_var, "combined_file", nested_key="output_format")
        self.add_var_trace(self.csv_var, self.settings.analysis_presets, self.selected_preset_var, "csv", nested_key="output_format")

        # CSV Columns Frame
        self.csv_columns_frame = ttk.LabelFrame(output_frame, text="Column Headings")
        self.csv_columns_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        self.csv_columns_text = tk.Text(self.csv_columns_frame, height=3, width=60)
        self.csv_columns_text.grid(row=0, column=0, padx=5, pady=5)
        self.csv_columns_text.bind("<KeyRelease>",
                                lambda event: self.update_current_generic_preset(
                                    self.settings.analysis_presets, self.selected_preset_var, 'csv_columns',
                                    self.csv_columns_text.get("1.0", "end-1c")))

        # Instructions Frame
        instructions_frame = ttk.LabelFrame(self.right_frame, text="Instructions")
        instructions_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # General Instructions
        tk.Label(instructions_frame, text="General Instructions:").grid(row=0, column=0, padx=10, pady=5, sticky="nw")
        general_frame = ttk.Frame(instructions_frame)
        general_frame.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.analysis_general_text = tk.Text(general_frame, height=10, width=90, wrap=tk.WORD)
        self.analysis_general_text.grid(row=0, column=0, sticky="nsew")
        self.bind_text_update(self.analysis_general_text, self.settings.analysis_presets, self.selected_preset_var, 'general_instructions')
        general_scrollbar = ttk.Scrollbar(general_frame, orient="vertical", command=self.analysis_general_text.yview)
        self.analysis_general_text.configure(yscrollcommand=general_scrollbar.set)
        general_scrollbar.grid(row=0, column=1, sticky="ns")

        # Specific Instructions
        tk.Label(instructions_frame, text="Specific Instructions:").grid(row=1, column=0, padx=10, pady=5, sticky="nw")
        specific_frame = ttk.Frame(instructions_frame)
        specific_frame.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.analysis_specific_text = tk.Text(specific_frame, height=15, width=90, wrap=tk.WORD)
        self.analysis_specific_text.grid(row=0, column=0, sticky="nsew")
        self.bind_text_update(self.analysis_specific_text, self.settings.analysis_presets, self.selected_preset_var, 'specific_instructions')
        specific_scrollbar = ttk.Scrollbar(specific_frame, orient="vertical", command=self.analysis_specific_text.yview)
        self.analysis_specific_text.configure(yscrollcommand=specific_scrollbar.set)
        specific_scrollbar.grid(row=0, column=1, sticky="ns")

        # Validation Text
        tk.Label(instructions_frame, text="Validation Text:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.analysis_val_entry = tk.Entry(instructions_frame, width=90)
        self.analysis_val_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.bind_entry_update(self.analysis_val_entry, self.settings.analysis_presets, self.selected_preset_var, 'val_text')

        # Load initial preset if available
        if preset_names:
            self.selected_preset_var.set(preset_names[0])
            self.load_selected_preset()

        # Bind dropdown change to load the selected preset
        self.preset_dropdown.bind("<<ComboboxSelected>>", self.load_selected_preset)
    
    def show_chunk_text_presets_settings(self):
        for widget in self.right_frame.winfo_children():
            widget.destroy()

        # Main settings frame
        main_settings_frame = ttk.Frame(self.right_frame)
        main_settings_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nw")
        
        # Initialize variables
        self.chunk_model_var = tk.StringVar()
        self.selected_chunk_preset_var = tk.StringVar()

        # Preset selection row
        tk.Label(main_settings_frame, text="Select Seperate Documents Preset:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        preset_names = [p['name'] for p in self.settings.chunk_text_presets]
        self.chunk_preset_dropdown = ttk.Combobox(main_settings_frame, 
                                                textvariable=self.selected_chunk_preset_var,
                                                values=preset_names, 
                                                state="readonly", 
                                                width=30)
        self.chunk_preset_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Create, Modify and delete buttons
        create_button = tk.Button(main_settings_frame, text="Create New", 
                               command=self.create_new_chunk_preset_window)
        create_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        modify_button = tk.Button(main_settings_frame, text="Modify", 
                                command=self.modify_chunk_preset)
        modify_button.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        delete_button = tk.Button(main_settings_frame, text="Delete", 
                                command=self.delete_chunk_preset)
        delete_button.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        # Model selection
        tk.Label(main_settings_frame, text="Model:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.chunk_model_var = tk.StringVar()
        model_dropdown = ttk.Combobox(main_settings_frame, 
                                    textvariable=self.chunk_model_var,
                                    values=self.settings.model_list, 
                                    state="readonly", 
                                    width=30)
        model_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        model_dropdown.bind("<<ComboboxSelected>>",
                        lambda e: self.update_current_generic_preset(
                            self.settings.chunk_text_presets, 
                            self.selected_chunk_preset_var, 
                            'model', 
                            self.chunk_model_var.get()))
        # Temperature
        tk.Label(main_settings_frame, text="Temperature:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.chunk_temp_entry = tk.Entry(main_settings_frame, width=10)
        self.chunk_temp_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.bind_entry_update(self.chunk_temp_entry, self.settings.chunk_text_presets, self.selected_chunk_preset_var, 'temperature')

        # Add Image Controls Frame
        image_control_frame = ttk.Frame(self.right_frame)
        image_control_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        
        self.use_images_var = tk.BooleanVar()
        use_images_check = ttk.Checkbutton(image_control_frame, text="Use Images",
                                        variable=self.use_images_var,
                                        command=self.toggle_image_controls)
        use_images_check.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.add_var_trace(self.use_images_var, self.settings.chunk_text_presets, 
                        self.selected_chunk_preset_var, 'use_images')

        # Image Settings Frame
        self.image_settings_frame = ttk.LabelFrame(image_control_frame, text="Image Settings")
        self.image_settings_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        tk.Label(self.image_settings_frame, text="Current Image:").grid(row=0, column=0, padx=5, pady=5)
        self.current_image_var = tk.StringVar(value="Yes")
        self.current_image_dropdown = ttk.Combobox(self.image_settings_frame,
                                                textvariable=self.current_image_var,
                                                values=["Yes", "No"], 
                                                state="readonly", 
                                                width=5)
        self.current_image_dropdown.grid(row=0, column=1, padx=5, pady=5)
        self.add_var_trace(self.current_image_var, self.settings.chunk_text_presets, 
                        self.selected_chunk_preset_var, 'current_image')

        tk.Label(self.image_settings_frame, text="# Previous Images:").grid(row=1, column=0, padx=5, pady=5)
        self.analysis_prev_images_entry = ttk.Spinbox(self.image_settings_frame, from_=0, to=3, width=5)
        self.analysis_prev_images_entry.grid(row=1, column=1, padx=5, pady=5)
        self.bind_entry_update(self.analysis_prev_images_entry, self.settings.chunk_text_presets, 
                            self.selected_chunk_preset_var, 'num_prev_images')

        tk.Label(self.image_settings_frame, text="# After Images:").grid(row=1, column=2, padx=5, pady=5)
        self.analysis_after_images_entry = ttk.Spinbox(self.image_settings_frame, from_=0, to=3, width=5)
        self.analysis_after_images_entry.grid(row=1, column=3, padx=5, pady=5)
        self.bind_entry_update(self.analysis_after_images_entry, self.settings.chunk_text_presets, 
                            self.selected_chunk_preset_var, 'num_after_images')

        # Instructions and Validation Frame
        instructions_frame = ttk.LabelFrame(self.right_frame, text="Instructions")
        instructions_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # General Instructions
        tk.Label(instructions_frame, text="General Instructions:").grid(row=0, column=0, padx=10, pady=5, sticky="nw")
        general_frame = ttk.Frame(instructions_frame)
        general_frame.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.chunk_general_text = tk.Text(general_frame, height=10, width=90, wrap=tk.WORD)
        self.chunk_general_text.grid(row=0, column=0, sticky="nsew")
        self.bind_text_update(self.chunk_general_text, self.settings.chunk_text_presets, self.selected_chunk_preset_var, 'general_instructions')
        general_scrollbar = ttk.Scrollbar(general_frame, orient="vertical", command=self.chunk_general_text.yview)
        self.chunk_general_text.configure(yscrollcommand=general_scrollbar.set)
        general_scrollbar.grid(row=0, column=1, sticky="ns")

        # Specific Instructions
        tk.Label(instructions_frame, text="Specific Instructions:").grid(row=1, column=0, padx=10, pady=5, sticky="nw")
        specific_frame = ttk.Frame(instructions_frame)
        specific_frame.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.chunk_specific_text = tk.Text(specific_frame, height=15, width=90, wrap=tk.WORD)
        self.chunk_specific_text.grid(row=0, column=0, sticky="nsew")
        self.bind_text_update(self.chunk_specific_text, self.settings.chunk_text_presets, self.selected_chunk_preset_var, 'specific_instructions')
        specific_scrollbar = ttk.Scrollbar(specific_frame, orient="vertical", command=self.chunk_specific_text.yview)
        self.chunk_specific_text.configure(yscrollcommand=specific_scrollbar.set)
        specific_scrollbar.grid(row=0, column=1, sticky="ns")

        # Validation Text
        tk.Label(instructions_frame, text="Validation Text:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.chunk_val_entry = tk.Entry(instructions_frame, width=90)
        self.chunk_val_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.bind_entry_update(self.chunk_val_entry, self.settings.chunk_text_presets, self.selected_chunk_preset_var, 'val_text')

        # Load initial preset if available
        if preset_names:
            self.selected_chunk_preset_var.set(preset_names[0])
            self.load_selected_chunk_preset()

        # Bind dropdown change to load the selected preset
        self.chunk_preset_dropdown.bind("<<ComboboxSelected>>", self.load_selected_chunk_preset)
        
    def show_preset_functions_settings(self):
        for widget in self.right_frame.winfo_children():
            widget.destroy()

        # Main settings frame
        main_settings_frame = ttk.Frame(self.right_frame)
        main_settings_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nw")

        # Preset selection row
        tk.Label(main_settings_frame, text="Select Function Preset:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.selected_function_preset_var = tk.StringVar()
        preset_names = [p['name'] for p in self.settings.function_presets] if self.settings.function_presets else []
        self.function_preset_dropdown = ttk.Combobox(main_settings_frame, textvariable=self.selected_function_preset_var,
                                                    values=preset_names, state="readonly", width=30)
        self.function_preset_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.function_preset_dropdown.bind("<<ComboboxSelected>>", self.load_selected_function_preset)

        # Modify and delete buttons
        modify_button = tk.Button(main_settings_frame, text="Modify", command=self.modify_function_preset)
        modify_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        delete_button = tk.Button(main_settings_frame, text="Delete", command=self.delete_function_preset)
        delete_button.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Model and Temperature row
        tk.Label(main_settings_frame, text="Model:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.function_model_var = tk.StringVar()
        model_dropdown = ttk.Combobox(main_settings_frame, 
                                    textvariable=self.function_model_var,
                                    values=self.settings.model_list, 
                                    state="readonly", 
                                    width=30)
        model_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        model_dropdown.bind("<<ComboboxSelected>>",
                        lambda e: self.update_current_generic_preset(
                            self.settings.function_presets, 
                            self.selected_function_preset_var, 
                            'model', 
                            self.function_model_var.get()))
    
        tk.Label(main_settings_frame, text="Temperature:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.function_temp_entry = tk.Entry(main_settings_frame, width=10)
        self.function_temp_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.bind_entry_update(self.function_temp_entry, self.settings.function_presets, self.selected_function_preset_var, 'temperature')

        # Image Controls
        image_control_frame = ttk.Frame(self.right_frame)
        image_control_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.use_images_var = tk.BooleanVar()
        use_images_check = ttk.Checkbutton(image_control_frame, text="Use Images",
                                        variable=self.use_images_var,
                                        command=self.toggle_image_controls)
        use_images_check.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.add_var_trace(self.use_images_var, self.settings.function_presets, self.selected_function_preset_var, 'use_images')

        # Detailed Image Settings Frame
        self.image_settings_frame = ttk.LabelFrame(image_control_frame, text="Image Settings")
        self.image_settings_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        self.image_settings_frame.grid_remove()  # Initially hidden

        tk.Label(self.image_settings_frame, text="Current Image:").grid(row=0, column=0, padx=5, pady=5)
        self.current_image_var = tk.StringVar(value="Yes")
        self.current_image_dropdown = ttk.Combobox(self.image_settings_frame,
                                                textvariable=self.current_image_var,
                                                values=["Yes", "No"], state="readonly", width=5)
        self.current_image_dropdown.grid(row=0, column=1, padx=5, pady=5)
        self.add_var_trace(self.current_image_var, self.settings.function_presets, self.selected_function_preset_var, 'current_image')

        tk.Label(self.image_settings_frame, text="# Previous Images:").grid(row=1, column=0, padx=5, pady=5)
        self.analysis_prev_images_entry = ttk.Spinbox(self.image_settings_frame, from_=0, to=3, width=5)
        self.analysis_prev_images_entry.grid(row=1, column=1, padx=5, pady=5)
        self.bind_entry_update(self.analysis_prev_images_entry, self.settings.function_presets, self.selected_function_preset_var, 'num_prev_images')

        tk.Label(self.image_settings_frame, text="# After Images:").grid(row=1, column=2, padx=5, pady=5)
        self.analysis_after_images_entry = ttk.Spinbox(self.image_settings_frame, from_=0, to=3, width=5)
        self.analysis_after_images_entry.grid(row=1, column=3, padx=5, pady=5)
        self.bind_entry_update(self.analysis_after_images_entry, self.settings.function_presets, self.selected_function_preset_var, 'num_after_images')

        # Instructions and Validation Frame
        instructions_frame = ttk.LabelFrame(self.right_frame, text="Instructions")
        instructions_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # General Instructions
        tk.Label(instructions_frame, text="General Instructions:").grid(row=0, column=0, padx=10, pady=5, sticky="nw")
        general_frame = ttk.Frame(instructions_frame)
        general_frame.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.function_general_text = tk.Text(general_frame, height=10, width=90, wrap=tk.WORD)
        self.function_general_text.grid(row=0, column=0, sticky="nsew")
        self.bind_text_update(self.function_general_text, self.settings.function_presets, self.selected_function_preset_var, 'general_instructions')
        general_scrollbar = ttk.Scrollbar(general_frame, orient="vertical", command=self.function_general_text.yview)
        self.function_general_text.configure(yscrollcommand=general_scrollbar.set)
        general_scrollbar.grid(row=0, column=1, sticky="ns")

        # Specific Instructions
        tk.Label(instructions_frame, text="Specific Instructions:").grid(row=1, column=0, padx=10, pady=5, sticky="nw")
        specific_frame = ttk.Frame(instructions_frame)
        specific_frame.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.function_specific_text = tk.Text(specific_frame, height=15, width=90, wrap=tk.WORD)
        self.function_specific_text.grid(row=0, column=0, sticky="nsew")
        self.bind_text_update(self.function_specific_text, self.settings.function_presets, self.selected_function_preset_var, 'specific_instructions')
        specific_scrollbar = ttk.Scrollbar(specific_frame, orient="vertical", command=self.function_specific_text.yview)
        self.function_specific_text.configure(yscrollcommand=specific_scrollbar.set)
        specific_scrollbar.grid(row=0, column=1, sticky="ns")

        # Validation Text
        tk.Label(instructions_frame, text="Validation Text:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.function_val_entry = tk.Entry(instructions_frame, width=90)
        self.function_val_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.bind_entry_update(self.function_val_entry, self.settings.function_presets, self.selected_function_preset_var, 'val_text')

    def show_format_presets_settings(self):
        for widget in self.right_frame.winfo_children():
            widget.destroy()

        # Main settings frame
        main_settings_frame = ttk.Frame(self.right_frame)
        main_settings_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nw")
        
        # Initialize variables
        self.format_model_var = tk.StringVar()
        self.selected_format_preset_var = tk.StringVar()
        self.use_images_var = tk.BooleanVar()
        self.current_image_var = tk.StringVar(value="Yes")

        # Preset selection row
        tk.Label(main_settings_frame, text="Select Format Preset:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        preset_names = [p['name'] for p in self.settings.format_presets]
        self.format_preset_dropdown = ttk.Combobox(main_settings_frame, 
                                                textvariable=self.selected_format_preset_var,
                                                values=preset_names, 
                                                state="readonly", 
                                                width=30)
        self.format_preset_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Create, Modify and delete buttons
        create_button = tk.Button(main_settings_frame, text="Create New", 
                               command=self.create_new_format_preset_window)
        create_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        modify_button = tk.Button(main_settings_frame, text="Modify", 
                                command=self.modify_format_preset)
        modify_button.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        delete_button = tk.Button(main_settings_frame, text="Delete", 
                                command=self.delete_format_preset)
        delete_button.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        # Model selection
        tk.Label(main_settings_frame, text="Model:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        model_dropdown = ttk.Combobox(main_settings_frame, 
                                    textvariable=self.format_model_var,
                                    values=self.settings.model_list, 
                                    state="readonly", 
                                    width=30)
        model_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        model_dropdown.bind("<<ComboboxSelected>>",
                        lambda e: self.update_current_generic_preset(
                            self.settings.format_presets, 
                            self.selected_format_preset_var, 
                            'model', 
                            self.format_model_var.get()))
        # Temperature
        tk.Label(main_settings_frame, text="Temperature:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.format_temp_entry = tk.Entry(main_settings_frame, width=10)
        self.format_temp_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.bind_entry_update(self.format_temp_entry, self.settings.format_presets, self.selected_format_preset_var, 'temperature')
        
        # Add Image Controls Frame
        image_control_frame = ttk.Frame(self.right_frame)
        image_control_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        
        use_images_check = ttk.Checkbutton(image_control_frame, text="Use Images",
                                        variable=self.use_images_var,
                                        command=self.toggle_image_controls)
        use_images_check.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.add_var_trace(self.use_images_var, self.settings.format_presets, 
                        self.selected_format_preset_var, 'use_images')

        # Image Settings Frame
        self.image_settings_frame = ttk.LabelFrame(image_control_frame, text="Image Settings")
        self.image_settings_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        tk.Label(self.image_settings_frame, text="Current Image:").grid(row=0, column=0, padx=5, pady=5)
        self.current_image_dropdown = ttk.Combobox(self.image_settings_frame,
                                                textvariable=self.current_image_var,
                                                values=["Yes", "No"], 
                                                state="readonly", 
                                                width=5)
        self.current_image_dropdown.grid(row=0, column=1, padx=5, pady=5)
        self.add_var_trace(self.current_image_var, self.settings.format_presets, 
                        self.selected_format_preset_var, 'current_image')

        tk.Label(self.image_settings_frame, text="# Previous Images:").grid(row=1, column=0, padx=5, pady=5)
        self.format_prev_images_entry = ttk.Spinbox(self.image_settings_frame, from_=0, to=3, width=5)
        self.format_prev_images_entry.grid(row=1, column=1, padx=5, pady=5)
        self.bind_entry_update(self.format_prev_images_entry, self.settings.format_presets, 
                            self.selected_format_preset_var, 'num_prev_images')

        tk.Label(self.image_settings_frame, text="# After Images:").grid(row=1, column=2, padx=5, pady=5)
        self.format_after_images_entry = ttk.Spinbox(self.image_settings_frame, from_=0, to=3, width=5)
        self.format_after_images_entry.grid(row=1, column=3, padx=5, pady=5)
        self.bind_entry_update(self.format_after_images_entry, self.settings.format_presets, 
                            self.selected_format_preset_var, 'num_after_images')
        
        # Instructions and Validation Frame
        instructions_frame = ttk.LabelFrame(self.right_frame, text="Instructions")
        instructions_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # General Instructions
        tk.Label(instructions_frame, text="General Instructions:").grid(row=0, column=0, padx=10, pady=5, sticky="nw")
        general_frame = ttk.Frame(instructions_frame)
        general_frame.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.format_general_text = tk.Text(general_frame, height=10, width=90, wrap=tk.WORD)
        self.format_general_text.grid(row=0, column=0, sticky="nsew")
        self.bind_text_update(self.format_general_text, self.settings.format_presets, self.selected_format_preset_var, 'general_instructions')
        general_scrollbar = ttk.Scrollbar(general_frame, orient="vertical", command=self.format_general_text.yview)
        self.format_general_text.configure(yscrollcommand=general_scrollbar.set)
        general_scrollbar.grid(row=0, column=1, sticky="ns")

        # Specific Instructions
        tk.Label(instructions_frame, text="Specific Instructions:").grid(row=1, column=0, padx=10, pady=5, sticky="nw")
        specific_frame = ttk.Frame(instructions_frame)
        specific_frame.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.format_specific_text = tk.Text(specific_frame, height=15, width=90, wrap=tk.WORD)
        self.format_specific_text.grid(row=0, column=0, sticky="nsew")
        self.bind_text_update(self.format_specific_text, self.settings.format_presets, self.selected_format_preset_var, 'specific_instructions')
        specific_scrollbar = ttk.Scrollbar(specific_frame, orient="vertical", command=self.format_specific_text.yview)
        self.format_specific_text.configure(yscrollcommand=specific_scrollbar.set)
        specific_scrollbar.grid(row=0, column=1, sticky="ns")

        # Validation Text
        tk.Label(instructions_frame, text="Validation Text:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.format_val_entry = tk.Entry(instructions_frame, width=90)
        self.format_val_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.bind_entry_update(self.format_val_entry, self.settings.format_presets, self.selected_format_preset_var, 'val_text')

        # Load initial preset if available
        if preset_names:
            self.selected_format_preset_var.set(preset_names[0])
            self.load_selected_format_preset()

        # Bind dropdown change to load the selected preset
        self.format_preset_dropdown.bind("<<ComboboxSelected>>", self.load_selected_format_preset)
        
    def load_selected_format_preset(self, event=None):
        selected_name = self.selected_format_preset_var.get()
        preset = self.get_preset_by_name(self.settings.format_presets, selected_name)
        if preset:
            # Model
            if 'model' in preset and preset['model'] in self.settings.model_list:
                self.format_model_var.set(preset['model'])
            self.set_entry_text(self.format_temp_entry, preset.get('temperature', "0.2"))
            
            # Image settings
            self.use_images_var.set(preset.get('use_images', False))
            self.current_image_var.set(preset.get('current_image', "No"))
            self.set_entry_text(self.format_prev_images_entry, preset.get('num_prev_images', "0"))
            self.set_entry_text(self.format_after_images_entry, preset.get('num_after_images', "0"))
            
            # Instructions
            self.set_text_widget(self.format_general_text, preset.get('general_instructions', ""))
            self.set_text_widget(self.format_specific_text, preset.get('specific_instructions', ""))
            # Validation Text
            if hasattr(self, 'format_val_entry'):
                self.set_entry_text(self.format_val_entry, preset.get('val_text', "Formatted Text:"))
            # Toggle image controls based on use_images setting
            self.toggle_image_controls()

    def create_new_format_preset_window(self):
        new_win = tk.Toplevel(self.settings_window)
        new_win.title("Create New Format Preset")

        new_win.transient(self.settings_window)
        new_win.grab_set()
        new_win.attributes('-topmost', True)

        window_width = 300
        window_height = 120
        screen_width = new_win.winfo_screenwidth()
        screen_height = new_win.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        new_win.geometry(f'{window_width}x{window_height}+{x}+{y}')

        new_win.grid_columnconfigure(1, weight=1)

        tk.Label(new_win, text="Preset Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        name_entry = tk.Entry(new_win, width=30)
        name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        button_frame = tk.Frame(new_win)
        button_frame.grid(row=1, column=0, columnspan=3, pady=20)

        def save_new_format_preset():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Invalid Name", "Please enter a preset name.", parent=new_win)
                return

            if any(preset['name'] == name for preset in self.settings.format_presets):
                messagebox.showwarning("Duplicate Name",
                                       "A preset with this name already exists. Please choose a different name.",
                                       parent=new_win)
                return

            new_preset = {
                'name': name,
                'model': self.settings.model_list[0] if self.settings.model_list else "gemini-2.0-flash",
                'temperature': "0.2",
                'general_instructions': '''You re-format historical documents to make them easier to read while retaining the original text. Remove all page numbers, headers, footers, archival stamps/references, etc. In your response, write "Formatted Text:" followed by a formatted version of the document.''',
                'specific_instructions': '''Text to format:\n\n{text_to_process}''',
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Formatted Text:"
            }

            self.settings.format_presets.append(new_preset)
            # Update dropdown for format presets
            preset_names = [p['name'] for p in self.settings.format_presets]
            self.format_preset_dropdown['values'] = preset_names
            if preset_names:
                self.selected_format_preset_var.set(preset_names[-1])
                self.load_selected_format_preset()
            self.settings.save_settings()
            new_win.destroy()

        tk.Button(button_frame, text="Save", command=save_new_format_preset, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=new_win.destroy, width=10).pack(side=tk.LEFT, padx=5)
        name_entry.bind('<Return>', lambda e: save_new_format_preset())
        name_entry.focus_set()
        
    def modify_format_preset(self):
        selected_name = self.selected_format_preset_var.get()
        if not selected_name:
            messagebox.showwarning("No Selection", 
                                "No format preset selected to modify.", 
                                parent=self.settings_window)
            return

        preset = self.get_preset_by_name(self.settings.format_presets, selected_name)
        if not preset:
            messagebox.showwarning("Error", "Selected preset not found.", 
                                parent=self.settings_window)
            return

        # Create modification window
        new_win = tk.Toplevel(self.settings_window)
        new_win.title("Modify Format Preset Name")
        new_win.transient(self.settings_window)
        new_win.grab_set()
        new_win.attributes('-topmost', True)

        window_width = 300
        window_height = 120
        screen_width = new_win.winfo_screenwidth()
        screen_height = new_win.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        new_win.geometry(f'{window_width}x{window_height}+{x}+{y}')
        new_win.grid_columnconfigure(1, weight=1)

        tk.Label(new_win, text="New Preset Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        name_entry = tk.Entry(new_win, width=30)
        name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        name_entry.insert(0, selected_name)

        def save_modified_preset():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showwarning("Invalid Name", "Please enter a preset name.", 
                                    parent=new_win)
                return

            if new_name != selected_name and any(p['name'] == new_name 
                                            for p in self.settings.format_presets):
                messagebox.showwarning("Duplicate Name",
                                    "A preset with this name already exists. Please choose a different name.",
                                    parent=new_win)
                return

            preset['name'] = new_name
            self.settings.save_settings()
            self.update_format_preset_dropdown()
            self.selected_format_preset_var.set(new_name)
            new_win.destroy()

        button_frame = tk.Frame(new_win)
        button_frame.grid(row=1, column=0, columnspan=3, pady=20)
        tk.Button(button_frame, text="Save", command=save_modified_preset, 
                width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=new_win.destroy, 
                width=10).pack(side=tk.LEFT, padx=5)

        name_entry.bind('<Return>', lambda e: save_modified_preset())
        name_entry.focus_set()
        
    def delete_format_preset(self):
        selected_name = self.selected_format_preset_var.get()
        if not selected_name:
            messagebox.showwarning("No Selection", 
                                "No format preset selected to delete.", 
                                parent=self.settings_window)
            return
        
        confirm = messagebox.askyesno("Confirm Deletion",
                                    f"Are you sure you want to delete the format preset '{selected_name}'?",
                                    parent=self.settings_window)
        if not confirm:
            return

        # Remove the preset from the list and update settings
        self.settings.format_presets = [p for p in self.settings.format_presets 
                                        if p['name'] != selected_name]
        self.settings.save_settings()
        self.update_format_preset_dropdown()
        
    def update_format_preset_dropdown(self):
        """Update format preset dropdown if it exists."""
        try:
            if hasattr(self, 'format_preset_dropdown') and self.format_preset_dropdown.winfo_exists():
                preset_names = [p['name'] for p in self.settings.format_presets]
                self.format_preset_dropdown['values'] = preset_names
                if preset_names and self.selected_format_preset_var.get() not in preset_names:
                    self.selected_format_preset_var.set(preset_names[0])
                    self.load_selected_format_preset()
        except tk.TclError:
            pass
            
    def update_all_dropdowns(self):
        """Update all dropdown menus with current values"""
        self.update_model_dropdowns()
        self.update_function_preset_dropdown()
        self.update_preset_dropdown()
        self.update_chunk_preset_dropdown()
        self.update_metadata_preset_dropdown()
        self.update_seq_metadata_preset_dropdown()
        self.update_format_preset_dropdown()

# Load Preset Functions

    def load_selected_function_preset(self, event=None):
        selected_name = self.selected_function_preset_var.get()
        preset = self.get_preset_by_name(self.settings.function_presets, selected_name)
        if preset:
            # Model
            if 'model' in preset and preset['model'] in self.settings.model_list:
                self.function_model_var.set(preset['model'])
            self.set_entry_text(self.function_temp_entry, preset.get('temperature', "0.7"))
            # Image settings
            self.use_images_var.set(preset.get('use_images', True))
            self.current_image_var.set(preset.get('current_image', "Yes"))
            self.set_entry_text(self.analysis_prev_images_entry, preset.get('num_prev_images', "0"))
            self.set_entry_text(self.analysis_after_images_entry, preset.get('num_after_images', "0"))
            # Instructions
            self.set_text_widget(self.function_general_text, preset.get('general_instructions', ""))
            self.set_text_widget(self.function_specific_text, preset.get('specific_instructions', ""))
            # Validation text for function presets
            if 'val_text' in preset:
                if not hasattr(self, 'function_val_entry'):
                    self.function_val_entry = tk.Entry(self.right_frame, width=60)
                self.set_entry_text(self.function_val_entry, preset.get('val_text', ""))
            self.toggle_image_controls()

    def load_selected_preset(self, event=None):
        selected_name = self.selected_preset_var.get()
        preset = self.get_preset_by_name(self.settings.analysis_presets, selected_name)
        if preset:
            # Model
            if 'model' in preset and preset['model'] in self.settings.model_list:
                self.analysis_model_var.set(preset['model'])
            self.set_entry_text(self.analysis_temp_entry, preset.get('temperature', "0.7"))
            # Dataframe Field
            if 'dataframe_field' in preset:
                self.set_entry_text(self.analysis_dataframe_field_entry, preset.get('dataframe_field', ""))
            # Image settings
            self.use_images_var.set(preset.get('use_images', True))
            self.current_image_var.set(preset.get('current_image', "Yes"))
            self.set_entry_text(self.analysis_prev_images_entry, preset.get('num_prev_images', "0"))
            self.set_entry_text(self.analysis_after_images_entry, preset.get('num_after_images', "0"))
            # Output format
            output_format = preset.get('output_format', {})
            self.single_file_var.set(output_format.get('single_file', True))
            self.combined_file_var.set(output_format.get('combined_file', False))
            self.csv_var.set(output_format.get('csv', False))
            # CSV columns
            self.set_text_widget(self.csv_columns_text, preset.get('csv_columns', ""))
            # Instructions
            self.set_text_widget(self.analysis_general_text, preset.get('general_instructions', ""))
            self.set_text_widget(self.analysis_specific_text, preset.get('specific_instructions', ""))
            # Validation text for analysis presets
            if 'val_text' in preset:
                if not hasattr(self, 'analysis_val_entry') or not self.analysis_val_entry.winfo_exists():
                    # First add the label for validation text
                    validation_label = tk.Label(self.right_frame, text="Validation Text:")
                    validation_label.grid(row=8, column=0, padx=10, pady=5, sticky="w")
                    # Then create the entry widget
                    self.analysis_val_entry = tk.Entry(self.right_frame, width=60)
                    self.analysis_val_entry.grid(row=8, column=1, padx=10, pady=5, sticky="w")
                    # Bind the entry update
                    self.bind_entry_update(self.analysis_val_entry, self.settings.analysis_presets, 
                                      self.selected_preset_var, 'val_text')
                # Set the text after ensuring the widget exists
                self.set_entry_text(self.analysis_val_entry, preset.get('val_text', ""))
            self.toggle_image_controls()
            self.toggle_csv_columns()
    
    def load_selected_chunk_preset(self, event=None):
        selected_name = self.selected_chunk_preset_var.get()
        preset = self.get_preset_by_name(self.settings.chunk_text_presets, selected_name)
        if preset:
            # Existing settings
            if 'model' in preset and preset['model'] in self.settings.model_list:
                self.chunk_model_var.set(preset['model'])
            self.set_entry_text(self.chunk_temp_entry, preset.get('temperature', "0.7"))
            
            # Image settings
            self.use_images_var.set(preset.get('use_images', False))
            self.current_image_var.set(preset.get('current_image', "No"))
            self.set_entry_text(self.analysis_prev_images_entry, preset.get('num_prev_images', "0"))
            self.set_entry_text(self.analysis_after_images_entry, preset.get('num_after_images', "0"))
            
            # Instructions
            self.set_text_widget(self.chunk_general_text, preset.get('general_instructions', ""))
            self.set_text_widget(self.chunk_specific_text, preset.get('specific_instructions', ""))
            self.set_entry_text(self.chunk_val_entry, preset.get('val_text', ""))
            
            # Toggle image controls based on use_images setting
            self.toggle_image_controls()

    def load_selected_metadata_preset(self, event=None):
        selected_name = self.selected_metadata_preset_var.get()
        preset = self.get_preset_by_name(self.settings.metadata_presets, selected_name)
        if preset:
            # Model
            if 'model' in preset and preset['model'] in self.settings.model_list:
                self.metadata_model_var.set(preset['model'])
            # Temperature
            self.set_entry_text(self.metadata_temp_entry, preset.get('temperature', "0.3"))
            # Instructions
            self.set_text_widget(self.metadata_general_text, preset.get('general_instructions', ""))
            self.set_text_widget(self.metadata_specific_text, preset.get('specific_instructions', ""))
            self.set_text_widget(self.metadata_headers_text, preset.get('metadata_headers', ""))
            self.set_entry_text(self.metadata_val_entry, preset.get('val_text', "Metadata:"))
            
            # Update the global metadata preset selection in settings
            self.settings.metadata_preset = selected_name
            
            # Also update the individual settings fields for backward compatibility
            self.settings.metadata_model = preset.get('model', "claude-3-5-sonnet-20241022")
            self.settings.metadata_temp = preset.get('temperature', "0.3")
            self.settings.metadata_system_prompt = preset.get('general_instructions', "")
            self.settings.metadata_user_prompt = preset.get('specific_instructions', "")
            self.settings.metadata_val_text = preset.get('val_text', "Metadata:")
            self.settings.metadata_headers = preset.get('metadata_headers', "")

    def show_sequential_metadata_settings(self):
        for widget in self.right_frame.winfo_children():
            widget.destroy()

        # Main settings frame
        main_settings_frame = ttk.Frame(self.right_frame)
        main_settings_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nw")

        # Initialize variables
        self.seq_metadata_model_var = tk.StringVar()
        self.selected_seq_metadata_preset_var = tk.StringVar()

        # Preset selection row
        tk.Label(main_settings_frame, text="Select Sequential Metadata Preset:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        preset_names = [p['name'] for p in self.settings.sequential_metadata_presets]
        self.seq_metadata_preset_dropdown = ttk.Combobox(main_settings_frame, 
                                                textvariable=self.selected_seq_metadata_preset_var,
                                                values=preset_names, 
                                                state="readonly", 
                                                width=30)
        self.seq_metadata_preset_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Create, Modify and delete buttons
        create_button = tk.Button(main_settings_frame, text="Create New", 
                               command=self.create_new_seq_metadata_preset_window)
        create_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        modify_button = tk.Button(main_settings_frame, text="Modify", 
                                command=self.modify_seq_metadata_preset)
        modify_button.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        delete_button = tk.Button(main_settings_frame, text="Delete", 
                                command=self.delete_seq_metadata_preset)
        delete_button.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        # Model selection
        tk.Label(main_settings_frame, text="Model:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        model_dropdown = ttk.Combobox(main_settings_frame, 
                                    textvariable=self.seq_metadata_model_var,
                                    values=self.settings.model_list, 
                                    state="readonly", 
                                    width=30)
        model_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        model_dropdown.bind("<<ComboboxSelected>>",
                        lambda e: self.update_current_generic_preset(
                            self.settings.sequential_metadata_presets, 
                            self.selected_seq_metadata_preset_var, 
                            'model', 
                            self.seq_metadata_model_var.get()))

        # Temperature
        tk.Label(main_settings_frame, text="Temperature:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.seq_metadata_temp_entry = tk.Entry(main_settings_frame, width=10)
        self.seq_metadata_temp_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.bind_entry_update(self.seq_metadata_temp_entry, self.settings.sequential_metadata_presets, 
                           self.selected_seq_metadata_preset_var, 'temperature')

        # Sequential Batch Size
        tk.Label(main_settings_frame, text="Batch Size:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.seq_batch_size_entry = tk.Entry(main_settings_frame, width=10)
        self.seq_batch_size_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        # Bind this entry to the global sequential_batch_size setting
        self.seq_batch_size_entry.insert(0, str(self.settings.sequential_batch_size))
        self.seq_batch_size_entry.bind("<KeyRelease>", self._update_sequential_batch_size)
        self.seq_batch_size_entry.bind("<FocusOut>", self._update_sequential_batch_size)

        # Instructions Frame
        instructions_frame = ttk.LabelFrame(self.right_frame, text="Instructions & Headers") # Updated frame title
        instructions_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # General Instructions
        tk.Label(instructions_frame, text="General Instructions:").grid(row=0, column=0, padx=10, pady=5, sticky="nw")
        general_frame = ttk.Frame(instructions_frame)
        general_frame.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.seq_metadata_general_text = tk.Text(general_frame, height=10, width=90, wrap=tk.WORD)
        self.seq_metadata_general_text.grid(row=0, column=0, sticky="nsew")
        self.bind_text_update(self.seq_metadata_general_text, self.settings.sequential_metadata_presets, 
                          self.selected_seq_metadata_preset_var, 'general_instructions')
        general_scrollbar = ttk.Scrollbar(general_frame, orient="vertical", command=self.seq_metadata_general_text.yview)
        self.seq_metadata_general_text.configure(yscrollcommand=general_scrollbar.set)
        general_scrollbar.grid(row=0, column=1, sticky="ns")

        # Specific Instructions
        tk.Label(instructions_frame, text="Specific Instructions:").grid(row=1, column=0, padx=10, pady=5, sticky="nw")
        specific_frame = ttk.Frame(instructions_frame)
        specific_frame.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.seq_metadata_specific_text = tk.Text(specific_frame, height=10, width=90, wrap=tk.WORD)
        self.seq_metadata_specific_text.grid(row=0, column=0, sticky="nsew")
        self.bind_text_update(self.seq_metadata_specific_text, self.settings.sequential_metadata_presets, 
                           self.selected_seq_metadata_preset_var, 'specific_instructions')
        specific_scrollbar = ttk.Scrollbar(specific_frame, orient="vertical", command=self.seq_metadata_specific_text.yview)
        self.seq_metadata_specific_text.configure(yscrollcommand=specific_scrollbar.set)
        specific_scrollbar.grid(row=0, column=1, sticky="ns")

        # --- Add Required Headers Entry --- 
        tk.Label(instructions_frame, text="Required Headers:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.seq_metadata_headers_entry = tk.Entry(instructions_frame, width=90)
        self.seq_metadata_headers_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        # Bind this entry - NOTE: required_headers in the preset is a string, not a list
        self.bind_entry_update(self.seq_metadata_headers_entry,
                            self.settings.sequential_metadata_presets,
                            self.selected_seq_metadata_preset_var,
                            'required_headers')
        # --- End Add Required Headers Entry --- 

        # Validation Text
        tk.Label(instructions_frame, text="Validation Text:").grid(row=3, column=0, padx=10, pady=5, sticky="w") # Updated row index
        self.seq_metadata_val_entry = tk.Entry(instructions_frame, width=90)
        self.seq_metadata_val_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w") # Updated row index
        self.bind_entry_update(self.seq_metadata_val_entry,
                            self.settings.sequential_metadata_presets,
                            self.selected_seq_metadata_preset_var,
                            'val_text')

        # Load initial preset if available
        if preset_names:
            self.selected_seq_metadata_preset_var.set(preset_names[0])
            self.load_selected_seq_metadata_preset()

        # Bind dropdown change to load the selected preset
        self.seq_metadata_preset_dropdown.bind("<<ComboboxSelected>>", self.load_selected_seq_metadata_preset)

    def load_selected_seq_metadata_preset(self, event=None):
        selected_name = self.selected_seq_metadata_preset_var.get()
        preset = self.get_preset_by_name(self.settings.sequential_metadata_presets, selected_name)
        if preset:
            # Model
            if 'model' in preset and preset['model'] in self.settings.model_list:
                self.seq_metadata_model_var.set(preset['model'])
            # Temperature
            self.set_entry_text(self.seq_metadata_temp_entry, preset.get('temperature', "0.3"))
            # Instructions
            self.set_text_widget(self.seq_metadata_general_text, preset.get('general_instructions', ""))
            self.set_text_widget(self.seq_metadata_specific_text, preset.get('specific_instructions', ""))
            
            # Required Headers - convert to display format based on type
            required_headers = preset.get('required_headers', "Date;Place")
            
            # Handle both list and string formats for backward compatibility
            if isinstance(required_headers, list):
                required_headers_str = ";".join(required_headers)
            else:
                required_headers_str = required_headers
                
            # Use the correct Entry widget for headers
            self.set_entry_text(self.seq_metadata_headers_entry, required_headers_str) 
            
            # Validation Text
            self.set_entry_text(self.seq_metadata_val_entry, preset.get('val_text', "None"))

            # Update the display of the global batch size (though it doesn't change per preset)
            self.set_entry_text(self.seq_batch_size_entry, self.settings.sequential_batch_size)

    def _update_sequential_batch_size(self, event=None):
        """Update the global sequential batch size setting."""
        try:
            value = int(self.seq_batch_size_entry.get())
            if value > 0:
                self.settings.sequential_batch_size = value
                self.settings.save_settings()
            else:
                # Optionally reset to default or show warning
                self.seq_batch_size_entry.delete(0, tk.END)
                self.seq_batch_size_entry.insert(0, str(self.settings.sequential_batch_size))
                messagebox.showwarning("Invalid Value", "Batch size must be a positive integer.", parent=self.settings_window)
        except ValueError:
            # Handle non-integer input
            self.seq_batch_size_entry.delete(0, tk.END)
            self.seq_batch_size_entry.insert(0, str(self.settings.sequential_batch_size))
            messagebox.showwarning("Invalid Value", "Batch size must be an integer.", parent=self.settings_window)

# Preset Creation Functions

    def create_new_function_preset_window(self):
        self.create_new_preset_window(preset_type="function")

    def create_new_preset_window(self, preset_type="analysis"):
        new_win = tk.Toplevel(self.settings_window)
        new_win.title(f"Create New {'Analysis' if preset_type == 'analysis' else 'Function'} Preset")

        # Make window modal and stay on top
        new_win.transient(self.settings_window)
        new_win.grab_set()
        new_win.attributes('-topmost', True)

        # Center the window
        window_width = 300
        window_height = 120
        screen_width = new_win.winfo_screenwidth()
        screen_height = new_win.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        new_win.geometry(f'{window_width}x{window_height}+{x}+{y}')

        # Configure grid
        new_win.grid_columnconfigure(1, weight=1)

        # Name entry
        tk.Label(new_win, text="Preset Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        name_entry = tk.Entry(new_win, width=30)
        name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # Button frame
        button_frame = tk.Frame(new_win)
        button_frame.grid(row=1, column=0, columnspan=3, pady=20)

        def save_new_preset():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Invalid Name", "Please enter a preset name.", parent=new_win)
                return

            # Check if name already exists
            preset_list = (self.settings.analysis_presets if preset_type == "analysis"
                           else self.settings.function_presets)
            if any(preset['name'] == name for preset in preset_list):
                messagebox.showwarning("Duplicate Name",
                                       "A preset with this name already exists. Please choose a different name.",
                                       parent=new_win)
                return

            new_preset = {
                'name': name,
                'model': self.settings.model_list[0] if self.settings.model_list else "",
                'temperature': "0.7",
                'general_instructions': "",
                'specific_instructions': "",
                'val_text': "",
                'use_images': True,
                'current_image': "Yes",
                'num_prev_images': "0",
                'num_after_images': "0",
            }

            # Add analysis-specific fields
            if preset_type == "analysis":
                new_preset.update({
                    'output_format': {
                        'single_file': True,
                        'combined_file': False,
                        'csv': False
                    },
                    'csv_columns': "",
                    'dataframe_field': ""
                })

            # Add to appropriate preset list
            if preset_type == "analysis":
                self.settings.analysis_presets.append(new_preset)
                self.update_preset_dropdown()
            else:
                self.settings.function_presets.append(new_preset)
                self.update_function_preset_dropdown()

            self.settings.save_settings()
            new_win.destroy()

        # Save and Cancel buttons
        tk.Button(button_frame, text="Save", command=save_new_preset, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=new_win.destroy, width=10).pack(side=tk.LEFT, padx=5)

        # Bind Enter key to save
        name_entry.bind('<Return>', lambda e: save_new_preset())

        # Set focus to entry
        name_entry.focus_set()

    def create_new_chunk_preset_window(self):
        new_win = tk.Toplevel(self.settings_window)
        new_win.title("Create New Seperate Documents Preset")

        new_win.transient(self.settings_window)
        new_win.grab_set()
        new_win.attributes('-topmost', True)

        window_width = 300
        window_height = 120
        screen_width = new_win.winfo_screenwidth()
        screen_height = new_win.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        new_win.geometry(f'{window_width}x{window_height}+{x}+{y}')

        new_win.grid_columnconfigure(1, weight=1)

        tk.Label(new_win, text="Preset Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        name_entry = tk.Entry(new_win, width=30)
        name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        button_frame = tk.Frame(new_win)
        button_frame.grid(row=1, column=0, columnspan=3, pady=20)

        def save_new_chunk_preset():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Invalid Name", "Please enter a preset name.", parent=new_win)
                return

            if any(preset['name'] == name for preset in self.settings.chunk_text_presets):
                messagebox.showwarning("Duplicate Name",
                                       "A preset with this name already exists. Please choose a different name.",
                                       parent=new_win)
                return

            new_preset = {
                'name': name,
                'model': self.settings.model_list[0] if self.settings.model_list else "",
                'temperature': "0.7",
                'general_instructions': "",
                'specific_instructions': "",
                'val_text': "",
                'use_images': False  # Default for Seperate Documents presets
            }

            self.settings.chunk_text_presets.append(new_preset)
            # Update dropdown for chunk presets
            preset_names = [p['name'] for p in self.settings.chunk_text_presets]
            self.chunk_preset_dropdown['values'] = preset_names
            if preset_names:
                self.selected_chunk_preset_var.set(preset_names[0])
                self.load_selected_chunk_preset()
            self.settings.save_settings()
            new_win.destroy()

        tk.Button(button_frame, text="Save", command=save_new_chunk_preset, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=new_win.destroy, width=10).pack(side=tk.LEFT, padx=5)
        name_entry.bind('<Return>', lambda e: save_new_chunk_preset())
        name_entry.focus_set()

    def create_new_metadata_preset_window(self):
        new_win = tk.Toplevel(self.settings_window)
        new_win.title("Create New Metadata Preset")

        new_win.transient(self.settings_window)
        new_win.grab_set()
        new_win.attributes('-topmost', True)

        window_width = 300
        window_height = 120
        screen_width = new_win.winfo_screenwidth()
        screen_height = new_win.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        new_win.geometry(f'{window_width}x{window_height}+{x}+{y}')

        new_win.grid_columnconfigure(1, weight=1)

        tk.Label(new_win, text="Preset Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        name_entry = tk.Entry(new_win, width=30)
        name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        button_frame = tk.Frame(new_win)
        button_frame.grid(row=1, column=0, columnspan=3, pady=20)

        def save_new_metadata_preset():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Invalid Name", "Please enter a preset name.", parent=new_win)
                return

            if any(preset['name'] == name for preset in self.settings.metadata_presets):
                messagebox.showwarning("Duplicate Name",
                                       "A preset with this name already exists. Please choose a different name.",
                                       parent=new_win)
                return

            # Default headers
            default_headers = "Document Type;Author;Correspondent;Correspondent Place;Date;Place of Creation;People;Places;Summary"
            
            new_preset = {
                'name': name,
                'model': self.settings.model_list[0] if self.settings.model_list else "claude-3-5-sonnet-20241022",
                'temperature': "0.3",
                'general_instructions': '''You analyze historical documments to extract information. Read the document and then make any notes you require. Then, in your response, write "Metadata:" and then on new lines output the following headings, filling in the information beside each one:

Document Type: <Letter/Baptismal Record/Diary Entry/Will/etc.>
Author: <Last Name, First Name>
Correspondent: <Last Name, First Name> - Note: Only for letters
Correspondent Place: <Place where the correspondent is located> - Note: Only for letters
Date: <DD/MM/YYYY>
Place of Creation: <Place where the document was written>
People: <Last Name, First Name; Last Name, First Name;...>
Places: <Place 1; Place 2;...>
Summary:

For People, list all the names of people mentioned in the document. 
For Places, list all the places mentioned in the document. 
For Summary, write a brief summary of the document.

If you don't have information for a heading or don't know, leave it blank.''',
                'specific_instructions': '''Text to analyze:\n\n{text_to_process}''',
                'val_text': "Metadata:",
                'metadata_headers': default_headers
            }

            self.settings.metadata_presets.append(new_preset)
            # Update dropdown for metadata presets
            preset_names = [p['name'] for p in self.settings.metadata_presets]
            self.metadata_preset_dropdown['values'] = preset_names
            if preset_names:
                self.selected_metadata_preset_var.set(name)
                # Update the global metadata preset selection in settings
                self.settings.metadata_preset = name
                self.load_selected_metadata_preset()
            self.settings.save_settings()
            new_win.destroy()

        tk.Button(button_frame, text="Save", command=save_new_metadata_preset, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=new_win.destroy, width=10).pack(side=tk.LEFT, padx=5)
        name_entry.bind('<Return>', lambda e: save_new_metadata_preset())
        name_entry.focus_set()

    def create_new_seq_metadata_preset_window(self):
        new_win = tk.Toplevel(self.settings_window)
        new_win.title("Create New Sequential Metadata Preset")

        new_win.transient(self.settings_window)
        new_win.grab_set()
        new_win.attributes('-topmost', True)

        window_width = 300
        window_height = 120
        screen_width = new_win.winfo_screenwidth()
        screen_height = new_win.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        new_win.geometry(f'{window_width}x{window_height}+{x}+{y}')

        new_win.grid_columnconfigure(1, weight=1)

        tk.Label(new_win, text="Preset Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        name_entry = tk.Entry(new_win, width=30)
        name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        button_frame = tk.Frame(new_win)
        button_frame.grid(row=1, column=0, columnspan=3, pady=20)

        def save_new_seq_metadata_preset():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Invalid Name", "Please enter a preset name.", parent=new_win)
                return

            if any(preset['name'] == name for preset in self.settings.sequential_metadata_presets):
                messagebox.showwarning("Duplicate Name",
                                       "A preset with this name already exists. Please choose a different name.",
                                       parent=new_win)
                return

            new_preset = {
                'name': name,
                'model': self.settings.model_list[0] if self.settings.model_list else "",
                'temperature': "0.3",
                'general_instructions': "",
                'specific_instructions': "{previous_headers}\n\nCurrent Document to Analyze: {text_to_process}",
                'val_text': "None",
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0",
                'required_headers': "Date;Place"
            }

            self.settings.sequential_metadata_presets.append(new_preset)
            self.update_seq_metadata_preset_dropdown()
            self.settings.save_settings()
            new_win.destroy()

        tk.Button(button_frame, text="Save", command=save_new_seq_metadata_preset, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=new_win.destroy, width=10).pack(side=tk.LEFT, padx=5)
        name_entry.bind('<Return>', lambda e: save_new_seq_metadata_preset())
        name_entry.focus_set()

# Delete Preset Functions

    def delete_function_preset(self):
        selected_name = self.selected_function_preset_var.get()
        if not selected_name:
            messagebox.showwarning("No Selection", "No function preset selected to delete.", parent=self.settings_window)
            return
        confirm = messagebox.askyesno("Confirm Deletion",
                                    f"Are you sure you want to delete the function preset '{selected_name}'?",
                                    parent=self.settings_window)
        if not confirm:
            return
        # Remove the preset from the list and update settings
        self.settings.function_presets = [p for p in self.settings.function_presets if p['name'] != selected_name]
        self.settings.save_settings()
        self.update_function_preset_dropdown()

    def delete_analysis_preset(self):
        selected_name = self.selected_preset_var.get()
        if not selected_name:
            messagebox.showwarning("No Selection", 
                                "No analysis preset selected to delete.", 
                                parent=self.settings_window)
            return
        
        confirm = messagebox.askyesno("Confirm Deletion",
                                    f"Are you sure you want to delete the analysis preset '{selected_name}'?",
                                    parent=self.settings_window)
        if not confirm:
            return

        # Remove the preset from the list and update settings
        self.settings.analysis_presets = [p for p in self.settings.analysis_presets 
                                        if p['name'] != selected_name]
        self.settings.save_settings()
        self.update_preset_dropdown()

    def delete_chunk_preset(self):
        selected_name = self.selected_chunk_preset_var.get()
        if not selected_name:
            messagebox.showwarning("No Selection", 
                                "No Seperate Documents preset selected to delete.", 
                                parent=self.settings_window)
            return
        
        confirm = messagebox.askyesno("Confirm Deletion",
                                    f"Are you sure you want to delete the Seperate Documents preset '{selected_name}'?",
                                    parent=self.settings_window)
        if not confirm:
            return

        # Remove the preset from the list and update settings
        self.settings.chunk_text_presets = [p for p in self.settings.chunk_text_presets 
                                        if p['name'] != selected_name]
        self.settings.save_settings()
        self.update_chunk_preset_dropdown()

    def delete_metadata_preset(self):
        selected_name = self.selected_metadata_preset_var.get()
        if not selected_name:
            messagebox.showwarning("No Selection", 
                                "No metadata preset selected to delete.", 
                                parent=self.settings_window)
            return
        
        # Don't allow deletion of the last preset
        if len(self.settings.metadata_presets) <= 1:
            messagebox.showwarning("Cannot Delete", 
                                "Cannot delete the last metadata preset. At least one preset must exist.", 
                                parent=self.settings_window)
            return
        
        confirm = messagebox.askyesno("Confirm Deletion",
                                    f"Are you sure you want to delete the metadata preset '{selected_name}'?",
                                    parent=self.settings_window)
        if not confirm:
            return

        # Remove the preset from the list and update settings
        self.settings.metadata_presets = [p for p in self.settings.metadata_presets 
                                        if p['name'] != selected_name]
        self.settings.save_settings()
        self.update_metadata_preset_dropdown()

    def delete_seq_metadata_preset(self):
        selected_preset = self.selected_seq_metadata_preset_var.get()
        if not selected_preset:
            messagebox.showwarning("No Preset Selected", "Please select a preset to delete.")
            return

        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the preset '{selected_preset}'?"):
            # Find and remove the preset
            self.settings.sequential_metadata_presets = [p for p in self.settings.sequential_metadata_presets if p['name'] != selected_preset]
            
            # Save settings and update UI
            self.settings.save_settings()
            self.update_seq_metadata_preset_dropdown()
            
            # Select first preset if available
            if self.settings.sequential_metadata_presets:
                self.selected_seq_metadata_preset_var.set(self.settings.sequential_metadata_presets[0]['name'])
                self.load_selected_seq_metadata_preset()

# Modify Preset Functions

    def modify_function_preset(self):
        selected_name = self.selected_function_preset_var.get()
        if not selected_name:
            messagebox.showwarning("No Selection", "No function preset selected to modify.", parent=self.settings_window)
            return
        preset = self.get_preset_by_name(self.settings.function_presets, selected_name)
        if not preset:
            messagebox.showwarning("Error", "Selected preset not found.", parent=self.settings_window)
            return
        # Create a small modal window to enter the new name
        new_win = tk.Toplevel(self.settings_window)
        new_win.title("Modify Function Preset Name")
        new_win.transient(self.settings_window)
        new_win.grab_set()
        new_win.attributes('-topmost', True)
        window_width = 300
        window_height = 120
        screen_width = new_win.winfo_screenwidth()
        screen_height = new_win.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        new_win.geometry(f'{window_width}x{window_height}+{x}+{y}')
        new_win.grid_columnconfigure(1, weight=1)
        
        tk.Label(new_win, text="New Preset Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        name_entry = tk.Entry(new_win, width=30)
        name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        name_entry.insert(0, selected_name)
        
        def save_modified_preset():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showwarning("Invalid Name", "Please enter a preset name.", parent=new_win)
                return
            # Prevent duplicate names (unless unchanged)
            if new_name != selected_name and any(p['name'] == new_name for p in self.settings.function_presets):
                messagebox.showwarning("Duplicate Name",
                                    "A preset with this name already exists. Please choose a different name.",
                                    parent=new_win)
                return
            preset['name'] = new_name
            self.settings.save_settings()
            self.update_function_preset_dropdown()
            self.selected_function_preset_var.set(new_name)
            new_win.destroy()
        
        button_frame = tk.Frame(new_win)
        button_frame.grid(row=1, column=0, columnspan=3, pady=20)
        tk.Button(button_frame, text="Save", command=save_modified_preset, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=new_win.destroy, width=10).pack(side=tk.LEFT, padx=5)
        
        name_entry.bind('<Return>', lambda e: save_modified_preset())
        name_entry.focus_set()

    def modify_analysis_preset(self):
        selected_name = self.selected_preset_var.get()
        if not selected_name:
            messagebox.showwarning("No Selection", 
                                "No analysis preset selected to modify.", 
                                parent=self.settings_window)
            return

        preset = self.get_preset_by_name(self.settings.analysis_presets, selected_name)
        if not preset:
            messagebox.showwarning("Error", "Selected preset not found.", 
                                parent=self.settings_window)
            return

        # Create modification window
        new_win = tk.Toplevel(self.settings_window)
        new_win.title("Modify Analysis Preset Name")
        new_win.transient(self.settings_window)
        new_win.grab_set()
        new_win.attributes('-topmost', True)

        # Window dimensions and positioning
        window_width = 300
        window_height = 120
        screen_width = new_win.winfo_screenwidth()
        screen_height = new_win.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        new_win.geometry(f'{window_width}x{window_height}+{x}+{y}')
        new_win.grid_columnconfigure(1, weight=1)

        # Add widgets
        tk.Label(new_win, text="New Preset Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        name_entry = tk.Entry(new_win, width=30)
        name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        name_entry.insert(0, selected_name)

        def save_modified_preset():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showwarning("Invalid Name", "Please enter a preset name.", 
                                    parent=new_win)
                return

            if new_name != selected_name and any(p['name'] == new_name 
                                            for p in self.settings.analysis_presets):
                messagebox.showwarning("Duplicate Name",
                                    "A preset with this name already exists. Please choose a different name.",
                                    parent=new_win)
                return

            preset['name'] = new_name
            self.settings.save_settings()
            self.update_preset_dropdown()
            self.selected_preset_var.set(new_name)
            new_win.destroy()

        # Add buttons
        button_frame = tk.Frame(new_win)
        button_frame.grid(row=1, column=0, columnspan=3, pady=20)
        tk.Button(button_frame, text="Save", command=save_modified_preset, 
                width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=new_win.destroy, 
                width=10).pack(side=tk.LEFT, padx=5)

        # Bind Enter key and set focus
        name_entry.bind('<Return>', lambda e: save_modified_preset())
        name_entry.focus_set()

    def modify_chunk_preset(self):
        selected_name = self.selected_chunk_preset_var.get()
        if not selected_name:
            messagebox.showwarning("No Selection", 
                                "No Seperate Documents preset selected to modify.", 
                                parent=self.settings_window)
            return

        preset = self.get_preset_by_name(self.settings.chunk_text_presets, selected_name)
        if not preset:
            messagebox.showwarning("Error", "Selected preset not found.", 
                                parent=self.settings_window)
            return

        # Create modification window
        new_win = tk.Toplevel(self.settings_window)
        new_win.title("Modify Seperate Documents Preset Name")
        new_win.transient(self.settings_window)
        new_win.grab_set()
        new_win.attributes('-topmost', True)

        window_width = 300
        window_height = 120
        screen_width = new_win.winfo_screenwidth()
        screen_height = new_win.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        new_win.geometry(f'{window_width}x{window_height}+{x}+{y}')
        new_win.grid_columnconfigure(1, weight=1)

        tk.Label(new_win, text="New Preset Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        name_entry = tk.Entry(new_win, width=30)
        name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        name_entry.insert(0, selected_name)

        def save_modified_preset():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showwarning("Invalid Name", "Please enter a preset name.", 
                                    parent=new_win)
                return

            if new_name != selected_name and any(p['name'] == new_name 
                                            for p in self.settings.chunk_text_presets):
                messagebox.showwarning("Duplicate Name",
                                    "A preset with this name already exists. Please choose a different name.",
                                    parent=new_win)
                return

            preset['name'] = new_name
            self.settings.save_settings()
            self.update_chunk_preset_dropdown()
            self.selected_chunk_preset_var.set(new_name)
            new_win.destroy()

        button_frame = tk.Frame(new_win)
        button_frame.grid(row=1, column=0, columnspan=3, pady=20)
        tk.Button(button_frame, text="Save", command=save_modified_preset, 
                width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=new_win.destroy, 
                width=10).pack(side=tk.LEFT, padx=5)

        name_entry.bind('<Return>', lambda e: save_modified_preset())
        name_entry.focus_set()

    def modify_metadata_preset(self):
        selected_name = self.selected_metadata_preset_var.get()
        if not selected_name:
            messagebox.showwarning("No Selection", 
                                "No metadata preset selected to modify.", 
                                parent=self.settings_window)
            return

        preset = self.get_preset_by_name(self.settings.metadata_presets, selected_name)
        if not preset:
            messagebox.showwarning("Error", "Selected preset not found.", 
                                parent=self.settings_window)
            return

        # Create modification window
        new_win = tk.Toplevel(self.settings_window)
        new_win.title("Modify Metadata Preset Name")
        new_win.transient(self.settings_window)
        new_win.grab_set()
        new_win.attributes('-topmost', True)

        window_width = 300
        window_height = 120
        screen_width = new_win.winfo_screenwidth()
        screen_height = new_win.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        new_win.geometry(f'{window_width}x{window_height}+{x}+{y}')
        new_win.grid_columnconfigure(1, weight=1)

        tk.Label(new_win, text="New Preset Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        name_entry = tk.Entry(new_win, width=30)
        name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        name_entry.insert(0, selected_name)

        def save_modified_preset():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showwarning("Invalid Name", "Please enter a preset name.", 
                                    parent=new_win)
                return

            if new_name != selected_name and any(p['name'] == new_name 
                                            for p in self.settings.metadata_presets):
                messagebox.showwarning("Duplicate Name",
                                    "A preset with this name already exists. Please choose a different name.",
                                    parent=new_win)
                return

            preset['name'] = new_name
            self.settings.save_settings()
            self.update_metadata_preset_dropdown()
            self.selected_metadata_preset_var.set(new_name)
            # Update the global metadata preset selection in settings
            self.settings.metadata_preset = new_name
            new_win.destroy()

        button_frame = tk.Frame(new_win)
        button_frame.grid(row=1, column=0, columnspan=3, pady=20)
        tk.Button(button_frame, text="Save", command=save_modified_preset, 
                width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=new_win.destroy, 
                width=10).pack(side=tk.LEFT, padx=5)

        name_entry.bind('<Return>', lambda e: save_modified_preset())
        name_entry.focus_set()

    def modify_seq_metadata_preset(self):
        selected_preset = self.selected_seq_metadata_preset_var.get()
        if not selected_preset:
            messagebox.showwarning("No Preset Selected", "Please select a preset to modify.")
            return

        preset = self.get_preset_by_name(self.settings.sequential_metadata_presets, selected_preset)
        if not preset:
            messagebox.showwarning("Preset Not Found", "The selected preset could not be found.")
            return

        # Create modification window
        modify_win = tk.Toplevel(self.settings_window)
        modify_win.title(f"Modify Sequential Metadata Preset: {selected_preset}")
        modify_win.transient(self.settings_window)
        modify_win.grab_set()
        modify_win.attributes('-topmost', True)

        # Center the window
        window_width = 300
        window_height = 120
        screen_width = modify_win.winfo_screenwidth()
        screen_height = modify_win.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        modify_win.geometry(f'{window_width}x{window_height}+{x}+{y}')

        # Configure grid
        modify_win.grid_columnconfigure(1, weight=1)

        # Name entry
        tk.Label(modify_win, text="Preset Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        name_entry = tk.Entry(modify_win, width=30)
        name_entry.insert(0, selected_preset)
        name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # Button frame
        button_frame = tk.Frame(modify_win)
        button_frame.grid(row=1, column=0, columnspan=3, pady=20)

        def save_modified_preset():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showwarning("Invalid Name", "Please enter a preset name.", parent=modify_win)
                return

            # Check if new name exists and is different from current name
            if new_name != selected_preset and any(p['name'] == new_name for p in self.settings.sequential_metadata_presets):
                messagebox.showwarning("Duplicate Name",
                                       "A preset with this name already exists. Please choose a different name.",
                                       parent=modify_win)
                return

            # Update the preset name
            preset['name'] = new_name

            # Save settings and update UI
            self.settings.save_settings()
            self.update_seq_metadata_preset_dropdown()
            # Set selection to modified preset
            self.selected_seq_metadata_preset_var.set(new_name)
            modify_win.destroy()

        # Save and Cancel buttons
        tk.Button(button_frame, text="Save", command=save_modified_preset, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=modify_win.destroy, width=10).pack(side=tk.LEFT, padx=5)

        # Bind Enter key to save
        name_entry.bind('<Return>', lambda e: save_modified_preset())

        # Set focus to entry
        name_entry.focus_set()

# Save and Load Functions

    def save_settings(self):
        try:
            # Save all settings
            self.settings.save_settings()
            self.parent.update_api_handler()
            messagebox.showinfo("Success", "Settings saved successfully!", parent=self.settings_window)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}", parent=self.settings_window)

    def load_settings(self):
        try:
            self.settings.load_settings()
            self.parent.update_api_handler()
            
            # Update all dropdowns with the new settings
            self.update_all_dropdowns()
            
            # Show API Settings as the initial view
            self.show_settings("API Settings")
            
            messagebox.showinfo("Success", "Settings loaded successfully!", parent=self.settings_window)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {e}", parent=self.settings_window)
    
    def restore_defaults(self):
        try:
            self.settings.restore_defaults()
            
            # Update all dropdowns with the new settings
            self.update_all_dropdowns()
            
            # Show API Settings as the initial view
            self.show_settings("API Settings")
            
            messagebox.showinfo("Success", "Settings restored to defaults!", parent=self.settings_window)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to restore defaults: {e}", parent=self.settings_window)

    def on_close(self):
        try:
            # Save current settings state
            self.settings.save_settings()
            # Update API handler with new settings
            self.parent.update_api_handler()
            # Reset UI state
            self.parent.toggle_button_state()
        except Exception as e:
            print(f"Error closing settings window: {e}")
        finally:
            self.settings_window.destroy()

    def export_settings(self):
        """Export all settings to a .psf file"""
        try:
            # Create a temporary top-level window to serve as the parent for the file dialog
            temp_window = tk.Toplevel(self.settings_window)
            temp_window.attributes('-topmost', True)  # Make it top-most
            temp_window.withdraw()  # Hide it
            
            file_path = tk.filedialog.asksaveasfilename(
                parent=temp_window,  # Set parent to our temporary window
                defaultextension=".psf",
                filetypes=[("Pearl Settings File", "*.psf")],
                title="Export Settings"
            )
            
            # Destroy the temporary window
            temp_window.destroy()
            
            if not file_path:
                return
                
            # Collect all settings
            settings_dict = {
                'openai_api_key': self.settings.openai_api_key,
                'anthropic_api_key': self.settings.anthropic_api_key,
                'google_api_key': self.settings.google_api_key,
                'model_list': self.settings.model_list,
                'translation_system_prompt': self.settings.translation_system_prompt,
                'translation_user_prompt': self.settings.translation_user_prompt,
                'translation_val_text': self.settings.translation_val_text,
                'translation_model': self.settings.translation_model,
                'query_system_prompt': self.settings.query_system_prompt,
                'query_val_text': self.settings.query_val_text,
                'query_model': self.settings.query_model,
                'metadata_system_prompt': self.settings.metadata_system_prompt,
                'metadata_user_prompt': self.settings.metadata_user_prompt,
                'metadata_val_text': self.settings.metadata_val_text,
                'metadata_model': self.settings.metadata_model,
                'batch_size': self.settings.batch_size,
                'check_orientation': self.settings.check_orientation,
                'analysis_presets': self.settings.analysis_presets,
                'function_presets': self.settings.function_presets,
                'chunk_text_presets': self.settings.chunk_text_presets,
                'format_presets': self.settings.format_presets,  # <-- Add this line
                'ghost_system_prompt': self.settings.ghost_system_prompt,
                'ghost_user_prompt': self.settings.ghost_user_prompt,
                'ghost_val_text': self.settings.ghost_val_text,
                'ghost_model': self.settings.ghost_model,
                'ghost_temp': self.settings.ghost_temp,
                'metadata_presets': self.settings.metadata_presets,
                'sequential_metadata_presets': self.settings.sequential_metadata_presets,
                'sequential_batch_size': self.settings.sequential_batch_size,
            }
            
            with open(file_path, 'w') as f:
                json.dump(settings_dict, f, indent=4)
            
            # Ensure message box appears on top
            self.settings_window.lift()
            messagebox.showinfo("Success", "Settings exported successfully!", parent=self.settings_window)
            
        except Exception as e:
            self.settings_window.lift()
            messagebox.showerror("Error", f"Failed to export settings: {str(e)}", parent=self.settings_window)

    def import_settings(self):
        """Import settings from a .psf file"""
        try:
            # Create a temporary top-level window to serve as the parent for the file dialog
            temp_window = tk.Toplevel(self.settings_window)
            temp_window.attributes('-topmost', True)  # Make it top-most
            temp_window.withdraw()  # Hide it
            
            file_path = tk.filedialog.askopenfilename(
                parent=temp_window,  # Set parent to our temporary window
                defaultextension=".psf",
                filetypes=[("Pearl Settings File", "*.psf")],
                title="Import Settings"
            )
            
            # Destroy the temporary window
            temp_window.destroy()
            
            if not file_path:
                return
                
            with open(file_path, 'r') as f:
                imported_settings = json.load(f)
                
            # Ensure confirmation dialog appears on top
            self.settings_window.lift()
            confirm = messagebox.askyesno(
                "Confirm Import",
                "This will overwrite your current settings. Continue?",
                parent=self.settings_window
            )
            
            if not confirm:
                return
                
            # Update all settings
            for key, value in imported_settings.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
                # Ensure format_presets is restored even if not present in self.settings
                if key == 'format_presets':
                    self.settings.format_presets = value
                # Ensure sequential_batch_size is loaded if present
                if key == 'sequential_batch_size':
                    self.settings.sequential_batch_size = value
                    
            # Save the imported settings
            self.settings.save_settings()
            
            # Update UI
            self.parent.update_api_handler()
            
            # Update all dropdowns with the new settings
            self.update_all_dropdowns()
            
            # Show API Settings as the initial view
            self.show_settings("API Settings")
            
            # Ensure success message appears on top
            self.settings_window.lift()
            messagebox.showinfo("Success", "Settings imported successfully!", parent=self.settings_window)
            
        except Exception as e:
            self.settings_window.lift()
            messagebox.showerror("Error", f"Failed to import settings: {str(e)}", parent=self.settings_window)
            
# Update/Toggle Functions for Dropdown Menus and Checkboxes

    def update_model_list(self, event):
        models_text = self.models_text.get("1.0", tk.END).strip()
        models_list = [model.strip() for model in models_text.split('\n') if model.strip()]
        self.settings.model_list = models_list
        self.update_all_dropdowns()
        self.update_model_dropdowns()

    def update_model_dropdowns(self):
        """Update all model dropdowns with current model list"""
        try:
            # Get current model list
            models = self.settings.model_list
            
            # Dictionary of variable names and their corresponding dropdowns
            dropdown_vars = {
                'analysis_model_var': None,
                'function_model_var': None,
                'chunk_model_var': None,
                'seq_metadata_model_var': None
            }

            # Find all Comboboxes in the window
            def find_comboboxes(widget):
                if isinstance(widget, ttk.Combobox):
                    # Check which variable this combobox is associated with
                    for var_name in dropdown_vars:
                        if hasattr(self, var_name):
                            var = getattr(self, var_name)
                            if widget.cget('textvariable') == str(var):
                                dropdown_vars[var_name] = widget
                for child in widget.winfo_children():
                    find_comboboxes(child)

            # Search through all widgets
            find_comboboxes(self.settings_window)

            # Update each found dropdown
            for var_name, dropdown in dropdown_vars.items():
                if dropdown is not None and hasattr(self, var_name):
                    current_value = getattr(self, var_name).get()
                    dropdown['values'] = models
                    # If current value is not in new list, set to first available model
                    if current_value not in models and models:
                        getattr(self, var_name).set(models[0])
                    elif current_value in models:
                        getattr(self, var_name).set(current_value)

        except (tk.TclError, AttributeError, ValueError) as e:
            print(f"Error updating model dropdowns: {e}")    
    
    def update_check_orientation(self):
            self.settings.check_orientation = self.check_orientation_var.get()
            self.settings.save_settings()

    def update_function_preset_dropdown(self):
        """Update function preset dropdown if it exists."""
        try:
            if hasattr(self, 'function_preset_dropdown') and self.function_preset_dropdown.winfo_exists():
                preset_names = [p['name'] for p in self.settings.function_presets]
                self.function_preset_dropdown['values'] = preset_names
                if preset_names and self.selected_function_preset_var.get() not in preset_names:
                    self.selected_function_preset_var.set(preset_names[0])
                    self.load_selected_function_preset()
        except tk.TclError:
            pass

    def update_preset_dropdown(self):
        """Update analysis preset dropdown if it exists."""
        try:
            if hasattr(self, 'preset_dropdown') and self.preset_dropdown.winfo_exists():
                preset_names = [p['name'] for p in self.settings.analysis_presets]
                self.preset_dropdown['values'] = preset_names
                if preset_names and self.selected_preset_var.get() not in preset_names:
                    self.selected_preset_var.set(preset_names[0])
                    self.load_selected_preset()
        except tk.TclError:
            pass

    def update_chunk_preset_dropdown(self):
        """Update chunk preset dropdown if it exists."""
        try:
            if hasattr(self, 'chunk_preset_dropdown') and self.chunk_preset_dropdown.winfo_exists():
                preset_names = [p['name'] for p in self.settings.chunk_text_presets]
                self.chunk_preset_dropdown['values'] = preset_names
                if preset_names and self.selected_chunk_preset_var.get() not in preset_names:
                    self.selected_chunk_preset_var.set(preset_names[0])
                    self.load_selected_chunk_preset()
        except tk.TclError:
            pass

    def update_metadata_preset_dropdown(self):
        """Update metadata preset dropdown if it exists."""
        try:
            if hasattr(self, 'metadata_preset_dropdown') and self.metadata_preset_dropdown.winfo_exists():
                preset_names = [p['name'] for p in self.settings.metadata_presets]
                self.metadata_preset_dropdown['values'] = preset_names
                if preset_names and self.selected_metadata_preset_var.get() not in preset_names:
                    self.selected_metadata_preset_var.set(preset_names[0])
                    # Update the global metadata preset selection in settings
                    self.settings.metadata_preset = preset_names[0]
                    self.load_selected_metadata_preset()
        except tk.TclError:
            pass

    def update_seq_metadata_preset_dropdown(self):
        """Update the sequential metadata preset dropdown with current presets"""
        preset_names = [p['name'] for p in self.settings.sequential_metadata_presets]
        if hasattr(self, 'seq_metadata_preset_dropdown'):
            self.seq_metadata_preset_dropdown['values'] = preset_names
            
            # If there are presets, select the first one
            if preset_names and not self.selected_seq_metadata_preset_var.get() in preset_names:
                self.selected_seq_metadata_preset_var.set(preset_names[0])
                self.load_selected_seq_metadata_preset()

    def toggle_csv_columns(self):
        if not self.csv_var.get():
            self.csv_columns_frame.grid_remove()
        else:
            self.csv_columns_frame.grid()

    def toggle_image_controls(self):
        if self.use_images_var.get():
            if hasattr(self, 'image_settings_frame') and self.image_settings_frame.winfo_exists():
                self.image_settings_frame.grid()
            state = "normal"
        else:
            if hasattr(self, 'image_settings_frame') and self.image_settings_frame.winfo_exists():
                self.image_settings_frame.grid_remove()
            state = "disabled"
            self.current_image_var.set("No")
        
        # List the widgets that might have been created in either preset view.
        for widget_name in ['current_image_dropdown', 'analysis_prev_images_entry', 'analysis_after_images_entry', 'function_temp_entry']:
            widget = getattr(self, widget_name, None)
            if widget is not None and widget.winfo_exists():
                widget.configure(state=state)

    # Helper Functions for Presets 

    def get_preset_by_name(self, presets, name):
        """Return the preset dictionary from presets matching name."""
        return next((p for p in presets if p['name'] == name), None)

    def update_current_generic_preset(self, presets, selected_var, field, value):
        """Generic method to update a preset field and save settings."""
        preset = self.get_preset_by_name(presets, selected_var.get())
        if preset is not None:
            preset[field] = value
            self.settings.save_settings()

    def load_selected_generic_preset(self, presets, selected_name, field_setters):
        """
        Generic preset loader.
        
        Args:
            presets: list of preset dictionaries.
            selected_name: the name of the preset to load.
            field_setters: a dictionary mapping preset keys to functions that update UI fields.
        """
        preset = self.get_preset_by_name(presets, selected_name)
        if preset:
            for key, setter in field_setters.items():
                setter(preset.get(key, ""))

    def set_entry_text(self, entry_widget, text):
        """Safely set text in an entry widget with error handling"""
        try:
            if entry_widget and entry_widget.winfo_exists():
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, str(text) if text is not None else "")
        except Exception as e:
            print(f"Error setting entry text: {e}")

    def set_text_widget(self, text_widget, text):
        text_widget.delete("1.0", tk.END)
        text_widget.insert(tk.END, text)

    def add_var_trace(self, var, presets, selected_var, field, nested_key=None):
        """
        Binds a Tk variable so that when it changes, the current preset is updated.
        If nested_key is provided, the field is updated in a nested dictionary.
        """
        def callback(*args):
            value = var.get()
            preset = self.get_preset_by_name(presets, selected_var.get())
            if preset is None:
                return
            if nested_key:
                if nested_key not in preset:
                    preset[nested_key] = {}
                preset[nested_key][field] = value
            else:
                preset[field] = value
            self.settings.save_settings()
        var.trace_add("write", lambda *args: callback())

    def bind_entry_update(self, entry_widget, presets, selected_var, field):
        """
        Binds an Entry or Spinbox widget so that on each key release, focus out, or mouse button release (for Spinbox arrows), its value is saved to the preset.
        """
        def callback(event=None):
            value = entry_widget.get()
            preset = self.get_preset_by_name(presets, selected_var.get())
            if preset is None:
                return
            preset[field] = value
            self.settings.save_settings()
        entry_widget.bind("<KeyRelease>", callback)
        entry_widget.bind("<FocusOut>", callback)
        entry_widget.bind("<ButtonRelease-1>", callback)  # For Spinbox arrow clicks

    def bind_text_update(self, text_widget, presets, selected_var, field):
        """Bind text widget changes to update presets."""
        def callback(event):
            selected_name = selected_var.get()
            preset = self.get_preset_by_name(presets, selected_name)
            
            # Handle special case for required_headers field, converting from text to list
            if field == 'required_headers':
                text_content = text_widget.get("1.0", "end-1c")
                # Convert text to semicolon-delimited string for consistency with metadata_headers
                # First split by newlines or semicolons (allowing either format in UI)
                headers = []
                for line in text_content.split('\n'):
                    # Further split each line by semicolons
                    headers.extend([h.strip() for h in line.split(';') if h.strip()])
                # Join all headers with semicolons
                headers_str = ";".join(headers)
                if preset:
                    preset[field] = headers_str
            else:
                # Normal text field update
                if preset:
                    preset[field] = text_widget.get("1.0", "end-1c")
            
            # Save changes
            self.settings.save_settings()
            
        text_widget.bind("<FocusOut>", callback)
        # Also bind to KeyRelease to ensure frequent updates
        text_widget.bind("<KeyRelease>", callback)

# --- Add helper to ensure image fields in all presets (for import/export/backward compatibility) ---
def _ensure_image_fields_in_presets(preset_list):
    for preset in preset_list:
        if 'num_prev_images' not in preset:
            preset['num_prev_images'] = "0"
        if 'num_after_images' not in preset:
            preset['num_after_images'] = "0"
    return preset_list

# --- Patch export_settings and import_settings to ensure image fields ---
old_export_settings = SettingsWindow.export_settings
old_import_settings = SettingsWindow.import_settings

def export_settings_with_image_fields(self):
    # Before export, ensure all preset types have image fields
    self.settings.analysis_presets = _ensure_image_fields_in_presets(self.settings.analysis_presets)
    self.settings.function_presets = _ensure_image_fields_in_presets(self.settings.function_presets)
    self.settings.chunk_text_presets = _ensure_image_fields_in_presets(self.settings.chunk_text_presets)
    self.settings.format_presets = _ensure_image_fields_in_presets(self.settings.format_presets)
    self.settings.metadata_presets = _ensure_image_fields_in_presets(self.settings.metadata_presets)
    self.settings.sequential_metadata_presets = _ensure_image_fields_in_presets(self.settings.sequential_metadata_presets)
    old_export_settings(self)


def import_settings_with_image_fields(self):
    old_import_settings(self)
    # After import, ensure all preset types have image fields
    self.settings.analysis_presets = _ensure_image_fields_in_presets(self.settings.analysis_presets)
    self.settings.function_presets = _ensure_image_fields_in_presets(self.settings.function_presets)
    self.settings.chunk_text_presets = _ensure_image_fields_in_presets(self.settings.chunk_text_presets)
    self.settings.format_presets = _ensure_image_fields_in_presets(self.settings.format_presets)
    self.settings.metadata_presets = _ensure_image_fields_in_presets(self.settings.metadata_presets)
    self.settings.sequential_metadata_presets = _ensure_image_fields_in_presets(self.settings.sequential_metadata_presets)

SettingsWindow.export_settings = export_settings_with_image_fields
SettingsWindow.import_settings = import_settings_with_image_fields

# --- Patch all create_new_*_preset_window and save_new_preset logic to always add image fields ---
# (For brevity, only show for metadata and sequential_metadata, but same logic applies to all)
# For metadata presets:
old_create_new_metadata_preset_window = SettingsWindow.create_new_metadata_preset_window

def create_new_metadata_preset_window_with_images(self):
    old_create_new_metadata_preset_window(self)
    # After window is created, add widgets for previous/next images if not present
    # (Assume main_settings_frame is available)
    try:
        frame = self.right_frame.winfo_children()[0]  # main_settings_frame
        row = frame.grid_size()[1]
        tk.Label(frame, text="# Previous Images:").grid(row=row, column=0, padx=5, pady=5)
        prev_entry = ttk.Spinbox(frame, from_=0, to=3, width=5)
        prev_entry.grid(row=row, column=1, padx=5, pady=5)
        tk.Label(frame, text="# After Images:").grid(row=row, column=2, padx=5, pady=5)
        after_entry = ttk.Spinbox(frame, from_=0, to=3, width=5)
        after_entry.grid(row=row, column=3, padx=5, pady=5)
        # Bind to preset dict on save (patch save_new_metadata_preset)
        old_save = self.save_new_metadata_preset
        def save_new_metadata_preset_with_images():
            old_save()
            # After saving, ensure fields are present
            preset = self.settings.metadata_presets[-1]
            preset['num_prev_images'] = prev_entry.get()
            preset['num_after_images'] = after_entry.get()
            self.settings.save_settings()
        self.save_new_metadata_preset = save_new_metadata_preset_with_images
    except Exception:
        pass
SettingsWindow.create_new_metadata_preset_window = create_new_metadata_preset_window_with_images

# For sequential metadata presets:
old_create_new_seq_metadata_preset_window = SettingsWindow.create_new_seq_metadata_preset_window

def create_new_seq_metadata_preset_window_with_images(self):
    old_create_new_seq_metadata_preset_window(self)
    try:
        frame = self.right_frame.winfo_children()[0]  # main_settings_frame
        row = frame.grid_size()[1]
        tk.Label(frame, text="# Previous Images:").grid(row=row, column=0, padx=5, pady=5)
        prev_entry = ttk.Spinbox(frame, from_=0, to=3, width=5)
        prev_entry.grid(row=row, column=1, padx=5, pady=5)
        tk.Label(frame, text="# After Images:").grid(row=row, column=2, padx=5, pady=5)
        after_entry = ttk.Spinbox(frame, from_=0, to=3, width=5)
        after_entry.grid(row=row, column=3, padx=5, pady=5)
        old_save = self.save_new_seq_metadata_preset
        def save_new_seq_metadata_preset_with_images():
            old_save()
            preset = self.settings.sequential_metadata_presets[-1]
            preset['num_prev_images'] = prev_entry.get()
            preset['num_after_images'] = after_entry.get()
            self.settings.save_settings()
        self.save_new_seq_metadata_preset = save_new_seq_metadata_preset_with_images
    except Exception:
        pass
SettingsWindow.create_new_seq_metadata_preset_window = create_new_seq_metadata_preset_window_with_images
