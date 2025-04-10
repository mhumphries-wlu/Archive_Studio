# util/CompileDocuments.py

# This file contains the CompileDocuments class, which is used to compile
# the documents in the project. It is used to create a new dataframe with
# the compiled documents.

import os, sys
from tkinter import messagebox
import pandas as pd
from datetime import datetime

class CompileDocuments:
    def __init__(self, parent):
        self.parent = parent
        self.main_df = parent.main_df
        self.compiled_df = pd.DataFrame(columns=[
            "Document_No", "Text", "Translation", "Original_Index", "Image_Path", "Author", 
            "Correspondent", "Creation_Place", "Correspondent_Place",
            "Date", "Places", "People", "Summary", "Notes", "Document_Type"
        ])

    def process_ai_response(self, response, index):
        """Process the AI response and update the compiled_df"""
        try:
            fields = {
                'Document_Type': '',
                'People': '',
                'Places': '',
                'Summary': '',
                'Date': '',
                'Author': '',
                'Correspondent': '',
                'Creation_Place': '',
                'Correspondent_Place': '',
                'Document_Type': ''
            }
            
            lines = response.split('\n')
            current_field = None
            field_content = []

            # Process each line
            for line in lines:
                line = line.strip()
                
                # Check if line starts with any of our fields
                found_field = False
                for field in fields.keys():
                    if line.startswith(f"{field}:"):
                        if current_field and field_content:
                            fields[current_field] = ' '.join(field_content).strip()
                            field_content = []
                        
                        current_field = field
                        content = line[len(field)+1:].strip()
                        if content:
                            fields[field] = content
                        else:
                            field_content = []
                        found_field = True
                        break
                
                if not found_field and current_field and line:
                    if fields[current_field]:
                        fields[current_field] += ' ' + line
                    else:
                        field_content.append(line)

            if current_field and field_content:
                fields[current_field] = ' '.join(field_content).strip()

            # Update the compiled_df with extracted fields
            for field, value in fields.items():
                self.compiled_df.at[index, field] = value

            return True

        except Exception as e:
            self.parent.error_logging(f"Error processing AI response for index {index}: {str(e)}")
            return False

    def export_results(self):
        """Export the compiled results to a APD file (Archive Pearl Document)"""
        try:
            if not hasattr(self.parent, 'project_directory') or not self.parent.project_directory:
                raise Exception("Project directory not found")

            # Get project name from the directory path
            project_name = os.path.basename(self.parent.project_directory)
            
            # Create the output filename using the project name
            output_filename = f"{project_name}.apd"
            output_path = os.path.join(self.parent.project_directory, output_filename)
            
            # Save the main analysis file
            self.compiled_df.to_csv(output_path, index=False, encoding='utf-8')
                        
            messagebox.showinfo("Success", f"Analysis results have been exported to:\n{output_path}")
            
            return output_path

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export results: {str(e)}")
            self.parent.error_logging(f"Error exporting analysis results: {str(e)}")
            return None
                
    def compile_documents(self, force_recompile=True):
        try:
            # Fetch the latest main_df from the parent
            self.main_df = self.parent.main_df
            
            # Ensure project directory exists
            if not hasattr(self.parent, 'project_directory') or not self.parent.project_directory:
                raise Exception("Project directory not found")

            # Reset the compiled_df
            self.compiled_df = pd.DataFrame(columns=[
                "Index", "Original_Index", "Document_No", "Document_Page", "Image_Path", 
                "Document_Type", "Citation", "Author", "Correspondent", "Creation_Place", 
                "Correspondent_Place", "Date", "Places", "People", "Summary", "Text", 
                "Translation", "Data_Analysis", "Relevance", "Notes", "Query_Memory"
            ])
            
            # Initialize variables
            all_text = []
            all_indices = []
            all_images = []
            current_document_no = 1
            documents = []

            # First pass: collect all text and corresponding indices/images
            for index, row in self.main_df.iterrows():
                # Get the correct text version using parent's data_operations method
                text_content = self.parent.data_operations.find_right_text(index).strip()
                
                # Get image path and convert to relative path
                image_path = row['Image_Path'] if pd.notna(row['Image_Path']) else ""
                if image_path:
                    # Convert absolute path to relative path
                    try:
                        # Get the relative path from project directory to image
                        rel_path = os.path.relpath(image_path, self.parent.project_directory)
                        # Normalize path separators to forward slashes
                        rel_path = rel_path.replace('\\', '/')
                    except ValueError:
                        # If the paths are on different drives, just use the base filename
                        rel_path = f"images/{os.path.basename(image_path)}"
                
                # Add to our collections
                all_text.append(text_content)
                all_indices.append(index)
                all_images.append(rel_path if image_path else "")

            # Combine all text into a single string
            combined_text = " ".join(all_text)
            document_texts = [text.strip() for text in combined_text.split("*****") if text.strip()]

            # Process each document
            current_pos = 0
            for doc_text in document_texts:
                text_start = combined_text.find(doc_text, current_pos)
                text_end = text_start + len(doc_text)
                
                doc_indices = []
                doc_images = []
                seen_images = set()
                
                running_length = 0
                for idx, text in enumerate(all_text):
                    next_length = running_length + len(text) + 1
                    
                    if (running_length <= text_end and next_length >= text_start):
                        doc_indices.append(all_indices[idx])
                        if all_images[idx] and all_images[idx] not in seen_images:
                            seen_images.add(all_images[idx])
                            doc_images.append(all_images[idx])
                    
                    running_length = next_length

                documents.append({
                    'Document_No': current_document_no,
                    'Text': doc_text,
                    'Original_Index': doc_indices,
                    'Image_Path': doc_images
                })
                
                current_document_no += 1
                current_pos = text_end

            # Define column dtypes
            column_dtypes = {
                "Index": 'float64',
                "Document_No": 'int64',
                "Document_Page": 'float64',
                "Original_Index": 'object',
                "Image_Path": 'object',
                "Document_Type": 'object',
                "Citation": 'object',
                "Author": 'object',
                "Correspondent": 'object',
                "Creation_Place": 'object',
                "Correspondent_Place": 'object',
                "Date": 'object',
                "Places": 'object',
                "People": 'object',
                "Summary": 'object',
                "Text": 'object',
                "Translation": 'object',
                "Data_Analysis": 'object',
                "Relevance": 'object',
                "Notes": 'object',
                "Query_Memory": 'object'
            }

            # Create DataFrame from documents list
            self.compiled_df = pd.DataFrame(documents)

            # Ensure all expected columns exist with correct dtypes
            for col, dtype in column_dtypes.items():
                if col not in self.compiled_df.columns:
                    self.compiled_df[col] = pd.Series(dtype=dtype)
                else:
                    self.compiled_df[col] = self.compiled_df[col].astype(dtype)

            return self.compiled_df

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while compiling documents: {str(e)}")
            self.parent.error_logging(f"Error in compile_documents: {str(e)}")
            return None