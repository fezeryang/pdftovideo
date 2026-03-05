"""PDF extraction module using PyMuPDF (fitz)."""

import logging
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF
logger = logging.getLogger(__name__)

class PDFExtractionError(Exception):
    """Custom exception for PDF extraction errors."""
    pass


def extract_text(pdf_path: str) -> str:
    """
    Extract text from all pages of a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text from all pages concatenated together
        
    Raises:
        PDFExtractionError: If PDF cannot be opened or is corrupted
        FileNotFoundError: If PDF file does not exist
    """
    path = Path(pdf_path)
    logger.debug("Attempting to extract text from PDF: %s", pdf_path)
    
    if not path.exists():
        logger.error("PDF file not found: %s", pdf_path)
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if not path.is_file():
        logger.error("Path is not a file: %s", pdf_path)
        raise PDFExtractionError(f"Path is not a file: {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        logger.info("Opened PDF with %d pages: %s", page_count, pdf_path)
    except Exception as e:
        logger.error("Failed to open PDF '%s': %s", pdf_path, e)
        raise PDFExtractionError(f"Failed to open PDF: {e}")
    
    try:
        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_parts.append(page.get_text())
            logger.debug("Extracted text from page %d/%d", page_num + 1, len(doc))
        
        total_chars = sum(len(p) for p in text_parts)
        logger.info("Extracted %d characters from %d pages", total_chars, len(doc))
        return "\n".join(text_parts)
    
    except Exception as e:
        logger.error("Failed to extract text from PDF '%s': %s", pdf_path, e)
        raise PDFExtractionError(f"Failed to extract text from PDF: {e}")
    
    finally:
        doc.close()


def extract_images(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract images from all pages of a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of dictionaries containing image data with keys:
        - 'page': Page number (0-indexed)
        - 'xref': Image reference number
        - 'width': Image width in pixels
        - 'height': Image height in pixels
        - 'image_data': Raw image bytes
        - 'ext': Image file extension (e.g., 'png', 'jpeg')
        
    Raises:
        PDFExtractionError: If PDF cannot be opened or is corrupted
        FileNotFoundError: If PDF file does not exist
    """
    path = Path(pdf_path)
    logger.debug("Attempting to extract images from PDF: %s", pdf_path)
    
    if not path.exists():
        logger.error("PDF file not found: %s", pdf_path)
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if not path.is_file():
        logger.error("Path is not a file: %s", pdf_path)
        raise PDFExtractionError(f"Path is not a file: {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        logger.info("Opened PDF with %d pages for image extraction: %s", page_count, pdf_path)
    except Exception as e:
        logger.error("Failed to open PDF '%s': %s", pdf_path, e)
        raise PDFExtractionError(f"Failed to open PDF: {e}")
    
    try:
        images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            logger.debug("Found %d images on page %d/%d", len(image_list), page_num + 1, len(doc))
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                
                try:
                    base_image = doc.extract_image(xref)
                    
                    images.append({
                        'page': page_num,
                        'xref': xref,
                        'width': base_image['width'],
                        'height': base_image['height'],
                        'image_data': base_image['image'],
                        'ext': base_image['ext']
                    })
                except Exception as e:
                    # Skip individual images that fail to extract
                    # but continue processing other images
                    logger.warning("Failed to extract image %d on page %d: %s", img_index + 1, page_num + 1, e)
                    continue
        
        logger.info("Extracted %d images from %d pages", len(images), len(doc))
        return images
        
    
    except Exception as e:
        logger.error("Failed to extract images from PDF '%s': %s", pdf_path, e)
        raise PDFExtractionError(f"Failed to extract images from PDF: {e}")
    
    finally:
        doc.close()
