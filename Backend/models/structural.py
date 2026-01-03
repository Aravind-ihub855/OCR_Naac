"""
Structural Reconstruction Models - Layer 3

Internal processing models and output models for structural reconstruction.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Optional


# -------------------- Internal Processing Models --------------------

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


# -------------------- Output Models --------------------

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
