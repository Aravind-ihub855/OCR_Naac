"""
Geometric Table Reconstructor (Non-AI)
Uses projection profiles and clustering to reconstruct tables from granular OCR signals.
"""

import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from collections import defaultdict

logger = logging.getLogger("GeometricReconstructor")

def reconstruct_geometric(signals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reconstruct tables using pure geometry.
    Input: Granular signals (Output 2) -> Pages -> Blocks (Words)
    Output: Structured Tables
    """
    reconstructed_pages = []
    
    for page in signals.get('pages', []):
        logger.info(f"Reconstructing Page {page['page_num']}...")
        page_result = _process_page_geometric(page)
        reconstructed_pages.append(page_result)
        
    return {
        "pages": reconstructed_pages
    }

def _process_page_geometric(page: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single page to find tables."""
    blocks = page.get('blocks', [])
    if not blocks:
        return {"page_num": page.get('page_num'), "tables": []}
    
    # 1. Form Text Lines (Y-clustering)
    # Sort by Y, then X
    blocks.sort(key=lambda b: (b['bbox']['top'], b['bbox']['left']))
    
    lines = _form_lines(blocks)
    
    # 2. Detect Table Regions (Heuristic)
    # For this specific task (Income & Expenditure), the whole page is often a table.
    # We will try to detect columns globally first.
    
    # 3. Detect Columns (X-projection)
    columns = _detect_columns_projection(lines)
    
    # 4. Map Lines to Rows/Cells
    rows = _map_to_grid(lines, columns)
    
    # 5. Post-process (Filter empty rows, merge headers)
    cleaned_table = _clean_table(rows, columns)
    
    return {
        "page_num": page.get('page_num'),
        "tables": [cleaned_table] if cleaned_table['rows'] else []
    }

def _form_lines(blocks: List[Dict]) -> List[Dict]:
    """Group words into horizontal lines."""
    if not blocks:
        return []
        
    lines = []
    current_line = [blocks[0]]
    
    for block in blocks[1:]:
        last_block = current_line[-1]
        
        # Check vertical overlap/alignment
        # Center Y comparison
        y_center_last = last_block['bbox']['top'] + last_block['bbox']['height']/2
        y_center_curr = block['bbox']['top'] + block['bbox']['height']/2
        
        # Height comparison
        avg_height = (last_block['bbox']['height'] + block['bbox']['height']) / 2
        
        # If aligned vertically within 50% of height
        if abs(y_center_curr - y_center_last) < avg_height * 0.5:
            current_line.append(block)
        else:
            # New line
            lines.append(_merge_line_blocks(current_line))
            current_line = [block]
            
    lines.append(_merge_line_blocks(current_line))
    return lines

def _merge_line_blocks(line_blocks: List[Dict]) -> Dict:
    """Merge a list of word blocks into a single line object."""
    # Re-sort by X to be sure
    line_blocks.sort(key=lambda b: b['bbox']['left'])
    
    text = " ".join([b['text'] for b in line_blocks])
    
    left = line_blocks[0]['bbox']['left']
    top = min(b['bbox']['top'] for b in line_blocks)
    right = max(b['bbox']['left'] + b['bbox']['width'] for b in line_blocks)
    bottom = max(b['bbox']['top'] + b['bbox']['height'] for b in line_blocks)
    
    return {
        "text": text,
        "bbox": {
            "left": left,
            "top": top,
            "width": right - left,
            "height": bottom - top,
            "x_center": left + (right - left)/2,
            "y_center": top + (bottom - top)/2
        },
        "words": line_blocks
    }

def _detect_columns_projection(lines: List[Dict]) -> List[Dict]:
    """
    Detect columns using gap analysis on X-coordinates.
    We look for vertical stats where NO text exists crossing that X line.
    """
    if not lines:
        return []
        
    # Stats of text coverage
    # Determine page width roughly
    max_width = 0
    for l in lines:
        r = l['bbox']['left'] + l['bbox']['width']
        if r > max_width:
            max_width = r
            
    if max_width == 0: return []
    
    # Create a histogram of "text presence" at each X pixel
    # Just iterate and mark intervals
    # Optimization: Use intervals and merge them
    
    # Simpler approach for tables: Clustering X-centers or Finding Gaps
    # Let's find vertical gaps that are "wide enough" and "tall enough"
    
    # Collect all separate word x-intervals from the processed lines
    # (Using the merged lines might hide gaps between words, so we look at original words)
    all_words = []
    for l in lines:
        all_words.extend(l['words'])
        
    # Project X intervals
    # We want to find x_ranges where density is 0
    
    # Sort words by left
    all_words.sort(key=lambda b: b['bbox']['left'])
    
    # We sweep a vertical line. 
    # But text is sparse.
    # Approach: Cluster the X-centers of words?
    # Or Cluster X-ranges.
    
    # Let's use specific column separators detection.
    # Group words by rough alignment.
    
    # Quick Heuristic:
    # 1. Project all word intervals onto X-axis.
    # 2. Histogram with bin size ~10px.
    # 3. Find peaks (columns) and valleys (gaps).
    
    bins = [0] * int(max_width + 100)
    for w in all_words:
        l = int(w['bbox']['left'])
        r = int(w['bbox']['left'] + w['bbox']['width'])
        for i in range(l, r):
            if i < len(bins):
                bins[i] += 1
                
    # Threshold: if bin > N, it's a column.
    # Actually, gaps are where bin is near 0.
    
    # Find gaps
    gaps = []
    in_gap = False
    start_gap = 0
    
    # Filter: Low density = gap. High density = column.
    # However, rows have spaces. The sum over ALL rows should show peaks at columns.
    
    threshold = len(lines) * 0.05 # 5% of lines have text there -> column
    # Maybe simpler: Find peaks.
    
    columns = []
    in_col = False
    col_start = 0
    
    for i, val in enumerate(bins):
        if val > 2: # At least 2 words overlap at this X
            if not in_col:
                in_col = True
                col_start = i
        else:
            if in_col:
                in_col = False
                # End of column
                columns.append({"left": col_start, "right": i})
                
    # Merge close columns
    merged_cols = []
    if columns:
        curr = columns[0]
        for next_col in columns[1:]:
            if next_col['left'] - curr['right'] < 20: # 20px gap tolerance
                curr['right'] = next_col['right']
            else:
                merged_cols.append(curr)
                curr = next_col
        merged_cols.append(curr)
        
    return merged_cols

def _map_to_grid(lines: List[Dict], columns: List[Dict]) -> List[List[str]]:
    """Map text lines to the detected columns."""
    rows = []
    
    for line in lines:
        # Create empty row
        row_cells = [""] * len(columns)
        
        # For each word in the line, find which column it falls into
        for word in line['words']:
            w_center = word['bbox']['left'] + word['bbox']['width']/2
            
            # Find matching column
            match_idx = -1
            min_dist = float('inf')
            
            for i, col in enumerate(columns):
                # Check overlap
                if word['bbox']['left'] < col['right'] and (word['bbox']['left'] + word['bbox']['width']) > col['left']:
                     match_idx = i
                     break
                
                # Distance to center
                col_center = (col['left'] + col['right']) / 2
                dist = abs(w_center - col_center)
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i
            
            if match_idx == -1:
                match_idx = closest_idx # Fallback to closest
            
            # Append text
            if row_cells[match_idx]:
                 row_cells[match_idx] += " " + word['text']
            else:
                 row_cells[match_idx] = word['text']
                 
        rows.append(row_cells)
        
    return rows

def _clean_table(rows: List[List[str]], columns: List[Dict]) -> Dict[str, Any]:
    """Format the output table."""
    # Filter empty rows
    valid_rows = [r for r in rows if any(c.strip() for c in r)]
    
    return {
        "headers": [], # detection logic omitted for simplicity
        "rows": valid_rows,
        "n_cols": len(columns)
    }
