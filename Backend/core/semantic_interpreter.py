"""
Semantic Interpretation Module - Layer 4 

This is where AI enters the pipeline.
Uses LLM to understand MEANING, not layout.

"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

from langchain_core.prompts import ChatPromptTemplate
from services.llm import get_groq_llm
from models import SemanticColumn, SemanticTable, DocumentMetadata, SemanticOutput

logger = logging.getLogger("PDF_Agent.SemanticInterpreter")


# -------------------- Main Entry Point --------------------

def interpret_semantics(structure: Dict[str, Any]) -> SemanticOutput:
    """Main entry point for Layer 4."""
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
        return _fallback_output(tables, metadata_blocks)
    
    processing_notes = []
    
    # Step 1: Extract document metadata
    logger.info("Extracting document metadata...")
    doc_metadata = _extract_document_metadata(llm, metadata_blocks, tables)
    processing_notes.append(f"Extracted metadata with {doc_metadata.confidence:.0%} confidence")
    
    # Step 2: Merge all table data and interpret as a whole document
    # This is crucial for financial documents that span multiple pages
    logger.info("Interpreting document tables...")
    interpreted_tables = _interpret_financial_document(llm, tables, doc_metadata, metadata_blocks)
    
    for table in interpreted_tables:
        processing_notes.append(f"Table '{table.table_name}' with {len(table.rows)} rows")
    
    logger.info(f"Semantic interpretation complete: {len(interpreted_tables)} tables")
    
    return SemanticOutput(
        tables=[t.to_dict() for t in interpreted_tables],
        metadata=doc_metadata.to_dict(),
        processing_notes=processing_notes
    )


# -------------------- Metadata Extraction --------------------

def _extract_document_metadata(
    llm, 
    metadata_blocks: List[Dict[str, Any]],
    tables: List[Dict[str, Any]]
) -> DocumentMetadata:
    """Extract document-level metadata using LLM"""
    
    # Combine all text sources
    all_text_parts = []
    
    # From metadata blocks
    for b in metadata_blocks[:30]:
        all_text_parts.append(b.get('text', ''))
    
    # From table raw text (first few rows)
    for table in tables[:2]:
        for row in table.get('rows', [])[:5]:
            cells = row.get('cells', [])
            all_text_parts.extend([str(c) for c in cells if c])
    
    combined_text = "\n".join(all_text_parts)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a document metadata extraction agent for Indian financial documents.

        Extract metadata from the provided OCR text. This may be from:
        - Income & Expenditure Accounts
        - Balance Sheets
        - Fixed Asset Schedules
        - NAAC Reports
        - Audit Reports

        Return ONLY valid JSON:
        {{
        "title": "Full document title",
        "organization": "Organization/College name",
        "address": "Full address if present",
        "year": "Financial year (e.g., '2020-2021')",
        "period": "Period description (e.g., 'For the year ended 31.03.2021')",
        "document_type": "Income and Expenditure Account | Balance Sheet | Fixed Assets Schedule | other",
        "auditor": "Auditor name and firm if present",
        "place": "Place of signing",
        "date": "Date of document",
        "confidence": 0.0 to 1.0
        }}

        Rules:
        - Extract ONLY what is explicitly stated
        - For organization, look for college/institution names
        - Indian format: dates as DD.MM.YYYY, amounts with Indian comma notation"""),
                ("human", "OCR Text:\n{text}")
    ])
    
    try:
        formatted = prompt.format_messages(text=combined_text[:4000])
        response = llm.invoke(formatted)
        result = _parse_json_response(response.content)
        
        return DocumentMetadata(
            title=result.get('title'),
            organization=result.get('organization'),
            address=result.get('address'),
            department=result.get('department'),
            year=result.get('year'),
            period=result.get('period'),
            document_type=result.get('document_type'),
            auditor=result.get('auditor'),
            place=result.get('place'),
            date=result.get('date'),
            confidence=result.get('confidence', 0.5)
        )
    except Exception as e:
        logger.warning(f"Metadata extraction failed: {e}")
        return DocumentMetadata(confidence=0.0)


# -------------------- Financial Document Interpretation --------------------

def _interpret_financial_document(
    llm, 
    tables: List[Dict[str, Any]], 
    doc_metadata: DocumentMetadata,
    metadata_blocks: List[Dict[str, Any]]
) -> List[SemanticTable]:
    """
    Interpret financial document tables.
    
    Handles special cases:
    - Income & Expenditure (dual-column: Expenditure | Amount | Income | Amount)
    - Balance Sheet (dual-column: Liabilities | Amount | Assets | Amount)
    - Fixed Assets Schedule (multi-column depreciation table)
    """
    
    # Collect all raw text from tables
    all_raw_text = []
    for table in tables:
        for row in table.get('rows', []):
            cells = row.get('cells', [])
            row_text = " | ".join(str(c) for c in cells if c)
            if row_text.strip():
                all_raw_text.append(row_text)
    
    raw_content = "\n".join(all_raw_text)
    
    # Also include metadata blocks for context
    context_text = "\n".join([b.get('text', '') for b in metadata_blocks[:20]])
    
    doc_type = doc_metadata.document_type or "Financial Statement"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert financial document parser for Indian educational institutions.

        You are given raw OCR text from a scanned financial document. Your task is to RECONSTRUCT the original table structure accurately.

        CRITICAL: Indian financial statements often have SIDE-BY-SIDE layouts:

        INCOME & EXPENDITURE ACCOUNT format:
        | Expenditure | Amount (Rs.) | Income | Amount (Rs.) |
        | Salary | 18,18,25,263 | Fees Receipts | 20,20,50,837 |

        BALANCE SHEET format:
        | Liabilities | Amount (Rs.P) | Assets | Amount (Rs.P) |
        | Capital Account | 50,00,000 | Fixed Assets | 9,36,10,338 |

        Return ONLY valid JSON with this structure:
        {{
        "tables": [
            {{
            "table_name": "Income and Expenditure Account",
            "table_intent": "income_expenditure",
            "columns": [
                {{"name": "Expenditure", "data_type": "string"}},
                {{"name": "Expenditure Amount (Rs.)", "data_type": "currency"}},
                {{"name": "Income", "data_type": "string"}},
                {{"name": "Income Amount (Rs.)", "data_type": "currency"}}
            ],
            "rows": [
                {{
                "data": {{
                    "Expenditure": "Salary",
                    "Expenditure Amount (Rs.)": "18,18,25,263",
                    "Income": "Fees Receipts",
                    "Income Amount (Rs.)": "20,20,50,837"
                }},
                "is_noise": false
                }}
            ]
            }}
        ]
        }}

        CRITICAL RULES:
        1. PRESERVE Indian number format exactly (e.g., 18,18,25,263 NOT 181825263)
        2. For dual-column tables, create 4 columns (Left Description, Left Amount, Right Description, Right Amount)
        3. Match expenditure items with their amounts on the LEFT side
        4. Match income items with their amounts on the RIGHT side
        5. Empty cells should be ""
        6. Include TOTAL rows with is_noise: false (they are important)
        7. Mark signature/footer/auditor rows as is_noise: true
        8. Extract ALL data rows - do not skip any
        9. If the document has multiple tables (e.g., Income & Expenditure + Balance Sheet), create separate table entries
        10. For Fixed Assets schedule, preserve all columns including depreciation details"""),
                ("human", """Document Type: {doc_type}
        Organization: {org}
        Period: {period}

        CONTEXT (headers/titles):
        {context}

        RAW TABLE DATA:
        {raw_data}

        Parse this into structured tables. Preserve ALL data and Indian number formatting.""")
    ])
    
    try:
        formatted = prompt.format_messages(
            doc_type=doc_type,
            org=doc_metadata.organization or "Unknown",
            period=doc_metadata.period or doc_metadata.year or "Unknown",
            context=context_text[:1000],
            raw_data=raw_content[:6000]  # Larger context for financial docs
        )
        
        response = llm.invoke(formatted)
        result = _parse_json_response(response.content)
        
        interpreted_tables = []
        for idx, table_data in enumerate(result.get('tables', [])):
            table = SemanticTable(
                table_id=f"table_{idx + 1}",
                table_name=table_data.get('table_name', f'Table {idx + 1}'),
                table_intent=table_data.get('table_intent', 'financial'),
                confidence=0.85,
                columns=table_data.get('columns', []),
                rows=table_data.get('rows', []),
                page_range=[1, len(tables)]
            )
            interpreted_tables.append(table)
        
        if not interpreted_tables:
            # Fallback to basic interpretation
            return [_fallback_table(t) for t in tables]
        
        return interpreted_tables
        
    except Exception as e:
        logger.error(f"Financial document interpretation failed: {e}")
        return [_fallback_table(t) for t in tables]


# -------------------- Utility Functions --------------------

def _parse_json_response(content: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling markdown blocks"""
    content = content.strip()
    
    # Remove markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        parts = content.split("```")
        if len(parts) >= 2:
            content = parts[1].strip()
    
    # Clean up common issues
    content = content.replace('\n', ' ').replace('\r', '')
    
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
        metadata={"confidence": 0, "note": "LLM unavailable"},
        processing_notes=["Semantic interpretation skipped - LLM unavailable"]
    )


def _fallback_table(table: Dict[str, Any]) -> SemanticTable:
    """Create a basic semantic table without LLM"""
    table_id = table.get('table_id', 'unknown')
    header_row = table.get('header_row', [])
    rows = table.get('rows', [])
    columns = table.get('columns', [])
    
    # Determine column count from data
    max_cols = 0
    for row in rows:
        cells = row.get('cells', [])
        max_cols = max(max_cols, len(cells))
    
    if not max_cols and columns:
        max_cols = len(columns)
    
    # Use headers if available
    if header_row and len(header_row) >= max_cols:
        col_names = header_row[:max_cols]
    else:
        col_names = [f"Column_{i+1}" for i in range(max_cols)]
    
    # Convert rows
    semantic_rows = []
    for row in rows:
        cells = row.get('cells', [])
        data = {}
        for i, col_name in enumerate(col_names):
            if i < len(cells):
                data[col_name] = cells[i] if cells[i] else ""
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
        confidence=0.3,
        columns=[
            {"name": name, "original_name": name, "data_type": "string", "confidence": 0.3}
            for name in col_names
        ],
        rows=semantic_rows,
        page_range=[table.get('page_start', 1), table.get('page_end', 1)]
    )
