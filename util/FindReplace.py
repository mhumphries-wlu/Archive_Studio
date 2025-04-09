# util/FindReplace.py

# This file contains the FindReplace class, which is used to handle
# the find and replace functionality in the application.
import tkinter as tk
from tkinter import messagebox
import string, re
import pandas as pd

class FindReplace:
    """
    A class to handle find and replace functionality in a text editor with DataFrame backing.
    
    Provides functionality for:
    - Finding text with case sensitivity option
    - Replacing single or all occurrences of text
    - Navigating through matches
    - Highlighting matched text
    """

    def __init__(self, parent, text_display, main_df, navigate_callback, get_page_counter, get_main_df_callback, text_display_var):
        """
        Initialize the FindReplace window and its functionality.
        
        Args:
            parent: Parent tkinter window
            text_display: Text widget where content is displayed
            main_df: DataFrame containing the document data
            navigate_callback: Callback function for navigation
            get_page_counter: Function to get current page number
            get_main_df_callback: Function to get updated DataFrame
            text_display_var: StringVar holding the currently selected text type in the main app
        """
        self.parent = parent
        self.text_display = text_display
        self.main_df = main_df
        self.find_replace_toggle = False
        self.find_replace_matches_df = pd.DataFrame(columns=["Index", "Page", "Match_Number"])
        self.link_nav = 0
        self.navigate_callback = navigate_callback
        self.get_page_counter = get_page_counter
        self.get_main_df = get_main_df_callback
        self.text_display_var = text_display_var
        self.case_sensitive = tk.BooleanVar(value=False)
        self.current_match_position = 0

# GUI Functions

    def create_find_replace_window(self, selected_text=""):
        """Create and configure the find/replace dialog window."""
        try:
            self.find_replace_window = tk.Toplevel(self.parent)
            self.find_replace_window.title("Find and Replace")
            self.find_replace_window.attributes("-topmost", True)
            self.find_replace_window.geometry("400x200")

            # Search Entry
            search_label = tk.Label(self.find_replace_window, text="Search:")
            search_label.grid(row=0, column=0, padx=5, pady=5)
            self.search_entry = tk.Entry(self.find_replace_window, width=50)
            self.search_entry.grid(row=0, column=1, padx=5, pady=5, columnspan=5)
            self.search_entry.insert(0, selected_text)

            # Replace Entry
            replace_label = tk.Label(self.find_replace_window, text="Replace:")
            replace_label.grid(row=1, column=0, padx=5, pady=5)
            self.replace_entry = tk.Entry(self.find_replace_window, width=50)
            self.replace_entry.grid(row=1, column=1, padx=5, pady=5, columnspan=5)

            # Case sensitivity checkbox
            self.case_checkbox = tk.Checkbutton(
                self.find_replace_window, 
                text="Case Sensitive",
                variable=self.case_sensitive
            )
            self.case_checkbox.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

            # Action buttons
            find_button = tk.Button(self.find_replace_window, text="Find", 
                                  command=self.find_matches)
            find_button.grid(row=2, column=0, padx=5, pady=15)

            find_all_button = tk.Button(self.find_replace_window, text="Find All", 
                                      command=self.find_all_matches)
            find_all_button.grid(row=2, column=1, padx=5, pady=5)

            empty_label = tk.Label(self.find_replace_window, text="")
            empty_label.grid(row=2, column=2, padx=20)

            replace_button = tk.Button(self.find_replace_window, text="Replace", 
                                     command=self.replace_text)
            replace_button.grid(row=2, column=3, padx=5, pady=5)

            replace_all_button = tk.Button(self.find_replace_window, text="Replace All", 
                                         command=self.replace_all_text)
            replace_all_button.grid(row=2, column=4, padx=5, pady=5)

            # Navigation frame
            nav_frame = tk.Frame(self.find_replace_window)
            nav_frame.grid(row=5, column=3, columnspan=2, padx=5, pady=15)

            self.first_match_button = tk.Button(nav_frame, text="|<<", 
                                              command=self.go_to_first_match, 
                                              state=tk.DISABLED)
            self.first_match_button.pack(side=tk.LEFT)

            self.prev_match_button = tk.Button(nav_frame, text="<<", 
                                             command=self.go_to_prev_match, 
                                             state=tk.DISABLED)
            self.prev_match_button.pack(side=tk.LEFT)

            self.next_match_button = tk.Button(nav_frame, text=">>", 
                                             command=self.go_to_next_match, 
                                             state=tk.DISABLED)
            self.next_match_button.pack(side=tk.LEFT)

            self.last_match_button = tk.Button(nav_frame, text=">>|", 
                                             command=self.go_to_last_match, 
                                             state=tk.DISABLED)
            self.last_match_button.pack(side=tk.LEFT)

            # Match counter frame
            match_frame = tk.Frame(self.find_replace_window)
            match_frame.grid(row=5, column=0, columnspan=2, padx=5, pady=5)

            self.current_match_label = tk.Label(match_frame, text="Match: 0 ")
            self.current_match_label.pack(side=tk.LEFT)

            self.total_matches_label = tk.Label(match_frame, text="/ 0")
            self.total_matches_label.pack(side=tk.LEFT)

            self.find_replace_toggle = True
            self.find_replace_window.protocol("WM_DELETE_WINDOW", self.close_find_replace_window)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to create find/replace window: {str(e)}")

    def close_find_replace_window(self):
        """Close the find/replace dialog window and reset toggle."""
        self.find_replace_toggle = False
        self.find_replace_window.destroy()

    def highlight_text(self):
        """Highlight all occurrences of the search term in the current text."""
        try:
            search_term = self.search_entry.get().strip()
            if not search_term:
                return

            self.text_display.tag_remove("highlight", "1.0", tk.END)
            
            start_pos = "1.0"
            while True:
                start_pos = self.text_display.search(
                    search_term, 
                    start_pos, 
                    tk.END, 
                    nocase=not self.case_sensitive.get(),
                    regexp=False
                )
                
                if not start_pos:
                    break
                    
                end_pos = f"{start_pos}+{len(search_term)}c"
                self.text_display.tag_add("highlight", start_pos, end_pos)
                start_pos = end_pos

            self.text_display.tag_config("highlight", background="yellow")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to highlight text: {str(e)}")

# Navigation Functions

    def _navigate_to_match(self, target_position):
        """
        Base navigation function that handles all match navigation.
        
        Args:
            target_position: The target match position to navigate to
        """
        try:
            if self.find_replace_matches_df.empty:
                return
                
            self.current_match_position = target_position
            self.link_nav = int(self.find_replace_matches_df.iloc[target_position]["Index"])
            self.navigate_callback(3)
            self.highlight_text()
            self.update_matches_counter()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to navigate to match: {str(e)}")
    
    def go_to_prev_match(self):
        """Navigate to the previous match in the document."""
        if not self.find_replace_matches_df.empty:
            total_matches = len(self.find_replace_matches_df)
            target = (self.current_match_position - 1) % total_matches
            self._navigate_to_match(target)
    
    def go_to_next_match(self):
        """Navigate to the next match in the document."""
        if not self.find_replace_matches_df.empty:
            total_matches = len(self.find_replace_matches_df)
            target = (self.current_match_position + 1) % total_matches
            self._navigate_to_match(target)
    
    def go_to_first_match(self):
        """Navigate to the first match in the document."""
        self._navigate_to_match(0)
    
    def go_to_last_match(self):
        """Navigate to the last match in the document."""
        if not self.find_replace_matches_df.empty:
            self._navigate_to_match(len(self.find_replace_matches_df) - 1)

# Helper Functions

    def update_matches_counter(self):
        """Update the match counter display."""
        try:
            if self.find_replace_matches_df.empty:
                self.current_match_label.config(text="Match: 0")
                self.total_matches_label.config(text="/ 0")
                return
                
            current_match = self.find_replace_matches_df.iloc[self.current_match_position]["Match_Number"]
            total_matches = len(self.find_replace_matches_df)
            self.current_match_label.config(text=f"Match: {current_match}")
            self.total_matches_label.config(text=f"/ {total_matches}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update match counter: {str(e)}")

    def enable_navigation_buttons(self):
        """Enable all navigation buttons."""
        for button in [self.first_match_button, self.prev_match_button, 
                      self.next_match_button, self.last_match_button]:
            button.config(state=tk.NORMAL)

    def disable_navigation_buttons(self):
        """Disable all navigation buttons."""
        for button in [self.first_match_button, self.prev_match_button, 
                      self.next_match_button, self.last_match_button]:
            button.config(state=tk.DISABLED)

    def get_active_text_column(self, row_index):
        """Get the active text column based on Text_Toggle value."""
        # --- THIS METHOD IS NO LONGER USED ---
        # Kept for reference during transition, will be removed later.
        try:
            text_toggle = self.main_df.loc[row_index, 'Text_Toggle']
            column_map = {
                "Original_Text": "Original_Text",
                "Corrected_Text": "Corrected_Text",
                "Formatted_Text": "Formatted_Text",
                "Translation": "Translation", # Added Translation
                "Separated_Text": "Separated_Text", # Added Separated_Text
                "None": None
            }
            return column_map.get(text_toggle)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get active text column: {str(e)}")
            return None

# Find and Replace Functions

    def find_and_replace(self, event=None):
        """Open the find and replace window."""
        try:
            selected_text = ""
            if self.text_display.tag_ranges("sel"):
                selected_text = self.text_display.get("sel.first", "sel.last")
                selected_text = selected_text.strip().strip(string.punctuation)

            if self.find_replace_toggle:
                self.search_entry.delete(0, tk.END)
                self.search_entry.insert(0, selected_text)
                return

            self.create_find_replace_window(selected_text)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open find and replace window: {str(e)}")

    def find_matches(self, main_df=None):
        """Find all matches of the search term in the document."""
        try:           
            # Clear existing highlighting at the start
            self.text_display.tag_remove("highlight", "1.0", tk.END)

            self.main_df = self.get_main_df()
            if main_df is not None:
                self.main_df = main_df

            search_term = self.search_entry.get().strip()
            if not search_term:
                messagebox.showwarning("Warning", "Please enter a search term.")
                return

            matches = []
            match_counter = 0

            # Get the column name from the main app's dropdown selection
            active_column = self.text_display_var.get()

            # If "None" is selected or the column doesn't exist, don't search
            if active_column == "None" or active_column not in self.main_df.columns:
                 messagebox.showinfo("No Searchable Text", f"No text selected or column '{active_column}' not found.")
                 self.disable_navigation_buttons()
                 self.find_replace_matches_df = pd.DataFrame(columns=["Index", "Page", "Match_Number"])
                 self.current_match_position = 0
                 self.update_matches_counter()
                 return # Exit the function

            for index, row in self.main_df.iterrows():
                # No longer need get_active_text_column per row
                # active_column is determined once from the dropdown

                # Check if the determined column exists for safety (might be redundant now)
                if active_column not in row:
                     continue

                text = row[active_column]
                if pd.notna(text) and isinstance(text, str):
                    if self.case_sensitive.get():
                        found_matches = [m.start() for m in re.finditer(re.escape(search_term), text)]
                    else:
                        found_matches = [m.start() for m in re.finditer(re.escape(search_term), text, re.IGNORECASE)]

                    for _ in found_matches:
                        match_counter += 1
                        matches.append({
                            "Index": int(index),
                            "Page": int(row["Index"]),
                            "Match_Number": match_counter
                        })

            if matches:
                self.find_replace_matches_df = pd.DataFrame(matches)
                self.find_replace_matches_df = self.find_replace_matches_df.sort_values(["Page", "Match_Number"])
                self.current_match_position = 0
                self.enable_navigation_buttons()
                self.link_nav = self.find_replace_matches_df.iloc[0]["Index"]
                self.navigate_callback(3)
                self.highlight_text()
            else:
                messagebox.showinfo("No Matches", "No matches found.")
                self.disable_navigation_buttons()
                self.find_replace_matches_df = pd.DataFrame(columns=["Index", "Page", "Match_Number"])
                self.current_match_position = 0

            self.update_matches_counter()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to find matches: {str(e)}")

    def find_all_matches(self):
        """Wrapper for find_matches()."""
        self.find_matches()

    def replace_text(self):
        """Replace the current occurrence of the search term."""
        try:
            search_term = self.search_entry.get().strip()
            replace_term = self.replace_entry.get()
            
            if not search_term:
                messagebox.showwarning("Warning", "Please enter a search term.")
                return

            current_text = self.text_display.get("1.0", tk.END)
            if self.case_sensitive.get():
                pattern = re.compile(re.escape(search_term))
            else:
                pattern = re.compile(re.escape(search_term), re.IGNORECASE)
            
            new_text = pattern.sub(replace_term, current_text)
            
            self.text_display.delete("1.0", tk.END)
            self.text_display.insert("1.0", new_text)
            
            current_page = self.get_page_counter()
            # Get the column name from the main app's dropdown selection
            active_column = self.text_display_var.get()
            # Only update DataFrame if a valid text type is selected
            if active_column != "None" and active_column in self.main_df.columns:
                self.main_df.loc[current_page, active_column] = new_text.strip()
            elif active_column == "None":
                 messagebox.showwarning("Warning", "Cannot save replacement. No text type selected in the main window dropdown.")
            else: # Column not found (should be rare if dropdown is synced)
                 messagebox.showerror("Error", f"Cannot save replacement. Column '{active_column}' not found in data.")

            self.find_matches()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to replace text: {str(e)}")

    def replace_all_text(self):
        """Replace all occurrences of the search term in the document."""
        try:
            if not messagebox.askyesno("Replace All", 
                "Are you sure you want to replace all occurrences? This action cannot be undone."):
                return

            search_term = self.search_entry.get().strip()
            replace_term = self.replace_entry.get()

            if not search_term:
                messagebox.showwarning("Warning", "Please enter a search term.")
                return

            total_replacements = 0
            pages_affected = set()
            
            # Compile pattern with flags
            flags = re.IGNORECASE if not self.case_sensitive.get() else 0
            pattern = re.compile(re.escape(search_term), flags)

            # Get the column name from the main app's dropdown selection ONE time
            active_column = self.text_display_var.get()

            # If "None" is selected or the column doesn't exist, don't replace
            if active_column == "None":
                 messagebox.showwarning("Warning", "Cannot perform Replace All. No text type selected in the main window dropdown.")
                 return
            if active_column not in self.main_df.columns:
                 messagebox.showerror("Error", f"Cannot perform Replace All. Column '{active_column}' not found in data.")
                 return

            for index, row in self.main_df.iterrows():
                # Use the globally determined active_column
                if active_column not in row: # Safety check
                     continue

                text = row[active_column]
                if pd.notna(text) and isinstance(text, str):
                    # Count occurrences using the same pattern
                    occurrences = len(pattern.findall(text))

                    if occurrences > 0:
                        # Use the same pattern for replacement
                        new_text = pattern.sub(replace_term, text)
                        self.main_df.loc[index, active_column] = new_text
                        total_replacements += occurrences
                        pages_affected.add(index)

            current_page = self.get_page_counter()
            # Update the text display IF the current page was affected AND the active_column is valid
            if current_page in pages_affected and active_column != "None" and active_column in self.main_df.columns:
                 self.text_display.delete("1.0", tk.END)
                 self.text_display.insert("1.0", self.main_df.loc[current_page, active_column])

            self.text_display.tag_remove("highlight", "1.0", tk.END)
            self.find_replace_matches_df = pd.DataFrame(columns=["Index", "Page", "Match_Number"])
            self.current_match_position = 0
            self.disable_navigation_buttons()
            self.update_matches_counter()

            messagebox.showinfo("Replace Complete", 
                f"Replaced {total_replacements} occurrence(s) across {len(pages_affected)} page(s).")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to replace all text: {str(e)}")    
    
    def update_main_df(self, new_df):
        """Update the main DataFrame reference."""
        self.main_df = new_df