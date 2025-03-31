import asyncio, base64, os
from pathlib import Path
from PIL import Image

# OpenAI API
from openai import OpenAI
import openai

# Anthropic API
from anthropic import AsyncAnthropic
import anthropic

# Google API
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
# Add new imports for updated Gemini approach
from google import genai as genai_client
from google.genai import types

class APIHandler:
    def __init__(self, openai_api_key, anthropic_api_key, google_api_key, app=None):
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
        self.google_api_key = google_api_key
        self.app = app  # Reference to main app for error logging
        
    def log_error(self, error_message, additional_info=None):
        """Log errors using the app's error_logging if available, otherwise silently continue"""
        if self.app and hasattr(self.app, 'error_logging'):
            self.app.error_logging(error_message, additional_info)

    async def route_api_call(self, engine, system_prompt, user_prompt, temp, 
                            image_data=None, text_to_process=None, val_text=None, 
                            index=None, is_base64=True, formatting_function=False, 
                            api_timeout=80, job_type=None, job_params=None):
        """
        Routes the API call to the appropriate service based on the engine name.
        image_data can be either:
        - None
        - A single image (base64 string or path)
        - A list of tuples [(image_data, label), ...]
        """
        # Extract required_headers for metadata validation if applicable
        required_headers = None
        if job_type == "Metadata" and job_params and "required_headers" in job_params:
            required_headers = job_params["required_headers"]
        
        if "gpt" in engine.lower() or "o1" in engine.lower() or "o3" in engine.lower():
            return await self.handle_gpt_call(system_prompt, user_prompt, temp, 
                                            image_data, text_to_process, val_text, 
                                            engine, index, is_base64, formatting_function, 
                                            api_timeout, job_type, required_headers)
        elif "gemini" in engine.lower():
            return await self.handle_gemini_call(system_prompt, user_prompt, temp, 
                                            image_data, text_to_process, val_text, 
                                            engine, index, is_base64, formatting_function, 
                                            api_timeout, job_type, required_headers)
        elif "claude" in engine.lower():
            return await self.handle_claude_call(system_prompt, user_prompt, temp, 
                                            image_data, text_to_process, val_text, 
                                            engine, index, is_base64, formatting_function, 
                                            api_timeout, job_type, required_headers)
        else:
            raise ValueError(f"Unsupported engine: {engine}")
    
    def _prepare_gpt_messages(self, system_prompt, user_prompt, image_data):
        """Handle both single and multiple image cases for GPT"""
        # Check if using o-series model
        is_o_series_model = "o1" in system_prompt.lower() or "o3" in system_prompt.lower()
        
        # Prepare the system/developer message
        initial_message = {
            "role": "developer" if is_o_series_model else "system",
            "content": system_prompt
        }
        
        if not image_data:
            return [
                initial_message,
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
            ]
        
        # Single image case
        if isinstance(image_data, str):
            return [
                initial_message,
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "high"
                            },
                        },
                    ],
                }
            ]
        
        # Multiple images case
        content = [{"type": "text", "text": user_prompt}]
        for image_data, label in image_data:
            if label:
                content.append({"type": "text", "text": label})
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_data}",
                    "detail": "high"
                }
            })
        
        return [
            initial_message,
            {"role": "user", "content": content}
        ]
    
    def _prepare_gemini_content(self, user_prompt, image_data, is_base64=True):
        """Handle both single and multiple image cases for Gemini"""
        content = []
        
        # Add the user prompt first
        if user_prompt:
            content.append(user_prompt)
        
        if not image_data:
            return content
        
        # Single image case
        if isinstance(image_data, (str, Path)):
            image = Image.open(image_data)  # Changed from PIL.Image to Image
            content.append(image)
            return content
        
        # Multiple images case - handle as a sequence
        for image_path, label in image_data:
            if label:
                content.append(label)
            # Load image directly using PIL
            image = Image.open(image_path)  # Changed from PIL.Image to Image
            content.append(image)
        
        return content
    
    async def _prepare_claude_content(self, user_prompt, image_data, is_base64=True):
        """Handle both single and multiple image cases for Claude"""
        content = []
        
        if not image_data:
            if user_prompt.strip():
                content.append({"type": "text", "text": user_prompt.strip()})
            return content
        
        # Handle multiple images case
        if isinstance(image_data, list):
            for img_data, label in image_data:
                if label:
                    content.append({"type": "text", "text": label})
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": img_data
                    }
                })
        
        # Handle single image case
        elif isinstance(image_data, str):
            content.append({"type": "text", "text": "Document Image:"})
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_data
                }
            })
        
        # Add the user prompt at the end if it exists
        if user_prompt.strip():
            content.append({"type": "text", "text": user_prompt.strip()})
        
        return content    

    async def handle_gpt_call(self, system_prompt, user_prompt, temp, image_data, 
                            text_to_process, val_text, engine, index, 
                            is_base64=True, formatting_function=False, api_timeout=25.0,
                            job_type=None, required_headers=None):
        client = OpenAI(api_key=self.openai_api_key, timeout=api_timeout)
        
        populated_user_prompt = (user_prompt if formatting_function 
                            else user_prompt.format(text_to_process=text_to_process))
        max_tokens = 200 if "pagination" in user_prompt.lower() else 1500
        
        # Increase max_tokens for metadata jobs
        if job_type == "Metadata":
            max_tokens = 2000
            
        # Use more retries for metadata jobs which are more complex
        max_retries = 5 if job_type == "Metadata" else 3
        retries = 0
        
        # Check if using o1 or o3 models
        is_o_series_model = "o1" in engine.lower() or "o3" in engine.lower()
        
        while retries < max_retries:
            try:
                messages = self._prepare_gpt_messages(system_prompt, populated_user_prompt, 
                                                    image_data)
                
                # Prepare API call parameters
                api_params = {
                    "model": engine,
                    "messages": messages,
                }
                
                # Add model-specific parameters
                if is_o_series_model:
                    api_params["response_format"] = {"type": "text"}
                    api_params["reasoning_effort"] = "low"
                else:
                    api_params["temperature"] = temp
                    api_params["max_tokens"] = max_tokens
                
                message = client.chat.completions.create(**api_params)
                
                response = message.choices[0].message.content
                validation_result = self._validate_response(response, val_text, index, job_type, required_headers)
                
                # If validation failed and we have retries left, try again with higher temperature
                if validation_result[0] == "Error" and retries < max_retries - 1:
                    # Gradually increase temperature for creativity if we keep getting invalid responses
                    if job_type == "Metadata" and not is_o_series_model:
                        new_temp = min(0.9, float(temp) + (retries * 0.1))
                        api_params["temperature"] = new_temp
                        
                        # For metadata, sometimes increasing max_tokens helps
                        if retries >= 2:
                            new_max_tokens = min(4000, max_tokens + 500)
                            api_params["max_tokens"] = new_max_tokens
                    
                    retries += 1
                    # Add backoff between retries
                    retry_delay = 1 * (1.5 ** retries)  # Exponential backoff
                    await asyncio.sleep(retry_delay)
                    continue
                
                return validation_result

            except (openai.APITimeoutError, openai.APIError) as e:
                self.log_error(f"GPT API Error with {engine} for index {index}", f"{str(e)}")
                retries += 1
                if retries == max_retries:
                    return "Error", index
                # Add backoff between retries
                retry_delay = 1 * (1.5 ** retries)  # Exponential backoff
                await asyncio.sleep(retry_delay)

    async def handle_gemini_call(self, system_prompt, user_prompt, temp, image_data, 
                                text_to_process, val_text, engine, index, 
                                is_base64=True, formatting_function=False, api_timeout=120.0,
                                job_type=None, required_headers=None):
        # Initialize client with API key
        client = genai_client.Client(api_key=self.google_api_key)
        
        populated_user_prompt = (user_prompt if formatting_function 
                            else user_prompt.format(text_to_process=text_to_process))

        # Generate content config
        generate_content_config = types.GenerateContentConfig(
            temperature=temp,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_mime_type="text/plain",
            system_instruction=[
                types.Part.from_text(text=system_prompt),
            ],
        )

        # Use more retries for metadata jobs which are more complex
        max_retries = 5 if job_type == "Metadata" else 3
        retries = 0
        
        while retries < max_retries:
            try:
                # Prepare content object
                parts = []
                
                # Handle image data
                if image_data:
                    if isinstance(image_data, (str, Path)):
                        # Single image case
                        uploaded_file = client.files.upload(file=image_data)
                        parts.append(types.Part.from_uri(
                            file_uri=uploaded_file.uri,
                            mime_type="image/jpeg"
                        ))
                    else:
                        # Multiple images case
                        for img_path, label in image_data:
                            if label:
                                parts.append(types.Part.from_text(text=label))
                            uploaded_file = client.files.upload(file=img_path)
                            parts.append(types.Part.from_uri(
                                file_uri=uploaded_file.uri,
                                mime_type="image/jpeg"
                            ))
                
                # Add the user prompt
                parts.append(types.Part.from_text(text=populated_user_prompt))
                
                # Create content object
                contents = [
                    types.Content(
                        role="user",
                        parts=parts,
                    ),
                ]

                # Stream the response and collect the text
                response_text = ""
                for chunk in client.models.generate_content_stream(
                    model=engine,
                    contents=contents,
                    config=generate_content_config,
                ):
                    if hasattr(chunk, 'text') and chunk.text is not None:
                        response_text += chunk.text
                
                # Validate the response
                validation_result = self._validate_response(response_text, val_text, index, job_type, required_headers)
                
                # If validation failed and we have retries left, try again with higher temperature
                if validation_result[0] == "Error" and retries < max_retries - 1:
                    # Gradually increase temperature for creativity if we keep getting invalid responses
                    if job_type == "Metadata":
                        new_temp = min(0.9, float(temp) + (retries * 0.1))
                        generate_content_config.temperature = new_temp
                    
                    retries += 1
                    # Add backoff between retries
                    retry_delay = 1 * (1.5 ** retries)  # Exponential backoff
                    await asyncio.sleep(retry_delay)
                    continue
                
                return validation_result

            except Exception as e:
                self.log_error(f"Gemini API Error with {engine} for index {index}", f"{str(e)}")
                retries += 1
                if retries == max_retries:
                    return "Error", index
                # Add backoff between retries
                retry_delay = 1 * (1.5 ** retries)  # Exponential backoff
                await asyncio.sleep(retry_delay)

    async def handle_claude_call(self, system_prompt, user_prompt, temp, image_data, 
                                text_to_process, val_text, engine, index, 
                                is_base64=True, formatting_function=False, api_timeout=120.0,
                                job_type=None, required_headers=None):
        async with AsyncAnthropic(api_key=self.anthropic_api_key, 
                                max_retries=0, timeout=api_timeout) as client:
            populated_user_prompt = (user_prompt if formatting_function 
                                else user_prompt.format(text_to_process=text_to_process))

            # Set max_tokens based on job type or prompt contents
            if "Pagination:" in user_prompt.lower():
                max_tokens = 200
            elif "extract information" in user_prompt.lower():
                max_tokens = 1500
            elif "Split Before:" in user_prompt:
                max_tokens = 200
            elif job_type == "Metadata":
                max_tokens = 2000
            else:
                max_tokens = 1200

            try:
                # Ensure image_data is properly formatted base64 string
                if isinstance(image_data, list):
                    content = []
                    for img, label in image_data:
                        if label:
                            content.append({"type": "text", "text": label})
                        # Ensure img is a valid base64 string
                        if isinstance(img, bytes):
                            img = base64.b64encode(img).decode('utf-8')
                        elif not isinstance(img, str):
                            raise ValueError(f"Invalid image data type: {type(img)}")
                        
                        content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": img
                            }
                        })
                elif isinstance(image_data, str):
                    content = [
                        {"type": "text", "text": "Document Image:"},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data
                            }
                        }
                    ]
                else:
                    content = []

                # Add the user prompt at the end
                if populated_user_prompt.strip():
                    content.append({"type": "text", "text": populated_user_prompt.strip()})

                # Use more retries for metadata jobs which are more complex
                max_retries = 5 if job_type == "Metadata" else 3
                retries = 0
                
                while retries < max_retries:
                    try:
                        message = await client.messages.create(
                            max_tokens=max_tokens,
                            messages=[{"role": "user", "content": content}],
                            system=system_prompt,
                            model=engine,
                            temperature=temp,
                            timeout=api_timeout
                        )
                        
                        response = message.content[0].text
                        validation_result = self._validate_response(response, val_text, index, job_type, required_headers)
                        
                        # If validation failed and we have retries left, try again with higher temperature
                        if validation_result[0] == "Error" and retries < max_retries - 1:
                            # Gradually increase temperature for creativity if we keep getting invalid responses
                            if job_type == "Metadata":
                                new_temp = min(0.9, float(temp) + (retries * 0.1))
                                temp = new_temp
                                
                                # For metadata, sometimes increasing max_tokens helps
                                if retries >= 2:
                                    max_tokens = min(4000, max_tokens + 500)
                            
                            retries += 1
                            # Add backoff between retries
                            retry_delay = 1 * (1.5 ** retries)  # Exponential backoff
                            await asyncio.sleep(retry_delay)
                            continue
                        
                        return validation_result

                    except (anthropic.APITimeoutError, anthropic.APIError) as e:
                        self.log_error(f"Claude API Error with {engine} for index {index}", f"{str(e)}")
                        retries += 1
                        if retries == max_retries:
                            return "Error", index
                        # Add backoff between retries
                        retry_delay = 1 * (1.5 ** retries)  # Exponential backoff
                        await asyncio.sleep(retry_delay)
                        
            except Exception as e:
                self.log_error(f"Error preparing Claude content for index {index}", f"{str(e)}")
                return "Error", index
                
    def _validate_response(self, response, val_text, index, job_type=None, required_headers=None):
        """
        Validates and processes the API response.
        
        Args:
            response: The response text from the API
            val_text: The validation text to look for (can be None or "None")
            index: The index of the current document
            job_type: The type of job being processed (e.g., "Metadata")
            required_headers: List of required headers for metadata validation
            
        Returns:
            Tuple of (processed_response, index)
        """
        # First check if we have a valid response
        if not response:
            self.log_error(f"Empty API response for index {index}", f"job_type: {job_type}")
            return "Error", index
            
        # If no validation text is needed, return the full response
        if not val_text or val_text == "None":
            return response, index
            
        # Check if validation text exists in response
        try:
            if val_text in response:
                # For all job types, extract everything after the validation text
                processed_response = response.split(val_text, 1)[1].strip()
                
                # Special validation for Metadata responses
                if job_type == "Metadata" and required_headers:
                    # Check if all required headers are present in the response
                    missing_headers = []
                    has_content = False
                    header_contents = {}
                    
                    for header in required_headers:
                        header_pattern = f"{header}:"
                        if header_pattern not in processed_response:
                            missing_headers.append(header)
                            continue
                            
                        # Check if header has actual content
                        try:
                            # Split the text by the header and get the content after it
                            split_parts = processed_response.split(header_pattern, 1)
                            if len(split_parts) > 1:
                                # Find the content until the next header or end of text
                                header_content = split_parts[1].strip()
                                
                                # If there's another header, only take text until that header
                                next_header_pos = float('inf')
                                for next_header in required_headers:
                                    next_pattern = f"\n{next_header}:"
                                    pos = header_content.find(next_pattern)
                                    if pos != -1 and pos < next_header_pos:
                                        next_header_pos = pos
                                
                                if next_header_pos != float('inf'):
                                    header_content = header_content[:next_header_pos].strip()
                                
                                # Log the content found for this header
                                header_contents[header] = header_content
                                
                                # Check if there's meaningful content
                                if header_content and not header_content.isspace():
                                    has_content = True
                        except Exception as e:
                            self.log_error(f"Error checking content for header {header}", f"{str(e)}")
                    
                    # Request error (retry) if headers are missing or all headers are empty
                    if missing_headers:
                        self.log_error(f"Missing required headers in metadata response", f"Missing: {missing_headers}, index: {index}")
                        return "Error", index
                    
                    if not has_content:
                        self.log_error(f"All metadata headers are empty", f"index: {index}, job_type: {job_type}")
                        return "Error", index
                
                return processed_response, index
            else:
                self.log_error(f"Validation text not found in response", f"val_text: {val_text}, index: {index}")
        except TypeError:
            # Handle case where response or val_text is not a string
            self.log_error(f"Validation error - Response type mismatch", f"Response: {type(response)}, Val_text: {type(val_text)}")
            return "Error", index
            
        # If validation text not found, return error
        return "Error", index

    def prepare_image_data(self, image_data, engine, is_base64=True):
        """
        Prepare image data based on the engine and format requirements.
        
        Args:
            image_data: Can be a single image path or a list of tuples [(path, label), ...]
            engine: The AI engine being used
            is_base64: Whether to encode the images to base64
        
        Returns:
            Processed image data in the appropriate format for the specified engine
        """
        if not image_data:
            return None

        # For Gemini, just return the file paths, no need for base64 encoding
        # as we'll upload them directly using client.files.upload
        if "gemini" in engine.lower():
            return image_data

        needs_base64 = is_base64 and ("gpt" in engine.lower() or "o1" in engine.lower() or "o3" in engine.lower() or "claude" in engine.lower())
        
        # Handle single image case
        if isinstance(image_data, str):
            return self.encode_image(image_data) if needs_base64 else image_data

        # Handle multiple images case
        processed_data = []
        for img_path, label in image_data:
            if needs_base64:
                encoded_image = self.encode_image(img_path)
                if encoded_image:
                    processed_data.append((encoded_image, label))
            else:
                processed_data.append((img_path, label))

        return processed_data

    def encode_image(self, image_path):
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            self.log_error(f"Error encoding image", f"Path: {image_path}, Error: {str(e)}")
            return None

    def _format_content_for_print(self, content):
        formatted_content = []
        for item in content:
            if item['type'] == 'text':
                formatted_content.append(item['text'])
            elif item['type'] == 'image_url':
                formatted_content.append("{IMAGE}")
        return formatted_content
    
    def _format_gemini_content_for_print(self, content):
        return [item if isinstance(item, str) else "{IMAGE}" for item in content]
    
    def _format_claude_content_for_print(self, content):
        formatted_content = []
        for item in content:
            if item['type'] == 'text':
                formatted_content.append(item['text'])
            elif item['type'] == 'image':
                formatted_content.append("{IMAGE}")
        return formatted_content