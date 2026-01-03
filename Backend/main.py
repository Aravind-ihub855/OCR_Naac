"""
PDF → Excel Intelligent Data Mapping (Foundational Agent)
Complete 7-Layer Architecture with Document Reasoning

Layer 0: FastAPI entry point
Layer 1: Document classification
Layer 2: Signal preservation (OCR)
Layer 3: Structural reconstruction (geometry)
Layer 4: Semantic interpretation (basic LLM)
Layer 5: Document Reasoning (NEW - archetype detection & understanding)
Layer 6: Data mapping & Excel generation
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from core.document_classifier import analyze_document
from core.signal_preservor import preserve_signals
from core.structural_reconstructor import reconstruct_structure
from core.document_reasoner import reason_document
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
    title="PDF → Excel Foundational Agent",
    description="Intelligent data mapping with Document Reasoning",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------- Layer 0: PDF Upload --------------------
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Layer 0: Accept PDF upload."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    pdf_bytes = await file.read()
    return {
        "status": "received",
        "filename": file.filename,
        "size_kb": round(len(pdf_bytes) / 1024, 2),
        "message": "Use /convert for intelligent PDF to Excel conversion"
    }


# -------------------- Layer 1: Document Analysis --------------------
@app.post("/analyze")
async def analyze_pdf(file: UploadFile = File(...)):
    """Layer 1: Analyze PDF structure."""
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
    """Layer 2: Extract OCR signals."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if dpi < 72 or dpi > 600:
        raise HTTPException(status_code=400, detail="DPI must be between 72 and 600")
    
    try:
        pdf_bytes = await file.read()
        signals = preserve_signals(pdf_bytes, dpi=dpi)
        return {"status": "extracted", "dpi": dpi, "signals": signals.to_dict()}
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Layer 3: Structural Reconstruction --------------------
@app.post("/reconstruct")
async def reconstruct_tables(file: UploadFile = File(...), dpi: int = 300):
    """Layer 3: Reconstruct table structures."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if dpi < 72 or dpi > 600:
        raise HTTPException(status_code=400, detail="DPI must be between 72 and 600")
    
    try:
        pdf_bytes = await file.read()
        signals = preserve_signals(pdf_bytes, dpi=dpi)
        structure = reconstruct_structure(signals.to_dict())
        return {"status": "reconstructed", "structure": structure.to_dict()}
    except Exception as e:
        logger.error(f"Reconstruction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Layer 5: Document Reasoning (NEW) --------------------
@app.post("/reason")
async def reason_about_document(file: UploadFile = File(...), dpi: int = 300):
    """
    Layer 5: Document Reasoning - The intelligence layer.
    
    This endpoint:
    1. Detects document archetype (Income & Expenditure, Balance Sheet, etc.)
    2. Applies archetype-specific schemas
    3. Understands dual-column layouts
    4. Returns semantically reasoned tables
    
    Requires GROQ_API_KEY.
    """
    logger.info(f"=== Document Reasoning: {file.filename} ===")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if dpi < 72 or dpi > 600:
        raise HTTPException(status_code=400, detail="DPI must be between 72 and 600")
    
    try:
        pdf_bytes = await file.read()
        
        # Layer 2: Signal preservation
        signals = preserve_signals(pdf_bytes, dpi=dpi)
        
        # Layer 3: Structural reconstruction
        structure = reconstruct_structure(signals.to_dict())
        
        # Layer 5: Document Reasoning
        reasoning = reason_document(signals.to_dict(), structure.to_dict())
        
        return {
            "status": "reasoned",
            "filename": file.filename,
            "archetype": reasoning.archetype,
            "document_type": reasoning.document_type,
            "reasoning": reasoning.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Reasoning failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Full Pipeline: Convert with Reasoning --------------------
@app.post("/convert")
async def convert_to_excel(file: UploadFile = File(...), dpi: int = 300):
    """
    FULL PIPELINE with Document Reasoning: PDF → Excel
    
    Pipeline:
    1. Layer 2: OCR with signal preservation
    2. Layer 3: Structural reconstruction
    3. Layer 5: Document Reasoning (archetype detection)
    4. Layer 6: Excel generation with proper formatting
    
    Returns Excel file with:
    - Metadata sheet
    - Properly formatted financial tables
    - Dual-column layouts preserved
    
    Requires GROQ_API_KEY.
    """
    logger.info(f"=== INTELLIGENT PIPELINE: {file.filename} ===")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if dpi < 72 or dpi > 600:
        raise HTTPException(status_code=400, detail="DPI must be between 72 and 600")
    
    try:
        pdf_bytes = await file.read()
        
        # Layer 2: Signal preservation
        logger.info("Layer 2: OCR Signal Preservation...")
        signals = preserve_signals(pdf_bytes, dpi=dpi)
        signals_dict = signals.to_dict()
        
        # Layer 3: Structural reconstruction
        logger.info("Layer 3: Structural Reconstruction...")
        structure = reconstruct_structure(signals_dict)
        structure_dict = structure.to_dict()
        
        # Layer 5: Document Reasoning (THE KEY LAYER)
        logger.info("Layer 5: Document Reasoning...")
        reasoning = reason_document(signals_dict, structure_dict)
        
        logger.info(f"  → Detected archetype: {reasoning.archetype}")
        logger.info(f"  → Document type: {reasoning.document_type}")
        logger.info(f"  → Tables found: {len(reasoning.tables)}")
        
        # Convert reasoning output to semantic format for data mapper
        semantic_output = {
            "tables": reasoning.tables,
            "metadata": reasoning.metadata,
            "processing_notes": reasoning.reasoning_chain
        }
        
        # Layer 6: Data mapping and Excel generation
        logger.info("Layer 6: Excel Generation...")
        mapping_result, excel_file = map_to_excel(semantic_output)
        
        output_filename = file.filename.replace('.pdf', '.xlsx').replace('.PDF', '.xlsx')
        if not output_filename.endswith('.xlsx'):
            output_filename += '.xlsx'
        
        logger.info(f"=== PIPELINE COMPLETE: {output_filename} ===")
        logger.info(f"  → Archetype: {reasoning.archetype}")
        logger.info(f"  → Tables: {len(reasoning.tables)}")
        logger.info(f"  → Rows: {mapping_result.validation_summary.get('total_rows', 0)}")
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={output_filename}"}
        )
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


