# Standard library imports
import os
import base64
import time
import tempfile
import logging

# Third-party imports
import openai
import PyPDF2
from docx import Document

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GenAI:
    """
    A class for interacting with the OpenAI API to generate text,
    perform text-to-speech, and handle basic document processing tasks.

    Attributes:
    ----------
    client : openai.Client
        An instance of the OpenAI client initialized with the API key.
    openai_api_key : str
        The OpenAI API key.
    """
    def __init__(self, openai_api_key):
        """
        Initializes the GenAI class with the provided OpenAI API key.

        Parameters:
        ----------
        openai_api_key : str
            The API key for accessing OpenAI's services.
        """
        if not openai_api_key:
            raise ValueError("OpenAI API key is required.")
        self.client = openai.Client(api_key=openai_api_key)
        self.openai_api_key = openai_api_key
        logging.info("GenAI client initialized.")

    def generate_text(self, prompt, instructions='You are a helpful AI podcast generator.', model="gpt-4o", output_type='text', temperature=0.7):
        """
        Generates a text completion using the OpenAI API.

        Parameters:
        ----------
        prompt : str
            The user input or query for the AI.
        instructions : str, optional
            System-level instructions for the AI's behavior.
        model : str, optional
            The OpenAI model to use.
        output_type : str, optional
            The format of the output (currently only 'text' supported effectively here).
        temperature : float, optional
            Controls randomness in the generation.

        Returns:
        -------
        str
            The AI-generated response as a string.

        Raises:
        ------
        openai.APIError
            If there is an issue with the OpenAI API call.
        """
        logging.info(f"Generating text with model {model} and temperature {temperature}.")
        try:
            completion = self.client.chat.completions.create(
                model=model,
                temperature=temperature,
                # response_format={"type": output_type}, # May cause issues depending on model/output
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": prompt}
                ]
            )
            response = completion.choices[0].message.content
            logging.info("Text generation successful.")
            # Basic cleaning, might need refinement
            response = response.replace("```json", "").replace("```", "").strip()
            return response
        except openai.APIError as e:
            logging.error(f"OpenAI API error during text generation: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error during text generation: {e}")
            raise

    def generate_audio(self, text, file_path, model='tts-1', voice='nova', speed=1.0):
        """
        Generates an audio file from text using OpenAI's TTS model.

        Parameters
        ----------
        text : str
            The input text to convert into speech.
        file_path : str
            The output file path for the generated audio (e.g., 'podcast.mp3').
        model : str, optional
            The OpenAI TTS model (e.g., 'tts-1', 'tts-1-hd').
        voice : str, optional
            The voice to use ('alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer').
        speed : float, optional
            Speech speed multiplier (0.25 to 4.0).

        Returns
        -------
        bool
            True if audio generation is successful.

        Raises:
        ------
        openai.APIError
            If there is an issue with the OpenAI API call.
        ValueError
            If the speed parameter is outside the valid range.
        """
        if not (0.25 <= speed <= 4.0):
            raise ValueError("Speed must be between 0.25 and 4.0")

        logging.info(f"Generating audio with model {model}, voice {voice}, speed {speed}.")
        try:
            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                speed=speed
            )
            # Stream the audio content to the specified file
            response.stream_to_file(file_path)
            logging.info(f"Audio successfully generated and saved to {file_path}.")
            return True
        except openai.APIError as e:
            logging.error(f"OpenAI API error during audio generation: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error during audio generation: {e}")
            raise

    def read_text_file(self, file_path):
        """Reads content from a plain text file."""
        logging.info(f"Reading text file: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logging.error(f"Error reading text file {file_path}: {e}")
            raise

    def read_pdf(self, file_path):
        """Reads text content from a PDF file."""
        logging.info(f"Reading PDF file: {file_path}")
        text = ""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n" # Add newline between pages
            logging.info(f"Successfully read {len(reader.pages)} pages from PDF: {file_path}")
            return text
        except Exception as e:
            logging.error(f"Error reading PDF file {file_path}: {e}")
            raise

    def read_docx(self, file_path):
        """Reads text content from a DOCX file."""
        logging.info(f"Reading DOCX file: {file_path}")
        try:
            doc = Document(file_path)
            full_text = [para.text for para in doc.paragraphs]
            logging.info(f"Successfully read DOCX file: {file_path}")
            return '\n'.join(full_text)
        except Exception as e:
            logging.error(f"Error reading DOCX file {file_path}: {e}")
            raise

