"""
Document Reasoning Layer - Layer 5 

Approach:
1. Collect text PER PAGE (not combined)
2. Detect table types on EACH PAGE
3. Reconstruct each table separately
4. Combine all tables in output
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from langchain_core.prompts import ChatPromptTemplate
from services.llm import get_groq_llm
from models import DocumentArchetype, ARCHETYPE_SCHEMAS, ReasonedTable, DocumentReasoning

logger = logging.getLogger("PDF_Agent.DocumentReasoner")


# -------------------- Main Entry Point --------------------

def reason_document(
    ocr_signals: Dict[str, Any],
    structural_output: Dict[str, Any]
) -> DocumentReasoning:
    """
    Main entry point - Enhanced for MULTI-TABLE documents.
    
    Approach: Process EACH PAGE separately to detect and extract all tables.
    """
    logger.info("Starting Document Reasoning (Layer 5) - Multi-Table v3")
    
    reasoning_chain = []
    all_tables = []
    
    # Initialize LLM
    try:
        llm = get_groq_llm()
    except ValueError as e:
        logger.error(f"LLM initialization failed: {e}")
        return _fallback_reasoning(structural_output)
    
    # Step 1: Collect text PER PAGE
    pages = ocr_signals.get('pages', [])
    page_count = len(pages)
    reasoning_chain.append(f"Processing {page_count} pages")
    
    # Step 2: Process EACH page to detect and extract tables
    for page_idx, page in enumerate(pages):
        page_num = page_idx + 1
        logger.info(f"Processing page {page_num}/{page_count}...")
        
        # Collect page text with layout info
        page_text, layout_info = _collect_page_text(page)
        
        if not page_text.strip():
            reasoning_chain.append(f"Page {page_num}: Empty, skipped")
            continue
        
        # Detect what type of table is on this page
        archetype = _detect_page_archetype(llm, page_text)
        reasoning_chain.append(f"Page {page_num}: Detected {archetype.value}")
        
        # Extract table based on archetype
        table = _extract_table_from_page(llm, page_text, layout_info, archetype, page_num)
        
        if table:
            all_tables.append(table)
            reasoning_chain.append(f"Page {page_num}: Extracted {table.table_name} ({len(table.rows)} rows)")
        else:
            reasoning_chain.append(f"Page {page_num}: No table extracted")
    
    # Step 3: Extract metadata from full document
    full_text = '\n'.join([_collect_page_text(p)[0] for p in pages])
    metadata = _extract_metadata(llm, full_text[:3000])
    
    logger.info(f"Document reasoning complete: {len(all_tables)} tables from {page_count} pages")
    
    # Determine primary archetype from first table
    primary_archetype = all_tables[0].archetype if all_tables else "general_table"
    
    return DocumentReasoning(
        document_type="Financial Statements" if len(all_tables) > 1 else (all_tables[0].table_name if all_tables else "Unknown"),
        archetype=primary_archetype,
        organization=metadata.get('organization', ''),
        period=metadata.get('period', ''),
        tables=[t.to_dict() for t in all_tables],
        metadata=metadata,
        reasoning_chain=reasoning_chain
    )


# -------------------- Page Text Collection --------------------

def _collect_page_text(page: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Collect text from a single page with layout info."""
    
    blocks = page.get('blocks', [])
    page_width = page.get('width', 1) or 1
    
    text_parts = []
    left_blocks = []
    right_blocks = []
    
    for block in blocks:
        text = block.get('text', '').strip()
        if not text:
            continue
        
        left = block.get('left', 0) or 0
        normalized_x = left / page_width if page_width > 0 else 0.5
        
        if normalized_x < 0.5:
            left_blocks.append(text)
        else:
            right_blocks.append(text)
        
        text_parts.append(text)
    
    layout_info = {
        "left_blocks": left_blocks,
        "right_blocks": right_blocks
    }
    
    return '\n'.join(text_parts), layout_info


# -------------------- Page Archetype Detection --------------------

def _detect_page_archetype(llm, page_text: str) -> DocumentArchetype:
    """Detect what type of financial table is on this page."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Classify this page of an Indian financial document.

What type of table is on this page?

Options:
1. income_expenditure - Contains: Salary, Fees Receipts, Expenditure items, Income items, "Excess of Income/Expenditure"
2. balance_sheet - Contains: Liabilities, Assets, Capital Account, Fixed Assets, Bank accounts
3. fixed_assets - Contains: Depreciation, WDV (Written Down Value), Rate %, Asset descriptions, multiple numeric columns
4. general_table - None of the above

Return ONLY JSON:
{{"archetype": "income_expenditure | balance_sheet | fixed_assets | general_table"}}"""),
        ("human", "Page text:\n{text}")
    ])
    
    try:
        response = llm.invoke(prompt.format_messages(text=page_text[:4000]))
        result = _parse_json_response(response.content)
        
        archetype_map = {
            'income_expenditure': DocumentArchetype.INCOME_EXPENDITURE,
            'balance_sheet': DocumentArchetype.BALANCE_SHEET,
            'fixed_assets': DocumentArchetype.FIXED_ASSETS,
            'general_table': DocumentArchetype.GENERAL_TABLE
        }
        
        return archetype_map.get(result.get('archetype', 'general_table'), DocumentArchetype.GENERAL_TABLE)
        
    except Exception as e:
        logger.warning(f"Page archetype detection failed: {e}")
        return DocumentArchetype.GENERAL_TABLE


# -------------------- Table Extraction per Archetype --------------------

def _extract_table_from_page(
    llm, 
    page_text: str, 
    layout_info: Dict[str, Any],
    archetype: DocumentArchetype,
    page_num: int
) -> Optional[ReasonedTable]:
    """Extract table from a single page based on its archetype."""
    
    if archetype == DocumentArchetype.INCOME_EXPENDITURE:
        return _extract_income_expenditure(llm, page_text, layout_info, page_num)
    elif archetype == DocumentArchetype.BALANCE_SHEET:
        return _extract_balance_sheet(llm, page_text, layout_info, page_num)
    elif archetype == DocumentArchetype.FIXED_ASSETS:
        return _extract_fixed_assets(llm, page_text, layout_info, page_num)
    else:
        return _extract_general_table(llm, page_text, layout_info, page_num)


def _extract_income_expenditure(llm, text: str, layout: Dict, page_num: int) -> Optional[ReasonedTable]:
    """Extract Income & Expenditure Account."""
    
    left_text = '\n'.join(layout.get('left_blocks', []))
    right_text = '\n'.join(layout.get('right_blocks', []))
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are reconstructing an Indian Income and Expenditure Account from OCR.

STRUCTURE:
- LEFT SIDE: Expenditure items (Salary, PF, ESI, Gratuity, etc.) with amounts
- RIGHT SIDE: Income items (Fees Receipts, Interest, Consultancy, etc.) with amounts
- Format: | Expenditure | Amount (Rs.) | Income | Amount (Rs.) |

RULES:
1. Preserve Indian number format exactly (18,18,25,263)
2. Extract ALL rows, don't skip any
3. Include "Excess of Income over Expenditure" as the balancing item
4. Mark the TOTAL row with is_total: true
5. If one side has more items, leave the other side cells empty ""

Return ONLY JSON:
{{
  "table_name": "Income and Expenditure Account",
  "rows": [
    {{"Expenditure": "Salary", "Expenditure Amount (Rs.)": "18,18,25,263", "Income": "Fees Receipts", "Income Amount (Rs.)": "20,20,50,837", "is_total": false}},
    {{"Expenditure": "Provident Fund", "Expenditure Amount (Rs.)": "51,45,523", "Income": "Other Fee Receipts", "Income Amount (Rs.)": "3,57,44,893", "is_total": false}},
    ...
    {{"Expenditure": "Total", "Expenditure Amount (Rs.)": "24,82,58,295", "Income": "Total", "Income Amount (Rs.)": "24,82,58,295", "is_total": true}}
  ]
}}"""),
        ("human", """FULL PAGE TEXT:
{text}

LEFT SIDE (Expenditure):
{left}

RIGHT SIDE (Income):
{right}

Extract the complete Income and Expenditure table.""")
    ])
    
    try:
        response = llm.invoke(prompt.format_messages(
            text=text[:8000], left=left_text[:3000], right=right_text[:3000]
        ))
        result = _parse_json_response(response.content)
        
        rows = []
        for r in result.get('rows', []):
            rows.append({
                "data": {
                    "Expenditure": r.get("Expenditure", ""),
                    "Expenditure Amount (Rs.)": r.get("Expenditure Amount (Rs.)", ""),
                    "Income": r.get("Income", ""),
                    "Income Amount (Rs.)": r.get("Income Amount (Rs.)", "")
                },
                "is_total": r.get("is_total", False),
                "is_noise": False
            })
        
        return ReasonedTable(
            table_name="Income and Expenditure Account",
            archetype=DocumentArchetype.INCOME_EXPENDITURE.value,
            columns=ARCHETYPE_SCHEMAS[DocumentArchetype.INCOME_EXPENDITURE]['columns'],
            rows=rows,
            constraints_validated={},
            confidence=0.9,
            reasoning_notes=["Dual-column I&E reconstruction"],
            page_number=page_num
        )
        
    except Exception as e:
        logger.error(f"I&E extraction failed: {e}")
        return None


def _extract_balance_sheet(llm, text: str, layout: Dict, page_num: int) -> Optional[ReasonedTable]:
    """Extract Balance Sheet."""
    
    left_text = '\n'.join(layout.get('left_blocks', []))
    right_text = '\n'.join(layout.get('right_blocks', []))
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are reconstructing an Indian Balance Sheet from OCR.

STRUCTURE:
- LEFT SIDE: Liabilities (God's Account, Capital Account, Current Account, Deposits, Creditors)
- RIGHT SIDE: Assets (Fixed Assets, Loans, Receivables, Bank Accounts, Cash)
- MUST BALANCE: Total Liabilities = Total Assets

Handle sub-items like "Current Account with - Central Bank of India" as separate rows.

Return ONLY JSON:
{{
  "table_name": "Balance Sheet",
  "rows": [
    {{"Liabilities": "God's Account", "Liabilities Amount (Rs.)": "1,808.00", "Assets": "Fixed Assets", "Assets Amount (Rs.)": "9,36,10,338", "is_total": false}},
    ...
    {{"Liabilities": "Total", "Liabilities Amount (Rs.)": "16,62,07,490", "Assets": "Total", "Assets Amount (Rs.)": "16,62,07,490", "is_total": true}}
  ]
}}"""),
        ("human", "PAGE TEXT:\n{text}\n\nLEFT (Liabilities):\n{left}\n\nRIGHT (Assets):\n{right}")
    ])
    
    try:
        response = llm.invoke(prompt.format_messages(
            text=text[:8000], left=left_text[:3000], right=right_text[:3000]
        ))
        result = _parse_json_response(response.content)
        
        rows = []
        for r in result.get('rows', []):
            rows.append({
                "data": {
                    "Liabilities": r.get("Liabilities", ""),
                    "Liabilities Amount (Rs.)": r.get("Liabilities Amount (Rs.)", ""),
                    "Assets": r.get("Assets", ""),
                    "Assets Amount (Rs.)": r.get("Assets Amount (Rs.)", "")
                },
                "is_total": r.get("is_total", False),
                "is_noise": False
            })
        
        return ReasonedTable(
            table_name="Balance Sheet",
            archetype=DocumentArchetype.BALANCE_SHEET.value,
            columns=ARCHETYPE_SCHEMAS[DocumentArchetype.BALANCE_SHEET]['columns'],
            rows=rows,
            constraints_validated={},
            confidence=0.9,
            reasoning_notes=["Dual-column Balance Sheet reconstruction"],
            page_number=page_num
        )
        
    except Exception as e:
        logger.error(f"Balance Sheet extraction failed: {e}")
        return None


def _extract_fixed_assets(llm, text: str, layout: Dict, page_num: int) -> Optional[ReasonedTable]:
    """Extract Fixed Assets Schedule."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are reconstructing an Indian Fixed Assets Schedule from OCR.

This is a MULTI-COLUMN depreciation table with columns:
- Sl. No.
- Description of Assets
- WDV as on Opening (01.04.YYYY)
- Additions
- Deletions
- Total
- Rate %
- Depreciation
- WDV as on Closing (31.03.YYYY)

Return JSON:
{{
  "table_name": "Details of Fixed Assets",
  "rows": [
    {{"Sl. No.": "1", "Description of Assets": "Computer and Accessories", "WDV Opening": "70,17,556", "Additions": "38,979", "Deletions": "-", "Total": "70,56,535", "Rate %": "40", "Depreciation": "28,21,048", "WDV Closing": "42,25,958", "is_total": false}},
    ...
    {{"Sl. No.": "", "Description of Assets": "Total", "WDV Opening": "10,70,77,731", ..., "is_total": true}}
  ]
}}"""),
        ("human", "Page text:\n{text}")
    ])
    
    try:
        response = llm.invoke(prompt.format_messages(text=text[:10000]))
        result = _parse_json_response(response.content)
        
        columns = ARCHETYPE_SCHEMAS[DocumentArchetype.FIXED_ASSETS]['columns']
        rows = []
        for r in result.get('rows', []):
            data = {col['name']: r.get(col['name'], '') for col in columns}
            rows.append({"data": data, "is_total": r.get("is_total", False), "is_noise": False})
        
        return ReasonedTable(
            table_name="Details of Fixed Assets",
            archetype=DocumentArchetype.FIXED_ASSETS.value,
            columns=columns,
            rows=rows,
            constraints_validated={},
            confidence=0.85,
            reasoning_notes=["Multi-column Fixed Assets reconstruction"],
            page_number=page_num
        )
        
    except Exception as e:
        logger.error(f"Fixed Assets extraction failed: {e}")
        return None


def _extract_general_table(llm, text: str, layout: Dict, page_num: int) -> Optional[ReasonedTable]:
    """Extract general table."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Extract any tables from this page text.
Return JSON: {{"table_name": "...", "columns": [...], "rows": [...]}}"""),
        ("human", "{text}")
    ])
    
    try:
        response = llm.invoke(prompt.format_messages(text=text[:6000]))
        result = _parse_json_response(response.content)
        
        columns = result.get('columns', [{"name": "Content", "type": "string"}])
        rows = []
        for r in result.get('rows', []):
            if isinstance(r, dict):
                data = {col.get('name', f'Col{i}'): r.get(col.get('name', ''), '') for i, col in enumerate(columns)}
                rows.append({"data": data, "is_total": False, "is_noise": False})
        
        if not rows:
            return None
        
        return ReasonedTable(
            table_name=result.get('table_name', 'Extracted Table'),
            archetype='general_table',
            columns=columns,
            rows=rows,
            constraints_validated={},
            confidence=0.6,
            reasoning_notes=["General extraction"],
            page_number=page_num
        )
        
    except:
        return None


# -------------------- Metadata Extraction --------------------

def _extract_metadata(llm, text: str) -> Dict[str, Any]:
    """Extract document metadata."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Extract metadata from this Indian financial document.

Return JSON:
{{
  "organization": "College/Institution name",
  "address": "Full address",
  "period": "For the year ended DD.MM.YYYY",
  "year": "YYYY-YYYY",
  "auditor": "Auditor firm name",
  "place": "City",
  "date": "DD.MM.YYYY"
}}"""),
        ("human", "{text}")
    ])
    
    try:
        response = llm.invoke(prompt.format_messages(text=text))
        return _parse_json_response(response.content)
    except:
        return {}


# -------------------- Utility --------------------

def _parse_json_response(content: str) -> Dict[str, Any]:
    """Parse JSON from LLM response."""
    content = content.strip()
    
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        parts = content.split("```")
        if len(parts) >= 2:
            content = parts[1].strip()
    
    return json.loads(content)


def _fallback_reasoning(structural_output: Dict[str, Any]) -> DocumentReasoning:
    """Fallback when LLM unavailable."""
    return DocumentReasoning(
        document_type="Unknown",
        archetype="general_table",
        organization="",
        period="",
        tables=[],
        metadata={},
        reasoning_chain=["Fallback: LLM unavailable"]
    )
