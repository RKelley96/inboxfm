# app.py
import streamlit as st
import os
import tempfile
import uuid
from pathlib import Path
import time
import traceback

# --- Attempt to import utility functions ---
try:
    if not os.path.exists("utils.py"):
        utils_found = False
    else:
        from utils import read_uploaded_files, generate_script_and_audio
        utils_found = True
except ImportError as import_err:
    utils_found = False
    if os.path.exists("utils.py"):
        def read_uploaded_files(files):
            st.error(f"Import Error: {import_err}. Check `read_uploaded_files` in utils.py.")
            raise NotImplementedError("`read_uploaded_files` missing/broken.")
        def generate_script_and_audio(texts, instructions, duration, audio_path, voice):
            st.error(f"Import Error: {import_err}. Check `generate_script_and_audio` in utils.py.")
            raise NotImplementedError("`generate_script_and_audio` missing/broken.")

# --- Page Configuration ---
st.set_page_config(
    page_title="Inbox.fm Podcast Generator", # Simplified Title
    page_icon="🎙️",
    layout="wide"
)

# --- Custom CSS Styling (Sleeker Look) ---
st.markdown("""
<style>
    /* Base & Fonts */
    body {
        font-family: 'Inter', sans-serif; /* Cleaner sans-serif font */
        background-color: #f8f9fa; /* Light grey background */
    }
    /* Add Inter font from Google Fonts */
    @import url('[https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap](https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap)');

    /* Headers */
    .main-header {
        font-size: 2.5rem; /* Slightly smaller */
        font-weight: 700; /* Bold */
        color: #212529; /* Dark grey */
        text-align: center;
        padding-top: 1.5rem;
        margin-bottom: 1.5rem; /* More space below */
    }
    /* Removed sub-header class - simplified */
    .section-header {
        font-size: 1.4rem; /* Adjusted size */
        font-weight: 600; /* Semi-bold */
        color: #007bff; /* Primary blue */
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #dee2e6; /* Lighter border */
        padding-bottom: 0.4rem;
    }
    .info-text {
        font-size: 0.95rem; /* Slightly smaller */
        color: #6c757d; /* Medium grey */
        margin-bottom: 1rem;
        line-height: 1.6;
    }

    /* Buttons */
    .stButton>button {
        background-color: #007bff; /* Primary blue */
        color: white;
        font-weight: 500; /* Medium weight */
        border-radius: 6px; /* Slightly less rounded */
        padding: 0.6rem 1.2rem;
        border: none;
        transition: background-color 0.2s ease, transform 0.1s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        width: 100%; /* Full width buttons in columns */
        margin-top: 0.5rem; /* Consistent spacing */
    }
    .stButton>button:hover {
        background-color: #0056b3; /* Darker blue */
        box-shadow: 0 2px 5px rgba(0,0,0,0.15);
        transform: translateY(-1px); /* Slight lift effect */
    }
    .stButton>button:disabled {
        background-color: #adb5bd; /* Grey disabled */
        color: #e9ecef;
        cursor: not-allowed;
        box-shadow: none;
        transform: none;
    }
    .stDownloadButton>button { /* Keep download distinct */
        background-color: #28a745; /* Success green */
        border-color: #28a745;
    }
    .stDownloadButton>button:hover {
        background-color: #218838; /* Darker green */
        border-color: #1e7e34;
    }

    /* Radio Buttons (for duration) */
    div[role="radiogroup"] {
        display: flex;
        flex-wrap: wrap; /* Allow wrapping */
        gap: 10px; /* Space between buttons */
        justify-content: space-between; /* Distribute space */
        margin-bottom: 1rem;
    }
    div[role="radiogroup"] label { /* Style individual radio items */
      background-color: #e9ecef; /* Light grey background */
      padding: 8px 15px;
      border-radius: 6px;
      border: 1px solid #ced4da;
      cursor: pointer;
      transition: background-color 0.2s ease, border-color 0.2s ease;
      flex-grow: 1; /* Allow buttons to grow */
      text-align: center;
      font-weight: 500;
      color: #495057;
    }
    div[role="radiogroup"] label:hover {
      background-color: #dee2e6;
      border-color: #adb5bd;
    }
    /* Style the selected radio button */
    div[role="radiogroup"] input[type="radio"]:checked + div label{
       background-color: #007bff; /* Blue selected */
       color: white;
       border-color: #0056b3;
    }


    /* Inputs & Widgets */
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div {
        border-radius: 6px;
        border: 1px solid #ced4da; /* Standard border color */
        background-color: #fff; /* White background */
        font-size: 0.95rem;
    }
    .stFileUploader label {
        border-radius: 6px;
        border: 2px dashed #ced4da;
        background-color: #f8f9fa;
        transition: border-color 0.2s ease, background-color 0.2s ease;
    }
    .stFileUploader label:hover {
        border-color: #007bff;
        background-color: #e7f1ff; /* Light blue tint on hover */
    }
    .stExpander {
        border: 1px solid #dee2e6;
        border-radius: 6px;
        background-color: #fff;
        margin-top: 1rem;
    }
    .stExpander header {
        font-weight: 600;
        color: #495057; /* Darker grey */
        font-size: 1rem;
    }

    /* Alerts */
    .stAlert {
        border-radius: 6px;
        font-size: 0.9rem;
        padding: 0.8rem 1rem;
    }
    .stAlert strong {
         font-weight: 600;
    }
    .success-text { /* Custom success message */
        color: #155724; /* Dark green text */
        background-color: #d4edda; /* Light green background */
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        border-left: 5px solid #28a745; /* Green border */
        font-weight: 500;
    }

</style>
""", unsafe_allow_html=True)


# --- Session State Initialization ---
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp(prefix=f"inboxfm_{uuid.uuid4()}_")
if 'newsletter_text' not in st.session_state:
    st.session_state.newsletter_text = None
if 'podcast_script' not in st.session_state:
    st.session_state.podcast_script = None
if 'audio_file_path' not in st.session_state:
    st.session_state.audio_file_path = None
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False
if 'last_error' not in st.session_state:
    st.session_state.last_error = None
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'upload_key' not in st.session_state:
    st.session_state.upload_key = 0
if 'selected_voice' not in st.session_state:
    st.session_state.selected_voice = "nova"
if 'selected_duration' not in st.session_state: # New state for duration
    st.session_state.selected_duration = None # Default to None (auto)


# --- Helper Functions ---
def reset_app_state():
    """Resets the session state variables related to a processing run."""
    st.session_state.newsletter_text = None
    st.session_state.podcast_script = None
    st.session_state.audio_file_path = None
    st.session_state.is_processing = False
    st.session_state.last_error = None
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.upload_key += 1
    st.session_state.selected_duration = None # Reset duration on start over
    # Keep temp_dir and voice selection

# --- App Header ---
st.markdown('<div class="main-header">Inbox.fm 🎙️</div>', unsafe_allow_html=True)
# Removed sub-header for simplicity

if not utils_found:
    st.error("🚨 **Critical Setup Error:** `utils.py` could not be found or is missing required functions. Please ensure `utils.py` and `genai.py` are in the same directory as `app.py`. Core functionality is disabled.", icon="⚙️")

# --- Main Layout Columns ---
col1, col2 = st.columns([3, 2]) # Input column slightly wider

with col1:
    # --- Step 1: Upload ---
    st.markdown('<div class="section-header">1. Upload Newsletters</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Select .txt, .pdf, or .docx files", # Simplified label
        type=["txt", "pdf", "docx"],
        accept_multiple_files=True,
        key=f"newsletter_uploader_{st.session_state.upload_key}",
        disabled=not utils_found
    )

    # File processing logic (runs on upload)
    if uploaded_files and st.session_state.newsletter_text is None and not st.session_state.is_processing:
         if utils_found:
            try:
                with st.spinner("Reading files..."):
                    st.session_state.last_error = None
                    extracted_text = read_uploaded_files(uploaded_files)
                    st.session_state.newsletter_text = extracted_text
                    if not extracted_text:
                         st.warning("⚠️ Could not extract text from uploaded files.")
            except Exception as e:
                st.error(f"Error reading files: {e}")
                st.session_state.last_error = f"File Reading Error: {e}"
                st.session_state.newsletter_text = None
            # No automatic rerun needed here, state update handles UI change

    # --- Step 2: Customize ---
    st.markdown('<div class="section-header">2. Customize Podcast</div>', unsafe_allow_html=True)

    # Duration Selection using Radio buttons
    st.markdown("**Target Duration (Approximate):**")
    duration_options = {
        'Auto (Default)': None, # Represent 'Auto' as None
        '~5 min': 5,
        '~10 min': 10,
        '~15 min': 15
    }
    # Get the current index based on stored duration value
    duration_keys = list(duration_options.keys())
    current_duration_value = st.session_state.selected_duration
    try:
        # Find the index corresponding to the stored value
        current_index = list(duration_options.values()).index(current_duration_value)
    except ValueError:
        current_index = 0 # Default to 'Auto' if value not found

    selected_duration_label = st.radio(
        "Select Podcast Length",
        options=duration_keys,
        index=current_index,
        key="duration_radio", # Widget key
        horizontal=True,
        label_visibility="collapsed" # Hide the "Select Podcast Length" label itself
    )
    # Update session state when radio button changes
    st.session_state.selected_duration = duration_options[selected_duration_label]


    # Voice Selection
    st.markdown("**Voice:**")
    voice_options = ["nova", "alloy", "echo", "fable", "onyx", "shimmer", "ash", "ballad", "coral", "sage"]
    st.selectbox(
        "Select AI Voice",
        options=voice_options,
        index=voice_options.index(st.session_state.selected_voice),
        key="voice_selector_widget",
        on_change=lambda: st.session_state.update(selected_voice=st.session_state.voice_selector_widget),
        disabled=not utils_found,
        label_visibility="collapsed" # Hide label
    )

    # Optional Instructions
    st.markdown("**Additional Instructions (Optional):**")
    instructions = st.text_area(
        "Add specific style notes, topics to focus on, etc.", # Simplified label
        placeholder="Example: Focus on the financial implications mentioned. Use an enthusiastic tone.",
        height=100,
        key="podcast_instructions",
        disabled=not utils_found,
        label_visibility="collapsed" # Hide label
    )

    # --- Reset Button (Moved to col1 for better flow) ---
    show_reset = st.session_state.newsletter_text or st.session_state.podcast_script or st.session_state.audio_file_path or st.session_state.last_error
    if show_reset:
        if st.button("🔄 Clear All & Start Over", key="reset_button", use_container_width=True):
            reset_app_state()
            st.rerun()


# --- Processing & Output Column ---
with col2:
    # --- Step 3: Generate ---
    st.markdown('<div class="section-header">3. Generate & Listen</div>', unsafe_allow_html=True)

    # Generate Button
    can_generate = utils_found and st.session_state.newsletter_text and not st.session_state.is_processing
    if st.button("🚀 Generate Podcast", key="generate_podcast_button", disabled=not can_generate, use_container_width=True):
        if not st.session_state.newsletter_text:
            st.warning("Please upload newsletter files first.")
        else:
            current_instructions = st.session_state.get("podcast_instructions", "")
            st.session_state.is_processing = True
            st.session_state.last_error = None
            st.session_state.podcast_script = None
            st.session_state.audio_file_path = None
            st.rerun()

    # --- Display Area ---
    if st.session_state.is_processing:
        # Show spinner centrally in the column
        with st.spinner("Generating podcast... This may take several moments..."):
            # The actual processing happens on the *next* rerun after setting is_processing=True
            # This block just shows the spinner while is_processing is True
            st.empty() # Placeholder to show spinner

    # Display Error if it occurred
    if st.session_state.last_error and not st.session_state.is_processing:
        st.error(f"⚠️ **Error:** {st.session_state.last_error}")

    # Display Audio Player & Download if successful
    if st.session_state.audio_file_path and os.path.exists(st.session_state.audio_file_path) and not st.session_state.is_processing:
        st.markdown('<div class="success-text">✅ Your podcast is ready!</div>', unsafe_allow_html=True)
        try:
             with open(st.session_state.audio_file_path, "rb") as audio_file:
                 audio_bytes = audio_file.read()
             st.audio(audio_bytes, format="audio/mp3")

             st.download_button(
                 label="⬇️ Download Podcast (.mp3)",
                 data=audio_bytes,
                 file_name=f"Inbox.fm_Podcast_{time.strftime('%Y%m%d_%H%M%S')}.mp3",
                 mime="audio/mp3",
                 key="download_button",
                 use_container_width=True
             )
        except FileNotFoundError:
             st.error("Error: Could not find generated audio file.")
             st.session_state.audio_file_path = None
             st.session_state.last_error = "Audio file missing after generation."
             # No acknowledge button here, error is shown, user can retry or reset
        except Exception as e:
             st.error(f"Error preparing audio: {e}")
             st.session_state.audio_file_path = None
             st.session_state.last_error = f"Audio display/download error: {e}"

    # Display Script Expander if script exists (even if audio failed)
    if st.session_state.podcast_script and not st.session_state.is_processing:
         with st.expander("📄 View Generated Script", expanded=False):
              st.text_area("Script:", value=st.session_state.podcast_script, height=300, key="script_display", disabled=True)

    # Initial guidance message
    if not st.session_state.podcast_script and not st.session_state.audio_file_path and not st.session_state.is_processing and not st.session_state.last_error:
         st.info("Upload files and click 'Generate Podcast' to begin." if utils_found else "⚙️ Application setup incomplete.")


# --- Footer ---
# Optional: Add a footer outside columns if desired
# st.markdown("---")
# st.markdown('<div class="info-text" style="text-align: center; font-size: 0.9rem; color: #adb5bd;">Inbox.fm - Powered by AI</div>', unsafe_allow_html=True)

