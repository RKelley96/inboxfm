import os
import tempfile
import logging
from pathlib import Path
from genai import GenAI # Assuming genai.py is in the same directory

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load API key from environment variable
# Ensure you have a .env file in the same directory with OPENAI_API_KEY=your_key
# or set the environment variable system-wide.
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize the GenAI class (handles API calls)
# Check if the API key is loaded
if not OPENAI_API_KEY:
    logging.error("OPENAI_API_KEY environment variable not found.")
    # You might want to raise an error or handle this case appropriately
    # For now, we'll let GenAI raise an error if it's not provided.
    jarvis = None
else:
    try:
        jarvis = GenAI(OPENAI_API_KEY)
    except ValueError as e:
        logging.error(f"Failed to initialize GenAI: {e}")
        jarvis = None # Ensure jarvis is None if initialization fails

# --- File Reading ---

def read_uploaded_files(uploaded_files, temp_dir):
    """
    Reads content from a list of uploaded files (Streamlit UploadedFile objects).
    Saves files temporarily to read them. Handles txt, pdf, docx.

    Args:
        uploaded_files (list): A list of Streamlit UploadedFile objects.
        temp_dir (str): Path to the temporary directory to store files.

    Returns:
        str: Combined text content from all readable files.
        list: List of filenames that were successfully read.
        list: List of filenames that failed to read.
    """
    combined_text = ""
    read_files = []
    failed_files = []

    if not jarvis:
        logging.error("GenAI not initialized. Cannot read files.")
        return "", [], [f.name for f in uploaded_files] # Return all as failed if jarvis is missing

    for uploaded_file in uploaded_files:
        file_path = os.path.join(temp_dir, uploaded_file.name)
        file_ext = Path(uploaded_file.name).suffix.lower()
        content = None

        try:
            # Save the uploaded file temporarily
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            logging.info(f"Temporarily saved uploaded file: {file_path}")

            # Read based on extension
            if file_ext == ".txt":
                content = jarvis.read_text_file(file_path)
            elif file_ext == ".pdf":
                content = jarvis.read_pdf(file_path)
            elif file_ext == ".docx":
                content = jarvis.read_docx(file_path)
            else:
                logging.warning(f"Unsupported file type: {uploaded_file.name}")
                failed_files.append(uploaded_file.name)
                continue # Skip to next file

            if content:
                combined_text += f"\n\n--- Content from {uploaded_file.name} ---\n\n" + content
                read_files.append(uploaded_file.name)
            else:
                logging.warning(f"No content extracted from: {uploaded_file.name}")
                failed_files.append(uploaded_file.name)

        except Exception as e:
            logging.error(f"Failed to read or process file {uploaded_file.name}: {e}")
            failed_files.append(uploaded_file.name)
        finally:
            # Clean up the temporary file immediately after reading
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logging.info(f"Removed temporary file: {file_path}")
                except OSError as e:
                    logging.error(f"Error removing temporary file {file_path}: {e}")


    return combined_text.strip(), read_files, failed_files

# --- Podcast Generation Logic ---

def estimate_word_count(length_option):
    """Estimates target word count based on length option."""
    if length_option == "2 mins":
        return 300 # Approx 150 wpm * 2
    elif length_option == "5 mins":
        return 750 # Approx 150 wpm * 5
    elif length_option == "10 mins":
        return 1500 # Approx 150 wpm * 10
    else: # Auto or unspecified
        return None # Let the AI decide or use a default logic

def generate_podcast_script(newsletter_text, instructions, length_option="Auto"):
    """
    Generates a podcast script using the AI based on newsletter content and instructions.

    Args:
        newsletter_text (str): Combined text from the uploaded newsletters.
        instructions (str): User-provided instructions for style, tone, focus.
        length_option (str): Desired length ("Auto", "2 mins", "5 mins", "10 mins").

    Returns:
        str: The generated podcast script.
    """
    if not jarvis:
        raise RuntimeError("GenAI service is not available.")
    if not newsletter_text:
        raise ValueError("Newsletter text cannot be empty.")

    word_count_target = estimate_word_count(length_option)
    length_guidance = f"Aim for a podcast script approximately {word_count_target} words long." if word_count_target else "Determine an appropriate length based on the content."

    # Construct the prompt for the AI
    prompt = f"""
    **Task:** Create a personalized podcast script summarizing and connecting insights from the following newsletter content.

    **Target Audience:** Busy millennial knowledge workers (25-40) in fields like finance, VC, and tech. They are intellectually curious and want actionable insights.

    **Podcast Goal:** Turn these newsletters into a concise, engaging audio summary that gives the listener an edge at work with minimal effort. Focus on key takeaways and meaningful connections between different sources if applicable.

    **User Instructions for Style/Content:**
    {instructions if instructions else "Default: Professional, insightful, and engaging tone. Summarize key points clearly."}

    **Length Guidance:**
    {length_guidance}

    **Newsletter Content:**
    ```
    {newsletter_text}
    ```

    **Output:**
    Produce ONLY the podcast script, ready to be read aloud. Start directly with the script content. Do not include introductory phrases like "Here is the podcast script:". Structure it logically, perhaps with a brief intro, main points, and a brief outro mentioning it was generated by Inbox.fm.
    """

    # Define system instructions for the AI model
    system_instructions = "You are Inbox.fm, an AI assistant that transforms email newsletters into personalized podcasts for busy professionals. Generate a clear, concise, and engaging podcast script based on the provided content and instructions."

    logging.info(f"Generating podcast script with length option: {length_option}")
    try:
        script = jarvis.generate_text(prompt, instructions=system_instructions, model="gpt-4o") # Use a powerful model
        logging.info("Podcast script generated successfully.")
        return script
    except Exception as e:
        logging.error(f"Error generating podcast script: {e}")
        raise # Re-raise the exception to be handled by the caller

def generate_podcast_audio(script_text, output_dir, voice_name='nova', speed=1.0, filename="podcast_output.mp3"):
    """
    Generates the podcast audio file from the script using AI TTS.

    Args:
        script_text (str): The podcast script.
        output_dir (str): Directory to save the audio file.
        voice_name (str): The AI voice to use.
        speed (float): Speech speed.
        filename (str): The name for the output audio file.

    Returns:
        str: The full path to the generated audio file.
    """
    if not jarvis:
        raise RuntimeError("GenAI service is not available.")
    if not script_text:
        raise ValueError("Script text cannot be empty.")

    audio_path = os.path.join(output_dir, filename)
    logging.info(f"Generating podcast audio file at: {audio_path}")

    try:
        success = jarvis.generate_audio(script_text, audio_path, voice=voice_name, speed=speed)
        if success:
            logging.info("Podcast audio generated successfully.")
            return audio_path
        else:
            # This part might not be reached if generate_audio raises an exception on failure
            raise RuntimeError("Audio generation reported failure without exception.")
    except Exception as e:
        logging.error(f"Error generating podcast audio: {e}")
        raise # Re-raise the exception

