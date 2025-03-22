import os
import pandas as pd
import fitz  # PyMuPDF
from tkinter import messagebox, filedialog, simpledialog

class ProjectIO:
    def __init__(self, app):
        self.app = app  # Reference to main app instance
        
    def create_new_project(self):
        if not messagebox.askyesno("New Project", "Creating a new project will reset the current application state. This action cannot be undone. Are you sure you want to proceed?"):
            return  # User chose not to proceed
        
        # Reset the application
        self.app.reset_application()

        # Enable drag and drop
        self.app.enable_drag_and_drop()

    def save_project(self):
        # If no project directory exists, call save_project_as.
        if not hasattr(self.app, 'project_directory') or not self.app.project_directory:
            self.save_project_as()
            return

        try:
            project_name = os.path.basename(self.app.project_directory)
            project_file = os.path.join(self.app.project_directory, f"{project_name}.pbf")

            # Create a copy of the DataFrame to prevent modifying the original
            save_df = self.app.main_df.copy()
            
            # Convert all absolute paths to relative paths
            for idx, row in save_df.iterrows():
                # Convert Image_Path to relative path
                if pd.notna(row['Image_Path']) and row['Image_Path']:
                    save_df.at[idx, 'Image_Path'] = self.app.get_relative_path(row['Image_Path'])
                
                # Convert Text_Path to relative path if it exists
                if pd.notna(row['Text_Path']) and row['Text_Path']:
                    save_df.at[idx, 'Text_Path'] = self.app.get_relative_path(row['Text_Path'])

            # Save the updated DataFrame with relative paths to the project file
            save_df.to_csv(project_file, index=False, encoding='utf-8')

            messagebox.showinfo("Success", f"Project saved successfully to {self.app.project_directory}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project: {e}")
            self.app.error_logging(f"Failed to save project: {e}")

    def open_project(self):
        project_directory = filedialog.askdirectory(title="Select Project Directory")
        if not project_directory:
            return

        project_name = os.path.basename(project_directory)
        project_file = os.path.join(project_directory, f"{project_name}.pbf")
        images_directory = os.path.join(project_directory, "images")

        if not os.path.exists(project_file) or not os.path.exists(images_directory):
            messagebox.showerror("Error", "Invalid project directory. Missing project file or images directory.")
            return

        try:
            # Read and process the project CSV file
            self.app.main_df = pd.read_csv(project_file, encoding='utf-8')
            
            # Ensure required text columns exist...
            for col in ["Original_Text", "First_Draft", "Final_Draft", "Text_Toggle"]:
                if col not in self.app.main_df.columns:
                    self.app.main_df[col] = ""
                else:
                    self.app.main_df[col] = self.app.main_df[col].astype('object')

            # Set project directory before resolving paths
            self.app.project_directory = project_directory
            self.app.images_directory = images_directory
            
            # The paths in the DataFrame are already relative to the project directory,
            # so we don't need to convert them again. The get_full_path method
            # will handle proper resolution when images and texts are loaded.

            # Reset page counter and load the first image and text.
            self.app.page_counter = 0
            if not self.app.main_df.empty:
                # Use get_full_path to resolve the relative path
                image_path = self.app.main_df.loc[0, 'Image_Path']
                self.app.current_image_path = self.app.get_full_path(image_path)
                self.app.image_handler.load_image(self.app.current_image_path)
                self.app.load_text()
            self.app.counter_update()

            messagebox.showinfo("Success", "Project loaded successfully.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open project: {e}")
            self.app.error_logging("Failed to open project", str(e))
    
    def save_project_as(self):
        # Ask the user to select a parent directory and project name.
        parent_directory = filedialog.askdirectory(title="Select Directory for New Project")
        if not parent_directory:
            return  # User cancelled
        project_name = simpledialog.askstring("Project Name", "Enter a name for the new project:")
        if not project_name:
            return  # User cancelled or provided an empty name

        # Create the project directory and images subfolder.
        project_directory = os.path.join(parent_directory, project_name)
        os.makedirs(project_directory, exist_ok=True)
        images_directory = os.path.join(project_directory, "images")
        os.makedirs(images_directory, exist_ok=True)

        # Path for the project file (CSV).
        project_file = os.path.join(project_directory, f"{project_name}.pbf")

        # Iterate over each row in the DataFrame.
        for index, row in self.app.main_df.iterrows():
            new_image_filename = f"{index+1:04d}_p{index+1:03d}.jpg"
            new_image_path = os.path.join(images_directory, new_image_filename)
            self.app.resize_image(row['Image_Path'], new_image_path)
            
            # Do not create a text file; store text in the DataFrame.
            new_text_path = ""  # No text file is created
            
            rel_image_path = os.path.relpath(new_image_path, project_directory)
            rel_text_path = ""  # No text file path

            self.app.main_df.at[index, 'Image_Path'] = rel_image_path
            self.app.main_df.at[index, 'Text_Path'] = rel_text_path

        # Save the DataFrame (project file) in the project directory.
        self.app.main_df.to_csv(project_file, index=False, encoding='utf-8')

        messagebox.showinfo("Success", f"Project saved successfully to {project_directory}")
        
        # Update the project directory references.
        self.app.project_directory = project_directory
        self.app.images_directory = images_directory

    def open_pdf(self, pdf_file=None):
        if pdf_file is None:
            pdf_file = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not pdf_file:
            return

        # Show progress bar immediately
        progress_window, progress_bar, progress_label = self.app.progress_bar.create_progress_window("Processing PDF")
        self.app.progress_bar.update_progress(0, 1)  # Show 0% progress immediately

        try:
            pdf_document = fitz.open(pdf_file)
            total_pages = len(pdf_document)

            # Get the starting index for new entries
            start_index = len(self.app.main_df)

            # Update progress bar with actual total
            self.app.progress_bar.update_progress(0, total_pages)

            for page_num in range(total_pages):
                self.app.progress_bar.update_progress(page_num + 1, total_pages)
            
                page = pdf_document[page_num]

                # Extract image at a lower resolution
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                temp_image_path = os.path.join(self.app.temp_directory, f"temp_page_{page_num + 1}.jpg")
                pix.save(temp_image_path)

                # Calculate new index and page number
                new_index = start_index + page_num
                new_page_num = new_index + 1

                # Resize and save the image using the existing resize_image method
                image_filename = f"{new_page_num:04d}_p{new_page_num:03d}.jpg"
                image_path = os.path.join(self.app.images_directory, image_filename)
                self.app.resize_image(temp_image_path, image_path)

                # Remove the temporary image
                os.remove(temp_image_path)

                # Extract text
                text_content = page.get_text()
                text_path = ""

                # Add to DataFrame
                new_row = pd.DataFrame({
                    "Index": [new_index],
                    "Page": [f"{new_page_num:04d}_p{new_page_num:03d}"],
                    "Original_Text": [text_content],
                    "First_Draft": [""],
                    "Final_Draft": [""],
                    "Image_Path": [image_path],
                    "Text_Path": [text_path],
                    "Text_Toggle": ["Original_Text"]
                })
                self.app.main_df = pd.concat([self.app.main_df, new_row], ignore_index=True)

            pdf_document.close()
            self.app.refresh_display()
            self.app.progress_bar.close_progress_window()
            messagebox.showinfo("Success", f"PDF processed successfully. {total_pages} pages added.")

        except Exception as e:
            self.app.progress_bar.close_progress_window()
            messagebox.showerror("Error", f"An error occurred while processing the PDF: {str(e)}")
            self.app.error_logging(f"Error in open_pdf: {str(e)}")

        finally:
            self.app.enable_drag_and_drop()
