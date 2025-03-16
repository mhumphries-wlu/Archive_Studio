# util/SettingsWindow.py

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
        if self.mode == "T_PEARL":
            menu_options = [
                "APIs and Login Settings",
                "Models and Import Settings",
                "",
                "Default Functions",
                "Seperate Documents Presets",
                "",
                "Load Settings",
                "Save Settings",
                "Export Settings",
                "Import Settings",
                "Restore Defaults",
                "Done"
            ]
        elif self.mode == "DB_VIEWER":
            menu_options = [
                "APIs and Login Settings",
                "Models and Import Settings",
                "",
                "Custom Functions",  # Only show Custom Functions for DB_VIEWER
                "",
                "Load Settings",
                "Save Settings",
                "Export Settings",
                "Import Settings",
                "Restore Defaults",
                "Done"
            ]

        for i, option in enumerate(menu_options):
            if option == "":
                empty_label = tk.Label(self.left_frame, text="", height=1)
                empty_label.grid(row=i, column=0)
            else:
                button = tk.Button(self.left_frame, text=option, width=30,
                                   command=lambda opt=option: self.show_settings(opt))
                button.grid(row=i, column=0, padx=10, pady=5, sticky="w")

    def show_settings(self, option):
        for widget in self.right_frame.winfo_children():
            widget.destroy()
            
        # Handle settings display based on mode
        if self.mode == "DB_VIEWER" and option in ["Default Functions", "Seperate Documents Presets"]:
            return  # Don't show these options in DB_VIEWER mode
            
        if option == "APIs and Login Settings":
            self.show_api_settings()
        elif option == "Models and Import Settings":
            self.show_models_and_import_settings()
        elif option == "Default Functions" and self.mode == "T_PEARL":
            self.show_preset_functions_settings()
        elif option == "Custom Functions":
            self.show_analysis_presets_settings()
        elif option == "Seperate Documents Presets" and self.mode == "T_PEARL":
            self.show_chunk_text_presets_settings()
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
        explanation_label = tk.Label(self.right_frame,
                                     text="""The Metadata function analyzes documents to extract structured information about document type, people, places, and other key details.""",
                                     wraplength=675, justify=tk.LEFT)
        explanation_label.grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="w")

        model_label = tk.Label(self.right_frame, text="Select model for Metadata:")
        model_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.metadata_model_var = tk.StringVar(value=self.settings.metadata_model)
        dropdown = ttk.Combobox(self.right_frame,
                                textvariable=self.metadata_model_var,
                                values=self.settings.model_list,
                                state="readonly",
                                width=30)
        dropdown.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        dropdown.bind("<<ComboboxSelected>>",
                      lambda event: setattr(self.settings, 'metadata_model',
                                              self.metadata_model_var.get()))

        general_label = tk.Label(self.right_frame, text="General Instructions:")
        general_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.metadata_general_entry = tk.Text(self.right_frame, height=30, width=90, wrap=tk.WORD)
        self.metadata_general_entry.insert(tk.END, self.settings.metadata_system_prompt)
        self.metadata_general_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        general_scrollbar = tk.Scrollbar(self.right_frame, command=self.metadata_general_entry.yview)
        general_scrollbar.grid(row=2, column=2, sticky="ns")
        self.metadata_general_entry.config(yscrollcommand=general_scrollbar.set)

        detailed_label = tk.Label(self.right_frame, text="Detailed Instructions:")
        detailed_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.metadata_detailed_entry = tk.Text(self.right_frame, height=15, width=90, wrap=tk.WORD)
        self.metadata_detailed_entry.insert(tk.END, self.settings.metadata_user_prompt)
        self.metadata_detailed_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        detailed_scrollbar = tk.Scrollbar(self.right_frame, command=self.metadata_detailed_entry.yview)
        detailed_scrollbar.grid(row=3, column=2, sticky="ns")
        self.metadata_detailed_entry.config(yscrollcommand=detailed_scrollbar.set)

        val_label = tk.Label(self.right_frame, text="Validation Text:")
        val_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.metadata_val_label_entry = tk.Text(self.right_frame, height=1, width=60)
        self.metadata_val_label_entry.insert(tk.END, self.settings.metadata_val_text)
        self.metadata_val_label_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")

        # Bind the text widgets to update settings variables
        self.metadata_general_entry.bind("<KeyRelease>",
                                         lambda event: setattr(self.settings, 'metadata_system_prompt',
                                                                 self.metadata_general_entry.get("1.0", "end-1c")))
        self.metadata_detailed_entry.bind("<KeyRelease>",
                                          lambda event: setattr(self.settings, 'metadata_user_prompt',
                                                                  self.metadata_detailed_entry.get("1.0", "end-1c")))
        self.metadata_val_label_entry.bind("<KeyRelease>",
                                           lambda event: setattr(self.settings, 'metadata_val_text',
                                                                   self.metadata_val_label_entry.get("1.0", "end-1c")))

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

        # New preset button
        new_preset_button = tk.Button(main_settings_frame, text="+", 
                                        command=lambda: self.create_new_preset_window("analysis"))
        new_preset_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Add modify and delete buttons
        modify_button = tk.Button(main_settings_frame, text="Modify", 
                                    command=self.modify_analysis_preset)
        modify_button.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        delete_button = tk.Button(main_settings_frame, text="🗑️", 
                                    command=self.delete_analysis_preset)
        delete_button.grid(row=0, column=4, padx=5, pady=5, sticky="w")

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
        
        # New preset button
        new_preset_button = tk.Button(main_settings_frame, text="+", 
                                    command=self.create_new_chunk_preset_window)
        new_preset_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Modify and delete buttons
        modify_button = tk.Button(main_settings_frame, text="Modify", 
                                command=self.modify_chunk_preset)
        modify_button.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        delete_button = tk.Button(main_settings_frame, text="🗑️", 
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

        # New preset button
        new_preset_button = tk.Button(main_settings_frame, text="+", command=self.create_new_function_preset_window)
        new_preset_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Insert the following buttons next to the + button:

        modify_button = tk.Button(main_settings_frame, text="Modify", command=self.modify_function_preset)
        modify_button.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        delete_button = tk.Button(main_settings_frame, text="🗑️", command=self.delete_function_preset)  # Use "🗑️" if supported; otherwise, use text="-"
        delete_button.grid(row=0, column=4, padx=5, pady=5, sticky="w")

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
                if not hasattr(self, 'analysis_val_entry'):
                    self.analysis_val_entry = tk.Entry(self.right_frame, width=60)
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
            self.show_settings("APIs and Login Settings")
            self.show_settings("Models")
            self.update_model_dropdowns()  # Add this line
            messagebox.showinfo("Success", "Settings loaded successfully!", parent=self.settings_window)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {e}", parent=self.settings_window)
    
    def restore_defaults(self):
        try:
            self.settings.restore_defaults()
            self.show_settings("APIs and Login Settings")
            self.show_settings("Models")
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
                'ghost_system_prompt': self.settings.ghost_system_prompt,
                'ghost_user_prompt': self.settings.ghost_user_prompt,
                'ghost_val_text': self.settings.ghost_val_text,
                'ghost_model': self.settings.ghost_model,
                'ghost_temp': self.settings.ghost_temp
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
                    
            # Save the imported settings
            self.settings.save_settings()
            
            # Update UI
            self.parent.update_api_handler()
            self.show_settings("APIs and Login Settings")
            self.show_settings("Models and Import Settings")
            self.update_model_dropdowns()
            
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
                'chunk_model_var': None
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

    def update_all_dropdowns(self):
        """Update all dropdown menus with new model list if they exist."""
        # Check if dropdowns exist and are valid before updating
        try:
            if hasattr(self, 'preset_dropdown') and self.preset_dropdown.winfo_exists():
                self.update_preset_dropdown()
            
            if hasattr(self, 'function_preset_dropdown') and self.function_preset_dropdown.winfo_exists():
                self.update_function_preset_dropdown()
            
            if hasattr(self, 'chunk_preset_dropdown') and self.chunk_preset_dropdown.winfo_exists():
                self.update_chunk_preset_dropdown()
        except tk.TclError:
            # Handle case where widgets are being destroyed
            pass

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
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, text)

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
        Binds an Entry widget so that on each key release its value is saved to the preset.
        """
        def callback(event):
            value = entry_widget.get()
            preset = self.get_preset_by_name(presets, selected_var.get())
            if preset is None:
                return
            preset[field] = value
            self.settings.save_settings()
        entry_widget.bind("<KeyRelease>", callback)

    def bind_text_update(self, text_widget, presets, selected_var, field):
        """
        Binds a Text widget so that on each key release its content is saved to the preset.
        """
        def callback(event):
            value = text_widget.get("1.0", "end-1c")
            preset = self.get_preset_by_name(presets, selected_var.get())
            if preset is None:
                return
            preset[field] = value
            self.settings.save_settings()
        text_widget.bind("<KeyRelease>", callback)
