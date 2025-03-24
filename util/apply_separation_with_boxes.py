import os
import pandas as pd
from tkinter import messagebox
from util.process_boxes import process_image_with_bounding_boxes, apply_separation_with_boxes_batched

def apply_document_separation_with_boxes(app):
    """
    Apply document separation based on ***** markers, replace main_df with compiled documents,
    and create separate images for each section based on bounding boxes.
    """
    print("\n===== Starting document separation with bounding boxes =====")
    
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
        
        print(f"Found {separator_count} separators across {len(pages_with_separators)} pages")
        
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
        print(f"Loaded settings from app, Google API key present: {'Yes' if settings.google_api_key else 'No'}")
        print(f"Batch size: {settings.batch_size if hasattr(settings, 'batch_size') else 'Not set'}")
        
        # Process images in batches
        image_to_boxes_map = {}
        
        # Create split_images directory in the project directory
        from util.process_boxes import get_split_images_dir
        split_images_dir = get_split_images_dir(app)
        os.makedirs(split_images_dir, exist_ok=True)
        print(f"Created/verified split_images directory at: {split_images_dir}")
        
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
        print("\nCompiling documents with separators...")
        compiled_df = analyzer.compile_documents(force_recompile=True)
        
        if compiled_df is None or compiled_df.empty:
            raise Exception("No documents were found after separation. Check that your separators are correct.")
        
        print(f"Successfully compiled {len(compiled_df)} documents")
        
        # Update progress
        app.progress_bar.update_progress(60, 100)
        progress_label.config(text="Creating new main dataframe...")
        
        # Create a new main_df with the same columns as the original
        new_main_df = pd.DataFrame(columns=app.main_df.columns)
        
        # For each row in compiled_df, create a new row in main_df
        for idx, row in compiled_df.iterrows():
            print(f"\nProcessing compiled document {idx+1}/{len(compiled_df)}")
            
            # Get the original indices that make up this document
            original_indices = row['Original_Index']
            
            # Use the first original index to get the image path
            first_idx = original_indices[0] if isinstance(original_indices, list) and original_indices else 0
            if first_idx < len(original_df):
                image_path = original_df.loc[first_idx, 'Image_Path']
            else:
                # Fallback to the first available image if index is out of range
                image_path = original_df.loc[0, 'Image_Path'] if not original_df.empty else ""
            
            print(f"Original image path: {image_path}")
            
            # Create a new row for the main_df
            new_row = {col: "" for col in app.main_df.columns}
            new_row['Index'] = idx
            new_row['Page'] = f"{idx+1:04d}_p{idx+1:03d}"
            new_row['Original_Text'] = row['Text'] if 'Text' in row and pd.notna(row['Text']) else ""
            new_row['Text_Toggle'] = "Original_Text" if new_row['Original_Text'].strip() else "None"
            
            text_length = len(new_row['Original_Text'])
            print(f"Text length: {text_length}")
            
            # Find the matching bounding box and set the image path to the cropped image
            found_match = False
            if image_path in image_to_boxes_map:
                boxes = image_to_boxes_map[image_path]
                print(f"Checking {len(boxes)} boxes for a match")
                
                # Find the box containing this text
                for box_idx, box in enumerate(boxes):
                    label_text = box['label']
                    original_text = new_row['Original_Text']
                    
                    # Check if there's significant text overlap (over 50% match)
                    overlap_ratio = _calculate_overlap(label_text, original_text)
                    print(f"Box {box_idx+1} overlap ratio: {overlap_ratio:.2f}")
                    
                    if label_text in original_text or original_text in label_text or overlap_ratio > 0.5:
                        # Use the cropped image path instead of the original
                        new_row['Image_Path'] = box['cropped_image_path']
                        print(f"Found matching box {box_idx+1}, using cropped image: {box['cropped_image_path']}")
                        found_match = True
                        break
                
                if not found_match:
                    # No matching box found, use the original image
                    new_row['Image_Path'] = image_path
                    print(f"No matching box found, using original image")
            else:
                # No boxes processed for this image, use the original
                new_row['Image_Path'] = image_path
                print(f"No boxes available for this image, using original image")
            
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
        print("===== Finished document separation with bounding boxes =====\n")

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