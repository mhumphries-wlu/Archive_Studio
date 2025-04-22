# util/ExportFunctions.py

# This file contains the ExportManager class, which is used to handle
# the export functions for the application.

import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import fitz
from PIL import Image
import pandas as pd
import asyncio
import traceback
import json
from util.SequentialData import call_sequential_api

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
                text = self.app.data_operations.find_right_text(index)
                
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
            text = self.app.data_operations.find_right_text(index)
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
                    text = self.app.data_operations.find_right_text(index)

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
                    text = self.app.data_operations.find_right_text(index)

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
        export_window.geometry("400x400")
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

    def export_as_csv(self, export_only_relevant=False, generate_metadata=None, selected_metadata_preset=None, single_author=None, citation=None, analyze_dates=None, text_source=None, sequential_preset=None):
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
            
            # --- Filter by Relevance if requested ---
            if export_only_relevant:
                if 'Relevance' in self.app.main_df.columns:
                    relevant_values = ["Relevant", "Partially Relevant"]
                    filtered_df = self.app.main_df[self.app.main_df['Relevance'].isin(relevant_values)].copy()
                    if filtered_df.empty:
                        messagebox.showinfo("No Relevant Data", "No relevant or partially relevant pages found to export.")
                        return
                    self.app.error_logging(f"Filtered DataFrame to {len(filtered_df)} relevant/partially relevant rows.")
                    source_df = filtered_df # Use the filtered df for the rest of the process
                else:
                    messagebox.showwarning("Relevance Column Missing", "Relevance column not found. Exporting all pages.")
                    source_df = self.app.main_df.copy() # Fallback to all pages
            else:
                source_df = self.app.main_df.copy() # Use all pages

            # Basic Pagination: Each page is its own row in the CSV
            compiled_df = source_df # Use the potentially filtered df
            
            # Make sure we have a Document_Page column using the original index
            if 'Document_Page' not in compiled_df.columns:
                compiled_df['Document_Page'] = compiled_df.index + 1

            # Ensure all required columns exist in the DataFrame
            compiled_df = self._ensure_required_columns(compiled_df)

            # Use the specified text source to populate the Text column
            # The 'text_source' parameter is already resolved by the caller (handle_csv_export)
            actual_text_source_column = 'Text' # Default fallback
            if text_source and text_source in self.app.main_df.columns:
                actual_text_source_column = text_source
                self.app.error_logging(f"Using resolved text source column: {actual_text_source_column}")
                # Ensure the source column exists in compiled_df if we need its data later
                if actual_text_source_column not in compiled_df.columns:
                    original_indices = compiled_df.index
                    compiled_df[actual_text_source_column] = self.app.main_df.loc[original_indices, actual_text_source_column]
            elif text_source:
                self.app.error_logging(f"Warning: Resolved text source '{text_source}' not found in DataFrame columns. Falling back to '{actual_text_source_column}'.")
            else:
                self.app.error_logging(f"No valid text source provided. Falling back to '{actual_text_source_column}'.")

            # Ask for metadata generation if not specified
            if generate_metadata is None:
                generate_metadata = messagebox.askyesno(
                    "Generate Metadata", 
                    "Do you want to generate metadata for each document? This may take some time depending on the number of documents."
                )
            
            # Generate metadata if requested
            if generate_metadata:
                # Pass the selected preset name to _generate_metadata
                # Also pass the resolved text source column name
                compiled_df = self._generate_metadata(
                    compiled_df,
                    selected_metadata_preset=selected_metadata_preset,
                    actual_text_source_column=actual_text_source_column
                )
            
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
            
            if analyze_dates:
                # Perform sequential analysis (this updates compiled_df in place)
                compiled_df, new_sequential_columns = self._analyze_sequential_data(compiled_df, sequential_preset)
                # Get the headers used by the sequential preset - RETAINED FOR LOGGING, NOT FOR EXPORT LIST
                sequential_preset_details = next((p for p in self.app.settings.sequential_metadata_presets
                                                 if p.get('name') == (sequential_preset or "Sequence_Dates")), None)
            else:
                 new_sequential_columns = [] # Ensure it's an empty list if not analyzing

            # Standardize place column names before final preparation
            compiled_df = self._standardize_place_column_names(compiled_df)
            
            # Prepare final dataframe for export, passing necessary info
            export_df = self._prepare_export_dataframe(
                compiled_df,
                single_author=single_author,
                citation=citation,
                text_source_column=actual_text_source_column,
                # Pass the list of new columns from sequential analysis
                new_sequential_columns=new_sequential_columns 
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
                text = self.app.data_operations.find_right_text(index)
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
                from util.CompileDocuments import CompileDocuments
                analyzer = CompileDocuments(self.app)
                
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
        
    def _generate_metadata(self, compiled_df, selected_metadata_preset=None, actual_text_source_column=None):
        """Generate metadata for documents using AI."""
        # Store the original main_df temporarily
        self._original_df = self.app.main_df.copy()
        self.app._is_generating_export_metadata = True # Add flag

        try:
            # Make a copy of compiled_df to avoid modifying the original
            temp_df = compiled_df.copy()

            # Store the original index before resetting
            temp_df_original_index = temp_df.index

            # Ensure all required columns for AI function exist
            temp_df = self._prepare_temp_df_for_ai(temp_df)

            # Reset the index for the AI function to use (0, 1, 2...)
            temp_df.reset_index(drop=True, inplace=True)
            self.app.error_logging(f"Reset index for temp_df. New length: {len(temp_df)}")

            # Replace the app's main_df with our temp_df temporarily
            self.app.main_df = temp_df

            # Call the app's AI function with the standard Metadata job
            print("Starting metadata generation with AI function...")
            # Pass the selected preset name to ai_function
            # Also pass the resolved text source column name
            self.app.ai_functions_handler.ai_function(
                all_or_one_flag="All Pages",
                ai_job="Metadata",
                selected_metadata_preset=selected_metadata_preset, # Pass the preset name here
                export_text_source=actual_text_source_column # Pass resolved source column
            )
            print("Metadata generation completed")

            # Retrieve the updated dataframe and copy metadata columns back
            updated_df = self.app.main_df.copy() # This df has index 0, 1, ...

            # Restore the original index to updated_df so it aligns with compiled_df
            if len(updated_df) == len(temp_df_original_index):
                updated_df.index = temp_df_original_index
                self.app.error_logging("Restored original index to updated_df for alignment.")
            else:
                 self.app.error_logging(f"CRITICAL: Length mismatch between updated_df ({len(updated_df)}) and original index ({len(temp_df_original_index)}). Cannot align indices reliably.", level="ERROR")
                 # Attempt partial alignment based on matching lengths if possible, or handle error
                 min_len = min(len(updated_df), len(temp_df_original_index))
                 updated_df = updated_df.iloc[:min_len]
                 updated_df.index = temp_df_original_index[:min_len]
                 messagebox.showerror("Index Alignment Error", "Could not reliably align generated metadata due to length mismatch. Results may be incomplete. Check logs.")


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

            # Determine which preset was actually used for generation
            # (This could be refined if the preset name used by AI function needs confirmation)
            preset_name_used = getattr(self.app.ai_functions_handler, 'last_used_metadata_preset', None) or getattr(self.app.settings, 'metadata_preset', None)

            # First try to get headers from the selected preset
            # Re-fetch the preset details based on the name (could be default or from dropdown)
            if preset_name_used and hasattr(self.app.settings, 'metadata_presets'):
                selected_preset = next((p for p in self.app.settings.metadata_presets if p.get('name') == preset_name_used), None)

                if selected_preset and 'metadata_headers' in selected_preset:
                    # Get headers from the selected preset
                    header_str = selected_preset['metadata_headers']
                    self.app.error_logging(f"Using metadata headers from preset '{preset_name_used}': {header_str}")
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
        
    def _analyze_sequential_data(self, compiled_df, preset_name=None):
        """Analyze sequential data in chunks, merge results, and return df and new columns."""
        new_sequential_columns = [] # Initialize
        original_columns = set(compiled_df.columns)
        result_df = pd.DataFrame() # Initialize empty result df
        progress_window, progress_bar, progress_label = None, None, None # Initialize progress bar vars

        try:
            self.app.error_logging(f"Starting sequential analysis with preset: {preset_name or 'Sequence_Dates'}", level="INFO")

            # --- Create Progress Bar ---
            total_items = len(compiled_df)
            progress_window, progress_bar, progress_label = self.app.progress_bar.create_progress_window(
                "Analyzing Sequential Data..."
            )
            self.app.progress_bar.update_progress(0, total_items)
            # --- End Progress Bar Creation ---

            # Call the API which now handles chunking and returns a combined DataFrame of results
            # Removed progress_window, progress_bar, progress_label arguments
            result_df = call_sequential_api(self.app, compiled_df, preset_name or "Sequence_Dates")

            # Check if result_df is empty (due to API errors or parsing errors in all chunks)
            if result_df.empty:
                self.app.error_logging("Sequential API calls/parsing failed to produce results DataFrame.", level="ERROR")
                return compiled_df, new_sequential_columns # Return original df and empty new columns list

            # --- Improved Debug Logging ---
            self.app.error_logging(f"Sequential API returned DataFrame with {len(result_df)} rows", level="INFO")
            if 'index' in result_df.columns:
                self.app.error_logging(f"Index range in result_df: Min={result_df['index'].min()}, Max={result_df['index'].max()}", level="INFO")
            
            # Check for indices in compiled_df that are missing in result_df
            if 'index' in result_df.columns:
                compiled_indices = set(compiled_df.index)
                result_indices = set(result_df['index'])
                missing_indices = compiled_indices - result_indices
                if missing_indices:
                    self.app.error_logging(f"Warning: {len(missing_indices)} indices from compiled_df missing in result_df: {sorted(missing_indices)}", level="WARNING")
            # --- End Improved Debug Logging ---

            # Ensure the result_df index is set correctly if 'index' column exists
            if 'index' in result_df.columns:
                 # Validate index values before setting
                 if result_df['index'].isna().any():
                     self.app.error_logging("Warning: NaN values found in 'index' column, these will be dropped when setting index", level="WARNING")
                 if result_df['index'].duplicated().any():
                     self.app.error_logging("Warning: Duplicate values found in 'index' column, later entries will override earlier ones", level="WARNING")
                     
                 # Drop rows with NaN index before setting
                 result_df = result_df.dropna(subset=['index'])
                 # Convert index to int if possible, handle potential errors
                 try:
                     result_df['index'] = result_df['index'].astype(int)
                 except ValueError:
                     self.app.error_logging("Warning: Could not convert 'index' column to int.", level="WARNING")
                     
                 result_df = result_df.set_index('index')
            else:
                 self.app.error_logging("Sequential API result DataFrame missing 'index' column for merging.", level="ERROR")
                 return compiled_df, new_sequential_columns

            # Identify new columns BEFORE merging
            original_columns = set(compiled_df.columns)
            new_sequential_columns = [col for col in result_df.columns if col not in original_columns]
            self.app.error_logging(f"Identified new sequential columns: {new_sequential_columns}", level="INFO")

            # --- Add Debug Logging --- 
            self.app.error_logging(f"Compiled DF length: {len(compiled_df)}, Result DF length: {len(result_df)}", level="INFO")
            self.app.error_logging(f"Indices in compiled_df: {sorted(compiled_df.index.tolist())[:10]} {'...' if len(compiled_df.index) > 10 else ''}", level="DEBUG")
            self.app.error_logging(f"Indices in result_df: {sorted(result_df.index.tolist())[:10]} {'...' if len(result_df.index) > 10 else ''}", level="DEBUG")
            self.app.error_logging(f"Compiled DF tail BEFORE update:\n{compiled_df.tail(3)}", level="DEBUG")
            self.app.error_logging(f"Result DF (from API) BEFORE update:\n{result_df.tail(3)}", level="DEBUG")
            # --- End Debug Logging ---

            # Preserve original compiled_df index
            compiled_df_original_index = compiled_df.index

            # Ensure compiled_df index is unique before merging
            if compiled_df.index.has_duplicates:
                self.app.error_logging(f"Warning: Duplicate indices found in compiled_df before merging sequential results. Keeping first occurrence.", level="WARNING")
                compiled_df = compiled_df[~compiled_df.index.duplicated(keep='first')]

            # Create a copy of the DataFrame before merging
            pre_merge_df = compiled_df.copy()

            # Perform a left merge on the index
            compiled_df = compiled_df.merge(result_df, how='left', left_index=True, right_index=True, suffixes=('', '_api'))

            # Prioritize API results for columns present in result_df
            for col in result_df.columns:
                api_col = col + '_api'
                if api_col in compiled_df.columns:
                    # Copy API data where it's not null, otherwise keep original
                    compiled_df[col] = compiled_df[api_col].combine_first(compiled_df[col])
                    # Drop the temporary API column
                    compiled_df = compiled_df.drop(columns=[api_col])

            # Log columns after merge and combine_first
            self.app.error_logging(f"Columns in compiled_df AFTER merge and combine_first: {compiled_df.columns.tolist()}", level="DEBUG")

            # Check for rows that should have data but don't
            expected_rows = compiled_df_original_index.tolist()
            expected_cols = new_sequential_columns
            has_missing = False
            
            for idx in expected_rows:
                for col in expected_cols:
                    if idx in compiled_df.index and idx in result_df.index:
                        if pd.isna(compiled_df.loc[idx, col]) and not pd.isna(result_df.loc[idx, col]):
                            self.app.error_logging(f"Warning: Row {idx}, column {col} has no value in result despite being in API result", level="WARNING")
                            compiled_df.loc[idx, col] = result_df.loc[idx, col] # Direct fix
                            has_missing = True
            
            if has_missing:
                self.app.error_logging("Fixed missing values after merge", level="INFO")
            # --- End Revised Merge Strategy --- 

            # Explicitly add columns that were completely new (not in original_columns)
            # This handles cases where `update` might not add columns if the index doesn't perfectly align initially
            # or if the new column was all NaN initially in compiled_df (though unlikely here)
            for col in new_sequential_columns:
                 if col not in compiled_df.columns and col in result_df.columns:
                      compiled_df[col] = result_df[col]
            
            self.app.error_logging(f"Successfully merged sequential analysis results. New columns added: {new_sequential_columns}")

            # --- Add Debug Logging --- 
            self.app.error_logging(f"Compiled DF tail AFTER update:\n{compiled_df.tail(3)}", level="DEBUG")
            # --- End Debug Logging ---

        except Exception as e:
            self.app.error_logging(f"Error during sequential data analysis or merge: {str(e)}\n{traceback.format_exc()}", level="ERROR")
            
        finally: # --- Ensure Progress Bar is Closed ---
            if progress_window:
                self.app.progress_bar.close_progress_window()
            # --- End Ensure Progress Bar is Closed ---

        # Return the modified DataFrame and the list of new column names
        # Ensure the list of new columns is accurate based on the final df state
        final_original_columns = set(pre_merge_df.columns)
        final_new_columns = [col for col in compiled_df.columns if col not in final_original_columns]
        self.app.error_logging(f"Returning final new columns: {final_new_columns}", level="INFO")
        return compiled_df, final_new_columns
        
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
                        # Corrected call: Use self.app.data_operations
                        fallback_text = self.app.data_operations.find_right_text(main_idx)
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
            import json
            print("Setting up asyncio event loop for batch date analysis")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Find the specified preset if provided
            if preset_name:
                sequence_dates_preset = next((p for p in self.app.settings.sequential_metadata_presets if p.get('name') == preset_name), None)
                if sequence_dates_preset:
                    self.app.error_logging(f"Using specified sequential preset: {preset_name}")
                else:
                    self.app.error_logging(f"Specified preset '{preset_name}' not found, falling back to default")
            else:
                sequence_dates_preset = next((p for p in self.app.settings.sequential_metadata_presets if p.get('name') == "Sequence_Dates"), None)

            # Get required headers
            required_headers = []
            if sequence_dates_preset and 'required_headers' in sequence_dates_preset:
                header_value = sequence_dates_preset['required_headers']
                if isinstance(header_value, str):
                    required_headers = [h.strip() for h in header_value.split(';') if h.strip()]
                elif isinstance(header_value, list):
                    required_headers = header_value
                self.app.error_logging(f"Found required headers in sequence preset: {required_headers}")

            # Build the batch JSON: [{"index": idx, "text": text} ...]
            batch = []
            for idx, row in date_df.iterrows():
                batch.append({"index": int(idx), "text": row["Text"]})
            batch_json = json.dumps(batch, ensure_ascii=False)

            # Compose the prompt for the model
            system_prompt = sequence_dates_preset["general_instructions"] if sequence_dates_preset else ""
            # Add explicit instruction for JSON input/output
            user_prompt = (
                "You will be given a JSON array of objects, each with an 'index' and 'text'. "
                "For each object, extract the required fields (" + ', '.join(required_headers) + ") from the text. "
                "Return a JSON array of objects, each with the same 'index' and the extracted fields as keys.\n"
                "Input JSON:\n" + batch_json + "\n\nRespond ONLY with the output JSON array."
            )
            temp = float(sequence_dates_preset.get("temperature", "0.2")) if sequence_dates_preset else 0.2
            model = sequence_dates_preset.get("model", "gemini-2.0-flash-lite") if sequence_dates_preset else "gemini-2.0-flash-lite"

            # Print the prompts for debugging
            print("\n--- SYSTEM PROMPT ---\n" + system_prompt)
            print("\n--- USER PROMPT ---\n" + user_prompt)

            # Async API call
            async def batch_call():
                response, _ = await api_handler.route_api_call(
                    engine=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temp=temp,
                    text_to_process=None,
                    val_text=None,
                    index=None,
                    is_base64=False,
                    formatting_function=True
                )
                return response

            response = loop.run_until_complete(batch_call())
            loop.close()
            print("\n--- MODEL RESPONSE ---\n" + str(response) + "\n")

            # Parse the model's JSON response
            try:
                parsed = json.loads(response)
                # Map results back to DataFrame by index
                for item in parsed:
                    idx = item.get("index")
                    for header in required_headers:
                        if header in item and idx in date_df.index:
                            date_df.at[idx, header] = item[header]
                self.app.error_logging(f"Batch date analysis: updated {len(parsed)} rows.")
            except Exception as e:
                self.app.error_logging(f"Failed to parse model JSON response: {str(e)}\nResponse was: {response}")

            return date_df
        except Exception as e:
            self.app.error_logging(f"Error in batch asyncio loop: {str(e)}")
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
        
    def _prepare_export_dataframe(self, compiled_df, single_author=None, citation=None, text_source_column='Text', new_sequential_columns=None):
        """Prepare the final dataframe for export using metadata + sequential columns."""
        self.app.error_logging(f"Preparing export dataframe. Text source: {text_source_column}, New sequential cols: {new_sequential_columns}")
        export_df = compiled_df.copy()
        
        if new_sequential_columns is None:
            new_sequential_columns = []

        # 1. Ensure 'Page' exists and is populated
        if 'Page' not in export_df.columns:
             export_df['Page'] = export_df.index + 1
        elif export_df['Page'].isna().any():
             export_df['Page'] = export_df.index + 1

        # 2. Handle Text Source and Ensure 'Original_Text' exists
        if text_source_column == 'Current Display':
            self.app.error_logging("Using 'Current Display' for text - applying find_right_text")
            original_indices = export_df.index
            text_values = []
            for idx in original_indices:
                try:
                    main_idx = idx if idx < len(self.app.main_df) else -1
                    if main_idx != -1:
                         text_values.append(self.app.data_operations.find_right_text(main_idx))
                    else:
                         text_values.append(export_df.at[idx, 'Text'] if 'Text' in export_df.columns else "")
                except Exception as e:
                    self.app.error_logging(f"Error getting 'Current Display' text for index {idx}: {e}")
                    text_values.append("")
            export_df['Original_Text'] = text_values
        elif text_source_column in export_df.columns:
            self.app.error_logging(f"Using column '{text_source_column}' for text")
            export_df['Original_Text'] = export_df[text_source_column]
        else:
            self.app.error_logging(f"Text source '{text_source_column}' not found, using 'Text' or empty")
            if 'Text' in export_df.columns:
                 export_df['Original_Text'] = export_df['Text']
            else:
                 export_df['Original_Text'] = ""
        # Ensure Original_Text column definitely exists
        if 'Original_Text' not in export_df.columns:
            export_df['Original_Text'] = ""

        # Remove the original source text column if it differs from Original_Text and Text
        if text_source_column not in ['Original_Text', 'Text'] and text_source_column in export_df.columns:
             try:
                 export_df = export_df.drop(columns=[text_source_column])
                 self.app.error_logging(f"Dropped original text source column: {text_source_column}")
             except KeyError:
                 self.app.error_logging(f"Could not drop original text source column: {text_source_column}")

        # 3. Handle Author Override
        if single_author:
            self.app.error_logging(f"Applying single author override: {single_author}")
            export_df['Author'] = single_author
        elif 'Author' not in export_df.columns:
            export_df['Author'] = "" 

        # 4. Handle Citation Override
        if citation:
            self.app.error_logging(f"Applying citation override: {citation}")
            export_df['Citation'] = citation
        elif 'Citation' not in export_df.columns:
            export_df['Citation'] = "" 

        # 5. Determine Final Columns based on Metadata + Sequential
        core_columns = ['Page', 'Original_Text']
        
        # Get metadata headers from the currently selected *metadata* preset
        metadata_headers = []
        preset_name = self.app.settings.metadata_preset
        selected_preset = next((p for p in self.app.settings.metadata_presets if p.get('name') == preset_name), None)
        if selected_preset and 'metadata_headers' in selected_preset:
            header_str = selected_preset['metadata_headers']
            # Ensure conversion to df column names (replace space with underscore)
            metadata_headers = [h.strip().replace(" ", "_") for h in header_str.split(';') if h.strip()]
            self.app.error_logging(f"Metadata headers from preset '{preset_name}': {metadata_headers}")
        else:
             self.app.error_logging(f"Metadata preset '{preset_name}' not found or has no headers.")
        
        # Combine core, metadata, and new sequential columns
        combined_columns = core_columns + metadata_headers + new_sequential_columns
        
        # Filter for existing columns and remove duplicates, maintaining order
        final_columns = []
        seen_columns = set()
        self.app.error_logging(f"Columns available in compiled_df for final selection: {compiled_df.columns.tolist()}", level="DEBUG") # Log available columns
        self.app.error_logging(f"Combined columns requested for export: {combined_columns}", level="DEBUG") # Log requested columns
        
        for col in combined_columns:
            if col in compiled_df.columns and col not in seen_columns:
                final_columns.append(col)
                seen_columns.add(col)
            elif col not in compiled_df.columns:
                 self.app.error_logging(f"Column '{col}' requested for export but not found in DataFrame.", level="WARNING")
        
        # Remove any stray index column if present
        if 'index' in final_columns: final_columns.remove('index')
        
        # Filter out columns where all values are empty/NaN
        export_ready_columns = []
        for col in final_columns:
            # Check if the column is entirely null/empty strings
            # Convert to string first to handle mixed types, strip whitespace
            is_empty = export_df[col].astype(str).str.strip().replace('nan', '', regex=False).replace('None', '', regex=False).eq('').all()
            if not is_empty:
                 export_ready_columns.append(col)
            else:
                 self.app.error_logging(f"Excluding column '{col}' from export because all values are empty.", level="INFO")
        
        self.app.error_logging(f"Final columns selected for export after empty check: {export_ready_columns}")
        
        # Return the DataFrame with only the selected and ordered columns
        return export_df[export_ready_columns]

    def _order_columns(self, columns_to_include):
        # This function is now effectively replaced by the logic in _prepare_export_dataframe
        # Keep it for potential future use or remove if confirmed obsolete.
        self.app.error_logging("Warning: _order_columns is likely obsolete due to changes in _prepare_export_dataframe.")
        return columns_to_include # Pass through for now

    def _log_export_summary(self, export_df):
        """Log summary information about the exported data."""
        print(f"Exported CSV with {len(export_df)} rows and {len(export_df.columns)} columns")
        print(f"Exported columns: {', '.join(export_df.columns.tolist())}")
        
        print("\nSample of exported data (last 3 rows):")
        sample_df = export_df.tail(3) if len(export_df) >= 3 else export_df
        
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
                text = self.app.data_operations.find_right_text(index)
                combined_text += text + " "
            
            documents_separated = "*****" in combined_text
        except:
            documents_separated = False

        # Create the CSV options window
        csv_window = tk.Toplevel(self.app)
        csv_window.title("CSV Export Options")
        csv_window.geometry("450x555")  # Increased from 530 to 555 (25px taller)
        csv_window.transient(self.app)  # Make window modal
        csv_window.grab_set()  # Make window modal

        # Store reference to the window for use in open_settings_to_tab
        self.csv_window = csv_window

        # Configure grid
        csv_window.grid_columnconfigure(0, weight=1)
        
        # Add title label
        title_label = ttk.Label(csv_window, text="CSV Export Options", font=("Arial", 12, "bold"))
        title_label.grid(row=0, column=0, pady=10, padx=10)

        # Create frame for options
        options_frame = ttk.Frame(csv_window)
        options_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        options_frame.grid_columnconfigure(1, weight=1)

        # --- Relevance Filtering Option ---
        relevance_frame = ttk.LabelFrame(options_frame, text="Page Filtering")
        relevance_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        relevance_frame.grid_columnconfigure(0, weight=1)

        export_scope_var = tk.StringVar(value="all") # Default to exporting all

        # Check if Relevance column exists and has data
        relevance_col_exists = 'Relevance' in self.app.main_df.columns
        has_relevance_data = False
        if relevance_col_exists:
            # Check for any non-empty/non-NA relevance values
            has_relevance_data = self.app.main_df['Relevance'].notna().any() and \
                                 (self.app.main_df['Relevance'].astype(str).str.strip() != '').any()

        ttk.Radiobutton(
            relevance_frame,
            text="Export All Pages",
            variable=export_scope_var,
            value="all"
        ).grid(row=0, column=0, sticky="w", pady=(5,0), padx=5)

        relevance_radio = ttk.Radiobutton(
            relevance_frame,
            text="Export Only Relevant/Partially Relevant Pages",
            variable=export_scope_var,
            value="relevant"
        )
        relevance_radio.grid(row=1, column=0, sticky="w", pady=(0,5), padx=5)

        # Disable relevance option if column doesn't exist or has no data
        if not has_relevance_data:
            relevance_radio.config(state="disabled")
            export_scope_var.set("all") # Force back to all if disabled
            # Add a label explaining why it's disabled
            disabled_label = ttk.Label(
                relevance_frame,
                text="(Enable by running Relevance Analysis first)",
                font=("Arial", 8, "italic")
            )
            disabled_label.grid(row=2, column=0, sticky="w", padx=10, pady=(0,5))
        
        # --- Text Source ---
        text_source_frame = ttk.LabelFrame(options_frame, text="Text Source")
        text_source_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        text_source_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(text_source_frame, text="Text Source:").grid(row=0, column=0, sticky="w", pady=5, padx=5)
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
            text_source_frame,
            textvariable=text_source_var,
            values=text_sources,
            state="readonly",
            width=25
        )
        text_source_dropdown.grid(row=0, column=1, sticky="w", pady=5, padx=5)

        # Description for text source
        text_source_desc = ttk.Label(
            text_source_frame,
            text="Select which text version to export in the Original_Text column",
            font=("Arial", 8),
            justify=tk.LEFT
        )
        text_source_desc.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10), padx=5)

        # --- Metadata Options ---
        metadata_options_frame = ttk.LabelFrame(options_frame, text="Metadata and Analysis")
        metadata_options_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        metadata_options_frame.grid_columnconfigure(1, weight=1)

        # Metadata generation checkbox
        generate_metadata_var = tk.BooleanVar(value=True)
        generate_metadata_cb = ttk.Checkbutton(
            metadata_options_frame,
            text="Generate/Include Metadata",
            variable=generate_metadata_var,
            command=lambda: toggle_metadata_options()
        )
        generate_metadata_cb.grid(row=0, column=0, columnspan=2, sticky="w", pady=5, padx=5)

        # Create a frame for metadata options (visible only if generate_metadata_var is True)
        metadata_frame = ttk.Frame(metadata_options_frame)
        # Don't grid remove here, rely on toggle_metadata_options initial call
        metadata_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=5, sticky="ew")

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
            width=25,
            name="metadata_preset_dropdown"
        )
        metadata_preset_dropdown.grid(row=0, column=1, sticky="w", pady=5, padx=5)

        # Add "+" button to open settings window to Metadata Presets tab
        metadata_add_button = ttk.Button(
            metadata_frame,
            text="+",
            width=2,
            command=lambda: self.open_settings_to_tab("Metadata Presets")
        )
        metadata_add_button.grid(row=0, column=2, sticky="w", pady=5, padx=0)
        
        # Create a tooltip for the button
        from util.SettingsWindow import CreateToolTip
        CreateToolTip(metadata_add_button, "Open settings to create a new metadata preset")

        # Single Author checkbox and entry
        single_author_var = tk.BooleanVar(value=False)
        single_author_cb = ttk.Checkbutton(
            metadata_frame,
            text="Single Author",
            variable=single_author_var,
            command=lambda: toggle_author_entry()
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
            text="Analyze Sequential Dates/Places",
            variable=sequential_dating_var,
            command=lambda: toggle_sequential_options()
        )
        sequential_dating_cb.grid(row=3, column=0, columnspan=2, sticky="w", pady=5)

        # Create a frame for sequential metadata options (hidden initially)
        sequential_frame = ttk.Frame(metadata_frame)
        sequential_frame.grid(row=4, column=0, columnspan=2, padx=20, pady=5, sticky="ew")
        sequential_frame.grid_remove()

        # Sequential metadata preset dropdown
        ttk.Label(sequential_frame, text="Sequential Preset:").grid(row=0, column=0, sticky="w", pady=5)
        sequential_preset_var = tk.StringVar()

        # Get preset names from settings
        sequential_preset_names = []
        if hasattr(self.app.settings, 'sequential_metadata_presets'):
            sequential_preset_names = [p['name'] for p in self.app.settings.sequential_metadata_presets]

        # Set initial value if presets exist
        if sequential_preset_names:
            # Default to 'Sequence_Dates' if available, otherwise first
            default_seq_preset = next((name for name in sequential_preset_names if name == "Sequence_Dates"), sequential_preset_names[0])
            sequential_preset_var.set(default_seq_preset)

        sequential_preset_dropdown = ttk.Combobox(
            sequential_frame,
            textvariable=sequential_preset_var,
            values=sequential_preset_names,
            state="readonly",
            width=25,
            name="sequential_preset_dropdown"
        )
        sequential_preset_dropdown.grid(row=0, column=1, sticky="w", pady=5, padx=5)
        
        # Add "+" button to open settings window to Sequential Metadata Presets tab
        sequential_add_button = ttk.Button(
            sequential_frame,
            text="+",
            width=2,
            command=lambda: self.open_settings_to_tab("Sequential Metadata Presets")
        )
        sequential_add_button.grid(row=0, column=2, sticky="w", pady=5, padx=0)
        
        # Create a tooltip for the button
        CreateToolTip(sequential_add_button, "Open settings to create a new sequential metadata preset")

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
                # Re-apply author and sequential state when shown
                toggle_author_entry()
                toggle_sequential_options()
            else:
                metadata_frame.grid_remove()

        # Function to toggle sequential options based on checkbox
        def toggle_sequential_options():
            # Only toggle if metadata options are visible
            if generate_metadata_var.get():
                if sequential_dating_var.get():
                    sequential_frame.grid()
                else:
                    sequential_frame.grid_remove()
            else: # Ensure it's hidden if metadata is off
                 sequential_frame.grid_remove()

        # Connect functions to checkboxes
        # Note: Command link added directly to Checkbutton definitions above

        # Add buttons frame
        button_frame = ttk.Frame(csv_window)
        button_frame.grid(row=3, column=0, pady=20)

        def handle_csv_export():
            # Get all options
            export_scope = export_scope_var.get() # 'all' or 'relevant'
            export_only_relevant = (export_scope == "relevant")

            generate_metadata = generate_metadata_var.get()
            selected_metadata_preset = metadata_preset_var.get() if generate_metadata else None
            single_author = None
            if generate_metadata and single_author_var.get():
                single_author = author_var.get()
            citation = citation_var.get() if generate_metadata else None
            analyze_dates = sequential_dating_var.get() if generate_metadata else False

            # Resolve text source selection
            selected_text_source_option = text_source_var.get()
            resolved_text_source = selected_text_source_option
            if selected_text_source_option == "Current Display":
                # Get the actual column name currently displayed in the main UI
                resolved_text_source = self.app.text_display_var.get()
                # Handle case where current display is "None"
                if resolved_text_source == "None":
                    messagebox.showerror("Error", "Cannot export metadata using 'Current Display' when it is set to 'None'. Please select a specific text source.")
                    return # Abort export
                self.app.error_logging(f"Resolved 'Current Display' to actual column: {resolved_text_source}")
            else:
                self.app.error_logging(f"Using specified text source column: {resolved_text_source}")

            # Get sequential preset selection
            selected_sequential_preset = None
            if analyze_dates and sequential_preset_var.get():
                selected_sequential_preset = sequential_preset_var.get()

            # Update the selected metadata preset in settings if needed
            if selected_metadata_preset and hasattr(self.app.settings, 'metadata_preset'):
                # Only update if the generation box is checked
                if generate_metadata:
                     self.app.settings.metadata_preset = selected_metadata_preset

            csv_window.destroy()

            # Call export_as_csv with all options
            self.export_as_csv(
                export_only_relevant=export_only_relevant, # Pass new flag
                generate_metadata=generate_metadata,
                selected_metadata_preset=selected_metadata_preset,
                single_author=single_author,
                citation=citation,
                analyze_dates=analyze_dates,
                text_source=resolved_text_source, # Pass the resolved source
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
        # toggle_sequential_options() # This is called within toggle_metadata_options
        toggle_author_entry() # Initialize author entry state 

    def open_settings_to_tab(self, tab_name):
        """Open the settings window to a specific tab"""
        # First close the current CSV export window if it exists
        if hasattr(self, 'csv_window') and self.csv_window.winfo_exists():
            self.csv_window.destroy()
        
        # Create a new settings window instance
        settings_window = self.app.create_settings_window_to_tab(tab_name)
        
        # Store reference to the settings window
        settings_tk_window = settings_window.settings_window
        
        # Function to check if settings window is still open
        def check_settings_window():
            try:
                # Check if settings window still exists
                if not settings_tk_window.winfo_exists():
                    # Settings window closed, reopen CSV export window
                    self.show_csv_export_options()
                    return  # Stop checking
                # Continue checking every 100ms
                self.app.after(100, check_settings_window)
            except Exception as e:
                # If any error occurs, reopen the CSV window
                print(f"Error checking settings window: {e}")
                self.show_csv_export_options()
        
        # Start checking after a short delay
        self.app.after(200, check_settings_window)
    
    def refresh_preset_dropdowns(self):
        """Refresh the metadata preset dropdowns with any new values"""
        if hasattr(self, 'csv_window') and self.csv_window.winfo_exists():
            # Find and update the metadata preset dropdown
            for widget in self.csv_window.winfo_children():
                self._refresh_dropdown_in_widget(widget)
    
    def _refresh_dropdown_in_widget(self, widget):
        """Recursively search for and refresh Combobox widgets in the given widget"""
        if isinstance(widget, ttk.Combobox):
            # Check if it's the metadata preset dropdown
            if widget.winfo_name() == "metadata_preset_dropdown":
                preset_names = []
                if hasattr(self.app.settings, 'metadata_presets'):
                    preset_names = [p['name'] for p in self.app.settings.metadata_presets]
                widget['values'] = preset_names
            # Check if it's the sequential preset dropdown
            elif widget.winfo_name() == "sequential_preset_dropdown":
                sequential_preset_names = []
                if hasattr(self.app.settings, 'sequential_metadata_presets'):
                    sequential_preset_names = [p['name'] for p in self.app.settings.sequential_metadata_presets]
                widget['values'] = sequential_preset_names
        
        # Check children widgets recursively
        for child in widget.winfo_children():
            self._refresh_dropdown_in_widget(child) 