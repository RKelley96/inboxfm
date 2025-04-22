# app.py
import streamlit as st
import os
import tempfile
import uuid
from pathlib import Path
import time
import traceback # For displaying detailed errors if needed

# --- Attempt to import utility functions ---
try:
    # Check explicitly if utils.py exists before trying to import
    if not os.path.exists("utils.py"):
        utils_found = False
        # No need to raise FileNotFoundError here, just set flag
    else:
        # Import the new combined function and the file reader
        from utils import read_uploaded_files, generate_script_and_audio
        utils_found = True
except ImportError as import_err:
    utils_found = False
    # Define dummy functions if utils.py exists but functions are missing
    def read_uploaded_files(files):
        st.error(f"Import Error: {import_err}. `read_uploaded_files` is missing from utils.py.")
        raise NotImplementedError("`read_uploaded_files` is not implemented in utils.py.")
    def generate_script_and_audio(texts, instructions, audio_path, voice):
        st.error(f"Import Error: {import_err}. `generate_script_and_audio` is missing from utils.py.")
        raise NotImplementedError("`generate_script_and_audio` is not implemented or utils.py is missing.")
        # return None, None # Match expected return signature

# --- Page Configuration ---
st.set_page_config(
    page_title="Inbox.fm: Your Personal Newsletter Podcast",
    page_icon="🎙️",
    layout="wide"
)

# --- Custom CSS Styling ---
# Using the improved CSS from the previous app.py version
st.markdown("""
<style>
    /* General Styling */
    body {
        font-family: sans-serif;
    }
    .main-header {
        font-size: 2.8rem; /* Slightly larger */
        font-weight: 600; /* Bolder */
        color: #1a5276; /* Dark blue */
        margin-bottom: 0.5rem;
        text-align: center; /* Center header */
        padding-top: 1rem;
    }
    .sub-header {
        font-size: 1.3rem;
        font-weight: 400; /* Normal weight */
        color: #566573; /* Medium grey-blue */
        margin-bottom: 2rem; /* More space below sub-header */
        text-align: center;
    }
    .section-header {
        font-size: 1.6rem; /* Slightly larger section headers */
        font-weight: 600;
        color: #117a65; /* Darker teal */
        margin-top: 2.5rem; /* More space above sections */
        margin-bottom: 1.2rem;
        border-bottom: 3px solid #16a085; /* Thicker border */
        padding-bottom: 0.5rem;
    }
    .info-text {
        font-size: 1rem;
        color: #566573; /* Match sub-header color */
        margin-bottom: 1rem;
        line-height: 1.6; /* Improve readability */
    }

    /* Button Styling */
    .stButton>button {
        background-color: #16a085; /* Teal */
        color: white;
        font-weight: bold;
        border-radius: 8px; /* More rounded corners */
        padding: 0.7rem 1.5rem; /* Larger padding for main button */
        border: none;
        transition: background-color 0.3s ease; /* Smooth hover effect */
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); /* Subtle shadow */
        width: 100%; /* Make generate button full width */
        margin-top: 1rem; /* Space above button */
    }
    .stButton>button:hover {
        background-color: #117a65; /* Darker teal on hover */
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .stButton>button:disabled {
        background-color: #aed6f1; /* Lighter blue when disabled */
        color: #eaf2f8;
        cursor: not-allowed;
        box-shadow: none;
    }

    /* Download Button Specifics */
    .stDownloadButton>button {
        background-color: #2e86c1; /* Primary blue */
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        border: none;
        transition: background-color 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        width: 100%; /* Make download button full width */
        margin-top: 1rem; /* Add space above download button */
    }
    .stDownloadButton>button:hover {
        background-color: #21618c; /* Darker blue on hover */
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }

    /* Success/Info/Error Messages */
    .success-text {
        color: #1e8449; /* Darker green */
        background-color: #e8f8f5;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 6px solid #2ecc71; /* Thicker green border */
        font-weight: 500;
    }
    .stAlert { /* Style Streamlit's default info/warning/error boxes */
        border-radius: 8px;
        font-size: 0.95rem;
    }
    .stAlert strong { /* Make bold text in alerts stand out */
         font-weight: 600;
    }

    /* Spinner */
    .stSpinner > div > div {
         border-top-color: #16a085 !important; /* Teal spinner */
         border-right-color: #16a085 !important;
         border-width: 4px !important; /* Make spinner thicker */
         width: 40px !important; /* Make spinner larger */
         height: 40px !important;
    }

    /* Layout Adjustments */
    .stTextArea textarea { /* Style text areas */
        border-radius: 8px;
        border: 1px solid #d5dbdb; /* Light grey border */
        background-color: #fdfefe; /* Slightly off-white background */
        font-family: monospace; /* Use monospace for script */
        font-size: 0.9rem;
    }
    .stSelectbox div[data-baseweb="select"] > div { /* Style select box */
        border-radius: 8px;
        border: 1px solid #d5dbdb;
    }
    .stFileUploader label { /* Style file uploader */
        border-radius: 8px;
        border: 2px dashed #aed6f1; /* Dashed border */
        background-color: #f4f6f7; /* Very light grey background */
    }
    .stFileUploader label:hover {
        border-color: #2e86c1; /* Blue border on hover */
        background-color: #eaf2f8;
    }
    /* Expander styling */
    .stExpander {
        border: 1px solid #d5dbdb;
        border-radius: 8px;
        background-color: #fdfefe;
        margin-top: 1rem;
    }
    .stExpander header {
        font-weight: 600;
        color: #1a5276;
    }

</style>
""", unsafe_allow_html=True)


# --- Session State Initialization ---
# Use consistent naming scheme
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp(prefix=f"inboxfm_{uuid.uuid4()}_")
if 'newsletter_text' not in st.session_state:
    st.session_state.newsletter_text = None
if 'podcast_script' not in st.session_state:
    st.session_state.podcast_script = None
if 'audio_file_path' not in st.session_state:
    st.session_state.audio_file_path = None
if 'is_processing' not in st.session_state: # Single processing flag
    st.session_state.is_processing = False
if 'last_error' not in st.session_state:
    st.session_state.last_error = None
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'upload_key' not in st.session_state: # To force re-run on new uploads
    st.session_state.upload_key = 0
if 'selected_voice' not in st.session_state: # Store voice selection reliably
    st.session_state.selected_voice = "nova"


# --- Helper Functions ---
def reset_app_state():
    """Resets the session state variables related to a processing run."""
    print("--- app.py: Resetting application state. ---")
    st.session_state.newsletter_text = None
    st.session_state.podcast_script = None
    st.session_state.audio_file_path = None
    st.session_state.is_processing = False
    st.session_state.last_error = None
    st.session_state.session_id = str(uuid.uuid4()) # New ID for next potential run
    st.session_state.upload_key += 1 # Change uploader key to clear it
    # Keep temp_dir for the session

# --- App Header ---
st.markdown('<div class="main-header">Inbox.fm 🎙️</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Turn your newsletters into personalized podcasts.</div>', unsafe_allow_html=True)
st.markdown('<div class="info-text" style="text-align: center; max-width: 700px; margin: auto; margin-bottom: 2rem;">Upload your newsletters, provide instructions, choose a voice, and get a custom audio digest powered by AI.</div>', unsafe_allow_html=True)

# Display warning prominently if utils.py or its functions are missing/broken
if not utils_found:
    st.error("🚨 **Critical Setup Error:** `utils.py` could not be found or is missing required functions. Please ensure `utils.py` and `genai.py` are in the same directory as `app.py` and contain the necessary code. Core functionality is disabled.", icon="⚙️")

# --- Main Layout Columns ---
col1, col2 = st.columns([3, 2]) # Give input column slightly more space

with col1:
    # --- Step 1: Upload Newsletters ---
    st.markdown('<div class="section-header">Step 1: Upload Newsletters</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Upload your newsletter files (.txt, .pdf, .docx)",
        type=["txt", "pdf", "docx"],
        accept_multiple_files=True,
        # Use the counter in the key to force refresh when reset
        key=f"newsletter_uploader_{st.session_state.upload_key}",
        disabled=not utils_found # Disable if utils can't be loaded/found
    )

    # Process files only if they are newly uploaded (check against key change indirectly)
    if uploaded_files and st.session_state.newsletter_text is None and not st.session_state.is_processing:
         if utils_found:
            try:
                with st.spinner("Reading uploaded files... This might take a moment for PDFs."):
                    # Clear previous errors before processing
                    st.session_state.last_error = None
                    # Call the function from utils.py
                    extracted_text = read_uploaded_files(uploaded_files)
                    st.session_state.newsletter_text = extracted_text # Store result

                    if extracted_text is not None and extracted_text.strip() != "":
                         st.success(f"✅ Successfully processed {len(uploaded_files)} file(s). Ready for Step 2.")
                    else:
                         # Handle case where read_uploaded_files returns None or empty string
                         st.warning("⚠️ Could not extract text from any uploaded files, or files were empty. Please check file formats and content, or try different files.")
                         st.session_state.newsletter_text = None # Ensure it's None if no text

            except NotImplementedError as nie:
                 st.error(f"Setup Error: {nie}")
                 st.session_state.last_error = f"Setup Error: {nie}"
                 st.session_state.newsletter_text = None # Ensure state is reset
            except Exception as e:
                st.error(f"An unexpected error occurred while reading files: {e}")
                st.session_state.last_error = f"File Reading Error: {e}"
                st.session_state.newsletter_text = None
                # traceback.print_exc() # Uncomment for server-side debug logs
            # No rerun here, let Streamlit handle UI update naturally

    # --- Step 2: Podcast Instructions & Voice Selection ---
    st.markdown('<div class="section-header">Step 2: Customize Your Podcast</div>', unsafe_allow_html=True)
    instructions = st.text_area(
        "Podcast Instructions (Optional: Specify desired length e.g., '5 minutes'):",
        placeholder="Example: Create a concise, 5-minute summary focusing on the key takeaways for a tech professional. Make connections between the different newsletters. Use an upbeat, conversational tone.",
        height=120, # Slightly smaller height
        key="podcast_instructions",
        disabled=not utils_found
    )

    voice_options = ["nova", "alloy", "echo", "fable", "onyx", "shimmer", "ash", "ballad", "coral", "sage"]
    # Use the stored voice selection for consistency across reruns
    # Update the session state directly on change
    st.selectbox(
        "Select AI Voice:",
        options=voice_options,
        index=voice_options.index(st.session_state.selected_voice), # Use stored value
        key="voice_selector_widget", # Use a distinct key for the widget
        on_change=lambda: st.session_state.update(selected_voice=st.session_state.voice_selector_widget), # Update stored value on change
        disabled=not utils_found
    )


    # --- Step 3: Generate Podcast ---
    st.markdown('<div class="section-header">Step 3: Generate Podcast</div>', unsafe_allow_html=True)
    # Enable button only if utils are found, files were successfully read (content exists), and not currently processing
    can_generate = utils_found and st.session_state.newsletter_text and not st.session_state.is_processing
    if st.button("🚀 Generate Podcast (Script & Audio)", key="generate_podcast_button", disabled=not can_generate, use_container_width=True):
        if not st.session_state.newsletter_text:
            st.warning("Please upload and successfully process newsletter files first.")
        # Instructions are optional now, but we still need the variable
        current_instructions = st.session_state.get("podcast_instructions", "") # Get instructions text
        print("--- app.py: Generate Podcast button clicked. ---")
        st.session_state.is_processing = True
        st.session_state.last_error = None
        st.session_state.podcast_script = None # Clear previous results
        st.session_state.audio_file_path = None
        st.rerun() # Rerun to show spinner

# Handle combined script and audio generation if triggered
if st.session_state.is_processing:
     with col1:
         # Display spinner within the column where the action was triggered
         with st.spinner("Generating podcast script and audio... This may take several moments..."):
             try:
                 print("--- app.py: Now calling generate_script_and_audio in utils... ---")
                 current_instructions = st.session_state.get("podcast_instructions", "")
                 voice_to_use = st.session_state.selected_voice # Get selected voice

                 # Define the output path for the audio file
                 audio_filename = f"inboxfm_podcast_{st.session_state.session_id}.mp3"
                 # Ensure temp_dir exists (it should, but check defensively)
                 if not os.path.exists(st.session_state.temp_dir):
                     os.makedirs(st.session_state.temp_dir)
                 output_audio_path = os.path.join(st.session_state.temp_dir, audio_filename)

                 # Call the combined function from utils
                 script, audio_path = generate_script_and_audio(
                     st.session_state.newsletter_text,
                     current_instructions,
                     output_audio_path,
                     voice_to_use
                 )
                 print("--- app.py: generate_script_and_audio function returned. ---") # Log return

                 # Update state based on results
                 st.session_state.podcast_script = script
                 st.session_state.audio_file_path = audio_path # Will be None if audio failed or file missing

                 st.session_state.is_processing = False # Done processing

                 if script and audio_path:
                     st.success("✅ Podcast script and audio generated successfully!")
                 elif script and not audio_path:
                     st.warning("⚠️ Script generated, but audio generation failed. Check logs.")
                     st.session_state.last_error = "Audio generation failed after script creation."
                 elif not script:
                     st.error("❌ Failed to generate podcast script. Cannot proceed to audio.")
                     st.session_state.last_error = "Script generation failed."
                 else: # Should not happen if logic is correct, but catch all
                      st.error("❌ An unexpected issue occurred during generation.")
                      st.session_state.last_error = "Unknown generation error."

                 st.rerun() # Rerun to update UI state (remove spinner, show results)

             except NotImplementedError as nie:
                 st.error(f"Setup Error: {nie}")
                 st.session_state.last_error = f"Setup Error: {nie}"
                 st.session_state.is_processing = False
                 st.rerun()
             except ConnectionError as ce: # Catch specific error from utils
                 st.error(f"Connection Error: {ce}. Could not connect to AI service. Please check your API key and network connection.")
                 st.session_state.last_error = f"Connection Error: {ce}"
                 st.session_state.is_processing = False
                 st.rerun()
             except Exception as e:
                 st.error(f"An unexpected error occurred during generation: {e}")
                 st.session_state.last_error = f"Generation Error: {e}"
                 st.session_state.is_processing = False
                 # traceback.print_exc() # Uncomment for server-side debug logs
                 st.rerun()


# --- Output Section (Column 2) ---
with col2:
    st.markdown('<div class="section-header">Your Podcast</div>', unsafe_allow_html=True)

    # Display any errors that occurred during processing
    if st.session_state.last_error and not st.session_state.is_processing: # Show error only when not processing
        st.error(f"⚠️ **Error:** {st.session_state.last_error}")

    # Guidance text if nothing has been generated yet and no error shown
    if not st.session_state.podcast_script and not st.session_state.audio_file_path and not st.session_state.is_processing and not st.session_state.last_error:
         st.info("Follow the steps on the left to generate your podcast." if utils_found else "⚙️ Application setup incomplete. Please check `utils.py` and `genai.py` files.")

    # Display audio player and download button if audio exists
    if st.session_state.audio_file_path and os.path.exists(st.session_state.audio_file_path):
        st.markdown('<div class="success-text">✅ Your podcast is ready! Listen below or download the MP3.</div>', unsafe_allow_html=True)
        try:
             # Display audio player - Reading bytes might be more robust for temp files
             with open(st.session_state.audio_file_path, "rb") as audio_file:
                 audio_bytes = audio_file.read()
             st.audio(audio_bytes, format="audio/mp3")

             # Provide download button using the same bytes
             st.download_button(
                 label="⬇️ Download Podcast (.mp3)",
                 data=audio_bytes, # Use bytes directly
                 file_name=f"Inbox.fm_Podcast_{time.strftime('%Y%m%d_%H%M%S')}.mp3",
                 mime="audio/mp3",
                 key="download_button",
                 use_container_width=True # Make button full width
             )
        except FileNotFoundError:
             st.error("Error: Could not find the generated audio file for playback or download. It might have been cleaned up. Please try generating again.")
             st.session_state.audio_file_path = None # Reset path if file is missing
             st.session_state.last_error = "Audio file missing after generation."
             # Add a button to clear the missing state without rerunning immediately
             if st.button("Acknowledge Missing Audio", key="ack_missing_audio"):
                 st.session_state.last_error = None # Clear error on acknowledge
                 st.rerun()
        except Exception as e:
             st.error(f"An unexpected error occurred while preparing the audio player/download: {e}")
             st.session_state.audio_file_path = None # Reset path on error
             st.session_state.last_error = f"Audio display/download error: {e}"


    elif st.session_state.audio_file_path and not os.path.exists(st.session_state.audio_file_path):
        # If the path exists in state but the file doesn't (e.g., due to cleanup)
        st.warning("The previously generated audio file seems to be missing. Please generate it again.")
        # Don't reset audio path here, let user trigger reset or new generation
        # Add a button to clear the missing state without rerunning immediately
        if st.button("Acknowledge Missing Audio", key="ack_missing_audio_warn"):
             st.session_state.audio_file_path = None # Clear path on acknowledge
             st.session_state.last_error = None
             st.rerun()

    # Display script in an expander if it exists
    if st.session_state.podcast_script:
         with st.expander("📄 View Generated Script", expanded=False):
              st.text_area("Script:", value=st.session_state.podcast_script, height=300, key="script_display", disabled=True)


# --- Reset Button ---
st.divider() # Use st.divider() for a visual separator
# Show reset button if there's any state to clear or if there's an error displayed
show_reset = st.session_state.newsletter_text or st.session_state.podcast_script or st.session_state.audio_file_path or st.session_state.last_error
if show_reset:
    # Place reset button in the first column for better layout consistency
    with col1:
        if st.button("🔄 Start Over / Clear All", key="reset_button", use_container_width=True):
            reset_app_state()
            st.rerun()

# --- Footer ---
st.markdown("---")
st.markdown('<div class="info-text" style="text-align: center; font-size: 0.9rem;">Inbox.fm - Powered by AI</div>', unsafe_allow_html=True)

# Note: Robust temporary file cleanup often requires external mechanisms
# or careful handling within the session logic, especially for long-running apps.
# The tempfile module's directory might persist until the Python process ends.
