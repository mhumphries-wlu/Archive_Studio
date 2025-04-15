def process_split_image(self, current_image_path, current_image_row, left_image, right_image, split_type):
        try:
            # Get current sequence number from the filename
            # Handle the new format "0001_p001" by splitting on '_' and taking first part
            base_name = os.path.splitext(os.path.basename(current_image_path))[0]
            current_seq = 0
            
            # Try to extract sequence number from filename
            if '_p' in base_name:
                try:
                    current_seq = int(base_name.split('_p')[0])
                except (ValueError, IndexError):
                    # Fall back to a safe numeric value
                    current_seq = self.current_image_index + 1
            else:
                # Try to use just the numeric part if no '_p' pattern
                try:
                    current_seq = int(''.join(filter(str.isdigit, base_name)))
                except ValueError:
                    # Fall back to a safe numeric value
                    current_seq = self.current_image_index + 1
            
            # Calculate new sequence numbers for split images
            image_dir = os.path.dirname(current_image_path)
            next_images = [f for f in os.listdir(image_dir) 
                        if f.lower().endswith(('.jpg', '.jpeg')) and f != os.path.basename(current_image_path)]
            
            # Extract sequence numbers from filenames, handling the new format
            existing_numbers = []
            for fname in next_images:
                try:
                    if '_p' in fname:
                        num = int(os.path.splitext(fname)[0].split('_p')[0])
                    else:
                        num = int(''.join(filter(str.isdigit, os.path.splitext(fname)[0])))
                    existing_numbers.append(num)
                except (ValueError, IndexError):
                    continue
                    
            next_seq = max([current_seq] + existing_numbers) + 1
            
            # Generate new file names with proper sequential numbering
            left_image_path = os.path.join(image_dir, 
                                        f"{current_seq:04d}_p{current_seq:03d}.jpg")
            right_image_path = os.path.join(image_dir, 
                                        f"{next_seq:04d}_p{next_seq:03d}.jpg")

            # Ensure images are in RGB mode before saving
            left_image = left_image.convert("RGB")
            right_image = right_image.convert("RGB")
            
            # Save the split images
            left_image.save(left_image_path)
            right_image.save(right_image_path)
            
            # For the DataFrame operations, we need a safe numeric index
            # Ignore row.name completely - use the current_image_index directly
            current_index = self.current_image_index
            
            # Special handling for row name 'current'
            if isinstance(current_image_row.name, str) and current_image_row.name == 'current':
                current_index = self.current_image_index
            
            # Create new rows for the split images
            left_row = pd.DataFrame({
                'Image_Index': [current_index + 1],
                'Original_Image': [current_image_path],
                'Split_Image': [left_image_path],
                'Left_or_Right': ['Left']
            })
            
            right_row = pd.DataFrame({
                'Image_Index': [next_seq],
                'Original_Image': [current_image_path],
                'Split_Image': [right_image_path],
                'Left_or_Right': ['Right']
            })

            # Rebuild the DataFrame with the new rows
            try:
                # If current_image_row.name is a valid integer index, use it
                before_split = self.image_data.iloc[:current_index] if current_index > 0 else pd.DataFrame()
                after_split = self.image_data.iloc[current_index+1:] if current_index < len(self.image_data)-1 else pd.DataFrame()
            except Exception:
                # If there was any error with slicing, just rebuild the DataFrame completely
                # by filtering out the current row and adding the new rows
                before_split = self.image_data[self.image_data['Image_Index'] != self.current_image_index + 1]
                after_split = pd.DataFrame()
            
            # Combine everything
            self.image_data = pd.concat([
                before_split,
                left_row,
                right_row,
                after_split
            ]).reset_index(drop=True)
            
            # Update all Image_Index values to ensure proper sequence
            self.image_data['Image_Index'] = range(1, len(self.image_data) + 1)
            
            return True
            
        except Exception as e:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(current_dir)
            log_error(base_dir, "ERROR", f"Error in process_split_image", str(e))
            return False 

def split_image_manually(self):
        if not self.image_data.empty:
            try:
                # Get current image information
                current_image_row = self.image_data[self.image_data['Image_Index'] == self.current_image_index + 1].iloc[0]
                current_image_path = current_image_row['Split_Image'] if pd.notna(current_image_row['Split_Image']) else current_image_row['Original_Image']
                
                image = Image.open(current_image_path).convert("RGB")
                width, height = image.size
                
                # Check if cursor line exists and is active
                if not self.special_cursor_active:
                    messagebox.showerror("Error", "Please activate the split tool first (Ctrl+V for vertical or Ctrl+H for horizontal)")
                    return
                
                # Determine split type based on cursor state
                left_image = None
                right_image = None
                split_type = None
                
                if self.cursor_orientation == 'angled' and self.cursor_line:
                    left_image, right_image = self.angled_cursor_split(image, width, height)
                    split_type = 'angled'
                elif self.cursor_orientation == 'vertical' and self.vertical_line:
                    left_image, right_image = self.split_straight_cursor(image, width, height)
                    split_type = 'vertical'
                elif self.cursor_orientation == 'horizontal' and self.horizontal_line:
                    left_image, right_image = self.split_horizontal_cursor(image, width, height)
                    split_type = 'horizontal'
                else:
                    messagebox.showerror("Error", "Please position the split line first")
                    return
                
                if left_image is None or right_image is None:
                    messagebox.showerror("Error", "Failed to create split images")
                    return
                    
                # Process the split images
                success = self.process_split_image(current_image_path, current_image_row, left_image, right_image, split_type)
                
                if not success:
                    messagebox.showerror("Error", "Failed to process split images")
                    return
                
                # Clear cursor lines
                self.clear_cursor_lines()
                
                # Update display
                self.show_current_image()
                self.status = "changed"
                
            except Exception as e:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                base_dir = os.path.dirname(current_dir)
                log_error(base_dir, "ERROR", "Error splitting image", str(e))
                messagebox.showerror("Error", f"Error splitting image: {str(e)}") 

def split_straight_cursor(self, image, width, height):
        if self.vertical_line:
            try:
                # Get the x-coordinate of the vertical line
                canvas_x = self.image_canvas.coords(self.vertical_line)[0]
                
                # Convert from canvas coordinates to image coordinates 
                # by dividing by current_scale
                split_x = int(canvas_x / self.current_scale)
                
                # Ensure split_x is within image bounds
                split_x = max(0, min(split_x, width))
                
                # Create left and right images
                left_image = image.crop((0, 0, split_x, height))
                right_image = image.crop((split_x, 0, width, height))
                
                return left_image, right_image
            except Exception as e:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                base_dir = os.path.dirname(current_dir)
                log_error(base_dir, "ERROR", "Error in split_straight_cursor", str(e))
                return None, None
        return None, None

def angled_cursor_split(self, image, width, height):
        """Split image along the angled cursor line"""
        if self.cursor_line is None:
            return None, None
            
        try:
            # Get cursor line coordinates (canvas coordinates)
            canvas_coords = self.image_canvas.coords(self.cursor_line)
            x1, y1, x2, y2 = canvas_coords
            
            # Convert canvas coordinates to image coordinates
            x1 = int(x1 / self.current_scale)
            y1 = int(y1 / self.current_scale)
            x2 = int(x2 / self.current_scale)
            y2 = int(y2 / self.current_scale)
            
            # Create mask images
            mask = Image.new('L', (width, height), 0)
            draw = ImageDraw.Draw(mask)
            
            # Determine how to fill the mask based on original orientation
            if self.cursor_orientation == 'horizontal' or self.cursor_angle < 45 or self.cursor_angle > 315:
                # For horizontal-based splits, fill above the line
                points = [(0, 0), (width, 0), (x2, y2), (x1, y1)]
            else:
                # For vertical-based splits, fill left of the line
                points = [(0, 0), (x1, y1), (x2, y2), (0, height)]
                
            # Draw the polygon to create the mask
            draw.polygon(points, fill=255)
            
            # Create left and right images
            left_image = Image.new('RGB', (width, height), (0, 0, 0))
            right_image = Image.new('RGB', (width, height), (0, 0, 0))
            
            # Copy the appropriate parts of the original image
            left_image.paste(image, mask=mask)
            right_image.paste(image, mask=ImageChops.invert(mask))
            
            # Crop images to content
            left_bbox = left_image.convert('L').getbbox()
            right_bbox = right_image.convert('L').getbbox()
            
            if left_bbox:
                left_image = left_image.crop(left_bbox)
            if right_bbox:
                right_image = right_image.crop(right_bbox)
                
            return left_image, right_image
            
        except Exception as e:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(current_dir)
            log_error(base_dir, "ERROR", "Error in angled_cursor_split", str(e))
            return None, None 

def handle_mouse_click(self, event):
        if self.special_cursor_active and self.original_image:
            try:
                # Get the current cursor coordinates
                if self.cursor_orientation == 'angled' and self.cursor_line:
                    coords = self.image_canvas.coords(self.cursor_line)
                    if not coords:
                        return
                elif self.cursor_orientation == 'vertical' and self.vertical_line:
                    coords = self.image_canvas.coords(self.vertical_line)
                    if not coords:
                        return
                elif self.cursor_orientation == 'horizontal' and self.horizontal_line:
                    coords = self.image_canvas.coords(self.horizontal_line)
                    if not coords:
                        return
                else:
                    return

                self.call_split_image_functions()
                self.clear_cursor_lines()
                
                if self.batch_process.get():
                    # Move two images ahead after splitting
                    self.after(100, lambda: self.navigate_images(1))
                    self.after(200, lambda: self.navigate_images(1))
                    
                # Force cursor update with current mouse position
                mock_event = type('MockEvent', (), {
                    'x': self.image_canvas.winfo_pointerx() - self.image_canvas.winfo_rootx(),
                    'y': self.image_canvas.winfo_pointery() - self.image_canvas.winfo_rooty()
                })
                self.update_cursor_line(mock_event)
                    
            except Exception as e:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                base_dir = os.path.dirname(current_dir)
                log_error(base_dir, "ERROR", "Error in handle_mouse_click", str(e)) 

def commit_changes(self):
        if not self.folder_path or self.image_data.empty:
            return False

        try:
            # Set up the pass_images directory
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
            # Create the path that DataOperations expects (in subs/pass_images)
            subs_dir = os.path.join(current_script_dir, "subs")
            os.makedirs(subs_dir, exist_ok=True)
            pass_images_dir = os.path.join(subs_dir, "pass_images")
            
            # Create the pass_images directory if it doesn't exist
            os.makedirs(pass_images_dir, exist_ok=True)

            # Clear existing files in pass_images directory
            for item in os.listdir(pass_images_dir):
                item_path = os.path.join(pass_images_dir, item)
                try:
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
                except Exception as e:
                    base_dir = os.path.dirname(current_script_dir)
                    log_error(base_dir, "WARNING", f"Error deleting file {item_path}", str(e))
                    continue

            # Sort the DataFrame by Image_Index to ensure proper sequence
            sorted_data = self.image_data.sort_values('Image_Index')
            
            # Process and save images sequentially
            for i, row in sorted_data.iterrows():
                try:
                    # Create consistent naming scheme
                    new_name = f"{i+1:04d}.jpg"
                    new_path = os.path.join(pass_images_dir, new_name)
                    
                    # Determine source image - prefer Split_Image over Original_Image
                    source_path = row['Split_Image'] if pd.notna(row['Split_Image']) else row['Original_Image']
                    
                    # Copy and optimize image
                    with Image.open(source_path) as img:
                        img = img.convert('RGB')
                        img.save(new_path, 'JPEG', quality=95, optimize=True)
                        
                    # Keep track of the mapping between old and new paths
                    self.image_data.at[i, 'Final_Path'] = new_path
                    
                except Exception as e:
                    base_dir = os.path.dirname(current_script_dir)
                    log_error(base_dir, "ERROR", f"Error processing image {i+1}", str(e))
                    continue

            self.status = "saved"
            self.destroy()
            return True

        except Exception as e:
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(current_script_dir)
            log_error(base_dir, "ERROR", "Failed to save images", str(e))
            messagebox.showerror("Error", f"Failed to save images: {str(e)}")
            return False 

def crop_to_largest_white_area(self, image_path, threshold=127, margin=10):
        try:
            # Read the image
            image = cv2.imread(image_path)
            height, width = image.shape[:2]
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold
            _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
            
            # Find contours
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Find the largest contour
                largest_contour = max(contours, key=cv2.contourArea)
                
                # Get bounding rectangle with margin
                x, y, w, h = cv2.boundingRect(largest_contour)
                x = max(0, x - margin)
                y = max(0, y - margin)
                w = min(width - x, w + 2 * margin)
                h = min(height - y, h + 2 * margin)
                
                # Crop the image
                cropped = image[y:y+h, x:x+w]
                
                # Save the cropped image
                cv2.imwrite(image_path, cropped)
                
                # Force image reload if this is the current image
                current_image_row = self.image_data[self.image_data['Image_Index'] == self.current_image_index + 1].iloc[0]
                current_image_path = current_image_row['Split_Image'] if pd.notna(current_image_row['Split_Image']) else current_image_row['Original_Image']
                
                if image_path == current_image_path:
                    self.show_current_image()
                
                return True
                
        except Exception as e:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(current_dir)
            log_error(base_dir, "ERROR", "Error during auto-crop", str(e))
            messagebox.showerror("Error", f"Error during auto-crop: {str(e)}")
            return False

def show_current_image(self):
        if self.current_image_index >= len(self.image_data):
            return
            
        current_image_row = self.image_data[self.image_data['Image_Index'] == self.current_image_index + 1].iloc[0]
        
        # Determine which image path to use
        if pd.notna(current_image_row['Split_Image']):
            current_image_path = current_image_row['Split_Image']
        else:
            current_image_path = current_image_row['Original_Image']
            
        try:
            # Load and process the image
            image = Image.open(current_image_path)
            self.original_image = image  # Store the original image

            # Calculate scaling factors
            image_width, image_height = image.size
            canvas_width = self.image_canvas.winfo_width()
            canvas_height = self.image_canvas.winfo_height()
            scale_x = canvas_width / image_width
            scale_y = canvas_height / image_height
            self.current_scale = min(scale_x, scale_y)

            # Resize the image
            new_width = int(image_width * self.current_scale)
            new_height = int(image_height * self.current_scale)
            resized_image = image.resize((new_width, new_height), Image.LANCZOS)

            # Display the image
            photo = ImageTk.PhotoImage(resized_image)
            self.image_canvas.delete("all")
            self.image_canvas.image = photo
            self.image_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            self.image_canvas.config(scrollregion=self.image_canvas.bbox("all"))

            # If special cursor is active, redraw it
            if self.special_cursor_active:
                # Force cursor update with current mouse position
                mock_event = type('MockEvent', (), {
                    'x': self.image_canvas.winfo_pointerx() - self.image_canvas.winfo_rootx(),
                    'y': self.image_canvas.winfo_pointery() - self.image_canvas.winfo_rooty()
                })
                self.update_cursor_line(mock_event)
                
        except FileNotFoundError:
            messagebox.showerror("Error", "Image file not found.")  
        except Exception as e:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(current_dir)
            log_error(base_dir, "ERROR", "Error showing image", str(e)) 