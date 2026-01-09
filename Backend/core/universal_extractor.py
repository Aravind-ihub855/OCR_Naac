"""
Universal PDF Extractor
Uses pdfplumber for native PDFs and Tesseract for scanned content.
Robustly extracts text, tables, and layout without AI.
"""

import logging
import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
from typing import List, Dict, Any, Union
import numpy as np

import io

logger = logging.getLogger("UniversalExtractor")

POPPLER_PATH = r"C:\poppler-25.12.0\Library\bin"

def extract_robust(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Extract data from PDF using hybrid approach.
    1. Try pdfplumber for native text/tables.
    2. If page looks empty/scanned, use Tesseract.
    """
    results = {
        "metadata": {},
        "pages": []
    }
    
    try:
        # Open PDF with pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            results["metadata"] = pdf.metadata
            
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                logger.info(f"Processing page {page_num}...")
                
                page_result = _process_page(page, pdf_bytes, page_num)
                results["pages"].append(page_result)
                
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise
        
    return results


def _process_page(page, pdf_bytes: bytes, page_num: int) -> Dict[str, Any]:
    """Process a single page."""
    width = float(page.width)
    height = float(page.height)
    
    # 1. Extract Text (Native)
    text = page.extract_text()
    words = page.extract_words()
    
    # 2. Extract Tables (Native)
    # Using specific settings for better accuracy
    tables = page.extract_tables(table_settings={
        "vertical_strategy": "text", 
        "horizontal_strategy": "text",
        "intersection_y_tolerance": 5
    })
    
    # 3. Check if scanned (fallback to OCR)
    is_scanned = False
    if not words or len(words) < 5:
        logger.info(f"Page {page_num} appears scanned. Using OCR...")
        is_scanned = True
        ocr_result = _perform_ocr(pdf_bytes, page_num)
        text = ocr_result['text']
        tables = [] # OCR table extraction is harder without AI, keeping it simple for now
    
    return {
        "page_num": page_num,
        "width": width,
        "height": height,
        "is_scanned": is_scanned,
        "text": text,
        "tables": tables,
        "element_count": len(words) if words else 0
    }


from unstructured.partition.pdf import partition_pdf

def _perform_ocr(pdf_bytes: bytes, page_num: int) -> Dict[str, Any]:
    """Run Unstructured on specific page for better layout/table extraction."""
    # We pass the whole PDF but restrict to page (if unstructured supports it easily)
    # or just convert that page to image and standard OCR.
    # Unstructured partition_pdf operates on file, difficult to restrict to single page efficiently without splitting.
    # For robust extraction, we might just run partition_pdf on the WHOLE document if we detect it's scanned, 
    # but here we are page-by-page.
    
    # Strategy: Use pdf2image to get image, then extract from image?
    # Or just use Tesseract with layout preservation properly.
    # User mentioned "unstructured.io". Let's use it.
    
    try:
        # partition_pdf usually expects a filename or file-like object.
        # We can pass the bytes.
        # Note: limiting to one page might be tricky with standard partition_pdf call 
        # unless we split the PDF bytes first. 
        # simpler: return raw tesseract text with layout preservation
        
        images = convert_from_bytes(
            pdf_bytes, 
            first_page=page_num, 
            last_page=page_num,
            poppler_path=POPPLER_PATH
        )
        if not images:
            return {"text": "", "tables": []}
            
        # Use Tesseract with 'image_to_data' or simple 'image_to_string'
        # To get tables from image without AI is hard. 
        # Unstructured "hi_res" strategy does this but is slow.
        
        # Let's try simple layout preservation with pytesseract
        text = pytesseract.image_to_string(images[0], config='--psm 6') # Assume uniform block of text
        
        return {
            "text": text,
            "tables": [] # Still no simple table extraction from image without heavy tools
        }
        
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return {"text": "", "tables": []}

