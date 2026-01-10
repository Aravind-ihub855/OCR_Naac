import os
import time
import json
import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("PDF_Agent.Extractor")

class PDFExtractor:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def run_pipeline(self, pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Runs the multimodal extraction pipeline."""
        temp_path = f"tmp_{int(time.time())}_{filename}"
        with open(temp_path, "wb") as f:
            f.write(pdf_bytes)
        
        try:
            # 1. Upload to Gemini
            logger.info(f"Uploading {filename} to Gemini...")
            myfile = genai.upload_file(temp_path, mime_type="application/pdf")
            
            # 2. Wait for processing
            timeout = 30 # seconds
            start_wait = time.time()
            while myfile.state.name == "PROCESSING":
                if time.time() - start_wait > timeout:
                    raise TimeoutError("Gemini file processing timed out")
                time.sleep(2)
                myfile = genai.get_file(myfile.name)
            
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
            try:
                genai.delete_file(myfile.name)
            except:
                pass

    def _get_prompt(self) -> str:
        return """
        Extract all tables and metadata from this financial document.
        
        FORMAT RULES:
        1. Return ONLY valid JSON.
        2. Preserve dual-column financial layouts (Expenditure/Income or Liabilities/Assets).
        3. Keep Indian number formatting (lakhs/crores).
        4. Detect total rows and set "is_total": true.

        JSON STRUCTURE:
        {
          "metadata": {
            "organization": "string",
            "period": "string",
            "document_type": "string"
          },
          "tables": [
            {
              "table_name": "string",
              "columns": [{"name": "string", "data_type": "string|number"}],
              "rows": [{"data": {"col": "val"}, "is_total": boolean}]
            }
          ]
        }
        """

    def _parse_response(self, text: str) -> Dict[str, Any]:
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start == -1 or end == -1:
                raise ValueError("No JSON found in response")
            
            data = json.loads(text[start:end])
            
            # Ensure basic structure exists
            if "tables" not in data: data["tables"] = []
            if "metadata" not in data: data["metadata"] = {}
            data["processing_notes"] = ["Extracted via Gemini 1.5 Flash Vision"]
            
            return data
        except Exception as e:
            logger.error(f"JSON parsing error: {e}")
            return {"tables": [], "metadata": {}, "error": str(e)}

_extractor = None

def get_extractor():
    global _extractor
    if _extractor is None:
        _extractor = PDFExtractor()
    return _extractor
