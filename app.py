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
    page_title="Inbox.fm Podcast Generator",
    page_icon="🎙️",
    layout="wide"
)

# --- Custom CSS Styling (Enhanced Look) ---
st.markdown("""
<style>
    /* Base & Fonts */
    body {
        font-family: 'Inter', sans-serif;
        background-color: #f4f7f6; /* Lighter, slightly greenish background */
    }
    /* Add Inter font from Google Fonts */
    @import url('[https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap](https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap)');

    /* Headers */
    .main-header {
        font-size: 2.6rem;
        font-weight: 700;
        color: #2c3e50; /* Dark slate blue */
        text-align: center;
        padding-top: 2rem;
        margin-bottom: 2rem;
        letter-spacing: -0.5px; /* Tighter letter spacing */
    }
    .section-header {
        font-size: 1.3rem; /* Slightly smaller */
        font-weight: 600;
        color: #3498db; /* Brighter blue */
        margin-top: 1.5rem; /* Reduced top margin */
        margin-bottom: 0.8rem;
        border: none; /* Remove border */
        padding-bottom: 0;
    }
    .info-text {
        font-size: 0.9rem;
        color: #566573; /* Medium grey-blue */
        margin-bottom: 1rem;
        line-height: 1.5;
    }
    label.input-label { /* Custom class for labels */
        font-size: 0.95rem;
        font-weight: 500;
        color: #495057; /* Dark grey */
        margin-bottom: 0.3rem;
        display: block;
    }

    /* Input Area Styling */
    .stApp > header { /* Hide Streamlit's default header */
        background-color: transparent;
    }
    div[data-testid="stVerticalBlock"] { /* Target the main containers */
        border-radius: 12px; /* Rounded corners for sections */
        padding: 1.5rem 2rem; /* Add padding */
        background-color: #ffffff; /* White background for cards */
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); /* Subtle shadow */
        margin-bottom: 1.5rem; /* Space between cards */
    }
    /* Ensure columns don't have double background/padding */
     div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"] {
         background-color: transparent;
         box-shadow: none;
         padding: 0;
         border-radius: 0;
         margin-bottom: 0;
     }


    /* Buttons */
    .stButton>button {
        background-color: #3498db; /* Brighter blue */
        color: white;
        font-weight: 600; /* Bolder text */
        border-radius: 8px;
        padding: 0.7rem 1.5rem;
        border: none;
        transition: all 0.2s ease;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        width: 100%;
        margin-top: 1rem; /* Consistent spacing */
    }
    .stButton>button:hover {
        background-color: #2980b9; /* Darker blue */
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        transform: translateY(-2px);
    }
    .stButton>button:disabled {
        background-color: #aeb6bf; /* Grey disabled */
        color: #e9ecef;
        cursor: not-allowed;
        box-shadow: none;
        transform: none;
    }
    .stDownloadButton>button {
        background-color: #2ecc71; /* Bright green */
        border: none;
    }
    .stDownloadButton>button:hover {
        background-color: #28b463; /* Darker green */
    }

    /* Radio Buttons (Horizontal & Themed) */
    div[role="radiogroup"] {
        display: flex;
        flex-wrap: nowrap; /* Prevent wrapping */
        gap: 8px; /* Space between buttons */
        justify-content: flex-start; /* Align left */
        margin-bottom: 1rem;
        overflow-x: auto; /* Allow horizontal scroll on small screens if needed */
        padding-bottom: 5px; /* Space for scrollbar if it appears */
    }
    div[role="radiogroup"] label { /* Style individual radio items */
      background-color: #f1f3f5; /* Very light grey */
      padding: 6px 12px; /* Smaller padding */
      border-radius: 20px; /* Pill shape */
      border: 1px solid #dee2e6;
      cursor: pointer;
      transition: all 0.2s ease;
      font-weight: 500;
      font-size: 0.85rem; /* Smaller font */
      color: #495057;
      white-space: nowrap; /* Keep text on one line */
    }
    div[role="radiogroup"] label:hover {
      background-color: #e9ecef;
      border-color: #adb5bd;
    }
    div[role="radiogroup"] input[type="radio"]:checked + div label{
       background-color: #3498db; /* Blue selected */
       color: white;
       border-color: #2980b9;
       box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }


    /* Inputs & Widgets */
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div {
        border-radius: 8px;
        border: 1px solid #dee2e6;
        background-color: #f8f9fa; /* Match page background */
        font-size: 0.9rem;
        padding: 0.5rem 0.75rem;
    }
    .stFileUploader {
        border: none; /* Remove default border */
        padding: 0;
    }
    .stFileUploader label { /* Remove the dashed box */
        border: none;
        background-color: transparent;
        padding: 0;
        text-align: left; /* Align label text left */
        color: #495057; /* Standard text color */
        font-weight: 500;
    }
    .stFileUploader label span { /* Target the text span */
        font-size: 0.95rem;
    }
    .stFileUploader ul { /* Style the uploaded file list */
        margin-top: 0.5rem;
    }

    .stExpander {
        border: 1px solid #e9ecef; /* Lighter border */
        border-radius: 8px;
        background-color: #f8f9fa; /* Match background */
        margin-top: 1rem;
        box-shadow: none; /* Remove shadow */
    }
    .stExpander header {
        font-weight: 500; /* Medium weight */
        color: #495057;
        font-size: 0.95rem;
        padding: 0.6rem 1rem; /* Adjust padding */
        background-color: #f1f3f5; /* Header background */
        border-bottom: 1px solid #e9ecef;
    }
    .stExpander div[data-testid="stExpanderDetails"] { /* Content area */
        padding: 0.5rem 1rem 1rem 1rem; /* Adjust padding */
    }
    .stExpander div[data-testid="stExpanderDetails"] .stTextArea textarea {
        background-color: #fff; /* White background for script */
        font-size: 0.85rem;
    }

    /* Alerts */
    .stAlert {
        border-radius: 8px;
        font-size: 0.9rem;
        padding: 0.8rem 1rem;
    }
    .stAlert strong {
         font-weight: 600;
    }
    .success-text {
        color: #155724;
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 5px solid #28a745;
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

# --- App Header ---
st.markdown('<div class="main-header">Inbox.fm 🎙️</div>', unsafe_allow_html=True)

if not utils_found:
    st.error("🚨 **Critical Setup Error:** `utils.py` not found or missing functions. Core functionality disabled.", icon="⚙️")

# --- Main Layout Columns ---
col1, col2 = st.columns([3, 2]) # Input: 60%, Output: 40% approx

# --- Input Column (col1) ---
with col1:
    with st.container(): # Wrap inputs in a container for styling
        # --- Step 1: Upload ---
        st.markdown('<div class="section-header">1. Upload Newsletters</div>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Select or drag & drop files (.txt, .pdf, .docx)", # More inviting label
            type=["txt", "pdf", "docx"],
            accept_multiple_files=True,
            key=f"newsletter_uploader_{st.session_state.upload_key}",
            disabled=not utils_found,
            label_visibility="collapsed" # Hide default label, use markdown header instead
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

        # --- Step 2: Customize ---
        st.markdown('<div class="section-header">2. Customize Podcast</div>', unsafe_allow_html=True)

        # Duration Selection using Radio buttons
        st.markdown('<label class="input-label">Target Duration (Approximate)</label>', unsafe_allow_html=True)
        duration_options = {
            'Default': None, # Represent 'Auto' as None
            '2 mins': 2,
            '5 mins': 5,
            '10 mins': 10
        }
        duration_keys = list(duration_options.keys())
        current_duration_value = st.session_state.selected_duration
        try:
            current_index = list(duration_options.values()).index(current_duration_value)
        except ValueError:
            current_index = 0 # Default to 'Default'

        selected_duration_label = st.radio(
            "Select Podcast Length", # Hidden label, but needed for widget
            options=duration_keys,
            index=current_index,
            key="duration_radio",
            horizontal=True,
            label_visibility="collapsed"
        )
        # Update session state when radio button changes
        st.session_state.selected_duration = duration_options[selected_duration_label]


        # Voice Selection
        st.markdown('<label class="input-label">Voice</label>', unsafe_allow_html=True)
        voice_options = ["nova", "alloy", "echo", "fable", "onyx", "shimmer", "ash", "ballad", "coral", "sage"]
        st.selectbox(
            "Select AI Voice", # Hidden label
            options=voice_options,
            index=voice_options.index(st.session_state.selected_voice),
            key="voice_selector_widget",
            on_change=lambda: st.session_state.update(selected_voice=st.session_state.voice_selector_widget),
            disabled=not utils_found,
            label_visibility="collapsed"
        )

        # Optional Instructions
        st.markdown('<label class="input-label">Additional Instructions (Optional)</label>', unsafe_allow_html=True)
        instructions = st.text_area(
            "Add specific style notes, topics to focus on, etc.", # Hidden label
            placeholder="Example: Focus on financial implications. Use an enthusiastic tone.",
            height=100,
            key="podcast_instructions",
            disabled=not utils_found,
            label_visibility="collapsed"
        )

        # --- Reset Button ---
        show_reset = st.session_state.newsletter_text or st.session_state.podcast_script or st.session_state.audio_file_path or st.session_state.last_error
        if show_reset:
            if st.button("🔄 Clear & Start Over", key="reset_button", use_container_width=True):
                reset_app_state()
                st.rerun()


# --- Processing & Output Column (col2) ---
with col2:
     with st.container(): # Wrap outputs in a container for styling
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
                st.empty() # Placeholder to show spinner while processing happens on next run

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


