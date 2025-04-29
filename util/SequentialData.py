import json
import asyncio
import pandas as pd
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from util.JSONExtraction import extract_json_from_response

def df_to_json_array(df, text_column):
    """
    Convert a DataFrame to a JSON array string for sequential analysis.
    Each object contains 'index' (from df.index) and 'text' (from the 'Original_Text' column if it exists, otherwise from the specified column).
    """
    use_col = 'Original_Text' if 'Original_Text' in df.columns else text_column
    arr = []
    for idx, row in df.iterrows():
        arr.append({
            "index": int(idx),
            "text": str(row[use_col]) if use_col in row and row[use_col] is not None else ""
        })
    return json.dumps(arr, ensure_ascii=False)


async def _call_single_chunk_api(app, chunk_df, preset_name, text_column, previous_chunk_data=None):
    """Helper async function to call API for a single DataFrame chunk."""
    # Find the preset
    preset = next((p for p in app.settings.sequential_metadata_presets if p.get('name') == preset_name), None)
    if not preset:
        # Log error instead of raising, return None to indicate failure for this chunk
        app.error_logging(f"Sequential metadata preset '{preset_name}' not found for chunk.", level="ERROR")
        return None 

    system_prompt = preset.get('general_instructions', '')
    user_prompt_template = preset.get('specific_instructions', '')
    temp = float(preset.get('temperature', 0.2))
    model = preset.get('model', app.settings.model_list[0] if app.settings.model_list else 'default')
    val_text = preset.get('val_text', None)

    # Convert chunk df to json
    json_array = df_to_json_array(chunk_df, text_column)

    # Compose the user prompt with the JSON array
    if '{text_to_process}' in user_prompt_template:
        user_prompt = user_prompt_template.replace('{text_to_process}', json_array)
    else:
        user_prompt = f"{user_prompt_template}\nInput JSON:\n{json_array}"

    # --- Add context from previous chunk if available ---
    if previous_chunk_data and isinstance(previous_chunk_data, dict):
        # Extract location or other relevant fields from the previous chunk's last data item
        # For now, prioritize 'Location', but this could be made more dynamic
        previous_location = previous_chunk_data.get('Location')
        if previous_location:
            context_string = f"\n\nYour analysis starts part way through. The location of the last entry was: {previous_location}"
            user_prompt += context_string
            app.error_logging(f"Added context to prompt: {context_string}", level="INFO")
        else:
            # Optionally add context even if location is missing, using other fields
            # context_string = f"\n\nContext from previous entry: {previous_chunk_data}"
            # user_prompt += context_string
            app.error_logging(f"Previous chunk data provided, but 'Location' key missing or empty: {previous_chunk_data}", level="INFO")
    # --- End context addition ---

    # Print prompts for the first chunk for debugging (optional)
    # if chunk_df.index[0] == 0: # Example condition
    #    print("\n--- SYSTEM PROMPT (Chunk 0) ---\n" + system_prompt)
    #    print("\n--- USER PROMPT (Chunk 0) ---\n" + user_prompt)
        
    # Call the API asynchronously
    response, _ = await app.api_handler.route_api_call(
        engine=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temp=temp,
        image_data=None,
        text_to_process=None,
        val_text=val_text,
        index=None, # Index not directly relevant for chunk call
        is_base64=False,
        formatting_function=True
    )
    # Print API response for debugging
    if response is not None:
        print(f"\n--- API RESPONSE (Chunk starting index {chunk_df.index[0]}) ---\n" + str(response) + "\n")
    else:
        print(f"\n--- API RESPONSE (Chunk starting index {chunk_df.index[0]}) --- No response received (None)\n")
    return response

def _parse_index_string(index_str, app):
    """Parses a comma/space separated string of indices into a list of integers."""
    indices = []
    if not isinstance(index_str, str):
        app.error_logging(f"Invalid index string type: {type(index_str)}. Value: {index_str}", level="WARNING")
        return indices
    
    # Add debug logging for the raw input
    app.error_logging(f"Parsing index string: '{index_str}'", level="DEBUG")
    
    # Handle comma-separated values directly, which is the most common format for 'Indecies'
    app.error_logging(f"DEBUG _parse_index_string: Checking for comma in '{index_str}'", level="DEBUG")
    if ',' in index_str:
        app.error_logging(f"DEBUG _parse_index_string: Comma found. Splitting by comma.", level="DEBUG")
        for part in index_str.split(','):
            part = part.strip()
            app.error_logging(f"DEBUG _parse_index_string: Processing part '{part}'", level="DEBUG")
            if part and part.isdigit():
                app.error_logging(f"DEBUG _parse_index_string: Part '{part}' is digit. Appending.", level="DEBUG")
                try:
                    # Assume indices from API are 0-based
                    index_val = int(part)
                    if index_val >= 0: # Ensure non-negative index
                        indices.append(index_val)
                    else:
                        app.error_logging(f"Skipping invalid 0 or negative index derived from '{part}'.", level="WARNING")
                except ValueError:
                    app.error_logging(f"Could not convert part '{part}' to integer.", level="WARNING")
            else:
                app.error_logging(f"DEBUG _parse_index_string: Part '{part}' is empty or not digit.", level="DEBUG")
        
        app.error_logging(f"DEBUG _parse_index_string: After comma split loop, indices are: {indices}", level="DEBUG")
        if indices:
            app.error_logging(f"Parsed {len(indices)} indices from comma-separated list: {indices}", level="DEBUG")
            app.error_logging(f"DEBUG _parse_index_string: Returning indices (Exit Point 1).", level="DEBUG")
            return indices
        else:
            app.error_logging(f"DEBUG _parse_index_string: No indices found after comma split. Proceeding to fallback.", level="DEBUG")
    else:
        app.error_logging(f"DEBUG _parse_index_string: No comma found. Proceeding to fallback.", level="DEBUG")
    
    # Fall back to the original parsing logic for space-separated or other formats
    app.error_logging(f"DEBUG _parse_index_string: Using fallback regex split r'[\\s,]+' on '{index_str.strip()}'", level="DEBUG")
    parts = re.split(r'[\s,]+', index_str.strip()) # Use \s for any whitespace, retain comma
    app.error_logging(f"DEBUG _parse_index_string: Fallback parts: {parts}", level="DEBUG")
    for part in parts:
        part = part.strip()
        app.error_logging(f"DEBUG _parse_index_string: Processing fallback part '{part}'", level="DEBUG")
        if not part:
            continue
        if part.isdigit():
            app.error_logging(f"DEBUG _parse_index_string: Fallback part '{part}' is digit. Appending.", level="DEBUG")
            try:
                # Assume indices from API are 0-based
                index_val = int(part)
                if index_val >= 0: # Ensure non-negative index
                     indices.append(index_val)
                else:
                     app.error_logging(f"Skipping invalid 0 or negative index derived from '{part}'.", level="WARNING")
            except ValueError:
                app.error_logging(f"Could not convert part '{part}' to integer.", level="WARNING")
        # Add range handling here if necessary in the future
        # elif '-' in part: ... handle range ...
        else:
            app.error_logging(f"Skipping non-numeric index part: '{part}'", level="WARNING")
    
    app.error_logging(f"Parsed {len(indices)} indices using fallback regex split: {indices}", level="DEBUG")
    app.error_logging(f"DEBUG _parse_index_string: Returning indices (Exit Point 2).", level="DEBUG")
    return indices

def call_sequential_api(app, df, preset_name):
    """
    Call the API for sequential data analysis in chunks using the selected preset.
    - app: main app instance (must have .settings and .api_handler)
    - df: DataFrame to process
    - preset_name: name of the sequential metadata preset to use
    Returns: Combined DataFrame with results from all chunks, or empty DataFrame on error.
    """
    chunk_size = 25
    try:
        chunk_size = int(app.settings.sequential_batch_size)
        if chunk_size <= 0:
            app.error_logging(f"Invalid sequential_batch_size ({chunk_size}), defaulting to 25.", level="WARNING")
            chunk_size = 25
    except (ValueError, TypeError):
        app.error_logging(f"Error parsing sequential_batch_size ({app.settings.sequential_batch_size}), defaulting to 25.", level="WARNING")
        chunk_size = 25

    num_chunks = math.ceil(len(df) / chunk_size)
    df_chunks = [df.iloc[i * chunk_size:(i + 1) * chunk_size] for i in range(num_chunks)] # Use iloc for reliable slicing
    results_dfs = []
    previous_chunk_last_data = None # Store data from the last item of the previous chunk

    # Determine text column once
    text_column = 'Original_Text' if 'Original_Text' in df.columns else 'Text' # Simplified

    print(f"Processing sequential data in {num_chunks} chunks of size {chunk_size}...")

    # Process chunks sequentially to pass context
    for i, chunk in enumerate(df_chunks):
        print(f"Processing chunk {i+1}/{num_chunks} (Indices: {chunk.index.min()}-{chunk.index.max()})")
        try:
            # Call the API for the current chunk, passing data from the previous one
            raw_response = asyncio.run(_call_single_chunk_api(app, chunk, preset_name, text_column, previous_chunk_last_data))

            # Reset last data for the next iteration in case of failure
            current_chunk_last_data = None

            if raw_response and raw_response != "Error":
                # Use the new extraction function directly
                # It handles cleaning, parsing, regex fallback, and basic error logging
                parsed_chunk_data = extract_json_from_response(raw_response, app.error_logging)

                # Check if the extraction was successful and returned a non-empty list
                if isinstance(parsed_chunk_data, list) and parsed_chunk_data:
                    chunk_results = [] # Initialize list to hold rows for this chunk's DataFrame

                    # Process each item (dictionary) in the parsed list
                    for item in parsed_chunk_data:
                        if not isinstance(item, dict) or not item:
                            app.error_logging(f"Skipping non-dictionary or empty item in parsed data: {item}", level="WARNING")
                            continue

                        try:
                            item_keys = list(item.keys())
                            if not item_keys:
                                app.error_logging(f"Skipping item with no keys: {item}", level="WARNING")
                                continue

                            # Assume the first key is the index key
                            index_key_name = item_keys[0]
                            index_value = item[index_key_name]

                            # Collect all other keys and their values as data
                            data_to_apply = {k: v for i, (k, v) in enumerate(item.items()) if i > 0}

                            indices = []
                            # Determine indices based on the type of the index_value
                            if isinstance(index_value, int):
                                indices = [index_value] # Single index
                            elif isinstance(index_value, str):
                                # Parse the string value (e.g., "0, 1, 2")
                                indices = _parse_index_string(index_value, app)
                                # --- DEBUG: Print parsed indices ---
                                app.error_logging(f"DEBUG: Parsed indices from '{index_value}': {indices}", level="DEBUG")
                                # --- END DEBUG ---
                            else:
                                app.error_logging(f"Unexpected type for index key '{index_key_name}': {type(index_value)}. Value: {index_value}. Skipping item.", level="WARNING")
                                continue # Skip this item if index format is wrong

                            if not indices:
                                app.error_logging(f"Could not extract valid indices from key '{index_key_name}' with value '{index_value}'. Skipping item.", level="WARNING")
                                continue # Skip if parsing indices failed

                            # Create a row for each index
                            for idx in indices:
                                row_data = {'index': idx}
                                row_data.update(data_to_apply)
                                chunk_results.append(row_data)

                        except Exception as item_processing_error:
                            app.error_logging(f"Error processing item based on key order: {item_processing_error}. Item: {item}", level="ERROR")
                            continue # Skip to the next item on error

                    # After processing all items, check if we gathered any results
                    if chunk_results:
                        chunk_df = pd.DataFrame(chunk_results)
                        
                        # --- DEBUG: Print head and tail of chunk_df ---
                        print("\n--- Chunk DF Head (Debug) ---")
                        print(chunk_df.head(3))
                        print("\n--- Chunk DF Tail (Debug) ---")
                        print(chunk_df.tail(3))
                        print("--- End Chunk DF Debug ---\n")
                        # --- END DEBUG ---
                        
                        # Get the context data from the *last* processed item's data
                        # Find the last item in the original parsed_chunk_data that was successfully processed
                        last_processed_original_item = None
                        if parsed_chunk_data:
                           # Iterate backwards through original items to find the one corresponding to the last chunk_result
                           # This assumes indices are unique within the chunk processing
                           if chunk_results:
                              last_idx_in_results = chunk_results[-1].get('index')
                              for original_item in reversed(parsed_chunk_data):
                                 if isinstance(original_item, dict):
                                     original_keys = list(original_item.keys())
                                     if original_keys:
                                         original_index_key = original_keys[0]
                                         original_index_val = original_item.get(original_index_key)
                                         parsed_original_indices = []
                                         if isinstance(original_index_val, int):
                                             parsed_original_indices = [original_index_val]
                                         elif isinstance(original_index_val, str):
                                             parsed_original_indices = _parse_index_string(original_index_val, app)

                                         if last_idx_in_results in parsed_original_indices:
                                             last_processed_original_item = original_item
                                             break # Found the item

                        if last_processed_original_item:
                            item_keys = list(last_processed_original_item.keys())
                            # Use the identified item to extract context data (all keys except the first)
                            current_chunk_last_data = {k: v for i, (k, v) in enumerate(last_processed_original_item.items()) if i > 0}
                            app.error_logging(f"Set context for next chunk: {current_chunk_last_data}", level="DEBUG")
                        else:
                            current_chunk_last_data = None # Reset if context couldn't be determined
                            app.error_logging("Could not determine context for next chunk from last processed item.", level="WARNING")

                        # Log columns found and append DF
                        app.error_logging(f"Chunk DF columns: {chunk_df.columns.tolist()}", level="DEBUG")
                        app.error_logging(f"Chunk DF shape: {chunk_df.shape}, rows processed: {len(chunk_results)}", level="INFO")
                        results_dfs.append(chunk_df)
                        app.error_logging(f"Appended chunk_df to results_dfs. Current count: {len(results_dfs)}", level="DEBUG")
                    else:
                        app.error_logging("No valid rows generated from parsed chunk data.", level="WARNING")
                        # Ensure context is reset if no valid rows were generated
                        current_chunk_last_data = None

                else:
                     # This else catches cases where parsed_chunk_data is None (extraction failed)
                     # or it wasn't a non-empty list
                     if parsed_chunk_data is not None: # Only log if it wasn't None but still invalid
                         app.error_logging(f"Parsed JSON chunk was not a non-empty list: {type(parsed_chunk_data)}", level="WARNING")
                     # Error logging for failed parsing is handled within extract_json_from_response

            elif raw_response == "Error":
                 app.error_logging("API call for a chunk returned 'Error'", level="ERROR")
            # else: response was None or empty, ignore

            # Update the data for the next chunk's context
            previous_chunk_last_data = current_chunk_last_data

        except Exception as e:
            app.error_logging(f"Error processing chunk {i+1}: {str(e)}", level="ERROR")
            previous_chunk_last_data = None # Reset context if a chunk fails

    # Concatenate all collected DataFrames
    if results_dfs:
        try:
            # Concatenate, ignoring index to create a fresh one if merging different formats
            combined_df = pd.concat(results_dfs, ignore_index=True)
            # Drop duplicates based on 'index' keeping the last occurrence if any overlaps happened
            # (Unlikely with chunking but safe)
            if 'index' in combined_df.columns:
                 combined_df = combined_df.drop_duplicates(subset=['index'], keep='last')
            
            print("Last three rows of the combined DataFrame from API results:")
            print(combined_df.tail(3))
            # Check if the crucial 'index' column exists before returning
            if 'index' not in combined_df.columns:
                 app.error_logging("Combined DataFrame is missing the crucial 'index' column!", level="ERROR")
                 return pd.DataFrame() # Return empty if index is missing

            # --- Add Debug Logging --- 
            app.error_logging(f"Final combined_df shape before return: {combined_df.shape}", level="DEBUG")
            app.error_logging(f"Final combined_df tail before return:\n{combined_df.tail()}", level="DEBUG")
            # --- End Debug Logging ---

             # Sort by index before returning for consistency
            combined_df = combined_df.sort_values(by='index') # Keep original index for merging
            return combined_df
        except Exception as concat_err:
             app.error_logging(f"Error during final concatenation or sorting: {concat_err}", level="ERROR")
             # Log the list of dataframes that failed to concat
             app.error_logging(f"results_dfs content snippet: {[df.head(1) for df in results_dfs[:2]]}", level="DEBUG")
             return pd.DataFrame()
    else:
        print("No valid data parsed from any API chunks.")
        return pd.DataFrame() # Return empty if no data was successfully parsed
