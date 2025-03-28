import json, os, shutil

class Settings:
    def __init__(self):
        # Set default values
        self.restore_defaults()
        
        # Get the appropriate app data directory
        if os.name == 'nt':  # Windows
            app_data = os.path.join(os.environ['APPDATA'], 'TranscriptionPearl')
        else:  # Linux/Mac
            app_data = os.path.join(os.path.expanduser('~'), '.transcriptionpearl')
        
        # Create the directory if it doesn't exist
        os.makedirs(app_data, exist_ok=True)

        # Create global temp directory
        self.temp_directory = os.path.join(app_data, 'temp')
        self.temp_images = os.path.join(self.temp_directory, 'images')
        self.temp_processing = os.path.join(self.temp_directory, 'processing')
        
        # Create directories
        os.makedirs(self.temp_directory, exist_ok=True)
        os.makedirs(self.temp_images, exist_ok=True)
        os.makedirs(self.temp_processing, exist_ok=True)
        
        # Define settings file path
        self.settings_file_path = os.path.join(app_data, 'settings.json')
        
        # Load settings if they exist
        if os.path.exists(self.settings_file_path):
            self.load_settings()

    def restore_defaults(self):
        # Save current API keys
        saved_openai_key = getattr(self, 'openai_api_key', "")
        saved_anthropic_key = getattr(self, 'anthropic_api_key', "")
        saved_google_key = getattr(self, 'google_api_key', "")
        
        self.chunk_text_presets = [
            {
                "name": "Letterbook",
                "model": "gemini-2.0-flash",
                "temperature": "0.2",
                "general_instructions": f'''You are an expert in historical document analysis. You will be provided with an image of a page from a letterbook along with its transcription. These letterbooks contain a series of letters transcribed sequentially by a scribe, and letters may span multiple pages.

Your task is to insert a letter break marker ("*****") on a new line immediately before the beginning of each new letter. To do this accurately, follow these guidelines:

1. Identify a New Letter Opening:

Header Indicators: Look for a distinct block that includes one or more of the following: a salutation, a date, a place name, an address, an addressee's name, or a greeting (e.g., "New York, 23d Jany 1789", "Messrs Phynn and Ellis", "Dear Sir,"). This block is usually formatted separately from the narrative text.

Formatting Cues: Notice any clear changes in formatting such as text being offset, right-justified, or indented compared to the preceding narrative. Such changes often indicate the start of a letter.

2. Contextual Analysis:

End of Previous Letter: Determine where the previous letter ends. Typical end-of-letter elements include a signature, a closing salutation, or a block containing a place name or address.

Paragraph Continuity: If one paragraph directly follows another without a new header (i.e., no new name, date, address, or distinct formatting), treat it as a continuation of the same letter—even if the subject matter shifts.

3. Avoiding False Breaks:

No Break on Internal Paragraphs: Do not insert a letter break marker between paragraphs that are part of the same letter. A mere change in subject matter or a simple formatting variation that does not involve a standalone header should not trigger a new letter marker.

Uncertainty: When it is unclear whether a new letter is starting, rely on the absence of header elements and distinct formatting. In such cases, do not insert a break marker.

In your response, begin by providing a brief explanation of how the above clues were evaluated. Then on a new line write "Transcription:" followed by the present transcription of the text, inserting the letter break marker ("*****") on a new line immediately before any confirmed new letter.

Your objective is to ensure that break markers are inserted only when a new letter truly begins, avoiding incorrect breaks between paragraphs within the same letter.''',
                "specific_instructions": "Document Text: {text_to_process}",
                "val_text": "Transcription:",
                "use_images": False
            },
            {
                "name": "Diary",
                "model": "gemini-2.0-flash",
                "temperature": "0.2",
                "general_instructions": f'''You are an expert in historical document analysis. You will be provided with a page from a historical diary that may contain part of a diary entry that continues from a previous page and/or onto the next page, or it may contain multiple diary entries.

Your task is to insert an entry break marker ("*****") on a new line immediately before the beginning of each new diary entry (including the first entry on the page if it begins on this page). To do this accurately, follow these guidelines:

1. Identify a New Diary Entry Opening:

Date Indicators: Look for temporal markers that typically begin a new entry (e.g., "January 23, 1789", "Monday 4th", "Saturday 4th", etc). These date markers will always be found at the beginning of a paragraph.

Formatting Cues: Notice any clear changes in formatting such as marginal notations, paragraphing, indentation, line breaks, or that consistently indicate a new entry in this diary.

2. Contextual Analysis:

Chunk Boundaries: Be aware that the text you're analyzing might begin in the middle of an entry. If the text begins without a clear date marker but seems to continue from a previous page, it likely belongs to an entry that started on the previous page.

3. Avoiding False Breaks:

No Break on Topic Changes: Do not insert an entry break marker when the diarist merely changes topics within the same day's entry.

No Break on New Paragraphs that Do Not Begin With Some Sort of Date Indicator: Do not insert an entry break marker when the diarist merely starts a new paragraph that does not begin a new entry, as identified by the Date Indicators above.

Handling Uncertainty: If you cannot determine with reasonable confidence whether text represents a new entry, err on the side of continuity and do not insert a break marker.

In your response, begin by providing a brief explanation of how you identified entry breaks. Then on a new line write "Processed Diary Text:" followed by the exact text of the provided page with entry break markers ("*****") inserted on a new line immediately before each new diary entry.

Your objective is to preserve the original diary structure as accurately as possible, ensuring entries are properly delineated for future analysis.''',
"specific_instructions": "Document Text: {text_to_process}",               
"val_text": "Processed Diary Text:",
                "use_images": False
            },
            {
                "name": "Parish Register",
                "model": "gemini-2.0-flash",
                "temperature": "0.2",
                "general_instructions": '''You are an expert in historical document analysis, specialized in identifying boundaries between distinct entries in a parish register of baptisms marriages, and burials. When presented with transcribed text and its corresponding page image, your task is to re-transcribe the text exactly as written, although any marginalia, spacing, etc should be standardized and formatted as follows:

Title of entry
Content
Signatures etc

Preceed each new entry that begins on the current page with "*****" written on a new line. Skip this step when the first lines on a page began on the previous page.

In your response, write any notes you need to that will help you. Then write "Transcription: " followed by your re-formatted transcription and nothing else.''',
                "specific_instructions": "Document Text: {text_to_process}",
                "val_text": "Transcription:",
                "use_images": False
            }
        ]

        self.function_presets = [
            {
                'name': "HTR",
                'model': "gemini-2.0-flash",
                'temperature': "0.3",
                'general_instructions': '''Your task is to accurately transcribe handwritten historical documents, minimizing the CER and WER. Work character by character, word by word, line by line, transcribing the text exactly as it appears on the page. To maintain the authenticity of the historical text, retain spelling errors, grammar, syntax, and punctuation as well as line breaks. Transcribe all the text on the page including headers, footers, marginalia, insertions, page numbers, etc. If these are present, insert them where indicated by the author (as applicable). In your response, write: "Transcription:" followed only by your accurate transcription''',
                'specific_instructions': '''Carefully transcribe this page from an 18th/19th century document. In your response, write: "Transcription:" followed only by your accurate transcription.''',
                'use_images': True,
                'current_image': "Yes",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Transcription:"
            },
            {
                'name': "Correct_Text",
                'model': "claude-3-7-sonnet-20250219",
                'temperature': "0.2",
                'general_instructions': '''Your task is to compare handwritten pages of text with corresponding draft transcriptions, correcting the transcription to produce an accurate, publishable transcript. Be sure that the spelling, syntax, punctuation, and line breaks in the transcription match those on the handwritten page to preserve the historical integrity of the document. Numbers also easily misread, so pay close attention to digits. You must also ensure that the transcription begins and ends in the same place as the handwritten document. Include any catchwords at the bottom of the page. In your response write "Corrected Transcript:" followed by your corrected transcription.''',
                'specific_instructions': '''Your task is to use the handwritten page image to correct the following transcription, retaining the spelling, syntax, punctuation, line breaks, catchwords, etc of the original.\n\n{text_to_process}''',
                'use_images': True,
                'current_image': "Yes",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Corrected Transcript:"
            },
            {
                'name': "Identify_Errors",
                'model': "claude-3-7-sonnet-20250219",
                'temperature': "0.2",
                'general_instructions': '''Your task is to compare draft transcriptions with the original handwritten document. You will identify all the single words and multiple-word phrases exactly as written in the transcription where you are less than 90% certain the transcription is correct. In your response, write "Errors:" followed by a semi-colon delineated list of all the errors you have identified.''',
                'specific_instructions': '''Here is the text to analyze:\n\n{text_to_process}''',
                'use_images': True,
                'current_image': "Yes",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Errors:"
            },
            {
                'name': "Get_Names_and_Places",
                'model': "claude-3-5-sonnet-20241022",
                'temperature': "0.7",
                'general_instructions': '''Your task is to read a historical document sent by the user and extract a complete list of all the names of people and places mentioned in the document. The intent is to use these lists to highlight these terms in the document so a user can better see them.

In your response write "Names:" followed by an alphabetized, semicolon delineated list of all the names of people mentioned in the document, including any titles and honorifics. 

Then on a new line write "Places:" followed by an alphabetized, semicolon delineated list of all the places mentioned in the document.

In both lists, retain all the original spelling, capitalization, and punctuation so that the user can search for these terms in the document. If there are no names and/or places leave the lists blank.

End your response after finishing the second list.'''

,
                'specific_instructions': '''Here is the text to analyze:\n\n{text_to_process}''',
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "None"
            },

            {
                'name': "Metadata",
                'model': "claude-3-5-sonnet-20241022",
                'temperature': "0.3",
                'general_instructions': '''You analyze historical documments to extract information. Read the document and then make any notes you require. Then, in your response, write "Metadata:" and then on new lines output the following headings, filling in the information beside each one:

Document Type: <Letter/Baptismal Record/Diary Entry/Will/etc.>
Author: <Last Name, First Name> - Note: for letters, memos, etc. use the name of the author of document. For other documents where the primary purposes if official or semi-official documentation of an individual(s), like a parish Birth, Marriage or Death Record, prison record, military service file, etc, use the name of the person(s) who the record is about.
Correspondent: <Last Name, First Name> - Note: Only for letters; use the name of the person(s) who the document is addressed to
Correspondent Place: <Place where the correspondent is located> - Note: Only for letters; use the place where the correspondent is located
Date: <DD/MM/YYYY>
Place of Creation: <Place where the document was written; for diary entries, use the place where the diarist was located at the end of the day of the entry>
People: <Last Name, First Name; Last Name, First Name;...>
Places: <Last Name, First Name; Last Name, First Name;...>
Summary:

For People, list all the names of people mentioned in the document. For Places, list all the places mentioned in the document. For Summary, write a brief summary of the document.

If you don't have information for a heading or don't know, leave it blank.''',
                'specific_instructions': '''Text to analyze:\n\n{text_to_process}''',
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Metadata:",
                'required_headers': ["Document Type", "Author", "Date", "Place of Creation", "People", "Places", "Summary"]
            },

            {
                'name': "Sequence_Dates",
                'model': "gemini-2.0-flash-lite",
                'temperature': "0.2",
#                 'general_instructions': '''You analyze a historical document in a sequence of documents (like a diary or letterbook) to identify the date it was written. You will be provided with a current document to analyze as well as the date and text of the previous document in the sequence.

# Read the document. If you can establish the complete date (year, month, and day) from the information contained in the current document to analzye, use only this information to generate your response. If you can only find a partial date such as a day of the week, day of the month, etc in the current document to analyze, use the additional context provided by the date and text of the previous entry to fill in the missing information.

# In your response, write "Date:" followed by the date of the current entry in the format YYYY/MM/DD. If you are less than 75% sure about the correctness of your answer, write "CHECK" on the next line and a human will verify your response.''',

                'general_instructions': '''You analyze a historical document in a sequence of documents (like a diary or letterbook) to identify the date it was written and where it was written. You will be provided with a current document to analyze as well as the date, place it was written, and text of the previous document in the sequence.

Read the document. If you can establish the complete date (year, month, and day) and the place it was writtenfrom the information contained in the current document, use only this information to generate your response. For the place a document was written, in letters this is often written at the top. For diaries, it is often the place where the diarist was located at the end of the day of the entry. If the location does not explicity change from the previous entry, you can use the same location as the previous entry.

If you can only find a partial date such as a day of the week, day of the month, etc in the current document, use the additional context provided by the date and text of the previous entry to fill in the missing information.

In your response, write "Date:" followed by the date of the current entry in the format YYYY/MM/DD. Then write "Place:" followed by the place where the document was written. If you are less than 90 percent sure about the correctness of either answer, write "CHECK" on the next line and a human will verify your response.''',
                'specific_instructions': '''{previous_date}
{previous_place} 

{previous_data}

Current Document to Analyze: {text_to_process}''',
                'use_images': False,
                'current_image': "No",  
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "None"
            },

            {
                'name': "Auto_Rotate",
                'model': "gemini-1.5-pro",
                'temperature': "0.0",
                'general_instructions': '''Describe the orientation of the handwritten text on the image from the standard reading orientation. In your response, write "Orientation:" followed only by one of the following answers: standard, rotated 90 clockwise, rotated 180 degrees, rotated 90 counter-clockwise, no text. ''',
                'specific_instructions': "",
                'use_images': True,
                'current_image': "Yes",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Orientation:"
            },
            {
                'name': "Translation",
                'model': "claude-3-7-sonnet-20250219",
                'temperature': "0.2",
                'general_instructions': '''You translate historical documents from other languages into English. In your response, write "Translation:" followed by a faithful, accurate translation of the document.''',
                'specific_instructions': '''Text to translate:\n\n{text_to_process}''',
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Translation:"
            }

        ]

        self.analysis_presets = [
            {
                'name': "Relevance",
                'model': "gemini-2.0-flash",
                'temperature': "0.3",
                'general_instructions' : '''You provide expert historical analysis. You examine a historical document and evaluate whether it meets the relevance criteria specified by a user. That criteria might include subjective factors such as whether the given document might be relevant to a particular research question or theme, or objective factors such as whether the document fits specific temporal or geographic requirements. Read the user's instructions, then the document provided, and determine whether the document fits the user's relevance criteria or not. Provide a confidence level for your judgement where 100% means absolute certainty. \n\nYou must end your response by writing: "Relevance:" followed by "Relevant", "Partially Relevant", "Irrelevant", or "Uncertain".''',
                'specific_instructions': '''The user's query and specific criteria are as follows: {query_text}. \n\n Here is the text to analyze:\n\n{text_to_process}''',
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Relevance:",
                'dataframe_field': "Relevance"
            },
            {
                'name': "Bounding_Boxes",
                'model': "gemini-2.0-flash",
                'temperature': "0.0",
                'top-p' : "0.95",
                'structured_output' : True,
                'general_instructions': '''You draw bounding boxes on an image of historical documents to identify the location of specific text. ''',
                'specific_instructions': '''In the accompanying image, detect the bounding box for each block of text as separated by "******". Do not overlap the boxes: \n\n {text_to_process}''',
                'use_images': True,
                'current_image': "Yes",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': None
            },
            {
                'name': "Bounding_Boxes_By_Row",
                'model': "gemini-2.0-flash",
                'temperature': "0.0",
                'top-p' : "0.95",
                'structured_output' : True,
                'general_instructions': '''You draw bounding boxes on an image of historical documents to identify the location of specific text. ''',
                'specific_instructions': '''In the accompanying image, detect the bounding box around the following text block: \n\n {text_to_process}''',
                'use_images': True,
                'current_image': "Yes",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': None
            }            
        ] # List of dictionaries for analysis presets
        
        self.format_presets = [
            {
                'name': "Parish_Record",
                'model': "gemini-2.0-flash",
                'temperature': "0.2",
                'general_instructions': '''You re-format historical documents to make them easier to read while retaining the original text. Remove all page numbers, headers, footers, archival stamps/references, etc. Remove all line breaks and other formatting. When identifying information is present in the margins, move this to a title line above the main record,In your response, write "Formatted Text:" followed by a formatted version of the document.''',
                'specific_instructions': '''Text to format:\n\n{text_to_process}''',
                'use_images': False,
                'current_image': "No",
            },
            {
                'name': "Diary",
                'model': "gemini-2.0-flash",
                'temperature': "0.2",
                'general_instructions': '''You re-format historical documents to make them easier to read while retaining the original text. Remove all page numbers, headers, footers, archival stamps/references, etc. Remove all line breaks and other formatting. Ensure that each entry is starts on a new line and that they are separated by a blank line. Include any marginalia at the end of the entry in square brackets with the notation "Marginalia:". In your response, write "Formatted Text:" followed by a formatted version of the document.''',
                'specific_instructions': '''Text to format:\n\n{text_to_process}''',
            },
            {
                'name': "Letter",
                'model': "gemini-2.0-flash",
                'temperature': "0.2",
                'general_instructions': '''You re-format historical documents to make them easier to read while retaining the original text. Remove all page numbers, headers, footers, archival stamps/references, etc. Remove all line breaks and other formatting. For the text in the heading and/or salutation (ie above the main body of the letter), order the material in this way (where applicable): place the letter was written, date, salutation. Follow this with the body of the letter. Include any marginalia on a separate line at the end of the paragraph encased in square brackets beginning with "Marginalia:". For the valediction/complementary close, order material as follows (where applicable): complementary close, signature, place/address, date. In your response, write "Formatted Text:" followed by a formatted version of the document.''',
                'specific_instructions': '''Text to format:\n\n{text_to_process}''',
            }
        ]

        # Default metadata presets
        self.metadata_presets = [
            {
                'name': "Standard Metadata",
                'model': "claude-3-5-sonnet-20241022",
                'temperature': "0.3",
                'general_instructions': '''You analyze historical documments to extract information. Read the document and then make any notes you require. Then, in your response, write "Metadata:" and then on new lines output the following headings, filling in the information beside each one:

Document Type: <Letter/Baptismal Record/Diary Entry/Will/etc.>
Author: <Last Name, First Name> - Note: for letters, memos, etc. use the name of the author of document. For other documents where the primary purposes if official or semi-official documentation of an individual(s), like a parish Birth, Marriage or Death Record, prison record, military service file, etc, use the name of the person(s) who the record is about.
Correspondent: <Last Name, First Name> - Note: Only for letters; use the name of the person(s) who the document is addressed to
Correspondent Place: <Place where the correspondent is located> - Note: Only for letters; use the place where the correspondent is located
Date: <DD/MM/YYYY>
Place of Creation: <Place where the document was written; for diary entries, use the place where the diarist was located at the end of the day of the entry>
People: <Last Name, First Name; Last Name, First Name;...>
Places: <Last Name, First Name; Last Name, First Name;...>
Summary:

For People, list all the names of people mentioned in the document. For Places, list all the places mentioned in the document. For Summary, write a brief summary of the document.

If you don't have information for a heading or don't know, leave it blank.''',
                'specific_instructions': '''Text to analyze:\n\n{text_to_process}''',
                'val_text': "Metadata:",
                'metadata_headers': "Document Type;Author;Correspondent;Correspondent Place;Date;Place of Creation;People;Places;Summary"
            }
        ]
        
        self.batch_size = 50
        self.check_orientation = False
        
        self.model_list = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.5-preview"
            "o1",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-7-sonnet-20250219",
            "claude-3-opus-20240229",
            "gemini-2.0-pro-exp-02-05",
            "gemini-2.0-flash",
            "gemini-2.0-flash-thinking-exp-01-21"

        ]

        # Restore API keys
        self.openai_api_key = saved_openai_key
        self.anthropic_api_key = saved_anthropic_key
        self.google_api_key = saved_google_key

        # Default metadata settings - keep for backward compatibility
        self.metadata_model = "claude-3-5-sonnet-20241022"
        self.metadata_temp = "0.3"
        self.metadata_system_prompt = '''You analyze historical documments to extract information. Read the document and then make any notes you require. Then, in your response, write "Metadata:" and then on new lines output the following headings, filling in the information beside each one:

Document Type: <Letter/Baptismal Record/Diary Entry/Will/etc.>
Author: <Last Name, First Name> - Note: for letters, memos, etc. use the name of the author of document. For other documents where the primary purposes if official or semi-official documentation of an individual(s), like a parish Birth, Marriage or Death Record, prison record, military service file, etc, use the name of the person(s) who the record is about.
Correspondent: <Last Name, First Name> - Note: Only for letters; use the name of the person(s) who the document is addressed to
Correspondent Place: <Place where the correspondent is located> - Note: Only for letters; use the place where the correspondent is located
Date: <DD/MM/YYYY>
Place of Creation: <Place where the document was written; for diary entries, use the place where the diarist was located at the end of the day of the entry>
People: <Last Name, First Name; Last Name, First Name;...>
Places: <Last Name, First Name; Last Name, First Name;...>
Summary:

For People, list all the names of people mentioned in the document. For Places, list all the places mentioned in the document. For Summary, write a brief summary of the document.

If you don't have information for a heading or don't know, leave it blank.'''
        self.metadata_user_prompt = '''Text to analyze:\n\n{text_to_process}'''
        self.metadata_val_text = "Metadata:"
        self.metadata_headers = "Document Type;Author;Correspondent;Correspondent Place;Date;Place of Creation;People;Places;Summary"
        self.metadata_preset = "Standard Metadata"  # Store the selected preset name

        self.ghost_system_prompt = ""
        self.ghost_user_prompt = ""
        self.ghost_val_text = ""
        self.ghost_model = "gpt-4o"
        self.ghost_temp = 0.2

    def save_settings(self):
        settings = {
            'openai_api_key': self.openai_api_key,                                      # API keys
            'anthropic_api_key': self.anthropic_api_key,
            'google_api_key': self.google_api_key,
            'model_list': self.model_list,                                              # List of models
            'batch_size': self.batch_size,                                              # Batch size for processing
            'check_orientation': self.check_orientation,                                # Check orientation of text
            'analysis_presets': self.analysis_presets,
            'function_presets': self.function_presets,
            'chunk_text_presets': self.chunk_text_presets,
            'metadata_presets': self.metadata_presets,                                  # Add metadata presets
            # Add individual metadata settings for backward compatibility
            'metadata_model': self.metadata_model,
            'metadata_temp': self.metadata_temp,
            'metadata_system_prompt': self.metadata_system_prompt,
            'metadata_user_prompt': self.metadata_user_prompt,
            'metadata_val_text': self.metadata_val_text,
            'metadata_headers': self.metadata_headers,
            'metadata_preset': self.metadata_preset                                     # Store selected preset
        }
        
        with open(self.settings_file_path, 'w') as f:
            json.dump(settings, f, indent=4)

    def load_settings(self):
        try:
            with open(self.settings_file_path, 'r') as f:
                settings = json.load(f)
                
            # Load all settings using get() to provide defaults
            for key, value in settings.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                    
        except FileNotFoundError:
            self.restore_defaults()

    def clear_temp_directories(self):
        """Clear all temporary directories"""
        for directory in [self.temp_images, self.temp_processing]:
            if os.path.exists(directory):
                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)