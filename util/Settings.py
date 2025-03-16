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
                "general_instructions": "For diary entries, chunk text by identifying dated entries. Insert '*****' before each new entry.",
                "specific_instructions": "Document Text: {text_to_process}",
                "val_text": "Final Chunk:",
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
                'model': "gemini-1.5-pro-002",
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
                'model': "claude-3-5-sonnet-20240620",
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
                'model': "claude-3-5-sonnet-20240620",
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
                'name': "Single_Page_Pagination",
                'model': "gpt-4o",
                'temperature': "0.7",
                'general_instructions': '''You read a series of pages from an archival document sent by a user in order to group pages together. You will receive two pages: the previous page and the current page.

Your task is to answer Yes or No to each of the following questions:

1. Does the last sentence that begins on the previous page, carry over to the current page? <Yes/No>

2. Is the first text on the current page in any way a continuation of a diary entry, letter, parish record, or other discreet document that began on the previous page? This might include the complementary close, signatures, addresses, or other text that "belongs" with the text at the end of the previous page?

3. Does the initial text on the current page begin a completely new sentence or standalone document—one that does not continue, wrap up, or otherwise connect directly to any sentence or document that ended on the previous page?

If you answered No to BOTH questions 1 and 2 and YES to quesiton 3, end your response by writing "Pagination: New", otherwise end it with "Pagination: Continues".''',
                'specific_instructions': "Document Text: {text_to_process}",
                'use_images': True,
                'current_image': "Yes",
                'num_prev_images': "1",
                'num_after_images': "0",
                'val_text': "Pagination:"
            },
            {
                'name': "Multiple_Page_Pagination",
                'model': "gpt-4o",
                'temperature': "0.7",
                'general_instructions': '''You read a series of archival documents sent by a user. You will receive the active page (which is what you need to focus on) and for context the previous pages and the next page. Your task is to determine whether the active page continues the same document from the previous page or whether it starts a new document. Pay close attention to the handwriting, paper, and words at the end of the previous page, the start and end of the active page, and at the start of the next page. Look for clues like salutations, dates, headers, addresses, footers, etc. In your response, write "Pagination:" followed only by your answer, choosing one of: "Continues Previous Document", "Continues from Unknown Document" or "Start of New Document".''',
                'specific_instructions': "Document Text: {text_to_process}",
                'use_images': True,
                'current_image': "Yes",
                'num_prev_images': "2",
                'num_after_images': "1",
                'val_text': "Pagination:"
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
                'name': "Chunk_Text",
                'model': "claude-3-5-sonnet-20241022",
                'temperature': "0.7",
                'general_instructions': '''You are an expert in historical document analysis, specialized in identifying boundaries between distinct entries in a parish register of baptisms marriages, and burials. When presented with transcribed text and its corresponding page image, your task is to re-transcribe the text exactly as written, although any marginalia, spacing, etc should be standardized and formatted as follows:

Title of entry
Content
Signatures etc

Preceed each new entry that begins on the current page with "*****" written on a new line. Skip this step when the first lines on a page began on the previous page.

In your response, write any notes you need to that will help you. Then write "Final Response: " followed by your re-formatted transcription and nothing else.''',
                'specific_instructions': '''{text_to_process}''',
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "None"
            }
        ]

        self.analysis_presets = [
            {
                'name': "Relevance",
                'model': "gpt-4o",
                'temperature': "0.3",
                'general_instructions' : '''You provide expert historical analysis. You examine a historical document and evaluate whether it meets the relevance criteria specified by a user. That criteria might include subjective factors such as whether the given document might be relevant to a particular research question or theme, or objective factors such as whether the document fits specific temporal or geographic requirements. Read the user's instructions, then the document provided, and determine whether the document fits the user's relevance criteria or not. Provide a confidence level for your judgement where 100% means absolute certainty. \n\nYou must end your response by writing: "Relevance:" followed by "Relevant", "Irrelevant", or "Uncertain". Then write "Confidence Level:" followed by your level of confidence in this judgement out of 100%.''',
                'specific_instructions': '''The user's query and specific criteria are as follows: {query_text}. \n\n Here is the text to analyze:\n\n{text_to_process}''',
                'use_images': False,
                'current_image': "No",
                'num_prev_images': "0",
                'num_after_images': "0",
                'val_text': "Relevance:",
                'dataframe_field': "Relevance"
            },          
        ] # List of dictionaries for analysis presets
        
        self.translation_system_prompt = '''You will be given a transcription of a historical text along with the original page images to translate into English. 
            Retain all the original line breaks (as closely as possible). In your response write the word "Translation:" in English 
            followed only by your accurate translation of the text.'''
        self.translation_user_prompt = '''Text to translate into English:\n\n{text_to_process}\n\nOriginal Page Images:'''
        self.translation_val_text = "Translation:"
        self.translation_model = "gpt-4o"
       
        self.query_system_prompt = "You are an expert historian hired to perform work for another historian. You closely follow the user's instructions and are always truthful. When you don't know something or have insufficient information, explicitly tell the user 'I don't know' or 'I require more information to...'. "
        self.query_val_text = None
        self.query_model = "gpt-4o"

        self.metadata_system_prompt = '''You analyze historical documments to extract information. Read the document and then make any notes you require. Then, in your response, write "Metadata:" and then on new lines output the following headings, filling in the information beside each one:

Document Type: <Letter/Baptismal Record/Diary Entry/Will/etc.>
Author: <Last Name, First Name> - Note: for letters, memos, etc. use the name of the author of document. For other documents where the primary purposes if official or semi-official documentation of an individual(s), like a parish Birth, Marriage or Death Record, prison record, military service file, etc, use the name of the person(s) who the record is about.
Correspondent: <Last Name, First Name>
Correspondent Place: <Place where the correspondent is located>
Date: <DD/MM/YYYY>
Place of Creation: <Place where the document was created>
People: <Last Name, First Name; Last Name, First Name;...>
Places: <Last Name, First Name; Last Name, First Name;...>
Summary:

For People, list all the names of people mentioned in the document. For Places, list all the places mentioned in the document. For Summary, write a brief summary of the document.

If you don't have information for a heading or don't know, leave it blank.'''
        self.metadata_user_prompt = '''Text to analyze:\n\n{text_to_process}'''
        self.metadata_val_text = "Metadata:"
        self.metadata_model = "gemini-2.0-flash"

        self.batch_size = 50
        self.check_orientation = False
        
        self.model_list = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.5-preview"
            "o1",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-5-sonnet-20250219",
            "claude-3-opus-20240229",
            "gemini-2.0-pro-exp-02-05",
            "gemini-2.0-flash",
            "gemini-2.0-flash-thinking-exp-01-21"

        ]

        self.openai_api_key = ""
        self.anthropic_api_key = ""
        self.google_api_key = ""

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
            'translation_system_prompt': self.translation_system_prompt,                # Translation = Translating Text
            'translation_user_prompt': self.translation_user_prompt,
            'translation_val_text': self.translation_val_text,
            'translation_model': self.translation_model,
            'query_system_prompt': self.query_system_prompt,                            # Query = Answering Questions
            'query_val_text': self.query_val_text,
            'query_model': self.query_model,
            'metadata_system_prompt': self.metadata_system_prompt,                      # Metadata = Extracting Metadata
            'metadata_user_prompt': self.metadata_user_prompt,
            'metadata_val_text': self.metadata_val_text,
            'metadata_model': self.metadata_model,
            'batch_size': self.batch_size,                                              # Batch size for processing
            'check_orientation': self.check_orientation,                                # Check orientation of text
            'analysis_presets': self.analysis_presets,
            'function_presets': self.function_presets,
            'chunk_text_presets': self.chunk_text_presets

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