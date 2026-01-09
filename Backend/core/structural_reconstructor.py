"""
Structural Reconstruction Module - Layer 3

CRITICAL: This layer uses AI (LLM) to interpret granular signals into structured tables.

Pipeline:
1. Coordinate Normalization
2. Compact Context Construction
3. LLM-based Table Extraction
4. Structure Parsing

Output: Clean structural table graph
"""

import logging
import json
import os
from typing import List, Dict, Any, Optional
import numpy as np
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser

from services.llm import get_groq_llm
from models import NormalizedBlock, DetectedTable, StructuralOutput

logger = logging.getLogger("PDF_Agent.StructuralReconstructor")

# -------------------- Main Entry Point --------------------

def reconstruct_structure(signals: Dict[str, Any]) -> StructuralOutput:
    """
    Main entry point for Layer 3.
    Use LLM to interpret detailed layout signals.
    """
    logger.info("Starting structural reconstruction (Layer 3 - AI Powered)")
    
    pages = signals.get('pages', [])
    page_count = signals.get('page_count', 0)
    
    if not pages:
        return StructuralOutput(tables=[], metadata_blocks=[], page_count=0)
    
    all_tables = []
    metadata_blocks = []
    
    try:
        llm = get_groq_llm()
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        # Return empty or fallback? For now return empty with error log
        return StructuralOutput(tables=[], metadata_blocks=[], page_count=page_count)

    for i, page_data in enumerate(pages):
        page_num = page_data.get('page_num', i + 1)
        logger.info(f"Processing page {page_num} with AI...")
        
        # 1. Normalize
        normalized_blocks = _normalize_page_blocks(page_data)
        
        # 2. Construct Context
        context_str = _build_page_context(normalized_blocks)
        
        # 3. Call LLM
        extracted_data = _invoke_llm_extraction(llm, context_str, page_num)
        
        # 4. Process Output
        if extracted_data and 'tables' in extracted_data:
            for tbl in extracted_data['tables']:
                detected_table = _convert_to_detected_table(tbl, page_num, len(all_tables) + 1)
                all_tables.append(detected_table.to_dict())
        
        # Collect 'other' blocks as metadata
        # (For now, we assume LLM picks up tables, everything else is just text. 
        # We can refine metadata extraction later or ask LLM for it too.)
        # Quick fallback: treat non-table text as metadata? 
        # For this iteration, we focus on the USER's request: "AI to make it as table data"
        
    logger.info(f"AI Reconstruction complete: {len(all_tables)} tables detected.")
    
    return StructuralOutput(
        tables=all_tables,
        metadata_blocks=metadata_blocks,
        page_count=page_count
    )


# -------------------- Step 3.1: Coordinate Normalization --------------------

def _normalize_page_blocks(page_data: Dict[str, Any]) -> List[NormalizedBlock]:
    """Convert all blocks to normalized coordinates (0-1 range)"""
    page_width = page_data.get('width', 1)
    page_height = page_data.get('height', 1)
    page_num = page_data.get('page_num', 1)
    
    normalized = []
    
    for block in page_data.get('blocks', []):
        bbox = block.get('bbox', {})
        left = bbox.get('left', 0)
        top = bbox.get('top', 0)
        width = bbox.get('width', 0)
        height = bbox.get('height', 0)
        
        # Normalize to 0-1 range
        x_norm = left / page_width if page_width > 0 else 0
        y_norm = top / page_height if page_height > 0 else 0
        w_norm = width / page_width if page_width > 0 else 0
        h_norm = height / page_height if page_height > 0 else 0
        
        normalized.append(NormalizedBlock(
            text=block.get('text', ''),
            confidence=block.get('confidence', 0),
            x_norm=x_norm,
            y_norm=y_norm,
            w_norm=w_norm,
            h_norm=h_norm,
            x_center=x_norm + w_norm / 2,
            y_center=y_norm + h_norm / 2,
            page_num=page_num,
            block_num=block.get('block_num', 0),
            block_type=block.get('block_type', 'unknown'),
            word_count=block.get('word_count', 0),
            original_bbox=bbox
        ))
    
    # Sort blocks by Y (top to bottom), then X (left to right)
    normalized.sort(key=lambda b: (b.y_norm, b.x_norm))
    return normalized


# -------------------- Step 3.2: Context Construction --------------------

def _build_page_context(blocks: List[NormalizedBlock]) -> str:
    """
    Build a compact text representation of the page layout.
    Format: [y, x] Text
    Rounding to 2 decimals to save tokens.
    """
    lines = []
    for b in blocks:
        # Use round(..., 2) to minimize tokens
        # We put Y first because reading order is usually vertical first
        coords = f"[{b.y_norm:.2f},{b.x_norm:.2f}]"
        # Truncate very long text if necessary, but USER wants "exact meaning" so keep it.
        text = b.text.replace("\n", " ")
        lines.append(f"{coords} {text}")
    
    return "\n".join(lines)


# -------------------- Step 3.3: LLM Extraction --------------------

def _invoke_llm_extraction(llm, context_str: str, page_num: int) -> Optional[Dict[str, Any]]:
    """
    Call LLM to extract tables.
    """
    system_prompt = """You are a precise PDF Table Extraction Agent.
Your Goal: Extract structured tables from the provided page layout data.

Input Format: lines of "[y_coordinate, x_coordinate] Text content"
Output Format: JSON object with specific structure.

Rules:
1. Identify tabular structures based on alignment and content.
2. Merge cell content correctly.
3. Extract exact text.
4. Output JSON:
{
  "tables": [
    {
      "title": "Table Title (if any)",
      "headers": ["Col 1", "Col 2"],
      "rows": [
        ["Val 1", "Val 2"],
        ["Val A", "Val B"]
      ]
    }
  ]
}
If no tables found, return {"tables": []}.
"""
    
    user_prompt = f"Page {page_num} Layout Data:\n\n{context_str}"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content
        
        # Parse JSON
        # Find JSON substring if extra text exists
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end != -1:
            json_str = content[start:end]
            return json.loads(json_str)
        else:
            logger.warning(f"No JSON found in LLM response for page {page_num}")
            return None
            
    except Exception as e:
        logger.error(f"Error invoking LLM for page {page_num}: {e}")
        return None


# -------------------- Step 3.4: Convert to Model --------------------

def _convert_to_detected_table(llm_table: Dict, page_num: int, table_id_num: int) -> DetectedTable:
    """
    Convert LLM output to internal DetectedTable model.
    """
    headers = llm_table.get('headers', [])
    data_rows = llm_table.get('rows', [])
    
    # Create internal TableRow objects
    # We don't have exact y_center for rows from LLM unless we ask for it.
    # We will use dummy values or infer from index for now.
    
    converted_rows = []
    for idx, row_data in enumerate(data_rows):
        converted_rows.append({
            'row_id': idx,
            'cells': [str(c) for c in row_data], # Ensure strings
            'page': page_num,
            'confidence': 1.0 # AI is confident!
        })
    
    # Mock columns structure (required by DetectedTable)
    # Just generic columns based on header count
    col_count = len(headers)
    columns = []
    for i in range(col_count):
        columns.append({
            'index': i,
            'x_range': [0, 1] # Unknown
        })

    return DetectedTable(
        table_id=f"table_{table_id_num}",
        columns=columns,
        header_row=headers,
        rows=converted_rows,
        page_start=page_num,
        page_end=page_num
    )
