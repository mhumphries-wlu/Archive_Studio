import tkinter as tk
from PIL import Image, ImageTk, ImageOps
import os
import shutil

class ImageHandler:
    def __init__(self, image_display, app=None):
        self.image_display = image_display
        self.current_scale = 1
        self.original_image = None
        self.photo_image = None
        self.app = app  # Reference to the main application

    def start_pan(self, event):
        self.image_display.scan_mark(event.x, event.y)

    def pan(self, event):
        self.image_display.scan_dragto(event.x, event.y, gain=1)

    def zoom(self, event):
        scale = 1.5 if event.delta > 0 else 0.6667

        if self.original_image is None:
            return

        original_width, original_height = self.original_image.size

        new_width = int(original_width * self.current_scale * scale)
        new_height = int(original_height * self.current_scale * scale)

        if new_width < 50 or new_height < 50:
            return

        resized_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)

        self.photo_image = ImageTk.PhotoImage(resized_image)

        self.image_display.delete("all")
        self.image_display.create_image(0, 0, anchor="nw", image=self.photo_image)

        self.image_display.config(scrollregion=self.image_display.bbox("all"))

        self.current_scale *= scale

    def scroll(self, event):
        self.image_display.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def load_image(self, image_path):
        # Load the image
        self.original_image = Image.open(image_path)
        
        # Apply the current scale to the image
        original_width, original_height = self.original_image.size
        new_width = int(original_width * self.current_scale)
        new_height = int(original_height * self.current_scale)
        self.original_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)
        
        self.photo_image = ImageTk.PhotoImage(self.original_image)

        # Update the canvas item
        self.image_display.delete("all")
        self.image_display.create_image(0, 0, anchor="nw", image=self.photo_image)

        # Update the scroll region
        self.image_display.config(scrollregion=self.image_display.bbox("all"))

    def rotate_image(self, direction, current_image_path):
        try:
            # Open the image fresh from disk
            with Image.open(current_image_path) as img:
                # Rotate the image
                if direction == "clockwise":
                    rotated = img.rotate(-90, expand=True)
                else:
                    rotated = img.rotate(90, expand=True)
                
                # Save directly back to the same path
                rotated.save(current_image_path, quality=95)
            
            # Update the display
            self.load_image(current_image_path)
            
            return True, None

        except Exception as e:
            return False, f"An error occurred while rotating the image: {e}"

    def resize_image(self, image_path, output_path, max_size=1980):
        """Resize an image while maintaining aspect ratio"""
        with Image.open(image_path) as img:
            # Get the original image size
            width, height = img.size

            # Determine the larger dimension
            larger_dimension = max(width, height)

            # Calculate the scaling factor only if larger than max_size
            scale = 1.0
            if larger_dimension > max_size:
                scale = max_size / larger_dimension

            # Calculate new dimensions
            new_width = int(width * scale)
            new_height = int(height * scale)

            # Resize the image only if needed
            if scale < 1.0:
                img = img.resize((new_width, new_height), Image.LANCZOS)

            img = ImageOps.exif_transpose(img)

            # Save the image with high quality
            img.save(output_path, "JPEG", quality=95)

    def process_new_images(self, source_paths, images_directory, project_directory, temp_directory, main_df, page_counter_setter):
        """Process a list of new image paths, resize them, and prepare data for the main DataFrame"""
        successful_copies = 0
        start_index = len(main_df)  # Get index before adding new rows
        new_rows_list = []  # Collect new rows here

        for idx, source_path in enumerate(source_paths):
            new_index = start_index + idx  # Calculate index based on start and loop index
            file_extension = os.path.splitext(source_path)[1].lower()
            new_file_name = f"{new_index+1:04d}_p{new_index+1:03d}{file_extension}"
            dest_path = os.path.join(images_directory, new_file_name)

            try:
                # Instead of directly copying, resize and save the image
                self.resize_image(source_path, dest_path)
                # Store relative path
                relative_dest_path = os.path.relpath(dest_path, project_directory or temp_directory)

                text_file_name = f"{new_index+1:04d}_p{new_index+1:03d}.txt"
                text_file_path = os.path.join(images_directory, text_file_name)
                # Store relative path
                relative_text_path = os.path.relpath(text_file_path, project_directory or temp_directory)

                with open(text_file_path, "w", encoding='utf-8') as f:
                    f.write("")

                new_row_data = {
                    "Index": new_index,
                    "Page": f"{new_index+1:04d}_p{new_index+1:03d}",
                    "Original_Text": "",
                    "Corrected_Text": "",
                    "Formatted_Text": "",
                    "Image_Path": relative_dest_path,  # Use relative path
                    "Text_Path": relative_text_path,   # Use relative path
                    "Text_Toggle": "None",  # Changed from "Original_Text" to "None"
                    # Initialize other relevant columns as empty strings
                    "Translation": "", "Separated_Text": "", "People": "", "Places": "",
                    "Errors": "", "Errors_Source": "", "Relevance": ""
                }
                # Ensure all DataFrame columns are present in the new row data
                for col in main_df.columns:
                    if col not in new_row_data:
                        new_row_data[col] = ""

                new_rows_list.append(new_row_data)
                successful_copies += 1

            except Exception as e:
                if self.app:
                    self.app.error_logging(f"Error processing file {source_path}", f"{e}")
                    self.app.messagebox.showerror("Error", f"Failed to process the image {source_path}:\n{e}")
                raise e

        return successful_copies, new_rows_list

    def delete_image_files(self, image_path_abs, text_path_abs):
        """Delete image and text files from disk"""
        deleted_files = []
        try:
            if image_path_abs and os.path.exists(image_path_abs):
                os.remove(image_path_abs)
                deleted_files.append(image_path_abs)
            if text_path_abs and os.path.exists(text_path_abs):
                os.remove(text_path_abs)
                deleted_files.append(text_path_abs)
        except Exception as e:
            if self.app:
                self.app.error_logging(f"Error deleting files: {str(e)}")
            raise e
        
        return deleted_files