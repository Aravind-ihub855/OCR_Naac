
import os
import sys
import asyncio
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.signal_preservor import preserve_signals
from core.geometric_reconstructor import reconstruct_geometric

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyGeometric")

async def main():
    pdf_path = "sample_naac.pdf"
    if not os.path.exists(pdf_path):
        return

    logger.info("Verifying Geometric Reconstruction...")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # 1. Signals
    signals = preserve_signals(pdf_bytes, dpi=200)
    
    # 2. Geometric
    result = reconstruct_geometric(signals.to_dict())
    
    print("\n=== GEOMETRIC RESULT ===")
    for page in result['pages']:
        print(f"\nPage {page['page_num']}")
        for tbl in page['tables']:
            print(f"Table Found: {tbl['n_cols']} columns")
            # print first 5 rows
            for row in tbl['rows'][:10]:
                print(row)
                
if __name__ == "__main__":
    asyncio.run(main())
