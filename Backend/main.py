"""
PDF → Excel Intelligent Data Mapping (Foundational Agent)
Layer 0 + Layer 1 + Layer 2 + Layer 3 + Layer 4 + Layer 5

Layer 0: Basic FastAPI entry point
Layer 1: Document classification (type, pages, tables)
Layer 2: Signal preservation (OCR, bounding boxes, block types)
Layer 3: Structural reconstruction (geometry-based table detection)
Layer 4: Semantic interpretation (LLM-based understanding)
Layer 5: Data mapping (Excel-ready output)
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from document_classifier import analyze_document
from signal_preservor import preserve_signals
from structural_reconstructor import reconstruct_structure
from semantic_interpreter import interpret_semantics
from data_mapper import map_to_excel

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
    version="1.0.0"
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
    return {"status": "ok", "message": "PDF Agent is running", "version": "1.0.0"}


# -------------------- Layer 0: PDF Upload --------------------
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Layer 0: Accept PDF upload and return basic file info."""
    logger.info(f"Received file: {file.filename}")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    pdf_bytes = await file.read()
    file_size = len(pdf_bytes)
    
    return {
        "status": "received",
        "filename": file.filename,
        "size_bytes": file_size,
        "size_kb": round(file_size / 1024, 2),
        "message": "PDF received. Use /convert for full pipeline."
    }


# -------------------- Layer 1: Document Analysis --------------------
@app.post("/analyze")
async def analyze_pdf(file: UploadFile = File(...)):
    """Layer 1: Analyze PDF structure and classify document type."""
    logger.info(f"Analyzing document: {file.filename}")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    try:
        pdf_bytes = await file.read()
        analysis = analyze_document(pdf_bytes)
        return {"status": "analyzed", "filename": file.filename, "analysis": analysis.to_dict()}
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Layer 2: Signal Preservation --------------------
@app.post("/extract")
async def extract_signals(file: UploadFile = File(...), dpi: int = 300):
    """Layer 2: Extract and preserve all signals from PDF (OCR + bounding boxes)."""
    logger.info(f"Extracting signals from: {file.filename} (DPI: {dpi})")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if dpi < 72 or dpi > 600:
        raise HTTPException(status_code=400, detail="DPI must be between 72 and 600")
    
    try:
        pdf_bytes = await file.read()
        signals = preserve_signals(pdf_bytes, dpi=dpi)
        return {"status": "extracted", "filename": file.filename, "dpi": dpi, "signals": signals.to_dict()}
    except Exception as e:
        logger.error(f"Signal extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Layer 3: Structural Reconstruction --------------------
@app.post("/reconstruct")
async def reconstruct_tables(file: UploadFile = File(...), dpi: int = 300):
    """Layer 3: Reconstruct table structures using geometry-based rules."""
    logger.info(f"Reconstructing structure from: {file.filename} (DPI: {dpi})")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if dpi < 72 or dpi > 600:
        raise HTTPException(status_code=400, detail="DPI must be between 72 and 600")
    
    try:
        pdf_bytes = await file.read()
        signals = preserve_signals(pdf_bytes, dpi=dpi)
        structure = reconstruct_structure(signals.to_dict())
        return {"status": "reconstructed", "filename": file.filename, "dpi": dpi, "structure": structure.to_dict()}
    except Exception as e:
        logger.error(f"Structural reconstruction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Layer 4: Semantic Interpretation --------------------
@app.post("/interpret")
async def interpret_document(file: UploadFile = File(...), dpi: int = 300):
    """Layer 4: Semantic interpretation using LLM. Requires GROQ_API_KEY."""
    logger.info(f"Interpreting document: {file.filename} (DPI: {dpi})")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if dpi < 72 or dpi > 600:
        raise HTTPException(status_code=400, detail="DPI must be between 72 and 600")
    
    try:
        pdf_bytes = await file.read()
        signals = preserve_signals(pdf_bytes, dpi=dpi)
        structure = reconstruct_structure(signals.to_dict())
        semantic = interpret_semantics(structure.to_dict())
        return {"status": "interpreted", "filename": file.filename, "dpi": dpi, "result": semantic.to_dict()}
    except Exception as e:
        logger.error(f"Semantic interpretation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Layer 5: Full Pipeline → Excel --------------------
@app.post("/convert")
async def convert_to_excel(file: UploadFile = File(...), dpi: int = 300):
    """
    FULL PIPELINE: PDF → Excel conversion.
    
    Runs all 5 layers:
    1. Layer 2: OCR with signal preservation
    2. Layer 3: Structural reconstruction
    3. Layer 4: Semantic interpretation (LLM)
    4. Layer 5: Data mapping and Excel generation
    
    Returns Excel file (.xlsx) with formatted tables.
    Requires GROQ_API_KEY in .env file.
    """
    logger.info(f"=== FULL PIPELINE: Converting {file.filename} to Excel ===")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if dpi < 72 or dpi > 600:
        raise HTTPException(status_code=400, detail="DPI must be between 72 and 600")
    
    try:
        pdf_bytes = await file.read()
        
        # Layer 2: Signal preservation
        logger.info("Layer 2: Signal preservation...")
        signals = preserve_signals(pdf_bytes, dpi=dpi)
        
        # Layer 3: Structural reconstruction
        logger.info("Layer 3: Structural reconstruction...")
        structure = reconstruct_structure(signals.to_dict())
        
        # Layer 4: Semantic interpretation
        logger.info("Layer 4: Semantic interpretation...")
        semantic = interpret_semantics(structure.to_dict())
        
        # Layer 5: Data mapping and Excel generation
        logger.info("Layer 5: Data mapping and Excel generation...")
        mapping_result, excel_file = map_to_excel(semantic.to_dict())
        
        # Generate output filename
        output_filename = file.filename.replace('.pdf', '.xlsx').replace('.PDF', '.xlsx')
        if not output_filename.endswith('.xlsx'):
            output_filename += '.xlsx'
        
        logger.info(f"=== PIPELINE COMPLETE: {output_filename} ===")
        logger.info(f"Summary: {mapping_result.validation_summary}")
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={output_filename}"}
        )
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF to Excel conversion failed: {str(e)}")


# -------------------- Run with Uvicorn --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
