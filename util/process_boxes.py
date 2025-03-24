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
    Call the Gemini API to get bounding boxes for the text in the image.
    
    Args:
        image_path: Path to the image file
        text_to_process: Text to be processed by the Gemini API
        settings: Settings object containing API key and presets
        
    Returns:
        List of dictionaries with 'box_2d' and 'label' keys
    """
    print(f"Calling Gemini API for bounding boxes with image: {image_path}")
    print(f"Text to process length: {len(text_to_process)} characters")
    
    try:
        # Debug print for settings keys
        print(f"Settings keys: {dir(settings)}")
        
        # Validate settings object
        if not hasattr(settings, 'analysis_presets'):
            print("ERROR: settings.analysis_presets not found")
            raise ValueError("settings.analysis_presets not found")
            
        print(f"Number of analysis presets: {len(settings.analysis_presets)}")
        
        # Get the Bounding_Boxes preset from settings
        bounding_box_preset = None
        for preset in settings.analysis_presets:
            print(f"Checking preset: {preset.get('name', 'unnamed')}")
            if preset.get('name') == "Bounding_Boxes":
                bounding_box_preset = preset
                break
        
        if not bounding_box_preset:
            preset_names = [p.get('name', 'unnamed') for p in settings.analysis_presets]
            print(f"ERROR: Bounding_Boxes preset not found. Available presets: {preset_names}")
            raise ValueError("Bounding_Boxes preset not found in settings.analysis_presets")
        
        # Print the general instructions for debugging
        print(f"Found preset: {bounding_box_preset.get('name')}")
        print(f"General instructions: {bounding_box_preset.get('general_instructions', '')}")
        
        # Check if API keys are available
        print(f"Google API key exists: {hasattr(settings, 'google_api_key')}")
        if hasattr(settings, 'google_api_key'):
            key_length = len(settings.google_api_key) if settings.google_api_key else 0
            print(f"Google API key length: {key_length}")
        
        # Initialize API Handler
        try:
            print("Creating APIHandler...")
            api_handler = APIHandler(
                openai_api_key=getattr(settings, 'openai_api_key', ''),
                anthropic_api_key=getattr(settings, 'anthropic_api_key', ''),
                google_api_key=getattr(settings, 'google_api_key', '')
            )
            print("APIHandler created successfully")
        except Exception as e:
            print(f"ERROR creating APIHandler: {e}")
            raise ValueError(f"Failed to create APIHandler: {e}")
        
        # Format the user prompt with the text to process
        try:
            print("Formatting user prompt...")
            specific_instructions = bounding_box_preset.get('specific_instructions', "")
            print(f"Specific instructions template: {specific_instructions[:100]}...")
            
            # Check if the template is valid
            if "{text_to_process}" not in specific_instructions:
                print("WARNING: {text_to_process} placeholder not found in specific_instructions")
            
            # Format safely
            try:
                user_prompt = specific_instructions.format(text_to_process=text_to_process)
                print("User prompt formatting successful")
            except KeyError as e:
                print(f"ERROR formatting prompt - missing key: {e}")
                # Try a fallback approach
                user_prompt = specific_instructions.replace("{text_to_process}", text_to_process)
            except Exception as e:
                print(f"ERROR formatting prompt: {e}")
                # Emergency fallback
                user_prompt = f"""In the accompanying image, identify bounding boxes for each section containing the following text blocks:
                
{text_to_process}

Output as JSON array of objects with box_2d coordinates and label."""
                
            print(f"Formatted user prompt: {user_prompt[:200]}...")
        except Exception as e:
            print(f"ERROR in prompt preparation: {e}")
            raise ValueError(f"Failed to prepare prompt: {e}")
        
        # Prepare parameters for API call
        system_prompt = bounding_box_preset.get('general_instructions', "")
        temperature = float(bounding_box_preset.get('temperature', 0.0))
        model = bounding_box_preset.get('model', "gemini-2.0-flash")
        
        try:
            # Load the image
            print(f"Loading image from path: {image_path}")
            img = Image.open(image_path)
            print(f"Image loaded successfully: {img.format}, {img.size}")
            
            # Create an async event loop to run the async API call
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Make the API call
            print("Sending request to Gemini API...")
            result = loop.run_until_complete(
                api_handler.route_api_call(
                    engine=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temp=temperature,
                    image_data=image_path,
                    text_to_process=None,  # Already formatted in user_prompt
                    val_text=None,  # No validation text for this call
                    index=0,
                    is_base64=False,  # We're passing the image path directly
                    formatting_function=True,  # We've already formatted the prompt
                    api_timeout=120.0
                )
            )
            
            # Close the event loop
            loop.close()
            
            # Check if we got a valid response
            if result[0] == "Error":
                raise ValueError("Error from API call")
            
            # Extract the response
            response_text = result[0]
            
            # Print the full response for debugging
            print("\n========== FULL API RESPONSE ==========")
            print(response_text)
            print("=======================================\n")
            
            # Look for the standard response pattern with "Here are the bounding box detections:"
            # followed by JSON array
            bounding_box_pattern = r"Here are the bounding box detections:[\s\n]*(\[\s*\{.*\}\s*\])"
            json_match = re.search(bounding_box_pattern, response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
                print(f"Found JSON array after 'Here are the bounding box detections:'")
                print(f"Extracted JSON: {json_str[:100]}...")
                
                # Clean the JSON string
                cleaned_json = clean_json_string(json_str)
                
                try:
                    bounding_boxes = json.loads(cleaned_json)
                    print(f"Successfully parsed {len(bounding_boxes)} bounding boxes from response")
                    for i, box in enumerate(bounding_boxes):
                        print(f"Box {i+1}: {box}")
                    return bounding_boxes
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error with primary pattern: {e}")
                    # Continue to fallback methods
            
            # If the standard pattern fails, try different regex patterns
            patterns = [
                r'\[\s*\{.*\}\s*\]',  # Standard array of objects
                r'\{\s*"box_2d".*\}',  # Single object with box_2d
                r'\{\s*.*"box_2d".*\}',  # Object with box_2d anywhere
            ]
            
            json_str = None
            for pattern in patterns:
                json_match = re.search(pattern, response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    print(f"Found JSON using pattern: {pattern}")
                    print(f"Extracted JSON: {json_str[:100]}...")
                    break
            
            if json_str:
                # Clean the JSON string
                cleaned_json = clean_json_string(json_str)
                print(f"Cleaned JSON: {cleaned_json[:100]}...")
                
                # Check if we found a single object or an array
                if cleaned_json.strip().startswith('{'):
                    # Single object, wrap in array
                    cleaned_json = f"[{cleaned_json}]"
                    print("Wrapped single object in array")
                
                try:
                    bounding_boxes = json.loads(cleaned_json)
                    print(f"Successfully parsed {len(bounding_boxes)} bounding boxes from response")
                    for i, box in enumerate(bounding_boxes):
                        print(f"Box {i+1}: {box}")
                    return bounding_boxes
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error: {e}")
                    print(f"Invalid JSON: {cleaned_json[:200]}")
                    # Try more aggressive cleaning if normal cleaning failed
                    try:
                        # Try to extract just the array part
                        if '[' in cleaned_json and ']' in cleaned_json:
                            start_idx = cleaned_json.find('[')
                            end_idx = cleaned_json.rfind(']') + 1
                            array_only = cleaned_json[start_idx:end_idx]
                            bounding_boxes = json.loads(array_only)
                            print(f"Successfully parsed {len(bounding_boxes)} bounding boxes after extracting array")
                            return bounding_boxes
                    except Exception:
                        print("Failed to parse JSON even with array extraction")
            
            # If we couldn't extract JSON, try a different approach
            print("Could not extract JSON with regex, attempting to extract box info manually")
            
            # Look for box_2d patterns in the text
            box_pattern = r'box_2d"?\s*:\s*\[([\d\s,\.]+)\]'
            label_pattern = r'label"?\s*:\s*"([^"]+)"'
            
            box_matches = re.findall(box_pattern, response_text)
            label_matches = re.findall(label_pattern, response_text)
            
            if box_matches and len(box_matches) == len(label_matches):
                print(f"Found {len(box_matches)} box coordinates and labels using manual extraction")
                bounding_boxes = []
                
                for i, (box_str, label) in enumerate(zip(box_matches, label_matches)):
                    try:
                        # Clean and parse box coordinates
                        coords = [float(coord.strip()) for coord in box_str.split(',')]
                        if len(coords) == 4:
                            bounding_boxes.append({
                                'box_2d': coords,
                                'label': label
                            })
                            print(f"Manually extracted Box {i+1}: {coords} - {label[:30]}...")
                    except:
                        print(f"Error parsing coordinates for box {i+1}")
                
                if bounding_boxes:
                    return bounding_boxes
            
            # If all attempts fail, try a more aggressive manual extraction approach
            print("Trying manual coordinate extraction as last resort")
            
            # Try to match any box-like structures in the text
            box_pattern = r'(?:box_2d|coordinates|coord).*?\[([^\]]+)\]'
            label_pattern = r'(?:label|text).*?["\'](.*?)["\']'
            
            # Find all potential box coordinates
            box_matches = re.findall(box_pattern, response_text, re.IGNORECASE | re.DOTALL)
            
            # Find all potential labels
            label_matches = re.findall(label_pattern, response_text, re.IGNORECASE | re.DOTALL)
            
            print(f"Found {len(box_matches)} potential box coordinates and {len(label_matches)} potential labels")
            
            # If we have coordinates, try to parse them
            if box_matches:
                bounding_boxes = []
                
                # Match labels with coordinates if possible, otherwise use empty labels
                if len(label_matches) != len(box_matches):
                    print(f"Warning: Mismatch between coordinates ({len(box_matches)}) and labels ({len(label_matches)})")
                    # Fill missing labels with placeholders
                    if len(label_matches) < len(box_matches):
                        label_matches.extend(["Unknown text"] * (len(box_matches) - len(label_matches)))
                
                for i, (box_str, label) in enumerate(zip(box_matches, label_matches[:len(box_matches)])):
                    try:
                        # Clean up the coordinate string
                        box_str = box_str.strip()
                        box_str = re.sub(r'[^\d\s,\.]', '', box_str)  # Remove anything that's not a digit, space, comma, or period
                        
                        # Split by comma or space
                        coords_raw = re.split(r'[,\s]+', box_str)
                        # Filter out empty strings and convert to float
                        coords = [float(c) for c in coords_raw if c.strip()]
                        
                        # Ensure we have exactly 4 coordinates
                        if len(coords) < 4:
                            print(f"Warning: Not enough coordinates in box {i+1}, padding with zeros")
                            coords.extend([0] * (4 - len(coords)))
                        elif len(coords) > 4:
                            print(f"Warning: Too many coordinates in box {i+1}, using first 4")
                            coords = coords[:4]
                        
                        bounding_boxes.append({
                            'box_2d': coords,
                            'label': label
                        })
                        print(f"Manually extracted Box {i+1}: {coords} - {label[:30]}...")
                    except Exception as e:
                        print(f"Error parsing coordinates for box {i+1}: {str(e)}")
                
                if bounding_boxes:
                    print(f"Successfully extracted {len(bounding_boxes)} boxes using manual parsing")
                    return bounding_boxes
            
            # If all attempts fail, create a single box for the entire image
            print("All JSON parsing attempts failed. Creating a single box for the entire image.")
            return [{
                'box_2d': [0, 0, 1000, 1000],  # Full image coordinates
                'label': text_to_process[:500]  # Use the first part of the text as label
            }]
            
        except Exception as e:
            print(f"ERROR during API call: {e}")
            raise ValueError(f"API call failed: {e}")
            
    except Exception as e:
        print(f"ERROR in get_bounding_boxes_from_api setup: {str(e)}")
        raise

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
    print(f"Converting coordinates from normalized format: {box_coords}")
    
    y_min, x_min, y_max, x_max = box_coords
    
    # Convert from 0-1000 scale to actual pixel coordinates
    x_min_px = int(x_min * img_width / 1000)
    y_min_px = int(y_min * img_height / 1000)
    x_max_px = int(x_max * img_width / 1000)
    y_max_px = int(y_max * img_height / 1000)
    
    print(f"Initial pixel coordinates: ({x_min_px}, {y_min_px}, {x_max_px}, {y_max_px})")
    
    # Add buffer of 50 pixels in vertical direction
    buffer = 50
    
    # Extend horizontally to image edges (as in draw_box.py)
    x_min_px = 0  # Left edge of image
    x_max_px = img_width  # Right edge of image
    
    # Apply vertical buffer with boundary checks
    y_min_px = max(0, y_min_px - buffer)  # Ensure not less than 0
    y_max_px = min(img_height, y_max_px + buffer)  # Ensure not greater than image height
    
    print(f"Final pixel coordinates with buffer and horizontal extension: ({x_min_px}, {y_min_px}, {x_max_px}, {y_max_px})")
    
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
        print(f"Cropping image: {image_path}")
        print(f"Box coordinates from API: {box_coords}")
        
        # Open the image
        img = Image.open(image_path)
        img_width, img_height = img.size
        print(f"Original image size: {img_width}x{img_height}")
        
        # Normalize coordinates - only do this ONCE
        norm_coords = normalize_coordinates(box_coords, img_width, img_height)
        x_min, y_min, x_max, y_max = norm_coords
        print(f"Using normalized coordinates for cropping: ({x_min}, {y_min}, {x_max}, {y_max})")
        
        # Crop the image
        cropped_img = img.crop((x_min, y_min, x_max, y_max))
        print(f"Cropped image size: {cropped_img.width}x{cropped_img.height}")
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        print(f"Saving cropped image to: {output_path}")
        
        # Save the cropped image
        cropped_img.save(output_path)
        print(f"Successfully saved cropped image to: {output_path}")
        
        return output_path
    
    except Exception as e:
        print(f"Error cropping image: {e}")
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
    print(f"\n===== Processing image with bounding boxes =====")
    print(f"Image path: {image_path}")
    print(f"Text length: {len(text_to_process)} characters")
    
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
    print(f"Created split_images directory at: {split_images_dir}")
    
    # Get bounding boxes from API
    print("Calling Gemini API to get bounding boxes...")
    bounding_boxes = get_bounding_boxes_from_api(image_path, text_to_process, settings)
    print(f"Received {len(bounding_boxes)} bounding boxes from API")
    
    # Get image file name without extension
    image_basename = os.path.splitext(os.path.basename(image_path))[0]
    print(f"Image basename: {image_basename}")
    
    # Process each bounding box
    result = []
    for i, box_data in enumerate(bounding_boxes):
        print(f"\nProcessing box {i+1}/{len(bounding_boxes)}")
        box_coords = box_data['box_2d']
        label = box_data['label']
        print(f"Box coordinates: {box_coords}")
        print(f"Label: {label[:50]}...")
        
        # Generate output path for cropped image
        output_path = os.path.join(split_images_dir, f"{image_basename}_{i+1}.jpg")
        print(f"Output path: {output_path}")
        
        # Crop and save the image
        cropped_image_path = crop_image(image_path, box_coords, output_path)
        
        # Add the cropped image path to the result
        result.append({
            'box_2d': box_coords,
            'label': label,
            'cropped_image_path': cropped_image_path
        })
    
    print(f"Successfully processed {len(result)} bounding boxes")
    print(f"===== Finished processing image =====\n")
    return result

def test_process_image(image_path, text_to_process):
    """
    Test function to manually process an image with bounding boxes.
    
    Args:
        image_path: Path to the image file
        text_to_process: Text to be processed by the Gemini API
    """
    print(f"\n===== TESTING IMAGE PROCESSING =====")
    print(f"Image path: {image_path}")
    print(f"Text length: {len(text_to_process)}")
    
    # Mock settings object
    class MockSettings:
        def __init__(self, api_key):
            self.openai_api_key = ""
            self.anthropic_api_key = ""
            self.google_api_key = api_key
            self.analysis_presets = [
                {
                    'name': "Bounding_Boxes",
                    'model': "gemini-2.0-flash",
                    'temperature': "0.0",
                    'general_instructions': '''You are an API that generates bounding boxes for specific text blocks in historical document images. Your output must be strictly in JSON format following the exact schema provided.''',
                    'specific_instructions': '''In the accompanying image, identify bounding boxes for each section of the image that would contain the following text blocks. 

For each identified text block, you must output a JSON object with the following schema:
{
  "box_2d": [y_min, x_min, y_max, x_max],  // Values from 0-1000 representing normalized coordinates
  "label": "the exact text found in this section"
}

Your response must be a JSON array of these objects, and nothing else. Do not include any explanations or additional text.

Example valid output:
[
  {"box_2d": [45, 50, 159, 951], "label": "Text block 1"},
  {"box_2d": [215, 14, 350, 968], "label": "Text block 2"}
]

Text blocks to identify:

{text_to_process}''',
                    'use_images': True,
                    'current_image': "Yes",
                    'num_prev_images': "0",
                    'num_after_images': "0",
                    'val_text': None
                }
            ]
    
    # Get API key from environment variable
    import os
    api_key = os.environ.get('GOOGLE_API_KEY', '')
    
    if not api_key:
        print("ERROR: No Google API key found in environment variable GOOGLE_API_KEY")
        return
    
    # Create mock settings
    settings = MockSettings(api_key)
    
    # Process the image
    try:
        results = process_image_with_bounding_boxes(image_path, text_to_process, settings)
        print(f"\nSuccessfully processed image with {len(results)} bounding boxes")
        for i, result in enumerate(results):
            print(f"Box {i+1}:")
            print(f"  Coordinates: {result['box_2d']}")
            print(f"  Label: {result['label'][:50]}...")
            print(f"  Image: {result['cropped_image_path']}")
    except Exception as e:
        print(f"ERROR in test: {e}")
    
    print("===== TEST COMPLETED =====\n")

# Uncomment to run the test
# if __name__ == "__main__":
#     image_path = "path/to/your/image.jpg"
#     text_to_process = "Text to process..."
#     test_process_image(image_path, text_to_process) 

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
    print(f"\n===== Processing {len(image_paths)} images in batches =====")
    
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
    print(f"Using batch size: {batch_size}")
    
    # Process images in batches
    results = {}
    
    # Break the images into batches
    for i in range(0, len(image_paths), batch_size):
        batch_image_paths = image_paths[i:i+batch_size]
        batch_texts = texts[i:i+batch_size]
        print(f"\nProcessing batch {i//batch_size + 1} with {len(batch_image_paths)} images")
        
        # Process batch in parallel
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = []
            for img_path, text in zip(batch_image_paths, batch_texts):
                print(f"Submitting job for image: {img_path}")
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
    
    print(f"===== Completed processing {len(results)} images =====\n")
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

# For testing
def test_batch_processing(image_paths, texts, batch_size=2, app=None):
    """
    Test batch processing with multiple images
    
    Args:
        image_paths: List of image paths to process
        texts: List of texts corresponding to each image
        batch_size: Size of each batch (default 2)
        app: The application instance with project directory information
    """
    print(f"\n===== TESTING BATCH PROCESSING =====")
    
    # Mock settings object
    class MockSettings:
        def __init__(self, api_key, batch_size):
            self.openai_api_key = ""
            self.anthropic_api_key = ""
            self.google_api_key = api_key
            self.batch_size = batch_size
            self.analysis_presets = [
                {
                    'name': "Bounding_Boxes",
                    'model': "gemini-2.0-flash",
                    'temperature': "0.0",
                    'general_instructions': '''You are an API that generates bounding boxes for specific text blocks in historical document images. Your output must be strictly in JSON format following the exact schema provided.''',
                    'specific_instructions': '''In the accompanying image, identify bounding boxes for each section of the image that would contain the following text blocks. 

For each identified text block, you must output a JSON object with the following schema:
{
  "box_2d": [y_min, x_min, y_max, x_max],  // Values from 0-1000 representing normalized coordinates
  "label": "the exact text found in this section"
}

Your response must be a JSON array of these objects, and nothing else. Do not include any explanations or additional text.

Example valid output:
[
  {"box_2d": [45, 50, 159, 951], "label": "Text block 1"},
  {"box_2d": [215, 14, 350, 968], "label": "Text block 2"}
]

Text blocks to identify:

{text_to_process}''',
                    'use_images': True,
                    'current_image': "Yes",
                    'num_prev_images': "0",
                    'num_after_images': "0",
                    'val_text': None
                }
            ]
    
    # Get API key from environment variable
    import os
    api_key = os.environ.get('GOOGLE_API_KEY', '')
    
    if not api_key:
        print("ERROR: No Google API key found in environment variable GOOGLE_API_KEY")
        return
    
    # Create mock settings
    settings = MockSettings(api_key, batch_size)
    
    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run batch processing
        results = loop.run_until_complete(process_images_in_batches(image_paths, texts, settings, app))
        
        # Print results
        print("\nBatch processing results:")
        for img_path, boxes in results.items():
            print(f"Image: {img_path}")
            print(f"Boxes: {len(boxes)}")
            for i, box in enumerate(boxes):
                print(f"  Box {i+1}: {box['box_2d']} - {box['label'][:30]}...")
    except Exception as e:
        print(f"ERROR in batch test: {e}")
    finally:
        loop.close()
    
    print("===== BATCH TEST COMPLETED =====\n") 