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
            
            # Process each row sequentially
            total_rows = len(df)
            processed_rows = 0
            
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
                        # Extract date and place for current row
                        date_value, place_value = await self._process_row(df, index)
                        
                        # Update the dataframe with the extracted date
                        if date_value:
                            self.log(f"Found date for row {index}: {date_value}")
                            df.at[index, 'Date'] = date_value
                        else:
                            self.log(f"No date found for row {index}")
                            
                        # Update the dataframe with the extracted place
                        if place_value:
                            self.log(f"Found place for row {index}: {place_value}")
                            df.at[index, 'Creation_Place'] = place_value
                        else:
                            self.log(f"No place found for row {index}")
                    
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
            
            self.log(f"Analysis complete. {sum(df['Date'].astype(bool))} dates and {sum(df['Creation_Place'].astype(bool))} places found.")
            return df
            
        except Exception as e:
            self.log(f"Fatal error in process_dataframe: {str(e)}")
            self.log(traceback.format_exc())
            return subject_df  # Return original if we failed
    
    async def _process_row(self, df, current_index):
        """Process a single row to determine its date"""
        row = df.iloc[current_index]
        
        # Already has a date, no need to process
        if row['Date'] and row['Date'].strip():
            return row['Date'], row.get('Creation_Place', '')
        
        # Define models to try in order of increasing capability
        models_to_try = [
            "gemini-2.0-flash-lite",  # Default from Settings.py
            "gemini-2.0-flash",       # Second attempt with more powerful model
            "claude-3-7-sonnet-20250219"  # Third attempt with most powerful model
        ]
            
        # Get previous context, date, and place from earlier entries
        previous_data, previous_date, previous_place = self._prepare_context(df, current_index)
        
        # Get text to process
        text_to_process = row.get('Text', '')
        if not text_to_process:
            self.log(f"Empty text for row {current_index}, skipping")
            return "", ""
        
        # Get Sequence_Dates preset from function_presets
        sequence_dates_preset = next((p for p in self.settings.function_presets if p.get('name') == "Sequence_Dates"), None)
        if not sequence_dates_preset:
            self.log(f"Sequence_Dates preset not found, cannot process date for row {current_index}")
            return "", ""
        
        # Track if we've tried the special CHECK model
        tried_check_model = False
        
        # Try each model until we get a valid date or run out of models
        for attempt, model in enumerate(models_to_try):
            try:
                self.log(f"Attempt {attempt+1} for row {current_index} using model {model}")
                
                # Format the user prompt with the appropriate context
                user_prompt = sequence_dates_preset.get('specific_instructions', '').format(
                    previous_data=previous_data,
                    previous_date=previous_date,
                    previous_place=previous_place,
                    text_to_process=text_to_process
                )

                self.log(f"User prompt for row {current_index}, attempt {attempt+1}:\n{user_prompt[:200]}...")
                
                # Call the API with current model
                api_response, _ = await self.api_handler.route_api_call(
                    engine=model,  # Use the current model in the sequence
                    system_prompt=sequence_dates_preset.get('general_instructions', ''),
                    user_prompt=user_prompt,
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
                        extended_data, extended_dates, extended_places = self._prepare_extended_context(df, current_index, max_entries=10)
                        
                        # Format extended prompt
                        extended_prompt = f"""Previous Entries:
{extended_data}

Current Document to Analyze: {text_to_process}"""

                        self.log(f"Extended prompt for row {current_index}:\n{extended_prompt[:200]}...")
                        
                        # Call the API with the special model for CHECK cases
                        special_model = "gemini-2.0-pro-exp-02-05"
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
                            
                            # Extract date and place from special model response
                            date_detected = self._extract_date_from_response(check_response)
                            place_detected = self._extract_place_from_response(check_response)
                            
                            # If place is empty but we had a previous place, use that
                            if not place_detected and previous_place:
                                place_detected = previous_place
                                self.log(f"Using previous place '{place_detected}' for row {current_index}")
                                
                            return date_detected, place_detected
                        else:
                            self.log(f"No response from special model, continuing with regular model sequence")
                            continue
                    
                    # No CHECK flag or already tried special model, proceed with extraction
                    date_detected = self._extract_date_from_response(api_response)
                    place_detected = self._extract_place_from_response(api_response)
                    
                    # If place is empty but we had a previous place, use that
                    if not place_detected and previous_place:
                        place_detected = previous_place
                        self.log(f"Using previous place '{place_detected}' for row {current_index}")
                    
                    if date_detected:
                        self.log(f"Extracted date '{date_detected}' and place '{place_detected}' for row {current_index}")
                        return date_detected, place_detected
                    else:
                        if "More information required" in api_response:
                            if attempt < len(models_to_try) - 1:
                                self.log(f"Model {model} couldn't determine date, trying more powerful model")
                                continue
                            else:
                                self.log(f"Even most powerful model couldn't determine date for row {current_index}")
                                return "", place_detected
                        self.log(f"Could not extract date from response for row {current_index}")
                else:
                    self.log(f"No API response for row {current_index}")
                
            except Exception as e:
                self.log(f"Error processing row {current_index} with model {model}: {str(e)}")
                if attempt < len(models_to_try) - 1:
                    self.log(f"Trying next model due to error")
                    continue
                
        return "", ""
    
    def _prepare_context(self, df, current_index):
        """
        Prepare context from previous entry for the API call
        
        Args:
            df: The dataframe being processed
            current_index: Index of the current row
            
        Returns:
            Tuple of (previous_data, previous_date, previous_place)
        """
        try:
            # Initialize empty context
            previous_data = ""
            previous_date = "Previous Entry Date: " 
            previous_place = "Previous Entry Place: "
            
            # Get previous date if available
            if current_index > 0 and not pd.isna(df.at[current_index-1, 'Date']) and df.at[current_index-1, 'Date']:
                previous_date += df.at[current_index-1, 'Date']
            
            # Get previous place if available
            if current_index > 0 and 'Creation_Place' in df.columns and not pd.isna(df.at[current_index-1, 'Creation_Place']) and df.at[current_index-1, 'Creation_Place']:
                previous_place += df.at[current_index-1, 'Creation_Place']
            
            # Always include previous text context if available
            if current_index > 0:
                prev_text = df.at[current_index - 1, 'Text'] if not pd.isna(df.at[current_index - 1, 'Text']) else ""
                # Truncate text if too long
                if prev_text:
                    if len(prev_text) > 500:
                        prev_text = prev_text[:500] + "..."
                    previous_data = "Previous Entry Text: " + prev_text
            
            return previous_data, previous_date, previous_place
            
        except Exception as e:
            self.log(f"Error preparing context for row {current_index}: {str(e)}")
            return "", "", ""
            
    def _prepare_extended_context(self, df, current_index, max_entries=10):
        """
        Prepare extended context with multiple previous entries for special CHECK analysis
        
        Args:
            df: The dataframe being processed
            current_index: Index of the current row
            max_entries: Maximum number of previous entries to include
            
        Returns:
            Tuple of (extended_data, extended_dates, extended_places)
        """
        try:
            # Initialize context strings
            extended_data = ""
            extended_dates = ""
            extended_places = ""
            
            # Determine how many previous entries we can include
            num_prev_entries = min(current_index, max_entries)
            
            if num_prev_entries > 0:
                entries_data = []
                
                # Loop through previous entries, starting with the most recent
                for i in range(num_prev_entries):
                    prev_idx = current_index - (i + 1)
                    
                    if prev_idx < 0:
                        continue
                        
                    entry_num = i + 1
                    entry_text = ""
                    
                    # Get date for this entry
                    entry_date = ""
                    if not pd.isna(df.at[prev_idx, 'Date']) and df.at[prev_idx, 'Date']:
                        entry_date = df.at[prev_idx, 'Date']
                    
                    # Get place for this entry
                    entry_place = ""
                    if 'Creation_Place' in df.columns and not pd.isna(df.at[prev_idx, 'Creation_Place']) and df.at[prev_idx, 'Creation_Place']:
                        entry_place = df.at[prev_idx, 'Creation_Place']
                    
                    # Get text for this entry
                    entry_text = df.at[prev_idx, 'Text'] if not pd.isna(df.at[prev_idx, 'Text']) else ""
                    if len(entry_text) > 300:
                        entry_text = entry_text[:300] + "..."
                    
                    # Format the entry
                    entry_data = f"Entry {entry_num}:\n"
                    entry_data += f"Date: {entry_date}\n"
                    entry_data += f"Place: {entry_place}\n"
                    entry_data += f"Text: {entry_text}\n\n"
                    
                    entries_data.append(entry_data)
                
                # Combine all entries data
                extended_data = "\n".join(entries_data)
            
            return extended_data, extended_dates, extended_places
            
        except Exception as e:
            self.log(f"Error preparing extended context for row {current_index}: {str(e)}")
            return "", "", ""
    
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

async def analyze_dates(subject_df, api_handler, settings):
    """
    Main function to analyze dates in a dataframe
    
    Args:
        subject_df: DataFrame with columns 'Page', 'Text', and 'Date'
        api_handler: Instance of APIHandler class
        settings: Instance of Settings class
        
    Returns:
        DataFrame with 'Date' column populated
    """
    try:
        print("[analyze_dates] Starting date analysis")
        analyzer = DateAnalyzer(api_handler, settings)
        result = await analyzer.process_dataframe(subject_df)
        print("[analyze_dates] Date analysis complete")
        return result
    except Exception as e:
        print(f"[analyze_dates] Error analyzing dates: {str(e)}")
        print(traceback.format_exc())
        return subject_df  # Return original dataframe if we failed
