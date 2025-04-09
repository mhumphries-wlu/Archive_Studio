# util/NamesAndPlaces.py

# This file contains the NamesAndPlacesHandler class, which is used to handle
# the names and places for the application. 

import tkinter as tk
from tkinter import ttk, messagebox
import re

class NamesAndPlacesHandler:
    def __init__(self, app):
        self.app = app # Store reference to the main application
        self.names_textbox = None
        self.places_textbox = None

    def initiate_collation_and_show_window(self):
        """
        First collects names and places from the LLM, then shows the GUI for user editing.
        """
        # 1) Collect suggestions from the LLM automatically using the app's AI handler
        # Make sure the collate function exists in AIFunctionsHandler
        if hasattr(self.app.ai_functions_handler, 'collate_names_and_places'):
            self.app.ai_functions_handler.collate_names_and_places()
        else:
            self.app.error_logging("collate_names_and_places method not found in AIFunctionsHandler", level="ERROR")
            messagebox.showerror("Error", "Internal error: Collation function not found.")
            return

        # 2) Now show the user a GUI with the raw lines
        self.create_collate_names_places_window()

    def create_collate_names_places_window(self):
        """
        A larger window with two text boxes for the collated lines from the LLM.
        The user can manually edit or remove lines before applying replacements.
        """
        window = tk.Toplevel(self.app) # Use self.app as parent
        window.title("Collate Names & Places")
        window.geometry("600x500")
        window.grab_set()

        # Frame for labels
        lbl_frame = tk.Frame(window)
        lbl_frame.pack(side="top", fill="x", pady=5)

        names_label = tk.Label(lbl_frame, text="Collated Names (edit as needed):")
        names_label.pack(anchor="w", padx=5)

        # Text display for Names - Store reference in handler
        self.names_textbox = tk.Text(window, wrap="word", height=10)
        self.names_textbox.pack(fill="both", expand=True, padx=5, pady=(0,10))
        # Access collated data via the app's AI handler
        collated_names = getattr(self.app.ai_functions_handler, 'collated_names_raw', "")
        self.names_textbox.insert("1.0", collated_names)

        places_label = tk.Label(window, text="Collated Places (edit as needed):")
        places_label.pack(anchor="w", padx=5)

        # Text display for Places - Store reference in handler
        self.places_textbox = tk.Text(window, wrap="word", height=10)
        self.places_textbox.pack(fill="both", expand=True, padx=5, pady=(0,10))
        # Access collated data via the app's AI handler
        collated_places = getattr(self.app.ai_functions_handler, 'collated_places_raw', "")
        self.places_textbox.insert("1.0", collated_places)

        # Buttons at bottom
        btn_frame = tk.Frame(window)
        btn_frame.pack(side="bottom", pady=10)

        # Buttons now call methods within this handler instance
        btn_names = tk.Button(btn_frame, text="Replace Names", command=self.replace_names_button)
        btn_names.pack(side="left", padx=10)

        btn_places = tk.Button(btn_frame, text="Replace Places", command=self.replace_places_button)
        btn_places.pack(side="left", padx=10)

        btn_cancel = tk.Button(btn_frame, text="Cancel", command=window.destroy)
        btn_cancel.pack(side="left", padx=10)

        # Wait for the window (optional, but good practice if modal)
        self.app.wait_window(window)

    def replace_names_button(self):
        """
        Parse the user-edited names from self.names_textbox,
        then do the find-and-replace in the active text.
        """
        if not self.names_textbox:
             self.app.error_logging("Names textbox not initialized.", level="ERROR")
             return
        raw = self.names_textbox.get("1.0", tk.END)
        collated_dict = self.parse_collation_response(raw)
        # Call the method on the DataOperations instance via self.app
        self.app.data_operations.apply_collation_dict(collated_dict, is_names=True)

    def replace_places_button(self):
        """
        Parse the user-edited places from self.places_textbox,
        then do the find-and-replace in the active text.
        """
        if not self.places_textbox:
            self.app.error_logging("Places textbox not initialized.", level="ERROR")
            return
        raw = self.places_textbox.get("1.0", tk.END)
        collated_dict = self.parse_collation_response(raw)
        # Call the method on the DataOperations instance via self.app
        self.app.data_operations.apply_collation_dict(collated_dict, is_names=False)

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
                self.app.error_logging("Empty or invalid response text", level="WARNING") # Use app's logger
                return {}

            coll_dict = {}
            # Handle potential '\r\n' line endings as well
            lines = response_text.replace('\r\n', '\n').splitlines()

            response_found = False
            current_correct = None # Keep track of the last correct term for multi-line variants

            for ln in lines:
                ln = ln.strip()
                if not ln:
                    continue

                # Check for "Response:" header and skip it
                # Make the check case-insensitive and allow variations
                if ln.lower().startswith("response:") or ln.lower().startswith("collated names:") or ln.lower().startswith("collated places:"):
                    response_found = True
                    current_correct = None # Reset when a new header is found
                    continue

                # Handle various formatting possibilities
                if '=' in ln:
                    # Standard format: correct = variant1; variant2
                    parts = ln.split('=', 1)
                    correct = parts[0].strip()
                    variations_text = parts[1].strip()
                    current_correct = correct # Update the current correct term

                    # Handle different delimiter styles (semicolon first, then comma)
                    if ';' in variations_text:
                        variations = [v.strip() for v in variations_text.split(';') if v.strip()]
                    elif ',' in variations_text:
                        variations = [v.strip() for v in variations_text.split(',') if v.strip()]
                    else:
                        # If no delimiter, assume it's a single variant
                        variations = [variations_text] if variations_text else []

                    if correct and variations:
                        # If the correct term already exists, merge the variations
                        existing_variants = coll_dict.get(correct, [])
                        coll_dict[correct] = sorted(list(set(existing_variants + variations)), key=str.lower)

                # Handle case where line might be a continuation (starts with '; ' or ', ')
                elif response_found and current_correct and (ln.startswith(';') or ln.startswith(',')):
                        # This looks like a continuation line
                        continuation_text = ln[1:].strip() # Remove the leading delimiter
                        if ';' in continuation_text:
                            variations = [v.strip() for v in continuation_text.split(';') if v.strip()]
                        elif ',' in continuation_text:
                            variations = [v.strip() for v in continuation_text.split(',') if v.strip()]
                        else:
                            variations = [continuation_text] if continuation_text else []

                        if variations:
                            existing_variants = coll_dict.get(current_correct, [])
                            coll_dict[current_correct] = sorted(list(set(existing_variants + variations)), key=str.lower)

            total_variants = sum(len(variants) for variants in coll_dict.values())

            return coll_dict

        except Exception as e:
            self.app.error_logging(f"Error parsing collation response: {str(e)}") # Use app's logger
            return {}



