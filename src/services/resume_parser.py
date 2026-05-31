import fitz  # PyMuPDF
from typing import Any

class ResumeParsingError(Exception):
    """Custom exception raised when resume parsing fails due to formatting, corruption, or empty content."""
    pass

class ResumeParserService:
    """
    Service responsible for extracting plain text from PDF resumes.
    Decoupled from any framework or UI dependencies to ensure testability.
    """

    @staticmethod
    def extract_text_from_bytes(pdf_bytes: bytes) -> str:
        """
        Extracts raw text from a PDF file provided as bytes.

        Args:
            pdf_bytes (bytes): The raw binary content of the PDF file.

        Returns:
            str: The extracted and cleaned plain text from the PDF.

        Raises:
            ResumeParsingError: If the PDF is empty, corrupted, or has no extractable text.
        """
        # Edge Case: Check if file bytes are completely empty
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise ResumeParsingError("The uploaded file is empty.")

        try:
            # Load PDF directly from the byte stream
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            # Handle corrupted or invalid PDF structures
            raise ResumeParsingError(
                f"Failed to open the PDF. The file may be corrupted or invalid. Details: {str(e)}"
            )

        extracted_text = []

        try:
            # Iterate through each page of the document
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                page_text = page.get_text()
                if page_text:
                    extracted_text.append(page_text)
        except Exception as e:
            raise ResumeParsingError(
                f"An error occurred while reading page content from the PDF. Details: {str(e)}"
            )
        finally:
            # Ensure document is closed to release system resources
            pdf_document.close()

        # Combine text from all pages and strip leading/trailing whitespace
        full_text = "\n".join(extracted_text).strip()

        # Edge Case: Check if the text is empty (e.g. if the PDF only contains images)
        if not full_text:
            raise ResumeParsingError(
                "No readable text was found in the PDF. "
                "The document might be empty or contain only scanned images (OCR required)."
            )

        return full_text
