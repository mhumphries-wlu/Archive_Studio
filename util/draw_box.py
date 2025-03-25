import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import sys
import os
import json

def select_image():
    """Open a file dialog for the user to select an image file."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    file_path = filedialog.askopenfilename(
        title="Select an image file",
        filetypes=[
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif"),
            ("All files", "*.*")
        ]
    )
    if not file_path:
        print("No file selected. Exiting.")
        exit()
    return file_path

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
    
    # Extend horizontally to image edges
    x_min_px = 0  # Left edge of image
    x_max_px = img_width  # Right edge of image
    
    # Apply vertical buffer with boundary checks
    y_min_px = max(0, y_min_px - buffer)  # Ensure not less than 0
    y_max_px = min(img_height, y_max_px + buffer)  # Ensure not greater than image height
    
    return (x_min_px, y_min_px, x_max_px, y_max_px)

def get_boxes_data():
    """Get the boxes data from user input."""
    try:
        print("Enter coordinates as comma-separated values (y_min, x_min, y_max, x_max)")
        print("Values should be between 0 and 1000")
        coords_input = input("Enter coordinates: ")
        label = input("Enter label text: ")
        
        # Split and convert coordinates
        coords = [float(x.strip()) for x in coords_input.split(',')]
        if len(coords) != 4:
            raise ValueError("Please enter exactly 4 coordinates")
            
        y_min, x_min, y_max, x_max = coords
        
        # Validate input ranges
        if not all(0 <= x <= 1000 for x in [y_min, x_min, y_max, x_max]):
            raise ValueError("Coordinates must be between 0 and 1000")
        
        # Create box data structure
        box_data = [{
            "box_2d": [y_min, x_min, y_max, x_max],
            "label": label
        }]
        print("Successfully created box data from input")
        return box_data
        
    except ValueError as e:
        print(f"Error with input: {e}")
        messagebox.showerror("Error", f"Invalid input: {str(e)}")
        return None

def draw_boxes(image_path, boxes_data):
    """
    Draw multiple bounding boxes on an image.
    
    Args:
        image_path: Path to the image file
        boxes_data: List of dictionaries with 'box_2d' and 'label' keys
    """
    try:
        # Open the image
        print(f"Opening image: {image_path}")
        img = Image.open(image_path)
        print(f"Image format: {img.format}, Mode: {img.mode}, Size: {img.size}")
        
        img_width, img_height = img.size
        
        # Make a copy of the image to draw on
        draw_img = img.copy()
        
        # Create a drawing object
        draw = ImageDraw.Draw(draw_img)
        
        # Try to load a font, use default if not available
        try:
            # Try to load a nice font with different sizes based on platform
            if os.name == 'nt':  # Windows
                font_path = os.path.join(os.environ['WINDIR'], 'Fonts', 'Arial.ttf')
                font = ImageFont.truetype(font_path, 20)
                small_font = ImageFont.truetype(font_path, 16)
            else:  # Linux/Mac
                font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
                small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
        except IOError:
            # Use default font if custom font is not available
            font = ImageFont.load_default()
            small_font = font
        
        # Define colors for different boxes
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'cyan', 'magenta', 'yellow', 'lime', 'pink']
        
        print(f"Drawing {len(boxes_data)} boxes")
        
        # Draw each box with its label
        for i, box_data in enumerate(boxes_data):
            box_coords = box_data['box_2d']
            label = box_data['label']
            
            # Get normalized coordinates
            x_min, y_min, x_max, y_max = normalize_coordinates(box_coords, img_width, img_height)
            
            # Choose color (cycle through colors list)
            color = colors[i % len(colors)]
            
            # Draw the rectangle
            draw.rectangle([(x_min, y_min), (x_max, y_max)], outline=color, width=3)
            
            # Draw a label background
            text_width, text_height = draw.textbbox((0, 0), text=label, font=small_font)[2:4]
            
            # Draw the text background (semi-transparent)
            label_bg = Image.new('RGBA', draw_img.size, (0, 0, 0, 0))
            label_draw = ImageDraw.Draw(label_bg)
            label_draw.rectangle(
                [(x_min, y_min), (x_min + text_width + 10, y_min + text_height + 10)],
                fill=(0, 0, 0, 128)
            )
            draw_img = Image.alpha_composite(draw_img.convert('RGBA'), label_bg).convert('RGB')
            draw = ImageDraw.Draw(draw_img)
            
            # Draw the text
            draw.text((x_min + 5, y_min + 5), label, fill="white", font=small_font)
            
            print(f"Box {i+1}: {box_coords} -> ({x_min}, {y_min}), ({x_max}, {y_max})")
        
        # Display the image using matplotlib
        display_image_matplotlib(draw_img)
        
    except Exception as e:
        print(f"Error in draw_boxes: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

def display_image_matplotlib(img):
    """Display the image with matplotlib instead of Tkinter."""
    try:
        # Convert PIL Image to numpy array for matplotlib
        img_array = np.array(img)
        
        # Create figure and display the image
        plt.figure(figsize=(12, 12))
        plt.imshow(img_array)
        plt.axis('off')  # Turn off axis numbers
        plt.title('Image with Bounding Boxes')
        plt.tight_layout()
        plt.show()
        
    except Exception as e:
        print(f"Error displaying image with matplotlib: {e}")
        import traceback
        traceback.print_exc()
        
        # Create debug directory and save image as fallback
        debug_dir = "debug"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        debug_path = os.path.join(debug_dir, "debug_image.png")
        img.save(debug_path)
        print(f"Debug image saved to {debug_path}")
        
        # Try to open the saved image with the default viewer
        try:
            os.startfile(debug_path)  # Windows-specific
        except Exception as e2:
            print(f"Could not open debug image: {e2}")

def main():
    """Main function to coordinate the process."""
    try:
        # Select an image file
        image_path = select_image()
        
        # Get boxes data from the user
        boxes_data = get_boxes_data()
        
        if boxes_data:
            # Draw and display the bounding boxes
            draw_boxes(image_path, boxes_data)
        else:
            print("No valid boxes data provided. Exiting.")
        
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

if __name__ == "__main__":
    # Import numpy here to avoid import error if it's not needed
    import numpy as np
    print(f"Python version: {sys.version}")
    main()
