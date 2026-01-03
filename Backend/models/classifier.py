"""
Document Classification Models - Layer 1
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List


@dataclass
class DocumentAnalysis:
    """Result of document classification"""
    page_count: int
    content_type: str  # "text-based", "scanned", "mixed"
    has_tables: bool
    table_count: int
    text_extractable: bool
    pages_with_text: int
    pages_with_images: int
    raw_text_preview: str  
    page_details: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
