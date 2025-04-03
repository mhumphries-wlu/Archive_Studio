import os
import pandas as pd
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw
from util.process_boxes import process_image_with_bounding_boxes, apply_separation_with_boxes_batched, get_split_images_dir, normalize_coordinates

def create_separation_options_window(app):
    
    """
    Creates a window with options for document separation methods.
    
    Args:
        app: The main application instance
        
    Returns:
        options_window: The created window object
    """
    # Create the window
    options_window = tk.Toplevel(app)
    options_window.title("Document Separation Options")
    options_window.geometry("450x400")  # Increased height to show buttons
    options_window.grab_set()  # Make window modal
    
    # Header message
    header_label = tk.Label(
        options_window,
        text="Select Document Separation Method:",
        font=("Calibri", 12, "bold")
    )
    header_label.pack(pady=(20, 5))
    
    # Description
    description_label = tk.Label(
        options_window,
        text="All methods will separate documents based on ***** markers",
        font=("Calibri", 10)
    )
    description_label.pack(pady=(0, 15))
    
    # Remove the processing mode frame and dropdown
    # Always process by row (hidden from user)
    
    # Option variable
    option_var = tk.IntVar(value=0)
    
    # Options frame
    options_frame = tk.Frame(options_window)
    options_frame.pack(fill="both", expand=True, padx=25, pady=5)
    
    # Option 1: Retain Original Images
    option1 = tk.Radiobutton(
        options_frame,
        text="Retain Original Images",
        variable=option_var,
        value=0,
        font=("Calibri", 11)
    )
    option1.pack(anchor="w", pady=5)
    
    description1 = tk.Label(
        options_frame,
        text="Separate documents but keep using the original images",
        font=("Calibri", 9),
        fg="gray"
    )
    description1.pack(anchor="w", padx=25, pady=(0, 10))
    
    # Option 2: Crop Images
    option2 = tk.Radiobutton(
        options_frame,
        text="Crop Images to Documents (Experimental)",
        variable=option_var,
        value=1,
        font=("Calibri", 11)
    )
    option2.pack(anchor="w", pady=5)
    
    description2 = tk.Label(
        options_frame,
        text="Create cropped images for each separated document",
        font=("Calibri", 9),
        fg="gray"
    )
    description2.pack(anchor="w", padx=25, pady=(0, 10))
    
    # Option 3: Highlight Active Document
    option3 = tk.Radiobutton(
        options_frame,
        text="Highlight Active Document (Experimental)",
        variable=option_var,
        value=2,
        font=("Calibri", 11)
    )
    option3.pack(anchor="w", pady=5)
    
    description3 = tk.Label(
        options_frame,
        text="Create highlighted borders around each document section",
        font=("Calibri", 9),
        fg="gray"
    )
    description3.pack(anchor="w", padx=25, pady=(0, 10))
    
    # Buttons frame
    button_frame = tk.Frame(options_window)
    button_frame.pack(fill="x", side="bottom", pady=20)
    
    # Function to handle the Apply button
    def on_apply():
        option = option_var.get()
        options_window.destroy()
        
        if option == 0:
            # Option 1: Apply regular separation (retain original images)
            apply_document_separation(app)
        elif option == 1:
            # Option 2: Apply separation with cropped images
            # Always use By Row separation
            apply_document_separation_with_boxes_by_row(app)
        elif option == 2:
            # Option 3: Apply separation with highlighted images
            # Always use By Row separation
            apply_document_separation_with_highlights_by_row(app)
    
    # Function to handle Cancel button
    def on_cancel():
        options_window.destroy()
    
    # Create buttons
    apply_button = tk.Button(button_frame, text="Apply", command=on_apply, width=10)
    apply_button.pack(side="left", padx=10)
    
    cancel_button = tk.Button(button_frame, text="Cancel", command=on_cancel, width=10)
    cancel_button.pack(side="left", padx=10)
    
    # Center the window on the screen
    options_window.update_idletasks()
    width = options_window.winfo_width()
    height = options_window.winfo_height()
    x = (options_window.winfo_screenwidth() // 2) - (width // 2)
    y = (options_window.winfo_screenheight() // 2) - (height // 2)
    options_window.geometry(f'{width}x{height}+{x}+{y}')
    
    # Return the window object
    return options_window

def check_google_api_key(app):
    """Check if Google API key is set and valid"""
    if not hasattr(app, 'settings') or not hasattr(app.settings, 'google_api_key'):
        messagebox.showerror("Missing API Key", "Google API key not found in settings.")
        return False
        
    if not app.settings.google_api_key:
        messagebox.showerror("Missing API Key", 
            "Google API key is empty. Please set your Google API key in Settings > API Keys.")
        return False
        
    return True

def apply_document_separation(app):
    """Apply document separation based on ***** markers and replace main_df with the compiled documents."""
    
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
    if not messagebox.askyesno("Confirm Separation", 
                               "This will reorganize your documents based on ***** separators. Continue?"):
        return
    
    # Use progress bar
    progress_window, progress_bar, progress_label = app.progress_bar.create_progress_window("Applying Document Separation")
    app.progress_bar.update_progress(0, 100)
    
    try:
        # Import AnalyzeDocuments
        from util.AnalyzeDocuments import AnalyzeDocuments
        analyzer = AnalyzeDocuments(app)
        
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

def apply_document_separation_with_boxes(app):
    """
    Apply document separation based on ***** markers, replace main_df with compiled documents,
    and create separate images for each section based on bounding boxes.
    """
    
    if app.main_df.empty:
        messagebox.showinfo("No Documents", "No documents to separate.")
        return
    
    # Check if project directory exists
    if not hasattr(app, 'project_directory') or not app.project_directory:
        if messagebox.askyesno("Save Project", "To create cropped images, you need to save the project first. Would you like to save your project now?"):
            app.project_io.save_project()
        else:
            messagebox.showinfo("Operation Cancelled", "Document separation with boxes was cancelled.")
            return
            
    # Check again after potential save
    if not hasattr(app, 'project_directory') or not app.project_directory:
        messagebox.showinfo("Operation Cancelled", "Document separation with boxes was cancelled.")
        return
    
    # Check if Google API key is set
    if not check_google_api_key(app):
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
    if not messagebox.askyesno("Confirm Separation", 
                               "This will reorganize your documents based on ***** separators and create cropped images. Continue?"):
        return
    
    # Use progress bar
    progress_window, progress_bar, progress_label = app.progress_bar.create_progress_window("Applying Document Separation with Bounding Boxes")
    app.progress_bar.update_progress(0, 100)
    
    try:
        # Import AnalyzeDocuments
        from util.AnalyzeDocuments import AnalyzeDocuments
        analyzer = AnalyzeDocuments(app)
        
        # Get a copy of the original dataframe in case we need to restore it
        original_df = app.main_df.copy()
        
        # Update progress
        app.progress_bar.update_progress(10, 100)
        progress_label.config(text="Processing images with bounding boxes...")
        
        # Get the settings from the app
        settings = app.settings
        
        # Process images in batches
        image_to_boxes_map = {}
        
        # Create split_images directory in the project directory
        from util.process_boxes import get_split_images_dir
        split_images_dir = get_split_images_dir(app)
        os.makedirs(split_images_dir, exist_ok=True)
        
        # Process all images in batches
        try:
            
            # Process all images in parallel batches
            batch_results = apply_separation_with_boxes_batched(app)
            
            # Convert the results to our expected format
            for image_path, boxes in batch_results.items():
                # Find the relative path version used in the dataframe
                for img in original_df['Image_Path'].unique():
                    if pd.notna(img) and img and (img in image_path or (hasattr(app, 'get_full_path') and app.get_full_path(img) == image_path)):
                        image_to_boxes_map[img] = boxes
                        break
            
            
        except Exception as e:
            app.error_logging(f"Error in batched processing: {str(e)}")
            print(f"ERROR in batched processing: {str(e)}")
            # Continue with compilation even if image processing failed
        
        # Update progress
        app.progress_bar.update_progress(40, 100)
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
            
            # Get the original indices that make up this document
            original_indices = row['Original_Index']
            
            # Collect all original image paths associated with the indices
            original_image_paths = []
            if isinstance(original_indices, list) and original_indices:
                for original_idx in original_indices:
                    if original_idx < len(original_df):
                        path = original_df.loc[original_idx, 'Image_Path']
                        if pd.notna(path) and path not in original_image_paths:
                            original_image_paths.append(path)
            
            # Ensure we have at least one path if possible
            if not original_image_paths and not original_df.empty:
                first_path = original_df.loc[0, 'Image_Path']
                if pd.notna(first_path):
                    original_image_paths = [first_path]
            
            # Create a new row for the main_df
            new_row = {col: "" for col in app.main_df.columns}
            new_row['Index'] = idx
            new_row['Page'] = f"{idx+1:04d}_p{idx+1:03d}"
            new_row['Original_Text'] = row['Text'] if 'Text' in row and pd.notna(row['Text']) else ""
            new_row['Text_Toggle'] = "Original_Text" if new_row['Original_Text'].strip() else "None"
            
            # Update progress occasionally
            if idx % 10 == 0:
                progress_bar.step(2)
                progress_label.config(text=f"Processing document {idx+1} of {len(compiled_df)}...")
            
            # Determine the final image paths (cropped or original)
            final_image_paths = []
            processed_row_info = batch_results.get(idx) # Get processed info for this compiled row index

            if processed_row_info and 'box_2d' in processed_row_info:
                box_data = processed_row_info
                box_coords = box_data['box_2d']
                # Use the first original image path for cropping reference
                image_path_for_cropping = original_image_paths[0] if original_image_paths else None

                if image_path_for_cropping:
                    full_image_path = image_path_for_cropping
                    if not os.path.isabs(full_image_path) and hasattr(app, 'get_full_path'):
                         full_image_path = app.get_full_path(full_image_path)

                    # Generate output path for cropped image
                    image_basename = os.path.splitext(os.path.basename(full_image_path))[0]
                    output_path = os.path.join(split_images_dir, f"{image_basename}_doc_{idx+1}.jpg")
                    
                    try:
                        # Crop and save the image
                        cropped_image_path = crop_image(full_image_path, box_coords, output_path)
                        final_image_paths = [cropped_image_path] # Store as a list
                    except Exception as e:
                        app.error_logging(f"Error cropping image for row {idx}: {str(e)}")
                        final_image_paths = original_image_paths # Fallback to original paths list
                else:
                     final_image_paths = original_image_paths # Fallback if no ref path
            else:
                # No box found or not processed, use the original image paths
                final_image_paths = original_image_paths

            # Store the final list of image paths
            new_row['Image_Path'] = final_image_paths

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
        messagebox.showinfo("Success", f"Documents have been separated into {len(app.main_df)} entries with corresponding images.")
        
    except Exception as e:
        app.error_logging(f"Error applying document separation with boxes: {str(e)}")
        print(f"ERROR applying document separation with boxes: {str(e)}")
        messagebox.showerror("Error", f"Error applying document separation with boxes: {str(e)}")
        
    finally:
        # Close progress bar
        app.progress_bar.close_progress_window()

def apply_document_separation_with_highlights(app):
    """
    Apply document separation based on ***** markers, replace main_df with compiled documents,
    and create highlighted images showing the boundaries of each document section.
    """
    
    if app.main_df.empty:
        messagebox.showinfo("No Documents", "No documents to separate.")
        return
    
    # Check if project directory exists
    if not hasattr(app, 'project_directory') or not app.project_directory:
        if messagebox.askyesno("Save Project", "To create highlighted images, you need to save the project first. Would you like to save your project now?"):
            app.project_io.save_project()
        else:
            messagebox.showinfo("Operation Cancelled", "Document separation with highlighting was cancelled.")
            return
            
    # Check again after potential save
    if not hasattr(app, 'project_directory') or not app.project_directory:
        messagebox.showinfo("Operation Cancelled", "Document separation with highlighting was cancelled.")
        return
    
    # Check if Google API key is set
    if not check_google_api_key(app):
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
    if not messagebox.askyesno("Confirm Separation", 
                               "This will reorganize your documents based on ***** separators and create highlighted images. Continue?"):
        return
    
    # Use progress bar
    progress_window, progress_bar, progress_label = app.progress_bar.create_progress_window("Applying Document Separation with Highlighting")
    app.progress_bar.update_progress(0, 100)
    
    try:
        # Import AnalyzeDocuments
        from util.AnalyzeDocuments import AnalyzeDocuments
        analyzer = AnalyzeDocuments(app)
        
        # Get a copy of the original dataframe in case we need to restore it
        original_df = app.main_df.copy()
        
        # Update progress
        app.progress_bar.update_progress(10, 100)
        progress_label.config(text="Processing images with highlighting...")
        
        # Get the settings from the app
        settings = app.settings
        
        # Process images in batches
        image_to_boxes_map = {}
        
        # Create split_images directory in the project directory
        split_images_dir = get_split_images_dir(app)
        os.makedirs(split_images_dir, exist_ok=True)
        
        # Process all images in batches
        try:
            print(f"Starting batched processing of images...")
            
            # Process all images in parallel batches
            batch_results = apply_separation_with_boxes_batched(app)
            
            # Convert the results to our expected format
            for image_path, boxes in batch_results.items():
                # Find the relative path version used in the dataframe
                for img in original_df['Image_Path'].unique():
                    if pd.notna(img) and img and (img in image_path or (hasattr(app, 'get_full_path') and app.get_full_path(img) == image_path)):
                        image_to_boxes_map[img] = boxes
                        print(f"Mapped {len(boxes)} boxes to image: {img}")
                        break
            
            print(f"Completed batched processing: {len(image_to_boxes_map)} images with boxes")
            
        except Exception as e:
            app.error_logging(f"Error in batched processing: {str(e)}")
            print(f"ERROR in batched processing: {str(e)}")
            # Continue with compilation even if image processing failed
        
        # Update progress
        app.progress_bar.update_progress(40, 100)
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
            
            # Get the original indices that make up this document
            original_indices = row['Original_Index']
            
            # Collect all original image paths associated with the indices
            original_image_paths = []
            if isinstance(original_indices, list) and original_indices:
                for original_idx in original_indices:
                    if original_idx < len(original_df):
                        path = original_df.loc[original_idx, 'Image_Path']
                        if pd.notna(path) and path not in original_image_paths:
                            original_image_paths.append(path)
            
            # Ensure we have at least one path if possible
            if not original_image_paths and not original_df.empty:
                first_path = original_df.loc[0, 'Image_Path']
                if pd.notna(first_path):
                    original_image_paths = [first_path]
            
            # Create a new row for the main_df
            new_row = {col: "" for col in app.main_df.columns}
            new_row['Index'] = idx
            new_row['Page'] = f"{idx+1:04d}_p{idx+1:03d}"
            new_row['Original_Text'] = row['Text'] if 'Text' in row and pd.notna(row['Text']) else ""
            new_row['Text_Toggle'] = "Original_Text" if new_row['Original_Text'].strip() else "None"
            
            # Update progress occasionally
            if idx % 10 == 0:
                progress_bar.step(2)
                progress_label.config(text=f"Processing document {idx+1} of {len(compiled_df)}...")
            
            # Determine the final image paths (highlighted or original)
            final_image_paths = []
            processed_row_info = batch_results.get(idx) # Get processed info for this compiled row index

            if processed_row_info and 'box_2d' in processed_row_info:
                box_data = processed_row_info
                # Use the first original image path for highlighting reference
                image_path_for_highlighting = original_image_paths[0] if original_image_paths else None

                if image_path_for_highlighting:
                    full_image_path = image_path_for_highlighting
                    if not os.path.isabs(full_image_path) and hasattr(app, 'get_full_path'):
                         full_image_path = app.get_full_path(full_image_path)

                    # Generate a unique name for this document's highlighted image
                    image_basename = os.path.splitext(os.path.basename(full_image_path))[0]
                    highlighted_image_path = os.path.join(split_images_dir, f"{image_basename}_doc_{idx+1}_highlighted.jpg")
                    
                    try:
                        # Create highlighted image
                        highlight_image(full_image_path, box_data, highlighted_image_path)
                        final_image_paths = [highlighted_image_path] # Store as a list
                    except Exception as e:
                        app.error_logging(f"Error highlighting image for row {idx}: {str(e)}")
                        final_image_paths = original_image_paths # Fallback to original paths list
                else:
                     final_image_paths = original_image_paths # Fallback if no ref path
            else:
                # No box found or not processed, use the original image paths
                final_image_paths = original_image_paths
                
            # Store the final list of image paths
            new_row['Image_Path'] = final_image_paths
            
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
        messagebox.showinfo("Success", f"Documents have been separated into {len(app.main_df)} entries with highlighted images.")
        
    except Exception as e:
        app.error_logging(f"Error applying document separation with highlighting: {str(e)}")
        print(f"ERROR applying document separation with highlighting: {str(e)}")
        messagebox.showerror("Error", f"Error applying document separation with highlighting: {str(e)}")
        
    finally:
        # Close progress bar
        app.progress_bar.close_progress_window()

def highlight_image(image_path, box_data, output_path):
    """
    Draw blue border lines on an image based on a single bounding box.
    
    Args:
        image_path: Path to the original image
        box_data: Dictionary with 'box_2d' and 'label' keys for a single box
        output_path: Path to save the highlighted image
        
    Returns:
        Path to the saved highlighted image
    """
    try:
        
        # Open the image
        img = Image.open(image_path)
        img_width, img_height = img.size
        
        # Make a copy of the image to draw on
        draw_img = img.copy()
        
        # Create a drawing object
        draw = ImageDraw.Draw(draw_img)
        
        # Define border color - using a more vibrant blue color for better visibility
        border_color = (0, 50, 255)  # Brighter blue color
        
        # Get box coordinates
        box_coords = box_data['box_2d']
        
        # Normalize coordinates (adds buffer and extends horizontally)
        x_min, y_min, x_max, y_max = normalize_coordinates(box_coords, img_width, img_height)
        
        # Draw thicker border lines
        line_width = 5
        
        # Top line
        draw.line([(x_min, y_min), (x_max, y_min)], fill=border_color, width=line_width)
        
        # Bottom line
        draw.line([(x_min, y_max), (x_max, y_max)], fill=border_color, width=line_width)
        
        # Left line (adding vertical lines for better visibility)
        draw.line([(x_min, y_min), (x_min, y_max)], fill=border_color, width=line_width)
        
        # Right line
        draw.line([(x_max, y_min), (x_max, y_max)], fill=border_color, width=line_width)
        
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the highlighted image
        draw_img.save(output_path)
        
        return output_path
    
    except Exception as e:
        print(f"Error highlighting image: {e}")
        raise

def _calculate_overlap(text1, text2):
    """Calculate the overlap ratio between two text strings"""
    # Normalize the texts
    text1 = text1.strip().lower()
    text2 = text2.strip().lower()
    
    # If either text is empty, return 0
    if not text1 or not text2:
        return 0
        
    # Split into words
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    # Calculate overlap
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    if not union:
        return 0
        
    return len(intersection) / len(union) 

def apply_document_separation_with_boxes_by_row(app):
    """
    Apply document separation with bounding boxes, processing by row.
    This variant separates documents based on ***** markers and creates separate images for each section.
    """
    
    if app.main_df.empty:
        messagebox.showinfo("No Documents", "No documents to separate.")
        return
    
    # Check if project directory exists
    if not hasattr(app, 'project_directory') or not app.project_directory:
        if messagebox.askyesno("Save Project", "To create cropped images, you need to save the project first. Would you like to save your project now?"):
            app.project_io.save_project()
        else:
            messagebox.showinfo("Operation Cancelled", "Document separation with boxes was cancelled.")
            return
            
    # Check again after potential save
    if not hasattr(app, 'project_directory') or not app.project_directory:
        messagebox.showinfo("Operation Cancelled", "Document separation with boxes was cancelled.")
        return
    
    # Check if Google API key is set
    if not check_google_api_key(app):
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
    if not messagebox.askyesno("Confirm Separation", 
                               "This will reorganize your documents based on ***** separators and create cropped images for each row. Continue?"):
        return
    
    # Use progress bar
    progress_window, progress_bar, progress_label = app.progress_bar.create_progress_window("Applying Document Separation with Row-Based Bounding Boxes")
    app.progress_bar.update_progress(0, 100)
    
    try:
        # Import AnalyzeDocuments
        from util.AnalyzeDocuments import AnalyzeDocuments
        analyzer = AnalyzeDocuments(app)
        
        # Get a copy of the original dataframe in case we need to restore it
        original_df = app.main_df.copy()
        
        # Update progress
        app.progress_bar.update_progress(10, 100)
        progress_label.config(text="Compiling documents with separators...")
        
        # Compile documents based on separators
        compiled_df = analyzer.compile_documents(force_recompile=True)
        
        if compiled_df is None or compiled_df.empty:
            raise Exception("No documents were found after separation. Check that your separators are correct.")
        
        # Create split_images directory in the project directory
        split_images_dir = get_split_images_dir(app)
        os.makedirs(split_images_dir, exist_ok=True)
        
        # Update progress
        app.progress_bar.update_progress(30, 100)
        progress_label.config(text="Processing rows in batches...")
        
        # Process all rows in batches
        from util.process_boxes import apply_separation_with_boxes_by_row_batched, crop_image
        
        # Get batch results - dictionary mapping row indices to bounding boxes
        batch_results = apply_separation_with_boxes_by_row_batched(app, compiled_df, original_df)
        
        # Update progress
        app.progress_bar.update_progress(60, 100)
        progress_label.config(text="Creating new main dataframe...")
        
        # Create a new main_df with the same columns as the original
        new_main_df = pd.DataFrame(columns=app.main_df.columns)
        
        # For each row in compiled_df, create a new row in main_df
        for idx, row in compiled_df.iterrows():
            
            # Get the original indices that make up this document
            original_indices = row['Original_Index']
            
            # Collect all original image paths associated with the indices
            original_image_paths = []
            if isinstance(original_indices, list) and original_indices:
                for original_idx in original_indices:
                    if original_idx < len(original_df):
                        path = original_df.loc[original_idx, 'Image_Path']
                        if pd.notna(path) and path not in original_image_paths:
                            original_image_paths.append(path)
            
            # Ensure we have at least one path if possible
            if not original_image_paths and not original_df.empty:
                first_path = original_df.loc[0, 'Image_Path']
                if pd.notna(first_path):
                    original_image_paths = [first_path]
            
            # Create a new row for the main_df
            new_row = {col: "" for col in app.main_df.columns}
            new_row['Index'] = idx
            new_row['Page'] = f"{idx+1:04d}_p{idx+1:03d}"
            new_row['Original_Text'] = row['Text'] if 'Text' in row and pd.notna(row['Text']) else ""
            new_row['Text_Toggle'] = "Original_Text" if new_row['Original_Text'].strip() else "None"
            
            # Update progress occasionally
            if idx % 10 == 0:
                progress_bar.step(2)
                progress_label.config(text=f"Processing document {idx+1} of {len(compiled_df)}...")
            
            # Determine the final image paths (cropped or original)
            final_image_paths = []
            processed_row_info = batch_results.get(idx) # Get processed info for this compiled row index

            if processed_row_info and 'box_2d' in processed_row_info:
                box_data = processed_row_info
                box_coords = box_data['box_2d']
                # Use the first original image path for cropping reference
                image_path_for_cropping = original_image_paths[0] if original_image_paths else None

                if image_path_for_cropping:
                    full_image_path = image_path_for_cropping
                    if not os.path.isabs(full_image_path) and hasattr(app, 'get_full_path'):
                         full_image_path = app.get_full_path(full_image_path)

                    # Generate output path for cropped image
                    image_basename = os.path.splitext(os.path.basename(full_image_path))[0]
                    output_path = os.path.join(split_images_dir, f"{image_basename}_doc_{idx+1}.jpg")
                    
                    try:
                        # Crop and save the image
                        cropped_image_path = crop_image(full_image_path, box_coords, output_path)
                        final_image_paths = [cropped_image_path] # Store as a list
                    except Exception as e:
                        app.error_logging(f"Error cropping image for row {idx}: {str(e)}")
                        final_image_paths = original_image_paths # Fallback to original paths list
                else:
                     final_image_paths = original_image_paths # Fallback if no ref path
            else:
                # No box found or not processed, use the original image paths
                final_image_paths = original_image_paths

            # Store the final list of image paths
            new_row['Image_Path'] = final_image_paths

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
        messagebox.showinfo("Success", f"Documents have been separated into {len(app.main_df)} entries with cropped images for each row.")
        
    except Exception as e:
        app.error_logging(f"Error applying document separation with row-based boxes: {str(e)}")
        print(f"ERROR applying document separation with row-based boxes: {str(e)}")
        messagebox.showerror("Error", f"Error applying document separation with row-based boxes: {str(e)}")
        
    finally:
        # Close progress bar
        app.progress_bar.close_progress_window()

def apply_document_separation_with_highlights_by_row(app):
    """
    Apply document separation with highlights, processing by row.
    This variant separates documents based on ***** markers and creates highlighted images for each section.
    """
    
    if app.main_df.empty:
        messagebox.showinfo("No Documents", "No documents to separate.")
        return
    
    # Check if project directory exists
    if not hasattr(app, 'project_directory') or not app.project_directory:
        if messagebox.askyesno("Save Project", "To create highlighted images, you need to save the project first. Would you like to save your project now?"):
            app.project_io.save_project()
        else:
            messagebox.showinfo("Operation Cancelled", "Document separation with highlighting was cancelled.")
            return
            
    # Check again after potential save
    if not hasattr(app, 'project_directory') or not app.project_directory:
        messagebox.showinfo("Operation Cancelled", "Document separation with highlighting was cancelled.")
        return
    
    # Check if Google API key is set
    if not check_google_api_key(app):
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
    if not messagebox.askyesno("Confirm Separation", 
                               "This will reorganize your documents based on ***** separators and create highlighted images for each row. Continue?"):
        return
    
    # Use progress bar
    progress_window, progress_bar, progress_label = app.progress_bar.create_progress_window("Applying Document Separation with Row-Based Highlighting")
    app.progress_bar.update_progress(0, 100)
    
    try:
        # Import AnalyzeDocuments
        from util.AnalyzeDocuments import AnalyzeDocuments
        analyzer = AnalyzeDocuments(app)
        
        # Get a copy of the original dataframe in case we need to restore it
        original_df = app.main_df.copy()
        
        # Update progress
        app.progress_bar.update_progress(10, 100)
        progress_label.config(text="Compiling documents with separators...")
        
        # Compile documents based on separators
        compiled_df = analyzer.compile_documents(force_recompile=True)
        
        if compiled_df is None or compiled_df.empty:
            raise Exception("No documents were found after separation. Check that your separators are correct.")
        
        # Create split_images directory in the project directory
        split_images_dir = get_split_images_dir(app)
        os.makedirs(split_images_dir, exist_ok=True)
        
        # Update progress
        app.progress_bar.update_progress(30, 100)
        progress_label.config(text="Processing rows in batches...")
        
        # Process all rows in batches
        from util.process_boxes import apply_separation_with_boxes_by_row_batched
        
        # Get batch results - dictionary mapping row indices to bounding boxes
        batch_results = apply_separation_with_boxes_by_row_batched(app, compiled_df, original_df)
        
        # Update progress
        app.progress_bar.update_progress(60, 100)
        progress_label.config(text="Creating new main dataframe...")
        
        # Create a new main_df with the same columns as the original
        new_main_df = pd.DataFrame(columns=app.main_df.columns)
        
        # For each row in compiled_df, create a new row in main_df
        for idx, row in compiled_df.iterrows():
            
            # Get the original indices that make up this document
            original_indices = row['Original_Index']
            
            # Collect all original image paths associated with the indices
            original_image_paths = []
            if isinstance(original_indices, list) and original_indices:
                for original_idx in original_indices:
                    if original_idx < len(original_df):
                        path = original_df.loc[original_idx, 'Image_Path']
                        if pd.notna(path) and path not in original_image_paths:
                            original_image_paths.append(path)
            
            # Ensure we have at least one path if possible
            if not original_image_paths and not original_df.empty:
                first_path = original_df.loc[0, 'Image_Path']
                if pd.notna(first_path):
                    original_image_paths = [first_path]
            
            # Create a new row for the main_df
            new_row = {col: "" for col in app.main_df.columns}
            new_row['Index'] = idx
            new_row['Page'] = f"{idx+1:04d}_p{idx+1:03d}"
            new_row['Original_Text'] = row['Text'] if 'Text' in row and pd.notna(row['Text']) else ""
            new_row['Text_Toggle'] = "Original_Text" if new_row['Original_Text'].strip() else "None"
            
            # Update progress occasionally
            if idx % 10 == 0:
                progress_bar.step(2)
                progress_label.config(text=f"Processing document {idx+1} of {len(compiled_df)}...")
            
            # Determine the final image paths (highlighted or original)
            final_image_paths = []
            processed_row_info = batch_results.get(idx) # Get processed info for this compiled row index

            if processed_row_info and 'box_2d' in processed_row_info:
                box_data = processed_row_info
                # Use the first original image path for highlighting reference
                image_path_for_highlighting = original_image_paths[0] if original_image_paths else None

                if image_path_for_highlighting:
                    full_image_path = image_path_for_highlighting
                    if not os.path.isabs(full_image_path) and hasattr(app, 'get_full_path'):
                         full_image_path = app.get_full_path(full_image_path)

                    # Generate a unique name for this document's highlighted image
                    image_basename = os.path.splitext(os.path.basename(full_image_path))[0]
                    highlighted_image_path = os.path.join(split_images_dir, f"{image_basename}_doc_{idx+1}_highlighted.jpg")
                    
                    try:
                        # Create highlighted image
                        highlight_image(full_image_path, box_data, highlighted_image_path)
                        final_image_paths = [highlighted_image_path] # Store as a list
                    except Exception as e:
                        app.error_logging(f"Error highlighting image for row {idx}: {str(e)}")
                        final_image_paths = original_image_paths # Fallback to original paths list
                else:
                     final_image_paths = original_image_paths # Fallback if no ref path
            else:
                # No box found or not processed, use the original image paths
                final_image_paths = original_image_paths
                
            # Store the final list of image paths
            new_row['Image_Path'] = final_image_paths
            
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
        messagebox.showinfo("Success", f"Documents have been separated into {len(app.main_df)} entries with highlighted images for each row.")
        
    except Exception as e:
        app.error_logging(f"Error applying document separation with row-based highlighting: {str(e)}")
        print(f"ERROR applying document separation with row-based highlighting: {str(e)}")
        messagebox.showerror("Error", f"Error applying document separation with row-based highlighting: {str(e)}")
        
    finally:
        # Close progress bar
        app.progress_bar.close_progress_window() 