import json
import re

def extract_json_from_response(response_text: str, error_logging_func=None):
    """
    Attempts to extract and parse JSON data from a string,
    handling potential markdown code fences.

    Args:
        response_text (str): The raw string potentially containing JSON.
        error_logging_func (callable, optional): Function to log errors. Defaults to print.

    Returns:
        The parsed JSON object (dict or list) or None if parsing fails.
    """
    if not error_logging_func:
        error_logging_func = print

    if not isinstance(response_text, str) or not response_text.strip():
        error_logging_func("JSON Extraction: Input response is not a valid string or is empty.", level="WARNING")
        return None

    cleaned_json = response_text.strip()

    # Revised Fence Removal Logic:
    # Use regex to find content within ```json ... ``` or ``` ... ```, handling optional newlines
    fence_match = re.search(r'^```(?:json)?\s*([\s\S]*?)\s*```$', cleaned_json, re.MULTILINE)
    if fence_match:
        cleaned_json = fence_match.group(1).strip()
        error_logging_func("JSON Extraction: Removed markdown fences using regex.", level="DEBUG")
    else:
        # If regex didn't match fences, strip again just in case
        cleaned_json = cleaned_json.strip()
        error_logging_func("JSON Extraction: No markdown fences found via regex.", level="DEBUG")

    # Optional: Handle potential escapes (use with caution, might corrupt valid JSON)
    # cleaned_json = cleaned_json.replace('\\n', '\\\\n').replace('\\"', '\\\\"')

    # Log the string *just before* the first parse attempt
    error_logging_func(f"JSON Extraction: Attempting initial parse on:\n---\n{cleaned_json[:1000]}...\n---", level="DEBUG")

    try:
        # First, try a direct parse
        parsed_data = json.loads(cleaned_json)
        error_logging_func("JSON Extraction: Initial parse successful.", level="INFO")
        return parsed_data
    except json.JSONDecodeError as e:
        error_logging_func(f"JSON Extraction: Initial parsing failed: {e}. Attempting regex extraction.", level="DEBUG")
        # Log the exact string that failed initial parsing
        error_logging_func(f"Problematic JSON string for initial parse:\n---\n{cleaned_json[:1000]}...\n---", level="DEBUG")

        # Attempt to find JSON array or object using regex as a fallback
        # This regex looks for the first '{' or '[' and the last '}' or ']'
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', cleaned_json, re.DOTALL)

        if json_match:
            potential_json = json_match.group(1).strip() # Ensure stripped here too
            error_logging_func(f"JSON Extraction: Found potential JSON via regex:\n---\n{potential_json[:1000]}...\n---", level="DEBUG")
            try:
                # Try parsing the regex-extracted string
                parsed_data = json.loads(potential_json)
                error_logging_func("JSON Extraction: Successfully parsed JSON found via regex fallback.", level="INFO")
                return parsed_data
            except json.JSONDecodeError as inner_e:
                error_logging_func(f"JSON Extraction: Parsing failed even after regex extraction: {inner_e}", level="ERROR")
                error_logging_func(f"Regex extracted JSON string that failed parsing:\n---\n{potential_json[:1000]}...\n---", level="DEBUG")
                return None
        else:
            error_logging_func("JSON Extraction: Could not find JSON object or array structure using regex fallback.", level="ERROR")
            return None
    except Exception as ex:
        error_logging_func(f"JSON Extraction: An unexpected error occurred: {ex}", level="ERROR")
        return None
