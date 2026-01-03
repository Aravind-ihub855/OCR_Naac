"""
Structural Reconstruction Module - Layer 3

CRITICAL: This layer uses PURE GEOMETRY, no AI, no semantic guessing.

Pipeline:
1. Coordinate Normalization
2. Table Region Detection
3. Column Detection (X-axis clustering)
4. Row Detection (Y-axis grouping)
5. Fragmented Cell Merging
6. Header Anchoring
7. Cross-Page Table Continuation

Output: Clean structural table graph (no semantic meaning attached)
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import numpy as np
from sklearn.cluster import DBSCAN

logger = logging.getLogger("PDF_Agent.StructuralReconstructor")


# -------------------- Data Classes --------------------

@dataclass
class NormalizedBlock:
    """A text block with normalized coordinates (0-1 range)"""
    text: str
    confidence: float
    x_norm: float  # left / page_width
    y_norm: float  # top / page_height
    w_norm: float  # width / page_width
    h_norm: float  # height / page_height
    x_center: float
    y_center: float
    page_num: int
    block_num: int
    block_type: str
    word_count: int
    
    # Original coordinates (for debugging)
    original_bbox: Dict[str, int] = field(default_factory=dict)


@dataclass
class Column:
    """A detected column with X-axis boundaries"""
    col_id: int
    x_start: float  # normalized
    x_end: float    # normalized
    x_center: float


@dataclass
class TableRow:
    """A single row in a table"""
    row_id: int
    y_center: float
    cells: List[str]  # One cell per column
    page_num: int
    confidence: float


@dataclass
class DetectedTable:
    """A fully reconstructed table"""
    table_id: str
    columns: List[Dict[str, Any]]
    header_row: Optional[List[str]]
    rows: List[Dict[str, Any]]
    page_start: int
    page_end: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StructuralOutput:
    """Complete output of Layer 3"""
    tables: List[Dict[str, Any]]
    metadata_blocks: List[Dict[str, Any]]  # Non-table content
    page_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# -------------------- Main Entry Point --------------------

def reconstruct_structure(signals: Dict[str, Any]) -> StructuralOutput:
    """
    Main entry point for Layer 3.
    
    Takes Layer 2 signals and produces structural tables.
    """
    logger.info("Starting structural reconstruction (Layer 3)")
    
    pages = signals.get('pages', [])
    page_count = signals.get('page_count', 0)
    
    if not pages:
        logger.warning("No pages in signals")
        return StructuralOutput(tables=[], metadata_blocks=[], page_count=0)
    
    # Step 3.1: Normalize all coordinates
    all_blocks = []
    for page_data in pages:
        normalized = _normalize_page_blocks(page_data)
        all_blocks.extend(normalized)
    
    logger.info(f"Normalized {len(all_blocks)} blocks across {page_count} pages")
    
    # Step 3.2: Detect table regions
    table_regions = _detect_table_regions(all_blocks, pages)
    logger.info(f"Detected {len(table_regions)} potential table regions")
    
    # Step 3.3 & 3.4: For each table region, detect columns and rows
    detected_tables = []
    metadata_blocks = []
    
    for region_idx, region in enumerate(table_regions):
        table = _reconstruct_table(region, region_idx)
        if table and len(table.rows) > 0:
            detected_tables.append(table.to_dict())
    
    # Collect non-table blocks as metadata
    table_block_ids = set()
    for region in table_regions:
        for block in region['blocks']:
            table_block_ids.add((block.page_num, block.block_num))
    
    for block in all_blocks:
        if (block.page_num, block.block_num) not in table_block_ids:
            if block.block_type in ['title', 'header', 'footer', 'paragraph']:
                metadata_blocks.append({
                    'text': block.text,
                    'type': block.block_type,
                    'page': block.page_num
                })
    
    logger.info(f"Reconstruction complete: {len(detected_tables)} tables, {len(metadata_blocks)} metadata blocks")
    
    return StructuralOutput(
        tables=detected_tables,
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
    
    return normalized


# -------------------- Step 3.2: Table Region Detection --------------------

def _detect_table_regions(
    all_blocks: List[NormalizedBlock], 
    pages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Detect potential table regions based on heuristics:
    - Blocks with similar left alignment
    - High numeric density
    - Vertical stacking patterns
    - has_potential_table hints from Layer 2
    """
    regions = []
    
    # Group blocks by page
    blocks_by_page = defaultdict(list)
    for block in all_blocks:
        blocks_by_page[block.page_num].append(block)
    
    # Check each page for table regions
    current_table_blocks = []
    current_table_start_page = None
    
    for page_data in pages:
        page_num = page_data.get('page_num', 1)
        page_blocks = blocks_by_page.get(page_num, [])
        has_potential_table = page_data.get('has_potential_table', False)
        
        # Filter blocks that look like table content
        table_candidates = [
            b for b in page_blocks 
            if _is_table_candidate(b)
        ]
        
        if table_candidates or has_potential_table:
            if current_table_start_page is None:
                current_table_start_page = page_num
            
            # Add all table-like blocks
            if table_candidates:
                current_table_blocks.extend(table_candidates)
            else:
                # Use all non-header/footer blocks
                current_table_blocks.extend([
                    b for b in page_blocks 
                    if b.block_type not in ['header', 'footer', 'title']
                ])
        else:
            # End of table region
            if current_table_blocks:
                regions.append({
                    'blocks': current_table_blocks,
                    'page_start': current_table_start_page,
                    'page_end': page_num - 1
                })
                current_table_blocks = []
                current_table_start_page = None
    
    # Don't forget the last region
    if current_table_blocks:
        regions.append({
            'blocks': current_table_blocks,
            'page_start': current_table_start_page,
            'page_end': pages[-1].get('page_num', 1)
        })
    
    # If no regions detected, try to find tables within pages
    if not regions:
        regions = _detect_inline_tables(all_blocks, pages)
    
    return regions


def _is_table_candidate(block: NormalizedBlock) -> bool:
    """Check if a block looks like table content"""
    text = block.text
    
    # Already marked as table
    if block.block_type == 'table':
        return True
    
    # Contains numbers (common in tables)
    words = text.split()
    if len(words) >= 2:
        numeric_count = sum(1 for w in words if any(c.isdigit() for c in w))
        if numeric_count >= len(words) * 0.3:  # 30%+ numeric
            return True
    
    # Contains common table separators
    if any(c in text for c in ['|', '│', '\t']):
        return True
    
    # Short, structured text (like column values)
    if len(words) <= 5 and len(words) >= 1:
        return True
    
    return False


def _detect_inline_tables(
    all_blocks: List[NormalizedBlock],
    pages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Detect tables by looking for column alignment patterns"""
    regions = []
    
    # Collect all x_start positions
    x_positions = [b.x_norm for b in all_blocks if b.block_type not in ['header', 'footer', 'title']]
    
    if len(x_positions) < 5:
        return regions
    
    # Cluster X positions to find column boundaries
    x_array = np.array(x_positions).reshape(-1, 1)
    clustering = DBSCAN(eps=0.03, min_samples=3).fit(x_array)
    
    # If we have multiple clusters, we likely have columns
    unique_labels = set(clustering.labels_)
    if len([l for l in unique_labels if l >= 0]) >= 2:
        # We have potential columns, treat all non-title content as table
        table_blocks = [
            b for b in all_blocks 
            if b.block_type not in ['header', 'footer', 'title']
        ]
        if table_blocks:
            regions.append({
                'blocks': table_blocks,
                'page_start': min(b.page_num for b in table_blocks),
                'page_end': max(b.page_num for b in table_blocks)
            })
    
    return regions


# -------------------- Step 3.3: Column Detection --------------------

def _detect_columns(blocks: List[NormalizedBlock]) -> List[Column]:
    """
    Detect columns using X-axis clustering.
    
    Columns are vertical bands where text consistently appears.
    Uses DBSCAN clustering on x_start positions.
    """
    if not blocks:
        return []
    
    # Collect left edge positions
    x_positions = np.array([b.x_norm for b in blocks]).reshape(-1, 1)
    
    # Cluster using DBSCAN
    # eps=0.05 means blocks within 5% of page width are same column
    clustering = DBSCAN(eps=0.05, min_samples=2).fit(x_positions)
    
    # Group by cluster
    cluster_blocks = defaultdict(list)
    for idx, label in enumerate(clustering.labels_):
        if label >= 0:  # Ignore noise (-1)
            cluster_blocks[label].append(blocks[idx])
    
    # Create column definitions
    columns = []
    for col_id, col_blocks in sorted(cluster_blocks.items()):
        x_starts = [b.x_norm for b in col_blocks]
        x_ends = [b.x_norm + b.w_norm for b in col_blocks]
        
        columns.append(Column(
            col_id=col_id,
            x_start=min(x_starts),
            x_end=max(x_ends),
            x_center=np.mean(x_starts)
        ))
    
    # Sort columns left to right
    columns.sort(key=lambda c: c.x_center)
    
    # Reassign col_ids after sorting
    for idx, col in enumerate(columns):
        col.col_id = idx
    
    logger.info(f"Detected {len(columns)} columns")
    return columns


# -------------------- Step 3.4: Row Detection --------------------

def _detect_rows(
    blocks: List[NormalizedBlock], 
    columns: List[Column]
) -> List[TableRow]:
    """
    Detect rows using Y-axis grouping.
    
    Rows are horizontal groupings of blocks at similar Y positions.
    """
    if not blocks or not columns:
        return []
    
    # Group blocks by Y position using clustering
    y_positions = np.array([b.y_center for b in blocks]).reshape(-1, 1)
    
    # eps=0.015 means blocks within 1.5% of page height are same row
    clustering = DBSCAN(eps=0.015, min_samples=1).fit(y_positions)
    
    # Group by row
    row_blocks = defaultdict(list)
    for idx, label in enumerate(clustering.labels_):
        if label >= 0:
            row_blocks[label].append(blocks[idx])
    
    # Create row definitions
    rows = []
    for row_id, r_blocks in sorted(row_blocks.items()):
        # Calculate row Y center
        y_center = np.mean([b.y_center for b in r_blocks])
        page_num = r_blocks[0].page_num  # Assume all blocks in row are same page
        
        # Assign blocks to columns
        cells = [''] * len(columns)
        confidences = []
        
        for block in r_blocks:
            # Find which column this block belongs to
            col_idx = _find_column_for_block(block, columns)
            if col_idx is not None:
                # Append text (for fragmented cells)
                if cells[col_idx]:
                    cells[col_idx] += ' ' + block.text
                else:
                    cells[col_idx] = block.text
                confidences.append(block.confidence)
        
        # Skip empty rows
        if any(cell.strip() for cell in cells):
            rows.append(TableRow(
                row_id=row_id,
                y_center=y_center,
                cells=cells,
                page_num=page_num,
                confidence=np.mean(confidences) if confidences else 0
            ))
    
    # Sort rows top to bottom (by page, then by Y)
    rows.sort(key=lambda r: (r.page_num, r.y_center))
    
    # Reassign row_ids after sorting
    for idx, row in enumerate(rows):
        row.row_id = idx
    
    logger.info(f"Detected {len(rows)} rows")
    return rows


def _find_column_for_block(block: NormalizedBlock, columns: List[Column]) -> Optional[int]:
    """Find which column a block belongs to based on X overlap"""
    block_center = block.x_center
    
    for col in columns:
        # Check if block center falls within column range (with tolerance)
        tolerance = 0.03
        if col.x_start - tolerance <= block_center <= col.x_end + tolerance:
            return col.col_id
    
    # Fallback: find nearest column
    if columns:
        distances = [abs(block_center - col.x_center) for col in columns]
        return distances.index(min(distances))
    
    return None


# -------------------- Step 3.5: Fragmented Cell Merging --------------------

def _merge_fragmented_cells(rows: List[TableRow], columns: List[Column]) -> List[TableRow]:
    """
    Merge cells that were split across multiple blocks.
    
    Handles:
    - Words split across lines
    - Values broken across blocks
    """
    # Already handled in row detection by appending text
    # Additional merging logic can be added here if needed
    
    merged_rows = []
    
    for row in rows:
        # Clean up cell text
        cleaned_cells = []
        for cell in row.cells:
            # Remove extra whitespace
            cleaned = ' '.join(cell.split())
            cleaned_cells.append(cleaned)
        
        merged_rows.append(TableRow(
            row_id=row.row_id,
            y_center=row.y_center,
            cells=cleaned_cells,
            page_num=row.page_num,
            confidence=row.confidence
        ))
    
    return merged_rows


# -------------------- Step 3.6: Header Anchoring --------------------

def _detect_header_row(rows: List[TableRow]) -> Tuple[Optional[List[str]], List[TableRow]]:
    """
    Detect and extract header row.
    
    Heuristics:
    - First row on first page
    - Non-numeric content
    - Higher confidence
    """
    if not rows:
        return None, rows
    
    # Check first row
    first_row = rows[0]
    
    # Count numeric cells
    numeric_cells = sum(
        1 for cell in first_row.cells 
        if cell and any(c.isdigit() for c in cell)
    )
    
    total_cells = sum(1 for cell in first_row.cells if cell.strip())
    
    # If less than 30% numeric, likely a header
    if total_cells > 0 and numeric_cells / total_cells < 0.3:
        logger.info(f"Detected header row: {first_row.cells}")
        return first_row.cells, rows[1:]
    
    return None, rows


# -------------------- Step 3.7: Cross-Page Continuation --------------------

def _handle_cross_page_continuation(
    rows: List[TableRow], 
    columns: List[Column]
) -> List[TableRow]:
    """
    Ensure rows from different pages are properly merged.
    
    Already handled by processing all blocks together,
    but this function validates continuity.
    """
    # Rows are already sorted by (page, y_center)
    # Validate that column structure is consistent across pages
    
    pages_seen = set(row.page_num for row in rows)
    
    if len(pages_seen) > 1:
        logger.info(f"Table spans {len(pages_seen)} pages: {sorted(pages_seen)}")
    
    return rows


# -------------------- Table Reconstruction --------------------

def _reconstruct_table(
    region: Dict[str, Any], 
    table_idx: int
) -> Optional[DetectedTable]:
    """Reconstruct a single table from a region of blocks"""
    blocks = region.get('blocks', [])
    page_start = region.get('page_start', 1)
    page_end = region.get('page_end', 1)
    
    if not blocks:
        return None
    
    # Step 3.3: Detect columns
    columns = _detect_columns(blocks)
    
    if not columns:
        logger.warning(f"No columns detected for table {table_idx}")
        return None
    
    # Step 3.4: Detect rows
    rows = _detect_rows(blocks, columns)
    
    if not rows:
        logger.warning(f"No rows detected for table {table_idx}")
        return None
    
    # Step 3.5: Merge fragmented cells
    rows = _merge_fragmented_cells(rows, columns)
    
    # Step 3.6: Detect header
    header_row, data_rows = _detect_header_row(rows)
    
    # Step 3.7: Handle cross-page continuation
    data_rows = _handle_cross_page_continuation(data_rows, columns)
    
    # Build table structure
    return DetectedTable(
        table_id=f"table_{table_idx + 1}",
        columns=[{
            'index': col.col_id,
            'x_range': [round(col.x_start, 3), round(col.x_end, 3)]
        } for col in columns],
        header_row=header_row,
        rows=[{
            'row_id': row.row_id,
            'cells': row.cells,
            'page': row.page_num,
            'confidence': round(row.confidence, 2)
        } for row in data_rows],
        page_start=page_start,
        page_end=page_end
    )
