import logging
from markitdown import MarkItDown

# Configure logging
logger = logging.getLogger(__name__)

def parse_doc_to_markdown(file_path: str) -> str:
    """
    Parse a document file (PDF, DOCX, PPTX, etc.) and convert it to Markdown content using MarkItDown.
    
    Args:
        file_path (str): The absolute path to the document file.
        
    Returns:
        str: The converted Markdown content.
        
    Raises:
        Exception: If the file cannot be parsed or found.
    """
    try:
        md = MarkItDown()
        result = md.convert(file_path)
        return result.text_content
    except Exception as e:
        logger.error(f"Error parsing document file {file_path}: {e}")
        raise
