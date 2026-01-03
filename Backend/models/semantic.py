"""
Semantic Interpretation Models - Layer 4
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Optional


@dataclass
class SemanticColumn:
    """A semantically understood column"""
    name: str
    original_name: Optional[str]
    data_type: str
    confidence: float


@dataclass
class SemanticTable:
    """A fully interpreted table"""
    table_id: str
    table_name: str
    table_intent: str
    confidence: float
    columns: List[Dict[str, Any]]
    rows: List[Dict[str, Any]]
    page_range: List[int]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentMetadata:
    """Document-level extracted metadata"""
    title: Optional[str] = None
    organization: Optional[str] = None
    address: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    period: Optional[str] = None
    document_type: Optional[str] = None
    auditor: Optional[str] = None
    place: Optional[str] = None
    date: Optional[str] = None
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticOutput:
    """Complete output of Layer 4"""
    tables: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    processing_notes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
