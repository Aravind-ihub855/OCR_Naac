"""
PDF Processing Service

Business logic for PDF to Excel conversion.
"""

import logging
from typing import Tuple, Dict, Any
from io import BytesIO

from fastapi import UploadFile, HTTPException

from core.extractor import get_extractor
from core.data_mapper import map_to_excel

logger = logging.getLogger("PDF_Agent.Service")


class PDFService:
    """Service layer for PDF processing operations"""
    
    @staticmethod
    async def convert_pdf_to_excel(file: UploadFile) -> Tuple[BytesIO, str]:
        """
        Convert PDF to Excel file.
        
        Args:
            file: Uploaded PDF file
            
        Returns:
            Tuple of (excel_file, output_filename)
            
        Raises:
            HTTPException: If conversion fails
        """
        logger.info(f"=== Starting Conversion: {file.filename} ===")
        
        # Validate file type
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")
        
        try:
            # 1. Read PDF bytes
            pdf_bytes = await file.read()
            
            # 2. Extract Data using Gemini Multimodal Vision
            logger.info("Extracting data via Gemini API...")
            extractor = get_extractor()
            gemini_output = extractor.run_pipeline(pdf_bytes, file.filename)
            
            # 3. Handle cases where no tables are found
            if not gemini_output.get("tables"):
                logger.warning("No tabular data detected in document")
            
            # 4. Map to Structured Excel
            logger.info("Mapping to professional Excel format...")
            mapping_result, excel_file = map_to_excel(gemini_output)
            
            # 5. Prepare Filename
            output_filename = file.filename.rsplit('.', 1)[0] + ".xlsx"
            
            logger.info(f"=== Conversion Complete: {output_filename} ===")
            
            return excel_file, output_filename
            
        except Exception as e:
            logger.error(f"Pipeline failure: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
    
    @staticmethod
    async def analyze_pdf(file: UploadFile) -> Dict[str, Any]:
        """
        Analyze PDF and return raw JSON extraction without Excel conversion.
        
        Args:
            file: Uploaded PDF file
            
        Returns:
            Dictionary with status and extracted data
            
        Raises:
            HTTPException: If analysis fails
        """
        # Validate file type
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")
        
        try:
            pdf_bytes = await file.read()
            extractor = get_extractor()
            result = extractor.run_pipeline(pdf_bytes, file.filename)
            return {"status": "success", "data": result}
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# Singleton instance
_pdf_service: PDFService = None


def get_pdf_service() -> PDFService:
    """Get the singleton PDF service instance"""
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService()
    return _pdf_service
