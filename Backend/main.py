"""
PDF → Excel Intelligent Data Mapping (Foundational Agent)
Layer 0 + Layer 1 + Layer 2 + Layer 3

Layer 0: Basic FastAPI entry point
Layer 1: Document classification (type, pages, tables)
Layer 2: Signal preservation (OCR, bounding boxes, block types)
Layer 3: Structural reconstruction (geometry-based table detection)
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

from document_classifier import analyze_document
from signal_preservor import preserve_signals
from structural_reconstructor import reconstruct_structure

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
    version="0.4.0"  # Updated for Layer 3
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
    return {"status": "ok", "message": "PDF Agent is running", "version": "0.4.0"}


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
        "message": "PDF received. Use /analyze, /extract, or /reconstruct for processing."
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


# -------------------- Layer 2: Signal Preservation --------------------
@app.post("/extract")
async def extract_signals(file: UploadFile = File(...), dpi: int = 300):
    """
    Layer 2: Extract and preserve all signals from PDF (lossless).
    
    This endpoint performs OCR and preserves:
    - Page boundaries
    - Bounding boxes for all text blocks
    - Block type hints (title, table, paragraph, etc.)
    - Reading order
    - Raw text per page
    
    Parameters:
    - file: PDF file to process
    - dpi: Resolution for OCR (default 300, higher = slower but more accurate)
    
    Returns page-wise structure with complete signal preservation.
    """
    logger.info(f"Extracting signals from: {file.filename} (DPI: {dpi})")
    
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Validate DPI range
    if dpi < 72 or dpi > 600:
        raise HTTPException(status_code=400, detail="DPI must be between 72 and 600")
    
    try:
        pdf_bytes = await file.read()
        
        # Run signal preservation
        signals = preserve_signals(pdf_bytes, dpi=dpi)
        
        return {
            "status": "extracted",
            "filename": file.filename,
            "dpi": dpi,
            "signals": signals.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Signal extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Signal extraction failed: {str(e)}")


# -------------------- Layer 3: Structural Reconstruction --------------------
@app.post("/reconstruct")
async def reconstruct_tables(file: UploadFile = File(...), dpi: int = 300):
    """
    Layer 3: Reconstruct table structures using geometry-based rules.
    
    This endpoint runs the full pipeline (Layer 2 → Layer 3):
    1. OCR with signal preservation
    2. Coordinate normalization
    3. Table region detection
    4. Column detection (X-axis clustering)
    5. Row detection (Y-axis grouping)
    6. Header anchoring
    7. Cross-page table continuation
    
    Returns:
    - tables: List of detected tables with columns, headers, and rows
    - metadata_blocks: Non-table content (titles, headers, footers)
    
    NO AI used - pure geometry and heuristics.
    """
    logger.info(f"Reconstructing structure from: {file.filename} (DPI: {dpi})")
    
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Validate DPI range
    if dpi < 72 or dpi > 600:
        raise HTTPException(status_code=400, detail="DPI must be between 72 and 600")
    
    try:
        pdf_bytes = await file.read()
        
        # Run Layer 2: Signal preservation
        logger.info("Running Layer 2: Signal preservation...")
        signals = preserve_signals(pdf_bytes, dpi=dpi)
        
        # Run Layer 3: Structural reconstruction
        logger.info("Running Layer 3: Structural reconstruction...")
        structure = reconstruct_structure(signals.to_dict())
        
        return {
            "status": "reconstructed",
            "filename": file.filename,
            "dpi": dpi,
            "structure": structure.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Structural reconstruction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Structural reconstruction failed: {str(e)}")


# -------------------- Run with Uvicorn --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

