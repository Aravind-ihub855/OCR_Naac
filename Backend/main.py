from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse

import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import pdfplumber
import pandas as pd
import io
import json
import os
from dotenv import load_dotenv
import logging

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("Naac_OCR")

load_dotenv()

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq


# -------------------- FastAPI --------------------
app = FastAPI(title="PDF → Excel Foundational Agent")

# -------------------- LLM --------------------
def get_groq_llm():
    from langchain_groq import ChatGroq

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        logger.error("GROQ_API_KEY environment variable is not set")
        raise ValueError("GROQ_API_KEY not set")

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    logger.info(f"Using Groq model: {model}")

    return ChatGroq(
        groq_api_key=groq_api_key,  
        model=model,
        temperature=0.2,
    )

POPPLER_PATH = r"C:\poppler-25.12.0\Library\bin"


# -------------------- Table Structure Pre-Parsing --------------------
def extract_table_structure(pdf_bytes: bytes):
    """
    Use pdfplumber to detect table structures and layout information.
    Returns structured data about detected tables.
    """
    logger.info("Starting table structure detection with pdfplumber...")
    tables_info = []
    
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_tables = page.extract_tables()
                
                if page_tables:
                    logger.info(f"Page {page_num}: Detected {len(page_tables)} table(s)")
                    
                    for table_idx, table in enumerate(page_tables):
                        if table and len(table) > 0:
                            # Extract headers (first row)
                            headers = [cell if cell else "" for cell in table[0]]
                            
                            tables_info.append({
                                "page": page_num,
                                "table_index": table_idx,
                                "num_columns": len(headers),
                                "num_rows": len(table),
                                "headers": headers,
                                "sample_rows": table[1:3] if len(table) > 1 else []  # First 2 data rows as samples
                            })
                else:
                    logger.info(f"Page {page_num}: No tables detected")
        
        logger.info(f"Total tables detected across document: {len(tables_info)}")
        return tables_info
    
    except Exception as e:
        logger.warning(f"pdfplumber table detection failed: {str(e)}. Falling back to pure OCR.")
        return []


# -------------------- OCR --------------------
def extract_text_pagewise(pdf_bytes: bytes):
    logger.info(f"Extracting text from {len(pdf_bytes)} bytes of PDF")
    try:
        pages = convert_from_bytes(
            pdf_bytes,
            dpi=300,
            poppler_path=POPPLER_PATH
        )
        logger.info(f"Converted PDF to {len(pages)} images")
    except Exception as e:
        logger.error(f"Failed to convert PDF to images: {str(e)}")
        raise

    extracted = []

    for i, page in enumerate(pages, start=1):
        logger.info(f"Ocr-ing page {i}...")
        text = pytesseract.image_to_string(page, lang="eng")
        extracted.append({
            "page": i,
            "raw_text": text.strip()
        })

    logger.info("OCR extraction complete")
    return extracted

# -------------------- LLM Semantic Mapping --------------------
def llm_convert_to_table(page_text_entry, table_structure_hints):
    """
    LLM converts a SINGLE page of raw extracted text into structured tables + metadata.
    Uses pre-parsed table structure hints to preserve original table format.
    """
    logger.info(f"Starting LLM semantic mapping for Page {page_text_entry['page']}...")
    llm = get_groq_llm()

    # Format table structure hints for the LLM
    hints_text = ""
    if table_structure_hints:
        page_hints = [h for h in table_structure_hints if h['page'] == page_text_entry['page']]
        if page_hints:
            hints_text = "\n\n### DETECTED TABLE STRUCTURES (Use these as hints):\n"
            for hint in page_hints:
                hints_text += f"\n- Table {hint['table_index'] + 1}: {hint['num_columns']} columns, {hint['num_rows']} rows"
                hints_text += f"\n  Headers: {hint['headers']}"
                if hint['sample_rows']:
                    hints_text += f"\n  Sample rows: {hint['sample_rows'][:1]}"

    prompt = ChatPromptTemplate.from_messages([
        ("system",
        """
You are the "PDF → Excel Intelligent Data Mapping Foundational Agent".

Your mission: Extract ALL information from OCR-extracted text and preserve ORIGINAL TABLE STRUCTURES EXACTLY.

### INSTRUCTIONS:

1. **METADATA EXTRACTION**: Extract document metadata separately:
   - Document Title (e.g., "Income and Expenditure Account", "Balance Sheet")
   - Institution Name and Address
   - Period/Date Range (e.g., "For the year ended 31.03.2021")
   - Auditor Information
   - Place and Date of Report
   - Signatures and Designations

2. **TABLE EXTRACTION - CRITICAL RULES**:
   
   **IMPORTANT**: Many financial documents have tables with SIDE-BY-SIDE column groups.
   
   Example: "Income and Expenditure Account" typically has structure:
   | Expenditure | Amount (Rs.) | Income | Amount (Rs.) |
   
   - **DO NOT SPLIT** side-by-side columns into separate tables
   - **PRESERVE** the exact row-column alignment from the PDF
   - If a row has data in columns 1-2 and columns 3-4, include ALL 4 values in that row
   - Use empty strings "" for missing cells
   
   For each table:
   - Identify the FULL column set (e.g., ["Expenditure", "Amount (Rs.)", "Income", "Amount (Rs.)"])
   - Extract ALL rows with all column values
   - Maintain original column structure (do NOT force into generic schema)
   - If a table name is clear (e.g., "Income and Expenditure Account"), use it

3. **ZERO DATA LOSS**: 
   - Include every line of text
   - Do not skip footers, notes, or signatures
   - If data doesn't fit a table, put it in metadata

### OUTPUT FORMAT:

Return STRICT JSON:
{{
  "metadata": {{
    "document_title": "Main document title or type",
    "institution_name": "...",
    "address": "...",
    "period": "...",
    "auditor": "...",
    "place": "...",
    "date": "...",
    "notes": ["..."],
    "signatures": ["..."]
  }},
  "tables": [
    {{
      "table_name": "Income and Expenditure Account",
      "columns": ["Expenditure", "Amount (Rs.)", "Income", "Amount (Rs.)"],
      "rows": [
        ["Salary", "18,18,25,263", "Fees Receipts", "20,20,50,837"],
        ["Provident Fund", "51,45,523", "Other Fee Receipts", "3,57,44,893"],
        ["ESI", "8,38,877", "", ""],
        ...
      ]
    }}
  ]
}}

### CRITICAL RULES:
- Output ONLY the JSON block, nothing else
- PRESERVE original column names and structure
- DO NOT split side-by-side columns into separate tables
- Ensure each row has the SAME number of values as columns (use "" for empty cells)
- Do NOT summarize, rewrite, or omit data
- Map EVERY line from the OCR text
"""
        ),
        ("human", """OCR TEXT - PAGE {page_num}:
{text}
{hints}

Extract all data following the JSON format specified.""")
    ])

    formatted_prompt = prompt.format_messages(
        page_num=page_text_entry['page'],
        text=page_text_entry['raw_text'],
        hints=hints_text
    )
    
    logger.info(f"Invoking LLM for page {page_text_entry['page']}...")
    response = llm.invoke(formatted_prompt)
    
    content = response.content.strip()
    
    # Clean markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        page_data = json.loads(content)
        
        # Log what was extracted
        num_tables = len(page_data.get('tables', []))
        total_rows = sum(len(t.get('rows', [])) for t in page_data.get('tables', []))
        logger.info(f"Page {page_text_entry['page']}: Extracted {num_tables} table(s), {total_rows} total rows")
        
        return page_data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response for Page {page_text_entry['page']}. Content snippet: {content[:300]}")
        # Return empty structure to avoid crashing
        return {"metadata": {}, "tables": []}

# -------------------- Excel Generator --------------------
def json_to_excel(aggregated_data):
    """
    Generate multi-sheet Excel from aggregated data.
    - One "Metadata" sheet with document information
    - One sheet per table (named after the table)
    """
    logger.info("Creating multi-sheet Excel workbook...")
    
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Metadata
        metadata = aggregated_data.get("metadata", {})
        if metadata:
            metadata_rows = []
            for key, value in metadata.items():
                if isinstance(value, list):
                    value = "; ".join(str(v) for v in value if v)
                metadata_rows.append([key.replace("_", " ").title(), value])
            
            df_metadata = pd.DataFrame(metadata_rows, columns=["Field", "Value"])
            df_metadata.to_excel(writer, sheet_name="Metadata", index=False)
            logger.info("Created 'Metadata' sheet")
        
        # Sheets 2+: One per table
        tables = aggregated_data.get("tables", [])
        for idx, table in enumerate(tables):
            table_name = table.get("table_name", f"Table_{idx + 1}")
            # Clean sheet name (Excel limits: 31 chars, no special chars)
            sheet_name = table_name[:31].replace("/", "-").replace("\\", "-").replace(":", "-")
            
            columns = table.get("columns", [])
            rows = table.get("rows", [])
            
            if columns and rows:
                # Validate that all rows have the same number of values as columns
                validated_rows = []
                for row in rows:
                    if len(row) == len(columns):
                        validated_rows.append(row)
                    elif len(row) < len(columns):
                        # Pad with empty strings
                        padded_row = row + [""] * (len(columns) - len(row))
                        validated_rows.append(padded_row)
                        logger.warning(f"Row in '{table_name}' had {len(row)} values, expected {len(columns)}. Padded with empty strings.")
                    else:
                        # Truncate excess values
                        truncated_row = row[:len(columns)]
                        validated_rows.append(truncated_row)
                        logger.warning(f"Row in '{table_name}' had {len(row)} values, expected {len(columns)}. Truncated excess values.")
                
                df_table = pd.DataFrame(validated_rows, columns=columns)
                df_table.to_excel(writer, sheet_name=sheet_name, index=False)
                logger.info(f"Created '{sheet_name}' sheet with {len(validated_rows)} rows")
    
    output.seek(0)
    logger.info("Excel workbook creation complete")
    return output

# -------------------- API --------------------
@app.post("/extract")
async def extract_pdf(file: UploadFile = File(...)):
    logger.info(f"Received extraction request for file: {file.filename}")
    try:
        pdf_bytes = await file.read()

        # 0️⃣ Table Structure Pre-Parsing
        table_structure_hints = extract_table_structure(pdf_bytes)

        # 1️⃣ OCR (no data loss)
        page_texts = extract_text_pagewise(pdf_bytes)

        # 2️⃣ LLM semantic structuring (Process Page-by-Page with structure hints)
        aggregated_metadata = {}
        aggregated_tables = {}  # Key: table_name, Value: {"columns": [...], "rows": [...]}

        for page_entry in page_texts:
            page_data = llm_convert_to_table(page_entry, table_structure_hints)
            
            # Aggregate metadata (first occurrence wins)
            if not aggregated_metadata and page_data.get("metadata"):
                aggregated_metadata = page_data["metadata"]
            
            # Aggregate tables
            for table in page_data.get("tables", []):
                table_name = table.get("table_name", "Unnamed Table")
                columns = table.get("columns", [])
                rows = table.get("rows", [])
                
                if table_name in aggregated_tables:
                    # Table already exists, append rows if columns match
                    if aggregated_tables[table_name]["columns"] == columns:
                        aggregated_tables[table_name]["rows"].extend(rows)
                    else:
                        # Column mismatch, create a new variant
                        variant_name = f"{table_name} (Page {page_entry['page']})"
                        aggregated_tables[variant_name] = {
                            "table_name": variant_name,
                            "columns": columns,
                            "rows": rows
                        }
                else:
                    # New table
                    aggregated_tables[table_name] = {
                        "table_name": table_name,
                        "columns": columns,
                        "rows": rows
                    }
        
        # Format aggregated data
        final_data = {
            "metadata": aggregated_metadata,
            "tables": list(aggregated_tables.values())
        }
        
        logger.info(f"Aggregation complete: {len(aggregated_tables)} table(s), total rows: {sum(len(t['rows']) for t in aggregated_tables.values())}")

        # 3️⃣ Excel creation
        logger.info("Creating Excel file...")
        excel_file = json_to_excel(final_data)

        logger.info("Request processed successfully, streaming response")
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=extracted_{file.filename}.xlsx"}
        )
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        return {"error": str(e)}
