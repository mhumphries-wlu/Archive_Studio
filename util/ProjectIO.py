# util/ProjectIO.py

# This file contains the ProjectIO class, which is used to handle
# the project save and open functionality for the application.  

import os
import pandas as pd
import fitz  # PyMuPDF
from tkinter import messagebox, filedialog, simpledialog
import traceback

class ProjectIO:
    def __init__(self, app):
        self.app = app  # Reference to main app instance
        
    def create_new_project(self):
        if not messagebox.askyesno("New Project", "Creating a new project will reset the current application state. This action cannot be undone. Are you sure you want to proceed?"):
            return  # User chose not to proceed
        
        # Reset the application
        self.app.reset_application()

        # Enable drag and drop
        self.app.enable_drag_and_drop()

    def save_project(self):
        # ADD: Save current text using DataOperations
        self.app.data_operations.update_df()
        # If no project directory exists, call save_project_as.
        if not hasattr(self.app, 'project_directory') or not self.app.project_directory:
            self.save_project_as()
            return

        try:
            project_name = os.path.basename(self.app.project_directory)
            project_file = os.path.join(self.app.project_directory, f"{project_name}.pbf")

            # Create a copy of the DataFrame to prevent modifying the original
            save_df = self.app.main_df.copy()
            
            # Convert all absolute paths to relative paths
            for idx, row in save_df.iterrows():
                # Convert Image_Path to relative path
                if pd.notna(row['Image_Path']) and str(row['Image_Path']).strip():
                    # Extract the filename from the potentially absolute path stored in the row
                    image_filename = os.path.basename(str(row['Image_Path']))
                    # Construct the expected simple relative path
                    expected_relative_path = os.path.join("images", image_filename)
                    # Store the simple relative path
                    save_df.at[idx, 'Image_Path'] = expected_relative_path

                # Convert Text_Path to relative path if it exists
                if pd.notna(row['Text_Path']) and row['Text_Path']:
                    # Apply the same logic for Text_Path if it's used and needs similar treatment
                    text_filename = os.path.basename(str(row['Text_Path']))
                    # Assuming text files also reside directly in the project root or a specific subdir
                    # Adjust "textfiles" if they are stored elsewhere relative to the project root
                    # If Text_Path should always be relative to the project root directly:
                    expected_text_relative_path = text_filename
                    # If Text_Path is in a subdirectory like 'texts':
                    # expected_text_relative_path = os.path.join("texts", text_filename)
                    save_df.at[idx, 'Text_Path'] = expected_text_relative_path

            # Save the updated DataFrame with relative paths to the project file
            save_df.to_csv(project_file, index=False, encoding='utf-8')

            messagebox.showinfo("Success", f"Project saved successfully to {self.app.project_directory}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project: {e}")
            self.app.error_logging(f"Failed to save project: {e}")

    def open_project(self):
        # ADD: Save current text before opening using DataOperations
        self.app.data_operations.update_df()
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
            # Read and process the project CSV file
            # Use na_filter=False to prevent pandas from interpreting empty strings as NaN
            # Keep_default_na=False might also be useful depending on CSV content
            self.app.main_df = pd.read_csv(project_file, encoding='utf-8', na_filter=False, keep_default_na=False)

            # Ensure required text columns exist...
            for col in ["Original_Text", "Corrected_Text", "Formatted_Text", "Translation", "Separated_Text", "Text_Toggle", "Relevance", "Image_Path"]: # Ensure Image_Path is checked
                if col not in self.app.main_df.columns:
                    self.app.main_df[col] = ""
                else:
                    # Explicitly convert columns that should be string/object, handling potential non-string data gracefully
                    if col in ["Original_Text", "Corrected_Text", "Formatted_Text", "Translation", "Separated_Text", "Text_Toggle", "Relevance", "Image_Path"]:
                        self.app.main_df[col] = self.app.main_df[col].astype('object').fillna('') # Use object and fillna

            # Set project directory before resolving paths
            self.app.project_directory = project_directory
            self.app.images_directory = images_directory

            # Update Text_Toggle for each row to show the highest level of populated text
            for idx, row in self.app.main_df.iterrows():
                # Check text columns in order of priority (highest to lowest)
                if pd.notna(row['Separated_Text']) and str(row['Separated_Text']).strip():
                    self.app.main_df.at[idx, 'Text_Toggle'] = "Separated_Text"
                elif pd.notna(row['Translation']) and str(row['Translation']).strip():
                    self.app.main_df.at[idx, 'Text_Toggle'] = "Translation"
                elif pd.notna(row['Formatted_Text']) and str(row['Formatted_Text']).strip():
                    self.app.main_df.at[idx, 'Text_Toggle'] = "Formatted_Text"
                elif pd.notna(row['Corrected_Text']) and str(row['Corrected_Text']).strip():
                    self.app.main_df.at[idx, 'Text_Toggle'] = "Corrected_Text"
                elif pd.notna(row['Original_Text']) and str(row['Original_Text']).strip():
                    self.app.main_df.at[idx, 'Text_Toggle'] = "Original_Text"
                else:
                    self.app.main_df.at[idx, 'Text_Toggle'] = "None"

            # Initialize highlight toggles based on data presence
            self.initialize_highlight_toggles()

            # Check if any rows have relevance data and show the relevance dropdown if needed
            if 'Relevance' in self.app.main_df.columns:
                has_relevance = self.app.main_df['Relevance'].apply(
                    lambda x: pd.notna(x) and str(x).strip() != ""
                ).any()

                if has_relevance:
                    self.app.show_relevance.set(True)
                    self.app.toggle_relevance_visibility()
                    self.app.error_logging("Enabled relevance dropdown due to existing relevance data")

            # Reset page counter and load the first image and text.
            self.app.page_counter = 0
            if not self.app.main_df.empty:
                # --- Modified Image Loading ---
                image_path_rel = self.app.main_df.loc[0, 'Image_Path']

                # Check if image_path_rel is a valid, non-empty string
                if isinstance(image_path_rel, str) and image_path_rel.strip():
                    self.app.current_image_path = self.app.get_full_path(image_path_rel)
                    # Check if the resolved absolute path exists
                    if self.app.current_image_path and os.path.exists(self.app.current_image_path):
                        try:
                            self.app.image_handler.load_image(self.app.current_image_path)
                        except Exception as img_load_err:
                             # Catch potential errors during image loading itself (e.g., corrupted file)
                             messagebox.showerror("Image Load Error", f"Failed to load image for first page:\n{img_load_err}")
                             self.app.error_logging(f"Error loading first page image {self.app.current_image_path}: {img_load_err}", level="ERROR")
                             self.app.image_display.delete("all") # Clear image display
                             self.app.current_image_path = None
                    else:
                        # Handle case where path is valid string but file doesn't exist
                        self.app.error_logging(f"Image path invalid or file not found for first page: {self.app.current_image_path}", level="WARNING")
                        messagebox.showwarning("File Not Found", f"Image file not found for the first page:\n{self.app.current_image_path}")
                        self.app.image_display.delete("all") # Clear image display
                        self.app.current_image_path = None
                else:
                    # Handle case where Image_Path is empty, NaN, float, or other invalid type
                    self.app.error_logging(f"No valid image path found for the first page in the project. Value was: {image_path_rel} (Type: {type(image_path_rel)})", level="WARNING")
                    self.app.image_display.delete("all") # Clear image display
                    self.app.current_image_path = None
                # --- End Modified Image Loading ---

                # Set text_display_var to match the Text_Toggle for the first page
                if 0 in self.app.main_df.index:
                    current_toggle = self.app.main_df.loc[0, 'Text_Toggle']
                    # Ensure current_toggle is a string before setting
                    self.app.text_display_var.set(str(current_toggle) if pd.notna(current_toggle) else "None")

                self.app.load_text() # Load text regardless of image success
            else:
                # Handle case where DataFrame is empty after loading project file
                self.app.error_logging("Project file loaded, but DataFrame is empty.", level="WARNING")
                self.app.image_display.delete("all")
                self.app.text_display.delete("1.0", tk.END)
                self.app.current_image_path = None

            self.app.counter_update()

            messagebox.showinfo("Success", "Project loaded successfully.")

        except Exception as e:
            # Detailed error logging including traceback
            tb_str = traceback.format_exc()
            messagebox.showerror("Error", f"Failed to open project: {e}")
            self.app.error_logging(f"Failed to open project: {e}\nTraceback:\n{tb_str}", level="CRITICAL")

    def initialize_highlight_toggles(self):
        """Check for existing data in the DataFrame and set highlight toggles accordingly"""
        try:
            if self.app.main_df.empty:
                return
                
            # Turn off all toggles first
            self.app.highlight_names_var.set(False)
            self.app.highlight_places_var.set(False)
            self.app.highlight_changes_var.set(False)
            self.app.highlight_errors_var.set(False)
            
            # Check for People column data
            if 'People' in self.app.main_df.columns:
                has_people = self.app.main_df['People'].apply(
                    lambda x: pd.notna(x) and str(x).strip() != ""
                ).any()
                if has_people:
                    self.app.highlight_names_var.set(True)
                    self.app.error_logging("Enabled Names highlighting due to existing People data")
            
            # Check for Places column data
            if 'Places' in self.app.main_df.columns:
                has_places = self.app.main_df['Places'].apply(
                    lambda x: pd.notna(x) and str(x).strip() != ""
                ).any()
                if has_places:
                    self.app.highlight_places_var.set(True)
                    self.app.error_logging("Enabled Places highlighting due to existing Places data")
            
            # Check for Errors column data
            if 'Errors' in self.app.main_df.columns:
                has_errors = self.app.main_df['Errors'].apply(
                    lambda x: pd.notna(x) and str(x).strip() != ""
                ).any()
                if has_errors:
                    self.app.highlight_errors_var.set(True)
                    self.app.error_logging("Enabled Errors highlighting due to existing Errors data")
            
            # Check for Corrected_Text (enables Changes if Original_Text also exists)
            if 'Corrected_Text' in self.app.main_df.columns and 'Original_Text' in self.app.main_df.columns:
                has_changes = False
                
                # Check if any row has both Original_Text and Corrected_Text
                for _, row in self.app.main_df.iterrows():
                    has_original = pd.notna(row['Original_Text']) and row['Original_Text'].strip() != ""
                    has_Corrected_Text = pd.notna(row['Corrected_Text']) and row['Corrected_Text'].strip() != ""
                    
                    if has_original and has_Corrected_Text:
                        has_changes = True
                        break
                        
                # Also check for Translation or Formatted_Text
                if not has_changes and 'Translation' in self.app.main_df.columns:
                    for _, row in self.app.main_df.iterrows():
                        has_original = pd.notna(row['Original_Text']) and row['Original_Text'].strip() != ""
                        has_translation = pd.notna(row['Translation']) and row['Translation'].strip() != ""
                        
                        if has_original and has_translation:
                            has_changes = True
                            break
                            
                if has_changes:
                    self.app.highlight_changes_var.set(True)
                    self.app.error_logging("Enabled Changes highlighting due to existing draft/translation data")
                    
        except Exception as e:
            self.app.error_logging(f"Error initializing highlight toggles: {e}")
    
    def save_project_as(self):
        # ADD: Save current text before saving as using DataOperations
        self.app.data_operations.update_df()
        # Ask the user to select a parent directory and project name.
        parent_directory = filedialog.askdirectory(title="Select Directory for New Project")
        if not parent_directory:
            return  # User cancelled
        project_name = simpledialog.askstring("Project Name", "Enter a name for the new project:")
        if not project_name or not project_name.strip():
            messagebox.showwarning("Invalid Name", "Project name cannot be empty.")
            return  # User cancelled or provided an empty name

        # Create the project directory and images subfolder.
        project_directory = os.path.join(parent_directory, project_name)
        images_directory = os.path.join(project_directory, "images")
        try:
            # Check if directory exists and is not empty (optional, but safer)
            if os.path.exists(project_directory) and os.listdir(project_directory):
                 if not messagebox.askyesno("Directory Exists", f"The directory '{project_name}' already exists and may contain files. Overwrite or merge? (Choosing 'No' cancels the operation)"):
                     return # User chose not to overwrite/merge

            os.makedirs(project_directory, exist_ok=True)
            os.makedirs(images_directory, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Error", f"Could not create project directories: {e}")
            self.app.error_logging(f"Could not create project directories: {e}")
            return


        # Path for the project file (CSV).
        project_file = os.path.join(project_directory, f"{project_name}.pbf")

        try: # Add try/except around the processing loop and saving
            # Create a copy of the DataFrame to modify paths before saving
            save_df = self.app.main_df.copy()

            # Iterate over each row in the DataFrame (use the copy's index)
            for index in save_df.index: # Use index from the copy
                row = save_df.loc[index] # Get row data from the copy
                image_path_data = row['Image_Path'] # Get the path data (could be string or list)

                source_image_path_to_copy = None # Initialize the single source path we will copy

                # --- Determine the single source image path to copy ---
                if isinstance(image_path_data, list):
                    if image_path_data: # Check if list is not empty
                        # Take the first path from the list
                        potential_path = image_path_data[0]
                        # Ensure the path is a non-empty string
                        if pd.notna(potential_path) and isinstance(potential_path, str) and potential_path.strip():
                            source_image_path_to_copy = str(potential_path) # Ensure string
                        else:
                            self.app.error_logging(f"Warning: First element in Image_Path list for index {index} is invalid or empty. Skipping image copy for this row.", level="WARNING")
                    else:
                        self.app.error_logging(f"Warning: Image_Path list is empty for index {index}. Skipping image copy for this row.", level="WARNING")
                elif pd.notna(image_path_data) and isinstance(image_path_data, str) and image_path_data.strip():
                    # It's a valid single string path
                    source_image_path_to_copy = image_path_data
                else:
                    # Handle NaN, None, empty strings, or unexpected types
                    self.app.error_logging(f"Warning: Invalid or missing Image_Path for index {index}. Type: {type(image_path_data)}. Skipping image copy for this row.", level="WARNING")
                # --- End source path determination ---

                # Define the new image filename and absolute path in the target directory
                new_image_filename = f"{index+1:04d}_p{index+1:03d}.jpg" # Use index from the loop
                new_image_path_abs = os.path.join(images_directory, new_image_filename)
                # Define the relative path to store in the CSV
                rel_image_path_for_csv = os.path.relpath(new_image_path_abs, project_directory)

                if source_image_path_to_copy:
                    # Resolve the selected source path to absolute for reading
                    source_image_path_abs = self.app.get_full_path(source_image_path_to_copy)

                    if source_image_path_abs and os.path.exists(source_image_path_abs):
                        try:
                            # Call via image handler instead:
                            self.app.image_handler.resize_image(source_image_path_abs, new_image_path_abs)
                            # Update the Image_Path in the DataFrame being saved to the *new relative path*
                            save_df.at[index, 'Image_Path'] = rel_image_path_for_csv
                        except Exception as img_err:
                            self.app.error_logging(f"Error processing image for index {index} from {source_image_path_abs} to {new_image_path_abs}: {img_err}", level="ERROR")
                            # Save an empty path in the CSV if image processing fails
                            save_df.at[index, 'Image_Path'] = ""
                    else:
                        self.app.error_logging(f"Warning: Source image file not found for index {index}: {source_image_path_abs}. Saving empty path.", level="WARNING")
                        save_df.at[index, 'Image_Path'] = "" # Save empty path if source not found
                else:
                    # No valid source image path determined, save empty path in CSV
                    save_df.at[index, 'Image_Path'] = ""

                # Text_Path is generally empty/unused now, ensure it's empty in the saved file
                if 'Text_Path' in save_df.columns:
                    save_df.at[index, 'Text_Path'] = ""

            # --- End Loop ---

            # Save the modified DataFrame (now containing single, relative image paths)
            save_df.to_csv(project_file, index=False, encoding='utf-8')

            messagebox.showinfo("Success", f"Project saved successfully to {project_directory}")

            # Update the app's current project directory references ONLY after successful save
            self.app.project_directory = project_directory
            self.app.images_directory = images_directory
            # Optionally, refresh display if needed, though usually not required after save_as
            # self.app.refresh_display()

        except Exception as e: # Catch errors during the loop or saving
            messagebox.showerror("Error", f"Failed to save project as: {e}")
            self.app.error_logging(f"Failed to save project as: {e}")
            # Clean up partially created project directory? Maybe too risky.

    def open_pdf(self, pdf_file=None):
        if pdf_file is None:
            pdf_file = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not pdf_file:
            return

        # Ensure images directory exists (might be temp if no project loaded)
        if not hasattr(self.app, 'images_directory') or not self.app.images_directory:
             self.app.images_directory = os.path.join(self.app.temp_directory, "images")
        os.makedirs(self.app.images_directory, exist_ok=True)

        # Show progress bar immediately
        progress_window, progress_bar, progress_label = self.app.progress_bar.create_progress_window("Processing PDF")
        self.app.progress_bar.update_progress(0, 1)  # Show 0% progress immediately

        try:
            pdf_document = fitz.open(pdf_file)
            total_pages = len(pdf_document)

            # Get the starting index for new entries
            start_index = len(self.app.main_df)

            # Update progress bar with actual total
            self.app.progress_bar.set_total_steps(total_pages) # Use set_total_steps
            self.app.progress_bar.update_progress(0, total_pages) # Update progress to 0, pass total_pages

            new_rows_list = [] # Collect new rows

            for page_num in range(total_pages):
                self.app.progress_bar.update_progress(page_num + 1, total_pages)
                progress_label.config(text=f"Processing page {page_num + 1} of {total_pages}")
                self.app.update_idletasks() # Force UI update

                page = pdf_document[page_num]

                # Extract image at a suitable resolution
                # Using 300 DPI: matrix=fitz.Matrix(300/72, 300/72)
                # Using 150 DPI: matrix=fitz.Matrix(150/72, 150/72) - faster, smaller files
                dpi = 150 # Choose desired DPI
                mat = fitz.Matrix(dpi/72, dpi/72)
                pix = page.get_pixmap(matrix=mat, alpha=False) # alpha=False for JPG

                # Define paths using temp directory first
                temp_image_path = os.path.join(self.app.temp_directory, f"temp_page_{start_index + page_num + 1}.png") # Save as PNG initially for quality
                pix.save(temp_image_path)

                # Calculate new index and page number
                new_index = start_index + page_num
                new_page_num_str = f"{new_index+1:04d}_p{new_index+1:03d}"

                # Define final image path in images directory (could be temp or project)
                image_filename = f"{new_page_num_str}.jpg" # Final is JPG
                image_path_abs = os.path.join(self.app.images_directory, image_filename)

                # Resize/convert PNG temp image to JPG final image
                # self.app.resize_image(temp_image_path, image_path_abs) # resize_image handles conversion and saving as JPG
                # Call via image handler instead:
                self.app.image_handler.resize_image(temp_image_path, image_path_abs)

                # Get relative path for storage (relative to project or temp base)
                image_path_rel = self.app.get_relative_path(image_path_abs)

                # Remove the temporary PNG image
                try:
                     if os.path.exists(temp_image_path):
                         os.remove(temp_image_path)
                except Exception as e_rem:
                     self.app.error_logging(f"Could not remove temp PDF image {temp_image_path}: {e_rem}", level="WARNING")

                # Extract text
                text_content = page.get_text("text") # Use "text" for plain text extraction
                text_path = "" # No separate text file needed

                # Prepare row data
                new_row_data = {
                    "Index": new_index,
                    "Page": new_page_num_str,
                    "Original_Text": text_content if pd.notna(text_content) else "",
                    "Corrected_Text": "",
                    "Formatted_Text": "",
                    "Separated_Text": "",
                    "Translation": "",
                    "Image_Path": image_path_rel, # Store relative path
                    "Text_Path": text_path,
                    "Text_Toggle": "Original_Text" if text_content and text_content.strip() else "None",
                    "Relevance": "",
                     # Add other columns if they exist in main_df, initialized empty
                     **{col: "" for col in self.app.main_df.columns if col not in [
                        "Index", "Page", "Original_Text", "Corrected_Text", "Formatted_Text",
                        "Separated_Text", "Translation", "Image_Path", "Text_Path",
                        "Text_Toggle", "Relevance"
                    ]}
                }
                new_rows_list.append(new_row_data)

            pdf_document.close()

            # Concatenate new rows at once
            if new_rows_list:
                 new_rows_df = pd.DataFrame(new_rows_list)
                 self.app.main_df = pd.concat([self.app.main_df, new_rows_df], ignore_index=True)

            # Navigate to the first newly added page
            if total_pages > 0:
                 self.app.page_counter = start_index
            else: # If PDF was empty
                 self.app.page_counter = max(0, len(self.app.main_df) - 1) # Go to last page or 0

            self.app.refresh_display() # Refresh display for the new page
            self.app.progress_bar.close_progress_window()
            messagebox.showinfo("Success", f"PDF processed successfully. {total_pages} pages added.")

        except Exception as e:
            self.app.progress_bar.close_progress_window()
            messagebox.showerror("Error", f"An error occurred while processing the PDF: {str(e)}")
            self.app.error_logging(f"Error in open_pdf: {str(e)}")
            traceback.print_exc() # Print detailed traceback for debugging

        finally:
             # Clean up any remaining temp files (optional, be careful)
             # for f in os.listdir(self.app.temp_directory):
             #    if f.startswith("temp_page_") and (f.endswith(".png") or f.endswith(".jpg")):
             #        try: os.remove(os.path.join(self.app.temp_directory, f))
             #        except: pass
            self.app.enable_drag_and_drop()