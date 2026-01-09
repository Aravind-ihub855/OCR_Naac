
import os
import sys
import asyncio
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.universal_extractor import extract_robust

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyRobust")

async def main():
    pdf_path = "sample_naac.pdf"
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        return

    logger.info(f"Extracting structure from {pdf_path} (NON-AI)...")
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
        result = extract_robust(pdf_bytes)
        
        print("\n=== EXTRACTION RESULT (pages: {}) ===".format(len(result['pages'])))
        for page in result['pages']:
            print(f"\n--- Page {page['page_num']} ---")
            print(f"Is Scanned: {page['is_scanned']}")
            print(f"Tables Found: {len(page['tables'])}")
            if page['tables']:
                print("First Table Snippet:")
                for row in page['tables'][0][:3]:  # Print first 3 rows
                    print(row)
            print("-" * 20)
            
    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
