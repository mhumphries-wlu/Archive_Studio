import json
import asyncio
import pandas as pd
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

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
    if ',' in index_str:
        for part in index_str.split(','):
            part = part.strip()
            if part and part.isdigit():
                try:
                    # Assume indices from API are 0-based
                    index_val = int(part)
                    if index_val >= 0: # Ensure non-negative index
                        indices.append(index_val)
                    else:
                        app.error_logging(f"Skipping invalid 0 or negative index derived from '{part}'.", level="WARNING")
                except ValueError:
                    app.error_logging(f"Could not convert part '{part}' to integer.", level="WARNING")
        
        # If we successfully parsed comma-separated values, return them
        if indices:
            app.error_logging(f"Parsed {len(indices)} indices from comma-separated list: {indices}", level="DEBUG")
            return indices
    
    # Fall back to the original parsing logic for space-separated or other formats
    parts = re.split(r'[,\s]+', index_str.strip())
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.isdigit():
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
                # Clean the raw response string
                cleaned_json = str(raw_response).strip()
                # Remove potential markdown code fences (```json ... ``` or ``` ... ```)
                if cleaned_json.startswith("```json"):
                    cleaned_json = cleaned_json[7:]
                if cleaned_json.startswith("```"):
                     cleaned_json = cleaned_json[3:]
                if cleaned_json.endswith("```"):
                    cleaned_json = cleaned_json[:-3]
                cleaned_json = cleaned_json.strip() # Strip again after removal

                try:
                    parsed_chunk_data = json.loads(cleaned_json)
                    if isinstance(parsed_chunk_data, list) and parsed_chunk_data: # Ensure it's a non-empty list
                        first_item = parsed_chunk_data[0]
                        # --- Format Detection ---
                        if isinstance(first_item, dict) and 'index' in first_item:
                            # OLD FORMAT: List of dicts, each with 'index'
                            app.error_logging("Detected old format (list of dicts with 'index')", level="INFO")
                            chunk_df = pd.DataFrame(parsed_chunk_data)
                            results_dfs.append(chunk_df)
                        elif isinstance(first_item, dict) and any(re.match(r'^[\d,\s-]+$', str(v)) for v in first_item.values()):
                            # NEW FORMAT DETECTED: At least one value looks like a comma/space/hyphen separated list of numbers.
                            app.error_logging("Detected new format (dict with one index-like key and data keys)", level="INFO")
                            chunk_results = []

                            for item in parsed_chunk_data:
                                if isinstance(item, dict):
                                    index_key = None
                                    index_str = None
                                    data_to_apply = {}

                                    # Find the index key and separate data keys
                                    for k, v in item.items():
                                        # Check if value looks like a list of indices (string of digits, commas, spaces, hyphens)
                                        if isinstance(v, (str, int, float)) and re.match(r'^[\d,\s-]+$', str(v)):
                                            if index_key is None: # Found the first potential index key
                                                index_key = k
                                                index_str = str(v)
                                            else:
                                                 app.error_logging(f"Warning: Multiple potential index keys found in item: {item}. Using first one found ('{index_key}').", level="WARNING")
                                                 data_to_apply[k] = v # Treat subsequent index-like keys as data for now
                                        else:
                                            data_to_apply[k] = v # This is a data key

                                    if index_key is not None and index_str is not None:
                                        indices = _parse_index_string(index_str, app) # Parse the found index string
                                        # Data_to_apply now contains all keys *except* the identified index_key
                                        
                                        # Ensure all indices got parsed properly
                                        if not indices and index_str.strip():
                                            app.error_logging(f"Warning: Failed to parse any indices from '{index_str}'", level="WARNING")
                                        
                                        # Fix for 'Indecies' field when multiple indices are combined
                                        if index_key.lower() == 'indecies' or index_key.lower() == 'indices':
                                            app.error_logging(f"Found grouped indices: {index_str}", level="INFO")
                                            # Make sure we have at least one index
                                            if not indices:
                                                # Try a fallback parse for comma-separated indices
                                                try:
                                                    indices_str = index_str.strip()
                                                    raw_indices = [int(idx.strip()) for idx in indices_str.split(',') if idx.strip().isdigit()]
                                                    if raw_indices:
                                                        indices = raw_indices
                                                        app.error_logging(f"Parsed {len(indices)} indices using fallback method", level="INFO")
                                                except Exception as e:
                                                    app.error_logging(f"Fallback parsing failed: {e}", level="WARNING")

                                        for idx in indices:
                                            row_data = {'index': idx}
                                            row_data.update(data_to_apply) # Add the extracted data
                                            chunk_results.append(row_data)
                                    else:
                                         app.error_logging(f"Skipping item: Could not identify a unique index key in {item}", level="WARNING")
                                else:
                                     app.error_logging(f"Skipping invalid item in new format list: {item}", level="WARNING")

                            if chunk_results:
                                chunk_df = pd.DataFrame(chunk_results)
                                # Get the data from the *last* item processed in this chunk
                                if chunk_results:
                                    last_processed_item_in_chunk = chunk_results[-1]
                                    # We need the data part, excluding the 'index' key
                                    current_chunk_last_data = {k: v for k, v in last_processed_item_in_chunk.items() if k != 'index'}

                                # Log columns found in this chunk's df for debugging
                                app.error_logging(f"Chunk DF columns: {chunk_df.columns.tolist()}", level="DEBUG")
                                app.error_logging(f"Chunk DF shape: {chunk_df.shape}, rows processed: {len(chunk_results)}", level="INFO")
                                results_dfs.append(chunk_df)
                        else:
                            # Unrecognized format
                            app.error_logging(f"Unrecognized JSON structure in chunk response: First item: {first_item}", level="WARNING")
                            app.error_logging(f"Problematic JSON string (cleaned):\n{cleaned_json}", level="DEBUG")

                    else:
                         app.error_logging(f"Parsed JSON chunk was not a non-empty list: {type(parsed_chunk_data)}", level="WARNING")
                         app.error_logging(f"Problematic JSON string (cleaned):\n{cleaned_json}", level="DEBUG")
                         
                except json.JSONDecodeError as e:
                    app.error_logging(f"Error decoding JSON chunk: {e}", level="ERROR")
                    app.error_logging(f"Problematic JSON string (cleaned):\n{cleaned_json}", level="DEBUG")
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
