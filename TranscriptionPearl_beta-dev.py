import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import pandas as pd
import fitz, re, os, shutil, asyncio, difflib, ast
from PIL import Image, ImageTk, ImageOps
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# # Import Local Scripts
from util.subs.ImageSplitter import ImageSplitter
from util.FindReplace import FindReplace
from util.APIHandler import APIHandler
from util.ProgressBar import ProgressBar
from util.SettingsWindow import SettingsWindow
from util.Settings import Settings
from util.AnalyzeDocuments import AnalyzeDocuments
from util.ImageHandler import ImageHandler

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
            values=["None", "Original_Text", "First Draft", "Final Draft"],
            width=15,
            state="readonly"
        )
        self.text_display_dropdown.pack(side="left", padx=2)
        self.text_display_dropdown.bind('<<ComboboxSelected>>', self.on_text_display_change)
        
        # --- New: Chunking Strategy Dropdown in Middle Group ---
        self.chunking_strategy_var = tk.StringVar()
        # For now, initialize with an empty list; it will be updated after self.settings is set.
        self.chunking_dropdown = ttk.Combobox(middle_group, textvariable=self.chunking_strategy_var,
                                            values=[], state="readonly", width=30)
        # Add a label for clarity.
        chunking_label = tk.Label(middle_group, text="Document Type:")
        chunking_label.pack(side="left", padx=5)
        self.chunking_dropdown.pack(side="left", padx=5)
        
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

        self.enable_drag_and_drop() 
        self.create_menus()
        self.create_key_bindings()
        self.bind_key_universal_commands(self.text_display)
        
        # Initialize settings now (after the top frame is created)
        self.settings = Settings()
        
        # --- Update Chunking Dropdown with Actual Presets ---
        preset_names = [p['name'] for p in self.settings.chunk_text_presets] if self.settings.chunk_text_presets else []
        self.chunking_dropdown['values'] = preset_names
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
            self.settings.google_api_key
        )
        
        # Initialize the Progress Bar
        self.progress_bar = ProgressBar(self)

# GUI Setup

    def create_menus(self):
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)
        
        # File Menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        
        self.file_menu.add_command(label="New Project", command=self.create_new_project)
        self.file_menu.add_command(label="Open Project", command=self.open_project)
        self.file_menu.add_command(label="Save Project As...", command=self.save_project_as)
        self.file_menu.add_command(label="Save Project", command=self.save_project)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Import Images Only", command=lambda: self.open_folder(toggle="Images without Text"))        
        self.file_menu.add_command(label="Import Text and Images", command=lambda: self.open_folder(toggle="Images with Text"))        
        self.file_menu.add_command(label="Import PDF", command=self.open_pdf)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Export as Single Txt File", command=self.export_single_file)
        self.file_menu.add_command(label="Export as Multiple Txt Files", command=self.export_text_files)
        self.file_menu.add_command(label="Export as PDF with Text", command=self.export_as_pdf)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Settings", command=self.create_settings_window)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.quit)

        # Edit Menu

        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        
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

        self.process_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Process", menu=self.process_menu)

        self.process_menu.add_command(label="Recognize Text on Current Page", command=lambda: self.ai_function(all_or_one_flag="Current Page", ai_job="HTR"))        
        self.process_menu.add_command(label="Recognize Text on All Pages", command=lambda: self.ai_function(all_or_one_flag="All Pages", ai_job="HTR"))
        self.process_menu.add_separator()
        self.process_menu.add_command(label="Correct Text on Current Page", command=lambda: self.ai_function(all_or_one_flag="Current Page", ai_job="Correct_Text"))
        self.process_menu.add_command(label="Correct Text on All Pages", command=lambda: self.ai_function(all_or_one_flag="All Pages", ai_job="Correct_Text"))
        self.process_menu.add_separator()
        self.process_menu.add_command(label="Run Custom Function on Current Page", command=lambda: self.open_custom_function_window("Current Page"))
        self.process_menu.add_command(label="Run Custom Function on All Pages", command=lambda: self.open_custom_function_window("All Pages"))
        self.process_menu.add_separator()
        self.process_menu.add_command(label="Get Names and Places on Current Page", command=lambda: self.ai_function(all_or_one_flag="Current Page", ai_job="Get_Names_and_Places"))
        self.process_menu.add_command(label="Get Names and Places on All Pages", command=lambda: self.ai_function(all_or_one_flag="All Pages", ai_job="Get_Names_and_Places"))
        self.process_menu.add_separator()
        self.process_menu.add_command(
            label="Collate Names & Places",
            command=self.run_collation_and_open_window  # <-- new function
        )
        self.process_menu.add_separator()
        self.process_menu.add_command(label="Separate Documents on Current Page", 
                                    command=lambda: self.ai_function(all_or_one_flag="Current Page", 
                                                                ai_job="Chunk_Text"))
        self.process_menu.add_command(label="Separate Documents on All Pages", 
                                    command=lambda: self.ai_function(all_or_one_flag="All Pages", 
                                                                ai_job="Chunk_Text"))
        self.process_menu.add_separator()
        self.process_menu.add_command(label="Find Errors on Current Page", 
                                    command=lambda: self.ai_function(all_or_one_flag="Current Page", 
                                                                ai_job="Identify_Errors"))
        self.process_menu.add_command(label="Find Errors on All Pages", 
                                    command=lambda: self.ai_function(all_or_one_flag="All Pages", 
                                                                ai_job="Identify_Errors"))
        
        # Document Menu

        self.document_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Document", menu=self.document_menu)
        self.document_menu.add_command(label="Remove Pagination", 
                            command=self.remove_pagination,
                            state="disabled")  # Initially disabled

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

        self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Tools", menu=self.tools_menu)

        self.tools_menu.add_command(label="Edit Current Image", command=self.edit_single_image)
        self.tools_menu.add_command(label="Edit All Images", command=self.edit_all_images)

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

        # Image management bindings
        self.bind("<Control-d>", lambda event: self.delete_current_image())  # Added parentheses for method call
        self.bind("<Control-i>", lambda event: self.edit_single_image())  # Added parentheses for method call
        self.bind("<Control-Shift-i>", lambda event: self.edit_all_images())  # Added parentheses for method call

        # AI function bindings
        self.bind("<Control-1>", lambda event: self.ai_function(all_or_one_flag="Current Page", ai_job="HTR"))
        self.bind("<Control-Shift-1>", lambda event: self.ai_function(all_or_one_flag="All Pages", ai_job="HTR"))
        self.bind("<Control-2>", lambda event: self.ai_function(all_or_one_flag="Current Page", ai_job="Correct_Text"))
        self.bind("<Control-Shift-2>", lambda event: self.ai_function(all_or_one_flag="All Pages", ai_job="Correct_Text"))

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
            "Image_Path", 
            "Text_Path", 
            "Text_Toggle",
            # Names and Places columns
            "People",
            "Places",
            # Additional metadata columns that might be useful
            "Document_No",
            "Document_Type",
            "Creation_Date",
            "Author",
            "Correspondent",
            "Creation_Place",
            "Summary",
            "Notes",
            # Error tracking
            "Errors"
        ])
        
        # Initialize all text columns as empty strings instead of NaN
        text_columns = [
            "Original_Text", "First_Draft", "Final_Draft",
            "People", "Places", "Document_Type", "Author",
            "Correspondent", "Creation_Place", "Summary", "Notes",
            "Errors"  # Add Errors to text columns
        ]
        for col in text_columns:
            self.main_df[col] = ""
        
        # Initialize numeric columns
        self.main_df["Index"] = pd.Series(dtype=int)
        self.main_df["Document_No"] = pd.Series(dtype=int)
        
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
                
            # Convert to absolute path if necessary
            if not os.path.isabs(image_path):
                image_path = os.path.join(self.project_directory, image_path)
                
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
        print(f"find_replace_navigate called with direction {direction}")
        if hasattr(self, 'find_replace') and hasattr(self.find_replace, 'link_nav'):
            print(f"Setting page_counter to {self.find_replace.link_nav}")
            
            # Set the page counter
            self.page_counter = self.find_replace.link_nav
            
            try:
                # Get image path with safety checks
                image_path = self.main_df.iloc[self.page_counter]['Image_Path']
                if pd.isna(image_path):
                    messagebox.showerror("Error", "Invalid image path in database")
                    return
                    
                # Convert to absolute path if necessary
                if not os.path.isabs(image_path):
                    image_path = os.path.join(self.project_directory, image_path)
                    
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
                print(f"Error processing file {source_path}: {e}")
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
            print("No images were successfully processed")
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

# Project Save and Open Functions

    def create_new_project(self):
        if not messagebox.askyesno("New Project", "Creating a new project will reset the current application state. This action cannot be undone. Are you sure you want to proceed?"):
            return  # User chose not to proceed
        
        # Reset the application
        self.reset_application()

        # Enable drag and drop
        self.enable_drag_and_drop()

    def save_project(self):
        # If no project directory exists, call save_project_as.
        if not hasattr(self, 'project_directory') or not self.project_directory:
            self.save_project_as()
            return

        try:
            project_name = os.path.basename(self.project_directory)
            project_file = os.path.join(self.project_directory, f"{project_name}.pbf")

            # Save the updated DataFrame back to the project file.
            self.main_df.to_csv(project_file, index=False, encoding='utf-8')

            messagebox.showinfo("Success", f"Project saved successfully to {self.project_directory}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project: {e}")
            self.error_logging(f"Failed to save project: {e}")

    def open_project(self):
        project_directory = filedialog.askdirectory(title="Select Project Directory")
        if not project_directory:
            return

        project_name = os.path.basename(project_directory)
        project_file = os.path.join(project_directory, f"{project_name}.pbf")
        images_directory = os.path.join(project_directory, "images")

        if not os.path.exists(project_file) or not os.path.exists(images_directory):
            messagebox.showerror("Error", "Invalid project directory. Missing project file or images directory.")
            return

        try:
            # Read and process the project CSV file, update paths, etc.
            self.main_df = pd.read_csv(project_file, encoding='utf-8')
            # Ensure required text columns exist...
            for col in ["Original_Text", "First_Draft", "Final_Draft", "Text_Toggle"]:
                if col not in self.main_df.columns:
                    self.main_df[col] = ""
                else:
                    self.main_df[col] = self.main_df[col].astype('object')

            self.project_directory = project_directory
            self.images_directory = images_directory

            # Convert relative paths to absolute paths
            self.main_df['Image_Path'] = self.main_df['Image_Path'].apply(
                lambda x: os.path.join(self.project_directory, x) if pd.notna(x) else x)
            self.main_df['Text_Path'] = self.main_df['Text_Path'].apply(
                lambda x: os.path.join(self.project_directory, x) if pd.notna(x) else x)

            # Reset page counter and load the first image and text.
            self.page_counter = 0
            if not self.main_df.empty:
                self.current_image_path = self.main_df.loc[0, 'Image_Path']
                self.image_handler.load_image(self.current_image_path)
                self.load_text()
            self.counter_update()

            messagebox.showinfo("Success", "Project loaded successfully.")
            
            self.get_doc_type_with_ai()

            # Trigger document classification upon project load
            self.get_doc_type_with_ai()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open project: {e}")
            self.error_logging("Failed to open project", str(e))
    
    def save_project_as(self):
        # Ask the user to select a parent directory and project name.
        parent_directory = filedialog.askdirectory(title="Select Directory for New Project")
        if not parent_directory:
            return  # User cancelled
        project_name = simpledialog.askstring("Project Name", "Enter a name for the new project:")
        if not project_name:
            return  # User cancelled or provided an empty name

        # Create the project directory and images subfolder.
        project_directory = os.path.join(parent_directory, project_name)
        os.makedirs(project_directory, exist_ok=True)
        images_directory = os.path.join(project_directory, "images")
        os.makedirs(images_directory, exist_ok=True)

        # Path for the project file (CSV).
        project_file = os.path.join(project_directory, f"{project_name}.pbf")

        # Iterate over each row in the DataFrame.
        for index, row in self.main_df.iterrows():
            new_image_filename = f"{index+1:04d}_p{index+1:03d}.jpg"
            new_image_path = os.path.join(images_directory, new_image_filename)
            self.resize_image(row['Image_Path'], new_image_path)
            
            # Do not create a text file; store text in the DataFrame.
            new_text_path = ""  # No text file is created
            
            rel_image_path = os.path.relpath(new_image_path, project_directory)
            rel_text_path = ""  # No text file path

            self.main_df.at[index, 'Image_Path'] = rel_image_path
            self.main_df.at[index, 'Text_Path'] = rel_text_path

        # Save the DataFrame (project file) in the project directory.
        self.main_df.to_csv(project_file, index=False, encoding='utf-8')

        messagebox.showinfo("Success", f"Project saved successfully to {project_directory}")
        
        # Update the project directory references.
        self.project_directory = project_directory
        self.images_directory = images_directory

    def open_pdf(self, pdf_file=None):
        if pdf_file is None:
            pdf_file = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not pdf_file:
            return

        # Show progress bar immediately
        progress_window, progress_bar, progress_label = self.progress_bar.create_progress_window("Processing PDF")
        self.progress_bar.update_progress(0, 1)  # Show 0% progress immediately

        try:
            pdf_document = fitz.open(pdf_file)
            total_pages = len(pdf_document)

            # Get the starting index for new entries
            start_index = len(self.main_df)

            # Update progress bar with actual total
            self.progress_bar.update_progress(0, total_pages)

            for page_num in range(total_pages):
                self.progress_bar.update_progress(page_num + 1, total_pages)
            
                page = pdf_document[page_num]

                # Extract image at a lower resolution
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                temp_image_path = os.path.join(self.temp_directory, f"temp_page_{page_num + 1}.jpg")
                pix.save(temp_image_path)

                # Calculate new index and page number
                new_index = start_index + page_num
                new_page_num = new_index + 1

                # Resize and save the image using the existing resize_image method
                image_filename = f"{new_page_num:04d}_p{new_page_num:03d}.jpg"
                image_path = os.path.join(self.images_directory, image_filename)
                self.resize_image(temp_image_path, image_path)

                # Remove the temporary image
                os.remove(temp_image_path)

                # Extract text
                text_content = page.get_text()
                text_path = ""

                # Add to DataFrame
                new_row = pd.DataFrame({
                    "Index": [new_index],
                    "Page": [f"{new_page_num:04d}_p{new_page_num:03d}"],
                    "Original_Text": [text_content],
                    "First_Draft": [""],
                    "Final_Draft": [""],
                    "Image_Path": [image_path],
                    "Text_Path": [text_path],
                    "Text_Toggle": ["Original_Text"]
                })
                self.main_df = pd.concat([self.main_df, new_row], ignore_index=True)

            pdf_document.close()
            self.refresh_display()
            self.progress_bar.close_progress_window()
            self.get_doc_type_with_ai()
            messagebox.showinfo("Success", f"PDF processed successfully. {total_pages} pages added.")

        except Exception as e:
            self.progress_bar.close_progress_window()
            messagebox.showerror("Error", f"An error occurred while processing the PDF: {str(e)}")
            self.error_logging(f"Error in open_pdf: {str(e)}")

        finally:
            self.enable_drag_and_drop()

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

        self.get_doc_type_with_ai()
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
            
            self.get_doc_type_with_ai()
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
            "First_Draft": "First Draft",
            "Final_Draft": "Final Draft"
        }
        self.text_display_var.set(display_map.get(current_toggle, "None"))

        # Based on the toggle, select the text to display.
        if self.text_display_var.get() == "None":
            text = ""
        elif self.text_display_var.get() == "Original_Text":
            text = self.main_df.loc[index, 'Original_Text'] if pd.notna(self.main_df.loc[index, 'Original_Text']) else ""
        elif self.text_display_var.get() == "First Draft":
            text = self.main_df.loc[index, 'First_Draft'] if pd.notna(self.main_df.loc[index, 'First_Draft']) else ""
        elif self.text_display_var.get() == "Final Draft":
            text = self.main_df.loc[index, 'Final_Draft'] if pd.notna(self.main_df.loc[index, 'Final_Draft']) else ""
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
            available_options.append("First Draft")
        if pd.notna(self.main_df.loc[index, 'Final_Draft']) and self.main_df.loc[index, 'Final_Draft'].strip():
            available_options.append("Final Draft")
        self.text_display_dropdown['values'] = available_options

        if self.find_replace.find_replace_toggle:
            self.find_replace.highlight_text()

        self.highlight_text()
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

        if pd.notna(final_draft) and self.main_df.loc[index_no, 'Text_Toggle'] == "Final_Draft":
            text = final_draft
        elif pd.notna(first_draft) and self.main_df.loc[index_no, 'Text_Toggle'] == "First_Draft":
            text = first_draft
        elif pd.notna(original_text):
            text = original_text
        else:
            text = ""

        return text
        
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

    def error_logging(self, error_message, additional_info=None):
        try:
            error_logs_path = "util/error_logs.txt"
            with open(error_logs_path, "a", encoding='utf-8') as file:
                # Add stack trace
                import traceback
                stack = traceback.format_exc()
                
                log_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {error_message}"
                if additional_info:
                    log_message += f" - Additional Info: {additional_info}"
                if stack:
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
                        print(f"Error converting PNG file {file_path}: {e}")
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
            
            # If new images added are at least 50% of the previous count, run document classification
            if prev_count > 0 and len(valid_images) >= 0.5 * prev_count:
                self.get_doc_type_with_ai()
            elif prev_count == 0:  # If this is the first batch of images
                self.get_doc_type_with_ai()

            # Clean up any temporary converted files
            for image_path in valid_images:
                if image_path.endswith('_converted.jpg'):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        print(f"Error removing temporary file {image_path}: {e}")

        # Process PDF files
        if pdf_files:
            for pdf_file in pdf_files:
                try:
                    self.open_pdf(pdf_file)
                except Exception as e:
                    print(f"Error processing PDF file {pdf_file}: {e}")
                    messagebox.showerror("Error", f"Failed to process PDF file {pdf_file}: {e}")
        
        # Report invalid files
        if invalid_files:
            invalid_files_str = "\n".join(invalid_files)
            print(f"Invalid files: {invalid_files_str}")
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

    def parse_collation_response(self, response_text):
        """
        Parse lines like:
        Response:
        correct_spelling = variant1; variant2...
        ...
        Return a dict: { correct_spelling: [variant1, variant2...] }
        """
        coll_dict = {}
        lines = response_text.splitlines()
        for ln in lines:
            ln = ln.strip()
            if ln.lower().startswith("response:"):
                # skip "Response:" lines
                continue
            if '=' in ln:
                parts = ln.split('=', 1)
                correct = parts[0].strip()
                variations = parts[1].split(';')
                variations = [v.strip() for v in variations if v.strip()]
                if correct:
                    coll_dict[correct] = variations
        return coll_dict

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
        try:
            # Cleanup code
            self.destroy()
        except Exception as e:
            print(f"Error closing application: {str(e)}")
            self.destroy()

    def error_logging(self, error_message, additional_info=None):
        try:
            error_logs_path = "util/error_logs.txt"
            with open(error_logs_path, "a", encoding='utf-8') as file:
                # Add stack trace
                import traceback
                stack = traceback.format_exc()
                
                log_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {error_message}"
                if additional_info:
                    log_message += f" - Additional Info: {additional_info}"
                if stack:
                    log_message += f"\nStack trace:\n{stack}"
                file.write(log_message + "\n")
        except Exception as e:
            print(f"Error logging failed: {e}")

# GUI Actions / Toggles

    def open_custom_function_window(self, scope):
        # Create a modal window for selecting a function
        window = tk.Toplevel(self)
        window.title("Select Custom Function")
        window.grab_set()  # make window modal

        tk.Label(window, text="Select a custom function to run:").pack(padx=10, pady=10)
        
        # Get the default function names from your settings;
        # here we assume they are stored in self.settings.function_presets
        preset_names = [p['name'] for p in self.settings.function_presets] if self.settings.function_presets else []
        selected_function = tk.StringVar(value=preset_names[0] if preset_names else "")
        
        combobox = ttk.Combobox(window, textvariable=selected_function, values=preset_names, state="readonly", width=30)
        combobox.pack(padx=10, pady=5)
        
        def confirm_selection():
            self.custom_function_selected = selected_function.get()
            window.destroy()
            # Now call your AI function using the selected preset name.
            self.ai_function(all_or_one_flag=scope, ai_job="Custom")
        
        tk.Button(window, text="OK", command=confirm_selection).pack(pady=10)

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
            
        selected = self.text_display_var.get()
        index = self.page_counter
        
        # Map display names to DataFrame values
        display_map = {
            "None": "None",
            "Original_Text": "Original_Text",
            "First Draft": "First_Draft",
            "Final Draft": "Final_Draft"
        }
        
        # Update the Text_Toggle in the DataFrame
        self.main_df.at[index, 'Text_Toggle'] = display_map[selected]
        
        # Reload the text
        self.load_text()
  
    def toggle_text(self):
        if self.main_df.empty:
            return

        index = self.page_counter
        current_toggle = self.main_df.loc[index, 'Text_Toggle']
        has_corrected = pd.notna(self.main_df.loc[index, 'First_Draft'])
        has_second = pd.notna(self.main_df.loc[index, 'Final_Draft'])

        if current_toggle == "Original_Text":
            if has_corrected:
                self.main_df.loc[index, 'Text_Toggle'] = "First_Draft"
            elif has_second:
                self.main_df.loc[index, 'Text_Toggle'] = "Final_Draft"
        elif current_toggle == "First_Draft":
            if has_second:
                self.main_df.loc[index, 'Text_Toggle'] = "Final_Draft"
            else:
                self.main_df.loc[index, 'Text_Toggle'] = "Original_Text"
        elif current_toggle == "Final_Draft":
            self.main_df.loc[index, 'Text_Toggle'] = "Original_Text"

        self.load_text()
    
# Highlighting Functions

    def toggle_highlight_options(self):
        if self.highlight_changes_var.get():
            self.highlight_names_var.set(False)
            self.highlight_places_var.set(False)
            self.highlight_errors_var.set(False)
        elif self.highlight_names_var.get() or self.highlight_places_var.get() or self.highlight_errors_var.get():
            self.highlight_changes_var.set(False)
        
        self.highlight_text()

    def highlight_names_or_places(self):
        """Highlight names and/or places in the text based on DataFrame data"""
        # Clear existing highlights first
        self.text_display.tag_remove("name_highlight", "1.0", tk.END)
        self.text_display.tag_remove("place_highlight", "1.0", tk.END)
        
        # If neither highlighting option is selected, return early
        if not self.highlight_names_var.get() and not self.highlight_places_var.get():
            return
        
        # Configure the highlight tags
        self.text_display.tag_config("name_highlight", background="lightblue")
        self.text_display.tag_config("place_highlight", background="wheat1")
        
        # Get current page index
        current_index = self.page_counter
        
        try:
            # Check if we have names or places data in the main DataFrame
            if 'People' not in self.main_df.columns or 'Places' not in self.main_df.columns:
                return
                
            def process_entities(entities_str, tag):
                if pd.notna(entities_str) and entities_str:
                    entities = [entity.strip() for entity in entities_str.split(';')]
                    for entity in entities:
                        # Skip entries with square brackets
                        if '[' in entity or ']' in entity:
                            continue
                        
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
                                    self.text_display.tag_add(tag, start_index, f"{start_line}.end")
                                    self.text_display.tag_add(tag, f"{end_line}.0", end_index)
                        
                        # Also highlight individual words for names (except very short ones and common words)
                        if tag == "name_highlight":  # Only for names, not places
                            parts = entity.split()
                            for part in parts:
                                if len(part) > 2 and part.lower() not in ['the', 'and', 'of', 'in', 'on', 'at', 'la', 'le', 'les', 'de', 'du', 'des']:
                                    self.highlight_term(part, tag, exact_match=False)
            
            # Process names if the highlight names option is checked
            if self.highlight_names_var.get():
                names = self.main_df.loc[current_index, 'People']
                if pd.notna(names):
                    process_entities(names, "name_highlight")
            
            # Process places if the highlight places option is checked
            if self.highlight_places_var.get():
                places = self.main_df.loc[current_index, 'Places']
                if pd.notna(places):
                    process_entities(places, "place_highlight")
        
        except Exception as e:
            print(f"Error in highlight_names_or_places: {str(e)}")
            self.error_logging(f"Error in highlight_names_or_places: {str(e)}")

    def highlight_term(self, term, tag, exact_match=False):
        """Helper function to highlight a specific term in the text"""
        text_widget = self.text_display
        start_index = "1.0"
        
        # Escape special regex characters
        escaped_term = re.escape(term)
        
        while True:
            try:
                if exact_match:
                    # For exact matches (like place names), don't use word boundaries
                    start_index = text_widget.search(escaped_term, start_index, tk.END, 
                                                regexp=True, nocase=True)
                else:
                    # For individual words, use word boundaries
                    start_index = text_widget.search(r'\y' + escaped_term + r'\y', 
                                                start_index, tk.END, 
                                                regexp=True, nocase=True)
                
                if not start_index:
                    break
                    
                end_index = f"{start_index}+{len(term)}c"
                text_widget.tag_add(tag, start_index, end_index)
                start_index = end_index
                
            except Exception as e:
                print(f"Error highlighting term '{term}': {str(e)}")
                break

    def highlight_text(self):
        # Clear all existing highlights
        self.text_display.tag_remove("name_highlight", "1.0", tk.END)
        self.text_display.tag_remove("place_highlight", "1.0", tk.END)
        self.text_display.tag_remove("change_highlight", "1.0", tk.END)
        self.text_display.tag_remove("error_highlight", "1.0", tk.END)

        if self.highlight_changes_var.get():
            self.highlight_changes()
        else:
            self.highlight_names_or_places()
            if self.highlight_errors_var.get():
                self.highlight_errors()

    def highlight_changes(self):
        index = self.page_counter
        original_text = self.main_df.loc[index, 'Original_Text']
        first_draft = self.main_df.loc[index, 'First_Draft']

        if pd.isna(first_draft) or self.main_df.loc[index, 'Text_Toggle'] != "First_Draft":
            return

        self.text_display.tag_config("change_highlight", background="lightgreen")

        # Use difflib to find differences
        differ = difflib.Differ()
        diff = list(differ.compare(original_text.splitlines(), first_draft.splitlines()))

        line_num = 1
        for line in diff:
            if line.startswith('+ '):
                # This is a new line in First_Draft
                start = f"{line_num}.0"
                end = f"{line_num}.end"
                self.text_display.tag_add("change_highlight", start, end)
            elif line.startswith('- '):
                # This line was in original_text but not in First_Draft
                # We don't highlight it because it's not in the current text
                continue
            elif line.startswith('? '):
                # This line indicates where changes occurred within a line
                continue
            line_num += 1
    
    def highlight_errors(self):
        """Highlight error terms from the Errors column"""
        try:
            print("\nIn highlight_errors function:")
            # Configure error highlight style
            self.text_display.tag_configure("error_highlight", background="cyan")
            
            # Get current page index and text
            index = self.page_counter
            print(f"Current page index: {index}")
            if index not in self.main_df.index:
                print("Index not in DataFrame")
                return
                
            # Get the current text display mode
            selected = self.text_display_var.get()
            print(f"Current text display mode: {selected}")
            
            # Map display names to DataFrame columns
            text_map = {
                "Original Text": "Original_Text",
                "First Draft": "First_Draft",
                "Final Draft": "Final_Draft",
                "None": None
            }
            
            # Get the current text column
            current_col = text_map.get(selected)
            if not current_col:
                print("No valid text column selected")
                return
            print(f"Current text column: {current_col}")
                
            # Get errors for current page
            errors = self.main_df.at[index, 'Errors']
            print(f"Errors from DataFrame: {errors}")
            if pd.isna(errors) or not errors.strip():
                print("No errors found in DataFrame")
                return
                
            # Process and highlight errors
            def process_errors(errors_str):
                if not errors_str:
                    return
                error_terms = [term.strip() for term in errors_str.split(';') if term.strip()]
                print(f"Error terms to highlight: {error_terms}")
                for term in error_terms:
                    self.highlight_term(term, "error_highlight", exact_match=True)
            
            process_errors(errors)
                
        except Exception as e:
            print(f"Error highlighting errors: {str(e)}")
            self.error_logging(f"Error highlighting errors: {str(e)}")

# DF Update Functions

    def update_df(self):
        self.save_toggle = False
        # Get the text from the Text widget and clean it
        text = self.clean_text(self.text_display.get("1.0", tk.END))
        
        index = self.page_counter
        selected = self.text_display_var.get()
        
        # Map display names to DataFrame columns
        if selected == "Original_Text":
            self.main_df.loc[index, 'Original_Text'] = text
            self.main_df.loc[index, 'Text_Toggle'] = "Original_Text"
        elif selected == "First Draft":
            self.main_df.loc[index, 'First_Draft'] = text
            self.main_df.loc[index, 'Text_Toggle'] = "First_Draft"
        elif selected == "Final Draft":
            self.main_df.loc[index, 'Final_Draft'] = text
            self.main_df.loc[index, 'Text_Toggle'] = "Final_Draft"

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
                # Split response into Names and Places sections
                sections = response.split('\n')
                for section in sections:
                    if section.startswith("Names:"):
                        self.main_df.loc[index, 'People'] = section[6:].strip()
                    elif section.startswith("Places:"):
                        self.main_df.loc[index, 'Places'] = section[7:].strip()
            elif ai_job == "Chunk_Text":
                self.main_df.loc[index, 'Final_Draft'] = response
                self.main_df.loc[index, 'Text_Toggle'] = "Final_Draft"
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
            
            # Load the updated text
            self.load_text()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update DataFrame: {str(e)}")
            self.error_logging(f"Failed to update DataFrame: {str(e)}")

    def update_image_rotation(self, index, response):
        # Get the image path from the DataFrame.
        image_path = self.main_df.loc[index, 'Image_Path']
        # Convert relative path to absolute if necessary.
        if self.project_directory and not os.path.isabs(image_path):
            image_path = os.path.join(self.project_directory, image_path)
        
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
        
        if current_selection == "Final Draft":
            if messagebox.askyesno("Revert Text", 
                                "Do you want to revert to the first draft version?"):
                self.main_df.loc[index, 'Final_Draft'] = ""
                self.text_display_var.set("First Draft")
                self.main_df.loc[index, 'Text_Toggle'] = "First_Draft"
                
        elif current_selection == "First Draft":
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
                            "This will remove all corrections and cannot be undone."):
            self.main_df['Final_Draft'] = ""
            self.main_df['First_Draft'] = ""
            self.main_df['Text_Toggle'] = "Original_Text"
            self.text_display_var.set("Original_Text")
            
        self.load_text()
        self.counter_update()

    def remove_pagination(self):
        """Remove pagination markers from the current text."""
        if not self.main_df.empty:
            index = self.page_counter
            current_toggle = self.main_df.loc[index, 'Text_Toggle']
            
            # Get the current text based on Text_Toggle
            if current_toggle == "Final_Draft":
                text = self.main_df.loc[index, 'Final_Draft']
                column = 'Final_Draft'
            elif current_toggle == "First_Draft":
                text = self.main_df.loc[index, 'First_Draft']
                column = 'First_Draft'
            else:
                text = self.main_df.loc[index, 'Original_Text']
                column = 'Original_Text'

            # Remove the pagination markers
            if pd.notna(text):
                # Remove the pagination markers and any surrounding whitespace
                cleaned_text = re.sub(r'\s*\*{5,}\s*', '\n\n', text)
                
                # Update the DataFrame
                self.main_df.at[index, column] = cleaned_text
                
                # Update the display
                self.text_display.delete("1.0", tk.END)
                self.text_display.insert("1.0", cleaned_text)
                
                # Reset pagination flag
                self.pagination_added = False
                
                # Update the menu item state
                self.document_menu.entryconfig("Remove Pagination", state="disabled")

# Export Functions

    def export(self, export_path=None):
        """
        Export the processed text to a file.
        
        Args:
            export_path (str, optional): Path where the exported file should be saved.
                If None, a file dialog will be shown.
        """
        self.toggle_button_state()
        
        try:
            # If no export path is provided, show file dialog
            if export_path is None:
                export_path = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("Text files", "*.txt")],
                    title="Save Exported Text As"
                )
                
                if not export_path:  # User cancelled the dialog
                    self.toggle_button_state()
                    return

            combined_text = ""
            
            # Combine all the text values into a single string
            for index, row in self.main_df.iterrows():
                text = self.find_right_text(index)
                
                # Add appropriate spacing between entries
                if text:
                    if text[0].isalpha():  # If text starts with a letter
                        combined_text += text
                    else:
                        combined_text += "\n\n" + text
            
            # Clean up multiple newlines
            combined_text = re.sub(r"\n{3,}", "\n\n", combined_text)
            
            # Save the combined text to the chosen file
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(combined_text)
                
            # Show success message if this was manually triggered
            if export_path is None:
                messagebox.showinfo("Success", "Text exported successfully!")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export text: {str(e)}")
            self.error_logging(f"Failed to export text: {str(e)}")
            
        finally:
            self.toggle_button_state()

    def export_single_file(self):
        self.toggle_button_state()        
        combined_text = ""

        # Use a file dialog to ask the user where to save the exported text
        export_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            title="Save Exported Text As"
        )
        
        # Combine all the processed_text values into a single string
        for index, row in self.main_df.iterrows():
            text = self.find_right_text(index)
            if text and text[0].isalpha():
                combined_text += text
            else:
                combined_text += "\n\n" + text

        # Delete instances of three or more newline characters in a row, replacing them with two newline characters
        combined_text = re.sub(r"\n{3,}", "\n\n", combined_text)

        if not export_path:  # User cancelled the file dialog
            self.toggle_button_state()
            return

        # Save the combined text to the chosen file
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(combined_text)

        self.toggle_button_state()

    def export_text_files(self):
        """Export each page's text as a separate text file with sequential numbering."""
        if self.main_df.empty:
            messagebox.showwarning("No Data", "No documents to export.")
            return

        # Ask user for base filename and directory
        save_dir = filedialog.askdirectory(title="Select Directory to Save Text Files")
        if not save_dir:
            return

        base_filename = simpledialog.askstring("Input", "Enter base filename for text files:",
                                            initialvalue="document")
        if not base_filename:
            return

        try:
            # Show progress bar
            progress_window, progress_bar, progress_label = self.progress_bar.create_progress_window("Exporting Text Files")
            total_pages = len(self.main_df)
            self.progress_bar.update_progress(0, total_pages)

            # Track successful exports
            successful_exports = 0

            for index, row in self.main_df.iterrows():
                try:
                    # Update progress
                    self.progress_bar.update_progress(index + 1, total_pages)

                    # Get the text using existing function
                    text = self.find_right_text(index)

                    # Create filename with sequential numbering
                    filename = f"{base_filename}_{index+1:04d}.txt"
                    file_path = os.path.join(save_dir, filename)

                    # Write the text to file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(text if text else '')

                    successful_exports += 1

                except Exception as e:
                    self.error_logging(f"Error exporting text file for index {index}: {str(e)}")
                    continue

            self.progress_bar.close_progress_window()

            # Show completion message
            if successful_exports == total_pages:
                messagebox.showinfo("Success", f"Successfully exported {successful_exports} text files.")
            else:
                messagebox.showwarning("Partial Success", 
                                    f"Exported {successful_exports} out of {total_pages} text files.\n"
                                    f"Check the error log for details.")

        except Exception as e:
            self.progress_bar.close_progress_window()
            messagebox.showerror("Error", f"Failed to export text files: {str(e)}")
            self.error_logging(f"Text file export error: {str(e)}")

    def export_as_pdf(self):
        """Export the document as a PDF with images and their associated text."""
        if self.main_df.empty:
            messagebox.showwarning("No Data", "No documents to export.")
            return

        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save PDF As"
        )
        
        if not file_path:
            return

        try:
            # Show progress bar
            progress_window, progress_bar, progress_label = self.progress_bar.create_progress_window("Creating PDF")
            total_pages = len(self.main_df)
            self.progress_bar.update_progress(0, total_pages)

            # Create PDF document
            doc = fitz.open()
            
            for index, row in self.main_df.iterrows():
                try:
                    # Update progress
                    self.progress_bar.update_progress(index + 1, total_pages)
                    
                    # Get image path and ensure it's absolute
                    image_path = row['Image_Path']
                    if not os.path.isabs(image_path):
                        image_path = os.path.join(self.project_directory, image_path)

                    # Get associated text based on Text_Toggle
                    text = self.find_right_text(index)

                    # Create new page at A4 size
                    page = doc.new_page(width=595, height=842)  # A4 size in points

                    try:
                        # Open image and get its size
                        img = Image.open(image_path)
                        img_width, img_height = img.size
                        img.close()

                        # Calculate scaling to fit page while maintaining aspect ratio
                        page_width = page.rect.width
                        page_height = page.rect.height
                        
                        width_scale = page_width / img_width
                        height_scale = page_height / img_height
                        scale = min(width_scale, height_scale)

                        # Insert image with proper scaling
                        page.insert_image(
                            page.rect,  # Use full page rect
                            filename=image_path,
                            keep_proportion=True
                        )

                        # Add searchable text layer
                        if text:
                            page.insert_text(
                                point=(0, 0),  # Starting position
                                text=text,
                                fontsize=1,  # Very small font size
                                color=(0, 0, 0, 0),  # Transparent color
                                render_mode=3  # Invisible but searchable
                            )

                    except Exception as e:
                        self.error_logging(f"Error inserting image at index {index}: {str(e)}")
                        continue

                except Exception as e:
                    self.error_logging(f"Error processing page {index + 1}: {str(e)}")
                    continue

            # Save the PDF with optimization for images
            doc.save(
                file_path,
                garbage=4,
                deflate=True,
                pretty=False
            )
            doc.close()

            self.progress_bar.close_progress_window()
            messagebox.showinfo("Success", "PDF exported successfully!")

        except Exception as e:
            self.progress_bar.close_progress_window()
            messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")
            self.error_logging(f"PDF export error: {str(e)}")

# External Tools

    def find_and_replace(self, event=None):
        self.find_replace.update_main_df(self.main_df)
        self.find_replace.find_and_replace(event)
            
    
    def update_api_handler(self):
        self.api_handler = APIHandler(
            self.settings.openai_api_key, 
            self.settings.anthropic_api_key, 
            self.settings.google_api_key
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
                if not os.path.isabs(current_image_path):
                    current_image_path = os.path.join(self.project_directory, current_image_path)
                
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
                                    is_base64=True, formatting_function=False):
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
                formatting_function=formatting_function
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
            progress_title = f"Applying {ai_job} to {'Current Page' if all_or_one_flag == 'Current Page' else 'All Pages'}..."
            progress_window, progress_bar, progress_label = self.progress_bar.create_progress_window(progress_title)
            self.progress_bar.update_progress(0, 1)

            responses_dict = {}
            futures_to_index = {}
            processed_rows = 0
            total_rows = 0

            # Modified batch_df setup for different job types
            if ai_job == "HTR":
                if all_or_one_flag == "Current Page":
                    # Only process current page if it has no Original_Text
                    row = self.page_counter
                    if pd.isna(self.main_df.loc[row, 'Original_Text']) or self.main_df.loc[row, 'Original_Text'].strip() == '':
                        batch_df = self.main_df.loc[[row]]
                    else:
                        messagebox.showinfo("Skip", "This page already has recognized text.")
                        return
                else:
                    # Filter for pages without Original_Text
                    batch_df = self.main_df[
                        (self.main_df['Image_Path'].notna()) & 
                        (self.main_df['Image_Path'] != '') & 
                        ((self.main_df['Original_Text'].isna()) | (self.main_df['Original_Text'] == ''))
                    ]
# In the ai_function method, modify the batch_df setup section:

            elif ai_job == "Correct_Text":
                if all_or_one_flag == "Current Page":
                    # Only process current page if it has Original_Text but no First_Draft
                    row = self.page_counter
                    if pd.notna(self.main_df.loc[row, 'Original_Text']) and \
                    (pd.isna(self.main_df.loc[row, 'First_Draft']) or self.main_df.loc[row, 'First_Draft'].strip() == ''):
                        batch_df = self.main_df.loc[[row]]
                    else:
                        messagebox.showinfo("Skip", "This page either lacks Original_Text or already has corrections.")
                        return
                else:
                    # Filter for pages with Original_Text but without First_Draft
                    batch_df = self.main_df[
                        (self.main_df['Original_Text'].notna()) & 
                        (self.main_df['Original_Text'] != '') & 
                        ((self.main_df['First_Draft'].isna()) | (self.main_df['First_Draft'] == ''))
                    ]
            elif ai_job == "Create_Final_Draft":
                if all_or_one_flag == "Current Page":
                    # Only process current page if it has First_Draft but no Final_Draft
                    row = self.page_counter
                    if pd.notna(self.main_df.loc[row, 'First_Draft']) and \
                    (pd.isna(self.main_df.loc[row, 'Final_Draft']) or self.main_df.loc[row, 'Final_Draft'].strip() == ''):
                        batch_df = self.main_df.loc[[row]]
                    else:
                        messagebox.showinfo("Skip", "This page either lacks First_Draft or already has Final_Draft.")
                        return
                else:
                    # Filter for pages with First_Draft but without Final_Draft
                    batch_df = self.main_df[
                        (self.main_df['First_Draft'].notna()) & 
                        (self.main_df['First_Draft'] != '') & 
                        ((self.main_df['Final_Draft'].isna()) | (self.main_df['Final_Draft'] == ''))
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
            elif ai_job == "Chunk_Text":
                if all_or_one_flag == "Current Page":
                    row = self.page_counter
                    # Check if there's text to process
                    if self.find_right_text(row).strip():
                        batch_df = self.main_df.loc[[row]]
                    else:
                        messagebox.showinfo("Skip", "This page has no text to chunk.")
                        return
                else:
                    # Process only pages that have text
                    batch_df = self.main_df[
                        self.main_df.apply(lambda row: bool(self.find_right_text(row.name).strip()), axis=1)
                    ]
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
                                is_base64=not "gemini" in job_params['engine'].lower()
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
            self.progress_bar.close_progress_window()
            self.load_text()
            self.counter_update()
            self.toggle_button_state()

            if error_count > 0:
                message = f"An error occurred while processing the current page." if all_or_one_flag == "Current Page" else f"Errors occurred while processing {error_count} page(s)."
                messagebox.showwarning("Processing Error", message)
    
    def setup_job_parameters(self, ai_job):
        """
        Setup and return the job parameters for the specified AI job.
        For the "Chunk_Text" job, use the preset selected via the chunking strategy dropdown.
        For other jobs, use the function presets as before.
        """
        if ai_job == "Chunk_Text":
            # Use the selected chunking preset from the dropdown
            selected_name = self.chunking_strategy_var.get()
            preset = next((p for p in self.settings.chunk_text_presets if p['name'] == selected_name), None)
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
        elif ai_job == "Custom":
            # Use the custom function selected by the user
            custom_preset_name = self.custom_function_selected  # set in your custom selection window
            preset = next((p for p in self.settings.function_presets if p['name'] == custom_preset_name), None)
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
                raise ValueError("Custom preset not found.")
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
                    "use_images": preset.get('use_images', True),
                    "current_image": preset.get('current_image', "Yes"),
                    "num_prev_images": int(preset.get('num_prev_images', 0)),
                    "num_after_images": int(preset.get('num_after_images', 0))
                }
            else:
                return {
                    "temp": 0.7,
                    "val_text": "",
                    "engine": self.settings.model_list[0],
                    "user_prompt": "",
                    "system_prompt": "",
                    "batch_size": self.settings.batch_size,
                    "use_images": True,
                    "current_image": "Yes",
                    "num_prev_images": 0,
                    "num_after_images": 0
                }
        
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
    
    def get_doc_type_with_ai(self):
        pass
        # print ("In get_doc_type_with_ai")
        
        # # Build the list of document types from the chunk_text_presets
        # doc_types = [preset['name'] for preset in self.settings.chunk_text_presets] if self.settings.chunk_text_presets else []
        # list_of_doc_types = str(doc_types)
        
        # system_prompt = (
        #     f'You are a function in a program that classifies historical documents according to a set scheme. '
        #     f'You examine images of documents, write "Output:" and then output the most correct general classification '
        #     f'from the following list: {list_of_doc_types}, nothing else. If none of those apply or if more than one of '
        #     f'those applies, write "Output: Other" or "Output: N/A".'
        # )
        # user_prompt = ""  # Specific instructions are empty
        
        # # API call settings
        # temp = 0.2
        # val_text = "Output:"
        # engine = "gemini-2.0-flash"
        
        # # Prepare image data using the current image if available
        # if hasattr(self, 'current_image_path') and self.current_image_path:
        #     image_tuple = (self.current_image_path, "Document Image:")
        #     image_data = self.api_handler.prepare_image_data(
        #         [image_tuple], 
        #         engine, 
        #         is_base64=not ("gemini" in engine.lower())
        #     )
        # else:
        #     image_data = []
        
        # text_to_process = ""
        # index = 0  # Placeholder index
        
        # try:
        #     result = asyncio.run(
        #         self.process_api_request(
        #             system_prompt=system_prompt,
        #             user_prompt=user_prompt,
        #             temp=temp,
        #             image_data=image_data,
        #             text_to_process=text_to_process,
        #             val_text=val_text,
        #             engine=engine,
        #             index=index,
        #             is_base64=not ("gemini" in engine.lower()),
        #             formatting_function=False
        #         )
        #     )
        #     # Unpack the tuple returned by process_api_request
        #     response, _ = result

        #     print ("Response: ", response)

        #     # Keep only the first line of the response
        #     first_line = response.split("\n")[0].strip()
        #     # Remove the "Output:" prefix if present
        #     if first_line.startswith("Output:"):
        #         classification = first_line[len("Output:"):].strip()
        #     else:
        #         classification = first_line
            
        #     print ("Classification: ", classification)
            
        #     # Check if the classification is valid
        #     doc_types = [preset['name'] for preset in self.settings.chunk_text_presets]
        #     if classification in doc_types:
        #         self.chunking_strategy_var.set(classification)
        #     else:
        #         self.chunking_strategy_var.set("")
                
        # except Exception as e:
        #     self.chunking_strategy_var.set("")

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
            
            def gather_unique_items(column_name):
                """Helper function to gather unique items from a DataFrame column"""
                try:
                    all_items = []
                    if column_name in self.main_df.columns:
                        for val in self.main_df[column_name].dropna():
                            if val.strip():
                                entries = [x.strip() for x in val.split(';') if x.strip()]
                                all_items.extend(entries)
                    return sorted(set(all_items), key=lambda x: x.lower())
                except Exception as e:
                    self.error_logging(f"Error gathering items from {column_name}: {str(e)}")
                    return []

            # Gather unique names and places using the helper function
            unique_names = gather_unique_items('People')
            unique_places = gather_unique_items('Places')

            # If there's nothing to collate, return early
            if not unique_names and not unique_places:
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
                "contain variants of the same entity spelled incorrectly or with OCR errors." 
                "Ignore minor variants such as the inclusion of 'Mr' or other suffixes in names and concentrate on the core name as it would be used in a keyword search."
                "For name variants where the first name/iniital are different, groupt these together separately."
                "List only place names with multiple variants, group them together (using your judgement to combine names/places that are obvious errors or that are phonetically similar together) and pick the best spelling. Output them as:\n\n"
                "Response:\n"
                "most_complete_spelling = variant1; variant2; ...\n"
                "most_complete_spelling = variant1; variant2; ...\n"
            )

            # Show progress
            progress_window, progress_bar, progress_label = self.progress_bar.create_progress_window("Collating Names and Places")
            total_tasks = len(tasks)
            processed_tasks = 0

            try:
                # Process using same pattern as ai_function
                results = {}
                with ThreadPoolExecutor(max_workers=1) as executor:
                    futures_to_label = {}
                    
                    for label, items in tasks:
                        text_for_llm = "\n".join(items)
                        future = executor.submit(
                            asyncio.run,
                            self.process_api_request(
                                system_prompt=system_message,
                                user_prompt=f"Below is a list of {label}. Collate them.\n\n{text_for_llm}",
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

                    # Process results
                    for future in as_completed(futures_to_label):
                        label = futures_to_label[future]
                        try:
                            response, _ = future.result(timeout=30)  # Add timeout
                            results[label] = response
                        except Exception as e:
                            self.error_logging(f"Error processing {label}: {str(e)}")
                            results[label] = ""
                        
                        # Update progress
                        processed_tasks += 1
                        self.progress_bar.update_progress(processed_tasks, total_tasks)

                # Store results
                self.collated_names_raw = results.get("names", "")
                self.collated_places_raw = results.get("places", "")

            except Exception as e:
                self.error_logging(f"Error in main processing: {str(e)}")
                raise  # Re-raise to be caught by outer try-except

            finally:
                # Clean up progress bar
                try:
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
        
        finally:
            # Final cleanup and UI update
            try:
                self.update()  # Force GUI update
            except Exception as e:
                self.error_logging(f"Error in final UI update: {str(e)}")# Main Loop
                
if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        # Log the error
        print(f"Critical error in main loop: {str(e)}")
        # Try to write to error log if possible
        try:
            with open("critical_error.log", "a") as f:
                f.write(f"{datetime.now()}: {str(e)}\n")
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