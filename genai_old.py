# genai.py
import os
import openai
import PyPDF2
from docx import Document # Corrected import for python-docx
from dotenv import load_dotenv
import time # Added for potential delays if needed
import traceback # For detailed error logging

class GenAI:
    """
    A class for interacting with the OpenAI API to generate text and audio,
    and handle basic document processing tasks for the Inbox.fm app.
    (Version 2 - Includes debugging prints)
    """
    def __init__(self):
        """
        Initializes the GenAI class, loads the OpenAI API key from environment variables.
        Raises ValueError if the API key is not found.
        """
        print("--- genai.py: Initializing GenAI ---") # DEBUG PRINT
        print("--- genai.py: Attempting to load .env file ---") # DEBUG PRINT
        try:
            # Load environment variables from .env file if it exists
            # Specify override=False if you don't want .env to override existing env vars
            load_dotenv(override=True)
            print("--- genai.py: load_dotenv() called ---") # DEBUG PRINT
        except Exception as load_err:
             print(f"--- genai.py: Error calling load_dotenv(): {load_err} ---") # DEBUG PRINT

        print("--- genai.py: Attempting to get OPENAI_API_KEY from environment ---") # DEBUG PRINT
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        if not self.openai_api_key:
            print("--- genai.py: ERROR - OPENAI_API_KEY not found in environment! ---") # DEBUG PRINT
            raise ValueError("OPENAI_API_KEY environment variable not found. Please set it in a .env file or your environment.")
        else:
            # Mask the key partially for logging, showing only first/last few chars
            masked_key = self.openai_api_key[:5] + "..." + self.openai_api_key[-4:]
            print(f"--- genai.py: Found OPENAI_API_KEY starting with {masked_key} ---") # DEBUG PRINT

        try:
            # Initialize the OpenAI client
            print("--- genai.py: Attempting to initialize OpenAI client ---") # DEBUG PRINT
            # The 'proxies' argument is typically handled via environment variables (HTTP_PROXY, HTTPS_PROXY)
            # or passed via http_client in newer versions if needed explicitly.
            # Do not pass 'proxies' directly to openai.Client() unless using a very old version or specific http_client setup.
            self.client = openai.Client(api_key=self.openai_api_key)
            # Optional: Test connection briefly (e.g., list models) - uncomment if needed
            # print("--- genai.py: Testing client connection (listing models)... ---")
            # self.client.models.list(limit=1)
            print("--- genai.py: OpenAI client initialized successfully. ---") # DEBUG PRINT
        except TypeError as te:
             # Catch the specific TypeError if 'proxies' or another unexpected arg is passed
             print(f"--- genai.py: TYPE ERROR initializing OpenAI client: {te} ---")
             print("--- genai.py: This might be due to an incompatible library version or unexpected arguments. ---")
             traceback.print_exc()
             raise ConnectionError(f"Failed to initialize OpenAI client due to TypeError: {te}")
        except Exception as e:
            print(f"--- genai.py: ERROR initializing OpenAI client: {e} ---") # DEBUG PRINT
            traceback.print_exc()
            # Re-raise a more specific error or handle as needed
            raise ConnectionError(f"Failed to initialize OpenAI client: {e}")


    def generate_text(self, prompt, instructions='You are a helpful AI assistant.', model="gpt-4o-mini", output_type='text', temperature=0.7, max_tokens=1500):
        """
        Generates text completion using the OpenAI API (suitable for podcast script).

        Parameters:
        ----------
        prompt : str
            The main content input (e.g., combined newsletter text).
        instructions : str, optional
            System-level instructions defining the AI's role, tone, output format.
        model : str, optional
            The OpenAI model to use.
        output_type : str, optional
            The desired output format (usually 'text').
        temperature : float, optional
             Controls randomness (0.0 to 2.0). Lower values are more focused.
        max_tokens : int, optional
             Maximum length of the generated response.

        Returns:
        -------
        str
            The AI-generated text response. Returns None if an error occurs.
        """
        if not prompt:
            print("--- genai.py: Warning - generate_text called with empty prompt. ---")
            return None

        try:
            print(f"--- genai.py: Generating text with model {model}... ---") # Log start
            completion = self.client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": output_type},
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": prompt}
                ]
            )
            response = completion.choices[0].message.content
            print("--- genai.py: Text generation successful. ---") # Log success
            # Basic cleaning (can be expanded)
            response = response.replace("```json", "").replace("```", "").strip() # Remove potential markdown code fences and trim whitespace
            return response
        except Exception as e:
            print(f"--- genai.py: ERROR during OpenAI text generation: {e} ---") # DEBUG PRINT
            traceback.print_exc() # Log detailed error
            # Optionally, re-raise the exception or handle it more gracefully
            # raise e # Uncomment to propagate the error
            return None # Indicate failure

    def generate_audio(self, text, file_path, model='tts-1', voice='nova', speed=1.0):
        """
        Generates an audio file from text using OpenAI's TTS model.

        Parameters
        ----------
        text : str
            Input text to convert to speech.
        file_path : str
            Output file path for the generated audio (e.g., 'podcast.mp3').
        model : str, optional
            The OpenAI TTS model. 'tts-1' is standard, 'tts-1-hd' for higher quality.
        voice : str, optional
            The voice to use (e.g., 'nova', 'alloy', 'echo', 'fable', 'onyx', 'shimmer').
        speed : float, optional
            Speech speed multiplier (0.25 to 4.0).

        Returns
        -------
        bool
            True if audio generation was successful, False otherwise.
        """
        if not text:
             print("--- genai.py: Error - Cannot generate audio from empty text. ---")
             return False
        try:
            print(f"--- genai.py: Generating audio with voice '{voice}' to {file_path}... ---") # Log start
            # Ensure speed is within the valid range
            speed = max(0.25, min(speed, 4.0))

            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                speed=speed
            )
            response.stream_to_file(file_path)
            print("--- genai.py: Audio generation successful. ---") # Log success
            return True # Indicate success
        except Exception as e:
            print(f"--- genai.py: ERROR during OpenAI audio generation: {e} ---") # DEBUG PRINT
            traceback.print_exc() # Log detailed error
            # Optionally, re-raise the exception
            # raise e # Uncomment to propagate the error
            return False # Indicate failure

    def read_pdf(self, file_path):
        """
        Extracts text content from a PDF file.

        Parameters:
        ----------
        file_path : str or file-like object
            Path to the PDF file or a file-like object.

        Returns:
        -------
        str
            Extracted text content. Returns an empty string if an error occurs or file not found.
        """
        text = ""
        file_identifier = getattr(file_path, 'name', file_path) # Get filename if available
        try:
            # PyPDF2 can read directly from file-like objects or paths
            reader = PyPDF2.PdfReader(file_path)
            print(f"--- genai.py: Reading PDF: {file_identifier} ---") # Log which file is being read
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text: # Check if text extraction returned something
                        text += page_text + "\n" # Add newline between pages
                    else:
                        print(f"--- genai.py: Warning - No text extracted from page {i+1} of {file_identifier} ---")
                except Exception as page_err:
                     print(f"--- genai.py: Error extracting text from page {i+1} of {file_identifier}: {page_err} ---")
            print(f"--- genai.py: Finished reading PDF: {file_identifier} ---")
            return text
        except FileNotFoundError:
            print(f"--- genai.py: ERROR - PDF file not found at {file_path} ---")
            return ""
        except PyPDF2.errors.PdfReadError as pdf_err:
             print(f"--- genai.py: ERROR reading PDF file {file_identifier} (possibly corrupted or password-protected): {pdf_err} ---")
             return ""
        except Exception as e:
            print(f"--- genai.py: UNEXPECTED ERROR reading PDF file {file_identifier}: {e} ---")
            traceback.print_exc() # Log detailed error
            return "" # Return empty string on error

    def read_docx(self, file_path):
        """
        Extracts text content from a DOCX file.

        Parameters:
        ----------
        file_path : str or file-like object
            Path to the DOCX file or a file-like object.

        Returns:
        -------
        str
            Extracted text content. Returns an empty string if an error occurs or file not found.
        """
        text_list = []
        file_identifier = getattr(file_path, 'name', file_path) # Get filename if available
        try:
            # python-docx can read directly from file-like objects or paths
            print(f"--- genai.py: Reading DOCX: {file_identifier} ---") # Log which file is being read
            doc = Document(file_path)
            for para in doc.paragraphs:
                if para.text: # Append only if paragraph has text
                     text_list.append(para.text)
            print(f"--- genai.py: Finished reading DOCX: {file_identifier} ---")
            return '\n'.join(text_list)
        except FileNotFoundError:
            print(f"--- genai.py: ERROR - DOCX file not found at {file_path} ---")
            return ""
        except Exception as e:
             # Catch potential errors from python-docx itself (e.g., bad format)
            print(f"--- genai.py: ERROR reading DOCX file {file_identifier}: {e} ---")
            traceback.print_exc() # Log detailed error
            return "" # Return empty string on error
