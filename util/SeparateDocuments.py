# util/SeparateDocuments.py

# This file contains the SeparateDocuments class, which is used to handle
# the document separation for the application.

import os
import pandas as pd
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import re

def format_text_with_line_numbers(text):
    """
    Format text with line numbers for chunking.

    Args:
        text (str): The text to format with line numbers

    Returns:
        tuple: (formatted_text, line_map) where formatted_text has line numbers and
              line_map is a dict mapping line numbers to original text lines
    """
    if not text or not isinstance(text, str) or not text.strip():
        return "", {}

    lines = text.strip().split('\n')
    line_map = {}
    formatted_lines = []

    for i, line in enumerate(lines, 1):
        line_map[i] = line
        formatted_lines.append(f"{i}: {line}")

    formatted_text = '\n'.join(formatted_lines)
    return formatted_text, line_map

def insert_separators_by_line_numbers(original_text, line_numbers_response, line_map, error_logging_func=None):
    """
    Insert document separators based on line numbers from the API response.

    Args:
        original_text (str): The original text without line numbers
        line_numbers_response (str): The API response containing line numbers where separators should be inserted
        line_map (dict): Dictionary mapping line numbers to original text lines
        error_logging_func (callable, optional): Function to use for error logging

    Returns:
        str: Text with document separators inserted
    """
    try:
        # Extract line numbers from the response
        # The response should ideally be just the line numbers, e.g. "4;15;27"
        # or potentially have some validation text like "Line numbers: 4;15;27"

        line_numbers_str = line_numbers_response.strip()

        # Try to isolate the number string if there's a prefix
        if ':' in line_numbers_str:
             # Take the part after the last colon
             parts = line_numbers_str.rsplit(':', 1)
             if len(parts) > 1:
                 line_numbers_str = parts[1].strip()

        # Remove any remaining non-numeric/non-delimiter characters (except spaces for splitting)
        # Allow digits, semicolons, commas, and spaces
        cleaned_numbers_str = re.sub(r'[^\d;, ]', '', line_numbers_str)

        # Split by common delimiters (semicolon, comma, space)
        number_strings = re.split(r'[;, ]+', cleaned_numbers_str)

        line_numbers = []
        for num_str in number_strings:
            num_str_clean = num_str.strip()
            if num_str_clean.isdigit(): # Ensure it's purely digits
                try:
                    num = int(num_str_clean)
                    # Ensure line number is valid within the map
                    if num in line_map:
                        line_numbers.append(num)
                    else:
                        pass

                except ValueError:
                    # This shouldn't happen after isdigit check
                    if error_logging_func:
                        error_logging_func(f"Skipping non-integer value: '{num_str_clean}'", level="WARNING")
                    continue
            elif num_str_clean: # Log if non-empty but not digits
                 if error_logging_func:
                     error_logging_func(f"Skipping non-digit value: '{num_str_clean}'", level="WARNING")


        # Sort line numbers for consistent processing
        line_numbers = sorted(list(set(line_numbers))) # Ensure uniqueness and sort

        if not line_numbers:
            if error_logging_func:
                error_logging_func(f"No valid line numbers found in response: {line_numbers_response}", level="WARNING")
            return original_text # Return original text if no valid numbers found

        # Insert separators
        lines = original_text.split('\n')
        result_lines = []
        inserted_count = 0

        # Iterate through the original lines by their original index (1-based)
        for i, line in enumerate(lines, 1):
             # Insert separator *before* the line number specified by the AI
             if i in line_numbers:
                 # Avoid inserting multiple separators if numbers are consecutive
                 # Or if the previous line was already a separator
                 if not result_lines or result_lines[-1] != "*****":
                     result_lines.append("*****")
                     inserted_count += 1
             result_lines.append(line)

        return '\n'.join(result_lines)

    except Exception as e:
        if error_logging_func:
            error_logging_func(f"Error inserting separators: {str(e)}")
        return original_text # Return original text on error

def apply_document_separation(app):
    """
    Apply document separation based on ***** markers and replace main_df with the compiled documents.
    This function only uses the "keep entire page" method and doesn't modify images.
    
    Args:
        app: The main application instance
    """
    
    if app.main_df.empty:
        messagebox.showinfo("No Documents", "No documents to separate.")
        return
    
    # Check if any text contains the separator
    documents_separated = False
    try:
        # Check if documents are separated with ***** markers
        separator_count = 0
        pages_with_separators = []
        
        for index, row in app.main_df.iterrows():
            text = app.data_operations.find_right_text(index)
            if "*****" in text:
                separator_count += text.count("*****")
                pages_with_separators.append(index)
        
        documents_separated = separator_count > 0
        
        if not documents_separated:
            messagebox.showwarning(
                "Warning", 
                "No document separators ('*****') found. Please add separators to your text first."
            )
            return
    except Exception as e:
        app.error_logging(f"Error checking for document separators: {str(e)}")
        messagebox.showerror("Error", f"Error checking for document separators: {str(e)}")
        return
    
    # Confirm with user
    if not messagebox.askyesno("Warning", 
                               "This will reorganize your documents based on ***** separators.\n\nThis action cannot be undone!\n\nContinue?"):
        return
    
    # Use progress bar
    progress_window, progress_bar, progress_label = app.progress_bar.create_progress_window("Applying Document Separation")
    app.progress_bar.update_progress(0, 100)
    
    try:
        # Import CompileDocuments
        from util.CompileDocuments import CompileDocuments
        analyzer = CompileDocuments(app)
        
        # Get a copy of the original dataframe in case we need to restore it
        original_df = app.main_df.copy()
        
        # Update progress
        app.progress_bar.update_progress(20, 100)
        progress_label.config(text="Compiling documents with separators...")
        
        # Compile documents based on separators
        compiled_df = analyzer.compile_documents(force_recompile=True)
        
        if compiled_df is None or compiled_df.empty:
            raise Exception("No documents were found after separation. Check that your separators are correct.")
        
        # Update progress
        app.progress_bar.update_progress(60, 100)
        progress_label.config(text="Creating new main dataframe...")
        
        # Create a new main_df with the same columns as the original
        new_main_df = pd.DataFrame(columns=app.main_df.columns)
        
        # For each row in compiled_df, create a new row in main_df
        for idx, row in compiled_df.iterrows():
            # Create a new row for the main_df
            new_row = {col: "" for col in app.main_df.columns}
            new_row['Index'] = idx
            new_row['Page'] = f"{idx+1:04d}_p{idx+1:03d}"
            new_row['Original_Text'] = row['Text'] if 'Text' in row and pd.notna(row['Text']) else ""
            new_row['Text_Toggle'] = "Original_Text" if new_row['Original_Text'].strip() else "None"
            
            # Get the original indices that make up this document
            original_indices = row['Original_Index']
            
            # Collect all image paths associated with the original indices
            image_paths = []
            if isinstance(original_indices, list) and original_indices:
                for original_idx in original_indices:
                    if original_idx < len(original_df):
                        path = original_df.loc[original_idx, 'Image_Path']
                        if pd.notna(path) and path not in image_paths:
                            image_paths.append(path)
            
            # Ensure image_paths is a list, even if empty or single item
            if not image_paths:
                # Fallback: try to get the first image path if indices were problematic
                if not original_df.empty:
                     first_path = original_df.loc[0, 'Image_Path']
                     if pd.notna(first_path):
                         image_paths = [first_path]
                     else:
                         image_paths = [] # Store empty list if no path found
                else:
                     image_paths = [] # Store empty list if original_df is empty
            
            # Store the list of image paths
            new_row['Image_Path'] = image_paths
            
            # Copy metadata fields if they exist
            for metadata_field in ['People', 'Places', 'Document_Type', 'Author', 'Correspondent', 
                                   'Creation_Place', 'Correspondent_Place', 'Date', 'Summary']:
                if metadata_field in row and pd.notna(row[metadata_field]) and metadata_field in new_main_df.columns:
                    new_row[metadata_field] = row[metadata_field]
            
            # Add the row to the new main_df
            new_main_df.loc[idx] = new_row
        
        # Update progress
        app.progress_bar.update_progress(80, 100)
        progress_label.config(text="Finalizing changes...")
        
        # Replace the main_df with the new one
        app.main_df = new_main_df
        
        # Reset page counter
        app.page_counter = 0
        
        # Update the display
        app.refresh_display()
        app.counter_update()
        
        # Update progress
        app.progress_bar.update_progress(100, 100)
        
        # Show success message
        messagebox.showinfo("Success", f"Documents have been separated into {len(app.main_df)} entries.")
        
    except Exception as e:
        app.error_logging(f"Error applying document separation: {str(e)}")
        messagebox.showerror("Error", f"Error applying document separation: {str(e)}")
        
    finally:
        # Close progress bar
        app.progress_bar.close_progress_window() 