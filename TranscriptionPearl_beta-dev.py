import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import pandas as pd
import fitz, re, os, shutil, asyncio, difflib, ast
from PIL import Image, ImageTk, ImageOps
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import traceback

# # Import Local Scripts
from util.subs.ImageSplitter import ImageSplitter
from util.FindReplace import FindReplace
from util.APIHandler import APIHandler
from util.ProgressBar import ProgressBar
from util.SettingsWindow import SettingsWindow
from util.Settings import Settings
from util.AnalyzeDocuments import AnalyzeDocuments
from util.ImageHandler import ImageHandler
from util.ProjectIO import ProjectIO
from util.ExportFunctions import ExportManager
from util.AdvancedDiffHighlighting import highlight_text_differences

class App(TkinterDnD.Tk):

# Basic Setup

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Transcription Pearl 1.0 beta")  # Set the window title
        self.link_nav = 0
        self.geometry("1200x800")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        if os.name == 'nt':  # For Windows use the .ico file
            try:
                self.iconbitmap("util/pb.ico")
            except:
                pass  # If icon file is not found, use default icon

        # Flags, Toggles, and Variables
        self.save_toggle = False
        self.find_replace_toggle = False
        self.original_image = None
        self.photo_image = None
        self.pagination_added = False
        self.highlight_names_var = tk.BooleanVar()
        self.highlight_places_var = tk.BooleanVar()
        self.highlight_changes_var = tk.BooleanVar()
        self.highlight_errors_var = tk.BooleanVar()
        self.skip_completed_pages = tk.BooleanVar(value=True)  # Default to skipping completed pages
               
        self.current_scale = 1    

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Top frame
        self.grid_rowconfigure(1, weight=1)  # Main frame
        self.grid_rowconfigure(2, weight=0)  # Bottom frame

        # Modify the top frame configuration
        self.top_frame = tk.Frame(self)
        self.top_frame.grid(row=0, column=0, sticky="nsew")
        self.top_frame.grid_columnconfigure(1, weight=1)  # Make middle column expandable

        # Create groups in the top frame
        left_group = tk.Frame(self.top_frame)
        left_group.grid(row=0, column=0, sticky="w", padx=5)

        middle_group = tk.Frame(self.top_frame)
        middle_group.grid(row=0, column=1, sticky="ew", padx=5)

        right_group = tk.Frame(self.top_frame)
        right_group.grid(row=0, column=2, sticky="e", padx=(0, 5)) 
                
        # Left group elements (text type and toggle)
        text_label = tk.Label(left_group, text="Displayed Text:")
        text_label.pack(side="left", padx=2)
        
        self.text_display_var = tk.StringVar()
        self.text_display_var.set("None")  # Default value
        
        self.text_display_dropdown = ttk.Combobox(
            left_group, 
            textvariable=self.text_display_var,
            values=["None", "Original_Text", "First_Draft", "Final_Draft", "Translation"],
            width=15,
            state="readonly"
        )
        self.text_display_dropdown.pack(side="left", padx=2)
        self.text_display_dropdown.bind('<<ComboboxSelected>>', self.on_text_display_change)
        
        # --- New: Chunking Strategy Dropdown in Middle Group ---
        self.chunking_strategy_var = tk.StringVar()
        # For now, initialize with an empty list; it will be updated after self.settings is set.
        
        # Remove the dropdown and label from the middle group
        # Keep only the variable for use in other functions
        
        # Right group elements (navigation)
        self.button1 = tk.Button(right_group, text="<<", command=lambda: self.navigate_images(-2))
        self.button1.pack(side="left", padx=2)
        
        self.button2 = tk.Button(right_group, text="<", command=lambda: self.navigate_images(-1))
        self.button2.pack(side="left", padx=2)
        
        self.page_counter_var = tk.StringVar()
        self.page_counter_var.set("0 / 0")
        page_counter_label = tk.Label(right_group, textvariable=self.page_counter_var)
        page_counter_label.pack(side="left", padx=2)
        
        self.button4 = tk.Button(right_group, text=">", command=lambda: self.navigate_images(1))
        self.button4.pack(side="left", padx=2)
        
        self.button5 = tk.Button(right_group, text=">>", command=lambda: self.navigate_images(2))
        self.button5.pack(side="left", padx=2)
        
        # --- Main and Bottom Frames ---
        self.main_frame = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_frame.grid(row=1, column=0, sticky="nsew")
        
        self.text_display = self.create_text_widget(self.main_frame, "File to Edit", state="normal")
        
        self.image_display = tk.Canvas(self.main_frame, borderwidth=2, relief="groove")
        self.image_handler = ImageHandler(self.image_display)
        
        self.main_frame.add(self.text_display)
        self.main_frame.add(self.image_display)
        
        self.bottom_frame = tk.Frame(self)
        self.bottom_frame.grid_rowconfigure(0, weight=1)
        self.bottom_frame.grid(row=2, column=0, sticky="nsew")
        
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.bottom_frame.grid_columnconfigure(1, weight=1)
        
        button_frame = tk.Frame(self.bottom_frame)
        button_frame.grid(row=0, column=0, sticky="nsw")
        
        button_frame.grid_columnconfigure(0, weight=0)
        button_frame.grid_columnconfigure(1, weight=0)
        button_frame.grid_columnconfigure(2, weight=1)
        button_frame.grid_rowconfigure(0, weight=1)
        button_frame.grid_rowconfigure(1, weight=1)
        button_frame.grid_rowconfigure(2, weight=1)
        button_frame.grid_rowconfigure(3, weight=1)
        textbox_frame = tk.Frame(self.bottom_frame)
        textbox_frame.grid(row=0, column=1, sticky="nsew")
        
        textbox_frame.grid_columnconfigure(0, weight=0)
        textbox_frame.grid_columnconfigure(1, weight=1)
        textbox_frame.grid_rowconfigure(0, weight=1)
        textbox_frame.grid_rowconfigure(1, weight=1)
        textbox_frame.grid_rowconfigure(2, weight=1)
        
        # --- Continue with Existing Initialization ---
        self.initialize_temp_directory()
        if not hasattr(self, 'project_directory') or not self.project_directory:
            self.project_directory = self.temp_directory

        # Initialize settings now (after the top frame is created)
        self.settings = Settings()
        
        # Initialize the main DataFrame
        self.initialize_main_df()
        
        # --- Update Chunking Dropdown with Actual Presets ---
        preset_names = [p['name'] for p in self.settings.chunk_text_presets] if self.settings.chunk_text_presets else []
        if preset_names:
            self.chunking_strategy_var.set(preset_names[0])
        else:
            self.chunking_strategy_var.set("No Presets")
        
        # Initialize the Find and Replace window
        self.find_replace = FindReplace(
            parent=self,
            text_display=self.text_display,
            main_df=self.main_df,
            navigate_callback=self.find_replace_navigate,  # Use a dedicated method
            get_page_counter=lambda: self.page_counter,
            get_main_df_callback=lambda: self.main_df
        )
        
        # Initialize the API handler
        self.api_handler = APIHandler(
            self.settings.openai_api_key, 
            self.settings.anthropic_api_key, 
            self.settings.google_api_key,
            self
        )
        
        # Initialize the Progress Bar
        self.progress_bar = ProgressBar(self)

        # Initialize ProjectIO
        self.project_io = ProjectIO(self)

        # Initialize the export manager
        self.export_manager = ExportManager(self)

        # Configure highlight tags
        self.text_display.tag_config("name_highlight", background="lightblue")
        self.text_display.tag_config("place_highlight", background="wheat1")
        self.text_display.tag_config("change_highlight", background="lightgreen")
        self.text_display.tag_config("error_highlight", background="cyan")

        # Create menus and key bindings
        self.create_menus()
        self.create_key_bindings()
        self.bind_key_universal_commands(self.text_display)
        
        # Enable drag and drop
        self.enable_drag_and_drop() 

# GUI Setup

    def create_menus(self):
        # Create menu bar
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        # File menu
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New Project", command=self.create_new_project)
        self.file_menu.add_command(label="Open Project", command=self.open_project)
        self.file_menu.add_command(label="Save Project", command=self.save_project)
        self.file_menu.add_command(label="Save Project As", command=self.save_project_as)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Export Text...", command=self.export_manager.export_menu)
        self.file_menu.add_command(label="Export CSV...", command=self.export_manager.show_csv_export_options)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Settings", command=self.create_settings_window)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.on_closing)

        # Edit Menu

        self.edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=self.edit_menu)
        
        self.edit_menu.add_command(label="Find and Replace", command=self.find_and_replace)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Undo", command=self.undo)
        self.edit_menu.add_command(label="Redo", command=self.redo)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cut", 
            command=lambda: self.text_display.event_generate("<<Cut>>"))
        self.edit_menu.add_command(label="Copy", 
            command=lambda: self.text_display.event_generate("<<Copy>>"))
        self.edit_menu.add_command(label="Paste", 
        command=lambda: self.text_display.event_generate("<<Paste>>"))
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Rotate Image Clockwise", command=lambda: self.rotate_image("clockwise"))
        self.edit_menu.add_command(label="Rotate Image Counter-clockwise", command=lambda: self.rotate_image("counter-clockwise"))
        self.edit_menu.add_command(label="Auto-get Rotation (Current Page)", command=lambda: self.ai_function(all_or_one_flag="Current Page", ai_job="Auto_Rotate"))
        self.edit_menu.add_command(label="Auto-get Rotation (All Pages)", command=lambda: self.ai_function(all_or_one_flag="All Pages", ai_job="Auto_Rotate"))
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Revert Current Page", command=self.revert_current_page)
        self.edit_menu.add_command(label="Revert All Pages", command=self.revert_all_pages)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Delete Current Image", command=self.delete_current_image)

        # Process Menu

        self.process_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Process", menu=self.process_menu)

        # Add process mode toggle (Current Page vs All Pages)
        self.process_mode = tk.StringVar(value="Current Page")  # Default to Current Page
        
        # Mode selection submenu
        mode_menu = tk.Menu(self.process_menu, tearoff=0)
        
        # Page mode options
        mode_menu.add_radiobutton(label="Current Page", variable=self.process_mode, value="Current Page")
        mode_menu.add_radiobutton(label="All Pages", variable=self.process_mode, value="All Pages")
        
        # Add separator in the submenu
        mode_menu.add_separator()
        
        # Add Skip/Redo toggle as checkbutton
        mode_menu.add_checkbutton(
            label="Skip Completed Pages", 
            variable=self.skip_completed_pages,
            onvalue=True,
            offvalue=False
        )
        
        self.process_menu.add_cascade(label="Processing Mode", menu=mode_menu)
        
        self.process_menu.add_separator()
        
        # Add simplified processing commands that use the selected mode
        self.process_menu.add_command(label="Recognize Text", 
                                     command=lambda: self.ai_function(all_or_one_flag=self.process_mode.get(), ai_job="HTR"))
        
        self.process_menu.add_command(label="Correct Text", 
                                     command=lambda: self.ai_function(all_or_one_flag=self.process_mode.get(), ai_job="Correct_Text"))
        
        self.process_menu.add_separator()
        
        self.process_menu.add_command(label="Translate Text", 
                                     command=lambda: self.ai_function(all_or_one_flag=self.process_mode.get(), ai_job="Translation"))
        
        self.process_menu.add_separator()
        
        self.process_menu.add_command(label="Get Names and Places", 
                                     command=lambda: self.ai_function(all_or_one_flag=self.process_mode.get(), ai_job="Get_Names_and_Places"))
        
        self.process_menu.add_separator()
        
        self.process_menu.add_command(label="Identify Document Separation", 
                                     command=lambda: self.create_chunk_text_window(self.process_mode.get()))
        
        self.process_menu.add_command(label="Apply Separation", 
                                     command=self.open_document_separation_options)
        
        self.process_menu.add_separator()
        
        self.process_menu.add_command(label="Find Errors", 
                                     command=lambda: self.ai_function(all_or_one_flag=self.process_mode.get(), ai_job="Identify_Errors"))
        
        # Document Menu

        self.document_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Document", menu=self.document_menu)

        self.document_menu.add_separator()

        self.highlight_names_var = tk.BooleanVar()
        self.highlight_places_var = tk.BooleanVar()
        self.highlight_changes_var = tk.BooleanVar()
        self.highlight_errors_var = tk.BooleanVar()

        self.document_menu.add_checkbutton(label="Highlight Names", 
                                        variable=self.highlight_names_var,
                                        command=self.toggle_highlight_options)
        self.document_menu.add_checkbutton(label="Highlight Places", 
                                        variable=self.highlight_places_var,
                                        command=self.toggle_highlight_options)
        self.document_menu.add_checkbutton(label="Highlight Changes", 
                                        variable=self.highlight_changes_var,
                                        command=self.toggle_highlight_options)
        self.document_menu.add_checkbutton(label="Highlight Errors", 
                                        variable=self.highlight_errors_var,
                                        command=self.toggle_highlight_options)
                
        # Tools Menu

        self.tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Tools", menu=self.tools_menu)

        self.tools_menu.add_command(label="Edit Current Image", command=self.edit_single_image)
        self.tools_menu.add_command(label="Edit All Images", command=self.edit_all_images)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(
            label="Collate Names & Places",
            command=self.run_collation_and_open_window  # <-- new function
        )

    def create_key_bindings(self):
        # Navigation bindings
        self.bind("<Control-Home>", lambda event: self.navigate_images(-2))
        self.bind("<Control-Left>", lambda event: self.navigate_images(-1))
        self.bind("<Control-Right>", lambda event: self.navigate_images(1))
        self.bind("<Control-End>", lambda event: self.navigate_images(2))

        # Rotation bindings
        self.bind("<Control-bracketright>", lambda event: self.rotate_image("clockwise"))
        self.bind("<Control-bracketleft>", lambda event: self.rotate_image("counter-clockwise"))

        # Project management bindings
        self.bind("<Control-n>", lambda event: self.create_new_project())  # Fixed missing angle brackets
        self.bind("<Control-s>", lambda event: self.save_project())  # Added parentheses for method call
        self.bind("<Control-o>", lambda event: self.open_project())  # Added parentheses for method call

        # Edit bindings
        self.bind("<Control-z>", self.undo)
        self.bind("<Control-y>", self.redo)
        
        # Find and Replace bindings
        self.bind("<Control-f>", lambda event: self.find_and_replace())  # Added parentheses for method call

        # Revert bindings
        self.bind("<Control-r>", lambda event: self.revert_current_page())  # Added parentheses for method call
        self.bind("<Control-Shift-r>", lambda event: self.revert_all_pages())  # Added parentheses for method call

        # Text display toggle binding
        self.bind("<Control-Tab>", lambda event: self.toggle_text())

        # Image management bindings
        self.bind("<Control-d>", lambda event: self.delete_current_image())  # Added parentheses for method call
        self.bind("<Control-i>", lambda event: self.edit_single_image())  # Added parentheses for method call
        self.bind("<Control-Shift-i>", lambda event: self.edit_all_images())  # Added parentheses for method call

        # AI function bindings
        self.bind("<Control-1>", lambda event: self.ai_function(all_or_one_flag="Current Page", ai_job="HTR"))
        self.bind("<Control-Shift-1>", lambda event: self.ai_function(all_or_one_flag="All Pages", ai_job="HTR"))
        self.bind("<Control-2>", lambda event: self.ai_function(all_or_one_flag="Current Page", ai_job="Correct_Text"))
        self.bind("<Control-Shift-2>", lambda event: self.ai_function(all_or_one_flag="All Pages", ai_job="Correct_Text"))
        self.bind("<Control-t>", lambda event: self.ai_function(all_or_one_flag="Current Page", ai_job="Translation"))
        self.bind("<Control-Shift-t>", lambda event: self.ai_function(all_or_one_flag="All Pages", ai_job="Translation"))
        
        # Add key bindings for Chunk_Text
        self.bind("<Control-3>", lambda event: self.create_chunk_text_window("Current Page"))
        self.bind("<Control-Shift-3>", lambda event: self.create_chunk_text_window("All Pages"))
        
        # Add key binding for document separation
        self.bind("<Control-4>", lambda event: self.open_document_separation_options())

        # Mouse bindings
        self.image_display.bind("<Control-MouseWheel>", self.image_handler.zoom)
        self.image_display.bind("<MouseWheel>", self.image_handler.scroll)
        self.image_display.bind("<ButtonPress-1>", self.image_handler.start_pan)
        self.image_display.bind("<B1-Motion>", self.image_handler.pan)

    def create_collate_names_places_window(self):
        """
        A larger window with two text boxes for the collated lines from the LLM.
        The user can manually edit or remove lines before applying replacements.
        """
        window = tk.Toplevel(self)
        window.title("Collate Names & Places")
        window.geometry("600x500")
        window.grab_set()

        # Frame for labels
        lbl_frame = tk.Frame(window)
        lbl_frame.pack(side="top", fill="x", pady=5)
        
        names_label = tk.Label(lbl_frame, text="Collated Names (edit as needed):")
        names_label.pack(anchor="w", padx=5)

        # Text display for Names
        self.names_textbox = tk.Text(window, wrap="word", height=10)
        self.names_textbox.pack(fill="both", expand=True, padx=5, pady=(0,10))
        self.names_textbox.insert("1.0", self.collated_names_raw)

        places_label = tk.Label(window, text="Collated Places (edit as needed):")
        places_label.pack(anchor="w", padx=5)

        # Text display for Places
        self.places_textbox = tk.Text(window, wrap="word", height=10)
        self.places_textbox.pack(fill="both", expand=True, padx=5, pady=(0,10))
        self.places_textbox.insert("1.0", self.collated_places_raw)

        # Buttons at bottom
        btn_frame = tk.Frame(window)
        btn_frame.pack(side="bottom", pady=10)

        btn_names = tk.Button(btn_frame, text="Replace Names", command=self.replace_names_button)
        btn_names.pack(side="left", padx=10)

        btn_places = tk.Button(btn_frame, text="Replace Places", command=self.replace_places_button)
        btn_places.pack(side="left", padx=10)

        btn_cancel = tk.Button(btn_frame, text="Cancel", command=window.destroy)
        btn_cancel.pack(side="left", padx=10)

    def replace_names_button(self):
        """
        Parse the user-edited names from self.names_textbox,
        then do the find-and-replace in the active text.
        """
        raw = self.names_textbox.get("1.0", tk.END)
        collated_dict = self.parse_collation_response(raw)
        self.apply_collation_dict(collated_dict, is_names=True)

    def replace_places_button(self):
        """
        Parse the user-edited places from self.places_textbox,
        then do the find-and-replace in the active text.
        """
        raw = self.places_textbox.get("1.0", tk.END)
        collated_dict = self.parse_collation_response(raw)
        self.apply_collation_dict(collated_dict, is_names=False)

    def create_image_widget(self, frame, image_path, state):
        # Load the image
        original_image = Image.open(image_path)
        self.photo_image = ImageTk.PhotoImage(original_image)

        # Create a canvas and add the image to it
        self.canvas = tk.Canvas(frame, borderwidth=2, relief="groove")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo_image)
        self.canvas.grid(sticky="nsew")

        # Bind zoom and scroll events to the image_handler methods
        self.canvas.bind("<Control-MouseWheel>", self.image_handler.zoom)
        self.canvas.bind("<MouseWheel>", self.image_handler.scroll)

        return self.canvas

    def create_text_widget(self, frame, label_text, state):
        # Create a Text widget to display the contents of the selected file
        text_display = tk.Text(frame, wrap="word", state=state, undo=True)
        # Make the font size 16
        text_display.config(font=("Calibri", 20))
        
        text_display.grid(sticky="nsew")

        return text_display

    def bind_key_universal_commands(self, text_widget):
        text_widget.bind('<Control-h>', self.find_and_replace)
        text_widget.bind('<Control-f>', self.find_and_replace)
        text_widget.bind('<Control-z>', self.undo)
        text_widget.bind('<Control-y>', self.redo)
           
    def create_chunk_text_window(self, all_or_one_flag):
        """
        Creates a window for selecting document type before running Chunk_Text
        """
        # Create the window
        chunk_window = tk.Toplevel(self)
        chunk_window.title("Select Document Type")
        chunk_window.geometry("400x200")
        chunk_window.grab_set()  # Make window modal
        
        # Message explaining purpose
        message_label = tk.Label(chunk_window, 
            text="Select the document type for text chunking:",
            font=("Calibri", 12))
        message_label.pack(pady=15)
        
        # Create the chunking strategy dropdown in this window
        dropdown_frame = tk.Frame(chunk_window)
        dropdown_frame.pack(pady=10)
        
        chunking_label = tk.Label(dropdown_frame, text="Document Type:")
        chunking_label.pack(side="left", padx=5)
        
        # Create a new StringVar for this window's dropdown
        window_chunking_var = tk.StringVar()
        
        # If there's already a selected strategy, use it as default
        if hasattr(self, 'chunking_strategy_var') and self.chunking_strategy_var.get():
            window_chunking_var.set(self.chunking_strategy_var.get())
        
        # Get preset names for the dropdown
        preset_names = [p['name'] for p in self.settings.chunk_text_presets] if self.settings.chunk_text_presets else []
        
        # Create the dropdown
        chunking_dropdown = ttk.Combobox(dropdown_frame, 
                                      textvariable=window_chunking_var,
                                      values=preset_names, 
                                      state="readonly", 
                                      width=30)
        chunking_dropdown.pack(side="left", padx=5)
        
        # Set a default value if available
        if preset_names and not window_chunking_var.get():
            window_chunking_var.set(preset_names[0])
        
        # Buttons frame
        button_frame = tk.Frame(chunk_window)
        button_frame.pack(pady=20)
        
        # Function to handle OK button
        def on_ok():
            # Set the main window's chunking strategy variable
            self.chunking_strategy_var.set(window_chunking_var.get())
            # Close the window
            chunk_window.destroy()
            # Run the AI function with the selected parameters
            self.ai_function(all_or_one_flag=all_or_one_flag, ai_job="Chunk_Text")
        
        # Function to handle Cancel button
        def on_cancel():
            chunk_window.destroy()
        
        # Create buttons
        ok_button = tk.Button(button_frame, text="OK", command=on_ok, width=10)
        ok_button.pack(side="left", padx=10)
        
        cancel_button = tk.Button(button_frame, text="Cancel", command=on_cancel, width=10)
        cancel_button.pack(side="left", padx=10)
        
        # Center the window on the screen
        chunk_window.update_idletasks()
        width = chunk_window.winfo_width()
        height = chunk_window.winfo_height()
        x = (chunk_window.winfo_screenwidth() // 2) - (width // 2)
        y = (chunk_window.winfo_screenheight() // 2) - (height // 2)
        chunk_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Wait for the window to be closed
        self.wait_window(chunk_window)

# Initialize Settings Functions

    def reset_application(self):
        # Clear the main DataFrame
        self.initialize_main_df()
        
        # Reset Flags, Toggles, and Variables
        self.save_toggle = False
        self.find_replace_toggle = False
        self.original_image = None
        self.photo_image = None
        self.pagination_added = False
        self.highlight_names_var = tk.BooleanVar()
        self.highlight_places_var = tk.BooleanVar()
        self.highlight_changes_var = tk.BooleanVar()
        self.highlight_errors_var = tk.BooleanVar()
        
        # Reset page counter
        self.page_counter = 0
            
        # Reset flags
        self.save_toggle = False
        self.find_replace_toggle = False
        
        # Clear text displays
        self.text_display.delete("1.0", tk.END)
        
        # Clear image display
        self.image_display.delete("all")
        self.current_image_path = None
        self.original_image = None
        self.photo_image = None
        
        # Reset zoom and pan
        self.current_scale = 1
        
        # Reset counter
        self.counter_update()

        # Reset contingent menu items
        self.document_menu.entryconfig("Remove Pagination", state="disabled")

        # Clear project and image directories
        self.initialize_temp_directory()
        self.initialize_settings
                        
        # Clear the find and replace matches DataFrame
        self.find_replace_matches_df = pd.DataFrame(columns=["Index", "Page"])
        
        # Reset the dropdown to "None"
        self.text_display_var.set("None")

    def initialize_settings(self):   
        # Get the appropriate app data directory
        if os.name == 'nt':  # Windows
            app_data = os.path.join(os.environ['APPDATA'], 'TranscriptionPearl')
        else:  # Linux/Mac
            app_data = os.path.join(os.path.expanduser('~'), '.transcriptionpearl')
        
        # Create the directory if it doesn't exist
        os.makedirs(app_data, exist_ok=True)
        
        # Define settings file path
        self.settings_file_path = os.path.join(app_data, 'settings.json')
        
        # In initialize_temp_directory method, modify the DataFrame creation:
        self.initialize_main_df()

        # Initilize the dataframe to store metadata
        self.compiled_df = pd.DataFrame(columns=["Index", "Document_No", "Document_Type", "Text", "Translation", "Document_Page", "Citation", "Image_Path", "Author", "Correspondent", "Creation_Place", "Correspondent_Place:", "Date", "Places", "People", "Summary", "Temp_Data_Analysis", "Data_Analysis", "Query_Data", "Query_Memory", "Relevance", "Notes"])

        # First set default values
        self.restore_defaults()

        # Check if settings file exists and load it
        if os.path.exists(self.settings_file_path):
            self.load_settings()
  
    def initialize_temp_directory(self):
        """Initialize and manage temporary directories"""
        # Define temp directory paths
        self.temp_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "util", "temp")
        self.images_directory = os.path.join(self.temp_directory, "images")
        self.edit_temp_directory = os.path.join(self.temp_directory, "edit_temp")

        # Clear existing temp directories
        for dir_path in [self.temp_directory, self.images_directory, self.edit_temp_directory]:
            if os.path.exists(dir_path):
                try:
                    shutil.rmtree(dir_path)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to clear temp directory: {e}")
                    self.error_logging(f"Failed to clear temp directory: {e}")

        # Create fresh temp directories
        try:
            for dir_path in [self.temp_directory, self.images_directory, self.edit_temp_directory]:
                os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create temp directories: {e}")
            self.error_logging(f"Failed to create temp directories: {e}")

        # Reset the main DataFrame
        self.initialize_main_df()
        self.page_counter = 0

    def initialize_main_df(self):
        self.main_df = pd.DataFrame(columns=[
            # Basic columns
            "Index", 
            "Page", 
            "Original_Text", 
            "First_Draft", 
            "Final_Draft",
            "Translation",
            "Image_Path", 
            "Text_Path", 
            "Text_Toggle",
            # Names and Places columns
            "People",
            "Places",
            # Error tracking
            "Errors"
        ])
        
        # Initialize all text columns as empty strings instead of NaN
        text_columns = [
            "Original_Text", "First_Draft", "Final_Draft", "Translation",
            "People", "Places", "Errors"
        ]
        for col in text_columns:
            self.main_df[col] = ""
        
        # Initialize numeric columns
        self.main_df["Index"] = pd.Series(dtype=int)
        
        # Initialize date column
        self.main_df["Creation_Date"] = pd.Series(dtype='datetime64[ns]')

    def create_settings_window(self):
        self.toggle_button_state()
        settings_window = SettingsWindow(self, mode="T_PEARL")

    def enable_drag_and_drop(self):
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.drop) 

# Navigation Functions

    def navigate_images(self, direction):
        if self.main_df.empty:
            return

        # Save current text changes before navigating only if not in "None" mode
        current_display = self.main_df.loc[self.page_counter, 'Text_Toggle']
        if current_display != "None":
            # Get the current text from the text widget
            text = self.clean_text(self.text_display.get("1.0", tk.END))
            
            # Save the text to the appropriate column based on CURRENT display type
            if current_display == "Original_Text":
                self.main_df.loc[self.page_counter, 'Original_Text'] = text
            elif current_display == "First_Draft":
                self.main_df.loc[self.page_counter, 'First_Draft'] = text
            elif current_display == "Final_Draft":
                self.main_df.loc[self.page_counter, 'Final_Draft'] = text
            elif current_display == "Translation":
                self.main_df.loc[self.page_counter, 'Translation'] = text
            
        # Handle double-arrow navigation
        if abs(direction) == 2:
            # Go to first image
            if direction < 0:
                self.page_counter = 0
            # Go to last image
            else:
                self.page_counter = len(self.main_df) - 1
        else:
            # Handle single-arrow navigation
            new_counter = self.page_counter + direction
            
            # Ensure the new counter is within valid bounds
            if new_counter < 0:
                new_counter = 0
            elif new_counter >= len(self.main_df):
                new_counter = len(self.main_df) - 1
                
            self.page_counter = new_counter

        try:
            # Get image path with safety checks
            image_path = self.main_df.iloc[self.page_counter]['Image_Path']
            if pd.isna(image_path):
                messagebox.showerror("Error", "Invalid image path in database")
                return
                
            # Use get_full_path to resolve relative paths
            image_path = self.get_full_path(image_path)
                
            if not os.path.exists(image_path):
                messagebox.showerror("Error", f"Image file not found: {image_path}")
                return
                
            self.current_image_path = image_path
            self.image_handler.load_image(self.current_image_path)
            self.load_text()
            self.counter_update()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to navigate images: {str(e)}")
            self.error_logging(f"Navigation error: {str(e)}")

    def counter_update(self):
        total_images = len(self.main_df) - 1

        if total_images >= 0:
            self.page_counter_var.set(f"{self.page_counter + 1} / {total_images + 1}")
        else:
            self.page_counter_var.set("0 / 0")

    def find_replace_navigate(self, direction):
        """Special navigation method for find/replace functionality"""
        if hasattr(self, 'find_replace') and hasattr(self.find_replace, 'link_nav'):
            
            # Set the page counter
            self.page_counter = self.find_replace.link_nav
            
            try:
                # Get image path with safety checks
                image_path = self.main_df.iloc[self.page_counter]['Image_Path']
                if pd.isna(image_path):
                    messagebox.showerror("Error", "Invalid image path in database")
                    return
                    
                # Use get_full_path to resolve relative paths
                image_path = self.get_full_path(image_path)
                    
                if not os.path.exists(image_path):
                    messagebox.showerror("Error", f"Image file not found: {image_path}")
                    return
                    
                # Update the current image path and load it
                self.current_image_path = image_path
                self.image_handler.load_image(self.current_image_path)
                
                # Load the text and update the counter
                self.load_text()
                self.counter_update()
                
                # Re-highlight search terms
                if hasattr(self, 'find_replace'):
                    self.find_replace.highlight_text()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to navigate images: {str(e)}")
                self.error_logging(f"Navigation error: {str(e)}")

# Image Functions

    def resize_image(self, image_path, output_path, max_size=1980):
        with Image.open(image_path) as img:
           
            # Get the original image size
            width, height = img.size
            
            # Determine the larger dimension
            larger_dimension = max(width, height)
            
            # Calculate the scaling factor
            scale = max_size / larger_dimension
            
            # Calculate new dimensions
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # Resize the image
            img = img.resize((new_width, new_height), Image.LANCZOS)

            img = ImageOps.exif_transpose(img)
            
            # Save the image with high quality
            img.save(output_path, "JPEG", quality=95)
    
    def process_new_images(self, source_paths):
        successful_copies = 0
        for source_path in source_paths:
            new_index = len(self.main_df)
            file_extension = os.path.splitext(source_path)[1].lower()
            new_file_name = f"{new_index+1:04d}_p{new_index+1:03d}{file_extension}"
            dest_path = os.path.join(self.images_directory, new_file_name)
            
            try:
                # Instead of directly copying, resize and save the image
                self.resize_image(source_path, dest_path)                
                text_file_name = f"{new_index+1:04d}_p{new_index+1:03d}.txt"
                text_file_path = os.path.join(self.images_directory, text_file_name)
                with open(text_file_path, "w", encoding='utf-8') as f:
                    f.write("")
                
                new_row = pd.DataFrame({
                    "Index": [new_index],
                    "Page": [f"{new_index+1:04d}_p{new_index+1:03d}"],
                    "Original_Text": [""],
                    "First_Draft": [""],
                    "Final_Draft": [""],
                    "Image_Path": [dest_path],
                    "Text_Path": [text_file_path],
                    "Text_Toggle": ["Original_Text"]
                })

                self.main_df = pd.concat([self.main_df, new_row], ignore_index=True)
                successful_copies += 1
            except Exception as e:
                self.error_logging(f"Error processing file {source_path}", f"{e}")
                messagebox.showerror("Error", f"Failed to process the image {source_path}:\n{e}")

        if successful_copies > 0:
            self.refresh_display()

            # Add auto-rotation if enabled in settings
            if hasattr(self, 'settings') and getattr(self.settings, 'check_orientation', False):
                # First rotation pass
                self.ai_function(all_or_one_flag="All Pages", ai_job="Auto_Rotate")
                
                # Brief pause to ensure all rotations are complete
                self.after(1000)  # 1 second pause
                
                # Second rotation pass
                self.ai_function(all_or_one_flag="All Pages", ai_job="Auto_Rotate")
        else:
            self.error_logging("No images were successfully processed", level="INFO")
            messagebox.showinfo("Information", "No images were successfully processed")

    def delete_current_image(self):
        if self.main_df.empty:
            messagebox.showinfo("No Images", "No images to delete.")
            return

        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the current image? This action cannot be undone."):
            return

        try:
            current_index = self.page_counter
            
            # Store the path of files to be deleted
            image_to_delete = self.main_df.loc[current_index, 'Image_Path']
            text_to_delete = self.main_df.loc[current_index, 'Text_Path']

            # Remove the row from the DataFrame
            self.main_df = self.main_df.drop(current_index).reset_index(drop=True)

            # Delete the actual files
            try:
                if os.path.exists(image_to_delete):
                    os.remove(image_to_delete)
                if os.path.exists(text_to_delete):
                    os.remove(text_to_delete)
            except Exception as e:
                self.error_logging(f"Error deleting files: {str(e)}")

            # Renumber the remaining entries
            for idx in range(len(self.main_df)):
                # Update Index
                self.main_df.at[idx, 'Index'] = idx
                
                # Create new page number
                new_page = f"{idx+1:04d}_p{idx+1:03d}"
                self.main_df.at[idx, 'Page'] = new_page
                
                # Get old file paths
                old_image_path = self.main_df.loc[idx, 'Image_Path']
                old_text_path = self.main_df.loc[idx, 'Text_Path']
                
                # Create new file paths
                new_image_name = f"{idx+1:04d}_p{idx+1:03d}{os.path.splitext(old_image_path)[1]}"
                new_text_name = f"{idx+1:04d}_p{idx+1:03d}.txt"
                
                new_image_path = os.path.join(os.path.dirname(old_image_path), new_image_name)
                new_text_path = os.path.join(os.path.dirname(old_text_path), new_text_name)
                
                # Rename files
                if os.path.exists(old_image_path):
                    os.rename(old_image_path, new_image_path)
                if os.path.exists(old_text_path):
                    os.rename(old_text_path, new_text_path)
                
                # Update paths in DataFrame
                self.main_df.at[idx, 'Image_Path'] = new_image_path
                self.main_df.at[idx, 'Text_Path'] = new_text_path

            # Adjust page counter if necessary
            if current_index >= len(self.main_df):
                self.page_counter = len(self.main_df) - 1
            
            # Refresh display
            if not self.main_df.empty:
                # Load the iamge using image handler
                self.image_handler.load_image(self.main_df.loc[self.page_counter, 'Image_Path'])

                
                self.load_text()
            else:
                # Clear displays if no images remain
                self.text_display.delete("1.0", tk.END)
                self.image_display.delete("all")

            self.counter_update()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while deleting the image: {str(e)}")
            self.error_logging(f"Error in delete_current_image: {str(e)}")

    def rotate_image(self, direction):
        success, error_message = self.image_handler.rotate_image(direction, self.main_df.loc[self.page_counter, 'Image_Path'])
        if not success:
            messagebox.showerror("Error", error_message)

# Project Save and Open Function Handlers

    def create_new_project(self):
        self.project_io.create_new_project()

    def save_project(self):
        # Save current changes before saving the project
        if not self.main_df.empty:
            current_display = self.main_df.loc[self.page_counter, 'Text_Toggle']
            if current_display != "None":
                # Get the current text from the text widget
                text = self.clean_text(self.text_display.get("1.0", tk.END))
                
                # Save the text to the appropriate column based on CURRENT display type
                if current_display == "Original_Text":
                    self.main_df.loc[self.page_counter, 'Original_Text'] = text
                elif current_display == "First_Draft":
                    self.main_df.loc[self.page_counter, 'First_Draft'] = text
                elif current_display == "Final_Draft":
                    self.main_df.loc[self.page_counter, 'Final_Draft'] = text
                elif current_display == "Translation":
                    self.main_df.loc[self.page_counter, 'Translation'] = text
        
        self.project_io.save_project()

    def open_project(self):
        # Save current changes before opening a new project
        if not self.main_df.empty:
            current_display = self.main_df.loc[self.page_counter, 'Text_Toggle']
            if current_display != "None":
                # Get the current text from the text widget
                text = self.clean_text(self.text_display.get("1.0", tk.END))
                
                # Save the text to the appropriate column based on CURRENT display type
                if current_display == "Original_Text":
                    self.main_df.loc[self.page_counter, 'Original_Text'] = text
                elif current_display == "First_Draft":
                    self.main_df.loc[self.page_counter, 'First_Draft'] = text
                elif current_display == "Final_Draft":
                    self.main_df.loc[self.page_counter, 'Final_Draft'] = text
                elif current_display == "Translation":
                    self.main_df.loc[self.page_counter, 'Translation'] = text
        
        self.project_io.open_project()

    def save_project_as(self):
        # Save current changes before saving as a new project
        if not self.main_df.empty:
            current_display = self.main_df.loc[self.page_counter, 'Text_Toggle']
            if current_display != "None":
                # Get the current text from the text widget
                text = self.clean_text(self.text_display.get("1.0", tk.END))
                
                # Save the text to the appropriate column based on CURRENT display type
                if current_display == "Original_Text":
                    self.main_df.loc[self.page_counter, 'Original_Text'] = text
                elif current_display == "First_Draft":
                    self.main_df.loc[self.page_counter, 'First_Draft'] = text
                elif current_display == "Final_Draft":
                    self.main_df.loc[self.page_counter, 'Final_Draft'] = text
                elif current_display == "Translation":
                    self.main_df.loc[self.page_counter, 'Translation'] = text
        
        self.project_io.save_project_as()

    def open_pdf(self, pdf_file=None):
        self.project_io.open_pdf(pdf_file)

# Loading Functions

    def open_folder(self, toggle):
        directory = filedialog.askdirectory()
        if directory:
            self.directory_path = directory  # Set the directory_path attribute
            self.project_directory = directory

            # Reset application state.
            self.reset_application()

            if toggle == "Images without Text":
                self.load_files_from_folder_no_text()
            else:
                self.load_files_from_folder()
            self.enable_drag_and_drop()

    def load_files_from_folder(self):
        if not self.directory_path:
            messagebox.showerror("Error", "No directory selected.")
            return

        # Reset DataFrame and page counter.
        self.initialize_main_df()
        self.page_counter = 0

        # Get lists of image and text files.
        image_files = [f for f in os.listdir(self.directory_path) if f.lower().endswith((".jpg", ".jpeg"))]
        text_files = [f for f in os.listdir(self.directory_path) if f.lower().endswith(".txt")]

        if not image_files:
            messagebox.showinfo("No Files", "No image files found in the selected directory.")
            return

        # Sort the files based on a numeric prefix.
        def sort_key(filename):
            match = re.match(r'(\d+)', filename)
            return int(match.group(1)) if match else float('inf')
        image_files.sort(key=sort_key)
        text_files.sort(key=sort_key)

        # Check that there is a matching text file for every image.
        if len(image_files) != len(text_files):
            messagebox.showerror("Error", "The number of image files and text files does not match.")
            return

        # Populate the DataFrame.
        for i, (image_file, text_file) in enumerate(zip(image_files, text_files), start=1):
            image_path = os.path.join(self.directory_path, image_file)
            text_path = os.path.join(self.directory_path, text_file)

            # Read text content.
            with open(text_path, "r", encoding='utf-8') as f:
                text_content = f.read()

            # NEW: Set Text_Toggle to "Original_Text" only if text_content is non-empty; otherwise "None".
            text_toggle = "Original_Text" if text_content.strip() else "None"

            page = f"{i:04d}_p{i:03d}"
            new_row = {
                "Index": i - 1,
                "Page": page,
                "Original_Text": text_content,
                "First_Draft": "",
                "Final_Draft": "",
                "Translation": "",
                "Image_Path": image_path,
                "Text_Path": text_path,
                "Text_Toggle": text_toggle,
                "People": "",
                "Places": "",
                "Errors": ""  # Add Errors column initialization
            }
            self.main_df.loc[i - 1] = new_row

        # Load the first image and its text.
        if len(self.main_df) > 0:
            self.current_image_path = self.main_df.loc[0, 'Image_Path']
            self.image_handler.load_image(self.current_image_path)
            self.load_text()
        else:
            messagebox.showinfo("No Files", "No files found in the selected directory.")

        self.counter_update()

    def load_files_from_folder_no_text(self):
        if self.directory_path:
            print(f"Looking for files in: {self.directory_path}")
            print(f"Directory contents: {os.listdir(self.directory_path)}")
            
            # Reset the page counter
            self.page_counter = 0

            # Load image files
            image_files = [file for file in os.listdir(self.directory_path)
                        if file.lower().endswith((".jpg", ".jpeg"))]

            print(f"Found image files: {image_files}")

            if not image_files:
                messagebox.showinfo("No Files", "No image files found in the selected directory.")
                return

            # Sort image files naturally (handling both numeric and text-based filenames)
            def natural_sort_key(s):
                # Split the string into text and numeric parts
                import re
                return [int(text) if text.isdigit() else text.lower()
                    for text in re.split(r'([0-9]+)', s)]
            
            image_files.sort(key=natural_sort_key)

            # Populate the DataFrame
            for i, image_file in enumerate(image_files, start=1):
                image_path = os.path.join(self.directory_path, image_file)

                # No text file needed for this import mode
                text_path = ""

                page = f"{i:04d}_p{i:03d}"
                new_row = {
                    "Index": i - 1,
                    "Page": page,
                    "Original_Text": "",
                    "First_Draft": "",
                    "Final_Draft": "",
                    "Translation": "",
                    "Image_Path": image_path,
                    "Text_Path": text_path,
                    "Text_Toggle": "None",
                    "People": "",
                    "Places": "",
                    "Errors": ""  # Add Errors column initialization
                }
                self.main_df = pd.concat([self.main_df, pd.DataFrame([new_row])], ignore_index=True)

            # Load the first image and text file
            if len(self.main_df) > 0:
                self.current_image_path = self.main_df.loc[0, 'Image_Path']
                self.image_handler.load_image(self.current_image_path)
                self.text_display_var.set("None")  # Set dropdown to "None"
                self.load_text()
            else:
                messagebox.showinfo("No Files", "No files found in the selected directory.")
            
            self.counter_update()

    def load_text(self):
        # Ensure there is at least one row and that the page counter is valid.
        if self.main_df.empty or self.page_counter < 0 or self.page_counter >= len(self.main_df):
            self.text_display.delete("1.0", tk.END)
            return
        index = self.page_counter
        current_toggle = self.main_df.loc[index, 'Text_Toggle']

        display_map = {
            "None": "None",
            "Original_Text": "Original_Text",
            "First_Draft": "First_Draft",
            "Final_Draft": "Final_Draft",
            "Translation": "Translation"
        }
        self.text_display_var.set(display_map.get(current_toggle, "None"))

        # Based on the toggle, select the text to display.
        if self.text_display_var.get() == "None":
            text = ""
        elif self.text_display_var.get() == "Original_Text":
            text = self.main_df.loc[index, 'Original_Text'] if pd.notna(self.main_df.loc[index, 'Original_Text']) else ""
        elif self.text_display_var.get() == "First_Draft":
            text = self.main_df.loc[index, 'First_Draft'] if pd.notna(self.main_df.loc[index, 'First_Draft']) else ""
        elif self.text_display_var.get() == "Final_Draft":
            text = self.main_df.loc[index, 'Final_Draft'] if pd.notna(self.main_df.loc[index, 'Final_Draft']) else ""
        elif self.text_display_var.get() == "Translation":
            text = self.main_df.loc[index, 'Translation'] if pd.notna(self.main_df.loc[index, 'Translation']) else ""
        else:
            text = ""

        self.text_display.delete("1.0", tk.END)
        if text:
            self.text_display.insert("1.0", text)

        # Update the dropdown options dynamically.
        available_options = ["None"]
        if pd.notna(self.main_df.loc[index, 'Original_Text']) and self.main_df.loc[index, 'Original_Text'].strip():
            available_options.append("Original_Text")
        if pd.notna(self.main_df.loc[index, 'First_Draft']) and self.main_df.loc[index, 'First_Draft'].strip():
            available_options.append("First_Draft")
        if pd.notna(self.main_df.loc[index, 'Final_Draft']) and self.main_df.loc[index, 'Final_Draft'].strip():
            available_options.append("Final_Draft")
        if pd.notna(self.main_df.loc[index, 'Translation']) and self.main_df.loc[index, 'Translation'].strip():
            available_options.append("Translation")
        self.text_display_dropdown['values'] = available_options

        # Re-highlight find/replace matches if that window is active
        if hasattr(self, 'find_replace') and self.find_replace.find_replace_toggle:
            self.find_replace.highlight_text()

        # Apply any active highlighting (names, places, changes, errors)
        self.highlight_text()
        
        # Update menu states based on data availability
        self.update_highlight_menu_states()
        
        self.counter_update()

# Utility Functions   
    
    def undo(self, event=None):
        try:
            self.text_display.edit_undo()
        except tk.TclError:
            pass
        
    def redo(self, event=None):
        try:
            self.text_display.edit_redo()
        except tk.TclError:
            pass

    def clean_text(self, text):
        """Clean text by replacing curly braces with parentheses and handling special cases"""
        if not isinstance(text, str):
            return text
            
        # Dictionary of replacements (add more variations as needed)
        replacements = {
            '{': '(',
            '}': ')',
            '﹛': '(',  # Alternative left curly bracket
            '﹜': ')',  # Alternative right curly bracket
            '｛': '(',  # Fullwidth left curly bracket
            '｝': ')',  # Fullwidth right curly bracket
            '❴': '(',  # Ornate left curly bracket
            '❵': ')',  # Ornate right curly bracket
            '⟨': '(',  # Mathematical left angle bracket
            '⟩': ')',  # Mathematical right angle bracket
            '『': '(',  # White corner bracket
            '』': ')',  # White corner bracket
            '〔': '(',  # Tortoise shell bracket
            '〕': ')',  # Tortoise shell bracket
        }
        
        # Replace all instances of special brackets with regular parentheses
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text

    def find_right_text(self, index_no):
        original_text = self.main_df.loc[index_no, 'Original_Text'] if 'Original_Text' in self.main_df.columns else ""
        first_draft = self.main_df.loc[index_no, 'First_Draft'] if 'First_Draft' in self.main_df.columns else ""
        final_draft = self.main_df.loc[index_no, 'Final_Draft'] if 'Final_Draft' in self.main_df.columns else ""
        translation = self.main_df.loc[index_no, 'Translation'] if 'Translation' in self.main_df.columns else ""

        # First check if there's a translation and if the current toggle is set to Translation
        if pd.notna(translation) and translation.strip() and self.main_df.loc[index_no, 'Text_Toggle'] == "Translation":
            text = translation
        # Then check for final draft
        elif pd.notna(final_draft) and final_draft.strip() and self.main_df.loc[index_no, 'Text_Toggle'] == "Final_Draft":
            text = final_draft
        # Then check for first draft
        elif pd.notna(first_draft) and first_draft.strip() and self.main_df.loc[index_no, 'Text_Toggle'] == "First_Draft":
            text = first_draft
        # Finally use original text if available
        elif pd.notna(original_text) and original_text.strip():
            text = original_text
        else:
            text = ""

        return text

    def find_chunk_text(self, index_no):
        """
        Special version of find_right_text specifically for Chunk_Text operations.
        Prioritizes First_Draft -> Original_Text, never uses Translation.
        Returns a tuple of (text_to_use, has_translation) where has_translation is a boolean.
        """
        first_draft = self.main_df.loc[index_no, 'First_Draft'] if 'First_Draft' in self.main_df.columns else ""
        original_text = self.main_df.loc[index_no, 'Original_Text'] if 'Original_Text' in self.main_df.columns else ""
        translation = self.main_df.loc[index_no, 'Translation'] if 'Translation' in self.main_df.columns else ""
        
        # Check if translation exists and is non-empty
        has_translation = pd.notna(translation) and translation.strip() != ""
        
        # First try First_Draft
        if pd.notna(first_draft) and first_draft.strip():
            return first_draft, has_translation
        # Then try Original_Text
        elif pd.notna(original_text) and original_text.strip():
            return original_text, has_translation
        # If neither is available, return empty string
        else:
            return "", has_translation 

    def toggle_button_state(self):
                
        if self.button1['state'] == "normal" and self.button2['state'] == "normal" and self.button4['state'] == "normal" and self.button5['state'] == "normal":
            self.button1.config(state="disabled")
            self.button2.config(state="disabled")
            self.button4.config(state="disabled")
            self.button5.config(state="disabled")

        else:
            self.button1.config(state="normal")
            self.button2.config(state="normal")
            self.button4.config(state="normal")
            self.button5.config(state="normal")

    def error_logging(self, error_message, additional_info=None, level="ERROR"):
        """
        Log errors to the error log file.
        
        Args:
            error_message (str): The main error message to log
            additional_info (str, optional): Additional information to include
            level (str, optional): Log level - only "ERROR" messages are logged
        """
        # Skip logging for non-error messages
        if level != "ERROR":
            return
            
        try:
            error_logs_path = "util/error_logs.txt"
            os.makedirs(os.path.dirname(error_logs_path), exist_ok=True)
            
            with open(error_logs_path, "a", encoding='utf-8') as file:
                # Add stack trace for errors
                stack = traceback.format_exc()
                
                log_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [{level}]: {error_message}"
                if additional_info:
                    log_message += f" - Additional Info: {additional_info}"
                if stack and stack != "NoneType: None\n":
                    log_message += f"\nStack trace:\n{stack}"
                file.write(log_message + "\n")
        except Exception as e:
            print(f"Error logging failed: {e}")

    def drop(self, event):
        file_paths = event.data
        file_paths = re.findall(r'\{[^}]*\}|\S+', file_paths)
        
        valid_images = []
        pdf_files = []
        invalid_files = []

        # Record current image count before processing new files
        prev_count = len(self.main_df)

        # Process all files first
        for file_path in file_paths:
            # Remove curly braces and any quotation marks
            file_path = file_path.strip('{}').strip('"')
            
            if os.path.isfile(file_path):
                lower_path = file_path.lower()
                if lower_path.endswith(('.jpg', '.jpeg')):
                    valid_images.append(file_path)
                elif lower_path.endswith('.png'):
                    try:
                        img = Image.open(file_path)
                        if img.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            background.paste(img, mask=img.split()[-1])
                            img = background
                        jpeg_path = os.path.splitext(file_path)[0] + '_converted.jpg'
                        img.convert('RGB').save(jpeg_path, 'JPEG', quality=95)
                        valid_images.append(jpeg_path)
                    except Exception as e:
                        self.error_logging(f"Error converting PNG file {file_path}", f"{e}")
                        invalid_files.append(file_path)
                elif lower_path.endswith('.pdf'):
                    pdf_files.append(file_path)
                else:
                    invalid_files.append(file_path)
            else:
                invalid_files.append(file_path)

        # Process valid image files
        if valid_images:
            self.process_new_images(valid_images)
            

            # Clean up any temporary converted files
            for image_path in valid_images:
                if image_path.endswith('_converted.jpg'):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        self.error_logging(f"Error removing temporary file {image_path}", f"{e}")

        # Process PDF files
        if pdf_files:
            for pdf_file in pdf_files:
                try:
                    self.open_pdf(pdf_file)
                except Exception as e:
                    self.error_logging(f"Error processing PDF file {pdf_file}", f"{e}")
                    messagebox.showerror("Error", f"Failed to process PDF file {pdf_file}: {e}")
        
        # Report invalid files
        if invalid_files:
            invalid_files_str = "\n".join(invalid_files)
            self.error_logging(f"Invalid files not processed: {invalid_files_str}", level="WARNING")
            messagebox.showwarning("Invalid Files", 
                f"The following files were not processed because they are not valid image or PDF files:\n\n{invalid_files_str}")
                
    def get_full_path(self, path):
        # If the path isn't a string, return an empty string.
        if not isinstance(path, str):
            return ""
        # If it's already absolute, return it.
        if os.path.isabs(path):
            return path
        # If a project is open, join with the project directory.
        if hasattr(self, 'project_directory') and self.project_directory:
            return os.path.join(self.project_directory, path)
        # Fallback: return the absolute path relative to the current directory.
        return os.path.abspath(path)
        
    def get_relative_path(self, path, base_path=None):
        """
        Convert an absolute path to a path relative to base_path.
        If base_path is not provided, use self.project_directory.
        """
        # If the path isn't a string or is empty, return an empty string
        if not isinstance(path, str) or not path:
            return ""
            
        # If the path is already relative, return it as is
        if not os.path.isabs(path):
            return path
            
        # Use project_directory as base_path if not provided
        if base_path is None:
            if hasattr(self, 'project_directory') and self.project_directory:
                base_path = self.project_directory
            else:
                # No base path to make relative to, return the path as is
                return path
                
        try:
            # Convert absolute path to path relative to base_path
            return os.path.relpath(path, base_path)
        except ValueError:
            # Handle case where paths are on different drives in Windows
            return path

    def parse_collation_response(self, response_text):
        """
        Parse lines like:
        Response:
        correct_spelling = variant1; variant2...
        ...
        Return a dict: { correct_spelling: [variant1, variant2...] }
        """
        try:
            if not response_text or not isinstance(response_text, str):
                self.error_logging("Empty or invalid response text", level="WARNING")
                return {}
                
            coll_dict = {}
            lines = response_text.splitlines()
            
            # Debug logging
            self.error_logging(f"Parsing {len(lines)} lines from response", level="DEBUG")
            
            response_found = False
            for ln in lines:
                ln = ln.strip()
                if not ln:
                    continue
                    
                # Check for "Response:" header and skip it
                if ln.lower().startswith("response:"):
                    response_found = True
                    continue
                
                # Handle various formatting possibilities
                if '=' in ln:
                    # Standard format: correct = variant1; variant2
                    parts = ln.split('=', 1)
                    correct = parts[0].strip()
                    variations_text = parts[1].strip()
                    
                    # Handle different delimiter styles
                    if ';' in variations_text:
                        variations = variations_text.split(';')
                    elif ',' in variations_text:
                        variations = variations_text.split(',')
                    else:
                        variations = [variations_text]
                        
                    variations = [v.strip() for v in variations if v.strip()]
                    
                    if correct and variations:
                        # If the correct term already exists, merge the variations
                        if correct in coll_dict:
                            coll_dict[correct].extend(variations)
                            # Remove duplicates
                            coll_dict[correct] = list(set(coll_dict[correct]))
                        else:
                            coll_dict[correct] = variations
                            
                        self.error_logging(f"Parsed entry: {correct} = {variations}", level="DEBUG")
                    
                # Handle case where line might be a continuation with no '=' sign
                elif response_found and len(coll_dict) > 0 and ln and ';' in ln:
                    # This might be a continuation line
                    last_key = list(coll_dict.keys())[-1]
                    variations = [v.strip() for v in ln.split(';') if v.strip()]
                    if variations:
                        coll_dict[last_key].extend(variations)
                        self.error_logging(f"Added continuation line to {last_key}: {variations}", level="DEBUG")
            
            # Final debugging info
            total_variants = sum(len(variants) for variants in coll_dict.values())
            self.error_logging(f"Parsed {len(coll_dict)} unique terms with {total_variants} total variants", level="DEBUG")
            
            return coll_dict
            
        except Exception as e:
            self.error_logging(f"Error parsing collation response: {str(e)}")
            return {}

    def apply_collation_dict(self, coll_dict, is_names=True):
        """
        For each row, find-and-replace all variations in the active text column.
        If is_names=True, we're applying name variants; else place variants.
        """
        import re

        for idx, row in self.main_df.iterrows():
            active_col = row.get('Text_Toggle', None)
            if active_col not in ["Original_Text", "First_Draft", "Final_Draft"]:
                continue
            
            old_text = row[active_col]
            if not isinstance(old_text, str) or not old_text.strip():
                continue

            # For each correct spelling => list of variants
            for correct_term, variants in coll_dict.items():
                for var in variants:
                    pattern = re.compile(re.escape(var), re.IGNORECASE)
                    old_text = pattern.sub(correct_term, old_text)

            self.main_df.at[idx, active_col] = old_text

        # Optionally refresh text if current row changed
        self.load_text()
        self.counter_update()

    def on_closing(self):
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            # Save any pending changes before quitting
            if not self.main_df.empty:
                current_display = self.main_df.loc[self.page_counter, 'Text_Toggle']
                if current_display != "None":
                    # Get the current text from the text widget
                    text = self.clean_text(self.text_display.get("1.0", tk.END))
                    
                    # Save the text to the appropriate column based on CURRENT display type
                    if current_display == "Original_Text":
                        self.main_df.loc[self.page_counter, 'Original_Text'] = text
                    elif current_display == "First_Draft":
                        self.main_df.loc[self.page_counter, 'First_Draft'] = text
                    elif current_display == "Final_Draft":
                        self.main_df.loc[self.page_counter, 'Final_Draft'] = text
                    elif current_display == "Translation":
                        self.main_df.loc[self.page_counter, 'Translation'] = text
            
            self.quit()
            

# GUI Actions / Toggles

    def run_collation_and_open_window(self):
        # 1) Collect suggestions from the LLM automatically
        self.collate_names_and_places()

        # 2) Now show the user a GUI with the raw lines
        self.create_collate_names_places_window()

    def refresh_display(self):
        """Refresh the current image and text display with proper path handling"""
        if not self.main_df.empty:
            # Ensure page_counter is within valid bounds
            self.page_counter = min(self.page_counter, len(self.main_df) - 1)
            self.page_counter = max(0, self.page_counter)

            try:
                # Get image path
                image_path = self.main_df.iloc[self.page_counter]['Image_Path']
                
                # Convert to absolute path if necessary
                if not os.path.isabs(image_path):
                    image_path = os.path.join(self.project_directory, image_path)
                
                # Verify file exists
                if os.path.exists(image_path):
                    self.current_image_path = image_path
                    self.image_handler.load_image(self.current_image_path)
                    self.load_text()
                else:
                    messagebox.showerror("Error", f"Image file not found: {image_path}")
                    
                self.counter_update()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to refresh display: {str(e)}")
                self.error_logging(f"Refresh display error: {str(e)}")
        else:
            print("No images to display")
            # Clear the image display
            self.image_display.delete("all")
            # Clear the text display
            self.text_display.delete("1.0", tk.END)
            self.counter_update()
    
    def on_text_display_change(self, event=None):
        if self.main_df.empty:
            return
            
        # Get the current and new display modes
        current_display = self.main_df.loc[self.page_counter, 'Text_Toggle']
        selected = self.text_display_var.get()
        index = self.page_counter
        
        # Only update if we're switching to a different mode and not from None
        if current_display != "None" and current_display != selected:
            # Get the current text from the text widget
            text = self.clean_text(self.text_display.get("1.0", tk.END))
            
            # Save the text to the appropriate column based on CURRENT display type (not new one)
            if current_display == "Original_Text":
                self.main_df.loc[index, 'Original_Text'] = text
            elif current_display == "First_Draft":
                self.main_df.loc[index, 'First_Draft'] = text
            elif current_display == "Final_Draft":
                self.main_df.loc[index, 'Final_Draft'] = text
            elif current_display == "Translation":
                self.main_df.loc[index, 'Translation'] = text
            
        # Map display names to DataFrame values
        display_map = {
            "None": "None",
            "Original_Text": "Original_Text",
            "First_Draft": "First_Draft",
            "Final_Draft": "Final_Draft",
            "Translation": "Translation"
        }
        
        # Update the Text_Toggle in the DataFrame
        self.main_df.at[index, 'Text_Toggle'] = display_map[selected]
        
        # Reload the text
        self.load_text()
        
        # Apply highlighting based on current settings
        self.highlight_text()
  
    def toggle_text(self):
        if self.main_df.empty:
            return

        # Get current state before toggling
        index = self.page_counter
        current_toggle = self.main_df.loc[index, 'Text_Toggle']
        
        # Only save changes if we're not in "None" mode
        if current_toggle != "None":
            # Get the current text from the text widget
            text = self.clean_text(self.text_display.get("1.0", tk.END))
            
            # Save the text to the appropriate column based on CURRENT display type
            if current_toggle == "Original_Text":
                self.main_df.loc[index, 'Original_Text'] = text
            elif current_toggle == "First_Draft":
                self.main_df.loc[index, 'First_Draft'] = text
            elif current_toggle == "Final_Draft":
                self.main_df.loc[index, 'Final_Draft'] = text
            elif current_toggle == "Translation":
                self.main_df.loc[index, 'Translation'] = text
            
        has_translation = pd.notna(self.main_df.loc[index, 'Translation']) and self.main_df.loc[index, 'Translation'].strip()
        has_corrected = pd.notna(self.main_df.loc[index, 'First_Draft']) and self.main_df.loc[index, 'First_Draft'].strip()
        has_final = pd.notna(self.main_df.loc[index, 'Final_Draft']) and self.main_df.loc[index, 'Final_Draft'].strip()
        has_original = pd.notna(self.main_df.loc[index, 'Original_Text']) and self.main_df.loc[index, 'Original_Text'].strip()

        # Prioritize Translation if it exists
        if current_toggle == "Translation":
            if has_final:
                self.main_df.loc[index, 'Text_Toggle'] = "Final_Draft"
            elif has_corrected:
                self.main_df.loc[index, 'Text_Toggle'] = "First_Draft"
            elif has_original:
                self.main_df.loc[index, 'Text_Toggle'] = "Original_Text"
        elif current_toggle == "Original_Text":
            if has_corrected:
                self.main_df.loc[index, 'Text_Toggle'] = "First_Draft"
            elif has_final:
                self.main_df.loc[index, 'Text_Toggle'] = "Final_Draft"
            elif has_translation:
                self.main_df.loc[index, 'Text_Toggle'] = "Translation"
        elif current_toggle == "First_Draft":
            if has_final:
                self.main_df.loc[index, 'Text_Toggle'] = "Final_Draft"
            elif has_translation:
                self.main_df.loc[index, 'Text_Toggle'] = "Translation"
            else:
                self.main_df.loc[index, 'Text_Toggle'] = "Original_Text"
        elif current_toggle == "Final_Draft":
            if has_translation:
                self.main_df.loc[index, 'Text_Toggle'] = "Translation"
            else:
                self.main_df.loc[index, 'Text_Toggle'] = "Original_Text"

        self.load_text()
    
# Highlighting Functions

    def toggle_highlight_options(self):
        """Update highlight display based on toggle states without mutual exclusivity"""
        self.error_logging("Toggling highlight options", 
                          f"Names: {self.highlight_names_var.get()}, "
                          f"Places: {self.highlight_places_var.get()}, "
                          f"Changes: {self.highlight_changes_var.get()}, "
                          f"Errors: {self.highlight_errors_var.get()}", 
                          level="DEBUG")
        
        # No more mutual exclusivity between highlight types
        # Just apply whatever is toggled
        
        # Apply highlighting
        self.highlight_text()
        
        # Update menu item states
        self.update_highlight_menu_states()

    def highlight_names_or_places(self):
        """Highlight names and/or places in the text based on DataFrame data"""
        # Clear existing highlights first
        self.text_display.tag_remove("name_highlight", "1.0", tk.END)
        self.text_display.tag_remove("place_highlight", "1.0", tk.END)
        
        # If neither highlighting option is selected, return early
        if not self.highlight_names_var.get() and not self.highlight_places_var.get():
            self.error_logging("No highlighting options selected", level="DEBUG")
            return
            
        self.error_logging(f"Highlight names: {self.highlight_names_var.get()}, Highlight places: {self.highlight_places_var.get()}", level="DEBUG")
        
        # Get current page index
        current_index = self.page_counter
        self.error_logging(f"Current page index: {current_index}", level="DEBUG")
        
        try:
            # Check if we have names or places data in the main DataFrame
            if 'People' not in self.main_df.columns or 'Places' not in self.main_df.columns:
                self.error_logging("People or Places column missing in DataFrame", level="WARNING")
                return
                
            # Check if we're at a valid index
            if current_index not in self.main_df.index:
                self.error_logging(f"Invalid index {current_index} in DataFrame", level="WARNING")
                return
                
            def process_entities(entities_str, tag):
                self.error_logging(f"Processing entities for {tag}: {entities_str}", level="DEBUG")
                
                if pd.isna(entities_str) or not entities_str:
                    self.error_logging(f"No {tag} data to highlight", level="DEBUG")
                    return
                    
                entities = [entity.strip() for entity in entities_str.split(';')]
                self.error_logging(f"Entities to highlight: {entities}", level="DEBUG")
                
                for entity in entities:
                    # Skip entries with square brackets
                    if '[' in entity or ']' in entity:
                        continue
                    
                    self.error_logging(f"Highlighting entity: '{entity}'", level="DEBUG")
                    # First try to highlight the complete entity
                    self.highlight_term(entity, tag, exact_match=True)
                    
                    # Get all text content
                    full_text = self.text_display.get("1.0", tk.END)
                    
                    # Handle hyphenated words
                    if '-' in entity:
                        # Split the entity into parts
                        parts = entity.split('-')
                        
                        # Look for parts separated by newline
                        for i in range(len(parts)-1):
                            part1 = parts[i].strip()
                            part2 = parts[i+1].strip()
                            
                            # Create pattern to match part1 at end of line and part2 at start of next line
                            pattern = f"{part1}-?\n+{part2}"
                            matches = re.finditer(pattern, full_text, re.IGNORECASE)
                            
                            for match in matches:
                                # Convert string index to line.char format
                                start_pos = "1.0"
                                match_start = match.start()
                                match_end = match.end()
                                
                                # Find the line and character position for start and end
                                start_line = 1
                                start_char = 0
                                current_pos = 0
                                
                                for line_num, line in enumerate(full_text.split('\n'), 1):
                                    if current_pos + len(line) + 1 > match_start:
                                        start_line = line_num
                                        start_char = match_start - current_pos
                                        break
                                    current_pos += len(line) + 1
                                
                                end_line = start_line
                                for line in full_text[match_start:match_end].split('\n'):
                                    if line:
                                        end_line += 1
                                
                                # Add tags to both parts
                                start_index = f"{start_line}.{start_char}"
                                end_index = f"{end_line}.{len(part2)}"
                                self.error_logging(f"Adding hyphenated tag from {start_index} to {start_line}.end", level="DEBUG")
                                self.error_logging(f"Adding hyphenated tag from {end_line}.0 to {end_index}", level="DEBUG")
                                self.text_display.tag_add(tag, start_index, f"{start_line}.end")
                                self.text_display.tag_add(tag, f"{end_line}.0", end_index)
                    
                    # Also highlight individual words for names (except very short ones and common words)
                    if tag == "name_highlight":  # Only for names, not places
                        parts = entity.split()
                        for part in parts:
                            if len(part) > 2 and part.lower() not in ['the', 'and', 'of', 'in', 'on', 'at', 'la', 'le', 'les', 'de', 'du', 'des']:
                                self.error_logging(f"Highlighting name part: '{part}'", level="DEBUG")
                                self.highlight_term(part, tag, exact_match=False)
            
            # Process names if the highlight names option is checked
            if self.highlight_names_var.get():
                self.error_logging(f"Getting names from index {current_index}", level="DEBUG")
                names = self.main_df.loc[current_index, 'People']
                self.error_logging(f"Names data: {names}", level="DEBUG")
                if pd.notna(names) and names.strip():
                    process_entities(names, "name_highlight")
                else:
                    self.error_logging("No names data available", level="DEBUG")
            
            # Process places if the highlight places option is checked
            if self.highlight_places_var.get():
                self.error_logging(f"Getting places from index {current_index}", level="DEBUG")
                places = self.main_df.loc[current_index, 'Places']
                self.error_logging(f"Places data: {places}", level="DEBUG")
                if pd.notna(places) and places.strip():
                    process_entities(places, "place_highlight")
                else:
                    self.error_logging("No places data available", level="DEBUG")
        
        except Exception as e:
            self.error_logging(f"Error in highlight_names_or_places: {str(e)}")

    def highlight_term(self, term, tag, exact_match=False):
        """Helper function to highlight a specific term in the text"""
        if not term or len(term) < 1:
            self.error_logging(f"Skipping empty or too short term", level="DEBUG")
            return
            
        text_widget = self.text_display
        start_index = "1.0"
        
        self.error_logging(f"Highlighting term: '{term}' with tag '{tag}', exact_match={exact_match}", level="DEBUG")
        
        # Get full text content for better context
        full_text = text_widget.get("1.0", tk.END)
        
        # Escape special regex characters in the search term
        escaped_term = re.escape(term)
        
        found_count = 0
        try:
            # For exact matches, we want to find the term regardless of word boundaries
            # For non-exact matches, we want to respect word boundaries
            if exact_match:
                # Look for the term without word boundaries
                pattern = re.compile(escaped_term, re.IGNORECASE)
            else:
                # Look for the term with word boundaries
                pattern = re.compile(r'\b' + escaped_term + r'\b', re.IGNORECASE)
                
            # Find all matches in the text
            for match in pattern.finditer(full_text):
                match_start = match.start()
                match_end = match.end()
                
                # Convert string indices to Tkinter line.char format
                # First, count how many newlines appear before the match
                lines_before = full_text[:match_start].count('\n')
                
                # Find the character position on the line where the match starts
                if lines_before == 0:
                    # If match is on the first line, the char position is just match_start
                    start_char = match_start
                else:
                    # Otherwise, find the last newline before match and calculate char position
                    last_nl = full_text[:match_start].rindex('\n')
                    start_char = match_start - last_nl - 1
                
                # Calculate the end position
                if '\n' in full_text[match_start:match_end]:
                    # If match spans multiple lines, highlight to end of first line
                    # and handle remaining highlighting separately
                    next_nl = full_text[match_start:].find('\n')
                    first_line_end = match_start + next_nl
                    
                    # Highlight the first line part
                    start_index = f"{lines_before + 1}.{start_char}"
                    end_index = f"{lines_before + 1}.end"
                    text_widget.tag_add(tag, start_index, end_index)
                    
                    # Process remaining lines of the match
                    remaining_text = full_text[first_line_end+1:match_end]
                    remaining_lines = remaining_text.count('\n') + 1
                    
                    for i in range(remaining_lines):
                        line_num = lines_before + 2 + i
                        if i < remaining_lines - 1:
                            # For all but the last line, highlight the entire line
                            text_widget.tag_add(tag, f"{line_num}.0", f"{line_num}.end")
                        else:
                            # For the last line, highlight up to the end of the match
                            last_line_chars = len(remaining_text.split('\n')[-1])
                            text_widget.tag_add(tag, f"{line_num}.0", f"{line_num}.{last_line_chars}")
                else:
                    # Match is on a single line
                    start_index = f"{lines_before + 1}.{start_char}"
                    end_index = f"{lines_before + 1}.{start_char + (match_end - match_start)}"
                    text_widget.tag_add(tag, start_index, end_index)
                
                found_count += 1
            
            self.error_logging(f"Found and highlighted {found_count} instances of '{term}'", level="DEBUG")
            
        except Exception as e:
            self.error_logging(f"Error highlighting term '{term}': {str(e)}")
            # Fall back to the simple approach if the regex-based approach fails
            try:
                current_idx = "1.0"
                while True:
                    current_idx = text_widget.search(term, current_idx, tk.END, nocase=True)
                    if not current_idx:
                        break
                    end_idx = f"{current_idx}+{len(term)}c"
                    text_widget.tag_add(tag, current_idx, end_idx)
                    current_idx = end_idx
            except Exception as inner_e:
                self.error_logging(f"Fallback highlighting also failed for '{term}': {str(inner_e)}")

    def highlight_text(self):
        """Apply all selected types of highlighting based on toggle states"""
        # Clear all existing highlights first
        self.text_display.tag_remove("name_highlight", "1.0", tk.END)
        self.text_display.tag_remove("place_highlight", "1.0", tk.END)
        self.text_display.tag_remove("change_highlight", "1.0", tk.END)
        self.text_display.tag_remove("error_highlight", "1.0", tk.END)

        # Apply each highlight type if its toggle is on
        if self.highlight_names_var.get() or self.highlight_places_var.get():
            self.highlight_names_or_places()
            
        if self.highlight_changes_var.get():
            self.highlight_changes()
            
        if self.highlight_errors_var.get():
            self.highlight_errors()

    def highlight_changes(self):
        """
        Highlight differences between the current text level and the previous level:
        - When viewing First_Draft, highlight changes from Original_Text
        - When viewing Final_Draft, highlight changes from First_Draft
        """
        index = self.page_counter
        current_toggle = self.main_df.loc[index, 'Text_Toggle']
        
        # Early exit if we're at the Original_Text level (no previous text to compare with)
        if current_toggle == "Original_Text" or current_toggle == "None":
            return
            
        # Determine which texts to compare based on current level
        if current_toggle == "First_Draft":
            # Compare First_Draft with Original_Text
            current_text = self.main_df.loc[index, 'First_Draft']
            previous_text = self.main_df.loc[index, 'Original_Text']
            
            # Skip if either text is missing
            if pd.isna(current_text) or pd.isna(previous_text):
                return
                
        elif current_toggle == "Final_Draft":
            # Compare Final_Draft with First_Draft
            current_text = self.main_df.loc[index, 'Final_Draft']
            previous_text = self.main_df.loc[index, 'First_Draft']
            
            # If First_Draft is empty, compare with Original_Text instead
            if pd.isna(previous_text) or previous_text.strip() == '':
                previous_text = self.main_df.loc[index, 'Original_Text']
                
            # Skip if either text is missing
            if pd.isna(current_text) or pd.isna(previous_text):
                return
        else:
            # Unrecognized toggle value
            return
        
        # Use the advanced highlighting
        highlight_text_differences(self.text_display, current_text, previous_text)

    def highlight_errors(self):
        """Highlight error terms from the Errors column"""
        try:
            self.error_logging("In highlight_errors function", level="DEBUG")
            
            # Get current page index and text
            index = self.page_counter
            self.error_logging(f"Current page index: {index}", level="DEBUG")
            if index not in self.main_df.index:
                self.error_logging("Index not in DataFrame", level="WARNING")
                return
                
            # Get the current text display mode
            selected = self.text_display_var.get()
            self.error_logging(f"Current text display mode: {selected}", level="DEBUG")
            
            # Map display names to DataFrame columns - fixed to match actual values
            text_map = {
                "None": None,
                "Original_Text": "Original_Text",
                "First_Draft": "First_Draft", 
                "Final_Draft": "Final_Draft"
            }
            
            # Get the current text column
            current_col = text_map.get(selected)
            if not current_col:
                self.error_logging("No valid text column selected", level="WARNING")
                return
            self.error_logging(f"Current text column: {current_col}", level="DEBUG")
                
            # Get errors for current page
            errors = self.main_df.at[index, 'Errors']
            self.error_logging(f"Errors from DataFrame: {errors}", level="DEBUG")
            if pd.isna(errors) or not errors.strip():
                self.error_logging("No errors found in DataFrame", level="DEBUG")
                return
                
            # Process and highlight errors
            def process_errors(errors_str):
                if not errors_str:
                    return
                error_terms = [term.strip() for term in errors_str.split(';') if term.strip()]
                self.error_logging(f"Error terms to highlight: {error_terms}", level="DEBUG")
                for term in error_terms:
                    self.highlight_term(term, "error_highlight", exact_match=True)
            
            process_errors(errors)
                
        except Exception as e:
            self.error_logging(f"Error highlighting errors: {str(e)}")

# DF Update Functions

    def update_df(self):
        self.save_toggle = False
        
        # Don't save anything if current display is "None"
        if self.text_display_var.get() == "None":
            return
            
        # Get the text from the Text widget and clean it
        text = self.clean_text(self.text_display.get("1.0", tk.END))
        
        index = self.page_counter
        selected = self.text_display_var.get()
        
        # Map display names to DataFrame columns
        if selected == "Original_Text":
            self.main_df.loc[index, 'Original_Text'] = text
            self.main_df.loc[index, 'Text_Toggle'] = "Original_Text"
        elif selected == "First_Draft":
            self.main_df.loc[index, 'First_Draft'] = text
            self.main_df.loc[index, 'Text_Toggle'] = "First_Draft"
        elif selected == "Final_Draft":
            self.main_df.loc[index, 'Final_Draft'] = text
            self.main_df.loc[index, 'Text_Toggle'] = "Final_Draft"
        elif selected == "Translation":
            self.main_df.loc[index, 'Translation'] = text
            self.main_df.loc[index, 'Text_Toggle'] = "Translation"

    def update_df_with_ai_job_response(self, ai_job, index, response):
        """Update the DataFrame with the AI job response"""
        try:
            if response == "Error":
                return
            
            # Get the current text display mode
            selected = self.text_display_var.get()
            
            # Update based on job type
            if ai_job == "HTR":
                self.main_df.loc[index, 'Original_Text'] = response
                self.main_df.loc[index, 'Text_Toggle'] = "Original_Text"
            elif ai_job == "Correct_Text":
                self.main_df.loc[index, 'First_Draft'] = response
                self.main_df.loc[index, 'Text_Toggle'] = "First_Draft"
            elif ai_job == "Get_Names_and_Places":
                print(f"\nProcessing Names and Places response: {response}")
                # Make sure the People and Places columns exist
                if 'People' not in self.main_df.columns:
                    self.main_df['People'] = ""
                if 'Places' not in self.main_df.columns:
                    self.main_df['Places'] = ""
                
                # Initialize empty values
                names = ""
                places = ""
                
                # New improved parsing approach that handles multiple formats
                lines = response.split('\n')
                
                # Try to find headers - check for both "Header:" format and "Header: data" format
                names_data = []
                places_data = []
                in_names_section = False
                in_places_section = False
                
                # First, try to handle the case where headers are on their own lines
                for i, line in enumerate(lines):
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # Check for headers
                    if line.lower() == "names:":
                        in_names_section = True
                        in_places_section = False
                        continue
                    elif line.lower() == "places:":
                        in_names_section = False
                        in_places_section = True
                        continue
                    
                    # Add data to the appropriate section
                    if in_names_section:
                        names_data.append(line)
                    elif in_places_section:
                        places_data.append(line)
                
                # If we found headers on their own lines, use the data we collected
                if names_data or places_data:
                    names = "; ".join(names_data)
                    places = "; ".join(places_data)
                else:
                    # Fall back to looking for "Header: data" format
                    for line in lines:
                        line = line.strip()
                        
                        # Look for "Names:" prefix followed by data
                        if line.lower().startswith("names:"):
                            # Extract everything after "Names:"
                            names_part = line[line.lower().find("names:") + 6:].strip()
                            if names_part:
                                names = names_part
                        
                        # Look for "Places:" prefix followed by data
                        elif line.lower().startswith("places:"):
                            # Extract everything after "Places:"
                            places_part = line[line.lower().find("places:") + 7:].strip()
                            if places_part:
                                places = places_part
                
                print(f"Extracted Names: '{names}'")
                print(f"Extracted Places: '{places}'")
                
                # Update the DataFrame
                self.main_df.loc[index, 'People'] = names
                self.main_df.loc[index, 'Places'] = places
                
                print(f"Updated DataFrame - People: '{self.main_df.loc[index, 'People']}'")
                print(f"Updated DataFrame - Places: '{self.main_df.loc[index, 'Places']}'")
                
                # Automatically enable name and place highlighting if data was found
                if names.strip():
                    self.highlight_names_var.set(True)
                if places.strip():
                    self.highlight_places_var.set(True)
                
                # No longer needed: self.highlight_changes_var.set(False)
                # We now allow multiple highlight types simultaneously
            elif ai_job == "Metadata":
                self.extract_metadata_from_response(index, response)
            elif ai_job == "Chunk_Text":
                # Store the response in Final_Draft
                self.main_df.loc[index, 'Final_Draft'] = response
                self.main_df.loc[index, 'Text_Toggle'] = "Final_Draft"
                
                # If translation exists, also store a copy in Translation column
                if pd.notna(self.main_df.loc[index, 'Translation']) and self.main_df.loc[index, 'Translation'].strip():
                    # We'll handle this in a separate AI job for translation chunking
                    pass
            elif ai_job == "Chunk_Translation":
                # Special job type for chunking translations
                if pd.notna(self.main_df.loc[index, 'Translation']) and self.main_df.loc[index, 'Translation'].strip():
                    self.main_df.loc[index, 'Translation'] = response
            elif ai_job == "Auto_Rotate":
                self.update_image_rotation(index, response)
            elif ai_job == "Identify_Errors":
                print("\nProcessing Identify_Errors response:")
                print(f"Raw response: {response}")
                
                # Take just the first line
                errors = response.split('\n')[0].strip()
                print(f"Extracted errors: {errors}")
                self.main_df.loc[index, 'Errors'] = errors
                
                # If there are errors, highlight them in the text
                if errors:
                    # Split errors by semicolon and strip whitespace
                    error_terms = [term.strip() for term in errors.split(';') if term.strip()]
                    print(f"Error terms to highlight: {error_terms}")
                    
                    # Clear existing highlights
                    self.text_display.tag_remove("error_highlight", "1.0", tk.END)
                    
                    # Add new error highlights
                    for term in error_terms:
                        self.highlight_term(term, "error_highlight", exact_match=True)
                    
                    # Configure error highlight style
                    self.text_display.tag_configure("error_highlight", background="cyan")
                    
                    # Turn on error highlighting
                    self.highlight_errors_var.set(True)
                    # No longer needed: self.highlight_changes_var.set(False)
                    # We now allow multiple highlight types simultaneously
            elif ai_job == "Translation":
                self.main_df.loc[index, 'Translation'] = response
                self.main_df.loc[index, 'Text_Toggle'] = "Translation"
            
            # Load the updated text
            self.load_text()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update DataFrame: {str(e)}")
            self.error_logging(f"Failed to update DataFrame: {str(e)}")

    def update_image_rotation(self, index, response):
        # Get the image path from the DataFrame.
        image_path = self.main_df.loc[index, 'Image_Path']
        # Use get_full_path to resolve relative paths
        image_path = self.get_full_path(image_path)
        
        # Dictionary mapping responses to orientation in degrees.
        orientation_map = {
            "standard": 0,
            "rotated 90 clockwise": 90,
            "rotated 180 degrees": 180,
            "rotated 90 counter-clockwise": 270,
            "no text": 0
        }
        
        response = response.strip().lower()
        print(f"\nInput Response: '{response}'")
        
        if response not in orientation_map:
            print(f"ERROR: Could not parse rotation angle from response: {response}")
            return
        
        current_orientation = orientation_map[response]
        print(f"Detected Orientation: {current_orientation} degrees from standard")
        
        if current_orientation == 0:
            print(f"No rotation needed for page index {index}.")
            return
        
        correction_angle = current_orientation
        print(f"Applying correction angle: {correction_angle} degrees")
        
        try:
            with Image.open(image_path) as img:
                rotated_img = img.rotate(correction_angle, expand=True)
                rotated_img.save(image_path, quality=95)
            
            if index == self.page_counter:
                self.image_handler.load_image(image_path)
                    
            print(f"Corrected page index {index} from {current_orientation} degrees to standard orientation")
        except Exception as e:
            print(f"Error rotating image at index {index}: {e}")
            self.error_logging(f"Error rotating image at index {index}: {e}")

    def revert_current_page(self):
        index = self.page_counter
        current_selection = self.text_display_var.get()
        
        if current_selection == "Translation":
            if messagebox.askyesno("Revert Text", 
                                "Do you want to revert the Translation and return to the final draft version?"):
                self.main_df.loc[index, 'Translation'] = ""
                if pd.notna(self.main_df.loc[index, 'Final_Draft']) and self.main_df.loc[index, 'Final_Draft'].strip():
                    self.text_display_var.set("Final_Draft")
                    self.main_df.loc[index, 'Text_Toggle'] = "Final_Draft"
                elif pd.notna(self.main_df.loc[index, 'First_Draft']) and self.main_df.loc[index, 'First_Draft'].strip():
                    self.text_display_var.set("First_Draft")
                    self.main_df.loc[index, 'Text_Toggle'] = "First_Draft"
                else:
                    self.text_display_var.set("Original_Text")
                    self.main_df.loc[index, 'Text_Toggle'] = "Original_Text"
        elif current_selection == "Final_Draft":
            if messagebox.askyesno("Revert Text", 
                                "Do you want to revert to the first draft version?"):
                self.main_df.loc[index, 'Final_Draft'] = ""
                self.text_display_var.set("First_Draft")
                self.main_df.loc[index, 'Text_Toggle'] = "First_Draft"
                
        elif current_selection == "First_Draft":
            if messagebox.askyesno("Revert Text", 
                                "Do you want to revert to the Original_Text version?"):
                self.main_df.loc[index, 'First_Draft'] = ""
                self.main_df.loc[index, 'Final_Draft'] = ""
                self.text_display_var.set("Original_Text")
                self.main_df.loc[index, 'Text_Toggle'] = "Original_Text"
                
        elif current_selection == "Original_Text":
            messagebox.showinfo("Original_Text", 
                            "You are already viewing the Original_Text version.")
            return
        
        self.load_text()
    
    def revert_all_pages(self):
        if messagebox.askyesno("Confirm Revert", 
                            "Are you sure you want to revert ALL pages to their Original_Text? "
                            "This will remove all corrections, translations, and cannot be undone."):
            self.main_df['Final_Draft'] = ""
            self.main_df['First_Draft'] = ""
            self.main_df['Translation'] = ""
            self.main_df['Text_Toggle'] = "Original_Text"
            self.text_display_var.set("Original_Text")
            
        self.load_text()
        self.counter_update()

# External Tools

    def find_and_replace(self, event=None):
        self.find_replace.update_main_df(self.main_df)
        self.find_replace.find_and_replace(event) 
    
    def update_api_handler(self):
        self.api_handler = APIHandler(
            self.settings.openai_api_key, 
            self.settings.anthropic_api_key, 
            self.settings.google_api_key,
            self
        )

    def edit_single_image(self):
        if self.main_df.empty:
            messagebox.showerror("Error", "No images have been loaded. Please load some images first.")
            return

        # Hide the main window
        self.withdraw()

        # Create a temporary directory for the single image
        single_temp_dir = os.path.join(self.images_directory, "single_temp")
        os.makedirs(single_temp_dir, exist_ok=True)

        try:
            # Copy the current image to temp directory
            current_image_path = self.main_df.loc[self.page_counter, 'Image_Path']
            temp_image_name = os.path.basename(current_image_path)
            temp_image_path = os.path.join(single_temp_dir, temp_image_name)
            
            shutil.copy2(current_image_path, temp_image_path)

            # Create an instance of ImageSplitter with the temp directory
            image_splitter = ImageSplitter(single_temp_dir)
            
            # Wait for the ImageSplitter window to close
            self.wait_window(image_splitter)

            if image_splitter.status == "saved":
                self.process_edited_single_image(current_image_path)
            elif image_splitter.status == "discarded":
                pass

        except Exception as e:
            print(f"Error in edit_single_image: {str(e)}")
            messagebox.showerror("Error", f"An error occurred while editing the image: {str(e)}")

        finally:
            # Clean up
            if os.path.exists(single_temp_dir):
                shutil.rmtree(single_temp_dir, ignore_errors=True)
            
            # Show the main window again
            self.deiconify()

    def edit_all_images(self):
        if self.main_df.empty:
            messagebox.showerror("Error", "No images have been loaded. Please load some images first.")
            return

        if not messagebox.askyesno("Warning", 
                                    "This action will replace all current images and text with the edited versions. "
                                    "All existing text will be lost. This action cannot be undone. "
                                    "Do you want to continue?"):
            return

        self.withdraw()
        all_temp_dir = os.path.join(self.images_directory, "all_temp")
        
        try:
            # Clean up existing temp directory if it exists
            if os.path.exists(all_temp_dir):
                shutil.rmtree(all_temp_dir)
            
            # Create fresh temp directory
            os.makedirs(all_temp_dir, exist_ok=True)

            # Copy all images to temp directory using absolute paths
            for index, row in self.main_df.iterrows():
                current_image_path = row['Image_Path']
                # Use get_full_path to resolve relative paths
                current_image_path = self.get_full_path(current_image_path)
                
                if os.path.exists(current_image_path):
                    temp_image_name = f"{index+1:04d}.jpg"
                    temp_image_path = os.path.join(all_temp_dir, temp_image_name)
                    shutil.copy2(current_image_path, temp_image_path)
                else:
                    raise FileNotFoundError(f"Image not found: {current_image_path}")

            image_splitter = ImageSplitter(all_temp_dir)
            self.wait_window(image_splitter)

            if image_splitter.status == "saved":
                self.reset_application()
                pass_images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                            "util", "subs", "pass_images")
                
                if not os.path.exists(pass_images_dir):
                    raise FileNotFoundError(f"pass_images directory not found at: {pass_images_dir}")
                
                self.directory_path = pass_images_dir
                self.load_files_from_folder_no_text()
            elif image_splitter.status == "discarded":
                messagebox.showinfo("Cancelled", "Image editing was cancelled. No changes were made.")

        except Exception as e:
            print(f"Error in edit_all_images: {str(e)}")
            messagebox.showerror("Error", f"An error occurred while editing the images: {str(e)}")
            self.error_logging(f"Error in edit_all_images: {str(e)}")
        finally:
            # Clean up temp directory
            if os.path.exists(all_temp_dir):
                try:
                    shutil.rmtree(all_temp_dir)
                except Exception as e:
                    print(f"Failed to clean up temp directory: {str(e)}")
            
            self.deiconify()
            # Functions Manipulating the DF

    def process_edited_single_image(self, original_image_path):
        try:
            pass_images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                        "util", "subs", "pass_images")

            if not os.path.exists(pass_images_dir):
                raise FileNotFoundError(f"pass_images directory not found at: {pass_images_dir}")

            # Get edited images and sort them numerically
            edited_images = sorted(
                [f for f in os.listdir(pass_images_dir) if f.endswith('.jpg')],
                key=lambda x: int(os.path.splitext(x)[0])
            )

            if not edited_images:
                raise ValueError("No edited images found")

            current_index = self.page_counter
            
            # Create new rows for all split images
            new_rows = []
            for i, img_file in enumerate(edited_images):
                edited_image_path = os.path.join(pass_images_dir, img_file)
                new_index = current_index + i
                new_image_name = f"{new_index+1:04d}.jpg"
                
                # Ensure target directory exists
                target_dir = os.path.join(self.project_directory, "images")
                os.makedirs(target_dir, exist_ok=True)
                
                new_image_path = os.path.join(target_dir, new_image_name)
                
                # Copy image
                shutil.copy2(edited_image_path, new_image_path)
                
                # Create new row
                new_row = {
                    "Index": new_index,
                    "Page": f"{new_index+1:04d}_p{new_index+1:03d}",
                    "Original_Text": "",
                    "First_Draft": "",
                    "Final_Draft": "",
                    "Image_Path": os.path.join("images", new_image_name),
                    "Text_Path": "",
                    "Text_Toggle": "None"
                }
                new_rows.append(new_row)
            
            # Update DataFrame
            self.main_df = pd.concat([
                self.main_df.iloc[:current_index],
                pd.DataFrame(new_rows),
                self.main_df.iloc[current_index+1:]
            ]).reset_index(drop=True)

            # Clean up pass_images directory
            try:
                for file in os.listdir(pass_images_dir):
                    file_path = os.path.join(pass_images_dir, file)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
            except Exception as e:
                print(f"Warning: Failed to clean up some temporary files: {e}")

            # Refresh display
            self.refresh_display()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process edited images: {str(e)}")
            self.error_logging(f"Process edited image error: {str(e)}") 

    async def process_api_request(self, system_prompt, user_prompt, temp, image_data, 
                                    text_to_process, val_text, engine, index, 
                                    is_base64=True, formatting_function=False, ai_job=None, job_params=None):
        try:
            return await self.api_handler.route_api_call(
                engine=engine,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temp=temp,
                image_data=image_data,
                text_to_process=text_to_process,
                val_text=val_text,
                index=index,
                is_base64=is_base64,
                formatting_function=formatting_function,
                job_type=ai_job,
                job_params=job_params
            )
            
        except Exception as e:
            print(f"API Error: {e}")
            return "Error", index

# AI Functions

    def ai_function(self, all_or_one_flag="All Pages", ai_job="HTR", batch_size=50):
        # Get job parameters including batch_size
        job_params = self.setup_job_parameters(ai_job)
        batch_size = job_params.get('batch_size', 50)  # Use job-specific batch size
    
        self.toggle_button_state()
        error_count = 0
        processed_indices = set() 

        try:
            # Handle Chunk_Text separately since it will create its own progress windows
            if ai_job == "Chunk_Text":
                if all_or_one_flag == "Current Page":
                    row = self.page_counter
                    # Check if there's text to process using the new find_chunk_text method
                    text_to_process, has_translation = self.find_chunk_text(row)
                    if text_to_process.strip():
                        batch_df = self.main_df.loc[[row]]
                    else:
                        messagebox.showinfo("Skip", "This page has no text to chunk.")
                        return
                else:
                    # Process only pages that have text using find_chunk_text
                    batch_df = self.main_df[
                        self.main_df.apply(lambda row: bool(self.find_chunk_text(row.name)[0].strip()), axis=1)
                    ]
                        
                # First process normal text
                self.process_chunk_text(batch_df, all_or_one_flag, "Chunk_Text")
                
                # Then process translations if they exist
                if all_or_one_flag == "Current Page":
                    # Check if current page has translation
                    row = self.page_counter
                    _, has_translation = self.find_chunk_text(row)
                    if has_translation:
                        # Process translation for current page
                        self.process_translation_chunks(self.main_df.loc[[row]], all_or_one_flag)
                else:
                    # Find all pages with translations and process them
                    translation_df = self.main_df[
                        self.main_df.apply(lambda row: bool(self.find_chunk_text(row.name)[1]), axis=1)
                    ]
                    if not translation_df.empty:
                        self.process_translation_chunks(translation_df, all_or_one_flag)
                
                # Restore button state and exit
                self.toggle_button_state()
                return
            
            # For all other job types, continue with the standard progress window
            progress_title = f"Applying {ai_job} to {'Current Page' if all_or_one_flag == 'Current Page' else 'All Pages'}..."
            progress_window, progress_bar, progress_label = self.progress_bar.create_progress_window(progress_title)
            self.progress_bar.update_progress(0, 1)

            responses_dict = {}
            futures_to_index = {}
            processed_rows = 0
            total_rows = 0

            # Get the Skip Completed Pages toggle value
            skip_completed = self.skip_completed_pages.get()

            # Modified batch_df setup for different job types
            if ai_job == "HTR":
                if all_or_one_flag == "Current Page":
                    # Only process current page if it has no Original_Text or if we're not skipping completed
                    row = self.page_counter
                    if (skip_completed and (pd.isna(self.main_df.loc[row, 'Original_Text']) or self.main_df.loc[row, 'Original_Text'].strip() == '')) or not skip_completed:
                        batch_df = self.main_df.loc[[row]]
                    else:
                        messagebox.showinfo("Skip", "This page already has recognized text.")
                        return
                else:
                    if skip_completed:
                        # Filter for pages without Original_Text
                        batch_df = self.main_df[
                            (self.main_df['Image_Path'].notna()) & 
                            (self.main_df['Image_Path'] != '') & 
                            ((self.main_df['Original_Text'].isna()) | (self.main_df['Original_Text'] == ''))
                        ]
                    else:
                        # Process all pages with images regardless of content
                        batch_df = self.main_df[
                            (self.main_df['Image_Path'].notna()) & 
                            (self.main_df['Image_Path'] != '')
                        ]

            elif ai_job == "Correct_Text":
                if all_or_one_flag == "Current Page":
                    # Logic for Current Page with Skip Completed option
                    row = self.page_counter
                    if skip_completed:
                        # Only process if it has Original_Text but no First_Draft
                        if pd.notna(self.main_df.loc[row, 'Original_Text']) and \
                        (pd.isna(self.main_df.loc[row, 'First_Draft']) or self.main_df.loc[row, 'First_Draft'].strip() == ''):
                            batch_df = self.main_df.loc[[row]]
                        else:
                            messagebox.showinfo("Skip", "This page either lacks Original_Text or already has corrections.")
                            return
                    else:
                        # Process regardless of First_Draft status as long as Original_Text exists
                        if pd.notna(self.main_df.loc[row, 'Original_Text']):
                            batch_df = self.main_df.loc[[row]]
                        else:
                            messagebox.showinfo("Skip", "This page lacks Original_Text.")
                            return
                else:
                    # Logic for All Pages with Skip Completed option
                    if skip_completed:
                        # Filter for pages with Original_Text but without First_Draft
                        batch_df = self.main_df[
                            (self.main_df['Original_Text'].notna()) & 
                            (self.main_df['Original_Text'] != '') & 
                            ((self.main_df['First_Draft'].isna()) | (self.main_df['First_Draft'] == ''))
                        ]
                    else:
                        # Process all pages with Original_Text regardless of First_Draft status
                        batch_df = self.main_df[
                            (self.main_df['Original_Text'].notna()) & 
                            (self.main_df['Original_Text'] != '')
                        ]
            elif ai_job == "Create_Final_Draft":
                if all_or_one_flag == "Current Page":
                    # Logic for Current Page with Skip Completed option
                    row = self.page_counter
                    if skip_completed:
                        # Only process if it has First_Draft but no Final_Draft
                        if pd.notna(self.main_df.loc[row, 'First_Draft']) and \
                        (pd.isna(self.main_df.loc[row, 'Final_Draft']) or self.main_df.loc[row, 'Final_Draft'].strip() == ''):
                            batch_df = self.main_df.loc[[row]]
                        else:
                            messagebox.showinfo("Skip", "This page either lacks First_Draft or already has Final_Draft.")
                            return
                    else:
                        # Process regardless of Final_Draft status as long as First_Draft exists
                        if pd.notna(self.main_df.loc[row, 'First_Draft']):
                            batch_df = self.main_df.loc[[row]]
                        else:
                            messagebox.showinfo("Skip", "This page lacks First_Draft.")
                            return
                else:
                    # Logic for All Pages with Skip Completed option
                    if skip_completed:
                        # Filter for pages with First_Draft but without Final_Draft
                        batch_df = self.main_df[
                            (self.main_df['First_Draft'].notna()) & 
                            (self.main_df['First_Draft'] != '') & 
                            ((self.main_df['Final_Draft'].isna()) | (self.main_df['Final_Draft'] == ''))
                        ]
                    else:
                        # Process all pages with First_Draft regardless of Final_Draft status
                        batch_df = self.main_df[
                            (self.main_df['First_Draft'].notna()) & 
                            (self.main_df['First_Draft'] != '')
                        ]
            # In the ai_function method, modify the batch_df setup section:
            elif ai_job == "Get_Names_and_Places":
                if all_or_one_flag == "Current Page":
                    row = self.page_counter
                    batch_df = self.main_df.loc[[row]]
                else:
                    # First ensure the columns exist
                    if 'People' not in self.main_df.columns:
                        self.main_df['People'] = ''
                    if 'Places' not in self.main_df.columns:
                        self.main_df['Places'] = ''
                        
                    # Then do the filtering
                    batch_df = self.main_df[
                        (self.main_df['Image_Path'].notna()) &
                        (self.main_df['Image_Path'] != '')
                    ]
            elif ai_job == "Auto_Rotate":
                if all_or_one_flag == "Current Page":
                    row = self.page_counter
                    batch_df = self.main_df.loc[[row]]
                else:
                    # Process all pages that have images
                    batch_df = self.main_df[
                        (self.main_df['Image_Path'].notna()) & 
                        (self.main_df['Image_Path'] != '')
                    ]
            elif ai_job == "Chunk_Translation":
                # This is a special internal job type not directly called by users
                pass
            elif ai_job == "Identify_Errors":
                if all_or_one_flag == "Current Page":
                    row = self.page_counter
                    # Only process current page
                    batch_df = self.main_df.loc[[row]]
                else:
                    # Process all pages that have text
                    batch_df = self.main_df[self.main_df['Image_Path'].notna() & (self.main_df['Image_Path'] != '')]
            elif ai_job == "Custom":
                if all_or_one_flag == "Current Page":
                    row = self.page_counter
                    batch_df = self.main_df.loc[[row]]
                else:
                    batch_df = self.main_df[self.main_df['Image_Path'].notna() & (self.main_df['Image_Path'] != '')]
            else:
                batch_df = self.main_df[self.main_df['Image_Path'].notna() & (self.main_df['Image_Path'] != '')]

            total_rows = len(batch_df)
            
            if total_rows == 0:
                if ai_job == "HTR":
                    messagebox.showinfo("No Work Needed", "All pages already have recognized text.")
                elif ai_job == "Correct_Text":
                    messagebox.showinfo("No Work Needed", "All pages either lack Original_Text or already have corrections.")
                elif ai_job == "Translation":
                    messagebox.showinfo("No Work Needed", "All pages either lack text to translate or already have translations.")
                else:
                    messagebox.showwarning("No Images", "No images are available for processing.")
                return

            # Set up job parameters
            job_params = self.setup_job_parameters(ai_job)

            # Process in batches
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                for i in range(0, total_rows, batch_size):
                    batch_df_subset = batch_df.iloc[i:i+batch_size]

                    for index, row_data in batch_df_subset.iterrows():
                        # Get images based on the job type
                        images_data = self.get_images_for_job(ai_job, index, row_data, job_params)

                        # Set text_to_process based on the job type
                        if ai_job == "HTR":
                            text_to_process = ''
                        elif ai_job == "Correct_Text": 
                            text_to_process = row_data['Original_Text']
                        elif ai_job == "Create_Final_Draft":
                            text_to_process = row_data['First_Draft']
                        elif ai_job == "Translation":
                            text_to_process = self.find_right_text(index)
                        else:
                            if row_data['Text_Toggle'] == "Original_Text":
                                text_to_process = row_data['Original_Text']
                            elif row_data['Text_Toggle'] == "First_Draft":
                                text_to_process = row_data['First_Draft']
                            elif row_data['Text_Toggle'] == "Final_Draft":
                                text_to_process = row_data['Final_Draft']
                            else:
                                text_to_process = ''
                           
                        # Submit the API request
                        future = executor.submit(
                            asyncio.run,
                            self.process_api_request(
                                system_prompt=job_params['system_prompt'],
                                user_prompt=job_params['user_prompt'],
                                temp=job_params['temp'],
                                image_data=images_data,
                                text_to_process=text_to_process,
                                val_text=job_params['val_text'],
                                engine=job_params['engine'],
                                index=index,
                                is_base64=not "gemini" in job_params['engine'].lower(),
                                ai_job=ai_job,
                                job_params=job_params
                            )
                        )

                        futures_to_index[future] = index

                        # Process results
                    for future in as_completed(futures_to_index):
                        try:
                            response, index = future.result()
                            responses_dict[index] = response
                            
                            # Only increment progress if this index hasn't been processed before
                            if index not in processed_indices:
                                processed_indices.add(index)
                                processed_rows += 1
                                self.progress_bar.update_progress(processed_rows, total_rows)
                            
                            # Process the response if there is no error
                            if response == "Error":
                                error_count += 1
                            else:
                                if ai_job == "Auto_Rotate":
                                    self.update_image_rotation(index, response)
                                else:
                                    self.update_df_with_ai_job_response(ai_job, index, response)
                        except Exception as e:
                            error_count += 1
                            self.error_logging(f"Error processing future for index {futures_to_index[future]}: {str(e)}")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred in ai_function: {str(e)}")
            self.error_logging(f"Error in ai_function: {str(e)}")

        finally:
            # Only close the progress window if we created one (Chunk_Text is handled separately)
            if ai_job != "Chunk_Text" and 'progress_window' in locals():
                self.progress_bar.close_progress_window()
            self.load_text()
            self.counter_update()
            self.toggle_button_state()

            if error_count > 0:
                message = f"An error occurred while processing the current page." if all_or_one_flag == "Current Page" else f"Errors occurred while processing {error_count} page(s)."
                messagebox.showwarning("Processing Error", message)
    
    def setup_job_parameters(self, ai_job):
        """Set up parameters for different AI jobs"""
        self.error_logging(f"Setting up job parameters for {ai_job}")
        self.error_logging(f"Available presets: {[p['name'] for p in self.settings.function_presets]}")
        
        if ai_job == "HTR":
            preset = next((p for p in self.settings.function_presets if p['name'] == "HTR"), None)
            if preset:
                return {
                    "temp": float(preset.get('temperature', 0.7)),
                    "val_text": preset.get('val_text', ''),
                    "engine": preset.get('model', self.settings.model_list[0]),
                    "user_prompt": preset.get('specific_instructions', ''),
                    "system_prompt": preset.get('general_instructions', ''),
                    "batch_size": self.settings.batch_size,
                    "use_images": preset.get('use_images', False)
                }
            else:
                # Fallback defaults if no preset is found
                return {
                    "temp": 0.7,
                    "val_text": "",
                    "engine": self.settings.model_list[0],
                    "user_prompt": "",
                    "system_prompt": "",
                    "batch_size": self.settings.batch_size,
                    "use_images": False
                }
        elif ai_job == "Chunk_Text":
            # Get the selected chunking strategy
            selected_strategy = self.chunking_strategy_var.get()
            preset = next((p for p in self.settings.chunk_text_presets if p['name'] == selected_strategy), None)
            
            if preset:
                return {
                    "temp": float(preset.get('temperature', 0.7)),
                    "val_text": preset.get('val_text', ''),
                    "engine": preset.get('model', self.settings.model_list[0]),
                    "user_prompt": preset.get('specific_instructions', ''),
                    "system_prompt": preset.get('general_instructions', ''),
                    "batch_size": self.settings.batch_size,
                    "use_images": preset.get('use_images', False)
                }
            else:
                self.error_logging(f"Chunk text preset not found for strategy: {selected_strategy}")
                raise ValueError(f"Chunk text preset not found for strategy: {selected_strategy}")
        elif ai_job == "Metadata":
            # Use the selected metadata preset
            try:
                # Get the currently selected metadata preset name
                preset_name = self.settings.metadata_preset if hasattr(self.settings, 'metadata_preset') else "Standard Metadata"
                
                # Find the preset in the metadata_presets list
                preset = next((p for p in self.settings.metadata_presets if p['name'] == preset_name), None)
                
                if preset:
                    return {
                        "temp": float(preset.get('temperature', 0.3)),
                        "val_text": preset.get('val_text', 'Metadata:'),
                        "engine": preset.get('model', self.settings.model_list[0] if self.settings.model_list else "claude-3-5-sonnet-20241022"),
                        "user_prompt": preset.get('specific_instructions', 'Text to analyze:\n\n{text_to_process}'),
                        "system_prompt": preset.get('general_instructions', ''),
                        "batch_size": self.settings.batch_size,
                        "use_images": False,  # Metadata doesn't use images by default
                        "headers": preset.get('metadata_headers', '').split(';') if preset.get('metadata_headers', '') else []
                    }
                else:
                    # If selected preset not found, fall back to legacy settings
                    self.error_logging(f"Selected metadata preset '{preset_name}' not found, using legacy settings")
                    return {
                        "temp": float(self.settings.metadata_temp),
                        "val_text": self.settings.metadata_val_text,
                        "engine": self.settings.metadata_model,
                        "user_prompt": self.settings.metadata_user_prompt,
                        "system_prompt": self.settings.metadata_system_prompt,
                        "batch_size": self.settings.batch_size,
                        "use_images": False,  # Metadata doesn't use images by default
                        "headers": self.settings.metadata_headers.split(';') if hasattr(self.settings, 'metadata_headers') else []
                    }
            except Exception as e:
                self.error_logging(f"Error setting up metadata parameters: {str(e)}")
                # If there's an error, use sensible defaults
                return {
                    "temp": 0.3,
                    "val_text": "Metadata:",
                    "engine": self.settings.model_list[0] if self.settings.model_list else "claude-3-5-sonnet-20241022",
                    "user_prompt": "Text to analyze:\n\n{text_to_process}",
                    "system_prompt": "You analyze historical documents to extract information.",
                    "batch_size": self.settings.batch_size,
                    "use_images": False,
                    "headers": ["Document Type", "Author", "Correspondent", "Correspondent Place", "Date", "Place of Creation", "People", "Places", "Summary"]
                }
        else:
            # Existing logic for function-based AI jobs
            preset = next((p for p in self.settings.function_presets if p['name'] == ai_job), None)
            if preset:
                return {
                    "temp": float(preset.get('temperature', 0.7)),
                    "val_text": preset.get('val_text', ''),
                    "engine": preset.get('model', self.settings.model_list[0]),
                    "user_prompt": preset.get('specific_instructions', ''),
                    "system_prompt": preset.get('general_instructions', ''),
                    "batch_size": self.settings.batch_size,
                    "use_images": preset.get('use_images', True)
                }
            else:
                self.error_logging(f"Preset not found for job: {ai_job}")
                raise ValueError(f"Preset not found for job: {ai_job}")
        
    def get_images_for_job(self, ai_job, index, row_data, job_params):
        """
        Get and prepare images for AI job processing.
        
        Args:
            ai_job (str): Type of AI job being performed
            index (int): Current index in the DataFrame
            row_data (pd.Series): Current row data
            job_params (dict): Parameters for the job
            
        Returns:
            list: Prepared image data or empty list if error occurs
        """
        try:
            # First check if we need images at all
            if not job_params.get("use_images", True) or job_params.get("current_image", "Yes") != "Yes":
                return []

            # Get image path with error checking
            try:
                current_image = row_data.get('Image_Path', "")
                if not current_image:
                    self.error_logging(f"Empty image path at index {index}")
                    return []
            except Exception as e:
                self.error_logging(f"Error getting image path at index {index}: {str(e)}")
                return []

            # Convert to absolute path
            try:
                current_image = self.get_full_path(current_image)
                if not current_image:
                    self.error_logging(f"Failed to get full path for image at index {index}")
                    return []
            except Exception as e:
                self.error_logging(f"Error converting to full path at index {index}: {str(e)}")
                return []

            # Validate image path
            if not isinstance(current_image, str) or not current_image.strip():
                self.error_logging(f"Invalid image path at index {index}: {current_image}")
                return []

            # Check if file exists
            if not os.path.exists(current_image):
                self.error_logging(f"Image file not found at index {index}: {current_image}")
                return []

            # Prepare image data
            try:
                raw_images_data = [(current_image, "Document Image:")]
                return self.api_handler.prepare_image_data(
                    raw_images_data,
                    job_params.get('engine', 'default_engine'),  # Added fallback
                    not "gemini" in job_params.get('engine', '').lower()
                )
            except Exception as e:
                self.error_logging(f"Error preparing image data at index {index}: {str(e)}")
                return []

        except Exception as e:
            self.error_logging(f"Critical error in get_images_for_job at index {index}: {str(e)}")
            return []  # Return empty list as safe fallback

    def collate_names_and_places(self):
        """
        Gather unique names & places, call the LLM for normalization, and
        store the raw 'Response:' text in self.collated_names_raw and
        self.collated_places_raw. Does NOT do final replacements.
        """
        try:
            # Initialize default values
            self.collated_names_raw = ""
            self.collated_places_raw = ""
            
            # Create progress window first so user gets immediate feedback
            progress_window, progress_bar, progress_label = self.progress_bar.create_progress_window("Collating Names and Places")
            self.progress_bar.update_progress(5, 100)  # Show 5% progress immediately

            def gather_unique_items(column_name):
                """Helper function to gather unique items from a DataFrame column"""
                try:
                    all_items = []
                    if column_name in self.main_df.columns:
                        for idx, val in self.main_df[column_name].dropna().items():
                            if val.strip():
                                entries = [x.strip() for x in val.split(';') if x.strip()]
                                self.error_logging(f"Gathered {len(entries)} items from {column_name} row {idx}: {entries}", level="DEBUG")
                                all_items.extend(entries)
                    unique_items = sorted(set(all_items), key=lambda x: x.lower())
                    self.error_logging(f"Total unique {column_name}: {len(unique_items)}", level="DEBUG")
                    return unique_items
                except Exception as e:
                    self.error_logging(f"Error gathering items from {column_name}: {str(e)}")
                    return []

            # Gather unique names and places using the helper function
            self.error_logging("Starting to gather unique names", level="DEBUG")
            unique_names = gather_unique_items('People')
            self.progress_bar.update_progress(15, 100)  # Update to 15% after gathering names
            
            self.error_logging("Starting to gather unique places", level="DEBUG")
            unique_places = gather_unique_items('Places')
            self.progress_bar.update_progress(25, 100)  # Update to 25% after gathering places
            
            # Log the counts
            self.error_logging(f"Found {len(unique_names)} unique names and {len(unique_places)} unique places", level="INFO")
            if unique_names:
                self.error_logging(f"Sample names: {unique_names[:10]}", level="DEBUG")
            if unique_places:
                self.error_logging(f"Sample places: {unique_places[:10]}", level="DEBUG")

            # If there's nothing to collate, return early
            if not unique_names and not unique_places:
                self.error_logging("No names or places to collate", level="INFO")
                self.progress_bar.close_progress_window()
                return

            # Create tasks list
            tasks = []
            if unique_names:
                tasks.append(("names", unique_names))
            if unique_places:
                tasks.append(("places", unique_places))

            # System prompt
            system_message = (
                "You are given a list of historical names or places. You will assemble lists that will be used to automatically find and replace spellings to normalize the text. Each list will "
                "contain variants of the same entity spelled incorrectly or with OCR errors.\n" 
                "Ignore minor variants such as the inclusion of 'Mr' or other suffixes in names and concentrate on the core name as it would be used in a keyword search.\n"
                "For name variants where the first name/initial are different, group these together separately.\n"
                "You MUST include ALL names or places from the input list - don't skip any!\n"
                "IMPORTANT: Every single name or place from the input list MUST appear somewhere in your output.\n"
                "List all place names with multiple variants, group them together (using your judgment to combine names/places that are obvious errors or that are phonetically similar together) and pick the best spelling. Output them as:\n\n"
                "Response:\n"
                "most_complete_spelling = variant1; variant2; ...\n"
                "most_complete_spelling = variant1; variant2; ...\n"
            )
            
            self.progress_bar.update_progress(35, 100)  # Update after preparing data

            try:
                # Process using same pattern as ai_function
                results = {}
                with ThreadPoolExecutor(max_workers=1) as executor:
                    futures_to_label = {}
                    
                    # Submit both tasks
                    for i, (label, items) in enumerate(tasks):
                        self.error_logging(f"Preparing {label} task with {len(items)} items", level="DEBUG")
                        text_for_llm = "\n".join(items)
                        future = executor.submit(
                            asyncio.run,
                            self.process_api_request(
                                system_prompt=system_message,
                                user_prompt=f"Below is a list of {label}. Collate them. You MUST include ALL items in your output - every single item in the list must appear somewhere in your response. Do not skip any items even if they seem like duplicates or errors.\n\n{text_for_llm}",
                                temp=0.5,
                                image_data=[],
                                text_to_process="",
                                val_text="Response:",
                                engine="gemini-2.0-flash-thinking-exp-01-21",
                                index=0,
                                is_base64=False
                            )
                        )
                        futures_to_label[future] = label
                        self.progress_bar.update_progress(40 + i*10, 100)  # 40% after submitting first task, 50% after second
                    
                    # Calculate progress increments for API calls
                    progress_per_task = 40 / len(tasks) if tasks else 0
                    progress_base = 50  # Start from 50%
                    
                    # Process results
                    for i, future in enumerate(as_completed(futures_to_label)):
                        label = futures_to_label[future]
                        try:
                            self.error_logging(f"Processing {label} API response", level="DEBUG")
                            response, _ = future.result(timeout=60)  # Add timeout of 60 seconds
                            self.error_logging(f"Received {label} response length: {len(response)}", level="DEBUG")
                            results[label] = response
                        except Exception as e:
                            self.error_logging(f"Error processing {label}: {str(e)}")
                            results[label] = ""
                        
                        # Update progress - 50% to 90% during API calls
                        current_progress = progress_base + (i + 1) * progress_per_task
                        self.progress_bar.update_progress(min(90, current_progress), 100)

                # Store results
                self.collated_names_raw = results.get("names", "")
                self.collated_places_raw = results.get("places", "")
                
                # Log the results for debugging
                if self.collated_names_raw:
                    self.error_logging(f"Collated names sample: {self.collated_names_raw[:200]}", level="DEBUG")
                if self.collated_places_raw:
                    self.error_logging(f"Collated places sample: {self.collated_places_raw[:200]}", level="DEBUG")
                
                # Verify if all names/places are present by parsing the results
                names_dict = self.parse_collation_response(self.collated_names_raw)
                places_dict = self.parse_collation_response(self.collated_places_raw)
                
                # Count total variants in dictionaries
                name_variants_count = sum(len(variants) for variants in names_dict.values())
                place_variants_count = sum(len(variants) for variants in places_dict.values())
                
                self.error_logging(f"Parsed {len(names_dict)} name groups with {name_variants_count} total variants", level="INFO")
                self.error_logging(f"Parsed {len(places_dict)} place groups with {place_variants_count} total variants", level="INFO")
                
                # Check for missing items
                if unique_names and name_variants_count < len(unique_names) * 0.8:  # If less than 80% included
                    self.error_logging(f"Warning: Only {name_variants_count} of {len(unique_names)} names were included in the result", level="WARNING")
                
                if unique_places and place_variants_count < len(unique_places) * 0.8:  # If less than 80% included
                    self.error_logging(f"Warning: Only {place_variants_count} of {len(unique_places)} places were included in the result", level="WARNING")
                
                self.progress_bar.update_progress(95, 100)  # Almost done

            except Exception as e:
                self.error_logging(f"Error in main processing: {str(e)}")
                raise  # Re-raise to be caught by outer try-except

            finally:
                # Clean up progress bar
                try:
                    self.progress_bar.update_progress(100, 100)  # Complete the progress
                    self.progress_bar.close_progress_window()
                except Exception as e:
                    self.error_logging(f"Error closing progress window: {str(e)}")

        except Exception as e:
            self.error_logging(f"Critical error in collate_names_and_places: {str(e)}")
            messagebox.showerror("Error", 
                "An error occurred while collating names and places. Check the error log for details.")
            # Ensure defaults are set
            self.collated_names_raw = ""
            self.collated_places_raw = ""
            # Make sure progress window is closed
            if 'progress_bar' in locals() and hasattr(self, 'progress_bar'):
                try:
                    self.progress_bar.close_progress_window()
                except:
                    pass
        
        finally:
            # Final cleanup and UI update
            try:
                self.update()  # Force GUI update
            except Exception as e:
                self.error_logging(f"Error in final UI update: {str(e)}")

    def process_chunk_text(self, batch_df, all_or_one_flag, ai_job_type):
        """
        Process text chunking for the standard text fields (First_Draft or Original_Text)
        
        Args:
            batch_df: DataFrame containing rows to process
            all_or_one_flag: "Current Page" or "All Pages" flag
            ai_job_type: The AI job type to use (should be "Chunk_Text")
        """
        try:
            # Get job parameters
            job_params = self.setup_job_parameters(ai_job_type)
            batch_size = job_params.get('batch_size', 50)
            
            # Show progress window
            progress_title = f"Applying {ai_job_type} to {'Current Page' if all_or_one_flag == 'Current Page' else 'All Pages'}..."
            progress_window, progress_bar, progress_label = self.progress_bar.create_progress_window(progress_title)
            self.progress_bar.update_progress(0, 1)
            
            total_rows = len(batch_df)
            processed_rows = 0
            error_count = 0
            processed_indices = set()
            
            # Process in batches
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures_to_index = {}
                
                for index, row_data in batch_df.iterrows():
                    # Get text to process from the find_chunk_text method (use only the first element of the tuple)
                    text_to_process, _ = self.find_chunk_text(index)
                    
                    # Get images
                    images_data = self.get_images_for_job(ai_job_type, index, row_data, job_params)
                    
                    # Submit the API request
                    future = executor.submit(
                        asyncio.run,
                        self.process_api_request(
                            system_prompt=job_params['system_prompt'],
                            user_prompt=job_params['user_prompt'],
                            temp=job_params['temp'],
                            image_data=images_data,
                            text_to_process=text_to_process,
                            val_text=job_params['val_text'],
                            engine=job_params['engine'],
                            index=index,
                            is_base64=not "gemini" in job_params['engine'].lower(),
                            ai_job=ai_job_type,
                            job_params=job_params
                        )
                    )
                    
                    futures_to_index[future] = index
                
                # Process results
                for future in as_completed(futures_to_index):
                    try:
                        response, index = future.result()
                        
                        # Only increment progress if this index hasn't been processed before
                        if index not in processed_indices:
                            processed_indices.add(index)
                            processed_rows += 1
                            self.progress_bar.update_progress(processed_rows, total_rows)
                        
                        # Process the response if there is no error
                        if response == "Error":
                            error_count += 1
                        else:
                            self.update_df_with_ai_job_response(ai_job_type, index, response)
                    except Exception as e:
                        error_count += 1
                        self.error_logging(f"Error processing future for index {futures_to_index[future]}: {str(e)}")
            
            # Display error message if needed
            if error_count > 0:
                message = f"An error occurred while processing the current page." if all_or_one_flag == "Current Page" else f"Errors occurred while processing {error_count} page(s)."
                messagebox.showwarning("Processing Error", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred in process_chunk_text: {str(e)}")
            self.error_logging(f"Error in process_chunk_text: {str(e)}")
            
        finally:
            # Close progress window
            self.progress_bar.close_progress_window()
            self.load_text()
            self.counter_update()
    
    def process_translation_chunks(self, translation_df, all_or_one_flag):
        """
        Process text chunking specifically for Translation field
        
        Args:
            translation_df: DataFrame containing rows with translations to process
            all_or_one_flag: "Current Page" or "All Pages" flag
        """
        try:
            # If no translations to process, return early
            if translation_df.empty:
                return
                
            # Count actual non-empty translations
            translations_to_process = 0
            for index, row_data in translation_df.iterrows():
                text = row_data['Translation'] if pd.notna(row_data['Translation']) else ""
                if text.strip():
                    translations_to_process += 1
                    
            # If no actual translations to process, return early
            if translations_to_process == 0:
                return
                
            # Get job parameters - use the same as Chunk_Text
            job_params = self.setup_job_parameters("Chunk_Text")
            batch_size = job_params.get('batch_size', 50)
            
            # Show progress window
            progress_title = f"Applying Chunking to Translation(s)..."
            progress_window, progress_bar, progress_label = self.progress_bar.create_progress_window(progress_title)
            self.progress_bar.update_progress(0, 1)
            
            total_rows = translations_to_process
            processed_rows = 0
            error_count = 0
            processed_indices = set()
            
            # Process in batches
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures_to_index = {}
                
                for index, row_data in translation_df.iterrows():
                    # Get translation text
                    text_to_process = row_data['Translation'] if pd.notna(row_data['Translation']) else ""
                    
                    # Skip if no translation
                    if not text_to_process.strip():
                        continue
                    
                    # Get images
                    images_data = self.get_images_for_job("Chunk_Text", index, row_data, job_params)
                    
                    # Submit the API request - use Chunk_Translation as job type
                    future = executor.submit(
                        asyncio.run,
                        self.process_api_request(
                            system_prompt=job_params['system_prompt'],
                            user_prompt=job_params['user_prompt'],
                            temp=job_params['temp'],
                            image_data=images_data,
                            text_to_process=text_to_process,
                            val_text=job_params['val_text'],
                            engine=job_params['engine'],
                            index=index,
                            is_base64=not "gemini" in job_params['engine'].lower(),
                            ai_job="Chunk_Translation",
                            job_params=job_params
                        )
                    )
                    
                    futures_to_index[future] = index
                
                # Process results
                for future in as_completed(futures_to_index):
                    try:
                        response, index = future.result()
                        
                        # Only increment progress if this index hasn't been processed before
                        if index not in processed_indices:
                            processed_indices.add(index)
                            processed_rows += 1
                            self.progress_bar.update_progress(processed_rows, total_rows)
                        
                        # Process the response if there is no error
                        if response == "Error":
                            error_count += 1
                        else:
                            # Use Chunk_Translation job type for updating
                            self.update_df_with_ai_job_response("Chunk_Translation", index, response)
                    except Exception as e:
                        error_count += 1
                        self.error_logging(f"Error processing translation future for index {futures_to_index[future]}: {str(e)}")
            
            # Display error message if needed
            if error_count > 0:
                message = f"An error occurred while processing translation." if all_or_one_flag == "Current Page" else f"Errors occurred while processing {error_count} translation(s)."
                messagebox.showwarning("Processing Error", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred in process_translation_chunks: {str(e)}")
            self.error_logging(f"Error in process_translation_chunks: {str(e)}")
            
        finally:
            # Only close progress window if we created one
            if 'progress_window' in locals():
                self.progress_bar.close_progress_window()
            self.load_text()
            self.counter_update()

    def run_collation_and_open_window(self):
        """
        First collects names and places from the LLM, then shows the GUI for user editing.
        """
        # 1) Collect suggestions from the LLM automatically
        self.collate_names_and_places()

        # 2) Now show the user a GUI with the raw lines
        self.create_collate_names_places_window()

    def refresh_display(self):
        """Refresh the current image and text display with proper path handling"""
        if not self.main_df.empty:
            # Ensure page_counter is within valid bounds
            self.page_counter = min(self.page_counter, len(self.main_df) - 1)
            self.page_counter = max(0, self.page_counter)

            try:
                # Get image path
                image_path = self.main_df.iloc[self.page_counter]['Image_Path']
                
                # Convert to absolute path if necessary
                if not os.path.isabs(image_path):
                    image_path = os.path.join(self.project_directory, image_path)
                
                # Verify file exists
                if os.path.exists(image_path):
                    self.current_image_path = image_path
                    self.image_handler.load_image(self.current_image_path)
                    self.load_text()
                else:
                    messagebox.showerror("Error", f"Image file not found: {image_path}")
                    
                self.counter_update()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to refresh display: {str(e)}")
                self.error_logging(f"Refresh display error: {str(e)}")
        else:
            self.error_logging("No images to display", level="INFO")
            # Clear the image display
            self.image_display.delete("all")
            # Clear the text display
            self.text_display.delete("1.0", tk.END)
            self.counter_update()

    def update_highlight_menu_states(self):
        """Enable or disable highlight menu items based on data availability"""
        if self.main_df.empty or self.page_counter < 0 or self.page_counter >= len(self.main_df):
            # Disable all highlight options if no data is loaded
            self.document_menu.entryconfig("Highlight Names", state="disabled")
            self.document_menu.entryconfig("Highlight Places", state="disabled")
            self.document_menu.entryconfig("Highlight Changes", state="disabled")
            self.document_menu.entryconfig("Highlight Errors", state="disabled")
            return
            
        # Get current page data
        index = self.page_counter
        current_toggle = self.main_df.loc[index, 'Text_Toggle']
        
        # Check for names data
        has_names = False
        if 'People' in self.main_df.columns:
            names = self.main_df.loc[index, 'People']
            has_names = pd.notna(names) and names.strip() != ""
        self.document_menu.entryconfig("Highlight Names", state="normal" if has_names else "disabled")
        
        # Check for places data
        has_places = False
        if 'Places' in self.main_df.columns:
            places = self.main_df.loc[index, 'Places']
            has_places = pd.notna(places) and places.strip() != ""
        self.document_menu.entryconfig("Highlight Places", state="normal" if has_places else "disabled")
        
        # Check for changes - needs at least two text versions
        has_changes = False
        if current_toggle == "First_Draft":
            original_text = self.main_df.loc[index, 'Original_Text'] if 'Original_Text' in self.main_df.columns else ""
            first_draft = self.main_df.loc[index, 'First_Draft'] if 'First_Draft' in self.main_df.columns else ""
            has_changes = (pd.notna(original_text) and original_text.strip() != "" and 
                          pd.notna(first_draft) and first_draft.strip() != "")
        elif current_toggle == "Final_Draft":
            first_draft = self.main_df.loc[index, 'First_Draft'] if 'First_Draft' in self.main_df.columns else ""
            final_draft = self.main_df.loc[index, 'Final_Draft'] if 'Final_Draft' in self.main_df.columns else ""
            has_changes = (pd.notna(first_draft) and first_draft.strip() != "" and 
                          pd.notna(final_draft) and final_draft.strip() != "")
            if not has_changes:
                # Try with Original_Text if First_Draft is empty
                original_text = self.main_df.loc[index, 'Original_Text'] if 'Original_Text' in self.main_df.columns else ""
                has_changes = (pd.notna(original_text) and original_text.strip() != "" and 
                              pd.notna(final_draft) and final_draft.strip() != "")
        self.document_menu.entryconfig("Highlight Changes", state="normal" if has_changes else "disabled")
        
        # Check for errors data
        has_errors = False
        if 'Errors' in self.main_df.columns:
            errors = self.main_df.loc[index, 'Errors']
            has_errors = pd.notna(errors) and errors.strip() != ""
        self.document_menu.entryconfig("Highlight Errors", state="normal" if has_errors else "disabled")

    def extract_metadata_from_response(self, index, response):
        """
        Extract metadata from an AI response and update the DataFrame columns.
        
        Args:
            index (int): The index in the DataFrame to update
            response (str): The API response text
            
        Returns:
            bool: True if metadata was successfully processed
        """
        try:
            # Check if response is None or empty
            if not response:
                self.error_logging(f"Empty metadata response for index {index}")
                return False
                
            # Log the entire response for debugging
            self.error_logging(f"Raw metadata response for index {index}:\n{response}")
            
            # Get metadata parameters
            job_params = self.setup_job_parameters("Metadata")
            val_text = job_params.get('val_text', "Metadata:")
            headers = job_params.get('headers', [])
            
            # First, ensure all required metadata columns exist in the DataFrame
            # Map from header names to column names (convert spaces to underscores)
            header_to_column = {}
            for header in headers:
                header = header.strip()
                if not header:
                    continue
                # Convert header to a valid column name
                column_name = header.replace(" ", "_")
                header_to_column[header] = column_name
                # Add column if it doesn't exist
                if column_name not in self.main_df.columns:
                    self.main_df[column_name] = ""
                    self.error_logging(f"Added new metadata column: {column_name}")
                    
            # Try to find metadata even if the specific marker is not present
            metadata_text = ""
            
            # First try with the expected marker
            if val_text in response:
                metadata_text = response.split(val_text, 1)[1].strip()
                self.error_logging(f"Found metadata marker '{val_text}' in response")
            # Try alternate markers if the main one isn't found
            elif "Metadata:" in response:
                metadata_text = response.split("Metadata:", 1)[1].strip()
                self.error_logging("Using alternate 'Metadata:' marker")
            # If no markers found, try to use the whole response if it looks like metadata
            elif ":" in response and len(headers) > 0 and any(header in response for header in headers):
                metadata_text = response.strip()
                self.error_logging("No marker found, using full response as it contains metadata fields")
            else:
                self.error_logging(f"No recognizable metadata format in response for index {index}")
                print(f"ERROR: No recognizable metadata format in response for index {index}")
                return False
                
            # Parse the metadata
            lines = metadata_text.split('\n')
            current_field = None
            metadata = {}
            field_values = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this line starts a new field
                if ":" in line:
                    parts = line.split(":", 1)
                    field_name = parts[0].strip()
                    value = parts[1].strip() if len(parts) > 1 else ""
                    
                    # Store field and value
                    field_values[field_name] = value
                    
                    # Start collecting multi-line fields
                    if field_name == "Summary":
                        current_field = 'Summary'
                        metadata[current_field] = value
                    else:
                        current_field = None
                elif current_field == 'Summary':
                    # Append to the existing summary
                    metadata[current_field] += " " + line
            
            # Update DataFrame
            fields_updated = 0
            
            # First update any fields from the metadata response
            for field_name, value in field_values.items():
                # Skip if empty
                if not value.strip():
                    continue
                
                # Find matching column name
                column_name = None
                
                # First try direct match with header
                if field_name in header_to_column:
                    column_name = header_to_column[field_name]
                
                # Try alternate mappings for backward compatibility
                if column_name is None:
                    alt_mappings = {
                        "Document Type": "Document_Type",
                        "Author": "Author",
                        "Correspondent": "Correspondent",
                        "Correspondent Place": "Correspondent_Place",
                        "Date": "Date",
                        "Place of Creation": "Creation_Place",
                        "People": "People",
                        "Places": "Places",
                        "Summary": "Summary"
                    }
                    if field_name in alt_mappings:
                        column_name = alt_mappings[field_name]
                
                # Update the column if we found a match
                if column_name and column_name in self.main_df.columns:
                    # Only update if the column is empty or this is a new value
                    if not pd.notna(self.main_df.at[index, column_name]) or not self.main_df.at[index, column_name].strip():
                        self.main_df.at[index, column_name] = value
                        fields_updated += 1
                        self.error_logging(f"Updated {column_name} with value: {value}")
            
            # Preserve existing People and Places if they exist and weren't updated
            for special_field in ["People", "Places"]:
                if special_field in self.main_df.columns:
                    # If the field wasn't updated but has existing value, preserve it
                    existing_value = self.main_df.at[index, special_field]
                    if pd.notna(existing_value) and existing_value.strip() and special_field not in field_values:
                        self.error_logging(f"Preserved existing {special_field}: {existing_value}")
                        fields_updated += 1  # Count as updated for success check
            
            # Check if we actually updated any fields
            if fields_updated > 0:
                self.error_logging(f"Successfully processed {fields_updated} metadata fields for index {index}")
                return True
            else:
                self.error_logging(f"No fields were updated for index {index}")
                # Print to console as well for immediate visibility
                print(f"ERROR: No fields were updated for index {index}. Parsed metadata text:\n{metadata_text}")
                return False
            
        except Exception as e:
            self.error_logging(f"Error extracting metadata for index {index}: {str(e)}")
            print(f"ERROR: Exception extracting metadata for index {index}: {str(e)}")
            return False

    def apply_document_separation(self):
        """Apply document separation based on ***** markers and replace main_df with the compiled documents."""
        from util.apply_separation_options import apply_document_separation
        apply_document_separation(self)

    def apply_document_separation_with_boxes(self):
        """Apply document separation based on ***** markers and replace main_df with the compiled documents,
        while also creating cropped images for each section."""
        from util.apply_separation_options import apply_document_separation_with_boxes
        apply_document_separation_with_boxes(self)
        
    def open_document_separation_options(self):
        """Opens a window with document separation options."""
        from util.apply_separation_options import create_separation_options_window
        create_separation_options_window(self)
        
    def update_separation_menu_state(self, state="normal"):
        """Update the state of the document separation menu items."""
        self.process_menu.entryconfig("Apply Separation", state=state)

if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        # Log the error
        print(f"Critical error in main loop: {str(e)}")
        # Try to write to error log if possible
        try:
            with open("util/error_logs.txt", "a") as f:
                f.write(f"{datetime.now()}: CRITICAL: {str(e)}\n{traceback.format_exc()}\n")
        except:
            pass
        # Try to show error message
        try:
            messagebox.showerror("Critical Error", 
                f"The application encountered a critical error and needs to close:\n{str(e)}")
        except:
            pass
        # Ensure app closes
        try:
            app.destroy()
        except:
            pass