# util/Highlights.py

# This file contains the HighlightHandler class, which is used to handle
# the highlights for the application.

import tkinter as tk
import pandas as pd
import re
from util.AdvancedDiffHighlighting import highlight_text_differences

class HighlightHandler:
    def __init__(self, app):
        self.app = app
        self.text_display = app.text_display # Direct reference for convenience
        # Configure necessary tags if not already done in App
        # It's better practice to have these configured in the App class where the widget is created,
        # but ensuring they exist here is a fallback.
        try:
            self.text_display.tag_config("name_highlight", background="lightblue")
            self.text_display.tag_config("place_highlight", background="wheat1")
            self.text_display.tag_config("change_highlight", background="lightgreen")
            self.text_display.tag_config("error_highlight", background="cyan")
        except tk.TclError:
             # Handle cases where text_display might not be fully initialized yet or tag exists
             pass
        # Advanced diff might configure its own tags, ensure consistency or pass tag names

    def highlight_names_or_places(self):
        """Highlight names and/or places in the text based on DataFrame data"""
        # Clear existing highlights first
        self.text_display.tag_remove("name_highlight", "1.0", tk.END)
        self.text_display.tag_remove("place_highlight", "1.0", tk.END)

        # If neither highlighting option is selected, return early
        if not self.app.highlight_names_var.get() and not self.app.highlight_places_var.get():
            return

        # Get current page index
        current_index = self.app.page_counter
        if self.app.main_df.empty or current_index >= len(self.app.main_df):
             self.app.error_logging("Invalid index or empty DataFrame for highlighting", level="WARNING")
             return

        try:
            row_data = self.app.main_df.loc[current_index]

            def process_entities(entities_str, tag):

                if pd.isna(entities_str) or not entities_str:
                    return

                # Split, strip, and filter empty strings
                entities = [entity.strip() for entity in entities_str.split(';') if entity.strip()]
                # Sort by length descending to match longer names first
                entities.sort(key=len, reverse=True)


                for entity in entities:
                    # Skip entries with square brackets (often indicating uncertainty or notes)
                    if '[' in entity or ']' in entity:
                        continue

                    # First try to highlight the complete entity
                    self.highlight_term(entity, tag, exact_match=True) # Use exact_match=True for full phrases

                    # Get all text content
                    full_text = self.text_display.get("1.0", tk.END)

                    # Handle hyphenated words across lines
                    if '-' in entity:
                        # Split the entity into parts
                        parts = entity.split('-')

                        # Look for parts separated by newline
                        for i in range(len(parts)-1):
                            part1 = parts[i].strip()
                            part2 = parts[i+1].strip()

                            # Create pattern to match part1 at end of line, optional hyphen, newline(s), and part2 at start of next line
                            # Use re.escape on parts
                            pattern = rf"{re.escape(part1)}-?\n+\s*{re.escape(part2)}" # Allow spaces after newline
                            try:
                                matches = re.finditer(pattern, full_text, re.IGNORECASE)
                            except re.error as re_err:
                                self.app.error_logging(f"Regex error for pattern '{pattern}': {re_err}", level="ERROR")
                                continue # Skip this pattern if invalid

                            for match in matches:
                                # Convert string index to line.char format
                                match_start = match.start()
                                match_end = match.end()

                                # Find the line and character position for start and end
                                start_line, start_char = self._index_to_line_char(full_text, match_start)
                                end_line, end_char = self._index_to_line_char(full_text, match_end)

                                # Add tags to both parts (highlight the whole matched span)
                                start_index = f"{start_line}.{start_char}"
                                end_index = f"{end_line}.{end_char}"

                                self.text_display.tag_add(tag, start_index, end_index)

            # Process names if the highlight names option is checked
            if self.app.highlight_names_var.get():
                names = row_data.get('People', "") # Use .get() for safety
                if pd.notna(names) and names.strip():
                    process_entities(names, "name_highlight")

            # Process places if the highlight places option is checked
            if self.app.highlight_places_var.get():
                places = row_data.get('Places', "") # Use .get() for safety
                if pd.notna(places) and places.strip():
                    process_entities(places, "place_highlight")

        except Exception as e:
            self.app.error_logging(f"Error in highlight_names_or_places: {str(e)}")

    def _index_to_line_char(self, text, index):
        """Convert a flat string index to a Tkinter 'line.char' index."""
        lines_before = text[:index].count('\n')
        line_start_index = text.rfind('\n', 0, index) + 1 if lines_before > 0 else 0
        char_index = index - line_start_index
        return lines_before + 1, char_index

    def highlight_term(self, term, tag, exact_match=False):
        """Helper function to highlight a specific term in the text"""
        if not term or not isinstance(term, str) or len(term) < 1:
            return

        text_widget = self.text_display
        start_index = "1.0"

        # Get full text content for searching
        full_text = text_widget.get("1.0", tk.END)
        if not full_text.strip(): # Skip if text widget is empty
            return

        # Escape special regex characters in the search term
        escaped_term = re.escape(term)

        found_count = 0
        try:
            # Define regex pattern based on exact_match flag
            if exact_match:
                # Look for the term anywhere (might match parts of words if not careful)
                # It's usually better to use boundaries even for "exact" phrase matching
                # Let's refine: use word boundaries unless the term itself starts/ends with non-word chars
                if re.match(r'\w', escaped_term) and re.search(r'\w$', escaped_term):
                     pattern = re.compile(r'\b' + escaped_term + r'\b', re.IGNORECASE)
                else:
                     # If term has leading/trailing non-word chars, don't add boundaries there
                     pattern = re.compile(escaped_term, re.IGNORECASE)

            else:
                # Standard word boundary match for individual words
                pattern = re.compile(r'\b' + escaped_term + r'\b', re.IGNORECASE)


            # Find all matches using the compiled pattern
            for match in pattern.finditer(full_text):
                match_start = match.start()
                match_end = match.end()

                # Convert flat indices to Tkinter line.char format
                start_line, start_char = self._index_to_line_char(full_text, match_start)
                end_line, end_char = self._index_to_line_char(full_text, match_end)

                start_tk_index = f"{start_line}.{start_char}"
                end_tk_index = f"{end_line}.{end_char}"

                # Add the tag to the matched range
                text_widget.tag_add(tag, start_tk_index, end_tk_index)
                found_count += 1

        except re.error as regex_error:
             self.app.error_logging(f"Regex error highlighting term '{term}' with pattern '{pattern.pattern}': {regex_error}", level="ERROR")
        except Exception as e:
            self.app.error_logging(f"Error highlighting term '{term}': {str(e)}", level="ERROR")
            # Fallback using simple text search (less accurate boundaries)
            try:
                current_idx = "1.0"
                fallback_count = 0
                while True:
                    current_idx = text_widget.search(term, current_idx, tk.END, nocase=True, exact=exact_match) # Use exact flag
                    if not current_idx:
                        break
                    end_idx = f"{current_idx}+{len(term)}c"
                    text_widget.tag_add(tag, current_idx, end_idx)
                    current_idx = end_idx
                    fallback_count += 1
                if fallback_count > 0:
                    self.app.error_logging(f"Highlighted {fallback_count} instances using fallback search.", level="WARNING")

            except Exception as inner_e:
                self.app.error_logging(f"Fallback highlighting also failed for '{term}': {str(inner_e)}", level="ERROR")

    def highlight_text(self):
        """Apply all selected types of highlighting based on toggle states"""
        # Clear all existing highlights first
        self.text_display.tag_remove("name_highlight", "1.0", tk.END)
        self.text_display.tag_remove("place_highlight", "1.0", tk.END)
        self.text_display.tag_remove("change_highlight", "1.0", tk.END)
        self.text_display.tag_remove("word_change_highlight", "1.0", tk.END) # Assuming this is from advanced diff
        self.text_display.tag_remove("error_highlight", "1.0", tk.END)

        # Apply each highlight type if its toggle is on
        if self.app.highlight_names_var.get() or self.app.highlight_places_var.get():
            self.highlight_names_or_places()

        if self.app.highlight_changes_var.get():
            self.highlight_changes()

        if self.app.highlight_errors_var.get():
             # Check if we're viewing the text version that the errors apply to
             if not self.app.main_df.empty and self.app.page_counter < len(self.app.main_df):
                 current_display = self.app.text_display_var.get()
                 index = self.app.page_counter
                 row_data = self.app.main_df.loc[index]

                 if 'Errors_Source' in self.app.main_df.columns:
                     errors_source = row_data.get('Errors_Source', "")

                     # Only apply error highlights if viewing the correct text version
                     # or if no specific source is recorded (for backward compatibility)
                     if not errors_source or errors_source == current_display:
                         self.highlight_errors()
                 else:
                     # For backward compatibility or if Errors_Source column doesn't exist
                     self.highlight_errors()
             else:
                 # No data or invalid index, don't highlight errors
                 pass

    def highlight_changes(self):
        """
        Highlight differences between the current text level and the previous level:
        - When viewing Corrected_Text, highlight changes from Original_Text
        - When viewing Formatted_Text, highlight changes from Corrected_Text (or Original if Corrected empty)
        - When viewing Translation, highlight changes from Formatted_Text (or Corrected/Original if others empty)
        """
        if self.app.main_df.empty or self.app.page_counter >= len(self.app.main_df):
             return

        index = self.app.page_counter
        row_data = self.app.main_df.loc[index]
        current_toggle = row_data.get('Text_Toggle', "None")

        current_text = row_data.get(current_toggle, "") if current_toggle != "None" else ""
        previous_text = ""

        # Determine which texts to compare based on current level
        if current_toggle == "Corrected_Text":
            previous_text = row_data.get('Original_Text', "")
        elif current_toggle == "Formatted_Text":
            # Compare Formatted_Text with Corrected_Text first
            previous_text = row_data.get('Corrected_Text', "")
            # If Corrected_Text is empty, compare with Original_Text instead
            if not previous_text or pd.isna(previous_text) or not previous_text.strip():
                previous_text = row_data.get('Original_Text', "")
        elif current_toggle == "Translation":
             # Compare Translation with Formatted_Text first
             previous_text = row_data.get('Formatted_Text', "")
             if not previous_text or pd.isna(previous_text) or not previous_text.strip():
                 previous_text = row_data.get('Corrected_Text', "")
             if not previous_text or pd.isna(previous_text) or not previous_text.strip():
                  previous_text = row_data.get('Original_Text', "")
        elif current_toggle == "Separated_Text":
             # Compare Separated_Text with Formatted_Text first
             previous_text = row_data.get('Formatted_Text', "")
             if not previous_text or pd.isna(previous_text) or not previous_text.strip():
                 previous_text = row_data.get('Corrected_Text', "")
             if not previous_text or pd.isna(previous_text) or not previous_text.strip():
                  previous_text = row_data.get('Original_Text', "")
        else:
            # Cannot compare if Original_Text, None, or unrecognized toggle
            return

        # Ensure texts are strings and not NaN
        current_text = current_text if pd.notna(current_text) else ""
        previous_text = previous_text if pd.notna(previous_text) else ""

        # Skip if either text is effectively empty or they are identical
        if not current_text.strip() or not previous_text.strip() or current_text == previous_text:
            return

        # Use the advanced highlighting function
        try:
             highlight_text_differences(self.text_display, current_text, previous_text)
        except Exception as e:
             self.app.error_logging(f"Error during advanced diff highlighting: {e}")
             # Simple fallback (less precise) - maybe just highlight the whole text?
             # self.text_display.tag_add("change_highlight", "1.0", tk.END)

    def highlight_errors(self):
        """Highlight error terms from the Errors column"""
        if self.app.main_df.empty or self.app.page_counter >= len(self.app.main_df):
             return

        try:

            # Get current page index and data
            index = self.app.page_counter
            row_data = self.app.main_df.loc[index]

            # Get the current text display mode
            selected_display = self.app.text_display_var.get()

            # Get the text version the errors apply to
            errors_source = row_data.get('Errors_Source', "")

            # Check again if we should highlight based on source (redundant but safe)
            if errors_source and errors_source != selected_display:
                return

            # Get errors for current page
            errors_str = row_data.get('Errors', "")
            if pd.isna(errors_str) or not errors_str.strip():
                return

            # Process and highlight errors
            def process_errors(errors_data):
                if not errors_data:
                    return
                # Split errors by semicolon and strip whitespace, filter empty
                error_terms = [term.strip() for term in errors_data.split(';') if term.strip()]
                # Sort by length descending to catch longer phrases first
                error_terms.sort(key=len, reverse=True)
                for term in error_terms:
                    self.highlight_term(term, "error_highlight", exact_match=True) # Use exact_match=True

            process_errors(errors_str)

        except Exception as e:
            self.app.error_logging(f"Error highlighting errors: {str(e)}")


