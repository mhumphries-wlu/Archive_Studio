# util/Settings.py

# This file contains the Settings class, which is used to handle
# the settings for the application.

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

        # Add sequential batch size
        self.sequential_batch_size = 25 # Default

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
                "general_instructions": f'''You are an expert in historical document analysis. You will be provided with a historical document with numbered lines. These letterbooks contain a series of letters transcribed sequentially by a scribe, and letters may span multiple pages.

Your task is to identify the line numbers immediately before the beginning of each new letter where a document separator should be inserted. To do this accurately, follow these guidelines:

1. Identify a New Letter Opening:

Header Indicators: Look for a distinct block that includes one or more of the following: a salutation, a date, a place name, an address, an addressee's name, or a greeting (e.g., "New York, 23d Jany 1789", "Messrs Phynn and Ellis", "Dear Sir,"). This block is usually formatted separately from the narrative text.

Formatting Cues: Notice any clear changes in formatting such as text being offset, right-justified, or indented compared to the preceding narrative. Such changes often indicate the start of a letter.

2. Contextual Analysis:

End of Previous Letter: Determine where the previous letter ends. Typical end-of-letter elements include a signature, a closing salutation, or a block containing a place name or address.

Paragraph Continuity: If one paragraph directly follows another without a new header (i.e., no new name, date, address, or distinct formatting), treat it as a continuation of the same letter—even if the subject matter shifts.

3. Avoiding False Breaks:

No Break on Internal Paragraphs: Do not insert a letter break marker between paragraphs that are part of the same letter. A mere change in subject matter or a simple formatting variation that does not involve a standalone header should not trigger a new letter marker.

4. Handling Uncertainty: When it is unclear whether a new letter is starting, rely on the absence of header elements and distinct formatting. In such cases, do not insert a break marker.

5. Handling the First Text on Page: be sure to include the line number of the first text on the page if it is a date indicator/element and otherwise appears to be a new letter.

In your response, begin by providing a brief explanation of how the above clues were evaluated. Then on a new line write "Document Break Lines:" followed by the line numbers where a document break should be inserted, separated by semicolons. 
For example: "Document Break Lines: 4;15;27"

These are the line numbers where a document separator should be placed immediately BEFORE that line. The document separator will mark the start of a new letter.

Your objective is to ensure that break markers are inserted only when a new letter truly begins, avoiding incorrect breaks between paragraphs within the same letter.''',
                "specific_instructions": "Document Text: {text_to_process}",
                "val_text": "Document Break Lines:",
                "use_images": False
            },
            {
                "name": "Diary",
                "model": "gemini-2.0-flash",
                "temperature": "0.2",
                "general_instructions": f'''You are an expert in historical document analysis. You will receieve a page from a historical diary with numbered lines. Your task is to identify the line numbers on which each new diary entry begins (including the first text on the page if it begins on this page). To do this accurately, follow these guidelines:

1. Identify a New Diary Entry Opening:

Date Indicators: Look for temporal markers at the beginning of a paragraph(e.g., "January 23, 1789", "Monday 4th", "Saturday 4th", etc). Sometimes date elements like the year, month (including abbreviations), day of the week, and day of the month might appear over multiple lines. When this is the case, the entry begins with the first element of the date.
Formatting Cues: Notice any clear changes in formatting such as marginal notations, paragraphing, indentation, line breaks, or that consistently indicate a new entry in this diary.

2. Contextual Analysis:

Chunk Boundaries: Be aware that the text you're analyzing might begin in the middle of an entry. If the text begins without a clear date marker/element but seems to continue from a previous page, it likely belongs to an entry that started on the previous page.

3. Avoiding False Breaks:

When the diarist merely changes topics within the same day's entry, it is not a new entry. Similarily, when the diarist merely starts a new paragraph without a date indicator, it is unlikely to be a new entry.

4. Handling Uncertainty: If you cannot determine with reasonable confidence whether text represents a new entry, err on the side of continuity and do not insert a break marker.

*****

Handling the First Text on Page: be sure to include the line number of the first text on the page if it is a date indicator/element and otherwise appears to be a new entry.

In your response, write "Document Break Lines:" followed by the line numbers where a document break should be inserted, separated by semicolons. Always include the first line number of the page if it is a date indicator or otherwise appears to be a new entry.
For example: "Document Break Lines: 4;15;27". 

These are the line numbers where a document separator should be placed immediately BEFORE that line. The document separator will mark the start of a new entry.

Your objective is to preserve the original diary structure as accurately as possible, ensuring entries are properly delineated for future analysis.''',
                "specific_instructions": "Document Text: {text_to_process}",               
                "val_text": "Document Break Lines:",
                "use_images": False
            },
            {
                "name": "Parish Register",
                "model": "gemini-2.0-flash",
                "temperature": "0.2",
                "general_instructions": '''You are an expert in historical document analysis, specialized in identifying boundaries between distinct entries in a parish register of baptisms marriages, and burials. When presented with transcribed text with numbered lines, your task is to identify where new entries begin.

Your task is to identify the line numbers immediately before the beginning of each new entry (including the first entry on the page if it begins on this page). Skip this step when the first lines on a page began on the previous page.

In your response, write any notes you need to that will help you. Then write "Document Break Lines:" followed by the line numbers where a document break should be inserted, separated by semicolons. 
For example: "Document Break Lines: 4;15;27"

These are the line numbers where a document separator should be placed immediately BEFORE that line. The document separator will mark the start of a new entry.''',
                "specific_instructions": "Document Text: {text_to_process}",
                "val_text": "Document Break Lines:",
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
                'name': "Auto_Rotate",
                'model': "gemini-2.0-flash",
                'temperature': "0.0",
                'general_instructions': '''Draw a bounding box around the first line of text on the page. In your analysis include titles, headers, paragraphs, etc.''',
                'specific_instructions': "",
                'use_images': True,
                'current_image': "Yes",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': None
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
                'specific_instructions': '''Use the following criteria to determine the level of relevance of a given document:\n\n {query_text}. \n\n Here is the document to analyze:\n\n{text_to_process}''',
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Relevance:",
            },
            {
                'name': "Collate_Names",
                'model': "gemini-2.5-pro-preview-03-25",
                'temperature': "0.2",
                'general_instructions': f"""You are given the text of a primary document and all the various spellings of the names of people mentioned in that document. Your task is to identify cases where more than one spelling (including errors and typos) is used to refer to a specific person in the document and then correct those errors. You will compile a list of names and their corrections which will be used in a regex function, replacing the error text with the correction.

RULES

Follow these rules when compiling your list of names and corrections:

- Only include cases where a name is spelled more than one way in your list.
- Treat whole names (IE "John Smith" as in "Last night John Smith arrived") as separate entries from single last names (IE "Smith" as in "Last night Smith arrived"); ignore orphaned/single first names entirely (IE "John" as in "Last night John arrived").
- Treat pluralized and possessives as separate entries from their singular/non-possessive forms (IE "John Smith's" would be a seperate correction item from "John Smith" to avoid confusion).
- Ignore honorifics, titles, etc unless the honorific/title requires correcting (IE use "John Smith" for "Mr. John Smith", "John Smith, Esq.", etc but correct "Mf. John Smith" to "Mr. John Smith" etc).
- Group variants of the same name together where a single change would apply to all errors (IE "John Smith = Johh Smith, Jonn Smith, John Smeth, John Smmth")

OUTPUT FORMAT

Each item in your list must be written on a new line. Each new line begins with the correction/correct form of the name followed by an equals sign and then the list of errors to which we will apply the correction in a semi-colon delineated list. Do not include any explanations or additional information in your list.

Example Output:

John Smith = John Smith; Jonn Smyth; Johh Smith
J. Smith = J Smeth; J Smmth; 7 Smith
Smith = Smihh; Smethh""",
                'specific_instructions': 'List of names to process:\n{text_for_llm}',
                'val_text': '',
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0"
            },
            {
                'name': "Collate_Places",
                'model': "gemini-2.5-pro-preview-03-25",
                'temperature': "0.2",
                'general_instructions': '''You are given a list of historical place names potentially containing spelling variations or OCR errors. Your task is to group variants of the same place together and choose the most complete or correct spelling as the primary entry. Format the output STRICTLY as follows, starting each line with the chosen primary spelling, followed by '=', then all identified variants (including the primary spelling itself) separated by semicolons.\n\nRules:\n- Group variants based on likely identity (similar spelling, OCR errors, phonetic similarity).\n- Every single item from the input list MUST appear as a variant in exactly one group in your output.\n- Output only the grouped lists in the specified format, starting immediately with the first primary spelling.\n\nFormat Example:\nLondon = London; Londn; london\n''',
                'specific_instructions': 'Collate the following list of places. Ensure every item appears in the output. Format according to the rules provided.\n\nList:\n{text_for_llm}',
                'val_text': '',
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0"
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
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Formatted Text:"
            },

            {
                'name': "Diary",
                'model': "gemini-2.0-flash",
                'temperature': "0.2",
                'general_instructions': '''You re-format historical documents to make them easier to read while retaining the original text. Remove all page numbers, headers, footers, archival stamps/references, etc. Remove all line breaks and other formatting. Ensure that each entry is starts on a new line and that they are separated by a blank line. Include any marginalia at the end of the entry in square brackets with the notation "Marginalia:". In your response, write "Formatted Text:" followed by a formatted version of the document.''',
                'specific_instructions': '''Text to format:\n\n{text_to_process}''',
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Formatted Text:"
            },
            {
                'name': "Letter",
                'model': "gemini-2.0-flash",
                'temperature': "0.2",
                'general_instructions': '''You re-format historical documents to make them easier to read while retaining the original text. Remove all page numbers, headers, footers, archival stamps/references, etc. Remove all line breaks and other formatting. For the text in the heading and/or salutation (ie above the main body of the letter), order the material in this way (where applicable): place the letter was written, date, salutation. Follow this with the body of the letter. Include any marginalia on a separate line at the end of the paragraph encased in square brackets beginning with "Marginalia:". For the valediction/complementary close, order material as follows (where applicable): complementary close, signature, place/address, date. In your response, write "Formatted Text:" followed by a formatted version of the document.''',
                'specific_instructions': '''Text to format:\n\n{text_to_process}''',
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Formatted Text:"
            }
        ]

        self.relevance_presets = [
            {
                'name': "Relevance",
                'model': "gemini-2.0-flash",
                'temperature': "0.3",
                'general_instructions' : '''You provide expert historical analysis. You examine a historical document and evaluate whether it meets the relevance criteria specified by a user. That criteria might include subjective factors such as whether the given document might be relevant to a particular research question or theme, or objective factors such as whether the document fits specific temporal or geographic requirements. Read the user's instructions, then the document provided, and determine whether the document fits the user's relevance criteria or not. Provide a confidence level for your judgement where 100% means absolute certainty. \n\nYou must end your response by writing: "Relevance:" followed by "Relevant", "Partially Relevant", "Irrelevant", or "Uncertain".''',
                'specific_instructions': '''Use the following criteria to determine the level of relevance of a given document:\n\n {query_text}. \n\n Here is the document to analyze:\n\n{text_to_process}''',
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Relevance:"
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
        
        self.sequential_metadata_presets = [
            {
                'name': "Sequence_Dates",
                'model': "gemini-2.0-flash-lite",
                'temperature': "0.2",
                'general_instructions': '''You analyze a historical document in a sequence of documents (like a diary or letterbook) to identify the date it was written and where it was written. You will be provided with a current document to analyze as well as the date, place it was written, and text of the previous document in the sequence.

Read the document. If you can establish the complete date (year, month, and day) and the place it was writtenfrom the information contained in the current document, use only this information to generate your response. For the place a document was written, in letters this is often written at the top. For diaries, it is often the place where the diarist was located at the end of the day of the entry. If the location does not explicity change from the previous entry, you can use the same location as the previous entry.

If you can only find a partial date such as a day of the week, day of the month, etc in the current document, use the additional context provided by the date and text of the previous entry to fill in the missing information.

In your response, write "Date:" followed by the date of the current entry in the format YYYY/MM/DD. Then write "Place:" followed by the place where the document was written. If you are less than 90 percent sure about the correctness of either answer, write "CHECK" on the next line and a human will verify your response.''',
                'specific_instructions': '''{previous_headers}

Current Document to Analyze: {text_to_process}''',
                'use_images': False,
                'current_image': "No",  
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "None"
            },
            {
                'name': "Sequence_Diary",
                'model': "gemini-2.0-flash-lite",
                'temperature': "0.2",
                'general_instructions': '''You analyze a historical diary entry in a sequence of diary entries to identify the date it was written, the place it was written, and who the author was. You will be provided with the current diary entry to analyze as well as information from the previous entry including its date, place, author, and text.

Read the current entry. If you can establish the complete date (year, month, and day), place, and author directly from information in the current entry, use only this information. For the place, it is often the location where the diarist was at the end of the day. If the location does not explicitly change from the previous entry, use the same location. Similarly, if the author is not explicitly mentioned, assume it's the same as the previous entry.

If you can only find partial information such as a day of the week or day of the month in the current entry, use the additional context provided by the previous entry to fill in the missing information.

In your response, provide the following information:
"Date:" followed by the date of the current entry in the format YYYY/MM/DD. 
"Place:" followed by the place where the diary entry was written.
"Author:" followed by the name of the diarist.

If you are less than 90 percent sure about the correctness of any answer, write "CHECK" on the next line and a human will verify your response.''',
                'specific_instructions': '''{previous_headers}

Current Diary Entry to Analyze: {text_to_process}''',
                'use_images': False,
                'current_image': "No",  
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "None"
            }
        ]

        self.batch_size = 50
        self.check_orientation = False
        
        self.model_list = [
            "gpt-4o",
            "gpt-4.5-preview",
            "claude-3-5-sonnet-20241022",
            "claude-3-7-sonnet-20250219",
            "gemini-2.0-flash",
            "gemini-2.5-pro-exp-03-25"
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
        self.metadata_preset = "Standard Metadata"  # Store the selected preset

        self.ghost_system_prompt = ""
        self.ghost_user_prompt = ""
        self.ghost_val_text = ""
        self.ghost_model = "gpt-4o"
        self.ghost_temp = 0.2

        # --- Add robust default initialization for translation settings ---
        self.translation_system_prompt = "You translate historical documents from other languages into English. In your response, write 'Translation:' followed by a faithful, accurate translation of the document."
        self.translation_user_prompt = "Text to translate:\n\n{text_to_process}"
        self.translation_val_text = "Translation:"
        self.translation_model = "claude-3-7-sonnet-20250219"

        # --- Add robust default initialization for query settings ---
        self.query_system_prompt = "You answer questions about historical documents. In your response, write 'Answer:' followed by a concise, accurate answer to the user's question."
        self.query_val_text = "Answer:"
        self.query_model = "claude-3-7-sonnet-20250219"

    def save_settings(self):
        settings = {
            'openai_api_key': self.openai_api_key,                                      # API keys
            'anthropic_api_key': self.anthropic_api_key,
            'google_api_key': self.google_api_key,
            'model_list': self.model_list,                                              # List of models
            'batch_size': self.batch_size,                                              # Batch size for processing
            'check_orientation': self.check_orientation,                                # Check orientation of text
            'analysis_presets': self._ensure_image_fields(self.analysis_presets),
            'function_presets': self._ensure_image_fields(self.function_presets),
            'chunk_text_presets': self._ensure_image_fields(self.chunk_text_presets),
            'format_presets': self._ensure_image_fields(self.format_presets),
            'metadata_presets': self._ensure_image_fields(self.metadata_presets),
            'sequential_metadata_presets': self._ensure_image_fields(self.sequential_metadata_presets),
            # Add individual metadata settings for backward compatibility
            'metadata_model': self.metadata_model,
            'metadata_temp': self.metadata_temp,
            'metadata_system_prompt': self.metadata_system_prompt,
            'metadata_user_prompt': self.metadata_user_prompt,
            'metadata_val_text': self.metadata_val_text,
            'metadata_headers': self.metadata_headers,
            'metadata_preset': self.metadata_preset,                                    # Store selected preset
            # Add translation and query settings
            'translation_system_prompt': self.translation_system_prompt,
            'translation_user_prompt': self.translation_user_prompt,
            'translation_val_text': self.translation_val_text,
            'translation_model': self.translation_model,
            'query_system_prompt': self.query_system_prompt,
            'query_val_text': self.query_val_text,
            'query_model': self.query_model,
            'sequential_batch_size': self.sequential_batch_size,                     # Sequential Batch Size
        }
        
        with open(self.settings_file_path, 'w') as f:
            json.dump(settings, f, indent=4)

    def load_settings(self):
        # Store default presets before loading from file
        default_analysis_presets = self._ensure_image_fields(self.analysis_presets)
        # Add other default preset lists here if needed for merging later

        try:
            with open(self.settings_file_path, 'r') as f:
                settings = json.load(f)

            # Load all settings using get() to provide defaults
            for key, value in settings.items():
                if hasattr(self, key):
                    # Skip loading presets here, handle them specifically after this loop
                    if key.endswith('_presets') and isinstance(value, list):
                        continue # Handle presets separately below
                    else:
                        setattr(self, key, value)

            # --- Merge Presets ---
            # Load analysis presets from file, ensuring image fields
            loaded_analysis_presets = self._ensure_image_fields(settings.get('analysis_presets', []))
            # Get names of loaded presets
            loaded_analysis_names = {p['name'] for p in loaded_analysis_presets}
            # Add default presets if they are missing in the loaded list
            for default_preset in default_analysis_presets:
                if default_preset['name'] not in loaded_analysis_names:
                    loaded_analysis_presets.append(default_preset)
            self.analysis_presets = loaded_analysis_presets

            # --- Load other preset types (ensure they exist in settings before loading) ---
            preset_keys = ['function_presets', 'chunk_text_presets', 'format_presets', 'metadata_presets', 'sequential_metadata_presets']
            for key in preset_keys:
                if key in settings and isinstance(settings[key], list):
                    setattr(self, key, self._ensure_image_fields(settings[key]))
                # Optional: Add merging logic for other presets here if needed in the future,
                # similar to how analysis_presets was handled above.

            # --- Load remaining specific settings ---
            # Ensure format_presets is loaded if present in file but not in self (already handled above)
            # Ensure sequential_batch_size is loaded if present
            if 'sequential_batch_size' in settings:
                self.sequential_batch_size = settings['sequential_batch_size']
            # Ensure translation and query fields are loaded even if missing from self
            for field in [
                'translation_system_prompt', 'translation_user_prompt', 'translation_val_text', 'translation_model',
                'query_system_prompt', 'query_val_text', 'query_model']:
                if field in settings:
                    setattr(self, field, settings[field])

            # Load backward-compatible metadata settings if presets aren't the primary source
            if 'metadata_preset' in settings: # Check if the old structure might be dominant
                 self.metadata_preset = settings.get('metadata_preset', "Standard Metadata")
                 self.metadata_model = settings.get('metadata_model', self.metadata_presets[0]['model'])
                 self.metadata_temp = settings.get('metadata_temp', self.metadata_presets[0]['temperature'])
                 self.metadata_system_prompt = settings.get('metadata_system_prompt', self.metadata_presets[0]['general_instructions'])
                 self.metadata_user_prompt = settings.get('metadata_user_prompt', self.metadata_presets[0]['specific_instructions'])
                 self.metadata_val_text = settings.get('metadata_val_text', self.metadata_presets[0]['val_text'])
                 self.metadata_headers = settings.get('metadata_headers', self.metadata_presets[0]['metadata_headers'])

        except FileNotFoundError:
            self.restore_defaults()
        except json.JSONDecodeError:
            print(f"Error decoding settings file: {self.settings_file_path}. Restoring defaults.")
            self.restore_defaults()
        except Exception as e:
            print(f"Unexpected error loading settings: {e}. Restoring defaults.")
            self.restore_defaults() # Restore defaults on any unexpected error during loading

    def _ensure_image_fields(self, presets):
        # Helper to ensure num_prev_images and num_after_images are present in all presets
        for preset in presets:
            if 'num_prev_images' not in preset:
                preset['num_prev_images'] = "0"
            if 'num_after_images' not in preset:
                preset['num_after_images'] = "0"
        return presets

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