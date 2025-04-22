# utils.py
import os
import tempfile
import PyPDF2 # Keep import in case needed for fallback or type hinting
import docx # python-docx library
import traceback # For more detailed error reporting
import re # For parsing time instructions
from genai import GenAI # Assuming genai.py is in the same directory

# Initialize the GenAI class (assuming it handles API key loading)
# Handle potential errors during GenAI initialization
jarvis = None # Initialize jarvis to None
print("--- utils.py: Attempting to initialize GenAI instance... ---") # DEBUG PRINT
try:
    # Create an instance of the GenAI class
    jarvis = GenAI()
    print("--- utils.py: GenAI instance (jarvis) created successfully. ---") # DEBUG PRINT
except ValueError as e:
    # This error likely means the API key is missing.
    print(f"--- utils.py: CRITICAL ERROR during GenAI initialization: {e} ---") # DEBUG PRINT
    print("--- utils.py: Ensure OPENAI_API_KEY is set in your environment or .env file. ---")
    # jarvis remains None
except ConnectionError as e:
    # This error means the client failed to initialize (e.g., network issue, bad key format)
    print(f"--- utils.py: CRITICAL CONNECTION ERROR during GenAI initialization: {e} ---") # DEBUG PRINT
    # jarvis remains None
except Exception as e:
    # Catch any other unexpected errors during initialization
    print(f"--- utils.py: An unexpected error occurred during GenAI initialization: {e} ---") # DEBUG PRINT
    traceback.print_exc()
    # jarvis remains None

# Check if initialization failed and print a clear status
if jarvis is None:
     print("--- utils.py: WARNING - GenAI instance (jarvis) is None. AI functionality will fail. ---") # DEBUG PRINT


def _estimate_word_count(minutes, words_per_minute=150):
    """Estimates target word count based on duration."""
    if minutes is None or minutes <= 0:
        return None # No specific target
    return int(minutes * words_per_minute)

def _parse_duration_from_instructions(instructions):
    """Attempts to parse a duration (in minutes) from user instructions."""
    if not instructions:
        return None
    # Look for patterns like "X minute", "X min", "X-minute"
    match = re.search(r'(\d+)\s*-?\s*min(ute)?s?', instructions, re.IGNORECASE)
    if match:
        try:
            minutes = int(match.group(1))
            print(f"--- utils.py: Parsed duration request: {minutes} minutes ---")
            return minutes
        except (ValueError, IndexError):
            return None
    return None


def read_uploaded_files(uploaded_file_list):
    """
    Reads a list of Streamlit UploadedFile objects, extracts text content
    from supported file types (.txt, .pdf, .docx).

    Args:
        uploaded_file_list: A list of Streamlit UploadedFile objects.

    Returns:
        A single string containing the concatenated text from all readable files,
        or None if no files were provided or readable.
    """
    all_text = []
    if not uploaded_file_list:
        print("--- utils.py: No files provided to read_uploaded_files. ---")
        return None

    print(f"--- utils.py: Starting processing of {len(uploaded_file_list)} uploaded files. ---")
    # Process each file directly using file-like object methods where possible
    for uploaded_file in uploaded_file_list:
        file_text = None
        file_name = uploaded_file.name
        print(f"--- utils.py: Processing file: {file_name} ---")
        try:
            # Determine file type and read content
            file_extension = os.path.splitext(file_name)[1].lower()

            if file_extension == ".txt":
                # Read as bytes first, then decode with error handling
                print(f"--- utils.py: Reading {file_name} as TXT ---")
                raw_bytes = uploaded_file.getvalue()
                try:
                    file_text = raw_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    print(f"--- utils.py: Warning - UTF-8 decoding failed for {file_name}. Trying 'latin-1'. ---")
                    try:
                       file_text = raw_bytes.decode('latin-1') # Common fallback
                    except Exception as decode_err:
                       print(f"--- utils.py: Error decoding {file_name} with fallback: {decode_err} ---")
                       file_text = "[Could not decode TXT file content]"


            elif file_extension == ".pdf":
                print(f"--- utils.py: Reading {file_name} as PDF ---")
                # Use the read_pdf method from GenAI instance if available
                if jarvis and hasattr(jarvis, 'read_pdf'):
                     # Pass the file-like object directly
                     file_text = jarvis.read_pdf(uploaded_file)
                     if not file_text: # Check if read_pdf returned empty string due to error
                          print(f"--- utils.py: Warning - Failed to extract text from PDF: {file_name} ---")
                          file_text = f"[No text extracted from PDF: {file_name}]" # Add placeholder
                else:
                     print(f"--- utils.py: Warning - Cannot read PDF '{file_name}' - GenAI instance or read_pdf method unavailable. ---")
                     file_text = f"[PDF reading unavailable for: {file_name}]"


            elif file_extension == ".docx":
                print(f"--- utils.py: Reading {file_name} as DOCX ---")
                 # Use the read_docx method from GenAI instance if available
                if jarvis and hasattr(jarvis, 'read_docx'):
                     # Pass the file-like object directly
                     file_text = jarvis.read_docx(uploaded_file)
                     if not file_text: # Check if read_docx returned empty string due to error
                          print(f"--- utils.py: Warning - Failed to extract text from DOCX: {file_name} ---")
                          file_text = f"[No text extracted from DOCX: {file_name}]" # Add placeholder
                else:
                    print(f"--- utils.py: Warning - Cannot read DOCX '{file_name}' - GenAI instance or read_docx method unavailable. ---")
                    file_text = f"[DOCX reading unavailable for: {file_name}]"

            else:
                print(f"--- utils.py: Warning - Unsupported file type skipped: {file_name} ---")
                file_text = f"[Unsupported file type: {file_name}]"

            # Add extracted text (or error placeholder) to the list
            # Only add if text was actually extracted, ignore placeholders unless debugging
            if file_text and not file_text.startswith("["):
                all_text.append(f"--- Content from {file_name} ---\n{file_text}\n--- End of {file_name} ---\n\n")
            elif file_text: # Include placeholders if needed for debugging counts etc.
                 print(f"--- utils.py: Placeholder added for {file_name}: {file_text} ---")
                 # all_text.append(file_text + "\n\n") # Uncomment to include placeholders in output

        except Exception as e:
            print(f"--- utils.py: Error processing file {file_name}: {e} ---")
            traceback.print_exc() # Print detailed traceback for debugging
            # Add a marker indicating which file failed
            all_text.append(f"[Error processing file: {file_name}]\n\n")

    # Combine all extracted texts
    print(f"--- utils.py: Finished processing {len(uploaded_file_list)} files. ---")
    combined_text = "".join(all_text)
    # Return None if the combined text is empty or only contains error messages/placeholders
    return combined_text if combined_text and not combined_text.strip().startswith("[") else None


def generate_podcast_script(text_data, instructions):
    """
    Generates a podcast script using the GenAI class based on provided text
    data and user instructions, attempting to adhere to length requests.

    Args:
        text_data (str): Concatenated text content from newsletters.
        instructions (str): User-provided instructions for style, tone, focus, length.

    Returns:
        A string containing the generated podcast script, or None if an error occurs.
    Raises:
        ConnectionError: If the GenAI instance is not available (e.g., API key issue).
        Exception: Propagates exceptions from the AI generation call.
    """
    print("--- utils.py: Entering generate_podcast_script function. ---") # DEBUG PRINT
    if not jarvis:
        print("--- utils.py: ERROR - GenAI (jarvis) not initialized in generate_podcast_script. ---")
        raise ConnectionError("AI service connection not established. Check API key and initialization.")

    if not text_data:
        print("--- utils.py: ERROR - No text data provided to generate_podcast_script. ---")
        return None # Return None if input text is empty

    # --- Length Control Logic ---
    target_minutes = _parse_duration_from_instructions(instructions)
    target_word_count = _estimate_word_count(target_minutes)
    length_instruction = ""
    if target_word_count:
        # Be very specific about the word count target
        length_instruction = (
            f"\nIMPORTANT LENGTH CONSTRAINT: The final script MUST be approximately {target_word_count} words long "
            f"(which corresponds to roughly {target_minutes} minutes of speaking time at a normal pace). "
            "Adhere closely to this word count."
        )
        print(f"--- utils.py: Adding length instruction: target ~{target_word_count} words. ---")
    else:
        # Provide a default guideline if no specific time was requested
        length_instruction = "\nLENGTH GUIDELINE: Aim for a concise script, typically between 500-1000 words, unless user instructions specify otherwise."
        print("--- utils.py: No specific duration found, using default length guideline. ---")
    # --- End Length Control Logic ---


    # Construct a more detailed prompt for the AI
    system_prompt = f"""
You are an expert podcast scriptwriter creating a personalized audio digest called 'Inbox.fm'.
Your target audience is busy, intellectually curious millennial knowledge workers (25-40) in fields like finance, VC, and tech. They use newsletters (like Axios Pro, The Information, a16z, Stratechery) to stay competitive.
Your task is to synthesize the key insights from the provided newsletter content into a coherent, engaging podcast script.

Follow these user instructions carefully:
'{instructions}'
{length_instruction}

Additional guidelines:
- Focus on summarizing key content and drawing meaningful connections across the provided sources.
- Aim for depth and retention, not just surface-level skimming.
- The tone should be professional yet conversational and engaging for audio.
- Structure the output clearly as a script. Start with a brief intro, synthesize the main points, and end with a brief outro. Use clear paragraph breaks.
- Do NOT just list summaries; synthesize the information into a narrative.
- Ensure the final script flows well and makes sense when read aloud.
- Avoid overly technical jargon unless the user instructions specify otherwise.
- Do not include any markdown formatting like ```, **, or lists using '*' or '-' in the final script. Output plain text suitable for text-to-speech.
"""

    # The user prompt will be the combined text data
    user_prompt = text_data
    print("--- utils.py: Attempting to generate podcast script via jarvis.generate_text... ---")

    try:
        # Call the text generation method from the GenAI instance
        script = jarvis.generate_text(
            prompt=user_prompt,
            instructions=system_prompt,
            model="gpt-4o-mini", # Consider gpt-4o for potentially better synthesis/length control
            temperature=0.6,    # Slightly lower temperature for more focused synthesis
            max_tokens=3000     # Increase max tokens slightly to allow for longer content if needed
        )
        if script:
             print("--- utils.py: Podcast script generated successfully by jarvis. ---")
             # Optional: Log word count of generated script for comparison
             # print(f"--- utils.py: Generated script word count: {len(script.split())} ---")
        else:
             print("--- utils.py: Warning - AI script generation returned None from jarvis. ---")
        return script # Returns the script string or None if GenAI.generate_text failed
    except Exception as e:
        print(f"--- utils.py: Error in generate_podcast_script calling jarvis.generate_text: {e} ---")
        traceback.print_exc()
        raise e # Re-raise the exception so app.py can catch it


def generate_podcast_audio(script, output_path, voice_name):
    """
    Generates an audio file from the podcast script using the GenAI class.
    (This function remains largely the same but will be called by the new combined function)

    Args:
        script (str): The generated podcast script text.
        output_path (str): The file path to save the generated MP3 audio.
        voice_name (str): The desired AI voice name (e.g., 'nova').

    Returns:
        bool: True if audio generation was successful, False otherwise.
    Raises:
        ConnectionError: If the GenAI instance is not available.
        Exception: Propagates exceptions from the audio generation call.
    """
    print("--- utils.py: Entering generate_podcast_audio function. ---") # DEBUG PRINT
    if not jarvis:
        print("--- utils.py: ERROR - GenAI (jarvis) not initialized in generate_podcast_audio. ---")
        raise ConnectionError("AI service connection not established. Check API key and initialization.")

    if not script:
        print("--- utils.py: ERROR - No script provided to generate_podcast_audio. ---")
        return False # Cannot generate audio from empty script

    print(f"--- utils.py: Attempting to generate podcast audio via jarvis.generate_audio using voice '{voice_name}'... ---")
    try:
        # Call the audio generation method from the GenAI instance
        success = jarvis.generate_audio(
            text=script,
            file_path=output_path,
            voice=voice_name,
            model='tts-1', # Standard quality TTS model - 'tts-1-hd' is higher quality but slower/more expensive
            speed=1.0      # Default speed, could be made configurable in app.py later
        )
        if success:
            print("--- utils.py: Podcast audio generated successfully by jarvis. ---")
        else:
            print("--- utils.py: Error - AI audio generation failed (jarvis.generate_audio returned False). ---")
        return success # Returns True or False based on jarvis.generate_audio result
    except Exception as e:
        print(f"--- utils.py: Error in generate_podcast_audio calling jarvis.generate_audio: {e} ---")
        traceback.print_exc()
        # Decide whether to return False or re-raise
        raise e # Re-raise if app.py should handle it explicitly
        # return False # Indicate failure

def generate_script_and_audio(text_data, instructions, output_audio_path, voice_name):
    """
    Generates both the podcast script and the audio file in sequence.

    Args:
        text_data (str): Concatenated text content from newsletters.
        instructions (str): User-provided instructions.
        output_audio_path (str): The full path to save the generated MP3 audio.
        voice_name (str): The desired AI voice name.

    Returns:
        tuple: (generated_script, audio_file_path)
               - generated_script (str): The text of the script, or None if script generation failed.
               - audio_file_path (str): The path to the saved audio file if successful, or None otherwise.
               Returns (None, None) if script generation fails.
    Raises:
        ConnectionError: If the GenAI instance is not available.
        Exception: Propagates exceptions from the underlying generation calls.
    """
    print(f"--- utils.py: Starting combined script and audio generation for voice '{voice_name}' ---")
    generated_script = None
    audio_file_path = None

    # Step 1: Generate Script
    try:
        generated_script = generate_podcast_script(text_data, instructions)
    except Exception as script_err:
        print(f"--- utils.py: Error during script generation step: {script_err} ---")
        # Re-raise the exception to be caught by app.py
        raise script_err

    # Step 2: Generate Audio ONLY if script generation was successful
    if generated_script:
        try:
            audio_success = generate_podcast_audio(generated_script, output_audio_path, voice_name)
            if audio_success and os.path.exists(output_audio_path):
                audio_file_path = output_audio_path
                print(f"--- utils.py: Combined generation successful. Audio at: {audio_file_path} ---")
            else:
                print("--- utils.py: Audio generation step failed or file not found. ---")
                # Keep generated_script, but audio_file_path remains None
        except Exception as audio_err:
            print(f"--- utils.py: Error during audio generation step: {audio_err} ---")
            # Keep generated_script, but audio_file_path remains None
            # Optionally re-raise or handle differently
            # raise audio_err # Uncomment to propagate audio-specific errors strongly
            pass # Allow returning the script even if audio fails

    else:
        print("--- utils.py: Script generation failed, skipping audio generation. ---")

    return generated_script, audio_file_path

