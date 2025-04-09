# util/SeparateDocuments.py

# This file contains the SeparateDocuments class, which is used to handle
# the document separation for the application.

import os
import pandas as pd
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

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
            text = app.find_right_text(index)
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