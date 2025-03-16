import tkinter as tk
from PIL import Image, ImageTk, ImageOps

class ImageHandler:
    def __init__(self, image_display):
        self.image_display = image_display
        self.current_scale = 1
        self.original_image = None
        self.photo_image = None

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