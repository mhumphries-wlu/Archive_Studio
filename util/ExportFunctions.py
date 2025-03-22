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

    def export_as_csv(self, use_custom_separation=False, generate_metadata=None, single_author=None, citation=None, analyze_dates=None):
        """Export metadata for each document as a CSV file."""
        if self.app.main_df.empty:
            messagebox.showwarning("No Data", "No documents to export.")
            return
            
        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save CSV As"
        )
        
        if not file_path:
            return
            
        try:
            # Add a debug log at the start of export process
            self.app.error_logging("Starting CSV export process")
            print(f"Starting CSV export process with {len(self.app.main_df)} rows in main_df")
            
            # Check if Custom Separation is requested and available
            documents_separated = False
            if use_custom_separation:
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
                        
                except Exception as e:
                    print(f"Error checking for document separators: {str(e)}")
                    self.app.error_logging(f"Error checking for document separators: {str(e)}")
                    documents_separated = False
                
                if not documents_separated:
                    # Warn the user that Custom Separation was requested but not available
                    messagebox.showwarning(
                        "Warning", 
                        "No document separators found. Falling back to Basic Pagination."
                    )
                    use_custom_separation = False
            
            # If using custom separation, use the existing document analyzer method
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
                        return
                    else:
                        print(f"Successfully compiled {len(compiled_df)} documents from separated text")
                        # Ensure we have the basic columns needed for export
                        if 'Text' not in compiled_df.columns:
                            print("Adding missing 'Text' column to compiled dataframe")
                            compiled_df['Text'] = ""
                        if 'Document_Page' not in compiled_df.columns:
                            print("Adding missing 'Document_Page' column to compiled dataframe")
                            compiled_df['Document_Page'] = compiled_df.index + 1
                except Exception as e:
                    print(f"Error compiling documents: {str(e)}")
                    self.app.error_logging(f"Error compiling documents: {str(e)}")
                    # Fall back to basic pagination
                    messagebox.showwarning(
                        "Warning", 
                        f"Error compiling documents: {str(e)}\n\nFalling back to Basic Pagination."
                    )
                    use_custom_separation = False
                    documents_separated = False
            
            if not use_custom_separation or not documents_separated:
                # Basic Pagination: Each page is its own row in the CSV
                compiled_df = self.app.main_df.copy()
                
                # Make sure we have a Document_Page column
                if 'Document_Page' not in compiled_df.columns:
                    compiled_df['Document_Page'] = compiled_df.index + 1
            
            # Ensure all required columns exist in the DataFrame
            required_columns = [
                'Document_Type', 'Author', 'Correspondent', 'Correspondent_Place',
                'Creation_Place', 'Date', 'Places', 'People', 'Summary'
            ]
            
            for col in required_columns:
                if col not in compiled_df.columns:
                    compiled_df[col] = ""
            
            # If generate_metadata is None, it means the function was called directly
            # and we need to ask the user
            if generate_metadata is None:
                generate_metadata = messagebox.askyesno(
                    "Generate Metadata", 
                    "Do you want to generate metadata for each document? This may take some time depending on the number of documents."
                )
            
            # If single_author is provided, set it for all rows
            if single_author:
                compiled_df['Author'] = single_author
                self.app.error_logging(f"Setting single author: {single_author} for all documents")
            
            # If citation is provided, set it for all rows
            if citation:
                compiled_df['Citation'] = citation
                self.app.error_logging(f"Setting citation: {citation} for all documents")
            
            if generate_metadata:
                # Store the original main_df temporarily
                original_df = self.app.main_df.copy()
                original_update_func = self.app.update_df_with_ai_job_response
                
                try:
                    # Make a copy of compiled_df to avoid modifying the original
                    temp_df = compiled_df.copy()
                    
                    # Ensure all required columns for AI function exist
                    text_columns = ['Text_Toggle', 'Original_Text', 'First_Draft', 'Final_Draft', 'Translation']
                    for col in text_columns:
                        if col not in temp_df.columns:
                            if col == 'Text_Toggle':
                                temp_df[col] = "Original_Text"
                            elif col == 'Original_Text':
                                temp_df[col] = temp_df['Text'] if 'Text' in temp_df.columns else ""
                            else:
                                temp_df[col] = ""
                    
                    # Ensure Image_Path column exists and has values
                    if 'Image_Path' not in temp_df.columns:
                        temp_df['Image_Path'] = ""
                    
                    # Replace the app's main_df with our temp_df temporarily
                    self.app.main_df = temp_df
                    
                    # Create a wrapper for the update_df_with_ai_job_response function
                    original_update_func = self.app.update_df_with_ai_job_response
                    
                    # Create a wrapper function to handle and extract metadata
                    def metadata_response_handler(ai_job, idx, response):
                        try:
                            # First call the original function to do its normal processing
                            result = original_update_func(ai_job, idx, response)
                            
                            # Then extract and structure metadata from the response
                            print(f"Processing metadata for index {idx}")
                            success = self.extract_and_map_metadata(temp_df, idx, response)
                            if not success:
                                print(f"WARNING: Failed to extract metadata for index {idx}")
                            else:
                                print(f"Successfully extracted metadata for index {idx}")
                            
                            return result
                        except Exception as e:
                            print(f"ERROR in metadata_response_handler for index {idx}: {str(e)}")
                            self.app.error_logging(f"Error in metadata_response_handler for index {idx}: {str(e)}")
                            return None
                    
                    # Replace the app's update function with our wrapper
                    self.app.update_df_with_ai_job_response = metadata_response_handler
                    
                    # Call the app's AI function with the standard Metadata job
                    print("Starting metadata generation with AI function...")
                    # Add tracking for processed rows
                    processed_indices = set()
                    
                    # Create a wrapper for update function to track processed indices
                    original_update = self.app.update_df_with_ai_job_response
                    
                    def tracking_update_wrapper(ai_job, idx, response):
                        processed_indices.add(idx)
                        return metadata_response_handler(ai_job, idx, response)
                    
                    # Replace the wrapper
                    self.app.update_df_with_ai_job_response = tracking_update_wrapper
                    
                    self.app.ai_function(all_or_one_flag="All Pages", ai_job="Metadata")
                    print("Metadata generation completed")
                    
                    # Check if any indices were skipped
                    all_expected_indices = set(range(len(temp_df)))
                    skipped_indices = all_expected_indices - processed_indices
                    if skipped_indices:
                        print(f"WARNING: The following indices were skipped: {sorted(skipped_indices)}")
                        self.app.error_logging(f"WARNING: Skipped metadata generation for indices: {sorted(skipped_indices)}")
                    
                    # Retrieve the updated dataframe
                    updated_df = self.app.main_df.copy()
                    
                    # Copy only the metadata columns back to compiled_df
                    metadata_columns = ['Document_Type', 'Author', 'Correspondent', 'Correspondent_Place',
                                        'Creation_Place', 'Date', 'Places', 'People', 'Summary']
                    
                    update_counts = {col: 0 for col in metadata_columns}
                    for col in metadata_columns:
                        if col in updated_df.columns:
                            compiled_df[col] = updated_df[col]
                            # Count non-empty values
                            update_counts[col] = updated_df[col].notna().sum()
                    
                    # Print summary of updates
                    print("\nMetadata generation summary:")
                    for col, count in update_counts.items():
                        print(f"  {col}: {count} entries")
                    
                except Exception as e:
                    print(f"CRITICAL ERROR in metadata generation: {str(e)}")
                    self.app.error_logging(f"Critical error in metadata generation: {str(e)}")
                    traceback_str = traceback.format_exc()
                    print(traceback_str)
                    self.app.error_logging(f"Traceback: {traceback_str}")
                
                finally:
                    # Restore the original main_df and update function
                    self.app.main_df = original_df
                    self.app.update_df_with_ai_job_response = original_update_func
                    
                    # Refresh the UI display
                    self.app.refresh_display()
                    self.app.load_text()
                    self.app.counter_update()
            
            # If single_author was set, reapply it to override AI-generated values
            if single_author:
                compiled_df['Author'] = single_author
            
            # If analyze_dates is None, ask the user
            if analyze_dates is None:
                analyze_dates = messagebox.askyesno(
                    "Analyze Dates Sequentially", 
                    "Do you want to analyze dates sequentially based on document context? This may take some time."
                )
            
            if analyze_dates:
                try:
                    # Use the existing progress bar using the same approach as in TranscriptionPearl_beta-dev.py
                    progress_window, progress_bar, progress_label = self.app.progress_bar.create_progress_window("Analyzing Dates Sequentially")
                    
                    # Update progress initially
                    total_rows = len(compiled_df)
                    self.app.progress_bar.update_progress(0, total_rows)
                    progress_label.config(text="Preparing date analysis...")
                    self.app.update_idletasks()
                    
                    # Import required modules
                    from util.AnalyzeDate import analyze_dates, DateAnalyzer
                    from util.APIHandler import APIHandler
                    
                    # Log the start of date analysis
                    self.app.error_logging("Starting date analysis sequence")
                    
                    # Clear the Date column in compiled_df to ensure fresh date analysis
                    self.app.error_logging("Clearing existing dates for fresh date analysis")
                    compiled_df['Date'] = ""
                    
                    # Create a date analysis dataframe from the COMPILED_DF (after metadata generation)
                    # This is important - we use the dataframe that already has metadata
                    date_df = pd.DataFrame()
                    date_df['Page'] = compiled_df.index
                    
                    # Get text for each row - we're using find_right_text on the pages
                    text_values = []
                    for idx in compiled_df.index:
                        try:
                            # Use compiled_df's text directly or find it in main_df if needed
                            if 'Text' in compiled_df.columns and not pd.isna(compiled_df.at[idx, 'Text']):
                                text_values.append(compiled_df.at[idx, 'Text'])
                            else:
                                # Fallback to find_right_text with the corresponding main_df index
                                main_idx = idx if idx < len(self.app.main_df) else len(self.app.main_df) - 1
                                text_values.append(self.app.find_right_text(main_idx))
                        except Exception as text_err:
                            self.app.error_logging(f"Error getting text for idx {idx}: {str(text_err)}")
                            text_values.append("")
                    
                    date_df['Text'] = text_values
                    
                    # Get existing dates from compiled_df if any
                    date_df['Date'] = compiled_df['Date'].apply(lambda x: str(x) if not pd.isna(x) else "")
                    
                    # Get existing Creation_Place from compiled_df if any
                    date_df['Creation_Place'] = compiled_df['Creation_Place'].apply(lambda x: str(x) if not pd.isna(x) else "")
                    
                    # Log dataframe creation
                    self.app.error_logging(f"Created date analysis dataframe with {len(date_df)} rows")
                    
                    # Initialize API handler
                    api_handler = APIHandler(
                        self.app.settings.openai_api_key,
                        self.app.settings.anthropic_api_key,
                        self.app.settings.google_api_key
                    )
                    
                    # Update progress
                    progress_label.config(text="Starting date analysis...")
                    self.app.update_idletasks()
                    
                    # Create a function to run in the main thread
                    def run_date_analysis():
                        try:
                            self.app.error_logging("Setting up asyncio event loop for date analysis")
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            # Process rows and update progress bar
                            async def process_with_progress():
                                analyzer = DateAnalyzer(api_handler, self.app.settings)
                                analyzer.set_progress_callback(lambda current, total: 
                                    self.app.progress_bar.update_progress(current, total))
                                return await analyzer.process_dataframe(date_df)
                            
                            result = loop.run_until_complete(process_with_progress())
                            loop.close()
                            self.app.error_logging("Date analysis completed successfully")
                            return result
                        except Exception as loop_err:
                            self.app.error_logging(f"Error in asyncio loop: {str(loop_err)}")
                            return None
                    
                    # Run the function in the main thread
                    result_df = run_date_analysis()
                    
                    # Update progress
                    progress_label.config(text="Finalizing date analysis...")
                    self.app.update_idletasks()
                    
                    # Copy the dates back to compiled_df if we got results
                    if result_df is not None:
                        update_count = 0
                        place_update_count = 0
                        for idx in result_df.index:
                            try:
                                if idx < len(compiled_df):
                                    # Update Date field
                                    if result_df.at[idx, 'Date']:
                                        compiled_df.at[idx, 'Date'] = result_df.at[idx, 'Date']
                                        update_count += 1
                                    
                                    # Update Creation_Place field
                                    if 'Creation_Place' in result_df.columns and result_df.at[idx, 'Creation_Place']:
                                        compiled_df.at[idx, 'Creation_Place'] = result_df.at[idx, 'Creation_Place']
                                        place_update_count += 1
                            except Exception as update_err:
                                self.app.error_logging(f"Error updating date/place at idx {idx}: {str(update_err)}")
                                continue
                        
                        self.app.error_logging(f"Updated {update_count} dates and {place_update_count} places in the compiled dataframe")
                    else:
                        self.app.error_logging("No date analysis results returned")
                    
                    # Close progress window
                    self.app.progress_bar.close_progress_window()
                    
                except Exception as e:
                    # Close progress window if open
                    try:
                        self.app.progress_bar.close_progress_window()
                    except:
                        pass
                    
                    self.app.error_logging(f"Date analysis failed: {str(e)}")
                    messagebox.showerror("Error", f"Failed to analyze dates: {str(e)}")
            
            # List of columns to exclude from the export
            columns_to_exclude = [
                'Original_Image', 'Image_Path', 'Index', 'Query_Memory'
            ]
            
            # If we're using Basic Pagination, keep the Document_Page column
            if not use_custom_separation or not documents_separated:
                # Remove Document_Page from the exclusion list if it exists there
                if 'Document_Page' in columns_to_exclude:
                    columns_to_exclude.remove('Document_Page')
            
            # Create a copy with only the desired columns
            export_df = compiled_df.copy()
            
            # Remove unwanted columns if they exist
            for col in columns_to_exclude:
                if col in export_df.columns:
                    export_df = export_df.drop(col, axis=1)
            
            # Add a column for the page text if it doesn't exist
            if 'Text' not in export_df.columns:
                # Find the text for each page from the original dataframe
                export_df['Text'] = ""
                for idx in export_df.index:
                    if idx < len(self.app.main_df):
                        export_df.at[idx, 'Text'] = self.app.find_right_text(idx)
            
            # Add Page column if using Basic Pagination
            if not use_custom_separation and 'Document_Page' in export_df.columns:
                export_df['Page'] = export_df['Document_Page']
            elif 'Document_Page' not in export_df.columns:
                export_df['Page'] = export_df.index + 1
                
            # Add Citation column if it doesn't exist
            if 'Citation' not in export_df.columns:
                export_df['Citation'] = ""
                
            # Set citation for all rows if provided
            if citation:
                export_df['Citation'] = citation
                
            # Clear correspondent fields for non-letter document types
            for idx in export_df.index:
                doc_type = str(export_df.at[idx, 'Document_Type']).lower()
                if doc_type != 'letter' and doc_type != '':
                    export_df.at[idx, 'Correspondent'] = ""
                    export_df.at[idx, 'Correspondent_Place'] = ""
                
            # Reorder columns to match the requested order
            ordered_columns = ['Page', 'Document_Type', 'Author', 'Correspondent', 
                              'Creation_Place', 'Date', 'People', 'Places', 
                              'Summary', 'Text', 'Citation']
            
            # Filter to only include columns that exist in the dataframe
            available_columns = [col for col in ordered_columns if col in export_df.columns]
            
            # Always include all metadata columns, even if they're empty
            for col in ['Document_Type', 'Author', 'Correspondent', 'Creation_Place', 
                        'Date', 'People', 'Places', 'Summary', 'Citation']:
                if col not in available_columns and col in export_df.columns:
                    available_columns.append(col)
            
            # Create final dataframe with only the desired columns in the specified order
            # Make sure the ordered_columns values exist in available_columns
            final_columns = [col for col in ordered_columns if col in available_columns]
            final_export_df = export_df[final_columns]
            
            # Save the filtered dataframe to CSV
            final_export_df.to_csv(file_path, index=False, encoding='utf-8')
            
            # Log summary of what was exported - helps diagnose missing rows
            print(f"Exported CSV with {len(final_export_df)} rows to {file_path}")
            # Log first few rows with metadata to check if they have expected data
            print("Sample of exported data (first 3 rows):")
            sample_df = final_export_df.head(3)
            for idx, row in sample_df.iterrows():
                print(f"Row {idx} metadata status:")
                for col in ['Document_Type', 'Author', 'Date', 'Summary']:
                    if col in row and not pd.isna(row[col]) and row[col]:
                        print(f"  {col}: Present")
                    else:
                        print(f"  {col}: MISSING")
            
            messagebox.showinfo("Success", "CSV exported successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export CSV: {str(e)}")
            self.app.error_logging(f"CSV export error: {str(e)}")
            
            # Ensure the original main_df is restored
            if 'original_df' in locals():
                self.app.main_df = original_df
                # Refresh the UI display
                self.app.refresh_display()
                self.app.load_text()
                self.app.counter_update()

    def extract_and_map_metadata(self, df, idx, response):
        """
        Extract metadata from an AI response and map it to the DataFrame columns.
        
        Args:
            df (pd.DataFrame): The DataFrame to update
            idx (int): The index in the DataFrame to update
            response (str): The API response text
            
        Returns:
            bool: True if metadata was successfully processed
        """
        try:
            # Check if response is None or empty
            if not response:
                self.app.error_logging(f"Empty response for idx {idx}")
                print(f"Empty response for idx {idx}")
                return False
                
            # Log the entire response for debugging
            self.app.error_logging(f"Raw metadata response for idx {idx}:\n{response}")
                
            # Get metadata preset to find validation text
            metadata_preset = next((p for p in self.app.settings.function_presets if p.get('name') == "Metadata"), None)
            val_text = metadata_preset.get('val_text', "Metadata:") if metadata_preset else "Metadata:"
            
            # Try to find metadata even if the specific marker is not present
            metadata_text = ""
            
            # First try with the expected marker
            if val_text in response:
                metadata_text = response.split(val_text, 1)[1].strip()
                self.app.error_logging(f"Found metadata marker '{val_text}' in response")
            # Try alternate markers if the main one isn't found
            elif "Metadata:" in response:
                metadata_text = response.split("Metadata:", 1)[1].strip()
                self.app.error_logging("Using alternate 'Metadata:' marker")
            # If no markers found, try to use the whole response if it looks like metadata
            elif ":" in response and any(field in response for field in ["Document Type", "Author", "People", "Places"]):
                metadata_text = response.strip()
                self.app.error_logging("No marker found, using full response as it contains metadata fields")
            else:
                self.app.error_logging(f"No recognizable metadata format in response for idx {idx}. Full response:\n{response}")
                # Print to console as well for immediate visibility
                print(f"ERROR: No recognizable metadata format in response for idx {idx}. Full response:\n{response}")
                return False
                
            # Parse the metadata
            lines = metadata_text.split('\n')
            current_field = None
            metadata = {}
            field_values = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this line starts a new field
                if ":" in line:
                    parts = line.split(":", 1)
                    field_name = parts[0].strip()
                    value = parts[1].strip() if len(parts) > 1 else ""
                    
                    # Store field and value
                    field_values[field_name] = value
                    
                    # Start collecting multi-line fields
                    if field_name == "Summary":
                        current_field = 'Summary'
                        metadata[current_field] = value
                    else:
                        current_field = None
                elif current_field == 'Summary':
                    # Append to the existing summary
                    metadata[current_field] += " " + line
            
            # Map fields to DataFrame columns
            mapping = {
                "Document Type": "Document_Type",
                "Author": "Author",
                "Correspondent": "Correspondent",
                "Correspondent Place": "Correspondent_Place",
                "Date": "Date",
                "Place of Creation": "Creation_Place",
                "People": "People",
                "Places": "Places"
            }
            
            # Log found fields
            self.app.error_logging(f"Found metadata fields: {', '.join(field_values.keys())}")
            
            # Update DataFrame
            fields_updated = 0
            for field_name, df_column in mapping.items():
                if field_name in field_values and df_column in df.columns:
                    df.at[idx, df_column] = field_values[field_name]
                    fields_updated += 1
            
            # Set the summary if we have one
            if 'Summary' in metadata and 'Summary' in df.columns:
                df.at[idx, 'Summary'] = metadata['Summary']
                fields_updated += 1
            
            # Check if we actually updated any fields
            if fields_updated > 0:
                self.app.error_logging(f"Successfully processed {fields_updated} metadata fields for idx {idx}")
                return True
            else:
                self.app.error_logging(f"No fields were updated for idx {idx}. Parsed metadata text:\n{metadata_text}")
                # Print to console as well for immediate visibility
                print(f"ERROR: No fields were updated for idx {idx}. Parsed metadata text:\n{metadata_text}")
                # Print the fields that were found but not mapped
                print(f"Fields found in response: {list(field_values.keys())}")
                print(f"Available df columns: {list(df.columns)}")
                return False
            
        except Exception as e:
            self.app.error_logging(f"Error extracting metadata at idx {idx}: {str(e)}")
            self.app.error_logging(f"Response that caused error:\n{response}")
            # Print to console as well for immediate visibility
            print(f"ERROR: Exception extracting metadata at idx {idx}: {str(e)}")
            print(f"Response that caused error:\n{response}")
            return False

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
        csv_window.geometry("450x400")
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

        # Metadata generation checkbox
        generate_metadata_var = tk.BooleanVar(value=True)
        generate_metadata_cb = ttk.Checkbutton(
            options_frame,
            text="Generate metadata for each document",
            variable=generate_metadata_var
        )
        generate_metadata_cb.grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

        # Create a frame for metadata options (hidden initially)
        metadata_frame = ttk.Frame(options_frame)
        metadata_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=5, sticky="ew")
        metadata_frame.grid_columnconfigure(1, weight=1)

        # Single Author checkbox and entry
        single_author_var = tk.BooleanVar(value=False)
        single_author_cb = ttk.Checkbutton(
            metadata_frame,
            text="Single Author",
            variable=single_author_var
        )
        single_author_cb.grid(row=0, column=0, sticky="w", pady=5)

        author_var = tk.StringVar()
        author_entry = ttk.Entry(metadata_frame, textvariable=author_var, width=30)
        author_entry.grid(row=0, column=1, sticky="w", pady=5, padx=5)
        author_entry.config(state="disabled")  # Initially disabled

        # Citation entry
        ttk.Label(metadata_frame, text="Citation:").grid(row=1, column=0, sticky="w", pady=5)
        citation_var = tk.StringVar()
        citation_entry = ttk.Entry(metadata_frame, textvariable=citation_var, width=30)
        citation_entry.grid(row=1, column=1, sticky="ew", pady=5, padx=5)

        # Sequential dating checkbox
        sequential_dating_var = tk.BooleanVar(value=False)
        sequential_dating_cb = ttk.Checkbutton(
            metadata_frame,
            text="Document has sequential dating (i.e., a diary)",
            variable=sequential_dating_var
        )
        sequential_dating_cb.grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

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

        # Connect functions to checkboxes
        single_author_var.trace_add("write", lambda *args: toggle_author_entry())
        generate_metadata_var.trace_add("write", lambda *args: toggle_metadata_options())

        # Add buttons frame
        button_frame = ttk.Frame(csv_window)
        button_frame.grid(row=2, column=0, pady=20)

        def handle_csv_export():
            # Get all options
            use_custom_separation = (pagination_var.get() == "Custom Separation")
            generate_metadata = generate_metadata_var.get()
            single_author = None
            if generate_metadata and single_author_var.get():
                single_author = author_var.get()
            citation = citation_var.get() if generate_metadata else None
            analyze_dates = sequential_dating_var.get() if generate_metadata else False

            csv_window.destroy()
            
            # Call export_as_csv with all options
            self.export_as_csv(
                use_custom_separation=use_custom_separation,
                generate_metadata=generate_metadata,
                single_author=single_author,
                citation=citation,
                analyze_dates=analyze_dates
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