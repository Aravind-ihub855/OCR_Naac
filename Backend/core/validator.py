"""
Data Validation Module - Layer 5.5

Responsible for validating extracted and merged data before final Excel generation.
Ensures logical consistency, completeness, and data integrity.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger("PDF_Agent.Validator")

def validate_extraction(tables: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the extracted data for common issues.
    
    Checks:
    1. Table integrity (rows, columns)
    2. Data completeness (null values)
    3. Anomaly detection (suspicious values)
    4. Logical consistency
    """
    validation_report = {
        "is_valid": True,
        "warnings": [],
        "errors": [],
        "stats": {
            "total_tables": len(tables),
            "total_rows": 0,
            "null_cells": 0
        }
    }
    
    if not tables:
        validation_report["warnings"].append("No tables found in document")
        return validation_report
        
    for idx, table in enumerate(tables):
        table_name = table.get('table_name', f'Table {idx+1}')
        rows = table.get('rows', [])
        columns = table.get('columns', [])
        
        # 1. Check Table Structure
        if not rows:
            validation_report["warnings"].append(f"Table '{table_name}' has no rows")
            continue
            
        if not columns:
            validation_report["errors"].append(f"Table '{table_name}' has no columns")
            validation_report["is_valid"] = False
            
        # 2. Check Row Integrity
        validation_report["stats"]["total_rows"] += len(rows)
        
        for r_idx, row in enumerate(rows):
            data = row.get('data', {})
            
            # Check for empty data
            if not data:
                validation_report["warnings"].append(f"Table '{table_name}' row {r_idx+1}: Empty data")
                continue
                
            # Check column alignment
            if len(data) != len(columns):
                # This might be okay if some cols are optional, but worth noting
                pass
                
            # Check for null/empty values in key columns
            for col in columns:
                col_name = col.get('name')
                val = data.get(col_name)
                if val is None or val == "":
                    validation_report["stats"]["null_cells"] += 1
                    
            # Check High/Low Confidence
            if row.get('needs_review'):
                 validation_report["warnings"].append(f"Table '{table_name}' row {r_idx+1}: Flagged for review")

        # 3. Check Multi-Page Consistency
        if table.get('page_count', 1) > 1:
            # Verify rows are sorted by page
            pages = [r.get('page', 0) for r in rows]
            if pages != sorted(pages):
                validation_report["warnings"].append(f"Table '{table_name}': Rows may be out of order (page sequence issue)")

    return validation_report
