import logging
from typing import List, Optional, Tuple
import mimetypes # To guess file type
import io # To handle byte streams for docx
import os

import pypdf
import docx # For .docx files
import markdown # For .md files
import requests # For fetching URLs
from bs4 import BeautifulSoup # For parsing HTML/MD
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



def load_pdf_text(file_path_or_stream: io.BytesIO) -> Optional[str]:
    """Loads text content from a PDF file path or a byte stream."""
    logger.info(f"Attempting to load PDF...")
    all_text = []
    try:
        pdf_reader = pypdf.PdfReader(file_path_or_stream)
        num_pages = len(pdf_reader.pages)
        logger.info(f"PDF loaded successfully. Number of pages: {num_pages}")

        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    all_text.append(page_text)
                else:
                    logger.warning(f"No text found on page {page_num + 1}")
            except Exception as page_exc:
                logger.error(f"Error extracting text from page {page_num + 1}: {page_exc}")

        if not all_text:
            logger.warning(f"No text could be extracted from the PDF.")
            return None

        full_text = "\n".join(all_text) # Keep page separation clear
        logger.info(f"Successfully extracted text from PDF. Total length: {len(full_text)} characters.")
        return full_text

    except pypdf.errors.PdfReadError as pdf_err:
        logger.error(f"Error reading PDF data: {pdf_err}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing PDF data: {e}")
        raise

def load_txt_text(file_path_or_stream: io.BytesIO) -> Optional[str]:
    """Loads text content from a TXT file path or a byte stream."""
    logger.info("Attempting to load TXT file...")
    try:
        # Assuming UTF-8 encoding, add error handling if needed
        content = file_path_or_stream.read().decode('utf-8', errors='replace')
        logger.info(f"Successfully loaded TXT file. Length: {len(content)} characters.")
        return content
    except Exception as e:
        logger.error(f"An error occurred while reading TXT data: {e}")
        return None
    
def load_docx_text(file_path_or_stream: io.BytesIO) -> Optional[str]:
    """Loads text content from a DOCX file path or a byte stream."""
    logger.info("Attempting to load DOCX file...")
    try:
        document = docx.Document(file_path_or_stream)
        full_text = [para.text for para in document.paragraphs]
        content = '\n'.join(full_text)
        logger.info(f"Successfully loaded DOCX file. Length: {len(content)} characters.")
        return content
    except Exception as e:
        logger.error(f"An error occurred while reading DOCX data: {e}")
        return None

def load_md_text(file_path_or_stream: io.BytesIO) -> Optional[str]:
    """Loads text content from a Markdown file path or a byte stream, converting to plain text."""
    logger.info("Attempting to load Markdown file...")
    try:
        md_content = file_path_or_stream.read().decode('utf-8', errors='replace')
        # Convert Markdown to HTML
        html = markdown.markdown(md_content)
        # Strip HTML tags to get plain text
        soup = BeautifulSoup(html, "html.parser")
        plain_text = soup.get_text(separator='\n', strip=True)
        logger.info(f"Successfully loaded and converted Markdown file. Length: {len(plain_text)} characters.")
        return plain_text
    except Exception as e:
        logger.error(f"An error occurred while reading or converting Markdown data: {e}")
        return None

def load_url_text(url: str) -> Optional[str]:
    """Fetches content from a URL and extracts plain text."""
    logger.info(f"Attempting to fetch and load content from URL: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'} # Basic user agent
        response = requests.get(url, headers=headers, timeout=15) # Added timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Use BeautifulSoup to parse HTML and extract text
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        # Get text, using newline as separator, and strip leading/trailing whitespace
        plain_text = soup.get_text(separator='\n', strip=True)

        if not plain_text:
            logger.warning(f"No significant text content found at URL: {url}")
            return None

        logger.info(f"Successfully fetched and extracted text from URL. Length: {len(plain_text)} characters.")
        return plain_text

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch URL {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"An error occurred processing URL {url}: {e}")
        return None
    
# --- Document Loading Dispatcher ---

LOADER_MAP = {
    "application/pdf": load_pdf_text,
    "text/plain": load_txt_text,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": load_docx_text,
    "text/markdown": load_md_text,
    "text/x-markdown": load_md_text, # Common alternative MIME type
}

def load_document(
    content_source: str, # Can be a file path or URL
    content_type: Optional[str] = None,
    file_stream: Optional[io.BytesIO] = None # Pass stream directly for uploads
    ) -> Optional[Tuple[str, str]]:
    """
    Loads text content from various sources (file path, URL, or stream).

    Args:
        content_source (str): The file path or URL.
        content_type (Optional[str]): The MIME type of the content, if known.
                                      Used for uploaded files.
        file_stream (Optional[io.BytesIO]): A byte stream of the file content.
                                           Takes precedence over reading from file path.

    Returns:
        Optional[Tuple[str, str]]: A tuple containing (extracted_text, source_identifier)
                                   where source_identifier is the filename or URL.
                                   Returns None if loading fails or source type is unsupported.
    """
    source_identifier = content_source # Default to path/URL
    text_content = None

    if content_source.startswith(('http://', 'https://')):
        logger.info(f"Detected URL source: {content_source}")
        text_content = load_url_text(content_source)
        source_identifier = content_source # Use URL as identifier

    elif file_stream:
        logger.info(f"Processing content from file stream for source: {content_source}")
        source_identifier = content_source # Use original filename passed as content_source
        if not content_type:
             # Try to guess type from filename if stream provided but type is missing
             guessed_type, _ = mimetypes.guess_type(source_identifier)
             content_type = guessed_type
             logger.info(f"Guessed content type from filename: {content_type}")

        loader_func = LOADER_MAP.get(content_type)
        if loader_func:
            text_content = loader_func(file_stream)
        else:
            logger.warning(f"Unsupported content type '{content_type}' for file stream: {source_identifier}")

    # Fallback: If not URL and no stream, assume it's a file path (less common in API context)
    elif os.path.exists(content_source):
         logger.warning(f"Processing content from file path (less common): {content_source}")
         source_identifier = os.path.basename(content_source)
         if not content_type:
             content_type, _ = mimetypes.guess_type(content_source)
             logger.info(f"Guessed content type from file path: {content_type}")

         loader_func = LOADER_MAP.get(content_type)
         if loader_func:
              try:
                  with open(content_source, "rb") as f:
                      text_content = loader_func(f)
              except FileNotFoundError:
                  logger.error(f"File not found at path: {content_source}")
              except Exception as e:
                  logger.error(f"Error opening/reading file path {content_source}: {e}")
         else:
              logger.warning(f"Unsupported content type '{content_type}' for file path: {content_source}")

    else:
         logger.error(f"Invalid content source or file not found: {content_source}")


    if text_content:
        return text_content, source_identifier
    else:
        logger.error(f"Failed to load or extract text from source: {source_identifier}")
        return None


# --- Text Splitting Function ---

def split_text_into_chunks(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 50   
) -> List[str]:
    """
    Splits a given text into smaller chunks using RecursiveCharacterTextSplitter.

    Args:
        text (str): The input text to be split.
        chunk_size (int): The maximum number of characters allowed in each chunk.
                          Defaults to 800.
        chunk_overlap (int): The number of characters that overlap between consecutive chunks.
                             Helps maintain context. Defaults to 100.

    Returns:
        List[str]: A list of text chunks (strings). Returns an empty list if input text is empty.
    """
    if not text:
        logger.warning("Input text for splitting is empty. Returning empty list.")
        return []

    logger.info(f"Splitting text into chunks. Chunk size: {chunk_size}, Overlap: {chunk_overlap}")

    # Initialize the text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len, # Function to measure chunk length (standard len for characters)
        is_separator_regex=False, # Treat separators literally
    )

    # Perform the split operation
    chunks = text_splitter.split_text(text)

    logger.info(f"Text split into {len(chunks)} chunks.")
    # Optional: Log first few characters of the first chunk for verification
    if chunks:
        logger.debug(f"First chunk preview: '{chunks[0][:100]}...'")

    return chunks