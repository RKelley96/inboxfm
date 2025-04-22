# utils.py
import os
import tempfile
import PyPDF2
import docx # python-docx library
import traceback
import re
from genai import GenAI

# Initialize the GenAI class
jarvis = None
try:
    jarvis = GenAI()
except (ValueError, ConnectionError) as e:
    print(f"CRITICAL ERROR during GenAI initialization: {e}")
except Exception as e:
    print(f"An unexpected error occurred during GenAI initialization: {e}")
    traceback.print_exc()

if jarvis is None:
     print("WARNING: GenAI instance (jarvis) is None. AI functionality will be unavailable.")


def _estimate_word_count(minutes, words_per_minute=150):
    """Estimates target word count based on duration."""
    if minutes is None or minutes <= 0:
        return None
    return int(minutes * words_per_minute)

# Removed _parse_duration_from_instructions as duration is now passed directly


def read_uploaded_files(uploaded_file_list):
    """
    Reads a list of Streamlit UploadedFile objects, extracts text content
    from supported file types (.txt, .pdf, .docx).
    """
    all_text = []
    if not uploaded_file_list:
        return None

    for uploaded_file in uploaded_file_list:
        file_text = None
        file_name = uploaded_file.name
        try:
            file_extension = os.path.splitext(file_name)[1].lower()

            if file_extension == ".txt":
                raw_bytes = uploaded_file.getvalue()
                try:
                    file_text = raw_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                       file_text = raw_bytes.decode('latin-1')
                    except Exception as decode_err:
                       print(f"Error decoding TXT file {file_name}: {decode_err}")
                       file_text = f"[Could not decode TXT: {file_name}]"

            elif file_extension == ".pdf":
                if jarvis and hasattr(jarvis, 'read_pdf'):
                     file_text = jarvis.read_pdf(uploaded_file)
                     if not file_text:
                          file_text = f"[No text extracted from PDF: {file_name}]"
                else:
                     file_text = f"[PDF reading unavailable for: {file_name}]"

            elif file_extension == ".docx":
                if jarvis and hasattr(jarvis, 'read_docx'):
                     file_text = jarvis.read_docx(uploaded_file)
                     if not file_text:
                          file_text = f"[No text extracted from DOCX: {file_name}]"
                else:
                    file_text = f"[DOCX reading unavailable for: {file_name}]"
            else:
                file_text = f"[Unsupported file type: {file_name}]"

            # Only append actual content or specific error messages if desired
            if file_text and not file_text.startswith("["):
                 all_text.append(f"--- Content from {file_name} ---\n{file_text}\n--- End of {file_name} ---\n\n")
            elif file_text:
                 print(f"Info/Warning for {file_name}: {file_text}")

        except Exception as e:
            print(f"Error processing file {file_name}: {e}")
            traceback.print_exc()
            all_text.append(f"[Error processing file: {file_name}]\n\n")

    combined_text = "".join(all_text)
    # Return None if the combined text is empty or only contains error markers
    return combined_text if combined_text and not combined_text.strip().startswith("[Error processing") else None


def generate_podcast_script(text_data, instructions, target_duration_minutes=None):
    """
    Generates a podcast script using the GenAI class, prioritizing explicit duration.

    Args:
        text_data (str): Concatenated text content from newsletters.
        instructions (str): User-provided instructions for style, tone, focus.
        target_duration_minutes (int, optional): Explicitly requested duration (e.g., 2, 5, 10). Defaults to None.

    Returns:
        A string containing the generated podcast script, or None if an error occurs.
    Raises:
        ConnectionError: If the GenAI instance is not available.
        Exception: Propagates exceptions from the AI generation call.
    """
    if not jarvis:
        raise ConnectionError("AI service connection not established.")
    if not text_data:
        return None

    # --- Length Control Logic ---
    # Prioritize the passed argument
    target_word_count = _estimate_word_count(target_duration_minutes)
    length_instruction = ""
    if target_word_count:
        length_instruction = (
            f"\nIMPORTANT LENGTH CONSTRAINT: The final script MUST be approximately {target_word_count} words long "
            f"(around {target_duration_minutes} minutes of speaking time). Adhere closely to this word count."
        )
        print(f"--- utils.py: Using explicit duration target: {target_duration_minutes} mins (~{target_word_count} words). ---")
    else:
        # If no duration passed (target_duration_minutes is None), provide a default guideline
        length_instruction = "\nLENGTH GUIDELINE: Aim for a concise script, typically between 500-1000 words, as no specific duration was selected."
        print("--- utils.py: No specific duration selected, using default length guideline. ---")
    # --- End Length Control Logic ---

    # Construct the system prompt
    system_prompt = f"""
You are an expert podcast scriptwriter creating a personalized audio digest called 'Inbox.fm'.
Your target audience is busy, intellectually curious millennial knowledge workers (25-40) in fields like finance, VC, and tech.
Your task is to synthesize the key insights from the provided newsletter content into a coherent, engaging podcast script.

Follow these user instructions for style and content focus:
'{instructions}'
{length_instruction}

Additional guidelines:
- Focus on summarizing key content and drawing meaningful connections across sources.
- Aim for depth and retention.
- The tone should be professional yet conversational.
- Structure the output clearly as a script (intro, main points, outro). Use clear paragraph breaks.
- Do NOT just list summaries; synthesize the information into a narrative.
- Ensure the final script flows well for audio.
- Avoid overly technical jargon unless requested.
- Output plain text suitable for text-to-speech (no markdown like ```, **, lists).
"""
    user_prompt = text_data

    try:
        script = jarvis.generate_text(
            prompt=user_prompt,
            instructions=system_prompt,
            model="gpt-4o-mini", # Or gpt-4o
            temperature=0.6,
            max_tokens=3000
        )
        return script
    except Exception as e:
        print(f"Error in generate_podcast_script calling jarvis.generate_text: {e}")
        traceback.print_exc()
        raise e


def generate_podcast_audio(script, output_path, voice_name):
    """
    Generates an audio file from the podcast script using the GenAI class.
    """
    if not jarvis:
        raise ConnectionError("AI service connection not established.")
    if not script:
        return False

    try:
        success = jarvis.generate_audio(
            text=script,
            file_path=output_path,
            voice=voice_name,
            model='tts-1',
            speed=1.0
        )
        return success
    except Exception as e:
        print(f"Error in generate_podcast_audio calling jarvis.generate_audio: {e}")
        traceback.print_exc()
        raise e


def generate_script_and_audio(text_data, instructions, target_duration_minutes, output_audio_path, voice_name):
    """
    Generates both the podcast script and the audio file in sequence.

    Args:
        text_data (str): Concatenated text content from newsletters.
        instructions (str): User-provided instructions.
        target_duration_minutes (int, optional): Explicitly requested duration (e.g., 2, 5, 10).
        output_audio_path (str): The full path to save the generated MP3 audio.
        voice_name (str): The desired AI voice name.

    Returns:
        tuple: (generated_script, audio_file_path)
    Raises:
        ConnectionError: If the GenAI instance is not available.
        Exception: Propagates exceptions from the underlying generation calls.
    """
    generated_script = None
    audio_file_path = None

    # Step 1: Generate Script, passing the duration target
    try:
        generated_script = generate_podcast_script(text_data, instructions, target_duration_minutes)
    except Exception as script_err:
        print(f"Error during script generation step: {script_err}")
        raise script_err # Propagate error

    # Step 2: Generate Audio ONLY if script generation was successful
    if generated_script:
        try:
            audio_success = generate_podcast_audio(generated_script, output_audio_path, voice_name)
            if audio_success and os.path.exists(output_audio_path):
                audio_file_path = output_audio_path
            else:
                 print("Audio generation step failed or file not found.")
        except Exception as audio_err:
            print(f"Error during audio generation step: {audio_err}")
            # Script exists, but audio failed - let app.py handle this state
            pass # Keep generated_script, audio_file_path remains None
    else:
        print("Script generation failed, skipping audio generation.")

    return generated_script, audio_file_path