"""
Backend Models Package

Contains all dataclasses organized by pipeline layer:
- Layer 1: classifier.py (DocumentAnalysis)
- Layer 2: signals.py (TextBlock, PageSignal, DocumentSignals, BlockType)
- Layer 3: structural.py (TableColumn, TableCell, TableRow, DetectedTable, StructuralOutput)
- Layer 4: semantic.py (SemanticColumn, SemanticTable, DocumentMetadata, SemanticOutput)
- Layer 5: reasoning.py (DocumentArchetype, ReasonedTable, DocumentReasoning)
- Layer 6: excel.py (ExcelColumn, ExcelRow, ExcelTable, MappingOutput)
"""

# Layer 1 - Classification
from .classifier import DocumentAnalysis

# Layer 2 - Signal Preservation
from .signals import BlockType, TextBlock, PageSignal, DocumentSignals

# Layer 3 - Structural Reconstruction
from .structural import NormalizedBlock, Column, TableRow, DetectedTable, StructuralOutput

# Layer 4 - Semantic Interpretation
from .semantic import SemanticColumn, SemanticTable, DocumentMetadata, SemanticOutput

# Layer 5 - Document Reasoning
from .reasoning import DocumentArchetype, ARCHETYPE_SCHEMAS, ReasonedTable, DocumentReasoning

# Layer 6 - Excel Output
from .excel import ExcelColumn, ExcelRow, ExcelTable, MappingOutput


__all__ = [
    # Layer 1
    "DocumentAnalysis",
    # Layer 2
    "BlockType", "TextBlock", "PageSignal", "DocumentSignals",
    # Layer 3
    "NormalizedBlock", "Column", "TableRow", "DetectedTable", "StructuralOutput",
    # Layer 4
    "SemanticColumn", "SemanticTable", "DocumentMetadata", "SemanticOutput",
    # Layer 5
    "DocumentArchetype", "ARCHETYPE_SCHEMAS", "ReasonedTable", "DocumentReasoning",
    # Layer 6
    "ExcelColumn", "ExcelRow", "ExcelTable", "MappingOutput",
]
