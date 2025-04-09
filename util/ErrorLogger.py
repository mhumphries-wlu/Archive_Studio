# util/ErrorLogger.py

# This file contains the ErrorLogger class, which is used to handle
# the error logging for the application.

import os
import traceback
from datetime import datetime

# Define log level mapping
LEVEL_MAP = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
DEFAULT_LOG_LEVEL = "ERROR" # Default if setting is invalid

def log_error(base_dir, log_level_setting, error_message, additional_info=None, level="ERROR"):
    """
    Logs messages to the error log file based on the configured log level.

    Args:
        base_dir (str): The base directory of the application (used to find the 'util' folder).
        log_level_setting (str): The minimum log level to record (e.g., "INFO", "ERROR").
        error_message (str): The main message to log.
        additional_info (str, optional): Additional details to include. Defaults to None.
        level (str, optional): The severity level of this specific message ("DEBUG", "INFO", "WARNING", "ERROR").
                               Defaults to "ERROR".
    """
    try:
        # Determine the numeric level for the current message and the setting
        message_level_num = LEVEL_MAP.get(level.upper(), 99) # Use 99 for unknown levels
        setting_level_num = LEVEL_MAP.get(str(log_level_setting).upper(), LEVEL_MAP[DEFAULT_LOG_LEVEL])

        # Skip logging if the message level is below the configured setting level
        if message_level_num < setting_level_num:
            return

        # Construct the path to the log file within the 'util' directory
        util_dir = os.path.join(base_dir, "util")
        os.makedirs(util_dir, exist_ok=True) # Ensure the directory exists
        error_logs_path = os.path.join(util_dir, "error_logs.txt")

        # Prepare the log entry
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp} [{level.upper()}]: {error_message}"

        if additional_info:
            log_entry += f" - Additional Info: {additional_info}"

        # Add stack trace for ERROR level messages, if available
        if level.upper() == "ERROR":
            stack = traceback.format_exc()
            # Add stack trace only if it's notDEFAULT_LOG_LEVEL])

        # Skip logging if the message level is below the configured setting level
        if message_level_num < setting_level_num:
            return

        # Construct the path to the log file within the 'util' directory
        util_dir = os.path.join(base_dir, "util")
        os.makedirs(util_dir, exist_ok=True) # Ensure the directory exists
        error_logs_path = os.path.join(util_dir, "error_logs.txt")

        # Prepare the log entry
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp} [{level.upper()}]: {error_message}"

        if additional_info:
            log_entry += f" - Additional Info: {additional_info}"

        # Add stack trace for ERROR level messages, if available
        if level.upper() == "ERROR":
            stack = traceback.format_exc()
            # Add stack trace only if it's not the default "NoneType: None\n"
            if stack and stack.strip() != "NoneType: None":
                log_entry += f"\nStack trace:\n{stack.strip()}"

        # Append the log entry to the file
        with open(error_logs_path, "a", encoding='utf-8') as file:
            file.write(log_entry + "\n")

    except Exception as e:
        # Fallback print if logging itself fails
        print(f"--- CRITICAL LOGGING FAILURE ---")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Original Level: {level}")
        print(f"Original Message: {error_message}")
        if additional_info:
            print(f"Original Additional Info: {additional_info}")
        print(f"Logging Exception: {e}")
        print(f"--- END CRITICAL LOGGING FAILURE ---")
