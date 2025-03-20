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
        """Process a single row with multiple retry attempts"""
        max_attempts = 5
        
        for attempt in range(max_attempts):
            try:
                self.log(f"Attempt {attempt+1} of {max_attempts} for row {current_index}")
                
                # Prepare previous data context
                previous_data, previous_date = self._prepare_context(df, current_index, attempt)
                
                # Current text to process
                text_to_process = df.at[current_index, 'Text'] if not pd.isna(df.at[current_index, 'Text']) else ""
                
                # Skip empty text
                if not text_to_process:
                    self.log(f"Empty text for row {current_index}, skipping")
                    return ""
                
                # Format the user prompt with the appropriate context
                user_prompt = self.settings.sequence_dates_user_prompt.format(
                    previous_data=previous_data,
                    previous_date=previous_date,
                    text_to_process=text_to_process
                )

                self.log(f"User prompt for row {current_index}, attempt {attempt+1}:\n{user_prompt[:200]}...")
                
                # Call the API
                api_response, _ = await self.api_handler.route_api_call(
                    engine=self.settings.sequence_dates_model,
                    system_prompt=self.settings.sequence_dates_system_prompt,
                    user_prompt=user_prompt,
                    temp=self.settings.sequence_dates_temp,
                    text_to_process=None,  # Already formatted in user_prompt
                    val_text=self.settings.sequence_dates_val_text,
                    index=current_index,
                    is_base64=False,
                    formatting_function=True
                )
                
                self.log(f"API response for row {current_index}, attempt {attempt+1}:\n{api_response[:200] if api_response != 'Error' else 'Error'}")
                
                # Check if we got a successful response with a date
                if api_response != "Error" and "Date:" in api_response:
                    # Extract date using regex
                    date_match = re.search(r'Date:\s*(.+?)(?:\n|$)', api_response)
                    if date_match:
                        extracted_date = date_match.group(1).strip()
                        self.log(f"Successfully extracted date: {extracted_date}")
                        return extracted_date
                
                # Short pause before retrying
                await asyncio.sleep(1)
                
            except Exception as e:
                self.log(f"Error in attempt {attempt+1} for row {current_index}: {str(e)}")
                self.log(traceback.format_exc())
                continue
        
        return ""  # Return empty string if all attempts fail
    
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
        """Convert number to ordinal string (1->First, 2->Second, etc.)"""
        ordinals = {
            1: "First",
            2: "Second", 
            3: "Third",
            4: "Fourth",
            5: "Fifth"
        }
        return ordinals.get(n, f"{n}th")

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
