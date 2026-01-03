"""
Signal Preservation Models - Layer 2
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List
from enum import Enum


class BlockType(str, Enum):
    """Types of content blocks detected"""
    TITLE = "title"
    TABLE = "table"
    PARAGRAPH = "paragraph"
    HEADER = "header"
    FOOTER = "footer"
    LIST = "list"
    UNKNOWN = "unknown"


@dataclass
class TextBlock:
    """A single text block with position and content"""
    text: str
    confidence: float
    bbox: Dict[str, int]  # {left, top, width, height}
    block_num: int
    line_num: int
    word_num: int
    block_type: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass 
class PageSignal:
    """All signals from a single page"""
    page_num: int
    width: int
    height: int
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""
    word_count: int = 0
    has_potential_table: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentSignals:
    """Complete signal preservation output"""
    page_count: int
    pages: List[Dict[str, Any]] = field(default_factory=list)
    total_words: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
