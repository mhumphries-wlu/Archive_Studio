# util/AnalyzeDate.py

# This file contains the DateAnalyzer class, which is used to handle
# the date analysis for the application.

import pandas as pd
import re
from typing import List, Tuple, Callable, Optional
import asyncio
import traceback

class DateAnalyzer:
    def __init__(self, api_handler, settings):
        self.api_handler = api_handler
        self.settings = settings
        self.debug = True  # Enable debug output
        self.progress_callback = None
        self.active_preset_name = None  # Store the active preset name
        
    def set_progress_callback(self, callback: Callable[[int, int], None]):
        """
        Set a callback function to report progress
        
        Args:
            callback: Function that takes (current, total) parameters
        """
        self.progress_callback = callback
        
    def log(self, message):
        """Print debug message if debug is enabled"""
        if self.debug:
            print(f"[DateAnalyzer] {message}")
        
    async def process_dataframe(self, subject_df):
        """
        Process each row in the dataframe sequentially to extract dates
        
        Args:
            subject_df: DataFrame with columns 'Page', 'Text', and 'Date'
            
        Returns:
            DataFrame with 'Date' column populated
        """
        try:
            self.log(f"Starting date analysis with {len(subject_df)} rows")
            
            # Create a copy of the dataframe to avoid modifying the original
            df = subject_df.copy()
            
            # Ensure Date column exists and is initially empty strings, not NaN
            if 'Date' not in df.columns:
                df['Date'] = ""
                self.log("Added Date column to dataframe")
                
            # Ensure Creation_Place column exists
            if 'Creation_Place' not in df.columns:
                df['Creation_Place'] = ""
                self.log("Added Creation_Place column to dataframe")
            
            # Get required headers from active preset
            required_headers = []
            
            # Check for the preset specified by active_preset_name first
            sequence_preset = None
            if self.active_preset_name:
                sequence_preset = next((p for p in self.settings.sequential_metadata_presets if p.get('name') == self.active_preset_name), None)
            
            # Fall back to Sequence_Dates preset if no active preset or active preset not found
            if not sequence_preset:
                sequence_preset = next((p for p in self.settings.sequential_metadata_presets if p.get('name') == "Sequence_Dates"), None)
            
            # Get required headers from preset
            if sequence_preset and 'required_headers' in sequence_preset:
                # Handle both string and list formats for backward compatibility
                header_value = sequence_preset['required_headers']
                if isinstance(header_value, str):
                    # Split semicolon-delimited string
                    required_headers = [h.strip() for h in header_value.split(';') if h.strip()]
                elif isinstance(header_value, list):
                    # Already a list
                    required_headers = header_value
                self.log(f"Using required headers from preset: {required_headers}")
            else:
                # Default required headers if not specified
                required_headers = ["Date", "Creation_Place"]
                self.log(f"Using default required headers: {required_headers}")
                
            # Ensure all required columns exist in the dataframe
            for header in required_headers:
                if header not in df.columns:
                    df[header] = ""
                    self.log(f"Added missing column for {header} to dataframe")
            
            # Process each row sequentially
            total_rows = len(df)
            processed_rows = 0
            
            # Track field updates for logging
            field_updates = {header: 0 for header in required_headers}
            
            for index, row in df.iterrows():
                try:
                    self.log(f"Processing row {index}")
                    current_text = row['Text'] if not pd.isna(row['Text']) else ""
                    
                    # Skip if the text is empty or if Date is already populated
                    if not current_text:
                        self.log(f"Skipping row {index}: empty text")
                        
                    elif df.at[index, 'Date'] and not pd.isna(df.at[index, 'Date']):
                        self.log(f"Skipping row {index}: date already populated ({df.at[index, 'Date']})")
                        
                    else:
                        # Extract date, place, and other fields for current row
                        date_value, place_value, all_fields = await self._process_row(df, index)
                        
                        # Update the dataframe with all extracted fields
                        for field, value in all_fields.items():
                            if field in df.columns and value:
                                df.at[index, field] = value
                                field_updates[field] = field_updates.get(field, 0) + 1
                                self.log(f"Updated {field}: {value} for row {index}")
                        
                        # Also update Date and Place fields for backward compatibility
                        if date_value:
                            self.log(f"Found date for row {index}: {date_value}")
                            df.at[index, 'Date'] = date_value
                            field_updates['Date'] = field_updates.get('Date', 0) + 1
                            
                        if place_value:
                            self.log(f"Found place for row {index}: {place_value}")
                            df.at[index, 'Creation_Place'] = place_value
                            df.at[index, 'Place'] = place_value
                            field_updates['Creation_Place'] = field_updates.get('Creation_Place', 0) + 1
                            field_updates['Place'] = field_updates.get('Place', 0) + 1
                    
                    # Update progress after each row
                    processed_rows += 1
                    if self.progress_callback:
                        self.progress_callback(processed_rows, total_rows)
                        
                except Exception as e:
                    self.log(f"Error processing row {index}: {str(e)}")
                    self.log(traceback.format_exc())
                    
                    # Still update progress even if there was an error
                    processed_rows += 1
                    if self.progress_callback:
                        self.progress_callback(processed_rows, total_rows)
                    
                    continue
            
            # Log field update summary
            update_summary = []
            for field, count in field_updates.items():
                if count > 0:
                    update_summary.append(f"{count} {field}")
            
            if update_summary:
                self.log(f"Analysis complete. Updated fields: {', '.join(update_summary)}")
            else:
                self.log("Analysis complete. No fields were updated.")
                
            return df
            
        except Exception as e:
            self.log(f"Fatal error in process_dataframe: {str(e)}")
            self.log(traceback.format_exc())
            return subject_df  # Return original if we failed
    
    async def _process_row(self, df, current_index):
        """Process a single row to determine its date and other required fields
        
        Returns:
            Tuple of (date_value, place_value, all_fields_dict) where all_fields_dict contains all extracted fields
        """
        row = df.iloc[current_index]
        
        # Already has a date, no need to process
        if row['Date'] and row['Date'].strip():
            return row['Date'], row.get('Creation_Place', ''), {}
        
        # Define models to try in order of increasing capability
        models_to_try = [
            "gemini-2.0-flash-lite",  # Default from Settings.py
            "gemini-2.0-flash",       # Second attempt with more powerful model
            "claude-3-7-sonnet-20250219"  # Third attempt with most powerful model
        ]
            
        # Get previous context and headers from earlier entries
        previous_data, previous_headers = self._prepare_context(df, current_index)
        
        # Get text to process
        text_to_process = row.get('Text', '')
        if not text_to_process:
            self.log(f"Empty text for row {current_index}, skipping")
            return "", "", {}
        
        # Look for the preset specified by active_preset_name first, if set
        sequence_dates_preset = None
        
        if self.active_preset_name:
            self.log(f"Looking for specified preset: {self.active_preset_name}")
            sequence_dates_preset = next((p for p in self.settings.sequential_metadata_presets if p.get('name') == self.active_preset_name), None)
            
            if sequence_dates_preset:
                self.log(f"Using specified sequential preset: {self.active_preset_name}")
            else:
                self.log(f"Specified preset '{self.active_preset_name}' not found, falling back to default")
        
        # If no active preset or preset not found, fallback to Sequence_Dates preset
        if not sequence_dates_preset:
            # First try to get Sequence_Dates preset from sequential_metadata_presets
            sequence_dates_preset = next((p for p in self.settings.sequential_metadata_presets if p.get('name') == "Sequence_Dates"), None)
            
            # If not found in sequential_metadata_presets, fall back to function_presets (for backward compatibility)
            if not sequence_dates_preset:
                sequence_dates_preset = next((p for p in self.settings.function_presets if p.get('name') == "Sequence_Dates"), None)
                if not sequence_dates_preset:
                    self.log(f"No suitable preset found for date analysis, cannot process date for row {current_index}")
                    return "", "", {}
                else:
                    self.log(f"Using Sequence_Dates preset from function_presets (backward compatibility)")
            else:
                self.log(f"Using default Sequence_Dates preset from sequential_metadata_presets")
        
        # Track if we've tried the special CHECK model
        tried_check_model = False
        
        # Get the required headers from the preset
        required_headers = []
        if 'required_headers' in sequence_dates_preset:
            # Handle both string and list formats for backward compatibility
            header_value = sequence_dates_preset['required_headers']
            if isinstance(header_value, str):
                # Split semicolon-delimited string
                required_headers = [h.strip() for h in header_value.split(';') if h.strip()]
            elif isinstance(header_value, list):
                # Already a list
                required_headers = header_value
            self.log(f"Using required headers from preset: {required_headers}")
        else:
            # Default required headers if not specified
            required_headers = ["Date", "Creation_Place"]
            self.log(f"Using default required headers: {required_headers}")
        
        # Try each model until we get a valid date or run out of models
        for attempt, model in enumerate(models_to_try):
            try:
                self.log(f"Attempt {attempt+1} for row {current_index} using model {model}")
                
                # Build previous context information dynamically based on required headers
                previous_context = ""
                for header in required_headers:
                    if header in previous_headers:
                        previous_context += f"Previous Entry {header}: {previous_headers[header]}\n"
                    else:
                        # Include header with empty value if not found to ensure the model knows about all fields
                        previous_context += f"Previous Entry {header}: \n"
                
                # Add previous text
                previous_context += f"\nPrevious Entry Text: {previous_data}\n" if previous_data else ""
                
                # Get the template and replace placeholders
                template = sequence_dates_preset.get('specific_instructions', '')
                
                # Check if template uses the old style with explicit placeholders
                if "{previous_date}" in template or "{previous_place}" in template:
                    # Convert from old style to new style
                    prompt = previous_context + "\nCurrent Document to Analyze: " + text_to_process
                else:
                    # Use the template with our dynamic context
                    prompt = template.format(
                        previous_headers=previous_context,
                        previous_data=previous_data,
                        text_to_process=text_to_process
                    )
                
                self.log(f"User prompt for row {current_index}, attempt {attempt+1}:\n{prompt[:200]}...")
                
                # Call the API with current model
                api_response, _ = await self.api_handler.route_api_call(
                    engine=model,  # Use the current model in the sequence
                    system_prompt=sequence_dates_preset.get('general_instructions', ''),
                    user_prompt=prompt,
                    temp=float(sequence_dates_preset.get('temperature', '0.2')),
                    text_to_process=None,  # Already formatted in user_prompt
                    val_text=sequence_dates_preset.get('val_text', 'None'),
                    index=current_index,
                    is_base64=False,
                    formatting_function=True
                )
                
                # Update our progress callback if provided
                if self.progress_callback:
                    self.progress_callback(current_index + 1, len(df))
                
                # Process the response
                if api_response:
                    self.log(f"API response for row {current_index}: {api_response[:100]}...")
                    
                    # Check if the response contains CHECK flag (low confidence)
                    if "CHECK" in api_response and not tried_check_model:
                        self.log(f"Found CHECK flag in response - trying special model with extended context")
                        
                        # Mark that we've tried the special model
                        tried_check_model = True
                        
                        # Get extended context with up to 10 previous entries
                        extended_data, extended_headers = self._prepare_extended_context(df, current_index, max_entries=10)
                        
                        # Build extended prompt with all required fields
                        extended_context = ""
                        for header in required_headers:
                            if header in extended_headers:
                                extended_context += f"Previous Entry {header}: {extended_headers[header]}\n"
                            else:
                                extended_context += f"Previous Entry {header}: \n"
                                
                        # Format extended prompt with more context
                        extended_prompt = f"Previous Entries Information:\n{extended_context}\n\nPrevious Entries Text:\n{extended_data}\n\nCurrent Document to Analyze: {text_to_process}"

                        self.log(f"Extended prompt for row {current_index}:\n{extended_prompt[:200]}...")
                        
                        # Call the API with the special model for CHECK cases
                        special_model = "gemini-2.5-pro-exp-03-25"  # Updated to use the newer Gemini model
                        self.log(f"Using special model {special_model} for CHECK response")
                        
                        check_response, _ = await self.api_handler.route_api_call(
                            engine=special_model,
                            system_prompt=sequence_dates_preset.get('general_instructions', ''),
                            user_prompt=extended_prompt,
                            temp=float(sequence_dates_preset.get('temperature', '0.2')),
                            text_to_process=None,
                            val_text=sequence_dates_preset.get('val_text', 'None'),
                            index=current_index,
                            is_base64=False,
                            formatting_function=True
                        )
                        
                        if check_response:
                            self.log(f"Special model response: {check_response[:100]}...")
                            
                            # Extract all fields from the response
                            extracted_fields = self._extract_fields_from_response(check_response, required_headers)
                            
                            # For backward compatibility, return Date and Place/Creation_Place
                            date_detected = extracted_fields.get('Date', '')
                            place_detected = extracted_fields.get('Place', extracted_fields.get('Creation_Place', ''))
                            
                            # If place is empty but we had a previous place, use that
                            if not place_detected and previous_headers.get('Creation_Place', ''):
                                place_detected = previous_headers['Creation_Place']
                                extracted_fields['Place'] = place_detected
                                extracted_fields['Creation_Place'] = place_detected
                                self.log(f"Using previous place '{place_detected}' for row {current_index}")
                            
                            # Return all extracted fields along with date and place
                            return date_detected, place_detected, extracted_fields
                        else:
                            self.log(f"No response from special model, continuing with regular model sequence")
                            continue
                    
                    # No CHECK flag or already tried special model, proceed with extraction
                    extracted_fields = self._extract_fields_from_response(api_response, required_headers)
                    
                    # For backward compatibility, return Date and Place/Creation_Place
                    date_detected = extracted_fields.get('Date', '')
                    place_detected = extracted_fields.get('Place', extracted_fields.get('Creation_Place', ''))
                    
                    # If place is empty but we had a previous place, use that
                    if not place_detected and previous_headers.get('Creation_Place', ''):
                        place_detected = previous_headers['Creation_Place']
                        extracted_fields['Place'] = place_detected
                        extracted_fields['Creation_Place'] = place_detected
                        self.log(f"Using previous place '{place_detected}' for row {current_index}")
                    
                    if date_detected:
                        self.log(f"Extracted date '{date_detected}' and place '{place_detected}' for row {current_index}")
                        return date_detected, place_detected, extracted_fields
                    else:
                        if "More information required" in api_response:
                            if attempt < len(models_to_try) - 1:
                                self.log(f"Model {model} couldn't determine date, trying more powerful model")
                                continue
                            else:
                                self.log(f"Even most powerful model couldn't determine date for row {current_index}")
                                return "", place_detected, extracted_fields
                        self.log(f"Could not extract date from response for row {current_index}")
                else:
                    self.log(f"No API response for row {current_index}")
                
            except Exception as e:
                self.log(f"Error processing row {current_index} with model {model}: {str(e)}")
                if attempt < len(models_to_try) - 1:
                    self.log(f"Trying next model due to error")
                    continue
                
        return "", "", {}
    
    def _prepare_context(self, df, current_index):
        """
        Prepare context from previous entry for the API call
        
        Args:
            df: The dataframe being processed
            current_index: Index of the current row
            
        Returns:
            Tuple of (previous_data, previous_headers)
        """
        try:
            # Initialize empty context
            previous_data = ""
            previous_headers = {}
            
            # Get required headers from the active preset
            required_headers = []
            
            # Check for the preset specified by active_preset_name first
            sequence_preset = None
            if self.active_preset_name:
                sequence_preset = next((p for p in self.settings.sequential_metadata_presets if p.get('name') == self.active_preset_name), None)
            
            # Fall back to Sequence_Dates preset if no active preset or active preset not found
            if not sequence_preset:
                sequence_preset = next((p for p in self.settings.sequential_metadata_presets if p.get('name') == "Sequence_Dates"), None)
            
            # Get required headers from preset
            if sequence_preset and 'required_headers' in sequence_preset:
                # Handle both string and list formats for backward compatibility
                header_value = sequence_preset['required_headers']
                if isinstance(header_value, str):
                    # Split semicolon-delimited string
                    required_headers = [h.strip() for h in header_value.split(';') if h.strip()]
                elif isinstance(header_value, list):
                    # Already a list
                    required_headers = header_value
                self.log(f"Using required headers from preset: {required_headers}")
            else:
                # Default required headers if not specified
                required_headers = ["Date", "Creation_Place"]
                self.log(f"Using default required headers: {required_headers}")
            
            # Get previous values for each required header if available
            if current_index > 0:
                for header in required_headers:
                    # Handle special case for Creation_Place (might be called Place_of_Creation)
                    column_names = [header]
                    if header == "Place" or header == "Creation_Place":
                        column_names.extend(["Place_of_Creation", "Creation_Place"])
                    
                    # Try each possible column name
                    for col_name in column_names:
                        if col_name in df.columns and not pd.isna(df.at[current_index-1, col_name]) and df.at[current_index-1, col_name]:
                            previous_headers[header] = df.at[current_index-1, col_name]
                            self.log(f"Found previous {header}: {previous_headers[header]}")
                            break
            
            # Always include previous text context if available
            if current_index > 0:
                prev_text = df.at[current_index - 1, 'Text'] if not pd.isna(df.at[current_index - 1, 'Text']) else ""
                # Truncate text if too long
                if prev_text:
                    if len(prev_text) > 500:
                        prev_text = prev_text[:500] + "..."
                    previous_data = prev_text
            
            return previous_data, previous_headers
            
        except Exception as e:
            self.log(f"Error preparing context for row {current_index}: {str(e)}")
            return "", {}
            
    def _prepare_extended_context(self, df, current_index, max_entries=10):
        """
        Prepare extended context with multiple previous entries for special CHECK analysis
        
        Args:
            df: The dataframe being processed
            current_index: Index of the current row
            max_entries: Maximum number of previous entries to include
            
        Returns:
            Tuple of (extended_data, extended_headers)
        """
        try:
            # Initialize context strings
            extended_data = ""
            extended_headers = {}
            
            # Get required headers from the active preset
            required_headers = []
            
            # Check for the preset specified by active_preset_name first
            sequence_preset = None
            if self.active_preset_name:
                sequence_preset = next((p for p in self.settings.sequential_metadata_presets if p.get('name') == self.active_preset_name), None)
            
            # Fall back to Sequence_Dates preset if no active preset or active preset not found
            if not sequence_preset:
                sequence_preset = next((p for p in self.settings.sequential_metadata_presets if p.get('name') == "Sequence_Dates"), None)
            
            # Get required headers from preset
            if sequence_preset and 'required_headers' in sequence_preset:
                # Handle both string and list formats for backward compatibility
                header_value = sequence_preset['required_headers']
                if isinstance(header_value, str):
                    # Split semicolon-delimited string
                    required_headers = [h.strip() for h in header_value.split(';') if h.strip()]
                elif isinstance(header_value, list):
                    # Already a list
                    required_headers = header_value
                self.log(f"Using required headers from preset: {required_headers}")
            else:
                # Default required headers if not specified
                required_headers = ["Date", "Creation_Place"]
                self.log(f"Using default required headers: {required_headers}")
            
            # Determine how many previous entries we can include
            num_prev_entries = min(current_index, max_entries)
            
            if num_prev_entries > 0:
                entries_data = []
                
                # Get the most recent entry's values for use in extended_headers
                prev_idx = current_index - 1
                if prev_idx >= 0:
                    # Get values for all required headers
                    for header in required_headers:
                        # Special handling for Place/Creation_Place
                        column_names = [header]
                        if header == "Place" or header == "Creation_Place":
                            column_names.extend(["Place_of_Creation", "Creation_Place"])
                        
                        # Try each possible column name
                        for col_name in column_names:
                            if col_name in df.columns and not pd.isna(df.at[prev_idx, col_name]) and df.at[prev_idx, col_name]:
                                extended_headers[header] = df.at[prev_idx, col_name]
                                self.log(f"Found previous {header} for extended context: {extended_headers[header]}")
                                break
                
                # Loop through previous entries, starting with the most recent
                for i in range(num_prev_entries):
                    prev_idx = current_index - (i + 1)
                    
                    if prev_idx < 0:
                        continue
                        
                    entry_num = i + 1
                    
                    # Build entry data with all required fields
                    entry_data = f"Entry {entry_num}:\n"
                    
                    # Add all required headers
                    for header in required_headers:
                        header_value = ""
                        # Try to find the value in different column variants
                        column_names = [header]
                        if header == "Place" or header == "Creation_Place":
                            column_names.extend(["Place_of_Creation", "Creation_Place"])
                            
                        for col_name in column_names:
                            if col_name in df.columns and not pd.isna(df.at[prev_idx, col_name]) and df.at[prev_idx, col_name]:
                                header_value = df.at[prev_idx, col_name]
                                break
                                
                        entry_data += f"{header}: {header_value}\n"
                    
                    # Get text for this entry
                    entry_text = df.at[prev_idx, 'Text'] if not pd.isna(df.at[prev_idx, 'Text']) else ""
                    if len(entry_text) > 300:
                        entry_text = entry_text[:300] + "..."
                    
                    entry_data += f"Text: {entry_text}\n\n"
                    entries_data.append(entry_data)
                
                # Combine all entries data
                extended_data = "\n".join(entries_data)
            
            return extended_data, extended_headers
            
        except Exception as e:
            self.log(f"Error preparing extended context for row {current_index}: {str(e)}")
            return "", {}
    
    def _get_ordinal(self, n):
        """Convert a number to its ordinal form (1st, 2nd, 3rd, etc.)"""
        ordinals = {1: "1st", 2: "2nd", 3: "3rd", 21: "21st", 22: "22nd", 23: "23rd"}
        if 11 <= n % 100 <= 13:
            return f"{n}th"
        return ordinals.get(n, f"{n}th")
        
    def _extract_date_from_response(self, response):
        """Extract date from API response"""
        if not response:
            return ""
            
        # Check for standard Date: format
        date_match = re.search(r'Date:\s*(.+?)(?:\n|Place:|$)', response)
        if date_match:
            return date_match.group(1).strip()
        
        # Look for date with variations in formatting
        # Try alternate patterns for "Date:"
        alt_date_patterns = [
            r'Date:\s*([^\n:]+)',            # Basic pattern: "Date: value"
            r'DATE:\s*([^\n:]+)',            # All caps
            r'date:\s*([^\n:]+)',            # Lowercase
            r'\bDate\b[^\n:]*:\s*([^\n:]+)'  # Any variation with "Date" as a word
        ]
        
        for pattern in alt_date_patterns:
            match = re.search(pattern, response)
            if match:
                self.log(f"Found date with alternate pattern: {pattern}")
                return match.group(1).strip()
        
        # Look for date patterns
        date_patterns = [
            # DD/MM/YYYY
            r'(\d{1,2}/\d{1,2}/\d{4})',
            # YYYY/MM/DD
            r'(\d{4}/\d{1,2}/\d{1,2})',
            # Month Day, Year
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            # Day Month Year
            r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(0).strip()
                
        # If no date pattern found but response looks like a precise date statement
        if len(response.strip()) < 30 and re.search(r'\b\d{4}\b', response):
            return response.strip()
            
        return ""
        
    def _extract_place_from_response(self, response):
        """Extract place from API response"""
        if not response:
            return ""
            
        # Check for standard Place: format
        place_match = re.search(r'Place:\s*(.+?)(?:\n|CHECK|$)', response)
        if place_match:
            return place_match.group(1).strip()
        
        # Try various alternate patterns
        alt_place_patterns = [
            r'Place:\s*([^:\n]+)',                   # More flexible ending
            r'PLACE:\s*([^:\n]+)',                   # All caps
            r'place:\s*([^:\n]+)',                   # Lowercase
            r'Place of Creation:\s*([^:\n]+)',       # Full variant
            r'PLACE OF CREATION:\s*([^:\n]+)',       # Full variant caps
            r'place of creation:\s*([^:\n]+)',       # Full variant lowercase
            r'Place of creation:\s*([^:\n]+)',       # Mixed case
            r'Creation Place:\s*([^:\n]+)',          # Alternate order
            r'\bCreation\b[^\n:]*\bPlace\b[^\n:]*:\s*([^:\n]+)', # Variation with Creation and Place
            r'\bPlace\b[^\n:]*\bof\b[^\n:]*\bCreation\b[^\n:]*:\s*([^:\n]+)'  # Variation with Place of Creation
        ]
        
        for pattern in alt_place_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                self.log(f"Found place with alternate pattern: {pattern}")
                return match.group(1).strip()
        
        return ""

    def _extract_fields_from_response(self, response, required_headers):
        """
        Extract all required fields from API response
        
        Args:
            response: The API response text
            required_headers: List of headers to extract
            
        Returns:
            Dictionary with field names as keys and extracted values as values
        """
        if not response:
            return {}
            
        extracted_fields = {}
        
        # Process each required field
        for header in required_headers:
            # Look for standard format: "Header: value"
            header_patterns = [
                rf'{header}:\s*(.+?)(?:\n|$)',            # Basic pattern: "Header: value"
                rf'{header.upper()}:\s*(.+?)(?:\n|$)',    # All caps
                rf'{header.lower()}:\s*(.+?)(?:\n|$)',    # Lowercase
                rf'\b{header}\b[^\n:]*:\s*(.+?)(?:\n|$)'  # Any variation with header as a word
            ]
            
            for pattern in header_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    self.log(f"Found {header} with pattern: {pattern}")
                    extracted_fields[header] = match.group(1).strip()
                    break
                    
        # Special handling for Date and Place which are backward compatible
        if 'Date' not in extracted_fields:
            extracted_fields['Date'] = self._extract_date_from_response(response)
            
        if 'Place' not in extracted_fields and 'Creation_Place' not in extracted_fields:
            place_value = self._extract_place_from_response(response)
            extracted_fields['Place'] = place_value
            extracted_fields['Creation_Place'] = place_value
            
        self.log(f"Extracted fields: {extracted_fields}")
        return extracted_fields

async def analyze_dates(subject_df, api_handler, settings, preset_name=None):
    """
    Main function to analyze dates in a dataframe
    
    Args:
        subject_df: DataFrame with columns 'Page', 'Text', and 'Date'
        api_handler: Instance of APIHandler class
        settings: Instance of Settings class
        preset_name: Optional name of the sequential metadata preset to use
        
    Returns:
        DataFrame with 'Date' column populated
    """
    try:
        print("[analyze_dates] Starting date analysis")
        analyzer = DateAnalyzer(api_handler, settings)
        
        # Set the active preset if specified
        if preset_name:
            print(f"[analyze_dates] Using specified preset: {preset_name}")
            analyzer.active_preset_name = preset_name
            
        result = await analyzer.process_dataframe(subject_df)
        print("[analyze_dates] Date analysis complete")
        return result
    except Exception as e:
        print(f"[analyze_dates] Error analyzing dates: {str(e)}")
        print(traceback.format_exc())
        return subject_df  # Return original dataframe if we failed
