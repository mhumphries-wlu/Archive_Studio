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
                        # Extract date for current row
                        date_value = await self._process_row(df, index)
                        
                        # Update the dataframe with the extracted date
                        if date_value:
                            self.log(f"Found date for row {index}: {date_value}")
                            df.at[index, 'Date'] = date_value
                        else:
                            self.log(f"No date found for row {index}")
                    
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
            
            self.log(f"Date analysis complete. {sum(df['Date'].astype(bool))} dates found.")
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
            return row['Date']
            
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                # Get previous context and date from earlier entries
                previous_data, previous_date = self._prepare_context(df, current_index, attempt)
                
                # Get text to process
                text_to_process = row.get('Text', '')
                if not text_to_process:
                    self.log(f"Empty text for row {current_index}, skipping")
                    return ""
                
                # Get Sequence_Dates preset from function_presets
                sequence_dates_preset = next((p for p in self.settings.function_presets if p.get('name') == "Sequence_Dates"), None)
                if not sequence_dates_preset:
                    self.log(f"Sequence_Dates preset not found, cannot process date for row {current_index}")
                    return ""
                
                # Format the user prompt with the appropriate context
                user_prompt = sequence_dates_preset.get('specific_instructions', '').format(
                    previous_data=previous_data,
                    previous_date=previous_date,
                    text_to_process=text_to_process
                )

                self.log(f"User prompt for row {current_index}, attempt {attempt+1}:\n{user_prompt[:200]}...")
                
                # Call the API
                api_response, _ = await self.api_handler.route_api_call(
                    engine=sequence_dates_preset.get('model', 'gemini-2.0-flash'),
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
                    
                    # Extract the date from the response
                    date_detected = self._extract_date_from_response(api_response)
                    if date_detected:
                        self.log(f"Extracted date '{date_detected}' for row {current_index}")
                        return date_detected
                    else:
                        if "More information required" in api_response:
                            if attempt < max_attempts - 1:
                                self.log(f"More information required for row {current_index}, retrying with more context...")
                                continue
                            else:
                                self.log(f"Still need more information after all attempts for row {current_index}")
                                return ""
                        self.log(f"Could not extract date from response for row {current_index}")
                else:
                    self.log(f"No API response for row {current_index}")
                
            except Exception as e:
                self.log(f"Error processing row {current_index}: {str(e)}")
                
        return ""
    
    def _prepare_context(self, df, current_index, attempt_number):
        """
        Prepare context from previous entries for the API call
        
        Args:
            df: The dataframe being processed
            current_index: Index of the current row
            attempt_number: The current attempt number (0-based)
            
        Returns:
            Tuple of (previous_data, previous_date)
        """
        try:
            # Initialize empty context
            previous_data = ""
            previous_date = ""
            
            # Get previous date if available
            if current_index > 0 and not pd.isna(df.at[current_index-1, 'Date']) and df.at[current_index-1, 'Date']:
                previous_date = f"Previous Date: {df.at[current_index-1, 'Date']}"
            
            # For first attempt, we don't include previous text data
            if attempt_number == 0:
                return previous_data, previous_date
            
            # Build context from previous entries
            context_entries = []
            
            # Number of previous entries to include, increases with each attempt
            # Start with 1 and add more context with each attempt
            entries_to_include = min(attempt_number, current_index)
            
            for i in range(1, entries_to_include + 1):
                if current_index - i >= 0:
                    ordinal = self._get_ordinal(i)
                    prev_text = df.at[current_index - i, 'Text'] if not pd.isna(df.at[current_index - i, 'Text']) else ""
                    # Truncate text if too long
                    if len(prev_text) > 500:
                        prev_text = prev_text[:500] + "..."
                    context_entries.append(f"{ordinal} Previous Entry: {prev_text}")
            
            # Join all context entries in reverse order (most recent first)
            if context_entries:
                previous_data = "\n\n".join(context_entries)
            
            return previous_data, previous_date
            
        except Exception as e:
            self.log(f"Error preparing context for row {current_index}: {str(e)}")
            return "", ""
    
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
        date_match = re.search(r'Date:\s*(.+?)(?:\n|$)', response)
        if date_match:
            return date_match.group(1).strip()
            
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
