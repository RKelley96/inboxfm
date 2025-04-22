import streamlit as st
import os
import tempfile
import uuid
import logging
from pathlib import Path
import base64 # Import base64 library

# Import functions from our utility script
# Ensure utils.py and genai.py are in the same directory
try:
    from utils import read_uploaded_files, generate_podcast_script, generate_podcast_audio
except ImportError:
    st.error("Failed to import required modules. Make sure 'utils.py' and 'genai.py' are in the correct directory.")
    st.stop() # Stop execution if imports fail

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants ---
# Directory to store generated audio files, relative to the app script
AUDIO_DIR = "audio_output"

# --- Page Configuration ---
st.set_page_config(
    page_title="Inbox.fm - Your Newsletter Podcast",
    page_icon="🎙️",
    layout="wide"
)

# --- Custom CSS Styling ---
st.markdown("""
<style>
    /* Main header style */
    .main-header {
        font-size: 2.5rem; /* Larger font size */
        font-weight: bold;
        color: #2E3B4E; /* Dark blue-gray color */
        text-align: center;
        margin-bottom: 1rem;
    }
    /* Sub-header style */
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #4A5568; /* Medium gray */
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        border-bottom: 2px solid #E2E8F0; /* Light gray border */
        padding-bottom: 0.3rem;
    }
    /* Informational text style */
    .info-text {
        font-size: 1rem;
        color: #718096; /* Lighter gray */
        text-align: center;
        margin-bottom: 2rem;
    }
    /* Style Streamlit buttons */
    .stButton>button {
        background-color: #4299E1; /* Blue background */
        color: white;
        font-weight: bold;
        border-radius: 0.5rem; /* Rounded corners */
        border: none;
        padding: 0.6rem 1.2rem;
        transition: background-color 0.3s ease; /* Smooth hover effect */
    }
    .stButton>button:hover {
        background-color: #2B6CB0; /* Darker blue on hover */
    }
    /* Style the file uploader */
    .stFileUploader label {
        font-weight: bold;
        color: #4A5568;
    }
    /* Center elements like audio player and download button */
    /* Target the custom HTML audio player */
    .audio-container, div[data-testid="stDownloadButton"] {
       display: flex;
       justify-content: center;
       margin-top: 1rem;
       flex-direction: column; /* Stack player and download */
       align-items: center;
    }
    .audio-container audio {
        width: 80%; /* Adjust width as needed */
        margin-bottom: 1rem; /* Space between player and download button */
    }
    div[data-testid="stDownloadButton"] button {
       background-color: #48BB78; /* Green background */
       width: auto; /* Adjust width automatically */
    }
    div[data-testid="stDownloadButton"] button:hover {
       background-color: #38A169; /* Darker green on hover */
    }

</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
# Initialize session state variables if they don't exist
# This helps maintain state across user interactions
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    # Use OS temp dir ONLY for temporary storage during file reading
    st.session_state.temp_dir_read = tempfile.mkdtemp()
    logging.info(f"Created temporary directory for file reading: {st.session_state.temp_dir_read}")
    # Ensure the dedicated audio output directory exists
    if not os.path.exists(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)
        logging.info(f"Created audio output directory: {AUDIO_DIR}")

if 'combined_text' not in st.session_state:
    st.session_state.combined_text = None
if 'podcast_script' not in st.session_state:
    st.session_state.podcast_script = None
# Store the relative path for web access and the full path for file operations
if 'audio_relative_path' not in st.session_state:
     st.session_state.audio_relative_path = None # Keep for potential future use? Or remove? Let's keep for now.
if 'audio_full_path' not in st.session_state:
    st.session_state.audio_full_path = None
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False
if 'error_message' not in st.session_state:
    st.session_state.error_message = None
if 'read_files_list' not in st.session_state:
    st.session_state.read_files_list = []
if 'failed_files_list' not in st.session_state:
    st.session_state.failed_files_list = []

# --- Helper Function ---
def reset_state():
    """Resets the session state for a new podcast generation."""
    st.session_state.combined_text = None
    st.session_state.podcast_script = None
    st.session_state.audio_relative_path = None
    st.session_state.audio_full_path = None
    st.session_state.is_processing = False
    st.session_state.error_message = None
    st.session_state.read_files_list = []
    st.session_state.failed_files_list = []
    # Note: We are not cleaning up the AUDIO_DIR here for simplicity,
    # but in a production app, you'd want a cleanup strategy.
    logging.info("Session state reset.")

# --- Main Application UI ---

# Header
st.markdown('<div class="main-header">🎙️ Inbox.fm</div>', unsafe_allow_html=True)
st.markdown('<div class="info-text">Transform your newsletters into personalized podcasts.</div>', unsafe_allow_html=True)

# Check for API Key early
if not os.getenv("OPENAI_API_KEY"):
    st.error("🚨 OpenAI API Key not found. Please set the OPENAI_API_KEY environment variable (e.g., in a .env file) and restart the app.")
    st.stop()

# Layout Columns
col1, col2 = st.columns([2, 1]) # Input column wider than output

with col1:
    st.markdown('<div class="sub-header">Step 1: Upload Newsletters</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Select one or more newsletter files (.txt, .pdf, .docx)",
        type=["txt", "pdf", "docx"],
        accept_multiple_files=True,
        key="newsletter_uploader"
    )

    if uploaded_files:
        st.success(f"{len(uploaded_files)} file(s) selected. Ready for processing.")

    st.markdown('<div class="sub-header">Step 2: Configure Your Podcast</div>', unsafe_allow_html=True)

    # Instructions Text Area
    instructions = st.text_area(
        "Instructions for Podcast Style & Content:",
        placeholder="e.g., Focus on actionable insights for tech investors. Keep the tone conversational but professional. Mention key company names.",
        height=100,
        key="podcast_instructions"
    )

    # Configuration Options in Columns
    config_col1, config_col2 = st.columns(2)

    with config_col1:
        # Length Selection
        length_option = st.selectbox(
            "Desired Podcast Length:",
            options=["Auto", "2 mins", "5 mins", "10 mins"],
            key="podcast_length"
        )

    with config_col2:
        # Voice Selection
        voice_option = st.selectbox(
            "Select AI Voice:",
            options=["nova", "alloy", "echo", "fable", "onyx", "shimmer"], # Common OpenAI voices
            key="podcast_voice"
        )

    # Generate Button
    st.markdown("---") # Visual separator
    generate_button = st.button("✨ Generate Podcast", key="generate_button", use_container_width=True)

# --- Processing Logic ---
if generate_button and uploaded_files:
    # Reset previous results before starting
    reset_state()
    st.session_state.is_processing = True
    st.session_state.error_message = None

    # Display spinner context manager
    with st.spinner("Processing... Reading files, generating script, and creating audio..."):
        try:
            # 1. Read Files (using OS temp dir for reading)
            logging.info("Starting file reading process.")
            combined_text, read_files, failed_files = read_uploaded_files(uploaded_files, st.session_state.temp_dir_read)
            st.session_state.combined_text = combined_text
            st.session_state.read_files_list = read_files
            st.session_state.failed_files_list = failed_files
            logging.info(f"Files read. Success: {len(read_files)}, Failed: {len(failed_files)}")

            # Check if any content was actually read
            if not combined_text:
                st.session_state.error_message = "Could not read any content from the uploaded files. Please check the file formats and content."
            else:
                # 2. Generate Script (only if text was read)
                logging.info("Generating podcast script.")
                script = generate_podcast_script(combined_text, instructions, length_option)
                st.session_state.podcast_script = script
                logging.info("Podcast script generated.")

                # 3. Generate Audio (saving to AUDIO_DIR)
                logging.info(f"Generating podcast audio in directory: {AUDIO_DIR}")
                # Define filename using session ID to avoid conflicts
                audio_filename = f"inboxfm_podcast_{st.session_state.session_id}.mp3"
                # Pass AUDIO_DIR as the output directory
                # generate_podcast_audio should return the full path to the saved file
                generated_audio_full_path = generate_podcast_audio(
                    script_text=script,
                    output_dir=AUDIO_DIR, # Pass the dedicated audio directory
                    voice_name=voice_option,
                    speed=1.0,
                    filename=audio_filename
                )

                # Check if the audio file was actually created and has size > 0
                if os.path.exists(generated_audio_full_path) and os.path.getsize(generated_audio_full_path) > 0:
                    st.session_state.audio_full_path = generated_audio_full_path
                    # Store the relative path just in case, but we won't use it for the player now
                    st.session_state.audio_relative_path = os.path.join(AUDIO_DIR, audio_filename)
                    logging.info(f"Podcast audio generated successfully at {st.session_state.audio_full_path}, size: {os.path.getsize(st.session_state.audio_full_path)} bytes")
                elif os.path.exists(generated_audio_full_path):
                    st.session_state.error_message = "Audio generation finished, but the audio file is empty (0 bytes)."
                    logging.error(f"Generated audio file is empty: {generated_audio_full_path}")
                else:
                    st.session_state.error_message = "Audio generation finished, but the audio file was not found."
                    logging.error(f"Audio file path not found after generation attempt: {generated_audio_full_path}")

        except Exception as e:
            # Catch any exception during the process
            logging.error(f"Error during podcast generation: {e}", exc_info=True)
            st.session_state.error_message = f"An error occurred: {e}"
            st.session_state.audio_full_path = None # Ensure paths are None on error
            st.session_state.audio_relative_path = None
        finally:
            # Ensure processing state is always turned off
            st.session_state.is_processing = False
            # Rerun to update the UI immediately after processing finishes or fails
            st.rerun()


elif generate_button and not uploaded_files:
    st.warning("Please upload at least one newsletter file.")

# --- Display Results ---
with col2:
    st.markdown('<div class="sub-header">Step 3: Listen & Download</div>', unsafe_allow_html=True)

    # Display status of file reading
    if st.session_state.read_files_list or st.session_state.failed_files_list:
        with st.expander("File Reading Status", expanded=False):
            if st.session_state.read_files_list:
                st.write("**Successfully Read:**")
                for fname in st.session_state.read_files_list:
                    st.caption(f"✅ {fname}")
            if st.session_state.failed_files_list:
                st.write("**Failed/Skipped:**")
                for fname in st.session_state.failed_files_list:
                    st.caption(f"❌ {fname}")

    # Display Error Message if it occurred
    if st.session_state.error_message:
        st.error(f"🚨 {st.session_state.error_message}")

    # Display Audio Player and Download Button if audio exists and full path is set
    if st.session_state.audio_full_path and os.path.exists(st.session_state.audio_full_path):
        st.success("🎉 Your podcast is ready!")

        # Embed HTML5 Audio Player using Base64 Data URL
        try:
            # *** CHANGE HERE: Read bytes, encode to Base64, create Data URL ***
            with open(st.session_state.audio_full_path, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode() # Decode to string
                data_url = f"data:audio/mp3;base64,{b64}"
                logging.info(f"Generated Base64 data URL (length: {len(data_url)}) for {st.session_state.audio_full_path}")

            audio_html = f"""
            <div class="audio-container">
                <audio controls src="{data_url}">
                    Your browser does not support the audio element. Please use the download button.
                </audio>
            </div>
            """
            st.markdown(audio_html, unsafe_allow_html=True)
            logging.info(f"Displaying HTML5 audio player using Base64 data URL.")

        except Exception as e:
            st.error(f"Error embedding Base64 audio player: {e}")
            logging.error(f"Error reading/encoding/displaying Base64 for {st.session_state.audio_full_path}: {e}", exc_info=True)


        # Download Button - Use the *full* path to read the file server-side
        try:
            with open(st.session_state.audio_full_path, "rb") as file:
                st.download_button(
                    label="⬇️ Download Podcast (.mp3)",
                    data=file, # Pass the file object directly for download
                    file_name=Path(st.session_state.audio_full_path).name,
                    mime="audio/mp3",
                    key="download_button"
                )
        except Exception as e:
            st.error(f"Error preparing download link: {e}")
            logging.error(f"Error creating download button for {st.session_state.audio_full_path}: {e}", exc_info=True)


    # Display message if still processing
    elif st.session_state.is_processing:
         st.info("⏳ Processing your request...")

    # Display message if no audio generated without error
    elif not st.session_state.is_processing and generate_button and not st.session_state.audio_full_path and not st.session_state.error_message:
         st.warning("Processing finished, but no audio file was generated. Please check logs or try again.")

    # Default message when idle
    elif not st.session_state.is_processing and not st.session_state.audio_full_path and not st.session_state.error_message:
        st.info("Upload files and click 'Generate Podcast' to create your audio summary.")


    # Display Generated Script (Optional)
    if st.session_state.podcast_script:
        with st.expander("View Generated Podcast Script", expanded=False):
            st.text_area("Script:", value=st.session_state.podcast_script, height=300, disabled=True, key="script_display")


# --- Footer ---
st.markdown("---")
st.markdown('<div class="info-text" style="font-size: 0.8rem;">Inbox.fm - Powered by AI</div>', unsafe_allow_html=True)

# Note: Temporary files for reading are stored in OS temp dir.
# Audio files are stored in the AUDIO_DIR ("audio_output") subdirectory.
# Implement cleanup logic for AUDIO_DIR in a real application.

