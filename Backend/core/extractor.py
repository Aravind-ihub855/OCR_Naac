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

9.  ✨ COMPREHENSIVE ENTITY DETECTION
   - 🖼️ LOGOS: Detect logos/images in headers. Return type="logo", content="Description" (e.g. "Company/College Logo"), position="header".
   - ✍️ SIGNATURES: Detect signing blocks at bottom. Return type="signature", signer_name="Name", designation="Role".
   - 🏢 METADATA: Header text like "Company Name" or "Address" -> type="metadata".
   - 📝 TEXT BLOCKS: Standard paragraph text.

10. 📐 LAYOUT PRESERVATION
   - The output "page_elements" list MUST map the visual vertical flow of the page 1:1.
   - Order: Header -> Logo -> Title -> Text -> Table -> Text -> Signature.

═══════════════════════════════════════════════════════════════════════════════
═══════════════════════════════════════════════════════════════════════════════
FEW-SHOT EXAMPLES (Generic Templates - Do NOT copy values):
(Standard table examples 1-6 omitted for brevity)

EXAMPLE 7: Full Page with Visual Elements
──────────────────────────────────────────
INPUT:
[Top Left: Logo]   [Organization/Company Name]
                   [City, State]

        Balance Sheet (202X-2X)

[Table Content...]

(Signed)
[Name of Signatory]
[Designation]

OUTPUT:
{
  "page_elements": [
    {"type": "logo", "content": "Organization Logo", "position": "header", "order": 1},
    {"type": "metadata", "key": "Organization", "value": "[Organization Name]", "order": 2},
    {"type": "metadata", "key": "Location", "value": "[City, State]", "order": 3},
    {"type": "heading", "content": "Balance Sheet (202X-2X)", "order": 4},
    {"type": "table", "table_name": "Balance Sheet", "rows": [...], "order": 5},
    {"type": "signature", "signer_name": "[Name of Signatory]", "designation": "[Designation]", "order": 6}
  ]
}

═══════════════════════════════════════════════════════════════════════════════
STRICT JSON SCHEMA (Follow exactly):
═══════════════════════════════════════════════════════════════════════════════

{
  "metadata": {
    "organization": "string",
    "period": "string",
    "total_pages": "integer"
  },
  "page_elements": [
    {
      "type": "table",
      "order": "number",
      "table_name": "string",
      "table_heading": "string",
      "page_number": "number",
      "continues_on_next_page": "boolean",
      "columns": [{"name": "string", "data_type": "string", "confidence": "0-1"}],
      "rows": [
        {
          "data": {"col": "val"},
          "is_total": "boolean",
          "page": "number",
          "confidence": "0-1"
        }
      ]
    },
    {
      "type": "logo",
      "order": "number",
      "content": "string (Description)",
      "position": "header|footer"
    },
    {
      "type": "signature",
      "order": "number",
      "signer_name": "string",
      "designation": "string"
    },
    {
      "type": "metadata",
      "order": "number",
      "key": "string",
      "value": "string"
    },
    {
      "type": "text_block",
      "order": "number",
      "content": "string",
      "section_heading": "string"
    },
    {
      "type": "heading",
      "order": "number",
      "content": "string"
    }
  ]
}

NOW EXTRACT THE DOCUMENT. Return ONLY the JSON output (lines 381...).
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
            
            # --- ADAPTER: page_elements -> tables ---
            if "page_elements" in data:
                elements = data["page_elements"]
                tables = [e for e in elements if e.get("type") == "table"]
                data["tables"] = tables
            # ----------------------------------------

            # Ensure basic structure exists
            if "tables" not in data: 
                data["tables"] = []
            if "metadata" not in data: 
                data["metadata"] = {}
            if "page_elements" not in data:
                data["page_elements"] = []
            
            # Add processing metadata
            if "processing_notes" not in data:
                data["processing_notes"] = []
            data["processing_notes"].append("Extracted via Gemini 2.5 Flash with Enhanced Prompt v3")
            
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
