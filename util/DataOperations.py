# util/DataOperations.py

# This file contains the DataOperations class, which is used to handle
# the data operations for the application.

import os
import pandas as pd
from tkinter import messagebox, END # Added END
import re # Added for apply_collation_dict and natural_sort_key
import shutil # Added for delete_current_image and process_edited_single_image

# Helper function for natural sorting (needed by process_edited_single_image)
def natural_sort_key(s):
    """Sorts strings with numbers in a way humans expect."""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'([0-9]+)', s)]

class DataOperations:
    def __init__(self, app_instance):
        """
        Initialize DataOperations with a reference to the main app.
        
        Args:
            app_instance: The main application instance that contains the DataFrame and utility methods
        """
        self.app = app_instance

    def initialize_main_df(self):
        """Initialize the main DataFrame with appropriate columns and data types"""
        # Define base columns - include all potentially used columns
        all_columns = [
            "Index", "Page",
            "Original_Text", "Corrected_Text", "Formatted_Text", "Translation", "Separated_Text",
            "Image_Path", "Text_Path", "Text_Toggle",
            "People", "Places",
            "Errors", "Errors_Source",
            "Relevance",
            "Document_Type", "Author", "Correspondent", "Correspondent_Place", "Date", "Creation_Place", "Summary",
            # Add any other columns used by AI functions or other parts
            "Document_No", "Citation", "Temp_Data_Analysis", "Data_Analysis", "Query_Data", "Query_Memory", "Notes"
        ]
        # Ensure uniqueness
        all_columns = sorted(list(set(all_columns)))

        self.app.main_df = pd.DataFrame(columns=all_columns)

        # Initialize all text-like columns as empty strings instead of NaN
        text_columns = [col for col in all_columns if col not in ["Index"]] # Assume all non-Index cols can be strings initially
        for col in text_columns:
            if col not in self.app.main_df.columns: # Should not happen with definition above, but safe check
                 self.app.main_df[col] = ""
            self.app.main_df[col] = self.app.main_df[col].astype(str) # Ensure string type

        # Initialize specific types
        self.app.main_df["Index"] = pd.Series(dtype=int)
        # Add specific type handling for other columns if needed (e.g., dates, numbers)
        # Example for Date (if conversion is desired):
        # if "Date" in self.app.main_df.columns:
        #     try:
        #         self.app.main_df["Date"] = pd.to_datetime(self.app.main_df["Date"], errors='coerce')
        #     except Exception as e:
        #          self.app.error_logging(f"Could not convert 'Date' column to datetime during init: {e}", level="WARNING")
        #          self.app.main_df["Date"] = pd.Series(dtype=str) # Fallback

    def parse_names_places_response(self, response):
        """Helper to parse Names/Places responses robustly."""
        names_list = []
        places_list = []
        in_names_section = False
        in_places_section = False

        # Handle potential '\r\n' line endings
        if not isinstance(response, str): # Ensure response is a string
             self.app.error_logging(f"Invalid response type for parsing: {type(response)}", level="WARNING")
             return "", ""
        lines = response.replace('\\r\\n', '\\n').split('\\n')

        for line in lines:
            line_strip = line.strip()
            if not line_strip: continue

            line_lower = line_strip.lower()

            # Check for section headers (allow variations)
            if line_lower.startswith("names:") or line_lower == "names":
                in_names_section = True
                in_places_section = False
                # Extract data if it's on the same line as the header
                if line_lower.startswith("names:") and len(line_strip) > 6:
                    data = line_strip[6:].strip()
                    if data: names_list.extend([n.strip() for n in data.split(';') if n.strip()])
                continue # Move to next line after header

            if line_lower.startswith("places:") or line_lower == "places":
                in_places_section = True
                in_names_section = False
                 # Extract data if it's on the same line as the header
                if line_lower.startswith("places:") and len(line_strip) > 7:
                    data = line_strip[7:].strip()
                    if data: places_list.extend([p.strip() for p in data.split(';') if p.strip()])
                continue # Move to next line after header

            # If we are in a section, add the line content
            if in_names_section:
                # Split potentially semi-colon separated items on the line
                names_list.extend([n.strip() for n in line_strip.split(';') if n.strip()])
            elif in_places_section:
                places_list.extend([p.strip() for p in line_strip.split(';') if p.strip()])

        # Deduplicate and join
        names = "; ".join(sorted(list(set(names_list)), key=str.lower))
        places = "; ".join(sorted(list(set(places_list)), key=str.lower))

        return names, places

    def update_df_with_ai_job_response(self, ai_job, index, response):
        """Update the DataFrame with the AI job response"""
        if self.app.main_df.empty or index >= len(self.app.main_df):
             self.app.error_logging(f"Skipping DF update for invalid index {index}", level="WARNING")
             return

        try:
            if response == "Error" or pd.isna(response): # Handle potential None/NaN response
                self.app.error_logging(f"Received error or empty response for job {ai_job} index {index}", level="WARNING")
                return

            # Clean the response text
            cleaned_response = self.app.clean_text(str(response)) # Ensure it's a string

            # Update based on job type
            target_column = None
            new_toggle = None
            highlight_changes = False
            highlight_names_places = False
            highlight_errors_flag = False

            if ai_job == "HTR":
                target_column = 'Original_Text'
                new_toggle = "Original_Text"
            elif ai_job == "Correct_Text":
                target_column = 'Corrected_Text'
                new_toggle = "Corrected_Text"
                highlight_changes = True
            elif ai_job == "Format_Text":
                 target_column = 'Formatted_Text'
                 new_toggle = "Formatted_Text"
                 highlight_changes = True
            elif ai_job == "Translation":
                 target_column = 'Translation'
                 new_toggle = "Translation"
                 highlight_changes = True
            elif ai_job == "Separated_Text" or ai_job == "Chunk_Text": # Handle chunking results
                 target_column = 'Separated_Text'
                 new_toggle = "Separated_Text"
            elif ai_job == "Get_Names_and_Places":
                # Ensure columns exist
                if 'People' not in self.app.main_df.columns: self.app.main_df['People'] = ""
                if 'Places' not in self.app.main_df.columns: self.app.main_df['Places'] = ""

                # Use robust parsing - NOW CALLS LOCAL METHOD
                names, places = self.parse_names_places_response(cleaned_response)
                self.app.main_df.loc[index, 'People'] = names
                self.app.main_df.loc[index, 'Places'] = places

                if names.strip() or places.strip():
                    highlight_names_places = True
            elif ai_job == "Metadata":
                # Metadata extraction now handled by its own function for complexity
                self.app.ai_functions_handler.extract_metadata_from_response(index, cleaned_response)
                # No direct text toggle change, but may update other columns
            elif ai_job == "Auto_Rotate":
                # Rotation is handled separately by update_image_rotation called within ai_function
                pass
            elif ai_job == "Identify_Errors":
                # Take just the first line if multiple lines exist
                errors = cleaned_response.split('\n')[0].strip()
                # Remove any potential prefix like "Errors:"
                if errors.lower().startswith("errors:"):
                     errors = errors[7:].strip()

                self.app.main_df.loc[index, 'Errors'] = errors

                # Store which version of text the errors apply to
                selected_source = getattr(self.app.ai_functions_handler, 'temp_selected_source', self.app.text_display_var.get())
                self.app.main_df.loc[index, 'Errors_Source'] = selected_source

                if errors:
                    highlight_errors_flag = True

            # Update the target column and toggle if defined
            if target_column:
                self.app.main_df.loc[index, target_column] = cleaned_response
            if new_toggle:
                 self.app.main_df.loc[index, 'Text_Toggle'] = new_toggle
                 # Update display dropdown if this is the current page
                 if index == self.app.page_counter:
                     self.app.text_display_var.set(new_toggle)

            # Set highlight flags
            if highlight_changes: self.app.highlight_changes_var.set(True)
            if highlight_names_places:
                self.app.highlight_names_var.set(bool(self.app.main_df.loc[index, 'People'].strip()))
                self.app.highlight_places_var.set(bool(self.app.main_df.loc[index, 'Places'].strip()))
            if highlight_errors_flag: self.app.highlight_errors_var.set(True)

            # Refresh the display ONLY if the current page was updated
            if index == self.app.page_counter:
                self.app.load_text() # This will re-apply highlights and update menus

        except Exception as e:
            messagebox.showerror("Error", f"Failed to update DataFrame for index {index}: {str(e)}")
            self.app.error_logging(f"Failed to update DataFrame for index {index}: {str(e)}")

    def update_df(self):
        """Explicitly save the currently displayed text to the correct DF column."""
        self.app.save_toggle = False # Assuming this flag indicates unsaved changes

        if not self.app.main_df.empty and self.app.page_counter < len(self.app.main_df):
            current_display = self.app.text_display_var.get()
            if current_display != "None":
                # Access text_display via self.app
                text = self.app.clean_text(self.app.text_display.get("1.0", END))
                if current_display in ["Original_Text", "Corrected_Text", "Formatted_Text", "Translation", "Separated_Text"]:
                    self.app.main_df.loc[self.app.page_counter, current_display] = text

            # Save relevance
            # Access relevance_var via self.app
            if hasattr(self.app, 'relevance_var') and 'Relevance' in self.app.main_df.columns:
                self.app.main_df.loc[self.app.page_counter, 'Relevance'] = self.app.relevance_var.get()

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
        # Access page_counter, main_df, load_text, counter_update, text_display via self.app
        if self.app.page_counter in self.app.main_df.index: # Check if index is valid
            current_page_active_col = self.app.main_df.loc[self.app.page_counter].get('Text_Toggle', None)
            # Find if current page index was modified
            current_text_widget_content = self.app.text_display.get("1.0", END).strip()
            if current_page_active_col in self.app.main_df.columns: # Ensure column exists
                modified_df_content = self.app.main_df.loc[self.app.page_counter, current_page_active_col]
                # Compare cleaned versions to avoid issues with trailing newlines
                if self.app.clean_text(modified_df_content) != self.app.clean_text(current_text_widget_content):
                    self.app.load_text() # Reload text only if current page changed
                    self.app.counter_update()
            else: # If active column somehow doesn't exist, still try to load
                 self.app.load_text()
                 self.app.counter_update()


        messagebox.showinfo("Replacement Complete", f"Replaced variations in {modified_count} page(s).")

    def delete_current_image(self):
        # Access main_df, page_counter, messagebox via self.app
        if self.app.main_df.empty:
            messagebox.showinfo("No Images", "No images to delete.")
            return

        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the current image and its data? This action cannot be undone."):
            return

        try:
            current_index = self.app.page_counter

            # Get file paths (convert relative to absolute)
            image_to_delete_rel = self.app.main_df.loc[current_index, 'Image_Path']
            text_to_delete_rel = self.app.main_df.loc[current_index, 'Text_Path']
            # Access get_full_path, image_handler via self.app
            image_to_delete_abs = self.app.get_full_path(image_to_delete_rel)
            text_to_delete_abs = self.app.get_full_path(text_to_delete_rel)

            # Delete the files from disk using ImageHandler
            self.app.image_handler.delete_image_files(image_to_delete_abs, text_to_delete_abs)

            # Remove the row from the DataFrame
            self.app.main_df = self.app.main_df.drop(current_index).reset_index(drop=True)

            # Renumber the remaining entries and rename files
            for idx in range(len(self.app.main_df)):
                # Update Index
                self.app.main_df.at[idx, 'Index'] = idx

                # Create new page number
                new_page = f"{idx+1:04d}_p{idx+1:03d}"
                self.app.main_df.at[idx, 'Page'] = new_page

                # Get old file paths (relative)
                old_image_path_rel = self.app.main_df.loc[idx, 'Image_Path']
                old_text_path_rel = self.app.main_df.loc[idx, 'Text_Path']

                # Resolve to absolute for renaming
                old_image_path_abs = self.app.get_full_path(old_image_path_rel)
                old_text_path_abs = self.app.get_full_path(old_text_path_rel)

                # Create new file paths (absolute for renaming, then get relative for storage)
                if old_image_path_abs: # Check if path exists
                    image_dir = os.path.dirname(old_image_path_abs)
                    new_image_name = f"{idx+1:04d}_p{idx+1:03d}{os.path.splitext(old_image_path_abs)[1]}"
                    new_image_path_abs = os.path.join(image_dir, new_image_name)
                    # Access get_relative_path via self.app
                    new_image_path_rel = self.app.get_relative_path(new_image_path_abs)
                    # Rename file
                    if os.path.exists(old_image_path_abs) and old_image_path_abs != new_image_path_abs:
                        os.rename(old_image_path_abs, new_image_path_abs)
                    # Update path in DataFrame
                    self.app.main_df.at[idx, 'Image_Path'] = new_image_path_rel

                if old_text_path_abs: # Check if path exists
                    text_dir = os.path.dirname(old_text_path_abs)
                    new_text_name = f"{idx+1:04d}_p{idx+1:03d}.txt"
                    new_text_path_abs = os.path.join(text_dir, new_text_name)
                    new_text_path_rel = self.app.get_relative_path(new_text_path_abs)
                    # Rename file
                    if os.path.exists(old_text_path_abs) and old_text_path_abs != new_text_path_abs:
                        os.rename(old_text_path_abs, new_text_path_abs)
                    # Update path in DataFrame
                    self.app.main_df.at[idx, 'Text_Path'] = new_text_path_rel

            # Adjust page counter if necessary
            if current_index >= len(self.app.main_df) and not self.app.main_df.empty:
                self.app.page_counter = len(self.app.main_df) - 1
            elif self.app.main_df.empty:
                 self.app.page_counter = 0

            # Refresh display
            # Access load_text, text_display, image_display, current_image_path, counter_update via self.app
            if not self.app.main_df.empty:
                # Load the image using image handler
                self.app.image_handler.load_image(self.app.get_full_path(self.app.main_df.loc[self.app.page_counter, 'Image_Path']))
                self.app.load_text()
            else:
                # Clear displays if no images remain
                self.app.text_display.delete("1.0", END)
                self.app.image_display.delete("all")
                self.app.current_image_path = None

            self.app.counter_update()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while deleting the image: {str(e)}")
            # Access error_logging via self.app
            self.app.error_logging(f"Error in delete_current_image: {str(e)}")

    def process_edited_single_image(self, original_image_path_rel):
        """
        Processes images saved by the ImageSplitter for a single-image edit.
        Replaces the original row in the DataFrame with new rows for each edited part,
        renames files, and updates subsequent rows/files.
        """
        try:
            pass_images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "subs", "pass_images") # Path relative to DataOperations.py

            if not os.path.exists(pass_images_dir):
                # Use app's error logging
                self.app.error_logging(f"pass_images directory not found at: {pass_images_dir}", level="ERROR")
                raise FileNotFoundError(f"pass_images directory not found at: {pass_images_dir}")

            # Get edited images and sort them naturally
            edited_images = sorted(
                [f for f in os.listdir(pass_images_dir) if f.lower().endswith((".jpg", ".jpeg"))],
                 key=natural_sort_key # Use helper function
            )

            if not edited_images:
                # This might happen if the user saved without making changes or splits
                messagebox.showinfo("No Changes", "No new image parts were created.")
                # Clean up pass_images directory anyway
                try:
                    for file in os.listdir(pass_images_dir):
                        file_path = os.path.join(pass_images_dir, file)
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                except Exception as e:
                    # Log error using app's logger
                    self.app.error_logging(f"Error cleaning up pass_images directory: {e}", level="ERROR")
                return # Exit without changing DataFrame

            # Use app's page_counter
            current_df_index = self.app.page_counter # The index in the DF being replaced/inserted after
            num_new_images = len(edited_images)

            # --- Prepare New Rows ---
            new_rows = []
            for i, img_file in enumerate(edited_images):
                edited_image_path_abs = os.path.join(pass_images_dir, img_file)

                # Determine the new index in the potentially expanded DataFrame
                # All new rows will be inserted starting at current_df_index
                new_df_index = current_df_index + i

                # Create new sequential filename based on its future position in the DataFrame
                # Note: This assumes the DF will be re-indexed later.
                # Let's use a temporary naming scheme first, then rename after re-indexing.
                # Use app's images_directory
                temp_new_image_name = f"temp_{current_df_index}_{i}.jpg"
                new_image_target_abs = os.path.join(self.app.images_directory, temp_new_image_name)

                # Copy image with temporary name
                shutil.copy2(edited_image_path_abs, new_image_target_abs)
                # Use app's path conversion
                new_image_target_rel = self.app.get_relative_path(new_image_target_abs)


                # Create new row data - Index/Page will be updated after insertion
                new_row = {
                    "Index": -1, # Placeholder index
                    "Page": "",  # Placeholder page
                    "Original_Text": "", "Corrected_Text": "", "Formatted_Text": "",
                    "Translation": "", "Separated_Text": "",
                    "Image_Path": new_image_target_rel, # Relative path to temp named file
                    "Text_Path": "",
                    "Text_Toggle": "None",
                    "People": "", "Places": "", "Errors": "", "Errors_Source": "", "Relevance": ""
                    # Add other columns initialized as empty
                }
                # Ensure all DF columns exist using app's main_df columns
                for col in self.app.main_df.columns:
                     if col not in new_row:
                          new_row[col] = ""
                new_rows.append(new_row)

            # --- Update DataFrame ---
            # Get rows before and after the insertion point using app's main_df
            df_before = self.app.main_df.iloc[:current_df_index]
            df_after = self.app.main_df.iloc[current_df_index+1:] # Skip the row being replaced

            # Concatenate the parts with the new rows and update app's main_df
            self.app.main_df = pd.concat([
                df_before,
                pd.DataFrame(new_rows),
                df_after
            ]).reset_index(drop=True) # Reset index immediately

            # --- Rename Files and Update Paths ---
            # Now that the DataFrame index is final, rename files and update paths
            for i in range(num_new_images):
                 new_final_index = current_df_index + i
                 # Use app's main_df
                 row_to_update = self.app.main_df.loc[new_final_index]

                 old_temp_path_rel = row_to_update['Image_Path']
                 # Use app's path conversion
                 old_temp_path_abs = self.app.get_full_path(old_temp_path_rel)

                 # Define final name and path using app's images_directory
                 final_image_name = f"{new_final_index+1:04d}_p{new_final_index+1:03d}.jpg"
                 final_image_path_abs = os.path.join(self.app.images_directory, final_image_name)
                 # Use app's path conversion
                 final_image_path_rel = self.app.get_relative_path(final_image_path_abs)

                 # Rename the image file
                 if os.path.exists(old_temp_path_abs):
                     os.rename(old_temp_path_abs, final_image_path_abs)
                 else:
                      # Use app's logger
                      self.app.error_logging(f"Temporary image file not found for renaming: {old_temp_path_abs}", level="WARNING")


                 # Update the app's DataFrame with final info
                 self.app.main_df.at[new_final_index, 'Index'] = new_final_index
                 self.app.main_df.at[new_final_index, 'Page'] = f"{new_final_index+1:04d}_p{new_final_index+1:03d}"
                 self.app.main_df.at[new_final_index, 'Image_Path'] = final_image_path_rel


            # Re-number indices and pages for rows *after* the inserted block
            # Use app's main_df
            for idx in range(current_df_index + num_new_images, len(self.app.main_df)):
                 old_page_parts = self.app.main_df.loc[idx, 'Page'].split('_p')
                 old_doc_num = int(old_page_parts[0])
                 # Only update index/page if it's different
                 if self.app.main_df.loc[idx, 'Index'] != idx:
                      self.app.main_df.at[idx, 'Index'] = idx
                      # Update page numbering based on new index
                      new_page_num = f"{idx+1:04d}_p{idx+1:03d}"
                      self.app.main_df.at[idx, 'Page'] = new_page_num

                      # Rename associated image file if needed
                      old_img_path_rel = self.app.main_df.loc[idx, 'Image_Path']
                      # Use app's path conversion
                      old_img_path_abs = self.app.get_full_path(old_img_path_rel)
                      if old_img_path_abs and os.path.exists(old_img_path_abs):
                          img_dir = os.path.dirname(old_img_path_abs)
                          new_img_name = f"{idx+1:04d}_p{idx+1:03d}{os.path.splitext(old_img_path_abs)[1]}"
                          new_img_path_abs = os.path.join(img_dir, new_img_name)
                          # Use app's path conversion
                          new_img_path_rel = self.app.get_relative_path(new_img_path_abs)

                          if old_img_path_abs != new_img_path_abs:
                              try:
                                  os.rename(old_img_path_abs, new_img_path_abs)
                                  self.app.main_df.at[idx, 'Image_Path'] = new_img_path_rel
                              except OSError as rename_err:
                                   # Use app's logger
                                   self.app.error_logging(f"Error renaming image for index {idx}: {rename_err}", level="ERROR")

            # Clean up pass_images directory
            try:
                for file in edited_images: # Use the list we already have
                    file_path = os.path.join(pass_images_dir, file)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
            except Exception as e:
                 # Use app's logger
                 self.app.error_logging(f"Error cleaning up pass_images directory: {e}", level="ERROR")

            # Refresh display to show the first inserted image
            # Use app's page_counter and refresh_display
            self.app.page_counter = current_df_index # Stay at the start of the inserted block
            self.app.refresh_display()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process edited images: {str(e)}")
            # Use app's logger
            self.app.error_logging(f"Process edited image error: {str(e)}")

    def revert_current_page(self):
        # Access main_df, page_counter, text_display_var, messagebox via self.app
        if self.app.main_df.empty or self.app.page_counter >= len(self.app.main_df):
             return

        index = self.app.page_counter
        current_selection = self.app.text_display_var.get()

        revert_options = {
            "Separated_Text": ("Translation", "Remove the separated text and view the Translation?"),
            "Translation": ("Formatted_Text", "Remove the Translation and view the Formatted Text?"),
            "Formatted_Text": ("Corrected_Text", "Remove the Formatted Text and view the Corrected Text?"),
            "Corrected_Text": ("Original_Text", "Remove the Corrected Text and view the Original Text?")
        }

        if current_selection in revert_options:
            target_version, confirmation_msg = revert_options[current_selection]

            if messagebox.askyesno("Revert Text", confirmation_msg):
                # Clear the current version's text
                self.app.main_df.loc[index, current_selection] = ""

                # Find the next best version to display
                fallback_order = ["Separated_Text", "Translation", "Formatted_Text", "Corrected_Text", "Original_Text"]
                next_best_version = "None"
                # Start checking from the target version downwards
                try:
                     start_checking_idx = fallback_order.index(target_version)
                except ValueError:
                     start_checking_idx = len(fallback_order) -1 # Start from Original if target invalid

                for version in fallback_order[start_checking_idx:]:
                     if version in self.app.main_df.columns and pd.notna(self.app.main_df.loc[index, version]) and self.app.main_df.loc[index, version].strip():
                          next_best_version = version
                          break

                # Set the new toggle and variable
                self.app.text_display_var.set(next_best_version)
                self.app.main_df.loc[index, 'Text_Toggle'] = next_best_version
                # Access load_text via self.app
                self.app.load_text() # Reload the display
            else:
                # User cancelled
                return
        elif current_selection == "Original_Text":
            messagebox.showinfo("Original Text",
                            "You are already viewing the Original Text version. Cannot revert further.")
            return
        elif current_selection == "None":
             messagebox.showinfo("No Text", "No text is currently displayed.")
             return
        else:
            # Should not happen if dropdown is managed correctly
             messagebox.showerror("Error", f"Unknown text type selected: {current_selection}")
             return

    def revert_all_pages(self):
        # Access messagebox, main_df, text_display_var, load_text, counter_update via self.app
        if messagebox.askyesno("Confirm Revert All",
                            "Are you sure you want to revert ALL pages to their Original Text?\n\n"
                            "This will permanently remove ALL content in the 'Corrected_Text', 'Formatted_Text', 'Translation', and 'Separated_Text' columns for every page. "
                            "This action cannot be undone."):

            reverted_cols = ['Corrected_Text', 'Formatted_Text', 'Translation', 'Separated_Text']
            for col in reverted_cols:
                 if col in self.app.main_df.columns:
                     self.app.main_df[col] = "" # Clear the entire column

            # Set toggle for all rows to Original_Text if it exists, otherwise None
            if 'Original_Text' in self.app.main_df.columns:
                 self.app.main_df['Text_Toggle'] = "Original_Text"
                 self.app.text_display_var.set("Original_Text")
            else:
                 self.app.main_df['Text_Toggle'] = "None"
                 self.app.text_display_var.set("None")

            self.app.load_text() # Reload current page display
            self.app.counter_update()
            messagebox.showinfo("Revert Complete", "All pages have been reverted to Original Text.")
