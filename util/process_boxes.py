import os
import json
import re
import asyncio
import pandas as pd
from PIL import Image
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from util.APIHandler import APIHandler

def clean_json_string(json_str):
    """
    Clean up JSON string for better parsing
    
    Args:
        json_str: JSON string to clean
        
    Returns:
        Cleaned JSON string
    """
    # Remove any leading/trailing whitespace
    cleaned = json_str.strip()
    
    # Fix potential JSON format issues
    cleaned = cleaned.replace("'", '"')  # Replace single quotes with double quotes
    cleaned = cleaned.replace("None", "null")  # Replace None with null
    cleaned = cleaned.replace("\n", "\\n")  # Fix newlines in strings
    
    # Remove any text before [ or after ]
    if '[' in cleaned:
        start_idx = cleaned.find('[')
        cleaned = cleaned[start_idx:]
    
    if ']' in cleaned:
        end_idx = cleaned.rfind(']') + 1
        cleaned = cleaned[:end_idx]
    
    return cleaned

def get_bounding_boxes_from_api(image_path, text_to_process, settings):
    """
    Call the Gemini API to get bounding boxes for the text in the image using the Google Generative AI SDK.
    
    Args:
        image_path: Path to the image file
        text_to_process: Text to be processed by the Gemini API
        settings: Settings object containing API key and presets
        
    Returns:
        List of dictionaries with 'box_2d' and 'label' keys
    """
    
    try:
        # Import the Google Generative AI library
        from google import genai
        from google.genai import types
        
        # Initialize the Gemini client with the API key from settings
        api_key = settings.google_api_key
        if not api_key:
            raise ValueError("Google API key is not set")
            
        client = genai.Client(api_key=api_key)
        
        # Upload the image file
        uploaded_file = client.files.upload(file=image_path)
        
        # Get the Bounding_Boxes preset from settings for system instructions
        system_instruction = "You draw bounding boxes on an image of historical documents to identify the location of specific text."
        for preset in settings.analysis_presets:
            if preset.get('name') == "Bounding_Boxes":
                if preset.get('general_instructions'):
                    system_instruction = preset.get('general_instructions')
                break
        
        # Create the content structure with the uploaded image and text prompt
        prompt_text = f"""In the accompanying image, identify bounding boxes for each section of the image that would surround the following text blocks. Make sure your boxes will capture all the text by providing generous margins: 

{text_to_process}"""
        
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=uploaded_file.uri,
                        mime_type=uploaded_file.mime_type,
                    ),
                    types.Part.from_text(text=prompt_text),
                ],
            ),
        ]
        
        # Define the generation configuration
        generate_content_config = types.GenerateContentConfig(
            temperature=0,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_mime_type="application/json",
            system_instruction=[
                types.Part.from_text(text=system_instruction),
            ],
        )
        
        # Make the API call
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=generate_content_config,
        )
        
        # Extract the response text
        response_text = response.text
        print("\n========== GEMINI API RESPONSE ==========")
        print(response_text)
        print("=======================================\n")
        
        # Parse the JSON response
        try:
            bounding_boxes = json.loads(response_text)
            
            # Convert the structure if needed
            result = []
            for box in bounding_boxes:
                # Convert the format if necessary
                if "box_2d" in box and ("text" in box or "label" in box):
                    result.append({
                        "box_2d": box["box_2d"],
                        "label": box.get("text", box.get("label", ""))
                    })
            
            print(f"Successfully parsed {len(result)} bounding boxes from response")
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Invalid JSON: {response_text[:200]}")
            
            # If parsing fails, attempt to extract JSON using regex
            import re
            json_pattern = r'\[[\s\S]*\]'  # Match anything that looks like a JSON array
            match = re.search(json_pattern, response_text)
            
            if match:
                try:
                    json_str = match.group(0)
                    cleaned_json = clean_json_string(json_str)
                    bounding_boxes = json.loads(cleaned_json)
                    
                    # Convert the structure if needed
                    result = []
                    for box in bounding_boxes:
                        if "box_2d" in box and ("text" in box or "label" in box):
                            result.append({
                                "box_2d": box["box_2d"],
                                "label": box.get("text", box.get("label", ""))
                            })
                    
                    print(f"Successfully parsed {len(result)} bounding boxes after regex extraction")
                    return result
                except Exception as inner_e:
                    print(f"Error in regex extraction: {inner_e}")
            
            # If all parsing attempts fail, create a single box for the entire image
            print("All JSON parsing attempts failed. Creating a single box for the entire image.")
            return [{
                'box_2d': [0, 0, 1000, 1000],  # Full image coordinates
                'label': text_to_process[:500]  # Use the first part of the text as label
            }]
    
    except Exception as e:
        print(f"ERROR in get_bounding_boxes_from_api: {str(e)}")
        # Return a default bounding box for the entire image in case of error
        return [{
            'box_2d': [0, 0, 1000, 1000],  # Full image coordinates
            'label': text_to_process[:500]  # Use the first part of the text as label
        }]

# Keep the original function as a fallback with a different name in case we need it
def get_bounding_boxes_from_api_legacy(image_path, text_to_process, settings):
    """
    Legacy version of the function that calls the Gemini API using APIHandler.
    This is kept as a fallback in case the new implementation has issues.
    """
    # Original implementation moved here
    # ... rest of the original implementation ...

def normalize_coordinates(box_coords, img_width, img_height):
    """
    Convert normalized coordinates (0-1000) to actual pixel coordinates.
    
    Args:
        box_coords: List in the format [y_min, x_min, y_max, x_max]
        img_width: Width of the image in pixels
        img_height: Height of the image in pixels
        
    Returns:
        Tuple of (x_min, y_min, x_max, y_max) in pixel coordinates
    """
    
    y_min, x_min, y_max, x_max = box_coords
    
    # Convert from 0-1000 scale to actual pixel coordinates
    x_min_px = int(x_min * img_width / 1000)
    y_min_px = int(y_min * img_height / 1000)
    x_max_px = int(x_max * img_width / 1000)
    y_max_px = int(y_max * img_height / 1000)
    
    
    # Add buffer of 50 pixels in vertical direction
    buffer = 50
    
    # Extend horizontally to image edges (as in draw_box.py)
    x_min_px = 0  # Left edge of image
    x_max_px = img_width  # Right edge of image
    
    # Apply vertical buffer with boundary checks
    y_min_px = max(0, y_min_px - buffer)  # Ensure not less than 0
    y_max_px = min(img_height, y_max_px + buffer)  # Ensure not greater than image height
    
    
    return (x_min_px, y_min_px, x_max_px, y_max_px)

def crop_image(image_path, box_coords, output_path):
    """
    Crop an image based on the bounding box coordinates.
    
    Args:
        image_path: Path to the original image
        box_coords: List in the format [y_min, x_min, y_max, x_max] from API
        output_path: Path to save the cropped image
        
    Returns:
        Path to the saved cropped image
    """
    try:
        
        # Open the image
        img = Image.open(image_path)
        img_width, img_height = img.size
        
        # Normalize coordinates - only do this ONCE
        norm_coords = normalize_coordinates(box_coords, img_width, img_height)
        x_min, y_min, x_max, y_max = norm_coords
        
        # Crop the image
        cropped_img = img.crop((x_min, y_min, x_max, y_max))
       
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the cropped image
        cropped_img.save(output_path)
        
        return output_path
    
    except Exception as e:
        raise

def get_split_images_dir(app=None):
    """
    Get the appropriate split_images directory path.
    
    Args:
        app: The application instance with project directory information
        
    Returns:
        Path to the split_images directory
    """
    if app and hasattr(app, 'project_directory') and app.project_directory:
        # Create in the project directory
        return os.path.join(app.project_directory, 'split_images')
    else:
        # Fallback to current working directory
        return os.path.join(os.getcwd(), 'split_images')

def process_image_with_bounding_boxes(image_path, text_to_process, settings, app=None):
    """
    Process an image with bounding boxes and create cropped images.
    
    Args:
        image_path: Path to the original image
        text_to_process: Text to be processed by the Gemini API
        settings: Settings object containing API key and presets
        app: The application instance with project directory information
        
    Returns:
        List of dictionaries with 'box_2d', 'label', and 'cropped_image_path' keys
    """
    
    # Check if we need to prompt the user to save the project first
    if app and (not hasattr(app, 'project_directory') or not app.project_directory):
        from tkinter import messagebox
        if messagebox.askyesno("Save Project", "To create cropped images, you need to save the project first. Would you like to save your project now?"):
            app.project_io.save_project()
            if not hasattr(app, 'project_directory') or not app.project_directory:
                messagebox.showinfo("Operation Cancelled", "Could not save project.")
                raise ValueError("Cannot proceed without saving the project first")
        else:
            raise ValueError("Cannot proceed without saving the project first")
    
    # Create split_images directory in the appropriate location
    split_images_dir = get_split_images_dir(app)
    os.makedirs(split_images_dir, exist_ok=True)
    
    # Get bounding boxes from API
    bounding_boxes = get_bounding_boxes_from_api(image_path, text_to_process, settings)
    
    # Get image file name without extension
    image_basename = os.path.splitext(os.path.basename(image_path))[0]
    
    # Process each bounding box
    result = []
    for i, box_data in enumerate(bounding_boxes):
        box_coords = box_data['box_2d']
        label = box_data['label']
        
        # Generate output path for cropped image
        output_path = os.path.join(split_images_dir, f"{image_basename}_{i+1}.jpg")
        
        # Crop and save the image
        cropped_image_path = crop_image(image_path, box_coords, output_path)
        
        # Add the cropped image path to the result
        result.append({
            'box_2d': box_coords,
            'label': label,
            'cropped_image_path': cropped_image_path
        })
    
    return result

async def process_images_in_batches(image_paths, texts, settings, app=None):
    """
    Process multiple images in parallel batches.
    
    Args:
        image_paths: List of image paths to process
        texts: List of texts corresponding to each image
        settings: Settings object containing API key and batch size
        app: The application instance with project directory information
        
    Returns:
        Dictionary mapping image paths to their bounding box results
    """
    
    # Check if we need to prompt the user to save the project first
    if app and (not hasattr(app, 'project_directory') or not app.project_directory):
        from tkinter import messagebox
        if messagebox.askyesno("Save Project", "To create cropped images, you need to save the project first. Would you like to save your project now?"):
            app.project_io.save_project()
            if not hasattr(app, 'project_directory') or not app.project_directory:
                messagebox.showinfo("Operation Cancelled", "Could not save project.")
                raise ValueError("Cannot proceed without saving the project first")
        else:
            raise ValueError("Cannot proceed without saving the project first")
    
    # Get batch size from settings (default to 4 if not specified)
    batch_size = getattr(settings, 'batch_size', 4)
    
    # Process images in batches
    results = {}
    
    # Break the images into batches
    for i in range(0, len(image_paths), batch_size):
        batch_image_paths = image_paths[i:i+batch_size]
        batch_texts = texts[i:i+batch_size]
        
        # Process batch in parallel
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = []
            for img_path, text in zip(batch_image_paths, batch_texts):
                future = executor.submit(process_image_with_bounding_boxes, img_path, text, settings, app)
                futures.append((img_path, future))
            
            # Collect results as they complete
            for img_path, future in futures:
                try:
                    result = future.result()
                    results[img_path] = result
                    print(f"Completed processing for {img_path}: {len(result)} boxes")
                except Exception as e:
                    print(f"Error processing {img_path}: {e}")
                    results[img_path] = []
    
    return results

def apply_separation_with_boxes_batched(app):
    """
    Apply document separation and process images in batches for better performance.
    This function should be called from apply_separation_with_boxes.py
    
    Args:
        app: The main application object
        
    Returns:
        Dictionary mapping image paths to their bounding box results
    """
    # Check if project directory exists
    if not hasattr(app, 'project_directory') or not app.project_directory:
        from tkinter import messagebox
        if messagebox.askyesno("Save Project", "To create cropped images, you need to save the project first. Would you like to save your project now?"):
            app.project_io.save_project()
        else:
            messagebox.showinfo("Operation Cancelled", "Document separation with boxes was cancelled.")
            return {}
            
    # Check again after potential save
    if not hasattr(app, 'project_directory') or not app.project_directory:
        from tkinter import messagebox
        messagebox.showinfo("Operation Cancelled", "Document separation with boxes was cancelled.")
        return {}
    
    # This is where we would collect all images and texts that need processing
    image_paths = []
    texts = []
    
    # Get all unique images from the original_df
    original_df = app.main_df.copy()
    unique_images = original_df['Image_Path'].unique()
    
    # Check if get_full_path method exists
    has_get_full_path = hasattr(app, 'get_full_path') and callable(getattr(app, 'get_full_path'))
    
    # Collect valid images and their texts
    for img in unique_images:
        if pd.isna(img) or not img:
            continue
            
        if has_get_full_path:
            full_path = app.get_full_path(img)
        else:
            # Try to handle relative paths
            if os.path.isabs(img):
                full_path = img
            else:
                # Try common patterns
                if app.project_directory and os.path.exists(app.project_directory):
                    full_path = os.path.join(app.project_directory, img)
                else:
                    full_path = os.path.join(os.getcwd(), img)
            
        if os.path.exists(full_path):
            # Get all text from this image's pages
            all_text_for_image = ""
            for idx, row in original_df[original_df['Image_Path'] == img].iterrows():
                all_text_for_image += app.find_right_text(idx) + "\n"
            
            if all_text_for_image.strip():
                image_paths.append(full_path)
                texts.append(all_text_for_image.strip())
    
    # Create event loop and run parallel processing
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        results = loop.run_until_complete(process_images_in_batches(image_paths, texts, app.settings, app))
    finally:
        loop.close()
    
    return results

def apply_separation_with_boxes_by_row_batched(app, compiled_df, original_df):
    """
    Process row-based document separation in batches for better performance.
    
    Args:
        app: The main application object
        compiled_df: The compiled DataFrame with separated documents
        original_df: The original DataFrame before separation
        
    Returns:
        Dictionary mapping row indices to their processed bounding box results
    """
    # Get batch size from settings (default to 50 if not specified)
    batch_size = getattr(app.settings, 'batch_size', 50)
    
    # Prepare batches of rows to process
    rows_to_process = []
    image_paths = []
    texts = []
    row_indices = []
    
    # Check if get_full_path method exists
    has_get_full_path = hasattr(app, 'get_full_path') and callable(getattr(app, 'get_full_path'))
    
    # Collect row data for processing
    for idx, row in compiled_df.iterrows():
        # Skip rows with empty text
        if 'Text' not in row or not pd.notna(row['Text']) or not row['Text'].strip():
            continue
            
        # Get the original indices that make up this document
        original_indices = row['Original_Index']
        
        # Use the first original index to get the image path
        first_idx = original_indices[0] if isinstance(original_indices, list) and original_indices else 0
        if first_idx < len(original_df):
            image_path = original_df.loc[first_idx, 'Image_Path']
        else:
            # Fallback to the first available image if index is out of range
            image_path = original_df.loc[0, 'Image_Path'] if not original_df.empty else ""
            
        if pd.isna(image_path) or not image_path:
            continue
            
        # Get the full image path
        if has_get_full_path:
            full_path = app.get_full_path(image_path)
        else:
            # Try to handle relative paths
            if os.path.isabs(image_path):
                full_path = image_path
            else:
                # Try common patterns
                if app.project_directory and os.path.exists(app.project_directory):
                    full_path = os.path.join(app.project_directory, image_path)
                else:
                    full_path = os.path.join(os.getcwd(), image_path)
        
        if os.path.exists(full_path):
            # Add this row to processing queue
            document_text = row['Text']
            
            image_paths.append(full_path)
            texts.append(document_text)
            row_indices.append(idx)
    
    # Create event loop and run parallel processing
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Process batches
        results_by_indices = {}
        
        # Process in batches of batch_size
        for i in range(0, len(row_indices), batch_size):
            batch_image_paths = image_paths[i:i+batch_size]
            batch_texts = texts[i:i+batch_size]
            batch_indices = row_indices[i:i+batch_size]
            
            # Run the batch asynchronously
            batch_results = loop.run_until_complete(
                process_rows_in_batches(batch_image_paths, batch_texts, batch_indices, app.settings, app)
            )
            
            # Add batch results to overall results
            results_by_indices.update(batch_results)
    finally:
        loop.close()
    
    return results_by_indices

async def process_rows_in_batches(image_paths, texts, row_indices, settings, app=None):
    """
    Process multiple document rows in parallel batches.
    
    Args:
        image_paths: List of image paths to process
        texts: List of texts corresponding to each row
        row_indices: List of row indices in the compiled DataFrame
        settings: Settings object containing API key and batch size
        app: The application instance with project directory information
        
    Returns:
        Dictionary mapping row indices to their bounding box results
    """
    
    # Get batch size from settings (default to 50 if not specified)
    batch_size = getattr(settings, 'batch_size', 50)
    
    # Process rows in batches
    results = {}
    
    # Split into smaller batches for concurrent processing
    max_workers = min(batch_size, 10)  # Limit concurrent API calls
    
    # Process batch in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, (img_path, text, row_idx) in enumerate(zip(image_paths, texts, row_indices)):
            # Check if Bounding_Boxes_By_Row preset exists
            preset_name = "Bounding_Boxes_By_Row"
            found_preset = False
            
            for preset in settings.analysis_presets:
                if preset.get('name') == preset_name:
                    found_preset = True
                    break
            
            # If the preset doesn't exist, fall back to the regular Bounding_Boxes preset
            if not found_preset:
                preset_name = "Bounding_Boxes"
                
            # Submit task to executor
            future = executor.submit(get_bounding_boxes_from_api, img_path, text, settings)
            futures.append((row_idx, future))
        
        # Collect results as they complete
        for row_idx, future in futures:
            try:
                bounding_boxes = future.result()
                if bounding_boxes and len(bounding_boxes) > 0:
                    results[row_idx] = bounding_boxes[0]  # Take first bounding box for row
                else:
                    results[row_idx] = None
                print(f"Completed processing for row {row_idx}")
            except Exception as e:
                print(f"Error processing row {row_idx}: {e}")
                results[row_idx] = None
    
    return results

