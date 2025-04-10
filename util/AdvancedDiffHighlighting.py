# AdvancedDiffHighlighting.py
# This file contains the AdvancedDiffHighlighter class, which is used to highlight
# specific differences between text versions.
# Instead of highlighting entire lines, this identifies and highlights
# specific characters that have changed.

import difflib
import tkinter as tk
import re
import os
from util.ErrorLogger import log_error

class AdvancedDiffHighlighter:
    """
    A class for more precise difference highlighting between text versions.
    Instead of highlighting entire lines, this identifies and highlights
    specific characters that have changed.
    """
    
    def __init__(self, text_widget, app=None):
        """
        Initialize with the text widget where highlighting will be applied.
        
        Args:
            text_widget: tkinter Text widget where highlighting will be applied
            app: Optional reference to main app for error logging
        """
        self.text_widget = text_widget
        self.app = app  # Store reference to main app for error logging
        
        # Configure the highlight tag if it doesn't exist
        try:
            self.text_widget.tag_configure("change_highlight", background="lightgreen")
        except Exception as e:
            self._log_error(f"Failed to configure change_highlight tag", str(e))
            
        # Configure word-level tag for more specific highlights
        try:
            self.text_widget.tag_configure("word_change_highlight", background="lightgreen")
        except Exception as e:
            self._log_error(f"Failed to configure word_change_highlight tag", str(e))
    
    def _log_error(self, error_message, additional_info=None, level="ERROR"):
        """Helper method to log errors using ErrorLogger"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_level_setting = "ERROR"  # Default log level
        
        # If app is available, try to get log_level from settings
        if self.app and hasattr(self.app, 'settings') and hasattr(self.app.settings, 'log_level'):
            log_level_setting = self.app.settings.log_level
        
        log_error(base_dir, log_level_setting, error_message, additional_info, level)
    
    def highlight_differences(self, previous_text, current_text):
        """
        Highlight specific differences between previous and current text.
        
        Args:
            previous_text: The older version of the text
            current_text: The current version of the text to highlight in
        """
        try:
            # Clear existing highlights
            self.text_widget.tag_remove("change_highlight", "1.0", tk.END)
            self.text_widget.tag_remove("word_change_highlight", "1.0", tk.END)
            
            # If either text is None or empty, return early
            if not previous_text or not current_text:
                return
            
            # First do line-level comparison to find which lines need detailed analysis
            previous_lines = previous_text.splitlines()
            current_lines = current_text.splitlines()
            
            # Use difflib to find line-level differences
            matcher = difflib.SequenceMatcher(None, previous_lines, current_lines)
            
            # Track current line number in the text widget
            widget_line = 1
            
            # Process each operation from the matcher
            for op, i1, i2, j1, j2 in matcher.get_opcodes():
                # 'equal' means the lines match, no highlighting needed
                if op == 'equal':
                    widget_line += (j2 - j1)
                    continue
                    
                # 'replace' means lines are different but correspond
                elif op == 'replace':
                    # Process each pair of different lines
                    for idx, (prev_line, curr_line) in enumerate(zip(previous_lines[i1:i2], current_lines[j1:j2])):
                        curr_widget_line = widget_line + idx
                        self._highlight_word_differences(prev_line, curr_line, curr_widget_line)
                    
                    # If lengths mismatch, handle remaining lines
                    if (i2 - i1) < (j2 - j1):
                        # More current lines than previous - additional lines were inserted
                        for idx in range(i2 - i1, j2 - j1):
                            line_num = widget_line + (i2 - i1) + idx
                            start = f"{line_num}.0"
                            end = f"{line_num}.end"
                            self.text_widget.tag_add("change_highlight", start, end)
                    
                    widget_line += (j2 - j1)
                    
                # 'delete' means lines were deleted, nothing to highlight in current text
                elif op == 'delete':
                    # Lines were in previous text but not in current text
                    # No highlighting needed as they don't exist in current display
                    pass
                    
                # 'insert' means new lines were added
                elif op == 'insert':
                    # Highlight all newly inserted lines
                    for idx in range(j2 - j1):
                        line_num = widget_line + idx
                        start = f"{line_num}.0"
                        end = f"{line_num}.end"
                        self.text_widget.tag_add("change_highlight", start, end)
                    
                    widget_line += (j2 - j1)
        except Exception as e:
            self._log_error("Error highlighting differences", str(e))
    
    def _highlight_word_differences(self, prev_line, curr_line, line_num):
        """
        Highlight specific word or character differences within a line.
        Ignores whitespace-only changes.
        
        Args:
            prev_line: Previous version of the line
            curr_line: Current version of the line
            line_num: Line number in the text widget
        """
        try:
            # Normalize whitespace for comparison (preserve words but standardize spaces)
            prev_line_normalized = re.sub(r'\s+', ' ', prev_line.strip())
            curr_line_normalized = re.sub(r'\s+', ' ', curr_line.strip())
            
            # If the lines are identical after normalizing whitespace, don't highlight anything
            if prev_line_normalized == curr_line_normalized:
                return
                
            # Split lines into words
            prev_words = self._tokenize_line(prev_line)
            curr_words = self._tokenize_line(curr_line)
            
            # Use sequence matcher to find word-level differences
            matcher = difflib.SequenceMatcher(None, prev_words, curr_words)
            
            # Track position in the line
            char_pos = 0
            
            for op, i1, i2, j1, j2 in matcher.get_opcodes():
                if op == 'equal':
                    # Words match, advance position
                    for word in curr_words[j1:j2]:
                        char_pos += len(word)
                
                elif op in ('replace', 'insert'):
                    # Words were replaced or inserted
                    for word in curr_words[j1:j2]:
                        # Skip highlighting for whitespace-only changes
                        if word.strip() == '':
                            char_pos += len(word)
                            continue
                            
                        # Check if this is a whitespace-only change
                        if op == 'replace' and i2-i1 == j2-j1:
                            # If same number of tokens, check if they're just whitespace variants
                            whitespace_only_change = True
                            for k in range(j2-j1):
                                prev_idx = i1 + k
                                curr_idx = j1 + k
                                
                                # If both are within bounds
                                if prev_idx < len(prev_words) and curr_idx < len(curr_words):
                                    prev_token = prev_words[prev_idx]
                                    curr_token = curr_words[curr_idx]
                                    
                                    # If both are whitespace or both are non-whitespace with same normalized form
                                    is_whitespace_change = (prev_token.strip() == '' and curr_token.strip() == '') or \
                                                          (prev_token.strip() != '' and curr_token.strip() != '' and 
                                                           prev_token.strip() == curr_token.strip())
                                    
                                    if not is_whitespace_change:
                                        whitespace_only_change = False
                                        break
                            
                            if whitespace_only_change:
                                char_pos += len(word)
                                continue
                        
                        # Highlight the word if it's not just a whitespace change
                        start = f"{line_num}.{char_pos}"
                        end = f"{line_num}.{char_pos + len(word)}"
                        self.text_widget.tag_add("word_change_highlight", start, end)
                        char_pos += len(word)
                
                elif op == 'delete':
                    # Words were deleted, nothing to highlight
                    pass
        except Exception as e:
            self._log_error(f"Error highlighting word differences at line {line_num}", str(e))
    
    def _tokenize_line(self, line):
        """
        Split a line into meaningful tokens for comparison.
        Includes whitespace as separate tokens to preserve spacing.
        
        Args:
            line: The text line to tokenize
            
        Returns:
            List of tokens (words and whitespace)
        """
        try:
            # Pattern to split by word boundaries but keep whitespace
            tokens = []
            
            # Pattern to match words or sequences of whitespace
            for match in re.finditer(r'(\s+|\S+)', line):
                tokens.append(match.group(0))
                
            return tokens
        except Exception as e:
            self._log_error("Error tokenizing line", str(e))
            return [] # Return empty list on error

def highlight_text_differences(text_widget, current_level, previous_level, app=None):
    """
    Highlight differences between two text levels in the text widget.
    
    Args:
        text_widget: tkinter Text widget where highlighting will be applied
        current_level: The text currently displayed
        previous_level: The text to compare against (previous version)
        app: Optional reference to main app for error logging
    """
    try:
        # Create highlighter
        highlighter = AdvancedDiffHighlighter(text_widget, app)
        
        # Apply highlighting
        highlighter.highlight_differences(previous_level, current_level)
    except Exception as e:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_level_setting = "ERROR"  # Default log level
        
        # If app is available, try to get log_level from settings
        if app and hasattr(app, 'settings') and hasattr(app.settings, 'log_level'):
            log_level_setting = app.settings.log_level
            
        log_error(base_dir, log_level_setting, "Error highlighting text differences", str(e))

# Function that could be integrated into the main application
def highlight_text_changes(self):
    """
    A function that could be used in the main application to highlight differences
    between the current text level and the previous level.
    
    This would replace the existing highlight_changes method in the main App class.
    """
    try:
        index = self.page_counter
        current_toggle = self.main_df.loc[index, 'Text_Toggle']
        
        # Early exit if we're at the Original_Text level (no previous text to compare with)
        if current_toggle == "Original_Text" or current_toggle == "None":
            return
            
        # Determine which texts to compare based on current level
        if current_toggle == "Corrected_Text":
            # Compare Corrected_Text with Original_Text
            current_text = self.main_df.loc[index, 'Corrected_Text']
            previous_text = self.main_df.loc[index, 'Original_Text']
            
            # Skip if either text is missing
            if pd.isna(current_text) or pd.isna(previous_text):
                return
                
        elif current_toggle == "Final_Draft":
            # Compare Final_Draft with Corrected_Text
            current_text = self.main_df.loc[index, 'Final_Draft']
            previous_text = self.main_df.loc[index, 'Corrected_Text']
            
            # If Corrected_Text is empty, compare with Original_Text instead
            if pd.isna(previous_text) or previous_text.strip() == '':
                previous_text = self.main_df.loc[index, 'Original_Text']
                
            # Skip if either text is missing
            if pd.isna(current_text) or pd.isna(previous_text):
                return
        else:
            # Unrecognized toggle value
            return
        
        # Use the advanced highlighting with app reference for error logging
        highlight_text_differences(self.text_display, current_text, previous_text, self)
    except Exception as e:
        self.error_logging(f"Error in highlight_text_changes", str(e)) 