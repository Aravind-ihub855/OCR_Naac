"""
Intelligent PDF → Excel Converter
Powered by Gemini 1.5 Flash Vision
"""

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from core.extractor import get_extractor
from core.data_mapper import map_to_excel

# -------------------- Logging Configuration --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("PDF_Agent")

# -------------------- FastAPI App --------------------
app = FastAPI(
    title="Intelligent PDF → Excel Parser",
    description="High-accuracy financial document extraction using Gemini Vision API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "online", "engine": "Gemini 1.5 Flash"}

# -------------------- Core Pipeline --------------------

@app.post("/convert")
async def convert_to_excel(file: UploadFile = File(...)):
    """
    Main Pipeline: PDF → Gemini Vision → Data Mapping → Excel
    
    This replaces all legacy layers (OCR, Geometry, Reasoning) 
    with a single high-accuracy multimodal API call.
    """
    logger.info(f"=== Starting Conversion: {file.filename} ===")
    
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
        
        # 4. Map to Structured Excel (Layer 6)
        logger.info("Mapping to professional Excel format...")
        mapping_result, excel_file = map_to_excel(gemini_output)
        
        # 5. Prepare Filename
        output_filename = file.filename.rsplit('.', 1)[0] + ".xlsx"
        
        logger.info(f"=== Conversion Complete: {output_filename} ===")
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={output_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
        
    except Exception as e:
        logger.error(f"Pipeline failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

@app.post("/analyze-only")
async def analyze_pdf(file: UploadFile = File(...)):
    """Returns the raw JSON extraction without converting to Excel."""
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
