
import os
import sys
import asyncio
import logging
from fastapi.responses import StreamingResponse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.signal_preservor import preserve_signals
from core.geometric_reconstructor import reconstruct_geometric
from core.simple_excel import generate_excel_geometric

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyExcel")

async def main():
    pdf_path = "sample_naac.pdf"
    if not os.path.exists(pdf_path):
        return

    logger.info("Verifying Geometric Excel Generation...")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # 1. Signals
    signals = preserve_signals(pdf_bytes, dpi=200)
    
    # 2. Geometric
    result = reconstruct_geometric(signals.to_dict())
    
    # 3. Excel
    excel_io = generate_excel_geometric(result)
    
    output_path = "output_geometric.xlsx"
    with open(output_path, "wb") as f:
        f.write(excel_io.read())
        
    logger.info(f"Excel saved to {output_path}. Size: {os.path.getsize(output_path)} bytes")

if __name__ == "__main__":
    asyncio.run(main())
