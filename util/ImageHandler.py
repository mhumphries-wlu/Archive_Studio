# util/ImageHandler.py

# This file contains the ImageHandler class, which is used to handle
# the image handling for the application.

import tkinter as tk
from PIL import Image, ImageTk, ImageOps, ExifTags
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
        img = Image.open(image_path)
        
        # Ensure EXIF orientation is applied for display
        img = ImageOps.exif_transpose(img)

        # Apply the current display scale (if any)
        original_width, original_height = img.size
        # Check if scaling is actually needed (current_scale might be 1)
        if abs(self.current_scale - 1.0) > 1e-6: # Check if scale is not effectively 1
            new_width = int(original_width * self.current_scale)
            new_height = int(original_height * self.current_scale)
            # Add a minimum size check to prevent errors with tiny scales
            if new_width > 0 and new_height > 0:
                self.original_image = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                self.original_image = img # Use original if scaled size is invalid
        else:
             self.original_image = img # Use the (exif transposed) image directly if scale is 1
        
        self.photo_image = ImageTk.PhotoImage(self.original_image)

        # Update the canvas item
        self.image_display.delete("all")
        self.image_display.create_image(0, 0, anchor="nw", image=self.photo_image)

        # Update the scroll region
        self.image_display.config(scrollregion=self.image_display.bbox("all"))

    def rotate_image(self, current_image_path, angle):
        """Rotates the image file on disk by the specified angle and updates display."""
        try:
            # Open the image fresh from disk
            with Image.open(current_image_path) as img:
                # Rotate the image by the given angle
                # Ensure EXIF data is handled if needed (though orientation tag should be removed)
                # img = ImageOps.exif_transpose(img) # Apply existing EXIF before rotating IF NEEDED
                rotated = img.rotate(angle, expand=True)
                
                # Save directly back to the same path, preserving quality
                # Handle potential format issues if not JPEG originally (though processing makes it JPEG)
                save_format = "JPEG"
                save_kwargs = {"quality": 95}
                if img.format and img.format != "JPEG":
                    # If original wasn't JPEG, consider keeping format or converting
                    # Since our processing pipeline standardizes to JPEG, saving as JPEG is fine.
                    pass 
                    
                # Add logic to handle EXIF data if needed (e.g., remove orientation tag again)
                # If the file being rotated *might* still have an orientation tag:
                original_exif = img.info.get('exif')
                final_exif = None
                if original_exif:
                    try:
                        orientation_tag_id = next((tag for tag, name in ExifTags.TAGS.items() if name == 'Orientation'), None)
                        if orientation_tag_id:
                            exif_dict = Image.Exif.load(original_exif)
                            if orientation_tag_id in exif_dict:
                                del exif_dict[orientation_tag_id]
                            for ifd_key in list(exif_dict.keys()):
                                if isinstance(exif_dict[ifd_key], dict) and orientation_tag_id in exif_dict[ifd_key]:
                                    del exif_dict[ifd_key][orientation_tag_id]
                            if exif_dict:
                                 final_exif = Image.Exif.dump(exif_dict)
                        else: # Keep original if tag ID not found
                             final_exif = original_exif
                    except Exception as exif_error:
                         # Log error but continue
                         if self.app:
                             self.app.error_logging(f"Could not process EXIF during rotation: {exif_error}", level="WARNING")
                         final_exif = original_exif # Fallback
                
                if final_exif:
                    save_kwargs["exif"] = final_exif
                
                rotated.save(current_image_path, format=save_format, **save_kwargs)
            
            # Update the display if this image is currently shown
            # Check if app and current_image_path attribute exist and match
            if self.app and hasattr(self.app, 'current_image_path') and self.app.current_image_path == current_image_path:
                 self.load_image(current_image_path)
            
            return True, None

        except FileNotFoundError:
             error_msg = f"Image not found at {current_image_path}"
             if self.app: self.app.error_logging(error_msg, level="ERROR")
             return False, error_msg
        except Exception as e:
            error_msg = f"An error occurred while rotating the image: {e}"
            if self.app: self.app.error_logging(error_msg, level="ERROR")
            return False, error_msg

    def resize_image(self, source_path, target_path, max_width=2048):
        """
        Resizes an image to a maximum width while maintaining aspect ratio
        and saves it to the target path, handling format conversion if necessary.

        Args:
            source_path (str): The path to the source image file.
            target_path (str): The path to save the resized image file.
            max_width (int): The maximum width for the resized image.
        """
        try:
            with Image.open(source_path) as img:
                # Store original exif before transpose might modify/remove it
                original_exif = img.info.get('exif')

                # Apply EXIF orientation transpose to the image object in memory
                img = ImageOps.exif_transpose(img)

                # Calculate new size based on the (potentially rotated) image dimensions
                img_width, img_height = img.size
                if img_width > max_width:
                    ratio = max_width / img_width
                    new_height = int(img_height * ratio)
                    new_size = (max_width, new_height)
                    resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
                else:
                    # No resize needed, just use the correctly oriented image
                    resized_img = img # Use img directly, no need to copy if not resizing

                # Ensure image is in RGB mode for saving as JPG
                if resized_img.mode in ('RGBA', 'LA', 'P'):
                    # Create a white background
                    background = Image.new('RGB', resized_img.size, (255, 255, 255))
                    # Paste using alpha mask if available
                    alpha_mask = None
                    processed_img_for_paste = resized_img # Start with resized_img

                    if resized_img.mode == 'RGBA':
                         alpha_mask = resized_img.split()[-1]
                    elif resized_img.mode == 'LA':
                         alpha_mask = resized_img.split()[-1]
                    elif resized_img.mode == 'P':
                        # Check if palette has transparency
                        if 'transparency' in resized_img.info:
                             # Convert to RGBA to handle transparency mask reliably
                            processed_img_for_paste = resized_img.convert('RGBA')
                            alpha_mask = processed_img_for_paste.split()[-1]
                        # else: No transparency, convert P directly to RGB later

                    if alpha_mask:
                        background.paste(processed_img_for_paste, (0, 0), alpha_mask)
                        final_image = background
                    else: # No alpha mask needed (or P without transparency)
                         final_image = resized_img.convert('RGB')

                elif resized_img.mode != 'RGB':
                    # Convert other modes (like L, CMYK) to RGB
                    final_image = resized_img.convert('RGB')
                else:
                    # Already RGB
                    final_image = resized_img # Use resized_img directly

                # Prepare EXIF data, removing orientation tag
                final_exif = None
                if original_exif:
                    try:
                        # Find the numerical ID for the Orientation tag
                        orientation_tag_id = -1
                        for tag, name in ExifTags.TAGS.items():
                            if name == 'Orientation':
                                orientation_tag_id = tag
                                break

                        if orientation_tag_id != -1:
                            exif_dict = Image.Exif.load(original_exif)
                            # Check and remove the orientation tag if it exists
                            if orientation_tag_id in exif_dict:
                                del exif_dict[orientation_tag_id]
                            # Some EXIF data might be nested, check common IFDs (like 0th)
                            for ifd_key in list(exif_dict.keys()):
                                 if isinstance(exif_dict[ifd_key], dict) and orientation_tag_id in exif_dict[ifd_key]:
                                     del exif_dict[ifd_key][orientation_tag_id]

                            # Only dump if there's still data left after removing orientation
                            if exif_dict:
                                 final_exif = Image.Exif.dump(exif_dict)
                        else: # Orientation tag ID not found in ExifTags? Keep original.
                             final_exif = original_exif

                    except Exception as exif_error:
                        # Log error if needed, but proceed without crashing
                        if self.app:
                             self.app.error_logging(f"Could not process EXIF data from {source_path}: {exif_error}", level="WARNING")
                        # Keep original EXIF if processing failed
                        final_exif = original_exif

                save_kwargs = {"quality": 95}
                if final_exif:
                    save_kwargs["exif"] = final_exif

                # Save the final image (always as JPG) with potentially modified EXIF
                final_image.save(target_path, "JPEG", **save_kwargs)

        except FileNotFoundError:
             self.app.error_logging(f"Resize Error: Source image not found at {source_path}", level="ERROR")
             raise # Re-raise for calling function to handle
        except Exception as e:
            self.app.error_logging(f"Error resizing/saving image from {source_path} to {target_path}: {e}", level="ERROR")
            raise # Re-raise for calling function to handle

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