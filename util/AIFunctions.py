# util/AIFunctions.py

# This file contains the AIFunctionsHandler class, which is used to handle
# the AI functions for the application.

import asyncio
import os
import re
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from tkinter import messagebox, TclError

import pandas as pd
from PIL import Image, ImageOps

# Assuming settings and other necessary imports are handled by the main app instance


class AIFunctionsHandler:
    def __init__(self, app_instance):
        self.app = app_instance
        # Initialize attributes to store collation results
        self.collated_names_raw = ""
        self.collated_places_raw = ""
        # Temporary attributes for passing selections between windows/functions
        self.temp_selected_source = None
        self.temp_format_preset = None

    async def process_api_request(self, system_prompt, user_prompt, temp, image_data,
                                    text_to_process, val_text, engine, index,
                                    is_base64=True, ai_job=None, job_params=None):
        """ Wrapper to call the API Handler's route_api_call method """
        try:
            # Ensure API Handler is available
            if not hasattr(self.app, 'api_handler') or not self.app.api_handler:
                self.app.error_logging(f"API Handler not initialized for index {index}", level="ERROR")
                return "Error: API Handler not ready", index

            return await self.app.api_handler.route_api_call(
                engine=engine,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temp=temp,
                image_data=image_data,
                text_to_process=text_to_process,
                val_text=val_text,
                index=index,
                is_base64=is_base64,
                job_type=ai_job, # Pass job_type for potential API handler logic
                job_params=job_params # Pass job_params
            )

        except Exception as e:
            self.app.error_logging(f"API Error during processing for index {index}, job {ai_job}", f"{e}", level="ERROR")
            # Optionally print traceback for detailed debugging
            # REMOVED traceback.print_exc()
            return "Error", index

    def ai_function(self, all_or_one_flag="All Pages", ai_job="HTR", batch_size=None, selected_metadata_preset=None, export_text_source=None, show_final_message=True):
        """ Main function to orchestrate AI jobs """
        # If export_text_source is provided (when called from export), set it as temp_selected_source
        # This ensures the existing logic for text source selection works correctly
        if export_text_source:
            self.temp_selected_source = export_text_source
            self.app.error_logging(f"Using export-provided text source: {export_text_source}", level="DEBUG")

        # Check if we should show text source selection window (moved check here)
        # Skip window if triggered by export (export_text_source is provided)
        if ai_job in ["Correct_Text", "Translation", "Identify_Errors", "Format_Text", "Metadata"] and not export_text_source:
             # Check if a selection window is needed (i.e., temp source not already set)
            source_needed = not hasattr(self, 'temp_selected_source') or not self.temp_selected_source
            # Check if format preset needed for Format_Text
            preset_needed = (ai_job == "Format_Text" and (not hasattr(self, 'temp_format_preset') or not self.temp_format_preset))

            if source_needed or preset_needed:
                # If needed, create the source window (which sets temp attributes)
                self.app.create_text_source_window(all_or_one_flag, ai_job)
                # Return because the window callback will re-invoke this process
                # via process_ai_with_selected_source
                return

        # If batch_size wasn't passed, get it from job parameters
        if batch_size is None:
             job_params_setup = self.setup_job_parameters(ai_job)
             batch_size = job_params_setup.get('batch_size', 50) # Use job-specific batch size or default

        self.app.toggle_button_state()
        error_count = 0
        processed_indices = set()
        batch_df = pd.DataFrame() # Initialize empty DataFrame
        total_rows = 0
        processed_rows = 0

        # --- Ensure additional_info is always defined ---
        additional_info = None
        if ai_job == "Format_Text":
            additional_info = getattr(self, 'temp_format_additional_info', None)

        try:
            # --- Chunk_Text Handling ---
            if ai_job == "Chunk_Text":
                 # Check if we have a text source selection for chunking
                 selected_text_source = getattr(self.app, 'chunk_text_source_var', None)
                 if selected_text_source: selected_text_source = selected_text_source.get()
                 if not selected_text_source:
                     selected_text_source = "Corrected_Text"  # Default if not set
                 self.app.error_logging(f"Chunking using source: {selected_text_source}", level="DEBUG")


                 if all_or_one_flag == "Current Page":
                     if self.app.main_df.empty or self.app.page_counter >= len(self.app.main_df):
                         messagebox.showinfo("Info", "No page loaded to process.")
                         self.app.toggle_button_state()
                         return
                     row = self.app.page_counter
                     row_data = self.app.main_df.loc[row]

                     # Get text based on the selected source
                     text_to_process = row_data.get(selected_text_source, "") if pd.notna(row_data.get(selected_text_source)) else ""

                     if not text_to_process.strip():
                         # Fallback to find_chunk_text if selected source is empty
                         text_to_process, _ = self.app.data_operations.find_chunk_text(row)

                     if text_to_process.strip():
                         batch_df = self.app.main_df.loc[[row]]
                     else:
                         messagebox.showinfo("Skip", f"This page has no text in {selected_text_source} (or fallback) to chunk.")
                         self.app.toggle_button_state()
                         return
                 else: # All Pages
                     # Function to check if a page has text in the specified source or fallback
                     def page_has_chunkable_text(row):
                         text = row.get(selected_text_source, "") if pd.notna(row.get(selected_text_source)) else ""
                         if text.strip(): return True
                         # Fallback check if selected source is empty
                         fallback_text, _ = self.app.data_operations.find_chunk_text(row.name)
                         return bool(fallback_text.strip())

                     batch_df = self.app.main_df[self.app.main_df.apply(page_has_chunkable_text, axis=1)]

                     if batch_df.empty:
                         messagebox.showinfo("Skip", f"No pages have text in {selected_text_source} (or fallback) to chunk.")
                         self.app.toggle_button_state()
                         return

                 # First process normal text (Separated_Text)
                 self.process_chunk_text(batch_df, all_or_one_flag, "Chunk_Text")

                 # Then process translations if they exist and Text_Toggle is 'Translation'
                 if all_or_one_flag == "Current Page":
                     row = self.app.page_counter
                     # Add checks to prevent index error if df is modified during processing
                     if row < len(self.app.main_df):
                         has_translation = pd.notna(self.app.main_df.loc[row, 'Translation']) and self.app.main_df.loc[row, 'Translation'].strip()
                         text_toggle = self.app.main_df.loc[row, 'Text_Toggle']
                         if has_translation and text_toggle == "Translation":
                             self.process_translation_chunks(self.app.main_df.loc[[row]], all_or_one_flag)
                 else: # All pages
                     translation_df = self.app.main_df[
                         (self.app.main_df['Translation'].notna()) &
                         (self.app.main_df['Translation'] != '') &
                         (self.app.main_df['Text_Toggle'] == "Translation")
                     ]
                     if not translation_df.empty:
                         self.process_translation_chunks(translation_df, all_or_one_flag)

                 # Restore button state and exit for Chunk_Text
                 # Buttons are handled in the finally block now

                 # We still need to return here to skip the main processing loop
                 return # End Chunk_Text specific logic


            # --- Standard Progress Window Setup (for non-chunking jobs) ---
            progress_title = f"Applying {ai_job.replace('_', ' ')} to {'Current Page' if all_or_one_flag == 'Current Page' else 'All Pages'}..."
            progress_window, progress_bar, progress_label = self.app.progress_bar.create_progress_window(progress_title)
            self.app.progress_bar.update_progress(0, 1) # Initial update

            responses_dict = {}
            futures_to_index = {}
            # processed_rows = 0 # Moved initialization up
            # total_rows = 0     # Moved initialization up

            # Get the Skip Completed Pages toggle value
            skip_completed = self.app.skip_completed_pages.get()

            # --- Determine Batch DataFrame (batch_df) ---
            # Logic to determine which rows go into batch_df based on ai_job, all_or_one_flag, and skip_completed
            # This involves checking if the source data exists and if the target data is missing (if skip_completed)

            # Use the selected source if available (set by create_text_source_window -> process_ai_with_selected_source)
            selected_source = getattr(self, 'temp_selected_source', None)

            if ai_job == "HTR":
                target_col = 'Original_Text'
                if all_or_one_flag == "Current Page":
                    row_idx = self.app.page_counter
                    if row_idx < len(self.app.main_df):
                         # Process if skipping is off OR if target is empty
                         if not skip_completed or pd.isna(self.app.main_df.loc[row_idx, target_col]) or not self.app.main_df.loc[row_idx, target_col].strip():
                              batch_df = self.app.main_df.loc[[row_idx]]
                         else: messagebox.showinfo("Skip", f"Page {row_idx+1} already has {target_col}.")
                    else: messagebox.showerror("Error", "Invalid page index.")
                else: # All Pages
                     source_check_df = self.app.main_df[(self.app.main_df['Image_Path'].notna()) & (self.app.main_df['Image_Path'] != '')]
                     if skip_completed:
                          batch_df = source_check_df[source_check_df[target_col].isna() | (source_check_df[target_col] == '')]
                     else: batch_df = source_check_df
            elif ai_job == "Correct_Text":
                 target_col = 'Corrected_Text'
                 source_col = selected_source or 'Original_Text' # Default source if not specified
                 if all_or_one_flag == "Current Page":
                      row_idx = self.app.page_counter
                      if row_idx < len(self.app.main_df):
                           row_data = self.app.main_df.loc[row_idx]
                           if pd.notna(row_data.get(source_col)) and row_data.get(source_col, "").strip():
                                if not skip_completed or pd.isna(row_data.get(target_col)) or not row_data.get(target_col, "").strip():
                                     batch_df = self.app.main_df.loc[[row_idx]]
                                else: messagebox.showinfo("Skip", f"Page {row_idx+1} already has {target_col}.")
                           else: messagebox.showinfo("Skip", f"Page {row_idx+1} has no source text in '{source_col}'.")
                      else: messagebox.showerror("Error", "Invalid page index.")
                 else: # All Pages
                      source_check_df = self.app.main_df[self.app.main_df[source_col].notna() & (self.app.main_df[source_col] != '')]
                      if skip_completed:
                           batch_df = source_check_df[source_check_df[target_col].isna() | (source_check_df[target_col] == '')]
                      else: batch_df = source_check_df
            elif ai_job == "Format_Text":
                target_col = 'Formatted_Text'
                source_col = selected_source # Rely on selection window default or user choice
                if not source_col: source_col = 'Corrected_Text' # Fallback default if window skipped somehow
                if all_or_one_flag == "Current Page":
                    row_idx = self.app.page_counter
                    if row_idx < len(self.app.main_df):
                        row_data = self.app.main_df.loc[row_idx]
                        actual_source_found = ""
                        # Find best source: Use selected source first, then Corrected, then Original
                        if selected_source and pd.notna(row_data.get(selected_source)) and row_data.get(selected_source,"").strip():
                            actual_source_found = selected_source
                        elif pd.notna(row_data.get('Corrected_Text')) and row_data.get('Corrected_Text',"").strip():
                             actual_source_found = 'Corrected_Text'
                        elif pd.notna(row_data.get('Original_Text')) and row_data.get('Original_Text',"").strip():
                             actual_source_found = 'Original_Text'

                        if actual_source_found:
                             if not skip_completed or pd.isna(row_data.get(target_col)) or not row_data.get(target_col, "").strip():
                                 batch_df = self.app.main_df.loc[[row_idx]]
                             else: messagebox.showinfo("Skip", f"Page {row_idx+1} already has {target_col}.")
                        else: messagebox.showinfo("Skip", f"Page {row_idx+1} has no source text (Selected/Corrected/Original).")
                    else: messagebox.showerror("Error", "Invalid page index.")
                else: # All Pages
                     def find_format_source(row):
                          if selected_source and pd.notna(row.get(selected_source)) and row.get(selected_source,"").strip(): return True
                          if pd.notna(row.get('Corrected_Text')) and row.get('Corrected_Text',"").strip(): return True
                          if pd.notna(row.get('Original_Text')) and row.get('Original_Text',"").strip(): return True
                          return False
                     source_check_df = self.app.main_df[self.app.main_df.apply(find_format_source, axis=1)]
                     if skip_completed:
                          batch_df = source_check_df[source_check_df[target_col].isna() | (source_check_df[target_col] == '')]
                     else: batch_df = source_check_df
            elif ai_job == "Translation":
                target_col = 'Translation'
                source_col = selected_source # Source MUST be selected for Translation via window
                if not source_col:
                     messagebox.showerror("Error", "Text source for translation not selected.")
                     self.app.toggle_button_state()
                     return
                if all_or_one_flag == "Current Page":
                     row_idx = self.app.page_counter
                     if row_idx < len(self.app.main_df):
                          row_data = self.app.main_df.loc[row_idx]
                          if pd.notna(row_data.get(source_col)) and row_data.get(source_col, "").strip():
                               if not skip_completed or pd.isna(row_data.get(target_col)) or not row_data.get(target_col, "").strip():
                                    batch_df = self.app.main_df.loc[[row_idx]]
                               else: messagebox.showinfo("Skip", f"Page {row_idx+1} already has {target_col}.")
                          else: messagebox.showinfo("Skip", f"Page {row_idx+1} has no source text in '{source_col}'.")
                     else: messagebox.showerror("Error", "Invalid page index.")
                else: # All Pages
                     source_check_df = self.app.main_df[self.app.main_df[source_col].notna() & (self.app.main_df[source_col] != '')]
                     if skip_completed:
                          batch_df = source_check_df[source_check_df[target_col].isna() | (source_check_df[target_col] == '')]
                     else: batch_df = source_check_df
            elif ai_job == "Identify_Errors":
                target_col = 'Errors' # Target is the Errors column
                source_col = selected_source # Source MUST be selected via window
                if not source_col:
                     messagebox.showerror("Error", "Text source for error identification not selected.")
                     self.app.toggle_button_state()
                     return
                if all_or_one_flag == "Current Page":
                     row_idx = self.app.page_counter
                     if row_idx < len(self.app.main_df):
                          row_data = self.app.main_df.loc[row_idx]
                          if pd.notna(row_data.get(source_col)) and row_data.get(source_col, "").strip():
                                # Always process errors, skip_completed doesn't apply same way
                                batch_df = self.app.main_df.loc[[row_idx]]
                          else: messagebox.showinfo("Skip", f"Page {row_idx+1} has no source text in '{source_col}'.")
                     else: messagebox.showerror("Error", "Invalid page index.")
                else: # All Pages
                     batch_df = self.app.main_df[self.app.main_df[source_col].notna() & (self.app.main_df[source_col] != '')]
            elif ai_job == "Get_Names_and_Places":
                 target_col = ['People', 'Places'] # Multiple target cols
                 # Assume source is always best available text, skip_completed doesn't apply
                 if all_or_one_flag == "Current Page":
                      row_idx = self.app.page_counter
                      if row_idx < len(self.app.main_df): batch_df = self.app.main_df.loc[[row_idx]]
                      else: messagebox.showerror("Error", "Invalid page index.")
                 else: # All Pages
                      batch_df = self.app.main_df.copy() # Process all rows
            elif ai_job == "Auto_Rotate":
                 target_col = None # No text target column
                 # Process all rows with images, skip_completed doesn't apply
                 source_check_df = self.app.main_df[(self.app.main_df['Image_Path'].notna()) & (self.app.main_df['Image_Path'] != '')]
                 if all_or_one_flag == "Current Page":
                     row_idx = self.app.page_counter
                     if row_idx in source_check_df.index: batch_df = self.app.main_df.loc[[row_idx]]
                     else: messagebox.showinfo("Skip", f"Page {row_idx+1} has no image path.")
                 else: # All Pages
                      batch_df = source_check_df
            elif ai_job == "Metadata":
                target_col = None # No single target, updates multiple cols
                source_col = selected_source # Source MUST be selected via window
                if not source_col:
                     messagebox.showerror("Error", "Text source for metadata extraction not selected.")
                     self.app.toggle_button_state()
                     return
                if all_or_one_flag == "Current Page":
                     row_idx = self.app.page_counter
                     if row_idx < len(self.app.main_df):
                          row_data = self.app.main_df.loc[row_idx]
                          if pd.notna(row_data.get(source_col)) and row_data.get(source_col, "").strip():
                               batch_df = self.app.main_df.loc[[row_idx]]
                          else: messagebox.showinfo("Skip", f"Page {row_idx+1} has no source text in '{source_col}'.")
                     else: messagebox.showerror("Error", "Invalid page index.")
                else: # All Pages
                     batch_df = self.app.main_df[self.app.main_df[source_col].notna() & (self.app.main_df[source_col] != '')]
            else: # Default case or unrecognized job
                messagebox.showerror("Error", f"Unrecognized AI Job type: {ai_job}")
                batch_df = pd.DataFrame() # Ensure empty DF

            # --- Check if any rows to process ---
            total_rows = len(batch_df) # Assign value to total_rows here
            if total_rows == 0:
                info_message = "No pages need processing for this task."
                if skip_completed:
                    job_name = ai_job.replace('_', ' ')
                    if target_col and isinstance(target_col, str):
                         info_message = f"All applicable pages already have content in '{target_col}' or lack source data."
                    elif ai_job == "HTR": info_message = "All pages already have recognized text."
                    elif ai_job == "Auto_Rotate": info_message = "No images found to rotate."
                    # Add more specific messages if needed
                messagebox.showinfo("No Work Needed", info_message)
                # self.app.toggle_button_state() # Moved to finally
                if 'progress_window' in locals() and progress_window.winfo_exists():
                    self.app.progress_bar.close_progress_window()
                return # Exit if nothing to process

            # --- Setup Job Parameters and Process Batches ---
            # Set the maximum value for the progress bar
            self.app.progress_bar.set_total_steps(total_rows) # <--- ADDED
            # Pass the selected preset name if provided (for Metadata job)
            job_params = self.setup_job_parameters(ai_job, selected_metadata_preset=selected_metadata_preset)

            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                # Submit all tasks first
                for index, row_data in batch_df.iterrows():
                    # Get images based on the job type and parameters
                    images_data = self.get_images_for_job(ai_job, index, row_data, job_params)

                    # Determine text_to_process based on the job
                    text_to_process = ""
                    source_col_used = None

                    if ai_job in ["HTR", "Auto_Rotate"]:
                        text_to_process = '' # No text input needed
                    
                    elif ai_job in ["Correct_Text", "Translation", "Identify_Errors", "Metadata"]:
                        # Use export_text_source if provided (export context), otherwise use temp source (standard UI flow)
                        source_col_used = export_text_source or selected_source
                        if not source_col_used:
                            # Fallback if neither export source nor temp source is set (shouldn't happen in normal flow)
                            self.app.error_logging(f"CRITICAL: Text source missing for job {ai_job} at index {index}", level="ERROR")
                            # Define a sensible default based on job, e.g.
                            source_col_used = 'Original_Text' if ai_job == "Correct_Text" else 'Corrected_Text'
                            self.app.error_logging(f"Using fallback source: {source_col_used}", level="WARNING")
                        text_to_process = row_data.get(source_col_used, "") if source_col_used else ""
                    elif ai_job == "Format_Text":
                        # Find best source: Use selected source first, then Corrected, then Original
                        if selected_source and pd.notna(row_data.get(selected_source)) and row_data.get(selected_source,"").strip():
                            source_col_used = selected_source
                        elif pd.notna(row_data.get('Corrected_Text')) and row_data.get('Corrected_Text',"").strip():
                             source_col_used = 'Corrected_Text'
                        elif pd.notna(row_data.get('Original_Text')) and row_data.get('Original_Text',"").strip():
                             source_col_used = 'Original_Text'
                        text_to_process = row_data.get(source_col_used, "") if source_col_used else ""
                        # --- Prepend additional info if present ---
                        if additional_info:
                            text_to_process = (
                                f"Here is some additional context from the user about the document to use: \n\n{additional_info}.\n\nHere is the  document to process: \n\n{text_to_process}"
                            )
                    elif ai_job == "Get_Names_and_Places":
                        text_to_process = self.app.data_operations.find_right_text(index) # Use best available text
                        source_col_used = "Best Available" # Indicate how source was chosen

                    # Ensure text is string and not NaN
                    text_to_process = str(text_to_process) if pd.notna(text_to_process) else ""

                    # Skip if text_to_process is empty for jobs that require it
                    if not text_to_process.strip() and ai_job not in ["HTR", "Auto_Rotate"]:
                        self.app.error_logging(f"Skipping index {index} for job {ai_job} due to empty source text ('{source_col_used}')", level="WARNING")
                        # Mark as processed for progress bar logic
                        processed_indices.add(index)
                        processed_rows +=1 # Increment processed_rows here
                        self.app.progress_bar.update_progress(processed_rows, total_rows)
                        continue

                    # Print the prompt
                    # REMOVED print(f"System Prompt: {job_params['system_prompt']}")
                    # REMOVED print(f"User Prompt: {job_params['user_prompt']}")

                    # Submit the API request
                    future = executor.submit(
                        asyncio.run,
                        self.process_api_request(
                            system_prompt=job_params['system_prompt'],
                            user_prompt=job_params['user_prompt'],
                            temp=job_params['temp'],
                            image_data=images_data,
                            text_to_process=text_to_process, # Send formatted text to AI
                            val_text=job_params['val_text'],
                            engine=job_params['engine'],
                            index=index,
                            is_base64=not "gemini" in job_params.get('engine','').lower(),
                            ai_job=ai_job,
                            job_params=job_params
                        )
                    )
                    futures_to_index[future] = index

                # --- Process results ---
                for future in as_completed(futures_to_index):
                    index = futures_to_index[future]
                    try:
                        response, idx_confirm = future.result() # Get result
                        
                        # REMOVED print(f"Response: {response}")
                        # --- Start Edit ---
                        print(f"Response received by ai_function for index {index}: {response}") # Added clarity
                        # --- End Edit ---
                        
                        if idx_confirm != index:
                            self.app.error_logging(f"Index mismatch! Future for {index}, result for {idx_confirm}", level="ERROR")
                            error_count += 1
                            # Update progress even on error
                            if index not in processed_indices:
                                processed_indices.add(index)
                                processed_rows += 1 # Increment processed_rows here
                                self.app.progress_bar.update_progress(processed_rows, total_rows)
                            continue

                        # Update progress only once per index
                        if index not in processed_indices:
                            processed_indices.add(index)
                            processed_rows += 1 # Increment processed_rows here
                            self.app.progress_bar.update_progress(processed_rows, total_rows)

                        # Process the response if there is no error
                        if response == "Error":
                            error_count += 1
                            self.app.error_logging(f"API returned error for index {index}, job {ai_job}", level="ERROR")
                        else:
                            # --- ADD DEBUG PRINT --- 
                            print(f"DEBUG: Checking condition for ai_job: '{ai_job}' at index {index}")
                            # --- END DEBUG PRINT ---
                            # Update DF or image based on job
                            # --- EDIT: Route Auto_Rotate to new function ---
                            if ai_job == "Auto_Rotate":
                                self.app.data_operations.determine_rotation_from_box(index, response)
                            else:
                                # This function now handles different jobs internally
                                # Call the method on the DataOperations instance via self.app
                                self.app.data_operations.update_df_with_ai_job_response(ai_job, index, response)

                    except Exception as e:
                         error_count += 1
                         self.app.error_logging(f"Error processing future result for index {index}, job {ai_job}: {str(e)}", level="ERROR")
                         # REMOVED traceback.print_exc() # Log detailed traceback

                         # Update progress even on error
                         if index not in processed_indices:
                            processed_indices.add(index)
                            processed_rows += 1 # Increment processed_rows here
                            self.app.progress_bar.update_progress(processed_rows, total_rows)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred in ai_function orchestration: {str(e)}")
            self.app.error_logging(f"Error in ai_function orchestration for job {ai_job}: {str(e)}", level="ERROR")
            # REMOVED traceback.print_exc()


        finally:
            # --- Cleanup ---
            # Close progress window if it exists and wasn't for Chunk_Text
            if ai_job != "Chunk_Text" and 'progress_window' in locals() and progress_window.winfo_exists():
                try:
                     self.app.progress_bar.close_progress_window()
                except TclError: # Handle cases where window might already be destroyed
                     pass

            # Ensure temporary selections are cleared
            if hasattr(self, 'temp_selected_source'): delattr(self, 'temp_selected_source')
            if hasattr(self, 'temp_format_preset'): delattr(self, 'temp_format_preset')
            # Add attribute to store the last used preset name (for ExportFunctions._copy_metadata_columns)
            if ai_job == "Metadata":
                 self.last_used_metadata_preset = job_params.get('preset_name_used', None)

            # Re-enable buttons if they are disabled
            if self.app.button1['state'] == 'disabled':
                 self.app.toggle_button_state()

            # Final status message - **FIX:** Only show if show_final_message is True and not Chunk_Text
            if show_final_message and ai_job != "Chunk_Text": # <-- Check show_final_message flag
                if error_count > 0:
                    total_processed_or_error = len(processed_indices) # Count includes errors and skips after submission
                    success_count = total_processed_or_error - error_count
                    # Use total_rows (number submitted) in the denominator for clarity
                    message = f"Processing complete for {success_count}/{total_rows} applicable pages with {error_count} error(s)."
                    messagebox.showwarning("Processing Warning", message)
                # Check total_rows > 0 before showing success message
                elif total_rows > 0: # Only show success if something was submitted
                     messagebox.showinfo("Processing Complete", f"Successfully processed {processed_rows}/{total_rows} applicable pages.")
                # If total_rows was 0 initially, the 'No Work Needed' message was already shown.

    def setup_job_parameters(self, ai_job, selected_metadata_preset=None):
        """Set up parameters for different AI jobs based on settings"""
        self.app.error_logging(f"Setting up job parameters for {ai_job}", level="DEBUG")
        # Ensure settings and presets are loaded/available
        if not hasattr(self.app, 'settings'):
             self.app.error_logging("Settings object not found!", level="ERROR")
             return {} # Return empty dict on critical error

        default_model = self.app.settings.model_list[0] if self.app.settings.model_list else "default-model-placeholder"
        default_batch_size = getattr(self.app.settings, 'batch_size', 10) # Default batch size from settings

        params = {
            "temp": 0.7, # Default temperature
            "val_text": "",
            "engine": default_model,
            "user_prompt": "",
            "system_prompt": "",
            "batch_size": default_batch_size,
            "use_images": False, # Default to not using images unless specified
            "current_image": "Yes", # Default to using current image if use_images is True
            "headers": [] # For metadata
        }

        try:
            if ai_job == "Chunk_Text":
                selected_strategy_name = self.app.chunking_strategy_var.get()
                preset = next((p for p in self.app.settings.chunk_text_presets if p.get('name') == selected_strategy_name), None)
                if preset:
                    params.update({
                        "temp": float(preset.get('temperature', 0.7)),
                        "val_text": preset.get('val_text', ''),
                        "engine": preset.get('model', default_model),
                        "user_prompt": preset.get('specific_instructions', ''),
                        "system_prompt": preset.get('general_instructions', ''),
                        "use_images": preset.get('use_images', False),
                        "current_image": preset.get("current_image", "Yes"),
                        "num_prev_images": int(preset.get("num_prev_images", 0)),
                        "num_after_images": int(preset.get("num_after_images", 0)),
                    })
                else:
                    self.app.error_logging(f"Chunk text preset '{selected_strategy_name}' not found. Using defaults.", level="WARNING")
                    params.update({
                         "system_prompt": "You identify line numbers where new logical documents begin within a potentially long text transcribed from historical documents. Output only the line number(s), separated by semicolons, where a new document clearly starts. If no separators are needed, output 'None'.",
                         "user_prompt": "Analyze the following text and provide the starting line number(s) for new documents:\n\n{text_to_process}",
                         "val_text": "" # Expecting numbers or None
                    })
            elif ai_job == "Metadata":
                 # Use the passed preset name if provided, otherwise use the setting
                 preset_name_to_use = selected_metadata_preset or getattr(self.app.settings, 'metadata_preset', "Standard Metadata")
                 self.app.error_logging(f"Attempting to load metadata preset: '{preset_name_to_use}'", level="DEBUG")
                 params['preset_name_used'] = preset_name_to_use # Store the name actually used
 
                 preset = None
                 # Validate that metadata_presets is a list and not empty
                 if isinstance(self.app.settings.metadata_presets, list) and self.app.settings.metadata_presets:
                      preset = next((p for p in self.app.settings.metadata_presets if p.get('name') == preset_name_to_use), None)
                 else:
                      self.app.error_logging("self.app.settings.metadata_presets is not a valid list or is empty.", level="ERROR")

                 if preset:
                     headers_str = preset.get('metadata_headers', '')
                     headers = [h.strip() for h in headers_str.split(';') if h.strip()] if headers_str else []
                     params.update({
                         "temp": float(preset.get('temperature', 0.3)),
                         "val_text": preset.get('val_text', 'Metadata:'),
                         "engine": preset.get('model', default_model),
                         "user_prompt": preset.get('specific_instructions', 'Text to analyze:\n\n{text_to_process}'),
                         "system_prompt": preset.get('general_instructions', 'Extract metadata.'),
                         "use_images": preset.get('use_images', False),
                         "current_image": preset.get("current_image", "Yes"),
                         "headers": headers,
                         "num_prev_images": int(preset.get("num_prev_images", 0)),
                         "num_after_images": int(preset.get("num_after_images", 0)),
                     })
                     self.app.error_logging(f"Using metadata preset '{preset_name_to_use}' with headers: {headers}", level="DEBUG")
                 else:
                      self.app.error_logging(f"Metadata preset '{preset_name_to_use}' not found. Using fallback defaults.", level="WARNING")
                      params['headers'] = ["Document Type", "Author", "Correspondent", "Date", "Summary"]
                      params['system_prompt'] = f"Extract the following metadata fields: {'; '.join(params['headers'])}."
                      params['user_prompt'] = "Text:\n{text_to_process}"
                      params['val_text'] = 'Metadata:'

            elif ai_job == "Format_Text":
                 format_preset_name = getattr(self, 'temp_format_preset', None)
                 preset = next((p for p in self.app.settings.format_presets if p.get('name') == format_preset_name), None)
                 if preset:
                      params.update({
                         "temp": float(preset.get('temperature', 0.2)),
                         "val_text": preset.get('val_text', "Formatted Text:"),
                         "engine": preset.get('model', default_model),
                         "user_prompt": preset.get('specific_instructions', 'Text to format:\n\n{text_to_process}'),
                         "system_prompt": preset.get('general_instructions', 'Format the text clearly.'),
                         "use_images": preset.get('use_images', False),
                         "current_image": preset.get("current_image", "Yes"),
                         "num_prev_images": int(preset.get("num_prev_images", 0)),
                         "num_after_images": int(preset.get("num_after_images", 0)),
                     })
                 else:
                     self.app.error_logging(f"Format preset '{format_preset_name}' not found. Using defaults.", level="WARNING")
                     params['system_prompt'] = "Format the historical document text for readability. Maintain original language."
                     params['user_prompt'] = "Format this text:\n{text_to_process}"
                     params['val_text'] = "Formatted Text:"


            else: # Handle other standard jobs using function_presets
                 preset = next((p for p in self.app.settings.function_presets if p.get('name') == ai_job), None)
                 if preset:
                     params.update({
                         "temp": float(preset.get('temperature', 0.7)),
                         "val_text": preset.get('val_text', ''),
                         "engine": preset.get('model', default_model),
                         "user_prompt": preset.get('specific_instructions', ''),
                         "system_prompt": preset.get('general_instructions', ''),
                         "use_images": preset.get('use_images', False),
                         "current_image": preset.get("current_image", "Yes"),
                         "num_prev_images": int(preset.get("num_prev_images", 0)),
                         "num_after_images": int(preset.get("num_after_images", 0)),
                     })
                     # Override use_images specifically for HTR and Auto_Rotate if not set in preset
                     if ai_job in ["HTR", "Auto_Rotate"] and not preset.get('use_images'):
                          params['use_images'] = True # These jobs typically NEED images

                 else:
                     self.app.error_logging(f"Function preset not found for job: {ai_job}. Using defaults.", level="ERROR")
                     # Set some basic defaults for common jobs if preset is missing
                     if ai_job == "HTR":
                          params['system_prompt'] = "Transcribe the text from the image."
                          params['use_images'] = True
                     elif ai_job == "Correct_Text":
                          params['system_prompt'] = "Correct spelling and grammar errors in the following text from a historical document."
                          params['user_prompt'] = "Text:\n{text_to_process}"
                     elif ai_job == "Auto_Rotate":
                          params['system_prompt'] = "Analyze the image and identify the bounding box coordinates for the first line of text you encounter (including titles, headers, etc.). Output ONLY a JSON list containing a single JSON object with keys 'box_2d' (a list of four numbers: [y_min, x_min, y_max, x_max] normalized 0-1000) and 'label' (e.g., 'first_line'). Example: [{'box_2d': [100, 50, 150, 800], 'label': 'first_line'}]"
                          params['user_prompt'] = "Provide the bounding box for the first line of text in the image in the specified JSON format."
                          params['val_text'] = '[{' # Check for start of JSON list/object
                          params['use_images'] = True
                     # Add other fallbacks as needed

            # Log the final parameters being used (truncated prompts)
            log_params = params.copy()
            log_params['user_prompt'] = (log_params['user_prompt'][:100] + "...") if len(log_params.get('user_prompt','')) > 100 else log_params.get('user_prompt','')
            log_params['system_prompt'] = (log_params['system_prompt'][:100] + "...") if len(log_params.get('system_prompt','')) > 100 else log_params.get('system_prompt','')
            # Remove sensitive headers if present before logging
            if 'headers' in log_params: del log_params['headers']
            self.app.error_logging(f"Final job parameters for {ai_job}: {log_params}", level="DEBUG")

            return params

        except Exception as e:
             self.app.error_logging(f"Error setting up job parameters for {ai_job}: {str(e)}", level="ERROR")
             # REMOVED traceback.print_exc()
             return params # Return defaults on error

    def get_images_for_job(self, ai_job, index, row_data, job_params):
        """
        Get and prepare images for AI job processing. Returns a list suitable for APIHandler.
        """
        images_to_prepare = [] # List of (image_path_abs, role_or_description) tuples
        try:
            # Check if this job uses images based on job_params
            if not job_params.get("use_images", False):
                return []

            # --- Get Previous Images ---
            num_prev = int(job_params.get("num_prev_images", 0))
            prev_indices = []
            for offset in range(num_prev, 0, -1):
                prev_index = index - offset
                if prev_index >= 0 and prev_index < len(self.app.main_df):
                    prev_img_rel = self.app.main_df.loc[prev_index].get('Image_Path', "")
                    if prev_img_rel:
                        prev_img_abs = self.app.get_full_path(prev_img_rel)
                        if prev_img_abs and os.path.exists(prev_img_abs):
                            prev_indices.append((prev_img_abs, offset))
            # Label logic for previous images
            if len(prev_indices) == 1:
                images_to_prepare.append((prev_indices[0][0], "Previous Page:"))
            elif len(prev_indices) > 1:
                for img_abs, offset in prev_indices:
                    images_to_prepare.append((img_abs, f"Previous Page -{offset}:"))

            # --- Get Current Image ---
            if job_params.get("current_image", "Yes") == "Yes":
                current_image_rel = row_data.get('Image_Path', "")
                if not current_image_rel:
                    self.app.error_logging(f"Empty primary image path at index {index}", level="WARNING")
                else:
                    current_image_abs = self.app.get_full_path(current_image_rel)
                    if not current_image_abs or not os.path.exists(current_image_abs):
                        self.app.error_logging(f"Primary image file not found at index {index}: {current_image_abs}", level="WARNING")
                    else:
                        images_to_prepare.append((current_image_abs, "Current Page:"))

            # --- Get Next Images ---
            num_next = int(job_params.get("num_after_images", 0))
            next_indices = []
            for offset in range(1, num_next + 1):
                next_index = index + offset
                if next_index < len(self.app.main_df):
                    next_img_rel = self.app.main_df.loc[next_index].get('Image_Path', "")
                    if next_img_rel:
                        next_img_abs = self.app.get_full_path(next_img_rel)
                        if next_img_abs and os.path.exists(next_img_abs):
                            next_indices.append((next_img_abs, offset))
            # Label logic for next images
            if len(next_indices) == 1:
                images_to_prepare.append((next_indices[0][0], "Next Page:"))
            elif len(next_indices) > 1:
                for img_abs, offset in next_indices:
                    images_to_prepare.append((img_abs, f"Next Page +{offset}:"))

            # Debug print for image context
            print(f"[DEBUG] Images for index {index}, job {ai_job}: {[{'path': p, 'label': l} for p, l in images_to_prepare]}")

            if not images_to_prepare:
                self.app.error_logging(f"No valid images found to prepare for index {index}, job {ai_job}", level="DEBUG")
                return []

            # Determine encoding based on engine
            default_model = self.app.settings.model_list[0] if self.app.settings.model_list else "default"
            engine_name = job_params.get('engine', default_model).lower()
            is_base64_needed = "gemini" not in engine_name

            prepared_data = self.app.api_handler.prepare_image_data(
                images_to_prepare,
                engine_name,
                is_base64_needed
            )
            self.app.error_logging(f"Prepared {len(prepared_data)} images for index {index}, job {ai_job}", level="DEBUG")
            return prepared_data

        except Exception as e:
            self.app.error_logging(f"Critical error in get_images_for_job at index {index}: {str(e)}", level="ERROR")
            return []  # Return empty list as safe fallback

    def collate_names_and_places(self, unique_names, unique_places):
        """
        Gather unique names & places (now passed as arguments), call the LLM for normalization, and
        store the raw 'Response:' text in self.collated_names_raw and
        self.collated_places_raw. Does NOT do final replacements.
        """
        try:
            # Initialize default values (ensure they exist on self)
            self.collated_names_raw = ""
            self.collated_places_raw = ""

            # Create progress window first
            progress_window, progress_bar, progress_label = self.app.progress_bar.create_progress_window("Collating Names and Places")
            self.app.progress_bar.update_progress(5, 100)

            self.app.error_logging(f"Found {len(unique_names)} unique names and {len(unique_places)} unique places", level="INFO")
            if not unique_names and not unique_places:
                self.app.error_logging("No names or places to collate", level="INFO")
                messagebox.showinfo("Collation", "No names or places found in the 'People' or 'Places' columns to collate.")
                self.app.progress_bar.close_progress_window()
                return

            # --- Prepare API Call ---
            tasks = []
            if unique_names:
                tasks.append(("names", unique_names, "Collate_Names"))
            if unique_places:
                tasks.append(("places", unique_places, "Collate_Places"))

            self.app.progress_bar.update_progress(35, 100)

            # --- Execute API Calls ---
            results = {}
            with ThreadPoolExecutor(max_workers=2) as executor: # Can run names/places in parallel
                futures_to_label = {}
                for label, items, preset_name in tasks:
                    self.app.error_logging(f"Preparing {label} task with {len(items)} items", level="DEBUG")
                    text_for_llm = "\n".join(items)
                    # Get the correct preset for this label
                    preset = next((p for p in self.app.settings.analysis_presets if p.get('name') == preset_name), None)
                    if not preset:
                        self.app.error_logging(f"{preset_name} analysis preset not found in settings. Using safe defaults.", level="ERROR")
                        # Safe fallback defaults
                        preset = {
                            'model': "gemini-2.5-pro-preview-03-25",
                            'temperature': 0.2,
                            'general_instructions': f"Collate {label}.",
                            'specific_instructions': f'Collate the following list of {label}.\\n\\nList:\\n{{text_for_llm}}',
                            'val_text': '',
                            'use_images': False,
                            'current_image': "No",
                            'num_prev_images': "0",
                            'num_after_images': "0"
                        }
                    system_message = preset.get('general_instructions', '')
                    temp = float(preset.get('temperature', 0.2))
                    engine = preset.get('model', self.app.settings.model_list[0] if self.app.settings.model_list else 'default')
                    val_text = preset.get('val_text', '')
                    use_images = preset.get('use_images', False)
                    current_image = preset.get('current_image', "No")
                    num_prev_images = int(preset.get('num_prev_images', 0))
                    num_after_images = int(preset.get('num_after_images', 0))
                    user_prompt_template = preset.get('specific_instructions', '')
                    user_prompt_text = user_prompt_template.replace("{text_for_llm}", text_for_llm)

                    future = executor.submit(
                        asyncio.run,
                        self.process_api_request(
                            system_prompt=system_message,
                            user_prompt=user_prompt_text,
                            temp=temp,
                            image_data=[],
                            text_to_process="", # Input is in the user prompt
                            val_text=val_text,
                            engine=engine,
                            index=0, # Index not relevant for this task
                            is_base64=False, # No images
                            ai_job="Collation", # Custom job type for logging/debugging
                            job_params={
                                'use_images': use_images,
                                'current_image': current_image,
                                'num_prev_images': num_prev_images,
                                'num_after_images': num_after_images
                            }
                        )
                    )
                    futures_to_label[future] = label

                # Process results as they complete
                progress_base = 35
                progress_per_task = (95 - progress_base) / len(tasks) if tasks else 0
                for i, future in enumerate(as_completed(futures_to_label)):
                    label = futures_to_label[future]
                    try:
                        response, _ = future.result(timeout=180) # Extended timeout
                        results[label] = response
                        self.app.error_logging(f"Received {label} collation response (length: {len(response)})", level="DEBUG")
                        # Log a snippet
                        self.app.error_logging(f"Response snippet ({label}): {response[:200]}...", level="DEBUG")
                    except Exception as e:
                        self.app.error_logging(f"Error getting result for {label} collation: {str(e)}", level="ERROR")
                        results[label] = f"Error: Collation failed - {e}" # Store error message

                    # Update progress
                    current_progress = progress_base + (i + 1) * progress_per_task
                    self.app.progress_bar.update_progress(int(current_progress), 100)


            # Store raw results (including potential errors)
            self.collated_names_raw = results.get("names", "")
            self.collated_places_raw = results.get("places", "")

            # --- Verification ---
            missing_names = []
            missing_places = []
            if unique_names:
                 names_dict = self.app.names_places_handler.parse_collation_response(self.collated_names_raw)
                 output_name_variants = set(var for sublist in names_dict.values() for var in sublist)
                 output_name_variants.update(names_dict.keys())
                 missing_names = [name for name in unique_names if name not in output_name_variants]
                 if missing_names:
                     self.app.error_logging(f"Warning: {len(missing_names)} names might be missing from collation output (e.g., {missing_names[:5]})", level="WARNING")

            if unique_places:
                 places_dict = self.app.names_places_handler.parse_collation_response(self.collated_places_raw)
                 output_place_variants = set(var for sublist in places_dict.values() for var in sublist)
                 output_place_variants.update(places_dict.keys())
                 missing_places = [place for place in unique_places if place not in output_place_variants]
                 if missing_places:
                     self.app.error_logging(f"Warning: {len(missing_places)} places might be missing from collation output (e.g., {missing_places[:5]})", level="WARNING")


        except Exception as e:
            self.app.error_logging(f"Critical error in collate_names_and_places: {str(e)}", level="ERROR")
            # REMOVED traceback.print_exc()
            messagebox.showerror("Error",
                "An error occurred while collating names and places. Check the error log for details.")
            # Ensure defaults are set
            self.collated_names_raw = "Error occurred during collation."
            self.collated_places_raw = "Error occurred during collation."
        finally:
            # Clean up progress bar
            try:
                if 'progress_window' in locals() and progress_window.winfo_exists():
                     self.app.progress_bar.update_progress(100, 100)
                     self.app.progress_bar.close_progress_window()
            except Exception as e_progress:
                self.app.error_logging(f"Error closing progress window: {e_progress}", level="WARNING")

    def process_chunk_text(self, batch_df, all_or_one_flag, ai_job_type):
        """
        Process text chunking for the standard text fields (Corrected_Text or Original_Text etc.)
        Updates the 'Separated_Text' column with the original text plus separators.
        """
        try:
            # Get job parameters
            job_params = self.setup_job_parameters(ai_job_type) # ai_job_type should be "Chunk_Text"
            batch_size = job_params.get('batch_size', 50)

            # Get selected text source from the main app instance
            selected_text_source = getattr(self.app, 'chunk_text_source_var', None)
            if selected_text_source: selected_text_source = selected_text_source.get()
            if not selected_text_source: selected_text_source = "Corrected_Text" # Default

            # Show progress window
            progress_title = f"Identifying Separators in {selected_text_source} ({'Current' if all_or_one_flag == 'Current Page' else 'All'} Pages)..."
            progress_window, progress_bar, progress_label = self.app.progress_bar.create_progress_window(progress_title)
            self.app.progress_bar.update_progress(0, 1)

            total_rows = len(batch_df)
            self.app.progress_bar.set_total_steps(total_rows) # <--- ADDED
            processed_rows = 0
            error_count = 0
            processed_indices = set()

            # Dictionary to store original text and line mappings for inserting separators later
            original_texts_and_maps = {}

            # Process in batches
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures_to_index = {}

                for index, row_data in batch_df.iterrows():
                     # Determine text to process based on selected source, with fallback
                     text_to_process = row_data.get(selected_text_source, "") if pd.notna(row_data.get(selected_text_source)) else ""
                     source_used = selected_text_source
                     if not text_to_process.strip():
                          text_to_process, _ = self.app.data_operations.find_chunk_text(index) # Use fallback
                          source_used = "Fallback (Corrected/Original)"

                     if not text_to_process.strip():
                         self.app.error_logging(f"Skipping index {index} for chunking, no text found in '{selected_text_source}' or fallback.", level="WARNING")
                         # Mark as processed for progress bar
                         processed_indices.add(index)
                         processed_rows += 1
                         self.app.progress_bar.update_progress(processed_rows, total_rows)
                         continue

                     # Format text with line numbers and store the mapping
                     # Import the function from SeparateDocuments instead of using app instance method
                     from util.SeparateDocuments import format_text_with_line_numbers
                     formatted_text, line_map = format_text_with_line_numbers(text_to_process)
                     original_texts_and_maps[index] = (text_to_process, line_map)

                     # Get images (if needed by the preset)
                     images_data = self.get_images_for_job(ai_job_type, index, row_data, job_params)

                     # Submit the API request
                     future = executor.submit(
                         asyncio.run,
                         self.process_api_request(
                             system_prompt=job_params['system_prompt'],
                             user_prompt=job_params['user_prompt'],
                             temp=job_params['temp'],
                             image_data=images_data,
                             text_to_process=formatted_text, # Send formatted text to AI
                             val_text=job_params['val_text'],
                             engine=job_params['engine'],
                             index=index,
                             is_base64=not "gemini" in job_params.get('engine','').lower(),
                             ai_job=ai_job_type,
                             job_params=job_params
                         )
                     )

                     futures_to_index[future] = index

                # Process results
                for future in as_completed(futures_to_index):
                    index = futures_to_index[future]
                    try:
                        response, idx_confirm = future.result()
                        if idx_confirm != index:
                            self.app.error_logging(f"Index mismatch! Future for {index}, result for {idx_confirm}", level="ERROR")
                            error_count += 1
                            # Update progress even on error
                            if index not in processed_indices:
                                processed_indices.add(index)
                                processed_rows += 1
                                self.app.progress_bar.update_progress(processed_rows, total_rows)
                            continue

                        # Update progress only once per index
                        if index not in processed_indices:
                            processed_indices.add(index)
                            processed_rows += 1
                            self.app.progress_bar.update_progress(processed_rows, total_rows)

                        # Process the response if there is no error
                        if response == "Error":
                            error_count += 1
                            self.app.error_logging(f"Chunking API returned error for index {index}", level="ERROR")
                        else:
                            # Process the line number response to add separators
                            if index in original_texts_and_maps:
                                original_text, line_map = original_texts_and_maps[index]
                                # Use the function from SeparateDocuments instead of app instance method
                                from util.SeparateDocuments import insert_separators_by_line_numbers
                                separated_text = insert_separators_by_line_numbers(
                                    original_text, 
                                    response, 
                                    line_map, 
                                    error_logging_func=self.app.error_logging
                                )
                                # Update the DataFrame using the dedicated method
                                self.update_df_with_chunk_result(index, separated_text, selected_text_source)
                            else:
                                error_count += 1
                                self.app.error_logging(f"Missing original text/map for index {index} during chunking result processing", level="ERROR")
                    except Exception as e:
                        error_count += 1
                        self.app.error_logging(f"Error processing chunking future result for index {index}: {str(e)}", level="ERROR")
                        # REMOVED traceback.print_exc() # Log detailed traceback
                        # Update progress even on error
                        if index not in processed_indices:
                            processed_indices.add(index)
                            processed_rows += 1
                            self.app.progress_bar.update_progress(processed_rows, total_rows)


            # Display error message if needed
            if error_count > 0:
                message = f"An error occurred while processing the current page." if all_or_one_flag == "Current Page" else f"Errors occurred while processing {error_count} page(s)."
                messagebox.showwarning("Processing Error", message)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred in process_chunk_text: {str(e)}")
            self.app.error_logging(f"Error in process_chunk_text: {str(e)}", level="ERROR")
            # REMOVED traceback.print_exc()

        finally:
            # Close progress window
            try:
                if 'progress_window' in locals() and progress_window.winfo_exists():
                    self.app.progress_bar.close_progress_window()
            except TclError: pass

            # Refresh display handled by main ai_function finally block
            # Buttons re-enabled by main ai_function finally block

    def process_translation_chunks(self, translation_df, all_or_one_flag):
        """
        Process text chunking specifically for Translation field.
        Updates the 'Translation' column itself with separators inserted.
        """
        try:
            # If no translations to process, return early
            if translation_df.empty:
                return

            # Count actual non-empty translations (where Text_Toggle is Translation)
            translations_to_process_df = translation_df[
                (translation_df['Translation'].notna()) &
                (translation_df['Translation'] != '') &
                (translation_df['Text_Toggle'] == "Translation") # Only process if it's the active view
            ]

            if translations_to_process_df.empty:
                 self.app.error_logging("No active translations found to chunk.", level="INFO")
                 return

            # Get job parameters - use the same preset as standard Chunk_Text
            job_params = self.setup_job_parameters("Chunk_Text")
            batch_size = job_params.get('batch_size', 50)

            # Show progress window
            progress_title = f"Identifying Separators in Translation(s)..."
            progress_window, progress_bar, progress_label = self.app.progress_bar.create_progress_window(progress_title)
            self.app.progress_bar.update_progress(0, 1)

            total_rows = len(translations_to_process_df)
            self.app.progress_bar.set_total_steps(total_rows) # <--- ADDED
            processed_rows = 0
            error_count = 0
            processed_indices = set()

            # Dictionary to store original translation text and line mappings
            original_translations_and_maps = {}

            # Process in batches
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures_to_index = {}

                for index, row_data in translations_to_process_df.iterrows():
                    # Get translation text (already verified non-empty and active)
                    text_to_process = row_data['Translation']

                    # Format text with line numbers and store the mapping
                    # Import the function from SeparateDocuments instead of using app instance method
                    from util.SeparateDocuments import format_text_with_line_numbers
                    formatted_text, line_map = format_text_with_line_numbers(text_to_process)
                    original_translations_and_maps[index] = (text_to_process, line_map)

                    # Get images (if needed by the preset)
                    images_data = self.get_images_for_job("Chunk_Text", index, row_data, job_params)

                    # Submit the API request - use Chunk_Text preset but identify job for logging
                    future = executor.submit(
                        asyncio.run,
                        self.process_api_request(
                            system_prompt=job_params['system_prompt'],
                            user_prompt=job_params['user_prompt'],
                            temp=job_params['temp'],
                            image_data=images_data,
                            text_to_process=formatted_text,
                            val_text=job_params['val_text'],
                            engine=job_params['engine'],
                            index=index,
                            is_base64=not "gemini" in job_params.get('engine','').lower(),
                            ai_job="Chunk_Translation", # Specific job type for clarity
                            job_params=job_params
                        )
                    )

                    futures_to_index[future] = index

                # Process results
                for future in as_completed(futures_to_index):
                    index = futures_to_index[future]
                    try:
                        response, idx_confirm = future.result()
                        if idx_confirm != index:
                            self.app.error_logging(f"Index mismatch! Future for {index}, result for {idx_confirm}", level="ERROR")
                            error_count += 1
                             # Update progress even on error
                            if index not in processed_indices:
                                processed_indices.add(index)
                                processed_rows += 1
                                self.app.progress_bar.update_progress(processed_rows, total_rows)
                            continue

                        # Update progress only once per index
                        if index not in processed_indices:
                            processed_indices.add(index)
                            processed_rows += 1
                            self.app.progress_bar.update_progress(processed_rows, total_rows)

                        # Process the response if there is no error
                        if response == "Error":
                            error_count += 1
                            self.app.error_logging(f"Chunking API returned error for translation index {index}", level="ERROR")
                        else:
                            # Process the line number response and update the Translation field
                            if index in original_translations_and_maps:
                                original_text, line_map = original_translations_and_maps[index]
                                # Use the function from SeparateDocuments instead of app instance method
                                from util.SeparateDocuments import insert_separators_by_line_numbers
                                separated_text = insert_separators_by_line_numbers(
                                    original_text, 
                                    response, 
                                    line_map, 
                                    error_logging_func=self.app.error_logging
                                )
                                # Update the Translation field directly in the DataFrame
                                self.app.main_df.loc[index, 'Translation'] = separated_text
                                self.app.error_logging(f"Updated Translation for index {index} with separators.", level="DEBUG")

                                # Update display ONLY if this is the current page and Translation was showing
                                if index == self.app.page_counter and self.app.text_display_var.get() == "Translation":
                                    self.app.load_text() # Reload to show updated translation
                            else:
                                error_count += 1
                                self.app.error_logging(f"Missing original translation/map for index {index}", level="ERROR")
                    except Exception as e:
                        error_count += 1
                        self.app.error_logging(f"Error processing translation chunking future result for index {index}: {str(e)}", level="ERROR")
                        # REMOVED traceback.print_exc()
                         # Update progress even on error
                        if index not in processed_indices:
                            processed_indices.add(index)
                            processed_rows += 1
                            self.app.progress_bar.update_progress(processed_rows, total_rows)

            # Display error message if needed
            if error_count > 0:
                message = f"An error occurred while processing translation." if all_or_one_flag == "Current Page" else f"Errors occurred while processing {error_count} translation(s)."
                messagebox.showwarning("Processing Error", message)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred in process_translation_chunks: {str(e)}")
            self.app.error_logging(f"Error in process_translation_chunks: {str(e)}", level="ERROR")
            # REMOVED traceback.print_exc()

        finally:
            # Close progress window if it exists
            try:
                if 'progress_window' in locals() and progress_window.winfo_exists():
                    self.app.progress_bar.close_progress_window()
            except TclError: pass

            # Refresh handled by main ai_function finally block

    def extract_metadata_from_response(self, index, response):
        """
        Extract metadata from an AI response and update the DataFrame columns.
        Uses headers defined in the 'Metadata' job parameters.
        """
        try:
            if self.app.main_df.empty or index >= len(self.app.main_df):
                 self.app.error_logging(f"Skipping metadata extraction for invalid index {index}", level="WARNING")
                 return False

            # Check if response is None or empty
            if not response or not str(response).strip():
                self.app.error_logging(f"Empty metadata response for index {index}", level="WARNING")
                return False

            response_str = str(response) # Ensure string type
            self.app.error_logging(f"Raw metadata response for index {index}:\n{response_str}", level="DEBUG")

            # Get metadata parameters, including headers
            job_params = self.setup_job_parameters("Metadata")
            val_text = job_params.get('val_text', "Metadata:")
            headers = job_params.get('headers', [])

            if not headers:
                 self.app.error_logging(f"No metadata headers defined in preset/settings for index {index}.", level="WARNING")
                 # Optionally, try to parse anyway if format is standard key: value
                 # return False # Or return False if headers are strictly required

            # Map header names to DataFrame column names (replace space with underscore)
            header_to_column = {header: header.replace(" ", "_") for header in headers if header}
            self.app.error_logging(f"Using metadata headers for parsing: {headers}", level="DEBUG")
            self.app.error_logging(f"Header to column mapping: {header_to_column}", level="DEBUG")

            # Ensure all target columns exist in the DataFrame
            for col_name in header_to_column.values():
                if col_name not in self.app.main_df.columns:
                    self.app.main_df[col_name] = ""
                    # Ensure new column is string type
                    self.app.main_df[col_name] = self.app.main_df[col_name].astype(str)
                    self.app.error_logging(f"Added missing metadata column: {col_name}", level="INFO")


            # Try to isolate metadata text (handle optional val_text prefix)
            metadata_text = response_str.strip()
            # Check case-insensitively for prefix and allow optional space/colon after val_text
            val_pattern = re.compile(f"^{re.escape(val_text)}[:\\s]*", re.IGNORECASE)
            match = val_pattern.match(metadata_text)
            if match:
                 metadata_text = metadata_text[match.end():].strip()
            # Fallback for "Metadata:"
            elif metadata_text.lower().startswith("metadata:"):
                 metadata_text = metadata_text[9:].strip()


            # Parse the metadata lines (key: value pairs) more robustly
            parsed_metadata = {}
            current_header = None
            current_value_lines = []

            lines = metadata_text.split('\n')
            for line in lines:
                line_strip = line.strip()
                if not line_strip: continue

                # Check if line starts with a known header followed by a colon
                # Prioritize longer headers first if there's overlap (e.g., "Place" vs "Place of Creation")
                sorted_headers = sorted(headers, key=len, reverse=True)
                matched_header = None
                value_part = ""

                for header in sorted_headers:
                    # Check for "Header:" format, case-insensitive, allow variations in spacing
                    header_pattern = re.compile(f"^{re.escape(header)}[:\\s]+", re.IGNORECASE)
                    match = header_pattern.match(line_strip)
                    if match:
                        matched_header = header # Use the canonical header
                        value_part = line_strip[match.end():].strip()
                        break # Found the best (longest) match for this line

                # If a new header was matched, finalize the previous header's value
                if matched_header:
                    if current_header:
                        parsed_metadata[current_header] = "\n".join(current_value_lines).strip() # Join multi-line values with newline
                        self.app.error_logging(f"Finalized value for '{current_header}': {parsed_metadata[current_header][:50]}...", level="DEBUG")

                    # Start the new header
                    current_header = matched_header
                    current_value_lines = [value_part] if value_part else []
                    self.app.error_logging(f"Started new header: '{current_header}', initial value: '{value_part}'", level="DEBUG")

                # If it didn't start with a known header, append to the value of the current header
                elif current_header:
                    current_value_lines.append(line_strip)

            # Finalize the value for the very last field found
            if current_header:
                 parsed_metadata[current_header] = "\n".join(current_value_lines).strip()
                 self.app.error_logging(f"Finalized value for last header '{current_header}': {parsed_metadata[current_header][:50]}...", level="DEBUG")


            # Update DataFrame
            fields_updated = 0
            for header, value in parsed_metadata.items():
                column_name = header_to_column.get(header)
                if column_name and column_name in self.app.main_df.columns:
                     # Clean value (e.g., remove quotes if present)
                     clean_value = value.strip().strip('"').strip("'").strip()
                     # Convert "None", "N/A", etc. to empty string
                     if clean_value.lower() in ["none", "n/a", "na", "unknown", "", "[unknown]"]:
                          clean_value = ""

                     # Update DF - Overwrite existing metadata
                     # Ensure type compatibility (convert value if needed, though should be string)
                     try:
                          self.app.main_df.at[index, column_name] = str(clean_value)
                          fields_updated += 1
                          self.app.error_logging(f"Updated column '{column_name}' with value: '{clean_value}' for index {index}", level="DEBUG")
                     except Exception as e_update:
                           self.app.error_logging(f"Error updating DF column '{column_name}' at index {index}: {e_update}", level="ERROR")

                elif header: # Log if header was parsed but no column matched
                      self.app.error_logging(f"Parsed header '{header}' has no matching column in {list(header_to_column.values())}.", level="WARNING")


            if fields_updated > 0:
                self.app.error_logging(f"Successfully processed {fields_updated} metadata fields for index {index}", level="INFO")
                return True
            else:
                self.app.error_logging(f"No metadata fields were updated for index {index}. Parsed text: {metadata_text}", level="WARNING")
                return False

        except Exception as e:
            self.app.error_logging(f"Error extracting metadata for index {index}: {str(e)}", level="ERROR")
            # REMOVED traceback.print_exc()
            return False

    def process_ai_with_selected_source(self, all_or_one_flag, ai_job):
        """
        Sets temporary attributes based on the source/preset selection window,
        then calls the main ai_function to proceed with processing.
        """
        try:
            # Make sure we have a selected text source from the window
            if not hasattr(self.app, 'text_source_var') or not self.app.text_source_var.get():
                messagebox.showwarning("No Source Selected", "No text source was selected.")
                return

            # Store the selected text source temporarily on the handler instance
            self.temp_selected_source = self.app.text_source_var.get()
            self.app.error_logging(f"Stored temp source: {self.temp_selected_source}", level="DEBUG")

            # For Format_Text, also get and store the selected format preset and additional info
            if ai_job == "Format_Text":
                if hasattr(self.app, 'format_preset_var') and self.app.format_preset_var.get():
                    self.temp_format_preset = self.app.format_preset_var.get()
                    self.app.error_logging(f"Stored temp format preset: {self.temp_format_preset}", level="DEBUG")
                else:
                    self.temp_format_preset = None
                    self.app.error_logging("Format preset variable not found or empty.", level="WARNING")
                # Store additional info if present
                if hasattr(self.app, 'format_additional_info'):
                    self.temp_format_additional_info = self.app.format_additional_info
                else:
                    self.temp_format_additional_info = None
            else:
                self.temp_format_additional_info = None

            # Now call the main AI function - it will use the temp attributes
            self.ai_function(all_or_one_flag=all_or_one_flag, ai_job=ai_job)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred preparing AI processing: {str(e)}")
            self.app.error_logging(f"Error in process_ai_with_selected_source: {str(e)}", level="ERROR")
            # REMOVED traceback.print_exc()
            # Clean up temp vars if ai_function wasn't called or errored immediately
            if hasattr(self, 'temp_selected_source'): delattr(self, 'temp_selected_source')
            if hasattr(self, 'temp_format_preset'): delattr(self, 'temp_format_preset')

    def update_df_with_chunk_result(self, index, separated_text, source_text_type):
        """
        Update the DataFrame with the chunked text result (text with separators).
        Always updates the 'Separated_Text' column.
        """
        if self.app.main_df.empty or index >= len(self.app.main_df):
            self.app.error_logging(f"Skipping chunk result update for invalid index {index}", level="WARNING")
            return

        try:
            # Ensure Separated_Text column exists
            if 'Separated_Text' not in self.app.main_df.columns:
                self.app.main_df['Separated_Text'] = ""
                self.app.main_df['Separated_Text'] = self.app.main_df['Separated_Text'].astype(str)


            # Always store the response in Separated_Text
            self.app.main_df.loc[index, 'Separated_Text'] = separated_text
            # Set the toggle to Separated_Text so it becomes the default view
            self.app.main_df.loc[index, 'Text_Toggle'] = "Separated_Text"
            
            # --- ADDED --- Call UI update handler
            self.app.update_display_after_ai(index, 'Separated_Text')
            # --- END ADDED ---

            self.app.error_logging(f"Chunk_Text processed from '{source_text_type}' and saved to Separated_Text for index {index}", level="DEBUG")

            # Update display ONLY if this is the current page - Handled by update_display_after_ai
            # if index == self.app.page_counter:
            #     self.app.text_display_var.set("Separated_Text")
            #     # load_text will be called by the main ai_function's finally block


        except Exception as e:
            self.app.error_logging(f"Error updating DataFrame with chunk result for index {index}: {str(e)}", level="ERROR")
            # REMOVED traceback.print_exc()

    def process_relevance_search(self, criteria_text, selected_source, mode):
        """Process the relevance search using AI and update the DataFrame"""
        if self.app.main_df.empty:
             messagebox.showinfo("No Documents", "No documents loaded to check for relevance.")
             return

        # Show progress window
        progress_title = f"Finding Relevant Documents ({mode})..."
        progress_window, progress_bar, progress_label = self.app.progress_bar.create_progress_window(progress_title)
        self.app.progress_bar.update_progress(0, 1)

        try:
            # Disable navigation buttons during processing
            self.app.toggle_button_state()

            # Determine which rows to process
            batch_df = pd.DataFrame()
            if mode == "Current Page":
                if self.app.page_counter < len(self.app.main_df):
                    batch_df = self.app.main_df.loc[[self.app.page_counter]]
                else:
                     messagebox.showerror("Error", "Invalid page index.")
            else: # All Pages
                 # Get rows with text in the selected source
                 if selected_source in self.app.main_df.columns:
                     batch_df = self.app.main_df[
                         (self.app.main_df[selected_source].notna()) &
                         (self.app.main_df[selected_source] != '')
                     ].copy() # Use copy to avoid SettingWithCopyWarning if modifying later
                 else:
                      messagebox.showerror("Error", f"Selected source column '{selected_source}' not found.")


            if batch_df.empty:
                messagebox.showinfo("No Data", f"No rows found with text in '{selected_source}' to analyze for relevance.")
                # Close progress window before returning
                if 'progress_window' in locals() and progress_window.winfo_exists():
                    self.app.progress_bar.close_progress_window()
                self.app.toggle_button_state()
                return

            # Set up job parameters based on relevance preset (find preset in settings)
            # Assume a preset named "Relevance" exists in analysis_presets
            relevance_preset = next((p for p in self.app.settings.analysis_presets if p.get('name') == "Relevance"), None)

            if not relevance_preset:
                messagebox.showerror("Error", "Relevance analysis preset not found in settings.")
                # Close progress window before returning
                if 'progress_window' in locals() and progress_window.winfo_exists():
                    self.app.progress_bar.close_progress_window()
                self.app.toggle_button_state()
                return

            # Setup job parameters, injecting the user's criteria text
            # Use specific_instructions field for the query prompt structure
            user_prompt_template = relevance_preset.get('specific_instructions', 'Text:\n{text_to_process}\n\nRelevance Criteria:{query_text}\n\nIs this text Relevant, Partially Relevant, Irrelevant, or Uncertain based ONLY on the criteria?')
            user_prompt_filled = user_prompt_template.replace("{query_text}", criteria_text) # Inject criteria

            job_params = {
                "temp": float(relevance_preset.get('temperature', 0.1)), # Low temp for classification
                "val_text": relevance_preset.get('val_text', ''), # Expect direct answer
                "engine": relevance_preset.get('model', self.app.settings.model_list[0] if self.app.settings.model_list else 'default'),
                "user_prompt": user_prompt_filled, # Use the filled template
                "system_prompt": relevance_preset.get('general_instructions', 'Classify text relevance based on criteria. Output only one word: Relevant, Partially Relevant, Irrelevant, or Uncertain.'),
                "batch_size": min(10, getattr(self.app.settings, 'batch_size', 10)), # Smaller batch for analysis
                "use_images": False # Relevance check is text-based
            }

            # Initialize counters
            total_rows = len(batch_df)
            self.app.progress_bar.set_total_steps(total_rows) # <--- ADDED
            processed_rows = 0
            error_count = 0
            processed_indices = set()

            # Ensure Relevance column exists
            if 'Relevance' not in self.app.main_df.columns:
                self.app.main_df['Relevance'] = ""
                self.app.main_df['Relevance'] = self.app.main_df['Relevance'].astype(str)


            # Process each row
            with ThreadPoolExecutor(max_workers=job_params['batch_size']) as executor:
                futures_to_index = {}

                # Submit tasks for all rows
                for index, row in batch_df.iterrows():
                    text_to_process = row[selected_source] # Already checked non-empty

                    if not pd.isna(text_to_process) and text_to_process.strip():
                        # Submit the API request
                        future = executor.submit(
                            asyncio.run,
                            self.process_api_request( # Use self here
                                system_prompt=job_params['system_prompt'],
                                user_prompt=job_params['user_prompt'], # Already contains criteria
                                temp=job_params['temp'],
                                image_data=[],  # No images
                                text_to_process=text_to_process,
                                val_text=job_params['val_text'],
                                engine=job_params['engine'],
                                index=index,
                                is_base64=False,
                                ai_job="Relevance", # Pass job type
                                job_params=job_params
                            )
                        )
                        futures_to_index[future] = index

                # Process results as they complete
                for future in as_completed(futures_to_index):
                    index = futures_to_index[future]
                    try:
                        response, idx_confirm = future.result()
                        if idx_confirm != index: raise ValueError("Index mismatch in result")

                        # Update progress
                        if index not in processed_indices:
                            processed_indices.add(index)
                            processed_rows += 1
                            self.app.progress_bar.update_progress(processed_rows, total_rows)

                        # Process the response
                        if response != "Error":
                            # Clean response: take first word, capitalize
                            first_word = response.strip().split()[0] if response.strip() else "Uncertain"
                            # Remove trailing punctuation like periods or commas
                            cleaned_word = re.sub(r'[.,!?;:]$', '', first_word)
                            capitalized_word = cleaned_word.capitalize()


                            # Validate response
                            valid_responses = ["Relevant", "Partially Relevant", "Irrelevant", "Uncertain"]
                            final_relevance = capitalized_word if capitalized_word in valid_responses else "Uncertain"

                            # Update the DataFrame
                            self.app.main_df.at[index, 'Relevance'] = final_relevance
                            self.app.error_logging(f"Set Relevance for index {index} to: {final_relevance}", level="DEBUG")
                        else:
                            error_count += 1
                            self.app.main_df.at[index, 'Relevance'] = "Error" # Mark as error

                    except Exception as e:
                        self.app.error_logging(f"Error processing relevance for index {index}: {str(e)}", level="ERROR")
                        # REMOVED traceback.print_exc()
                        error_count += 1
                        self.app.main_df.at[index, 'Relevance'] = "Error" # Mark as error
                         # Update progress even on error
                        if index not in processed_indices:
                            processed_indices.add(index)
                            processed_rows += 1
                            self.app.progress_bar.update_progress(processed_rows, total_rows)


            # Make the relevance dropdown visible after processing
            self.app.show_relevance.set(True)
            self.app.toggle_relevance_visibility()

            # Refresh display to show updated relevance for the current page
            self.app.load_text()

            # Show summary message
            if error_count > 0:
                messagebox.showwarning("Processing Complete",
                                    f"Relevance analysis complete with {error_count} errors. "
                                    f"Successfully processed {total_rows - error_count} documents.")
            else:
                messagebox.showinfo("Processing Complete",
                                     f"Relevance analysis complete. {total_rows} documents processed.")

        except Exception as e:
            self.app.error_logging(f"Error in process_relevance_search: {str(e)}", level="ERROR")
            # REMOVED traceback.print_exc()
            messagebox.showerror("Error", f"An error occurred during relevance analysis: {str(e)}")

        finally:
            # Close progress window and re-enable buttons
            try:
                 if 'progress_window' in locals() and progress_window.winfo_exists():
                     self.app.progress_bar.close_progress_window()
            except TclError: pass

            if self.app.button1['state'] == 'disabled':
                 self.app.toggle_button_state()

            # Refresh display again just in case
            self.app.refresh_display()