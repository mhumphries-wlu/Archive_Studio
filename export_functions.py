import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import fitz
from PIL import Image

class ExportManager:
    def __init__(self, app):
        self.app = app
        
    def export(self, export_path=None):
        """
        Export the processed text to a file.
        
        Args:
            export_path (str, optional): Path where the exported file should be saved.
                If None, a file dialog will be shown.
        """
        self.app.toggle_button_state()
        
        try:
            # If no export path is provided, show file dialog
            if export_path is None:
                export_path = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("Text files", "*.txt")],
                    title="Save Exported Text As"
                )
                
                if not export_path:  # User cancelled the dialog
                    self.app.toggle_button_state()
                    return

            combined_text = ""
            
            # Combine all the text values into a single string
            for index, row in self.app.main_df.iterrows():
                text = self.app.find_right_text(index)
                
                # Add appropriate spacing between entries
                if text:
                    if text[0].isalpha():  # If text starts with a letter
                        combined_text += text
                    else:
                        combined_text += "\n\n" + text
            
            # Clean up multiple newlines
            combined_text = re.sub(r"\n{3,}", "\n\n", combined_text)
            
            # Save the combined text to the chosen file
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(combined_text)
                
            # Show success message if this was manually triggered
            if export_path is None:
                messagebox.showinfo("Success", "Text exported successfully!")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export text: {str(e)}")
            self.app.error_logging(f"Failed to export text: {str(e)}")
            
        finally:
            self.app.toggle_button_state()

    def export_single_file(self):
        self.app.toggle_button_state()        
        combined_text = ""

        # Use a file dialog to ask the user where to save the exported text
        export_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            title="Save Exported Text As"
        )
        
        # Combine all the processed_text values into a single string
        for index, row in self.app.main_df.iterrows():
            text = self.app.find_right_text(index)
            if text and text[0].isalpha():
                combined_text += text
            else:
                combined_text += "\n\n" + text

        # Delete instances of three or more newline characters in a row, replacing them with two newline characters
        combined_text = re.sub(r"\n{3,}", "\n\n", combined_text)

        if not export_path:  # User cancelled the file dialog
            self.app.toggle_button_state()
            return

        # Save the combined text to the chosen file
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(combined_text)

        self.app.toggle_button_state()

    def export_text_files(self):
        """Export each page's text as a separate text file with sequential numbering."""
        if self.app.main_df.empty:
            messagebox.showwarning("No Data", "No documents to export.")
            return

        # Ask user for base filename and directory
        save_dir = filedialog.askdirectory(title="Select Directory to Save Text Files")
        if not save_dir:
            return

        base_filename = simpledialog.askstring("Input", "Enter base filename for text files:",
                                            initialvalue="document")
        if not base_filename:
            return

        try:
            # Show progress bar
            progress_window, progress_bar, progress_label = self.app.progress_bar.create_progress_window("Exporting Text Files")
            total_pages = len(self.app.main_df)
            self.app.progress_bar.update_progress(0, total_pages)

            # Track successful exports
            successful_exports = 0

            for index, row in self.app.main_df.iterrows():
                try:
                    # Update progress
                    self.app.progress_bar.update_progress(index + 1, total_pages)

                    # Get the text using existing function
                    text = self.app.find_right_text(index)

                    # Create filename with sequential numbering
                    filename = f"{base_filename}_{index+1:04d}.txt"
                    file_path = os.path.join(save_dir, filename)

                    # Write the text to file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(text if text else '')

                    successful_exports += 1

                except Exception as e:
                    self.app.error_logging(f"Error exporting text file for index {index}: {str(e)}")
                    continue

            self.app.progress_bar.close_progress_window()

            # Show completion message
            if successful_exports == total_pages:
                messagebox.showinfo("Success", f"Successfully exported {successful_exports} text files.")
            else:
                messagebox.showwarning("Partial Success", 
                                    f"Exported {successful_exports} out of {total_pages} text files.\n"
                                    f"Check the error log for details.")

        except Exception as e:
            self.app.progress_bar.close_progress_window()
            messagebox.showerror("Error", f"Failed to export text files: {str(e)}")
            self.app.error_logging(f"Text file export error: {str(e)}")

    def export_as_pdf(self):
        """Export the document as a PDF with images and their associated text."""
        if self.app.main_df.empty:
            messagebox.showwarning("No Data", "No documents to export.")
            return

        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save PDF As"
        )
        
        if not file_path:
            return

        try:
            # Show progress bar
            progress_window, progress_bar, progress_label = self.app.progress_bar.create_progress_window("Creating PDF")
            total_pages = len(self.app.main_df)
            self.app.progress_bar.update_progress(0, total_pages)

            # Create PDF document
            doc = fitz.open()
            
            for index, row in self.app.main_df.iterrows():
                try:
                    # Update progress
                    self.app.progress_bar.update_progress(index + 1, total_pages)
                    
                    # Get image path and ensure it's absolute
                    image_path = row['Image_Path']
                    if not os.path.isabs(image_path):
                        image_path = os.path.join(self.app.project_directory, image_path)

                    # Get associated text based on Text_Toggle
                    text = self.app.find_right_text(index)

                    # Create new page at A4 size
                    page = doc.new_page(width=595, height=842)  # A4 size in points

                    try:
                        # Open image and get its size
                        img = Image.open(image_path)
                        img_width, img_height = img.size
                        img.close()

                        # Calculate scaling to fit page while maintaining aspect ratio
                        page_width = page.rect.width
                        page_height = page.rect.height
                        
                        width_scale = page_width / img_width
                        height_scale = page_height / img_height
                        scale = min(width_scale, height_scale)

                        # Insert image with proper scaling
                        page.insert_image(
                            page.rect,  # Use full page rect
                            filename=image_path,
                            keep_proportion=True
                        )

                        # Add searchable text layer
                        if text:
                            page.insert_text(
                                point=(0, 0),  # Starting position
                                text=text,
                                fontsize=1,  # Very small font size
                                color=(0, 0, 0, 0),  # Transparent color
                                render_mode=3  # Invisible but searchable
                            )

                    except Exception as e:
                        self.app.error_logging(f"Error inserting image at index {index}: {str(e)}")
                        continue

                except Exception as e:
                    self.app.error_logging(f"Error processing page {index + 1}: {str(e)}")
                    continue

            # Save the PDF with optimization for images
            doc.save(
                file_path,
                garbage=4,
                deflate=True,
                pretty=False
            )
            doc.close()

            self.app.progress_bar.close_progress_window()
            messagebox.showinfo("Success", "PDF exported successfully!")

        except Exception as e:
            self.app.progress_bar.close_progress_window()
            messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")
            self.app.error_logging(f"PDF export error: {str(e)}")

    def export_menu(self):
        """Open a GUI window for choosing export options."""
        # Create the export window
        export_window = tk.Toplevel(self.app)
        export_window.title("Export...")
        export_window.geometry("400x250")  # Reduced height since we removed the text box
        export_window.transient(self.app)  # Make window modal
        export_window.grab_set()  # Make window modal

        # Configure grid
        export_window.grid_columnconfigure(0, weight=1)
        
        # Add title label
        title_label = ttk.Label(export_window, text="Choose Export Format", font=("Arial", 12, "bold"))
        title_label.grid(row=0, column=0, pady=20, padx=10)

        # Create frame for export options
        options_frame = ttk.Frame(export_window)
        options_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        # Export option variable
        export_var = tk.StringVar(value="single_text")

        # Add radio buttons for different export options
        ttk.Radiobutton(
            options_frame, 
            text="Single Text File (Combined)", 
            variable=export_var, 
            value="single_text"
        ).grid(row=0, column=0, sticky="w", pady=5)

        ttk.Radiobutton(
            options_frame, 
            text="Separate Text Files (One per page)", 
            variable=export_var, 
            value="separate_text"
        ).grid(row=1, column=0, sticky="w", pady=5)

        ttk.Radiobutton(
            options_frame, 
            text="PDF with Images and Searchable Text", 
            variable=export_var, 
            value="pdf"
        ).grid(row=2, column=0, sticky="w", pady=5)

        # Add buttons frame
        button_frame = ttk.Frame(export_window)
        button_frame.grid(row=2, column=0, pady=20)

        def handle_export():
            export_type = export_var.get()
            export_window.destroy()
            
            if export_type == "single_text":
                self.export()
            elif export_type == "separate_text":
                self.export_text_files()
            elif export_type == "pdf":
                self.export_as_pdf()

        # Add buttons
        ttk.Button(
            button_frame, 
            text="Export", 
            command=handle_export
        ).grid(row=0, column=0, padx=5)
        
        ttk.Button(
            button_frame, 
            text="Cancel", 
            command=export_window.destroy
        ).grid(row=0, column=1, padx=5) 