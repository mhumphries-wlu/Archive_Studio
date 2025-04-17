import tkinter as tk
from tkinter import messagebox
import pandas as pd
import os

class NavigationHandler:
    def __init__(self, app):
        self.app = app

    def navigate_images(self, direction):
        """Navigate between main document entries."""
        if self.app.main_df.empty:
            return

        # --- Save current text before navigating ---
        if self.app.page_counter < len(self.app.main_df):
            current_display_val = self.app.main_df.loc[self.app.page_counter, 'Text_Toggle']
            if current_display_val != "None":
                text = self.app.data_operations.clean_text(self.app.text_display.get("1.0", tk.END))
                if current_display_val in ["Original_Text", "Corrected_Text", "Formatted_Text", "Translation", "Separated_Text"]:
                    self.app.main_df.loc[self.app.page_counter, current_display_val] = text
        # --- End Save ---

        # Store the current display type before potentially changing the page
        selected_display = self.app.text_display_var.get()

        # Handle navigation logic
        if abs(direction) == 2:
            if direction < 0: self.app.page_counter = 0
            else: self.app.page_counter = len(self.app.main_df) - 1
        else:
            new_counter = self.app.page_counter + direction
            if new_counter < 0: new_counter = 0
            elif new_counter >= len(self.app.main_df): new_counter = len(self.app.main_df) - 1
            self.app.page_counter = new_counter

        # Reset document page index when moving between main documents
        self.app.current_doc_page_index = 0

        # Refresh display (loads image and text)
        self.app.refresh_display()

        # Ensure Text_Toggle reflects the display *before* navigation if it wasn't 'None'
        # This should be handled by refresh_display/load_text which reads the toggle from df
        # We might need to rethink saving the toggle if refresh logic changes
        # For now, let refresh_display handle setting the toggle based on the *new* page's data

    def counter_update(self):
        """Update the main page counter label."""
        if not hasattr(self.app, 'main_df') or self.app.main_df is None:
             total_images = -1 # No DataFrame loaded
        else:
            total_images = len(self.app.main_df) - 1 # Index is 0-based

        if total_images >= 0:
            self.app.page_counter_var.set(f"{self.app.page_counter + 1} / {total_images + 1}")
        else:
            self.app.page_counter_var.set("0 / 0")

    def find_replace_navigate(self, page_index):
        """Special navigation method called by find/replace functionality."""
        # Note: The find_replace logic might need adjustment to pass the index directly
        # Assuming find_replace sets app.page_counter or provides the target index

        if self.app.main_df.empty:
            return

        # Set the page counter directly from the provided index
        if 0 <= page_index < len(self.app.main_df):
            self.app.page_counter = page_index
        else:
            # Handle invalid index if necessary, e.g., clamp or log error
            self.app.error_logging(f"Invalid page index received from find/replace: {page_index}", level="WARNING")
            if page_index >= len(self.app.main_df):
                self.app.page_counter = len(self.app.main_df) - 1
            else:
                self.app.page_counter = 0 # Default to first page on error

        # Refresh the display for the new page
        self.app.refresh_display() # refresh_display now handles image loading and text loading

        # Re-highlight search terms after text is loaded by refresh_display
        if hasattr(self.app, 'find_replace') and self.app.find_replace.find_replace_toggle:
             # Ensure load_text (called by refresh_display) finishes before highlighting
             self.app.after(50, self.app.find_replace.highlight_text) # Small delay if needed

    def navigate_relevant(self, direction):
        """Navigate to the next/previous relevant or partially relevant document."""
        if self.app.main_df.empty:
            messagebox.showinfo("No Documents", "No documents loaded.")
            return

        if 'Relevance' not in self.app.main_df.columns:
            messagebox.showerror("Error", "Relevance data not found. Run 'Find Relevant Documents' first.")
            return

        target_relevance = ["Relevant", "Partially Relevant"]
        current_index = self.app.page_counter
        total_rows = len(self.app.main_df)

        # Filter for relevant rows and get their indices
        relevant_indices = self.app.main_df[self.app.main_df['Relevance'].isin(target_relevance)].index.tolist()

        if not relevant_indices:
            messagebox.showinfo("Not Found", "No documents marked as Relevant or Partially Relevant.")
            return

        next_index = -1

        if direction == 1: # Forward
            found_after = [idx for idx in relevant_indices if idx > current_index]
            if found_after:
                next_index = found_after[0]
            else:
                next_index = relevant_indices[0] # Wrap around

        elif direction == -1: # Backward
            found_before = [idx for idx in relevant_indices if idx < current_index]
            if found_before:
                next_index = found_before[-1]
            else:
                next_index = relevant_indices[-1] # Wrap around

        if next_index != -1 and next_index != current_index:
            # --- Save current state before navigating ---
            if self.app.page_counter < len(self.app.main_df):
                # Save text
                current_display = self.app.main_df.loc[self.app.page_counter, 'Text_Toggle']
                if current_display != "None":
                    text = self.app.data_operations.clean_text(self.app.text_display.get("1.0", tk.END))
                    if current_display in ["Original_Text", "Corrected_Text", "Formatted_Text", "Translation", "Separated_Text"]:
                        self.app.main_df.loc[self.app.page_counter, current_display] = text
                # Save relevance
                if hasattr(self.app, 'relevance_var') and 'Relevance' in self.app.main_df.columns:
                     self.app.main_df.loc[self.app.page_counter, 'Relevance'] = self.app.relevance_var.get()
            # --- End Save ---

            # Navigate
            self.app.page_counter = next_index
            self.app.refresh_display() # Use refresh_display for consistency
        elif next_index == current_index:
             messagebox.showinfo("Navigation Info", "Already at the only relevant document.")
        # else: # No need for this message if it wraps around
        #    messagebox.showinfo("Not Found", "No other relevant documents found.")

    def document_page_nav(self, direction):
        """Navigate between images within the current document's list."""
        if not isinstance(self.app.current_image_path_list, list) or len(self.app.current_image_path_list) <= 1:
            return

        total_doc_pages = len(self.app.current_image_path_list)
        new_doc_index = self.app.current_doc_page_index

        if abs(direction) == 2: # Double arrow
            if direction < 0: new_doc_index = 0
            else: new_doc_index = total_doc_pages - 1
        else: # Single arrow
            new_doc_index += direction

        # Clamp index
        new_doc_index = max(0, min(new_doc_index, total_doc_pages - 1))

        if new_doc_index != self.app.current_doc_page_index:
            self.app.current_doc_page_index = new_doc_index

            try:
                image_path_to_display = str(self.app.current_image_path_list[self.app.current_doc_page_index])
                image_path_abs = self.app.get_full_path(image_path_to_display)

                if image_path_abs and os.path.exists(image_path_abs):
                    self.app.current_image_path = image_path_abs
                    self.app.image_handler.load_image(self.app.current_image_path) # Use image_handler

                    current_doc_page_num = self.app.current_doc_page_index + 1
                    self.app.doc_page_counter_var.set(f"{current_doc_page_num} / {total_doc_pages}")
                else:
                    messagebox.showerror("Error", f"Image file not found: {image_path_abs or image_path_to_display}")
                    self.app.image_display.delete("all")
                    self.app.current_image_path = None
                    current_doc_page_num = self.app.current_doc_page_index + 1
                    self.app.doc_page_counter_var.set(f"{current_doc_page_num} / {total_doc_pages}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to navigate document page: {str(e)}")
                self.app.error_logging(f"Document page navigation error: {str(e)}")
        # No need to reload text, as text corresponds to the main document (page_counter) 