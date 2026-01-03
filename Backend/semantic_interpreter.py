"""
Semantic Interpretation Module - Layer 4

This is where AI enters the pipeline.
Uses LLM to understand MEANING, not layout.

Responsibilities:
- Header inference
- Column semantic classification
- Row normalization
- Noise/artifact removal
- Table intent detection
- Confidence scoring

What Layer 4 does NOT do:
❌ OCR
❌ Geometry detection
❌ Layout parsing
❌ Table structure detection
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

from langchain_core.prompts import ChatPromptTemplate
from llm import get_groq_llm

logger = logging.getLogger("PDF_Agent.SemanticInterpreter")


# -------------------- Data Classes --------------------

@dataclass
class SemanticColumn:
    """A semantically understood column"""
    name: str
    original_name: Optional[str]
    data_type: str  # "string", "number", "date", "currency", "identifier"
    confidence: float


@dataclass
class SemanticRow:
    """A normalized row with semantic understanding"""
    data: Dict[str, Any]
    is_noise: bool = False
    noise_type: Optional[str] = None  # "footer", "signature", "page_number", etc.


@dataclass
class SemanticTable:
    """A fully interpreted table"""
    table_id: str
    table_name: str
    table_intent: str  # "income_expenditure", "balance_sheet", "summary", etc.
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
    department: Optional[str] = None
    year: Optional[str] = None
    period: Optional[str] = None
    document_type: Optional[str] = None
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


# -------------------- Main Entry Point --------------------

def interpret_semantics(structure: Dict[str, Any]) -> SemanticOutput:
    """
    Main entry point for Layer 4.
    
    Takes Layer 3 structural output and produces semantic interpretation.
    """
    logger.info("Starting semantic interpretation (Layer 4)")
    
    tables = structure.get('tables', [])
    metadata_blocks = structure.get('metadata_blocks', [])
    page_count = structure.get('page_count', 0)
    
    if not tables:
        logger.warning("No tables to interpret")
        return SemanticOutput(
            tables=[],
            metadata={"confidence": 0},
            processing_notes=["No tables found in document"]
        )
    
    # Initialize LLM
    try:
        llm = get_groq_llm()
    except ValueError as e:
        logger.error(f"LLM initialization failed: {e}")
        # Return structure as-is without semantic enhancement
        return _fallback_output(tables, metadata_blocks)
    
    processing_notes = []
    
    # Step 1: Extract document metadata from metadata blocks
    logger.info("Extracting document metadata...")
    doc_metadata = _extract_document_metadata(llm, metadata_blocks)
    processing_notes.append(f"Extracted metadata with {doc_metadata.confidence:.0%} confidence")
    
    # Step 2: Interpret each table
    interpreted_tables = []
    for idx, table in enumerate(tables):
        logger.info(f"Interpreting table {idx + 1}/{len(tables)}...")
        semantic_table = _interpret_table(llm, table, doc_metadata, metadata_blocks)
        interpreted_tables.append(semantic_table.to_dict())
        processing_notes.append(
            f"Table '{semantic_table.table_name}' interpreted with {semantic_table.confidence:.0%} confidence"
        )
    
    logger.info(f"Semantic interpretation complete: {len(interpreted_tables)} tables processed")
    
    return SemanticOutput(
        tables=interpreted_tables,
        metadata=doc_metadata.to_dict(),
        processing_notes=processing_notes
    )


# -------------------- Metadata Extraction --------------------

def _extract_document_metadata(llm, metadata_blocks: List[Dict[str, Any]]) -> DocumentMetadata:
    """Extract document-level metadata using LLM"""
    
    if not metadata_blocks:
        return DocumentMetadata(confidence=0.0)
    
    # Combine metadata text
    metadata_text = "\n".join([
        f"[{b.get('type', 'unknown')}] {b.get('text', '')}"
        for b in metadata_blocks[:20]  # Limit to first 20 blocks
    ])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a document metadata extraction agent.

Extract metadata from the provided text blocks.

Return ONLY valid JSON in this exact format:
{{
  "title": "Document title or null",
  "organization": "Organization name or null",
  "department": "Department name or null",
  "year": "Year or fiscal year (e.g., '2021-2022') or null",
  "period": "Time period (e.g., 'For the year ended 31.03.2021') or null",
  "document_type": "Type (e.g., 'Financial Statement', 'NAAC Report', 'Audit Report') or null",
  "confidence": 0.0 to 1.0
}}

Rules:
- Extract ONLY what is explicitly stated
- Do NOT invent or guess data
- Set confidence based on clarity of extraction
- Return null for missing fields"""),
        ("human", "Text blocks:\n{text}")
    ])
    
    try:
        formatted = prompt.format_messages(text=metadata_text)
        response = llm.invoke(formatted)
        result = _parse_json_response(response.content)
        
        return DocumentMetadata(
            title=result.get('title'),
            organization=result.get('organization'),
            department=result.get('department'),
            year=result.get('year'),
            period=result.get('period'),
            document_type=result.get('document_type'),
            confidence=result.get('confidence', 0.5)
        )
    except Exception as e:
        logger.warning(f"Metadata extraction failed: {e}")
        return DocumentMetadata(confidence=0.0)


# -------------------- Table Interpretation --------------------

def _interpret_table(
    llm, 
    table: Dict[str, Any], 
    doc_metadata: DocumentMetadata,
    metadata_blocks: List[Dict[str, Any]]
) -> SemanticTable:
    """Interpret a single table semantically"""
    
    table_id = table.get('table_id', 'unknown')
    columns = table.get('columns', [])
    header_row = table.get('header_row', [])
    rows = table.get('rows', [])
    page_start = table.get('page_start', 1)
    page_end = table.get('page_end', 1)
    
    # Prepare context for LLM
    context = _build_table_context(table, doc_metadata, metadata_blocks)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a table semantic interpretation agent.

You are given a reconstructed table from OCR. Your job is to:
1. Infer meaningful column headers
2. Classify column data types
3. Normalize row data
4. Identify noise rows (footers, signatures, totals to exclude)
5. Determine table intent/purpose

Return ONLY valid JSON in this exact format:
{{
  "table_name": "Meaningful table name",
  "table_intent": "income_expenditure | balance_sheet | summary | data_table | other",
  "confidence": 0.0 to 1.0,
  "columns": [
    {{
      "name": "Column name",
      "original_name": "Original header if different or null",
      "data_type": "string | number | currency | date | identifier",
      "confidence": 0.0 to 1.0
    }}
  ],
  "rows": [
    {{
      "data": {{"Column1": "value1", "Column2": "value2"}},
      "is_noise": false,
      "noise_type": null
    }}
  ]
}}

CRITICAL RULES:
- Do NOT invent data
- Do NOT change numeric values
- Do NOT guess missing values
- Keep original numbers exactly as they appear
- Empty cells should be empty strings ""
- If a row is a footer/signature/total, mark is_noise=true
- Column names should be semantic (e.g., "Amount (Rs.)" not "Column 2")"""),
        ("human", "{context}")
    ])
    
    try:
        formatted = prompt.format_messages(context=context)
        response = llm.invoke(formatted)
        result = _parse_json_response(response.content)
        
        # Build semantic table
        return SemanticTable(
            table_id=table_id,
            table_name=result.get('table_name', f'Table {table_id}'),
            table_intent=result.get('table_intent', 'data_table'),
            confidence=result.get('confidence', 0.5),
            columns=result.get('columns', []),
            rows=result.get('rows', []),
            page_range=[page_start, page_end]
        )
        
    except Exception as e:
        logger.warning(f"Table interpretation failed for {table_id}: {e}")
        return _fallback_table(table)


def _build_table_context(
    table: Dict[str, Any], 
    doc_metadata: DocumentMetadata,
    metadata_blocks: List[Dict[str, Any]]
) -> str:
    """Build context string for LLM interpretation"""
    
    parts = []
    
    # Document metadata context
    if doc_metadata.title or doc_metadata.organization:
        parts.append("DOCUMENT CONTEXT:")
        if doc_metadata.title:
            parts.append(f"  Title: {doc_metadata.title}")
        if doc_metadata.organization:
            parts.append(f"  Organization: {doc_metadata.organization}")
        if doc_metadata.year:
            parts.append(f"  Year: {doc_metadata.year}")
        parts.append("")
    
    # Nearby metadata blocks (potential table titles)
    page_start = table.get('page_start', 1)
    nearby_blocks = [
        b for b in metadata_blocks 
        if b.get('page') == page_start and b.get('type') in ['title', 'header']
    ]
    if nearby_blocks:
        parts.append("NEARBY HEADERS:")
        for b in nearby_blocks[:3]:
            parts.append(f"  - {b.get('text', '')}")
        parts.append("")
    
    # Table structure
    parts.append("TABLE STRUCTURE:")
    
    header_row = table.get('header_row', [])
    if header_row:
        parts.append(f"  Detected Headers: {header_row}")
    else:
        parts.append("  Headers: Not detected (infer from data)")
    
    columns = table.get('columns', [])
    parts.append(f"  Column Count: {len(columns)}")
    parts.append("")
    
    # Table data (first 15 rows as sample)
    rows = table.get('rows', [])
    parts.append(f"TABLE DATA ({len(rows)} total rows, showing first 15):")
    
    for row in rows[:15]:
        cells = row.get('cells', [])
        row_str = " | ".join(str(c)[:50] for c in cells)  # Truncate long cells
        parts.append(f"  {row_str}")
    
    if len(rows) > 15:
        parts.append(f"  ... and {len(rows) - 15} more rows")
    
    return "\n".join(parts)


# -------------------- Utility Functions --------------------

def _parse_json_response(content: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling markdown blocks"""
    content = content.strip()
    
    # Remove markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.debug(f"Content was: {content[:500]}")
        raise


def _fallback_output(
    tables: List[Dict[str, Any]], 
    metadata_blocks: List[Dict[str, Any]]
) -> SemanticOutput:
    """Fallback when LLM is unavailable"""
    fallback_tables = [_fallback_table(t).to_dict() for t in tables]
    
    return SemanticOutput(
        tables=fallback_tables,
        metadata={"confidence": 0, "note": "LLM unavailable, using raw structure"},
        processing_notes=["Semantic interpretation skipped - LLM unavailable"]
    )


def _fallback_table(table: Dict[str, Any]) -> SemanticTable:
    """Create a basic semantic table without LLM"""
    table_id = table.get('table_id', 'unknown')
    header_row = table.get('header_row', [])
    rows = table.get('rows', [])
    columns = table.get('columns', [])
    
    # Use headers if available, else generate column names
    if header_row:
        col_names = header_row
    else:
        col_names = [f"Column_{i+1}" for i in range(len(columns))]
    
    # Convert rows to semantic format
    semantic_rows = []
    for row in rows:
        cells = row.get('cells', [])
        data = {}
        for i, col_name in enumerate(col_names):
            if i < len(cells):
                data[col_name] = cells[i]
            else:
                data[col_name] = ""
        semantic_rows.append({
            "data": data,
            "is_noise": False,
            "noise_type": None
        })
    
    return SemanticTable(
        table_id=table_id,
        table_name=f"Table {table_id}",
        table_intent="data_table",
        confidence=0.3,  # Low confidence for fallback
        columns=[
            {"name": name, "original_name": name, "data_type": "string", "confidence": 0.3}
            for name in col_names
        ],
        rows=semantic_rows,
        page_range=[table.get('page_start', 1), table.get('page_end', 1)]
    )
