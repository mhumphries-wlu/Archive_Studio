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
    print(f"Calling Gemini API for bounding boxes with image: {image_path}")
    print(f"Text to process length: {len(text_to_process)} characters")
    
    try:
        # Import the Google Generative AI library
        from google import genai
        from google.genai import types
        
        # Initialize the Gemini client with the API key from settings
        api_key = settings.google_api_key
        if not api_key:
            raise ValueError("Google API key is not set")
            
        print(f"Initializing Gemini client with API key")
        client = genai.Client(api_key=api_key)
        
        # Upload the image file
        print(f"Uploading image: {image_path}")
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
        print("Making request to Gemini API...")
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