"""
PDF → Excel Intelligent Data Mapping (Foundational Agent)
Layer 0 + Layer 1: Project Skeleton + Document Ingestion

Layer 0: Basic FastAPI entry point
Layer 1: Document classification (type, pages, tables)
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

from document_classifier import analyze_document

# -------------------- Logging Configuration --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("PDF_Agent")

# -------------------- FastAPI App --------------------
app = FastAPI(
    title="PDF → Excel Foundational Agent",
    description="Intelligent data mapping from complex PDFs to structured Excel",
    version="0.2.0"  # Updated for Layer 1
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------- Health Check --------------------
@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "PDF Agent is running", "version": "0.2.0"}


# -------------------- Layer 0: PDF Upload --------------------
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Layer 0: Accept PDF upload and return basic file info.
    """
    logger.info(f"Received file: {file.filename}")
    
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        logger.warning(f"Invalid file type: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted"
        )
    
    # Read file bytes
    pdf_bytes = await file.read()
    file_size = len(pdf_bytes)
    
    logger.info(f"File size: {file_size} bytes")
    
    return {
        "status": "received",
        "filename": file.filename,
        "size_bytes": file_size,
        "size_kb": round(file_size / 1024, 2),
        "message": "PDF received. Use /analyze for document classification."
    }


# -------------------- Layer 1: Document Analysis --------------------
@app.post("/analyze")
async def analyze_pdf(file: UploadFile = File(...)):
    """
    Layer 1: Analyze PDF structure and classify document type.
    
    Returns:
    - page_count: Number of pages
    - content_type: "text-based", "scanned", or "mixed"
    - has_tables: Boolean indicating table presence
    - table_count: Total tables detected
    - pages_with_text: Pages with extractable text
    - pages_with_images: Pages that need OCR
    - raw_text_preview: First 500 chars of text
    - page_details: Per-page breakdown
    """
    logger.info(f"Analyzing document: {file.filename}")
    
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    try:
        pdf_bytes = await file.read()
        
        # Run document analysis
        analysis = analyze_document(pdf_bytes)
        
        return {
            "status": "analyzed",
            "filename": file.filename,
            "analysis": analysis.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Document analysis failed: {str(e)}")


# -------------------- Run with Uvicorn --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
