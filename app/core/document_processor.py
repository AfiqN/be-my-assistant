import logging
from typing import List, Optional

import pypdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



def load_pdf_text(file_path: str) -> Optional[str]:
    """
    Loads text content from a PDF file.

    Args:
        file_path (str): The full path to the PDF file.

    Returns:
        Optional[str]: The extracted text content as a single string,
                       or None if the file cannot be read or contains no text.
    Raises:
        FileNotFoundError: If the specified file_path does not exist.
        Exception: For other potential issues during PDF processing.
    """
    logger.info(f"Attempting to load PDF from: {file_path}")
    all_text = []
    try:
        # Open the PDF file in binary read mode
        with open(file_path, "rb") as pdf_file:
            # Create a PDF reader object
            pdf_reader = pypdf.PdfReader(pdf_file)
            num_pages = len(pdf_reader.pages)
            logger.info(f"PDF loaded successfully. Number of pages: {num_pages}")

            # Iterate through each page and extract text
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:  # Ensure text was actually extracted
                        all_text.append(page_text)
                    else:
                        logger.warning(f"No text found on page {page_num + 1}")
                except Exception as page_exc:
                    logger.error(f"Error extracting text from page {page_num + 1}: {page_exc}")

            if not all_text:
                logger.warning(f"No text could be extracted from the PDF: {file_path}")
                return None

            # Join the text from all pages
            full_text = "\n".join(all_text) # Use newline as separator between pages
            logger.info(f"Successfully extracted text from PDF. Total length: {len(full_text)} characters.")
            return full_text

    except FileNotFoundError:
        logger.error(f"File not found at path: {file_path}")
        raise  # Re-raise the exception to be handled by the caller
    except pypdf.errors.PdfReadError as pdf_err:
        logger.error(f"Error reading PDF file {file_path}: {pdf_err}")
        # Depending on requirements, you might return None or raise a custom exception
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing PDF {file_path}: {e}")
        raise # Re-raise unexpected errors


def split_text_into_chunks(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100
) -> List[str]:
    """
    Splits a given text into smaller chunks using RecursiveCharacterTextSplitter.

    Args:
        text (str): The input text to be split.
        chunk_size (int): The maximum number of characters allowed in each chunk.
                          Defaults to 1000.
        chunk_overlap (int): The number of characters that overlap between consecutive chunks.
                             Helps maintain context. Defaults to 200.

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
        # Common separators tried in order by RecursiveCharacterTextSplitter:
        # ["\n\n", "\n", " ", ""]
    )

    # Perform the split operation
    chunks = text_splitter.split_text(text)

    logger.info(f"Text split into {len(chunks)} chunks.")
    # Optional: Log first few characters of the first chunk for verification
    if chunks:
        logger.debug(f"First chunk preview: '{chunks[0][:100]}...'")

    return chunks

# Example of how you might test this file directly (optional)
if __name__ == '__main__':
    # This block runs only when the script is executed directly (e.g., python app/core/document_processor.py)
    # It's useful for quick tests but formal testing should be done via test scripts/frameworks.

    # IMPORTANT: Create a dummy PDF file named 'sample.pdf' in the root directory
    # or change the path below to an existing PDF file for this test to work.
    test_pdf_path = 'sample.pdf' # Adjust path as needed

    try:
        print(f"--- Testing PDF Loading ---")
        extracted_text = load_pdf_text(test_pdf_path)

        if extracted_text:
            print(f"Successfully loaded text. Length: {len(extracted_text)} chars.")
            # print("\n--- First 500 Chars ---")
            # print(extracted_text[:500])
            # print("\n...")

            print("\n--- Testing Text Splitting ---")
            text_chunks = split_text_into_chunks(extracted_text, chunk_size=500, chunk_overlap=50)
            print(f"Text split into {len(text_chunks)} chunks.")

            if text_chunks:
                print("\n--- First Chunk ---")
                print(text_chunks[0])
                print("\n--- Second Chunk (if exists) ---")
                if len(text_chunks) > 1:
                    print(text_chunks[1])
                else:
                    print("Only one chunk was created.")
        else:
            print("Could not extract text from the PDF or PDF was empty.")

    except FileNotFoundError:
        print(f"ERROR: Test PDF file not found at '{test_pdf_path}'. Please create it or change the path.")
    except Exception as e:
        print(f"An error occurred during testing: {e}")