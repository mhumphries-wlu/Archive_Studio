import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import fitz
from PIL import Image
import pandas as pd
import asyncio
import traceback

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
                    # Use get_full_path to resolve relative paths
                    image_path = self.app.get_full_path(image_path)

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
        export_window.geometry("400x300")
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

    def _standardize_place_column_names(self, df):
        """Ensure consistent naming for place columns"""
        # Map Creation_Place to Place_of_Creation if needed
        if 'Creation_Place' in df.columns and 'Place_of_Creation' not in df.columns:
            df['Place_of_Creation'] = df['Creation_Place']
            self.app.error_logging("Mapped Creation_Place to Place_of_Creation for consistency")
        # Map Place_of_Creation to Creation_Place if needed
        elif 'Place_of_Creation' in df.columns and 'Creation_Place' not in df.columns:
            df['Creation_Place'] = df['Place_of_Creation']
            self.app.error_logging("Mapped Place_of_Creation to Creation_Place for consistency")
        return df

    def export_as_csv(self, use_custom_separation=False, generate_metadata=None, single_author=None, citation=None, analyze_dates=None, text_source=None, sequential_preset=None):
        """Export metadata for each document as a CSV file."""
        if self.app.main_df.empty:
            messagebox.showwarning("No Data", "No documents to export.")
            return
            
        # Ask user for save location
        file_path = self._get_csv_save_path()
        if not file_path:
            return
            
        try:
            # Add a debug log at the start of export process
            self.app.error_logging("Starting CSV export process")
            print(f"Starting CSV export process with {len(self.app.main_df)} rows in main_df")
            
            # Check for document separators if using custom separation
            if use_custom_separation:
                documents_separated = self._check_for_document_separators()
                if not documents_separated:
                    messagebox.showwarning(
                        "Warning", 
                        "No document separators found. Falling back to Basic Pagination."
                    )
                    use_custom_separation = False
            else:
                documents_separated = False
            
            # Compile documents based on pagination method
            compiled_df = self._compile_documents(use_custom_separation, documents_separated)
            if compiled_df is None or compiled_df.empty:
                return
                
            # Ensure all required columns exist in the DataFrame
            compiled_df = self._ensure_required_columns(compiled_df)
            
            # Use the specified text source to populate the Text column
            # We will handle the renaming to 'Original_Text' later in _prepare_export_dataframe
            actual_text_source_column = 'Text' # Default
            if text_source and text_source != "Text":
                self.app.error_logging(f"Using {text_source} as the source for text data")
                
                # Determine the actual column name or method to get the text
                if text_source == "Current Display":
                    # We'll apply this later row by row if needed
                    actual_text_source_column = 'Current Display'
                elif text_source in self.app.main_df.columns:
                    actual_text_source_column = text_source
                    # Ensure this column exists in compiled_df if needed
                    if actual_text_source_column not in compiled_df.columns and actual_text_source_column in self.app.main_df.columns:
                         # Simple page-by-page copy if pagination was basic
                        if not use_custom_separation:
                             compiled_df[actual_text_source_column] = self.app.main_df[actual_text_source_column]
                        else:
                             # This case is more complex if custom separation was used;
                             # For now, we'll rely on the 'Text' column populated during compile_documents
                             self.app.error_logging(f"Warning: Cannot directly map {text_source} with custom separation. Using compiled 'Text'.")
                             actual_text_source_column = 'Text'

                else:
                    # Fallback if the specified source doesn't exist
                    self.app.error_logging(f"Warning: Text source '{text_source}' not found. Falling back to 'Text'.")
                    actual_text_source_column = 'Text'

                self.app.error_logging(f"Actual text source column identified as: {actual_text_source_column}")
            
            # Ask for metadata generation if not specified
            if generate_metadata is None:
                generate_metadata = messagebox.askyesno(
                    "Generate Metadata", 
                    "Do you want to generate metadata for each document? This may take some time depending on the number of documents."
                )
            
            # Generate metadata if requested
            if generate_metadata:
                compiled_df = self._generate_metadata(compiled_df)
            
            # Reapply single author AFTER metadata generation if it was set
            # The override logic is handled later in _prepare_export_dataframe
            if single_author:
                 self.app.error_logging(f"Single author specified: {single_author}")

            # Set citation if provided - actual inclusion handled later
            if citation:
                self.app.error_logging(f"Citation specified: {citation}")
            
            # Analyze dates if requested
            if analyze_dates is None:
                analyze_dates = messagebox.askyesno(
                    "Analyze Dates Sequentially", 
                    "Do you want to analyze dates sequentially based on document context? This may take some time."
                )
            
            sequential_preset_headers = [] # Initialize
            if analyze_dates:
                # Perform sequential analysis (this updates compiled_df in place)
                compiled_df = self._analyze_dates_sequentially(compiled_df, sequential_preset)
                # Get the headers used by the sequential preset
                sequential_preset_details = next((p for p in self.app.settings.sequential_metadata_presets
                                                 if p.get('name') == (sequential_preset or "Sequence_Dates")), None)
                if sequential_preset_details and 'required_headers' in sequential_preset_details:
                    header_value = sequential_preset_details['required_headers']
                    if isinstance(header_value, str):
                        sequential_preset_headers = [h.strip() for h in header_value.split(';') if h.strip()]
                    elif isinstance(header_value, list):
                        sequential_preset_headers = header_value # Keep as list if already list
                    self.app.error_logging(f"Sequential preset headers: {sequential_preset_headers}")

            # Standardize place column names before final preparation
            compiled_df = self._standardize_place_column_names(compiled_df)
            
            # Prepare final dataframe for export, passing necessary info
            export_df = self._prepare_export_dataframe(
                compiled_df,
                single_author=single_author,
                citation=citation,
                text_source_column=actual_text_source_column,
                sequential_preset_headers=sequential_preset_headers
            )
            
            # Save to CSV
            export_df.to_csv(file_path, index=False, encoding='utf-8')
            
            # Log export summary
            self._log_export_summary(export_df)
            
            messagebox.showinfo("Success", "CSV exported successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export CSV: {str(e)}")
            self.app.error_logging(f"CSV export error: {str(e)}\n{traceback.format_exc()}") # Add traceback
            
            # Restore original dataframe if needed
            if hasattr(self, '_original_df'):
                self.app.main_df = self._original_df
                # Refresh the UI display
                self.app.refresh_display()
                self.app.load_text()
                self.app.counter_update()
            
    def _get_csv_save_path(self):
        """Ask user for CSV save location."""
        return filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save CSV As"
        )
        
    def _check_for_document_separators(self):
        """Check if documents are separated with ***** markers."""
        try:
            # More thorough check for separators - look at each row individually
            separator_count = 0
            pages_with_separators = []
            
            for index, row in self.app.main_df.iterrows():
                text = self.app.find_right_text(index)
                if "*****" in text:
                    separator_count += text.count("*****")
                    pages_with_separators.append(index)
            
            documents_separated = separator_count > 0
            
            if documents_separated:
                print(f"Found {separator_count} document separators ('*****') across {len(pages_with_separators)} pages")
                print(f"Pages with separators: {pages_with_separators}")
            else:
                print(f"No document separators found in any pages")
                
            return documents_separated
                
        except Exception as e:
            print(f"Error checking for document separators: {str(e)}")
            self.app.error_logging(f"Error checking for document separators: {str(e)}")
            return False
            
    def _compile_documents(self, use_custom_separation, documents_separated):
        """Compile documents based on pagination method."""
        if use_custom_separation and documents_separated:
            try:
                # Create analyzer to access compile_documents functionality
                from util.AnalyzeDocuments import AnalyzeDocuments
                analyzer = AnalyzeDocuments(self.app)
                
                # Force recompile to ensure document separators are processed
                print("Compiling documents using document separators...")
                compiled_df = analyzer.compile_documents(force_recompile=True)
                
                if compiled_df is None or compiled_df.empty:
                    print("WARNING: compile_documents returned empty dataframe")
                    messagebox.showwarning("Warning", "No documents were found to export. Please check if your documents are properly separated.")
                    return None
                else:
                    print(f"Successfully compiled {len(compiled_df)} documents from separated text")
                    # Ensure we have the basic columns needed for export
                    if 'Text' not in compiled_df.columns:
                        print("Adding missing 'Text' column to compiled dataframe")
                        compiled_df['Text'] = ""
                    if 'Document_Page' not in compiled_df.columns:
                        print("Adding missing 'Document_Page' column to compiled dataframe")
                        compiled_df['Document_Page'] = compiled_df.index + 1
                    return compiled_df
            except Exception as e:
                print(f"Error compiling documents: {str(e)}")
                self.app.error_logging(f"Error compiling documents: {str(e)}")
                # Fall back to basic pagination
                messagebox.showwarning(
                    "Warning", 
                    f"Error compiling documents: {str(e)}\n\nFalling back to Basic Pagination."
                )
        
        # Basic Pagination: Each page is its own row in the CSV
        compiled_df = self.app.main_df.copy()
        
        # Make sure we have a Document_Page column
        if 'Document_Page' not in compiled_df.columns:
            compiled_df['Document_Page'] = compiled_df.index + 1
            
        return compiled_df
        
    def _ensure_required_columns(self, df):
        """Ensure all required columns exist in the DataFrame."""
        # Basic required columns - always include these
        required_columns = ['Page', 'Text', 'Citation']
        
        # Get metadata headers from settings
        try:
            # Get headers from settings if available
            metadata_headers = []
            if hasattr(self.app.settings, 'metadata_headers'):
                header_str = self.app.settings.metadata_headers
                # Process the semicolon-separated list
                metadata_headers = [h.strip().replace(" ", "_") for h in header_str.split(';') if h.strip()]
                
            # Ensure all potentially needed columns exist
            all_possible_columns = required_columns + metadata_headers + ['People', 'Places', 'Translation', 'Separated_Text', 'Creation_Place', 'Date']
            
            # Log the columns we're going to add
            self.app.error_logging(f"Ensuring these columns exist in the DataFrame: {all_possible_columns}")
            
            # Add unique columns only
            for col in set(all_possible_columns):
                if col not in df.columns:
                    df[col] = ""
                    self.app.error_logging(f"Added missing column: {col}")
                    
        except Exception as e:
            # Fallback to basic columns if there's an error
            self.app.error_logging(f"Error setting up metadata columns: {str(e)}")
            basic_columns = ['Page', 'Text', 'Citation', 'People', 'Places', 'Translation', 'Separated_Text', 'Creation_Place', 'Date']
            for col in basic_columns:
                if col not in df.columns:
                    df[col] = ""
                    self.app.error_logging(f"Added missing basic column: {col}")
                
        return df
        
    def _generate_metadata(self, compiled_df):
        """Generate metadata for documents using AI."""
        # Store the original main_df temporarily
        self._original_df = self.app.main_df.copy()
        
        try:
            # Make a copy of compiled_df to avoid modifying the original
            temp_df = compiled_df.copy()
            
            # Ensure all required columns for AI function exist
            temp_df = self._prepare_temp_df_for_ai(temp_df)
            
            # Replace the app's main_df with our temp_df temporarily
            self.app.main_df = temp_df
            
            # Call the app's AI function with the standard Metadata job
            print("Starting metadata generation with AI function...")
            self.app.ai_function(all_or_one_flag="All Pages", ai_job="Metadata")
            print("Metadata generation completed")
            
            # Retrieve the updated dataframe and copy metadata columns back
            updated_df = self.app.main_df.copy()
            compiled_df = self._copy_metadata_columns(compiled_df, updated_df)
            
        except Exception as e:
            print(f"CRITICAL ERROR in metadata generation: {str(e)}")
            self.app.error_logging(f"Critical error in metadata generation: {str(e)}")
            traceback_str = traceback.format_exc()
            print(traceback_str)
            self.app.error_logging(f"Traceback: {traceback_str}")
        
        finally:
            # Restore the original main_df
            self.app.main_df = self._original_df
            
            # Refresh the UI display
            self.app.refresh_display()
            self.app.load_text()
            self.app.counter_update()
            
        return compiled_df
        
    def _prepare_temp_df_for_ai(self, df):
        """Prepare a temporary dataframe for AI processing."""
        # Ensure all required columns for AI function exist
        text_columns = ['Text_Toggle', 'Original_Text', 'Corrected_Text', 'Formatted_Text', 'Translation', 'Separated_Text']
        for col in text_columns:
            if col not in df.columns:
                if col == 'Text_Toggle':
                    df[col] = "Original_Text"
                elif col == 'Original_Text':
                    df[col] = df['Text'] if 'Text' in df.columns else ""
                else:
                    df[col] = ""
        
        # Ensure Image_Path column exists and has values
        if 'Image_Path' not in df.columns:
            df['Image_Path'] = ""
            
        return df
        
    def _copy_metadata_columns(self, target_df, source_df):
        """Copy metadata columns from source dataframe to target dataframe."""
        try:
            # Get the metadata headers from the selected preset
            metadata_columns = []
            preset_name = ""
            
            # First try to get headers from the selected preset
            if hasattr(self.app.settings, 'metadata_preset') and hasattr(self.app.settings, 'metadata_presets'):
                preset_name = self.app.settings.metadata_preset
                # Find the selected preset
                selected_preset = next((p for p in self.app.settings.metadata_presets if p.get('name') == preset_name), None)
                
                if selected_preset and 'metadata_headers' in selected_preset:
                    # Get headers from the selected preset
                    header_str = selected_preset['metadata_headers']
                    self.app.error_logging(f"Using metadata headers from preset '{preset_name}': {header_str}")
                    # Process the semicolon-separated list, converting to dataframe column names
                    metadata_columns = [h.strip().replace(" ", "_") for h in header_str.split(';') if h.strip()]
            
            # Fallback to settings metadata_headers if preset headers not found
            if not metadata_columns and hasattr(self.app.settings, 'metadata_headers'):
                header_str = self.app.settings.metadata_headers
                self.app.error_logging(f"Fallback to global metadata_headers: {header_str}")
                # Process the semicolon-separated list, converting to dataframe column names
                metadata_columns = [h.strip().replace(" ", "_") for h in header_str.split(';') if h.strip()]
            
            # Add default columns if no settings found
            if not metadata_columns:
                metadata_columns = [
                    'Document_Type', 'Author', 'Correspondent', 'Correspondent_Place',
                    'Creation_Place', 'Date', 'Places', 'People', 'Summary'
                ]
                self.app.error_logging(f"Using default metadata columns: {metadata_columns}")
            
            # Always ensure Creation_Place and Date are included in metadata columns
            essential_columns = ['Creation_Place', 'Date']
            for col in essential_columns:
                if col not in metadata_columns:
                    metadata_columns.append(col)
                    self.app.error_logging(f"Added essential column: {col}")
            
            # Log the columns we'll be copying
            self.app.error_logging(f"Metadata columns to copy: {metadata_columns}")
            
            # Create counter for updates
            update_counts = {col: 0 for col in metadata_columns}
            
            # Copy each column if it exists
            for col in metadata_columns:
                if col in source_df.columns:
                    # Check if column exists in target_df
                    if col not in target_df.columns:
                        target_df[col] = ""
                        self.app.error_logging(f"Created missing column in target: {col}")
                    
                    # Copy values from source to target
                    target_df[col] = source_df[col]
                    # Count non-empty values
                    update_counts[col] = source_df[col].notna().sum()
                    self.app.error_logging(f"Copied {update_counts[col]} values for column: {col}")
                else:
                    self.app.error_logging(f"Column not found in source dataframe: {col}")
                    
                    # Check if there's an alternate name for this column
                    alt_names = {
                        'Creation_Place': 'Place_of_Creation',
                        'Place_of_Creation': 'Creation_Place'
                    }
                    
                    if col in alt_names and alt_names[col] in source_df.columns:
                        alt_col = alt_names[col]
                        if col not in target_df.columns:
                            target_df[col] = ""
                        
                        # Copy from alternate column name
                        target_df[col] = source_df[alt_col]
                        update_counts[col] = source_df[alt_col].notna().sum()
                        self.app.error_logging(f"Copied {update_counts[col]} values from alternate column {alt_col} to {col}")
            
            # Print summary of updates
            print("\nMetadata generation summary:")
            for col, count in update_counts.items():
                print(f"  {col}: {count} entries")
            
        except Exception as e:
            self.app.error_logging(f"Error copying metadata columns: {str(e)}")
            print(f"Error copying metadata columns: {str(e)}")
            
        return target_df
        
    def _analyze_dates_sequentially(self, compiled_df, preset_name=None):
        """Analyze dates sequentially based on document context."""
        try:
            # Use the existing progress bar
            progress_window, progress_bar, progress_label = self.app.progress_bar.create_progress_window("Analyzing Dates and Places Sequentially")
            
            # Update progress initially
            total_rows = len(compiled_df)
            self.app.progress_bar.update_progress(0, total_rows)
            progress_label.config(text="Preparing date and place analysis...")
            self.app.update_idletasks()
            
            # Import required modules
            from util.AnalyzeDate import analyze_dates, DateAnalyzer
            from util.APIHandler import APIHandler
            
            # Log the start of date analysis
            self.app.error_logging(f"Starting date and place analysis sequence using preset: {preset_name if preset_name else 'default'}")
            
            # Save the preset name for later use
            self._sequential_preset_used = preset_name
            
            # Create date analysis dataframe
            date_df = self._prepare_date_df(compiled_df)
            
            # Initialize API handler
            api_handler = APIHandler(
                self.app.settings.openai_api_key,
                self.app.settings.anthropic_api_key,
                self.app.settings.google_api_key
            )
            
            # Update progress
            progress_label.config(text="Starting date and place analysis...")
            self.app.update_idletasks()
            
            # Run date analysis
            result_df = self._run_date_analysis(api_handler, date_df, preset_name)
            
            # Log the result dataframe structure and first few rows
            if result_df is not None:
                self.app.error_logging(f"Date analysis returned dataframe with columns: {', '.join(result_df.columns.tolist())}")
                sample_rows = min(3, len(result_df))
                for i in range(sample_rows):
                    row_data = {col: result_df.iloc[i][col] for col in result_df.columns}
                    self.app.error_logging(f"Sample row {i}: {row_data}")
            
            # Update progress
            progress_label.config(text="Finalizing date and place analysis...")
            self.app.update_idletasks()
            
            # Copy results back to compiled_df
            if result_df is not None:
                compiled_df = self._copy_date_results(compiled_df, result_df)
            
            # Clear the preset name after use
            self._sequential_preset_used = None
            
            # Close progress window
            self.app.progress_bar.close_progress_window()
            
        except Exception as e:
            # Clear the preset name if there was an error
            self._sequential_preset_used = None
            
            # Close progress window if open
            try:
                self.app.progress_bar.close_progress_window()
            except:
                pass
            
            self.app.error_logging(f"Date and place analysis failed: {str(e)}")
            messagebox.showerror("Error", f"Failed to analyze dates and places: {str(e)}")
            
        return compiled_df
        
    def _prepare_date_df(self, compiled_df):
        """Prepare dataframe for date analysis."""
        # Get required headers from sequential metadata preset
        required_headers = []
        if hasattr(self, '_sequential_preset_used') and self._sequential_preset_used:
            # Try to find the specified preset
            sequence_preset = next((p for p in self.app.settings.sequential_metadata_presets 
                                   if p.get('name') == self._sequential_preset_used), None)
            if sequence_preset and 'required_headers' in sequence_preset:
                # Handle both string and list formats for backward compatibility
                header_value = sequence_preset['required_headers']
                if isinstance(header_value, str):
                    # Split semicolon-delimited string
                    required_headers = [h.strip() for h in header_value.split(';') if h.strip()]
                elif isinstance(header_value, list):
                    # Already a list
                    required_headers = header_value
                self.app.error_logging(f"Using required headers from sequential preset: {required_headers}")
        
        # Default required headers if none found in preset
        if not required_headers:
            required_headers = ["Date", "Creation_Place"]
        
        # Clear the required columns in compiled_df to ensure fresh analysis
        self.app.error_logging("Clearing existing values for fresh date analysis")
        for header in required_headers:
            if header in compiled_df.columns:
                compiled_df[header] = ""
        
        # Create a date analysis dataframe from the compiled_df
        date_df = pd.DataFrame()
        date_df['Page'] = compiled_df.index
        
        # Get text for each row
        text_values = []
        for idx in compiled_df.index:
            row_text = "" # Default to empty
            try:
                # Try getting text from compiled_df first
                if 'Text' in compiled_df.columns:
                    compiled_text = compiled_df.at[idx, 'Text']
                    # Check if it's a non-empty, non-whitespace string
                    if pd.notna(compiled_text) and isinstance(compiled_text, str) and compiled_text.strip():
                        row_text = compiled_text
                        # self.app.error_logging(f"Idx {idx}: Using text from compiled_df: '{row_text[:50]}...'") # Optional debug log
                
                # If text from compiled_df wasn't usable, fall back to find_right_text
                if not row_text:
                    # Fallback to find_right_text with the corresponding main_df index
                    # Ensure index mapping is safe, especially after custom separation
                    main_idx = -1
                    if 'Document_Page' in compiled_df.columns:
                        # If custom separation was used, Document_Page might hold the original starting page index
                        try:
                            main_idx = int(compiled_df.at[idx, 'Document_Page']) -1 # Adjust to 0-based
                        except (ValueError, TypeError):
                            main_idx = idx # Fallback if Document_Page is not a number
                    else:
                        # If basic pagination, index should align
                        main_idx = idx

                    if 0 <= main_idx < len(self.app.main_df):
                        fallback_text = self.app.find_right_text(main_idx)
                        if fallback_text and fallback_text.strip():
                            row_text = fallback_text
                            # self.app.error_logging(f"Idx {idx}: Using fallback text from main_df[{main_idx}]: '{row_text[:50]}...'") # Optional debug log
                        # else:
                            # self.app.error_logging(f"Idx {idx}: Fallback text from main_df[{main_idx}] was empty.") # Optional debug log
                    # else:
                        # self.app.error_logging(f"Idx {idx}: Invalid main_idx ({main_idx}) for fallback.") # Optional debug log

                text_values.append(row_text)

            except Exception as text_err:
                self.app.error_logging(f"Error getting text for date analysis at idx {idx}: {str(text_err)}")
                text_values.append("") # Append empty string on error

        date_df['Text'] = text_values
        
        # Add columns for all required headers
        for header in required_headers:
            # Initialize the column in date_df
            date_df[header] = ""
            
            # If header exists in compiled_df, copy any existing values
            if header in compiled_df.columns:
                date_df[header] = compiled_df[header].apply(lambda x: str(x) if not pd.isna(x) else "")
                self.app.error_logging(f"Copied existing {header} values from compiled_df to date_df")
        
        # Ensure legacy Creation_Place column exists
        if 'Creation_Place' not in date_df.columns and 'Creation_Place' not in required_headers:
            date_df['Creation_Place'] = ""
            if 'Creation_Place' in compiled_df.columns:
                date_df['Creation_Place'] = compiled_df['Creation_Place'].apply(lambda x: str(x) if not pd.isna(x) else "")
            self.app.error_logging("Added legacy Creation_Place column to date_df")
        
        # Log dataframe creation
        self.app.error_logging(f"Created date analysis dataframe with {len(date_df)} rows and columns: {date_df.columns.tolist()}")
        
        return date_df
        
    def _run_date_analysis(self, api_handler, date_df, preset_name=None):
        """Run date analysis using asyncio."""
        try:
            print("Setting up asyncio event loop for date analysis")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Check for required headers in sequential metadata presets
            required_headers = []
            
            # Find the specified preset if provided
            if preset_name:
                sequence_dates_preset = next((p for p in self.app.settings.sequential_metadata_presets if p.get('name') == preset_name), None)
                if sequence_dates_preset:
                    self.app.error_logging(f"Using specified sequential preset: {preset_name}")
                else:
                    self.app.error_logging(f"Specified preset '{preset_name}' not found, falling back to default")
            else:
                # Default to Sequence_Dates preset
                sequence_dates_preset = next((p for p in self.app.settings.sequential_metadata_presets if p.get('name') == "Sequence_Dates"), None)
                
            if sequence_dates_preset and 'required_headers' in sequence_dates_preset:
                # Handle both string and list formats for backward compatibility
                header_value = sequence_dates_preset['required_headers']
                if isinstance(header_value, str):
                    # Split semicolon-delimited string
                    required_headers = [h.strip() for h in header_value.split(';') if h.strip()]
                elif isinstance(header_value, list):
                    # Already a list
                    required_headers = header_value
                self.app.error_logging(f"Found required headers in sequence preset: {required_headers}")
                
                # Ensure all required columns exist in the dataframe
                for header in required_headers:
                    if header not in date_df.columns:
                        date_df[header] = ""
                        self.app.error_logging(f"Added missing required column {header} to date analysis dataframe")
            
            # Process rows and update progress bar
            async def process_with_progress():
                from util.AnalyzeDate import DateAnalyzer, analyze_dates
                
                # Set up the analyzer for progress reporting
                analyzer = DateAnalyzer(api_handler, self.app.settings)
                analyzer.set_progress_callback(lambda current, total: 
                    self.app.progress_bar.update_progress(current, total))
                
                # Set the active preset if specified
                if preset_name:
                    self.app.error_logging(f"Setting active sequential preset to: {preset_name}")
                    analyzer.active_preset_name = preset_name
                
                # Process the dataframe using the analyzer directly
                return await analyzer.process_dataframe(date_df)
            
            result = loop.run_until_complete(process_with_progress())
            loop.close()
            print("Date analysis completed successfully")
            
            # Additional logging for result dataframe
            if result is not None:
                # Log column information
                self.app.error_logging(f"Date analysis result dataframe has columns: {result.columns.tolist()}")
                
                # Log row count
                self.app.error_logging(f"Date analysis result dataframe has {len(result)} rows")
                
                # Log dates found
                date_count = sum(result['Date'].notna() & (result['Date'] != ""))
                self.app.error_logging(f"Date analysis found {date_count} dates")
                
                # Check each required header and log count of non-empty values
                if sequence_dates_preset and 'required_headers' in sequence_dates_preset:
                    for header in required_headers:
                        if header in result.columns:
                            value_count = sum(result[header].notna() & (result[header] != ""))
                            self.app.error_logging(f"Date analysis found {value_count} {header} values")
                
                # Sample first few rows
                if len(result) > 0:
                    sample_size = min(3, len(result))
                    for i in range(sample_size):
                        # Create sample with all columns that have data
                        sample_data = {}
                        for col in result.columns:
                            if pd.notna(result.iloc[i].get(col)) and result.iloc[i].get(col) != "":
                                sample_data[col] = result.iloc[i].get(col)
                        self.app.error_logging(f"Sample row {i}: {sample_data}")
            else:
                self.app.error_logging("Date analysis returned None result")
            
            return result
        except Exception as e:
            self.app.error_logging(f"Error in asyncio loop: {str(e)}")
            traceback_str = traceback.format_exc()
            self.app.error_logging(f"Traceback: {traceback_str}")
            return None
            
    def _copy_date_results(self, compiled_df, result_df):
        """Copy date analysis results back to the compiled dataframe."""
        # Check for required headers in sequential metadata presets
        required_headers = []
        
        # First try to find the preset that was used for the analysis
        preset_name = None
        if hasattr(self, '_sequential_preset_used') and self._sequential_preset_used:
            preset_name = self._sequential_preset_used
            self.app.error_logging(f"Using specified sequential preset for copying results: {preset_name}")
        
        # Find the appropriate preset
        sequence_dates_preset = None
        if preset_name:
            # Try to find the specified preset
            sequence_dates_preset = next((p for p in self.app.settings.sequential_metadata_presets if p.get('name') == preset_name), None)
            if not sequence_dates_preset:
                self.app.error_logging(f"Specified preset '{preset_name}' not found, falling back to Sequence_Dates")
        
        # Fall back to Sequence_Dates if no preset was specified or found
        if not sequence_dates_preset:
            sequence_dates_preset = next((p for p in self.app.settings.sequential_metadata_presets if p.get('name') == "Sequence_Dates"), None)
            
        # Get required headers from the preset
        if sequence_dates_preset and 'required_headers' in sequence_dates_preset:
            # Handle both string and list formats for backward compatibility
            header_value = sequence_dates_preset['required_headers']
            if isinstance(header_value, str):
                # Split semicolon-delimited string
                required_headers = [h.strip() for h in header_value.split(';') if h.strip()]
            elif isinstance(header_value, list):
                # Already a list
                required_headers = header_value
            self.app.error_logging(f"Copying required headers from sequence preset: {required_headers}")
        else:
            # Default to basic headers if no preset found
            required_headers = ["Date", "Creation_Place"]
            self.app.error_logging(f"Using default required headers: {required_headers}")
        
        # Ensure all required columns exist in target dataframe
        for header in required_headers:
            if header not in compiled_df.columns:
                compiled_df[header] = ""
                self.app.error_logging(f"Added missing {header} column to compiled_df before copying results")
        
        # Ensure legacy Creation_Place column exists in target dataframe if not in required headers
        if 'Creation_Place' not in compiled_df.columns and 'Creation_Place' not in required_headers:
            compiled_df['Creation_Place'] = ""
            self.app.error_logging("Added missing Creation_Place column to compiled_df before copying results")
        
        # Create mappings between column variations
        column_mappings = {
            'Place': ['Creation_Place', 'Place_of_Creation'],
            'Creation_Place': ['Place', 'Place_of_Creation'],
            'Place_of_Creation': ['Place', 'Creation_Place']
        }
        
        # Track updates for each field
        update_counts = {header: 0 for header in required_headers}
        legacy_counts = {'Place_of_Creation': 0, 'Creation_Place': 0}
        
        for idx in result_df.index:
            try:
                if idx < len(compiled_df):
                    # Process each required field from the preset
                    for header in required_headers:
                        # Check if the header exists directly in result_df
                        if header in result_df.columns and pd.notna(result_df.at[idx, header]) and result_df.at[idx, header]:
                            # Copy the value directly
                            compiled_df.at[idx, header] = result_df.at[idx, header]
                            update_counts[header] += 1
                            
                            # Also update any mapped columns
                            if header in column_mappings:
                                for alt_col in column_mappings[header]:
                                    if alt_col in compiled_df.columns:
                                        compiled_df.at[idx, alt_col] = result_df.at[idx, header]
                                        legacy_counts[alt_col] = legacy_counts.get(alt_col, 0) + 1
                        else:
                            # Try alternate column names
                            found = False
                            if header in column_mappings:
                                for alt_col in column_mappings[header]:
                                    if alt_col in result_df.columns and pd.notna(result_df.at[idx, alt_col]) and result_df.at[idx, alt_col]:
                                        compiled_df.at[idx, header] = result_df.at[idx, alt_col]
                                        update_counts[header] += 1
                                        found = True
                                        break
                            
                            # If there are other columns in the result_df that aren't in required_headers, copy them too
                            if not found:
                                for col in result_df.columns:
                                    if col not in required_headers and col not in column_mappings.get(header, []):
                                        if pd.notna(result_df.at[idx, col]) and result_df.at[idx, col] and col not in ['Text', 'Page', 'Document_Page']:
                                            # Only copy if the column exists in target and has value
                                            if col in compiled_df.columns:
                                                compiled_df.at[idx, col] = result_df.at[idx, col]
                                                update_counts[col] = update_counts.get(col, 0) + 1
            except Exception as update_err:
                self.app.error_logging(f"Error updating fields at idx {idx}: {str(update_err)}")
                continue
        
        # Log update counts
        successful_updates = []
        for field, count in update_counts.items():
            if count > 0:
                successful_updates.append(f"{count} {field}")
                
        for field, count in legacy_counts.items():
            if count > 0 and field not in update_counts:
                successful_updates.append(f"{count} {field}")
        
        if successful_updates:
            summary_str = ", ".join(successful_updates)
            self.app.error_logging(f"Updated fields in the compiled dataframe: {summary_str}")
        else:
            self.app.error_logging("No fields were updated in the compiled dataframe")
        
        return compiled_df
        
    def _prepare_export_dataframe(self, compiled_df, single_author=None, citation=None, text_source_column='Text', sequential_preset_headers=None):
        """Prepare the final dataframe for export according to specific requirements."""
        self.app.error_logging(f"Preparing export dataframe. Text source: {text_source_column}")
        export_df = compiled_df.copy()

        # 1. Ensure 'Page' exists and is populated
        export_df['Page'] = export_df.index + 1

        # 2. Handle Text Source and Rename to 'Original_Text'
        if text_source_column == 'Current Display':
            self.app.error_logging("Using 'Current Display' for text - applying find_right_text")
            # Apply find_right_text row by row - ensure index alignment
            original_indices = export_df.index
            text_values = []
            for idx in original_indices:
                try:
                    # Use the original index from main_df if possible
                    main_idx = idx if idx < len(self.app.main_df) else -1
                    if main_idx != -1:
                         text_values.append(self.app.find_right_text(main_idx))
                    else:
                         # Fallback if index mapping is unclear (e.g., custom separation)
                         text_values.append(export_df.at[idx, 'Text'] if 'Text' in export_df.columns else "")
                except Exception as e:
                    self.app.error_logging(f"Error getting 'Current Display' text for index {idx}: {e}")
                    text_values.append("")
            export_df['Original_Text'] = text_values
        elif text_source_column in export_df.columns:
            self.app.error_logging(f"Using column '{text_source_column}' for text")
            export_df['Original_Text'] = export_df[text_source_column]
        else:
            self.app.error_logging(f"Text source '{text_source_column}' not found, defaulting to 'Text' column")
            export_df['Original_Text'] = export_df['Text'] if 'Text' in export_df.columns else ""
            
        # Remove the original source text column if it wasn't 'Text' and exists
        if text_source_column != 'Text' and text_source_column in export_df.columns:
             try:
                 export_df = export_df.drop(columns=[text_source_column])
                 self.app.error_logging(f"Dropped original text source column: {text_source_column}")
             except KeyError:
                 self.app.error_logging(f"Could not drop original text source column: {text_source_column}")

        # 3. Define the column order
        final_columns = ['Page']

        # 4. Add 'Author' - handle single_author override here
        if 'Author' in export_df.columns:
            if single_author:
                self.app.error_logging(f"Overriding 'Author' column with single author: {single_author}")
                export_df['Author'] = single_author
            final_columns.append('Author')
        elif single_author: # Add Author column if only single_author is provided
             self.app.error_logging(f"Adding 'Author' column with single author: {single_author}")
             export_df['Author'] = single_author
             final_columns.append('Author')

        # 5. Add Metadata Headers (from the currently selected preset)
        metadata_headers = []
        if hasattr(self.app.settings, 'metadata_preset'):
            preset_name = self.app.settings.metadata_preset
            selected_preset = next((p for p in self.app.settings.metadata_presets if p.get('name') == preset_name), None)
            if selected_preset and 'metadata_headers' in selected_preset:
                header_str = selected_preset['metadata_headers']
                metadata_headers = [h.strip().replace(" ", "_") for h in header_str.split(';') if h.strip()]
                self.app.error_logging(f"Metadata headers from preset '{preset_name}': {metadata_headers}")
            else:
                 self.app.error_logging(f"Metadata preset '{preset_name}' not found or has no headers.")
        
        # Add metadata headers to final list, excluding Page and Author (already handled)
        for header in metadata_headers:
            if header not in final_columns and header in export_df.columns:
                final_columns.append(header)
            elif header not in export_df.columns:
                 self.app.error_logging(f"Metadata header '{header}' not found in compiled data.")

        # 6. Add Sequential Metadata Headers (overwriting if necessary)
        if sequential_preset_headers:
            self.app.error_logging(f"Adding/overwriting with sequential headers: {sequential_preset_headers}")
            for header in sequential_preset_headers:
                if header == 'Author' and single_author:
                    # Skip Author if single_author override is active
                    continue
                if header in export_df.columns:
                    if header not in final_columns:
                        final_columns.append(header)
                    # Overwrite logic is implicitly handled by sequential analysis results already in compiled_df
                    # and the Author override above.
                else:
                     self.app.error_logging(f"Sequential header '{header}' not found in compiled data.")

        # 7. Add 'Original_Text' column (already created and populated)
        if 'Original_Text' in export_df.columns:
            if 'Original_Text' not in final_columns:
                final_columns.append('Original_Text')
        else:
            self.app.error_logging("'Original_Text' column is missing before final ordering.")

        # 8. Add 'Citation' if provided
        if citation:
            export_df['Citation'] = citation
            if 'Citation' not in final_columns:
                 final_columns.append('Citation')
                 self.app.error_logging("Adding 'Citation' column.")

        # Ensure all columns in final_columns actually exist in the DataFrame
        existing_final_columns = [col for col in final_columns if col in export_df.columns]

        # Check for missing essential columns and log
        if 'Page' not in existing_final_columns: self.app.error_logging("CRITICAL: 'Page' column missing in final export list!")
        if 'Original_Text' not in existing_final_columns: self.app.error_logging("CRITICAL: 'Original_Text' column missing in final export list!")
        
        self.app.error_logging(f"Final ordered columns for export: {existing_final_columns}")
        
        # Return the DataFrame with only the selected and ordered columns
        return export_df[existing_final_columns]

    def _order_columns(self, columns_to_include):
        # This function is now effectively replaced by the logic in _prepare_export_dataframe
        # Keep it for potential future use or remove if confirmed obsolete.
        self.app.error_logging("Warning: _order_columns is likely obsolete due to changes in _prepare_export_dataframe.")
        return columns_to_include # Pass through for now

    def _log_export_summary(self, export_df):
        """Log summary information about the exported data."""
        print(f"Exported CSV with {len(export_df)} rows and {len(export_df.columns)} columns")
        print(f"Exported columns: {', '.join(export_df.columns.tolist())}")
        
        print("\nSample of exported data (first 3 rows):")
        sample_df = export_df.head(3) if len(export_df) >= 3 else export_df
        
        for idx, row in sample_df.iterrows():
            print(f"\nRow {idx} content:")
            for col in export_df.columns:
                value = str(row[col]).strip() if pd.notna(row[col]) else "EMPTY"
                if len(value) > 50:
                    value = value[:47] + "..."
                print(f"  {col}: {value}")

    def show_csv_export_options(self):
        """Open a window with CSV export options."""
        # Determine if documents are separated (have "*****" markers)
        documents_separated = False
        try:
            # Check if any text contains the separator
            combined_text = ""
            for index, row in self.app.main_df.iterrows():
                text = self.app.find_right_text(index)
                combined_text += text + " "
            
            documents_separated = "*****" in combined_text
        except:
            documents_separated = False

        # Create the CSV options window
        csv_window = tk.Toplevel(self.app)
        csv_window.title("CSV Export Options")
        csv_window.geometry("450x550")  # Made taller to accommodate sequential preset dropdown
        csv_window.transient(self.app)  # Make window modal
        csv_window.grab_set()  # Make window modal

        # Configure grid
        csv_window.grid_columnconfigure(0, weight=1)
        
        # Add title label
        title_label = ttk.Label(csv_window, text="CSV Export Options", font=("Arial", 12, "bold"))
        title_label.grid(row=0, column=0, pady=10, padx=10)

        # Create frame for options
        options_frame = ttk.Frame(csv_window)
        options_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        options_frame.grid_columnconfigure(1, weight=1)

        # Pagination method
        ttk.Label(options_frame, text="Pagination Method:").grid(row=0, column=0, sticky="w", pady=5)
        pagination_var = tk.StringVar(value="basic")
        pagination_combobox = ttk.Combobox(
            options_frame,
            textvariable=pagination_var,
            state="readonly",
            width=25
        )
        
        # Set combobox values
        if documents_separated:
            pagination_combobox['values'] = ["Basic Pagination", "Custom Separation"]
        else:
            pagination_combobox['values'] = ["Basic Pagination"]
            
        pagination_combobox.current(0)  # Set default to first option
        pagination_combobox.grid(row=0, column=1, sticky="w", pady=5, padx=5)

        # Description for pagination
        pagination_desc = ttk.Label(
            options_frame,
            text="Basic Pagination: Each page as separate row\nCustom Separation: Use document separators",
            font=("Arial", 8),
            justify=tk.LEFT
        )
        pagination_desc.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

        # Text source dropdown
        ttk.Label(options_frame, text="Text Source:").grid(row=2, column=0, sticky="w", pady=5)
        text_source_var = tk.StringVar(value="Current Display")
        
        # Get text source options - always include Current Display
        text_sources = ["Current Display"]
        
        # Potential text source columns to check
        potential_sources = ["Original_Text", "Corrected_Text", "Formatted_Text", "Translation", "Separated_Text"]
        
        # Add columns that actually exist in the dataframe AND have non-empty values
        for col in potential_sources + [col for col in self.app.main_df.columns if col.endswith("_Text")]:
            # Skip duplicates
            if col in text_sources:
                continue
            
            # Check if column exists and has any non-empty values
            if col in self.app.main_df.columns:
                has_data = self.app.main_df[col].notna().any() and self.app.main_df[col].astype(str).str.strip().str.len().gt(0).any()
                if has_data:
                    text_sources.append(col)
                    print(f"Adding text source with data: {col}")
        
        text_source_dropdown = ttk.Combobox(
            options_frame,
            textvariable=text_source_var,
            values=text_sources,
            state="readonly",
            width=25
        )
        text_source_dropdown.grid(row=2, column=1, sticky="w", pady=5, padx=5)
        
        # Description for text source
        text_source_desc = ttk.Label(
            options_frame,
            text="Select which text version to export in the Text column",
            font=("Arial", 8),
            justify=tk.LEFT
        )
        text_source_desc.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 10))

        # Metadata generation checkbox
        generate_metadata_var = tk.BooleanVar(value=True)
        generate_metadata_cb = ttk.Checkbutton(
            options_frame,
            text="Generate metadata for each document",
            variable=generate_metadata_var,
            command=lambda: toggle_metadata_options()
        )
        generate_metadata_cb.grid(row=4, column=0, columnspan=2, sticky="w", pady=5)

        # Create a frame for metadata options (hidden initially)
        metadata_frame = ttk.Frame(options_frame)
        metadata_frame.grid(row=5, column=0, columnspan=2, padx=20, pady=5, sticky="ew")
        metadata_frame.grid_columnconfigure(1, weight=1)

        # Metadata preset dropdown
        ttk.Label(metadata_frame, text="Metadata Preset:").grid(row=0, column=0, sticky="w", pady=5)
        metadata_preset_var = tk.StringVar()
        
        # Get preset names from settings
        preset_names = []
        if hasattr(self.app.settings, 'metadata_presets'):
            preset_names = [p['name'] for p in self.app.settings.metadata_presets]
        
        # Set initial value to the current preset if it exists
        if hasattr(self.app.settings, 'metadata_preset') and self.app.settings.metadata_preset in preset_names:
            metadata_preset_var.set(self.app.settings.metadata_preset)
        elif preset_names:
            metadata_preset_var.set(preset_names[0])
        
        metadata_preset_dropdown = ttk.Combobox(
            metadata_frame,
            textvariable=metadata_preset_var,
            values=preset_names,
            state="readonly",
            width=25
        )
        metadata_preset_dropdown.grid(row=0, column=1, sticky="w", pady=5, padx=5)
        
        # Single Author checkbox and entry
        single_author_var = tk.BooleanVar(value=False)
        single_author_cb = ttk.Checkbutton(
            metadata_frame,
            text="Single Author",
            variable=single_author_var
        )
        single_author_cb.grid(row=1, column=0, sticky="w", pady=5)

        author_var = tk.StringVar()
        author_entry = ttk.Entry(metadata_frame, textvariable=author_var, width=30)
        author_entry.grid(row=1, column=1, sticky="w", pady=5, padx=5)
        author_entry.config(state="disabled")  # Initially disabled

        # Citation entry
        ttk.Label(metadata_frame, text="Citation:").grid(row=2, column=0, sticky="w", pady=5)
        citation_var = tk.StringVar()
        citation_entry = ttk.Entry(metadata_frame, textvariable=citation_var, width=30)
        citation_entry.grid(row=2, column=1, sticky="ew", pady=5, padx=5)

        # Sequential dating checkbox
        sequential_dating_var = tk.BooleanVar(value=False)
        sequential_dating_cb = ttk.Checkbutton(
            metadata_frame,
            text="Document has sequential dating (i.e., a diary)",
            variable=sequential_dating_var,
            command=lambda: toggle_sequential_options()
        )
        sequential_dating_cb.grid(row=3, column=0, columnspan=2, sticky="w", pady=5)

        # Create a frame for sequential metadata options (hidden initially)
        sequential_frame = ttk.Frame(metadata_frame)
        sequential_frame.grid(row=4, column=0, columnspan=2, padx=20, pady=5, sticky="ew")
        sequential_frame.grid_columnconfigure(1, weight=1)

        # Sequential metadata preset dropdown
        ttk.Label(sequential_frame, text="Sequential Preset:").grid(row=0, column=0, sticky="w", pady=5)
        sequential_preset_var = tk.StringVar()
        
        # Get preset names from settings
        sequential_preset_names = []
        if hasattr(self.app.settings, 'sequential_metadata_presets'):
            sequential_preset_names = [p['name'] for p in self.app.settings.sequential_metadata_presets]
        
        # Set initial value if presets exist
        if sequential_preset_names:
            sequential_preset_var.set(sequential_preset_names[0])
        
        sequential_preset_dropdown = ttk.Combobox(
            sequential_frame,
            textvariable=sequential_preset_var,
            values=sequential_preset_names,
            state="readonly",
            width=25
        )
        sequential_preset_dropdown.grid(row=0, column=1, sticky="w", pady=5, padx=5)

        # Function to toggle author entry based on checkbox
        def toggle_author_entry():
            if single_author_var.get():
                author_entry.config(state="normal")
            else:
                author_entry.config(state="disabled")

        # Function to toggle metadata options based on checkbox
        def toggle_metadata_options():
            if generate_metadata_var.get():
                metadata_frame.grid()
            else:
                metadata_frame.grid_remove()
                
        # Function to toggle sequential options based on checkbox
        def toggle_sequential_options():
            if sequential_dating_var.get():
                sequential_frame.grid()
            else:
                sequential_frame.grid_remove()

        # Connect functions to checkboxes
        single_author_var.trace_add("write", lambda *args: toggle_author_entry())

        # Add buttons frame
        button_frame = ttk.Frame(csv_window)
        button_frame.grid(row=2, column=0, pady=20)

        def handle_csv_export():
            # Get all options
            use_custom_separation = (pagination_var.get() == "Custom Separation")
            generate_metadata = generate_metadata_var.get()
            selected_metadata_preset = metadata_preset_var.get() if generate_metadata else None
            single_author = None
            if generate_metadata and single_author_var.get():
                single_author = author_var.get()
            citation = citation_var.get() if generate_metadata else None
            analyze_dates = sequential_dating_var.get() if generate_metadata else False
            text_source = text_source_var.get()
            
            # Get sequential preset selection
            selected_sequential_preset = None
            if analyze_dates and sequential_preset_var.get():
                selected_sequential_preset = sequential_preset_var.get()

            # Update the selected metadata preset in settings if needed
            if selected_metadata_preset and hasattr(self.app.settings, 'metadata_preset'):
                self.app.settings.metadata_preset = selected_metadata_preset

            csv_window.destroy()
            
            # Call export_as_csv with all options
            self.export_as_csv(
                use_custom_separation=use_custom_separation,
                generate_metadata=generate_metadata,
                single_author=single_author,
                citation=citation,
                analyze_dates=analyze_dates,
                text_source=text_source,
                sequential_preset=selected_sequential_preset
            )

        # Add buttons
        ttk.Button(
            button_frame, 
            text="Export", 
            command=handle_csv_export
        ).grid(row=0, column=0, padx=5)
        
        ttk.Button(
            button_frame, 
            text="Cancel", 
            command=csv_window.destroy
        ).grid(row=0, column=1, padx=5)

        # Initialize the UI state
        toggle_metadata_options()
        toggle_sequential_options()  # Initialize sequential options 