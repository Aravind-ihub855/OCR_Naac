import os
import time
import json
import logging
from typing import Dict, Any, List, Optional

from services.llm import get_llm_config

logger = logging.getLogger("PDF_Agent.Extractor")

class PDFExtractor:
    def __init__(self):
        # Use centralized LLM configuration
        self.llm_config = get_llm_config()
        self.model = self.llm_config.get_model()

    def run_pipeline(self, pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Runs the multimodal extraction pipeline."""
        temp_path = f"tmp_{int(time.time())}_{filename}"
        with open(temp_path, "wb") as f:
            f.write(pdf_bytes)
        
        try:
            # 1. Upload to Gemini
            logger.info(f"Uploading {filename} to Gemini...")
            myfile = self.llm_config.upload_file(temp_path, mime_type="application/pdf")
            
            # 2. Wait for processing
            timeout = 30 # seconds
            start_wait = time.time()
            while myfile.state.name == "PROCESSING":
                if time.time() - start_wait > timeout:
                    raise TimeoutError("Gemini file processing timed out")
                time.sleep(2)
                myfile = self.llm_config.get_file(myfile.name)
            
            if myfile.state.name == "FAILED":
                raise Exception(f"File processing failed: {myfile.state.name}")

            # 3. Prompt for extraction
            prompt = self._get_prompt()
            logger.info("Extracting data via Gemini...")
            response = self.model.generate_content([myfile, prompt])
            
            # 4. Parse Response
            return self._parse_response(response.text)

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            self.llm_config.delete_file(myfile.name)

    def _get_prompt(self) -> str:
        return """
You are an expert financial document extraction AI specializing in Indian accounting formats.

TASK: Extract ALL tables and metadata from this financial document with PERFECT accuracy.

═══════════════════════════════════════════════════════════════════════════════
CRITICAL VALIDATION RULES (MUST FOLLOW):
═══════════════════════════════════════════════════════════════════════════════

1.  NEVER HALLUCINATE
   - If text is unclear or ambiguous, use null - NEVER guess or invent data
   - If a number is partially visible, preserve what you see as a string
   - If table structure is unclear, flag with "needs_review": true

2.  PRESERVE EVERYTHING
   - Extract EVERY row, even if formatting is inconsistent
   - Include ALL columns, even if some cells are empty
   - Maintain exact text as it appears (don't normalize or "fix" spelling)
   - Keep page numbers and note table continuations across pages

3.  INDIAN NUMBER FORMAT
   - Preserve comma placement exactly: 18,25,263 (NOT 1,825,263)
   - Keep lakhs/crores notation: 5.2 Cr, 18.5 L
   - Maintain decimal precision as shown
   - Handle formats: 8,18,25,263 or 81825263 or 8,18,25,263.00

4. ✓ CROSS-CHECK TOTALS
   - Verify that "Total" rows match sum of components
   - For dual-column layouts, check if sides balance
   - Flag discrepancies with "total_mismatch": true

5.  DUAL-COLUMN LAYOUTS
   - Detect side-by-side tables (Expenditure | Income, Assets | Liabilities)
   - Create TWO separate tables, not one merged table
   - Preserve alignment and matching row positions

6.  MULTI-PAGE TABLE CONTINUATION
   - If you see the SAME table headers on multiple pages, this is ONE table
   - Use IDENTICAL "table_name" for all parts of the same table
   - Add "page_number" field to track which page each row came from
   - Set "continues_on_next_page": true if table continues to next page
   - ALL rows from continuation pages should be in the SAME table object

7.  🏷️ TABLE HEADINGS & CONTEXT (CRITICAL)
   - Extract text appearing IMMEDIATELY ABOVE the table as "table_heading"
   - COMBINE multi-line headers: If there is a Main Title and a Sub-title (e.g., "Programme Name"), join them
   - Format: "Main Title | Sub-detail" (e.g., "Action Taken Report | Programme: Aerospace Engineering")
   - IF NO TITLE EXISTS: INFER a professional name from the page content
   - For multiple tables, ensure each has a DISTINCT, accurate name based on its specific content

8.  📄 STRICT TOPOLOGY (Merged Cells - CRITICAL)
   - If a cell spans multiple rows/columns, REPEAT the value in EVERY cell
   - DO NOT use empty strings, "ditto", or "do" for merged areas
   - Example: If "2023" spans 3 rows, output "2023" for ALL 3 rows

9.  📄 PAGE STRUCTURE
   - Extract ALL content: Tables, Key Text Blocks, Document Titles
   - Maintain exact order of elements as they appear on the page
   - CAPTURE EVERYTHING: Do not ignore paragraphs between tables

═══════════════════════════════════════════════════════════════════════════════
FEW-SHOT EXAMPLES (Learn from these):
═══════════════════════════════════════════════════════════════════════════════

EXAMPLE 1: Simple Single-Column Table
─────────────────────────────────────
INPUT (from PDF):
┌─────────────────────────────┬──────────────┐
│ Description                 │ Amount (₹)   │
├─────────────────────────────┼──────────────┤
│ Salary                      │ 8,18,25,263  │
│ Provident Fund              │ 51,45,525    │
│ Medical Allowance           │ 12,50,000    │
├─────────────────────────────┼──────────────┤
│ Total                       │ 8,82,20,788  │
└─────────────────────────────┴──────────────┘

CORRECT OUTPUT:
{
  "table_name": "Salary Expenditure",
  "columns": [
    {"name": "Description", "data_type": "string", "confidence": 0.95},
    {"name": "Amount", "data_type": "number", "confidence": 0.95}
  ],
  "rows": [
    {
      "data": {"Description": "Salary", "Amount": "8,18,25,263"},
      "is_total": false,
      "is_header": false,
      "confidence": 0.95
    },
    {
      "data": {"Description": "Provident Fund", "Amount": "51,45,525"},
      "is_total": false,
      "is_header": false,
      "confidence": 0.95
    },
    {
      "data": {"Description": "Medical Allowance", "Amount": "12,50,000"},
      "is_total": false,
      "is_header": false,
      "confidence": 0.95
    },
    {
      "data": {"Description": "Total", "Amount": "8,82,20,788"},
      "is_total": true,
      "is_header": false,
      "confidence": 0.95
    }
    }
  ]
}

EXAMPLE 6: Multi-Line Context & Merged Cells (Based on User Requirement)
────────────────────────────────────────────────────────────────────────
INPUT (from PDF):
Stakeholders' Feedback – Action Taken Report (2021-2022)
Programme : B.E. - Aerospace Engineering

┌────────┬─────────────┬──────────────────────────┐
│ S.No   │ Stakeholder │ Name, Designation        │
├────────┼─────────────┼──────────────────────────┤
│ 1      │ Faculty     │ Mr. Nehru K              │
└────────┴─────────────┴──────────────────────────┘

CORRECT OUTPUT:
{
  "page_elements": [
    {
      "type": "table",
      "table_name": "Action Taken Report - Aerospace",
      "table_heading": "Stakeholders' Feedback – Action Taken Report (2021-2022) | Programme : B.E. - Aerospace Engineering",
      "columns": [...],
      "rows": [...]
    }
  ]
}
────────────────────────────────────────
INPUT (from PDF):
┌──────────────────┬──────────┬──────────────────┬──────────┐
│ Expenditure      │ Amount   │ Income           │ Amount   │
├──────────────────┼──────────┼──────────────────┼──────────┤
│ Salaries         │ 50,00,000│ Grants           │ 75,00,000│
│ Infrastructure   │ 25,00,000│ Fees             │ 30,00,000│
│ Maintenance      │ 10,00,000│ Donations        │ 5,00,000 │
├──────────────────┼──────────┼──────────────────┼──────────┤
│ Total            │ 85,00,000│ Total            │1,10,00,000│
└──────────────────┴──────────┴──────────────────┴──────────┘

CORRECT OUTPUT (TWO separate tables):
{
  "tables": [
    {
      "table_name": "Expenditure",
      "columns": [
        {"name": "Description", "data_type": "string", "confidence": 0.95},
        {"name": "Amount", "data_type": "number", "confidence": 0.95}
      ],
      "rows": [
        {"data": {"Description": "Salaries", "Amount": "50,00,000"}, "is_total": false, "confidence": 0.95},
        {"data": {"Description": "Infrastructure", "Amount": "25,00,000"}, "is_total": false, "confidence": 0.95},
        {"data": {"Description": "Maintenance", "Amount": "10,00,000"}, "is_total": false, "confidence": 0.95},
        {"data": {"Description": "Total", "Amount": "85,00,000"}, "is_total": true, "confidence": 0.95}
      ]
    },
    {
      "table_name": "Income",
      "columns": [
        {"name": "Description", "data_type": "string", "confidence": 0.95},
        {"name": "Amount", "data_type": "number", "confidence": 0.95}
      ],
      "rows": [
        {"data": {"Description": "Grants", "Amount": "75,00,000"}, "is_total": false, "confidence": 0.95},
        {"data": {"Description": "Fees", "Amount": "30,00,000"}, "is_total": false, "confidence": 0.95},
        {"data": {"Description": "Donations", "Amount": "5,00,000"}, "is_total": false, "confidence": 0.95},
        {"data": {"Description": "Total", "Amount": "1,10,00,000"}, "is_total": true, "confidence": 0.95}
      ]
    }
  ]
}

EXAMPLE 3: Compound Row (needs explosion)
──────────────────────────────────────────
INPUT (from PDF):
"Salary Provident Fund 8,18,25,263 51,45,525"

CORRECT OUTPUT (as separate rows):
[
  {"data": {"Description": "Salary", "Amount": "8,18,25,263"}, "is_total": false},
  {"data": {"Description": "Provident Fund", "Amount": "51,45,525"}, "is_total": false}
]

EXAMPLE 4: Multi-Page Table Continuation (CRITICAL)
────────────────────────────────────────────────────
INPUT (from PDF):

Page 1:
┌─────────────────────┬──────────────┐
│ Description         │ Amount (₹)   │
├─────────────────────┼──────────────┤
│ Salary              │ 50,00,000    │
│ Rent                │ 10,00,000    │
└─────────────────────┴──────────────┘

Page 2 (SAME HEADERS - This is a continuation!):
┌─────────────────────┬──────────────┐
│ Description         │ Amount (₹)   │
├─────────────────────┼──────────────┤
│ Utilities           │ 5,00,000     │
│ Maintenance         │ 3,00,000     │
└─────────────────────┴──────────────┘

Page 3 (SAME HEADERS - Still the same table!):
┌─────────────────────┬──────────────┐
│ Description         │ Amount (₹)   │
├─────────────────────┼──────────────┤
│ Insurance           │ 2,00,000     │
│ Total               │ 70,00,000    │
└─────────────────────┴──────────────┘

CORRECT OUTPUT (ONE table with all rows, NOT three separate tables):
{
  "table_name": "Expenditure",
  "page_number": 1,
  "continues_on_next_page": true,
  "columns": [
    {"name": "Description", "data_type": "string", "confidence": 0.95},
    {"name": "Amount", "data_type": "number", "confidence": 0.95}
  ],
  "rows": [
    {"data": {"Description": "Salary", "Amount": "50,00,000"}, "is_total": false, "page": 1, "confidence": 0.95},
    {"data": {"Description": "Rent", "Amount": "10,00,000"}, "is_total": false, "page": 1, "confidence": 0.95},
    {"data": {"Description": "Utilities", "Amount": "5,00,000"}, "is_total": false, "page": 2, "confidence": 0.95},
    {"data": {"Description": "Maintenance", "Amount": "3,00,000"}, "is_total": false, "page": 2, "confidence": 0.95},
    {"data": {"Description": "Insurance", "Amount": "2,00,000"}, "is_total": false, "page": 3, "confidence": 0.95},
    {"data": {"Description": "Total", "Amount": "70,00,000"}, "is_total": true, "page": 3, "confidence": 0.95}
  ]
}

WRONG OUTPUT (Don't do this!):
{
  "tables": [
    {"table_name": "Expenditure_Page1", "rows": [...]},  // ❌ WRONG - Don't split!
    {"table_name": "Expenditure_Page2", "rows": [...]},  // ❌ WRONG - Same table!
    {"table_name": "Expenditure_Page3", "rows": [...]}   // ❌ WRONG - Still same table!
  ]
}

═══════════════════════════════════════════════════════════════════════════════
STRICT JSON SCHEMA (Follow exactly):
═══════════════════════════════════════════════════════════════════════════════

{
  "metadata": {
    "organization": "string (name of institution/company)",
    "period": "string (financial year/date range)",
    "document_type": "string (e.g., 'Income & Expenditure', 'Balance Sheet')",
    "total_pages": "number",
    "extraction_date": "string (ISO format)"
  },
  "tables": [
    {
      "table_name": "string (descriptive name - USE SAME NAME for continuation tables)",
      "table_heading": "string (EXACT text found above table in PDF - REQUIRED)",
      "page_number": "number (starting page of this table)",
      "continues_on_next_page": "boolean (true if table continues to next page)",
      "columns": [
        {
          "name": "string (column header)",
          "data_type": "string (one of: 'string', 'number', 'date')",
          "confidence": "number (0.0 to 1.0)"
        }
      ],
      "rows": [
        {
          "data": {
            "column_name": "value (preserve exact format for numbers)"
          },
          "is_total": "boolean (true if this is a sum/total row)",
          "is_header": "boolean (true if this is a sub-header row)",
          "page": "number (which page this row is from - REQUIRED)",
          "confidence": "number (0.0 to 1.0)",
          "needs_review": "boolean (true if uncertain)"
        }
      ],
      "validation": {
        "totals_match": "boolean",
        "total_expected": "number or null",
        "total_calculated": "number or null"
      }
    }
  ],
  "processing_notes": ["array of strings with any warnings or observations"]
}

═══════════════════════════════════════════════════════════════════════════════
EDGE CASES TO HANDLE:
═══════════════════════════════════════════════════════════════════════════════

1. Multi-page tables: Set "continues_on_next_page": true
2. Merged header cells: Combine into single column name
3. Sub-totals: Mark as "is_total": true
4. Empty cells: Use null or empty string ""
5. Unclear text: Set "needs_review": true, "confidence": <0.7
6. Rotated/sideways tables: Extract normally, note in processing_notes
7. Handwritten annotations: Include in processing_notes, don't mix with table data

═══════════════════════════════════════════════════════════════════════════════
FINAL CHECKLIST (Before responding):
═══════════════════════════════════════════════════════════════════════════════

✓ All tables extracted (none missed)
✓ All rows included (even partial/unclear ones)
✓ Indian number format preserved
✓ Totals verified (or flagged if mismatch)
✓ Dual-column layouts split into separate tables
✓ Confidence scores assigned
✓ No hallucinated data
✓ Valid JSON structure

NOW EXTRACT THE DOCUMENT. Return ONLY the JSON output, no additional text.
        """

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse Gemini response with enhanced validation and error handling."""
        try:
            # Extract JSON from response
            start = text.find('{')
            end = text.rfind('}') + 1
            if start == -1 or end == -1:
                raise ValueError("No JSON found in response")
            
            data = json.loads(text[start:end])
            
            # Ensure basic structure exists
            if "tables" not in data: 
                data["tables"] = []
            if "metadata" not in data: 
                data["metadata"] = {}
            
            # Add processing metadata
            if "processing_notes" not in data:
                data["processing_notes"] = []
            data["processing_notes"].append("Extracted via Gemini 2.5 Flash with Enhanced Prompt v2")
            
            # Validate and enhance table structure
            for table in data.get("tables", []):
                # Ensure required fields exist
                if "columns" not in table:
                    table["columns"] = []
                if "rows" not in table:
                    table["rows"] = []
                
                # Add default confidence if missing
                for col in table.get("columns", []):
                    if "confidence" not in col:
                        col["confidence"] = 0.8
                
                for row in table.get("rows", []):
                    if "confidence" not in row:
                        row["confidence"] = 0.8
                    if "is_total" not in row:
                        row["is_total"] = False
                    if "is_header" not in row:
                        row["is_header"] = False
                    if "needs_review" not in row:
                        row["needs_review"] = False
                    if "page" not in row:
                        # Default to table's page_number if row doesn't specify
                        row["page"] = table.get("page_number", 1)
                
                # Add validation structure if missing
                if "validation" not in table:
                    table["validation"] = {
                        "totals_match": None,
                        "total_expected": None,
                        "total_calculated": None
                    }
            
            # Log quality metrics
            total_tables = len(data.get("tables", []))
            total_rows = sum(len(t.get("rows", [])) for t in data.get("tables", []))
            low_confidence_rows = sum(
                1 for t in data.get("tables", []) 
                for r in t.get("rows", []) 
                if r.get("confidence", 1.0) < 0.7
            )
            
            logger.info(f"Extraction complete: {total_tables} tables, {total_rows} rows, {low_confidence_rows} low-confidence rows")
            
            if low_confidence_rows > 0:
                data["processing_notes"].append(f"⚠️ {low_confidence_rows} rows flagged for manual review (confidence < 0.7)")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Response text: {text[:500]}...")
            return {
                "tables": [], 
                "metadata": {}, 
                "error": f"JSON parsing failed: {str(e)}",
                "processing_notes": ["Failed to parse Gemini response as JSON"]
            }
        except Exception as e:
            logger.error(f"Unexpected error in response parsing: {e}", exc_info=True)
            return {
                "tables": [], 
                "metadata": {}, 
                "error": str(e),
                "processing_notes": ["Unexpected error during response parsing"]
            }

_extractor = None

def get_extractor():
    global _extractor
    if _extractor is None:
        _extractor = PDFExtractor()
    return _extractor
