"""
Signal Preservation Module - Layer 2

CRITICAL: This layer preserves EVERYTHING without interpretation.

What we preserve:
- Page boundaries
- Bounding boxes for each text block
- Reading order
- Block type hints (title, table, paragraph)
- Line breaks and spacing

"""
import os
import logging
from typing import List, Dict, Any

from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image

from models import BlockType, TextBlock, PageSignal, DocumentSignals

logger = logging.getLogger("PDF_Agent.SignalPreserver")

POPPLER_PATH =r"C:\poppler-25.12.0\Library\bin"

def preserve_signals(pdf_bytes: bytes, dpi: int = 300) -> DocumentSignals:
    """
    Extract and preserve all signals from PDF without interpretation.
    """
    poppler_path = POPPLER_PATH
    logger.info(f"Starting signal preservation ({len(pdf_bytes)} bytes, {dpi} DPI)")
    
    # Convert PDF to images
    try:
        images = convert_from_bytes(
            pdf_bytes,
            dpi=dpi,
            poppler_path=poppler_path
        )
        logger.info(f"Converted to {len(images)} page images")
    except Exception as e:
        logger.error(f"PDF to image conversion failed: {e}")
        raise
    
    pages = []
    total_words = 0
    
    for page_num, image in enumerate(images, start=1):
        logger.info(f"Processing page {page_num}/{len(images)}...")
        page_signal = _extract_page_signals(image, page_num)
        pages.append(page_signal.to_dict())
        total_words += page_signal.word_count
    
    result = DocumentSignals(
        page_count=len(images),
        pages=pages,
        total_words=total_words
    )
    
    logger.info(f"Signal preservation complete: {len(images)} pages, {total_words} words")
    return result


def _extract_page_signals(image: Image.Image, page_num: int) -> PageSignal:
    """
    Extract all signals from a single page image.
    
    Uses Tesseract with full data output to get:
    - Word-level bounding boxes
    - Confidence scores
    - Block/line/word structure
    """
    width, height = image.size
    
    # Get detailed OCR data with bounding boxes
    ocr_data = pytesseract.image_to_data(
        image, 
        lang="eng",
        output_type=pytesseract.Output.DICT
    )
    
    blocks = []
    raw_text_parts = []
    word_count = 0
    current_block = None
    block_texts = {}  # block_num -> list of words
    
    # Process OCR output
    n_boxes = len(ocr_data['text'])
    
    for i in range(n_boxes):
        text = ocr_data['text'][i].strip()
        conf = int(ocr_data['conf'][i])
        
        # Skip empty or low-confidence entries
        if not text or conf < 0:
            continue
        
        block_num = ocr_data['block_num'][i]
        line_num = ocr_data['line_num'][i]
        word_num = ocr_data['word_num'][i]
        
        # Collect words by block
        if block_num not in block_texts:
            block_texts[block_num] = {
                'words': [],
                'bbox': {
                    'left': ocr_data['left'][i],
                    'top': ocr_data['top'][i],
                    'width': ocr_data['width'][i],
                    'height': ocr_data['height'][i]
                },
                'confidences': []
            }
        
        block_texts[block_num]['words'].append(text)
        block_texts[block_num]['confidences'].append(conf)
        
        # Expand bounding box to encompass all words in block
        block_texts[block_num]['bbox']['left'] = min(
            block_texts[block_num]['bbox']['left'], 
            ocr_data['left'][i]
        )
        block_texts[block_num]['bbox']['top'] = min(
            block_texts[block_num]['bbox']['top'], 
            ocr_data['top'][i]
        )
        
        right = ocr_data['left'][i] + ocr_data['width'][i]
        bottom = ocr_data['top'][i] + ocr_data['height'][i]
        
        current_right = block_texts[block_num]['bbox']['left'] + block_texts[block_num]['bbox']['width']
        current_bottom = block_texts[block_num]['bbox']['top'] + block_texts[block_num]['bbox']['height']
        
        if right > current_right:
            block_texts[block_num]['bbox']['width'] = right - block_texts[block_num]['bbox']['left']
        if bottom > current_bottom:
            block_texts[block_num]['bbox']['height'] = bottom - block_texts[block_num]['bbox']['top']
        
        word_count += 1
    
    # Convert block data to structured blocks
    for block_num in sorted(block_texts.keys()):
        block_data = block_texts[block_num]
        block_text = ' '.join(block_data['words'])
        avg_conf = sum(block_data['confidences']) / len(block_data['confidences']) if block_data['confidences'] else 0
        
        # Detect block type based on heuristics
        block_type = _detect_block_type(
            block_text, 
            block_data['bbox'], 
            width, 
            height,
            page_num
        )
        
        blocks.append({
            'block_num': block_num,
            'text': block_text,
            'confidence': round(avg_conf, 2),
            'bbox': block_data['bbox'],
            'block_type': block_type,
            'word_count': len(block_data['words'])
        })
        
        raw_text_parts.append(block_text)
    
    # Check for potential tables (multiple blocks with aligned columns)
    has_potential_table = _detect_potential_table(blocks, width)
    
    return PageSignal(
        page_num=page_num,
        width=width,
        height=height,
        blocks=blocks,
        raw_text='\n\n'.join(raw_text_parts),
        word_count=word_count,
        has_potential_table=has_potential_table
    )


def _detect_block_type(
    text: str, 
    bbox: Dict[str, int], 
    page_width: int, 
    page_height: int,
    page_num: int
    ) -> str:
    """
    Heuristic block type detection.
    
    Rules (no AI):
    - Short text at top = possible title/header
    - Short text at bottom = possible footer
    - Many pipe/bar chars = possible table
    - Bullet points = list
    - Default = paragraph
    """
    text_lower = text.lower()
    
    # Position-based hints
    y_position = bbox['top'] / page_height
    x_center = (bbox['left'] + bbox['width']/2) / page_width
    
    # Top 10% of page, centered = possible title
    if y_position < 0.10 and 0.3 < x_center < 0.7 and len(text.split()) < 15:
        return BlockType.TITLE.value
    
    # Top 15% = possible header
    if y_position < 0.15 and len(text.split()) < 20:
        return BlockType.HEADER.value
    
    # Bottom 10% = possible footer
    if y_position > 0.90:
        return BlockType.FOOTER.value
    
    # Table indicators
    table_chars = ['|', '│', '┃', '║']
    if any(char in text for char in table_chars):
        return BlockType.TABLE.value
    
    # Multiple numbers with consistent spacing might be table data
    words = text.split()
    if len(words) >= 3:
        numeric_count = sum(1 for w in words if any(c.isdigit() for c in w))
        if numeric_count >= len(words) * 0.5:  # 50%+ numeric
            return BlockType.TABLE.value
    
    # List indicators
    list_starters = ['•', '-', '*', '→', '►', '1.', '2.', '3.', 'i.', 'ii.']
    if any(text.strip().startswith(s) for s in list_starters):
        return BlockType.LIST.value
    
    # Default
    return BlockType.PARAGRAPH.value


def _detect_potential_table(blocks: List[Dict], page_width: int) -> bool:
    """
    Detect if blocks suggest a table structure.
    
    Heuristics:
    - Multiple blocks at similar Y positions (rows)
    - Consistent X positions across rows (columns)
    """
    if len(blocks) < 4:
        return False
    
    # Count blocks marked as table type
    table_blocks = sum(1 for b in blocks if b['block_type'] == BlockType.TABLE.value)
    if table_blocks >= 2:
        return True
    
    # Check for horizontal alignment (same Y, different X)
    y_groups = {}
    for block in blocks:
        y_key = block['bbox']['top'] // 50  # Group by ~50px bands
        if y_key not in y_groups:
            y_groups[y_key] = []
        y_groups[y_key].append(block)
    
    # Multiple items in same row suggests table
    rows_with_multiple = sum(1 for items in y_groups.values() if len(items) >= 2)
    if rows_with_multiple >= 2:
        return True
    
    return False
