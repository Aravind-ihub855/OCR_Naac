"""
PDF Document Classifier - Layer 1

Analyzes PDF to determine:
- Content type (text-based, scanned, mixed)
- Page count
- Table presence
- Raw text/layout preservation

NO table extraction, NO LLM usage at this layer.
"""

import io
import os
import logging
from typing import Dict, Any, Optional

import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image

from models import DocumentAnalysis

logger = logging.getLogger("PDF_Agent.Classifier")

POPPLER_PATH =r"C:\poppler-25.12.0\Library\bin"

def analyze_document(pdf_bytes: bytes) -> DocumentAnalysis:
    """
    Analyze PDF document to understand its structure.
    """
    
    poppler_path = POPPLER_PATH

    logger.info(f"Starting document analysis ({len(pdf_bytes)} bytes)")
    
    page_details = []
    total_text_chars = 0
    pages_with_text = 0
    pages_with_images = 0
    total_tables = 0
    
    # Phase 1: Try pdfplumber for text-based analysis
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            page_count = len(pdf.pages)
            logger.info(f"PDF has {page_count} pages")
            
            for page_num, page in enumerate(pdf.pages, start=1):
                page_info = {
                    "page": page_num,
                    "has_text": False,
                    "has_tables": False,
                    "table_count": 0,
                    "text_length": 0,
                    "needs_ocr": False
                }
                
                # Extract text
                text = page.extract_text() or ""
                text_length = len(text.strip())
                page_info["text_length"] = text_length
                
                if text_length > 50:  # Meaningful text threshold
                    page_info["has_text"] = True
                    pages_with_text += 1
                    total_text_chars += text_length
                else:
                    # Page might be scanned/image-based
                    page_info["needs_ocr"] = True
                    pages_with_images += 1
                
                # Detect tables
                tables = page.find_tables()
                if tables:
                    page_info["has_tables"] = True
                    page_info["table_count"] = len(tables)
                    total_tables += len(tables)
                
                page_details.append(page_info)
                logger.info(f"Page {page_num}: text={text_length} chars, tables={page_info['table_count']}, needs_ocr={page_info['needs_ocr']}")
                
    except Exception as e:
        logger.error(f"pdfplumber failed: {e}")
        raise
    
    # Phase 2: Determine content type
    if pages_with_images == 0:
        content_type = "text-based"
    elif pages_with_text == 0:
        content_type = "scanned"
    else:
        content_type = "mixed"
    
    # Phase 3: OCR sample for scanned pages (if needed)
    raw_text_preview = ""
    if content_type in ["scanned", "mixed"]:
        logger.info("Document has scanned pages, performing OCR sample...")
        try:
            raw_text_preview = _ocr_first_page(pdf_bytes)
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            raw_text_preview = "[OCR unavailable]"
    else:
        # Get text preview from pdfplumber
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                raw_text_preview = pdf.pages[0].extract_text() or ""
                raw_text_preview = raw_text_preview[:500]
        except Exception:
            raw_text_preview = ""
    
    # Build result
    result = DocumentAnalysis(
        page_count=page_count,
        content_type=content_type,
        has_tables=total_tables > 0,
        table_count=total_tables,
        text_extractable=pages_with_text > 0,
        pages_with_text=pages_with_text,
        pages_with_images=pages_with_images,
        raw_text_preview=raw_text_preview[:500],
        page_details=page_details
    )
    
    logger.info(f"Analysis complete: {content_type}, {total_tables} tables detected")
    return result


def _ocr_first_page(pdf_bytes: bytes) -> str:
    """OCR the first page of a scanned PDF"""
    try:
        images = convert_from_bytes(
            pdf_bytes,
            dpi=200,
            first_page=1,
            last_page=1,
            poppler_path=POPPLER_PATH
        )
        
        if images:
            text = pytesseract.image_to_string(images[0], lang="eng")
            return text.strip()[:500]
        return ""
    except Exception as e:
        logger.error(f"OCR error: {e}")
        raise
