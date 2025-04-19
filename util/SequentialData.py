import json
import asyncio
import pandas as pd
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

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


async def _call_single_chunk_api(app, chunk_df, preset_name, text_column):
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
    print(f"\n--- API RESPONSE (Chunk starting index {chunk_df.index[0]}) ---\n" + str(response) + "\n")
    return response

def call_sequential_api(app, df, preset_name):
    """
    Call the API for sequential data analysis in chunks using the selected preset.
    - app: main app instance (must have .settings and .api_handler)
    - df: DataFrame to process
    - preset_name: name of the sequential metadata preset to use
    Returns: Combined DataFrame with results from all chunks, or empty DataFrame on error.
    """
    chunk_size = 25
    num_chunks = math.ceil(len(df) / chunk_size)
    df_chunks = [df[i * chunk_size:(i + 1) * chunk_size] for i in range(num_chunks)]
    results_dfs = []
    futures = []
    
    # Determine text column once
    text_column = 'Original_Text' if 'Original_Text' in df.columns else 'Text' # Simplified

    print(f"Processing sequential data in {num_chunks} chunks of size {chunk_size}...")

    with ThreadPoolExecutor(max_workers=10) as executor: # Limit concurrency if needed
        for i, chunk in enumerate(df_chunks):
            print(f"Submitting chunk {i+1}/{num_chunks} (Indices: {chunk.index.min()}-{chunk.index.max()})")
            future = executor.submit(asyncio.run, _call_single_chunk_api(app, chunk, preset_name, text_column))
            futures.append(future)

        for future in as_completed(futures):
            try:
                raw_response = future.result()
                if raw_response and raw_response != "Error":
                    cleaned_json = str(raw_response).strip()
                    if cleaned_json.startswith("```json"):
                        cleaned_json = cleaned_json[7:]
                    if cleaned_json.startswith("```"):
                        cleaned_json = cleaned_json[3:]
                    if cleaned_json.endswith("```"):
                        cleaned_json = cleaned_json[:-3]
                    cleaned_json = cleaned_json.strip()
                    
                    try:
                        parsed_chunk_data = json.loads(cleaned_json)
                        if isinstance(parsed_chunk_data, list) and parsed_chunk_data: # Ensure it's a non-empty list
                             # Create DF for this chunk and add to list
                             chunk_df = pd.DataFrame(parsed_chunk_data)
                             results_dfs.append(chunk_df) 
                        else:
                             app.error_logging(f"Parsed JSON chunk was not a non-empty list: {type(parsed_chunk_data)}", level="WARNING")
                             app.error_logging(f"Problematic JSON string (cleaned):\n{cleaned_json}", level="DEBUG")
                             
                    except json.JSONDecodeError as e:
                        app.error_logging(f"Error decoding JSON chunk: {e}", level="ERROR")
                        app.error_logging(f"Problematic JSON string (cleaned):\n{cleaned_json}", level="DEBUG")
                elif raw_response == "Error":
                     app.error_logging("API call for a chunk returned 'Error'", level="ERROR")
                # else: response was None or empty, ignore
                     
            except Exception as e:
                app.error_logging(f"Error processing chunk future: {str(e)}", level="ERROR")

    # Concatenate all collected DataFrames
    if results_dfs:
        combined_df = pd.concat(results_dfs, ignore_index=True)
        print("First three rows of the combined DataFrame from API results:")
        print(combined_df.head(3))
        # Check if the crucial 'index' column exists before returning
        if 'index' not in combined_df.columns:
             app.error_logging("Combined DataFrame is missing the crucial 'index' column!", level="ERROR")
             return pd.DataFrame() # Return empty if index is missing
        return combined_df
    else:
        print("No valid data parsed from any API chunks.")
        return pd.DataFrame() # Return empty if no data was successfully parsed
