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
        self.apply_collation_dict(collated_dict, is_names=True)

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
        self.apply_collation_dict(collated_dict, is_names=False)

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

    def apply_collation_dict(self, coll_dict, is_names=True):
        """
        For each row, find-and-replace all variations in the active text column.
        If is_names=True, we're applying name variants; else place variants.
        """
        if not coll_dict:
                messagebox.showinfo("Info", f"No {'names' if is_names else 'places'} found to replace.")
                return

        modified_count = 0
        # Access main_df via self.app
        for idx, row in self.app.main_df.iterrows():
            active_col = row.get('Text_Toggle', None)
            if active_col not in ["Original_Text", "Corrected_Text", "Formatted_Text", "Translation", "Separated_Text"]:
                continue # Skip if no active text or if it's 'None'

            old_text = row.get(active_col, "") # Use .get for safety
            if not isinstance(old_text, str) or not old_text.strip():
                continue # Skip if text is empty or not a string

            new_text = old_text
            # For each correct spelling => list of variants
            for correct_term, variants in coll_dict.items():
                # Create a pattern that matches any of the variants (case-insensitive, whole words)
                # Ensure variants don't contain problematic regex characters or handle them
                escaped_variants = [re.escape(var) for var in variants if var] # Escape variants
                if not escaped_variants: continue # Skip if no valid variants

                # Build regex pattern: \b(var1|var2|var3)\b
                # Use word boundaries (\b) to avoid partial matches within words.
                # Sort variants by length descending to match longer variants first
                escaped_variants.sort(key=len, reverse=True)
                pattern_str = r'\b(' + '|'.join(escaped_variants) + r')\b'
                pattern = re.compile(pattern_str, re.IGNORECASE)

                # Replace all occurrences of any variant with the correct term
                new_text = pattern.sub(correct_term, new_text)

            # Update DataFrame only if text changed
            if new_text != old_text:
                self.app.main_df.at[idx, active_col] = new_text # Update app's main_df
                modified_count += 1

        # Refresh text display if the current page was modified
        # Access page_counter, main_df, load_text, counter_update via self.app
        if self.app.page_counter in self.app.main_df.index: # Check if index is valid
            current_page_active_col = self.app.main_df.loc[self.app.page_counter].get('Text_Toggle', None)
            # Find if current page index was modified
            current_text_widget_content = self.app.text_display.get("1.0", tk.END).strip()
            if current_page_active_col in self.app.main_df.columns: # Ensure column exists
                modified_df_content = self.app.main_df.loc[self.app.page_counter, current_page_active_col]
                if modified_df_content != current_text_widget_content:
                    self.app.load_text() # Reload text only if current page changed
                    self.app.counter_update()
            else: # If active column somehow doesn't exist, still try to load
                 self.app.load_text()
                 self.app.counter_update()


        messagebox.showinfo("Replacement Complete", f"Replaced variations in {modified_count} page(s).")



