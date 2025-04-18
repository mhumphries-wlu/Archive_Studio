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
        # Gather unique names and places first
        unique_names = self.gather_unique_items('People')
        unique_places = self.gather_unique_items('Places')

        # Debug: Print gathered unique names and places
        print(f"DEBUG: unique_names={unique_names}")
        print(f"DEBUG: unique_places={unique_places}")

        # 1) Collect suggestions from the LLM automatically using the app's AI handler
        # Make sure the collate function exists in AIFunctionsHandler
        if hasattr(self.app.ai_functions_handler, 'collate_names_and_places'):
            self.app.ai_functions_handler.collate_names_and_places(unique_names, unique_places)
            # Debug: Print the raw collation results after API call
            print(f"DEBUG: collated_names_raw={getattr(self.app.ai_functions_handler, 'collated_names_raw', None)}")
            print(f"DEBUG: collated_places_raw={getattr(self.app.ai_functions_handler, 'collated_places_raw', None)}")
        else:
            self.app.error_logging("collate_names_and_places method not found in AIFunctionsHandler", level="ERROR")
            messagebox.showerror("Error", "Internal error: Collation function not found.")
            return

        # 2) Now show the user a GUI with the raw lines
        self.create_collate_names_places_window()

    def create_collate_names_places_window(self):
        """
        A larger window with two spreadsheet-like areas for the collated lines from the LLM.
        Each area has two columns: Consolidated Term and Terms to Consolidate.
        The user can manually edit or remove lines before applying replacements.
        """
        window = tk.Toplevel(self.app) # Use self.app as parent
        window.title("Collate Names & Places")
        window.geometry("800x600")
        window.grab_set()

        # Frame for labels
        lbl_frame = tk.Frame(window)
        lbl_frame.pack(side="top", fill="x", pady=5)

        names_label = tk.Label(lbl_frame, text="Collated Names (edit as needed):")
        names_label.pack(anchor="w", padx=5)

        # Treeview for Names
        names_frame = tk.Frame(window)
        names_frame.pack(fill="both", expand=True, padx=5, pady=(0,10))
        self.names_tree = ttk.Treeview(names_frame, columns=("Consolidated Term", "Terms to Consolidate"), show="headings", height=8, selectmode="extended")
        self.names_tree.heading("Consolidated Term", text="Consolidated Term")
        self.names_tree.heading("Terms to Consolidate", text="Terms to Consolidate")
        self.names_tree.column("Consolidated Term", width=200)
        self.names_tree.column("Terms to Consolidate", width=500)
        self.names_tree.pack(fill="both", expand=True, side="left")

        # Populate names treeview
        collated_names = getattr(self.app.ai_functions_handler, 'collated_names_raw', "")
        names_dict = self.parse_collation_response(collated_names)
        for consolidated, variants in names_dict.items():
            self.names_tree.insert("", "end", values=(consolidated, "; ".join(variants)))

        # Enable in-place editing for names_tree
        self.names_tree.bind('<Double-1>', lambda event: self._edit_treeview_cell(event, self.names_tree))
        # Bind Delete key for names_tree
        self.names_tree.bind('<Delete>', lambda event: self.delete_selected_name_row())

        places_label = tk.Label(window, text="Collated Places (edit as needed):")
        places_label.pack(anchor="w", padx=5)

        # Treeview for Places
        places_frame = tk.Frame(window)
        places_frame.pack(fill="both", expand=True, padx=5, pady=(0,10))
        self.places_tree = ttk.Treeview(places_frame, columns=("Consolidated Term", "Terms to Consolidate"), show="headings", height=8, selectmode="extended")
        self.places_tree.heading("Consolidated Term", text="Consolidated Term")
        self.places_tree.heading("Terms to Consolidate", text="Terms to Consolidate")
        self.places_tree.column("Consolidated Term", width=200)
        self.places_tree.column("Terms to Consolidate", width=500)
        self.places_tree.pack(fill="both", expand=True, side="left")

        # Populate places treeview
        collated_places = getattr(self.app.ai_functions_handler, 'collated_places_raw', "")
        places_dict = self.parse_collation_response(collated_places)
        for consolidated, variants in places_dict.items():
            self.places_tree.insert("", "end", values=(consolidated, "; ".join(variants)))

        # Enable in-place editing for places_tree
        self.places_tree.bind('<Double-1>', lambda event: self._edit_treeview_cell(event, self.places_tree))
        # Bind Delete key for places_tree
        self.places_tree.bind('<Delete>', lambda event: self.delete_selected_place_row())

        # Buttons at bottom
        btn_frame = tk.Frame(window)
        btn_frame.pack(side="bottom", pady=10)

        btn_names = tk.Button(btn_frame, text="Replace Names", command=self.replace_names_button)
        btn_names.pack(side="left", padx=10)

        btn_places = tk.Button(btn_frame, text="Replace Places", command=self.replace_places_button)
        btn_places.pack(side="left", padx=10)

        btn_cancel = tk.Button(btn_frame, text="Cancel", command=window.destroy)
        btn_cancel.pack(side="left", padx=10)

        self.app.wait_window(window)

    def _edit_treeview_cell(self, event, tree):
        region = tree.identify('region', event.x, event.y)
        if region != 'cell':
            return
        row_id = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        if not row_id or not col:
            return
        col_index = int(col.replace('#', '')) - 1
        x, y, width, height = tree.bbox(row_id, col)
        value = tree.item(row_id, 'values')[col_index]

        # Destroy any previous active entry
        if hasattr(self, '_active_entry') and self._active_entry is not None:
            self._active_entry.destroy()
            self._active_entry = None
            self._active_entry_save = None

        entry = tk.Entry(tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, value)
        entry.focus_set()
        self._active_entry = entry

        def save_edit(event=None):
            new_value = entry.get()
            values = list(tree.item(row_id, 'values'))
            values[col_index] = new_value
            tree.item(row_id, values=values)
            entry.destroy()
            self._active_entry = None
            self._active_entry_save = None

        self._active_entry_save = save_edit
        entry.bind('<Return>', save_edit)
        entry.bind('<FocusOut>', save_edit)

    def replace_names_button(self):
        # Commit any open edit before reading the treeview
        if hasattr(self, '_active_entry') and self._active_entry is not None and self._active_entry_save:
            self._active_entry_save()
        if not hasattr(self, 'names_tree'):
            self.app.error_logging("Names treeview not initialized.", level="ERROR")
            return
        collated_dict = {}
        for row in self.names_tree.get_children():
            consolidated, variants = self.names_tree.item(row, 'values')
            variant_list = [v.strip() for v in variants.split(';') if v.strip()]
            if consolidated and variant_list:
                collated_dict[consolidated] = variant_list
        self.app.data_operations.apply_collation_dict(collated_dict, is_names=True)

    def replace_places_button(self):
        # Commit any open edit before reading the treeview
        if hasattr(self, '_active_entry') and self._active_entry is not None and self._active_entry_save:
            self._active_entry_save()
        if not hasattr(self, 'places_tree'):
            self.app.error_logging("Places treeview not initialized.", level="ERROR")
            return
        collated_dict = {}
        for row in self.places_tree.get_children():
            consolidated, variants = self.places_tree.item(row, 'values')
            variant_list = [v.strip() for v in variants.split(';') if v.strip()]
            if consolidated and variant_list:
                collated_dict[consolidated] = variant_list
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

    def gather_unique_items(self, column_name):
        """Helper function to gather unique items from a DataFrame column"""
        all_items = set() # Use a set for efficiency
        if column_name in self.app.main_df.columns:
            try:
                series = self.app.main_df[column_name].dropna().astype(str) # Ensure string type
                split_items = series.str.split(';').explode().str.strip()
                all_items.update(split_items[split_items != ''].tolist())
            except Exception as e:
                self.app.error_logging(f"Error during vectorized gathering from {column_name}: {e}. Falling back to iteration.", level="WARNING")
                all_items = set()
                for idx, val in self.app.main_df[column_name].dropna().items():
                    if isinstance(val, str) and val.strip():
                        entries = [x.strip() for x in val.split(';') if x.strip()]
                        all_items.update(entries)

        unique_items = sorted(list(all_items), key=str.lower)
        self.app.error_logging(f"Total unique {column_name}: {len(unique_items)}", level="DEBUG")
        return unique_items

    def delete_selected_name_row(self):
        if hasattr(self, 'names_tree'):
            selected = self.names_tree.selection()
            for item in selected:
                self.names_tree.delete(item)

    def delete_selected_place_row(self):
        if hasattr(self, 'places_tree'):
            selected = self.places_tree.selection()
            for item in selected:
                self.places_tree.delete(item)



