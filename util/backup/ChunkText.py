
import re, asyncio

class ChunkText:
    def __init__(self, api_handler=None):
        self.api_handler = api_handler
        
    async def process_api_request(self, engine, system_prompt, user_prompt, temp, 
                                image_data, text_to_process, val_text, index, 
                                is_base64=True, formatting_function=False):
        """Process API requests using the API handler"""
        try:
            if self.api_handler is None:
                raise ValueError("API handler not initialized")
                
            # Format the user prompt if there's text to process
            formatted_user_prompt = user_prompt
            if text_to_process and not formatting_function:
                formatted_user_prompt = user_prompt.format(text_to_process=text_to_process)

            return await self.api_handler.route_api_call(
                engine=engine,
                system_prompt=system_prompt,
                user_prompt=formatted_user_prompt,
                temp=temp,
                image_data=image_data,
                text_to_process=text_to_process,
                val_text=val_text,
                index=index,
                is_base64=is_base64,
                formatting_function=formatting_function
            )
            
        except Exception as e:
            print(f"API Error in ChunkText: {e}")
            return "Error", index
                
    def split_text(self, text, max_words=800, strategy="basic"):

        if strategy == "basic":
            return self.basic_chunking(text, max_words)
        
        elif strategy == "detect_segment":
            return self.detect_segment_chunking(text, max_words)

    def basic_chunking(self, text, max_words):
            # Split text into lines
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            line_word_count = len(line.split())
            
            # If adding this line would exceed the limit, try to find a break point
            if current_word_count + line_word_count > max_words and current_chunk:
                # Look back through current chunk for a break point
                break_found = False
                
                # Convert current chunk back to text for analysis
                chunk_text = '\n'.join(current_chunk)
                
                # Try each splitting rule in order
                split_patterns = [
                    # Period + blank line + capital letter
                    r'(\.\n\n[A-Z])',
                    # Letter/digit + blank line + capital letter
                    r'([a-zA-Z0-9]\n\n[A-Z])',
                    # Just a blank line
                    r'(\n\n)'
                ]
                
                for pattern in split_patterns:
                    if break_found:
                        break
                        
                    matches = list(re.finditer(pattern, chunk_text))
                    if matches:
                        # Use the last match as the break point
                        last_match = matches[-1]
                        split_point = last_match.start() + 1  # +1 to keep the period
                        
                        # Split the chunk
                        chunks.append(chunk_text[:split_point].strip())
                        
                        # Start new chunk with remaining text
                        remaining_text = chunk_text[split_point:].strip()
                        current_chunk = remaining_text.split('\n') if remaining_text else []
                        current_word_count = sum(len(line.split()) for line in current_chunk)
                        break_found = True
                
                # If no break point found, just split at max_words
                if not break_found:
                    chunks.append(chunk_text)
                    current_chunk = []
                    current_word_count = 0
            
            # Add current line to chunk
            current_chunk.append(line)
            current_word_count += line_word_count
            i += 1
        
        # Add final chunk if it exists
        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def detect_segment_chunking(self, text, max_words):
        # 1. First get basic chunks
        basic_chunks = self.basic_chunking(text, max_words)
        
        # 2. Process each chunk with LLM to find natural break points
        system_prompt = """You are a text analysis expert. Your task is to identify natural break points in text segments 
        where the text transitions between different documents, diary entries, letters, or similar distinct sections.
        Respond only with lines starting with 'Split Before:' followed by the text that should start each new section. 
        If no natural breaks exist, respond with 'Nothing to Split'."""
        
        user_prompt = """Analyze this text segment and identify any natural break points where the text transitions 
        between different documents, diary entries, or sections. These might be starts of new letters, diary entries, 
        or distinct document sections. For each break point, in your response write "Split Before:" followed by enough unique text so that a python script will be able to identify the start of the new section using a regex function. For example:
        
        Split Before: Montreal 22 June 1789
        Split Before: Albany 23 June 1789"""
        
        processed_chunks = []
        
        # Process each chunk asynchronously
        for i, chunk in enumerate(basic_chunks):
            response = asyncio.run(self.process_api_request(
                engine="claude-3-5-sonnet-20241022",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temp=0.2,
                image_data=None,
                text_to_process=chunk,
                val_text="Split Before:",
                index=i,
                is_base64=False,
                formatting_function=False
            ))
            
            if isinstance(response, tuple):
                response = response[0]  # Extract response from (response, index) tuple
            
            # Process the response
            if response and "Nothing to Split" not in response:
                modified_chunk = chunk
                # Find all "Split Before:" lines
                split_points = [line.replace("Split Before:", "").strip() 
                            for line in response.split('\n') 
                            if line.startswith("Split Before:")]
                
                # Insert markers before each split point
                for split_text in split_points:
                    if split_text in modified_chunk:
                        modified_chunk = modified_chunk.replace(
                            split_text, 
                            f"\n*****\n{split_text}"
                        )
                processed_chunks.append(modified_chunk)
            else:
                # If no splits needed, keep chunk as is
                processed_chunks.append(chunk)
        
        # 4. Concatenate all processed chunks
        bulk_doc = "\n".join(processed_chunks)
        
        # 5. Split on ***** markers
        final_chunks = [chunk.strip() for chunk in bulk_doc.split("*****") if chunk.strip()]
        
        return final_chunks

