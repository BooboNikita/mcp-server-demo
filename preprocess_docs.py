import os
import sys
import logging
import argparse

# Add src to path to allow imports
sys.path.append(os.path.join(os.getcwd(), 'src'))

from utils import parse_doc_to_markdown

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_file(file_path: str):
    """
    Process a single file and convert it to Markdown.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found at: {file_path}")
        return

    # Determine output path
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = os.path.dirname(file_path)
    output_path = os.path.join(output_dir, f"{base_name}.md")

    try:
        logger.info(f"Starting to parse document: {file_path}")
        markdown_content = parse_doc_to_markdown(file_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        logger.info(f"Successfully converted document to Markdown.")
        logger.info(f"Output saved to: {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to process document {file_path}: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Convert documents to Markdown using MarkItDown.")
    parser.add_argument("files", nargs='+', help="Path to the file(s) to process")
    
    args = parser.parse_args()

    for file_path in args.files:
        # Resolve absolute path
        abs_path = os.path.abspath(file_path)
        process_file(abs_path)

if __name__ == "__main__":
    main()
