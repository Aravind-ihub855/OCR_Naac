import os
import time
import json
import logging
from typing import Dict, Any, List, Optional

from typing import Dict, Any, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from services.llm import get_llm_config
from core.prompts import EXTRACTION_SYSTEM_PROMPT

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
            myfile = self._upload_file_with_retry(temp_path, "application/pdf")
            
            # 2. Wait for processing
            self._wait_for_processing(myfile)
            
            # Refresh file state after wait
            myfile = self.llm_config.get_file(myfile.name)
            if myfile.state.name == "FAILED":
                raise Exception(f"File processing failed: {myfile.state.name}")

            # 3. Prompt for extraction
            prompt = self._get_prompt()
            logger.info("Extracting data via Gemini...")
            response = self._generate_content_with_retry(myfile, prompt)
            
            # 4. Parse Response
            return self._parse_response(response.text)

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            # Cleanup remote file if it exists
            try:
                if 'myfile' in locals():
                    self.llm_config.delete_file(myfile.name)
            except Exception:
                pass

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _upload_file_with_retry(self, path: str, mime_type: str):
        return self.llm_config.upload_file(path, mime_type=mime_type)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _generate_content_with_retry(self, file_obj, prompt):
        return self.model.generate_content([file_obj, prompt])

    def _wait_for_processing(self, file_obj):
        """Wait for file processing with timeout."""
        timeout = 60
        start_wait = time.time()
        
        while True:
            current_file = self.llm_config.get_file(file_obj.name)
            if current_file.state.name != "PROCESSING":
                break
                
            if time.time() - start_wait > timeout:
                raise TimeoutError("Gemini file processing timed out")
            time.sleep(2)

    def _get_prompt(self) -> str:
        return EXTRACTION_SYSTEM_PROMPT

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
