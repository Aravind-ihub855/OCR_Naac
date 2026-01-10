"""
Intelligent PDF → Excel Converter
Powered by Gemini 1.5 Flash Vision

API Endpoints Only - No Business Logic
"""

import logging
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from services.pdf_service import get_pdf_service

# Load environment variables
load_dotenv()

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

# -------------------- API Endpoints --------------------

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "online", "engine": "Gemini 1.5 Flash"}


@app.post("/convert")
async def convert_to_excel(file: UploadFile = File(...)):
    """
    Convert PDF to Excel.
    
    Main Pipeline: PDF → Gemini Vision → Data Mapping → Excel
    """
    pdf_service = get_pdf_service()
    excel_file, output_filename = await pdf_service.convert_pdf_to_excel(file)
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={output_filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@app.post("/analyze-only")
async def analyze_pdf(file: UploadFile = File(...)):
    """Returns the raw JSON extraction without converting to Excel."""
    pdf_service = get_pdf_service()
    result = await pdf_service.analyze_pdf(file)
    return result
