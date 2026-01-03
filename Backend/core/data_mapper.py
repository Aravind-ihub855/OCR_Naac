"""
Data Mapping Module - Layer 6

The "Truth Engine" - converts semantic interpretation to Excel-ready structure.

This layer is primarily ALGORITHMIC, not LLM-heavy.

Responsibilities:
1. Column hypothesis generation (x-position clustering)
2. Numeric-to-description binding
3. Row explosion for compound rows
4. Header anchoring & propagation
5. Cross-page table continuation
6. Totals & consistency validation
7. Noise finalization
8. Excel generation
"""

import io
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows

logger = logging.getLogger("PDF_Agent.DataMapper")


# -------------------- Main Entry Point --------------------

def map_to_excel(semantic_result: Dict[str, Any]) -> Tuple[MappingOutput, io.BytesIO]:
    """
    Main entry point for Layer 5.
    
    Takes Layer 4 semantic output and produces:
    1. Excel-ready structured data
    2. Actual Excel file as BytesIO
    """
    logger.info("Starting data mapping (Layer 5)")
    
    tables = semantic_result.get('tables', [])
    metadata = semantic_result.get('metadata', {})
    
    if not tables:
        logger.warning("No tables to map")
        empty_output = MappingOutput(
            tables=[],
            metadata_sheet=metadata,
            validation_summary={"total_tables": 0, "all_valid": True}
        )
        excel_file = _generate_excel([], metadata)
        return empty_output, excel_file
    
    # Process each table
    excel_tables = []
    validation_results = []
    
    for idx, table in enumerate(tables):
        logger.info(f"Processing table {idx + 1}/{len(tables)}: {table.get('table_name', 'Unknown')}")
        
        # Step 1: Resolve columns
        resolved_columns = _resolve_columns(table)
        
        # Step 2: Resolve rows (bind numerics, explode compound rows)
        resolved_rows = _resolve_rows(table, resolved_columns)
        
        # Step 3: Finalize noise (remove or move to footnotes)
        clean_rows = _finalize_noise(resolved_rows)
        
        # Step 4: Validate totals
        validation = _validate_totals(clean_rows, resolved_columns)
        validation_results.append(validation)
        
        # Step 5: Create Excel table
        sheet_name = _sanitize_sheet_name(table.get('table_name', f'Table_{idx + 1}'))
        
        excel_table = ExcelTable(
            table_name=table.get('table_name', f'Table {idx + 1}'),
            sheet_name=sheet_name,
            columns=[ExcelColumn(name=c['name'], data_type=c.get('data_type', 'string')) 
                     for c in resolved_columns],
            rows=clean_rows,
            validation=validation
        )
        excel_tables.append(excel_table)
    
    # Generate Excel file
    logger.info("Generating Excel file...")
    excel_file = _generate_excel(excel_tables, metadata)
    
    # Build output
    output = MappingOutput(
        tables=[t.to_dict() for t in excel_tables],
        metadata_sheet=metadata,
        validation_summary={
            "total_tables": len(excel_tables),
            "tables_with_valid_totals": sum(1 for v in validation_results if v.get('totals_match', False)),
            "all_valid": all(v.get('totals_match', True) for v in validation_results),
            "total_rows": sum(len(t.rows) for t in excel_tables)
        }
    )
    
    logger.info(f"Data mapping complete: {len(excel_tables)} tables, {output.validation_summary['total_rows']} rows")
    return output, excel_file


# -------------------- Column Resolution --------------------

def _resolve_columns(table: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Resolve column structure from semantic table.
    
    Uses semantic columns if available, otherwise generates from data.
    """
    semantic_columns = table.get('columns', [])
    
    if semantic_columns:
        # Use semantic columns, ensure proper structure
        resolved = []
        for col in semantic_columns:
            resolved.append({
                'name': col.get('name', 'Column'),
                'data_type': _normalize_data_type(col.get('data_type', 'string')),
                'confidence': col.get('confidence', 0.5)
            })
        return resolved
    
    # Fallback: Generate columns from first row
    rows = table.get('rows', [])
    if rows and rows[0].get('data'):
        first_row = rows[0]['data']
        return [
            {'name': key, 'data_type': 'string', 'confidence': 0.3}
            for key in first_row.keys()
        ]
    
    return [{'name': 'Column_1', 'data_type': 'string', 'confidence': 0.1}]


def _normalize_data_type(dtype: str) -> str:
    """Normalize data type to Excel-compatible types"""
    dtype = dtype.lower()
    if dtype in ['number', 'numeric', 'int', 'float', 'currency', 'amount']:
        return 'number'
    if dtype in ['date', 'datetime', 'time']:
        return 'date'
    return 'string'


# -------------------- Row Resolution --------------------

def _resolve_rows(table: Dict[str, Any], columns: List[Dict[str, Any]]) -> List[ExcelRow]:
    """
    Resolve rows: bind numerics to descriptions, explode compound rows.
    """
    semantic_rows = table.get('rows', [])
    column_names = [c['name'] for c in columns]
    
    resolved_rows = []
    
    for row in semantic_rows:
        # Skip noise rows
        if row.get('is_noise', False):
            continue
        
        data = row.get('data', {})
        
        if not data:
            continue
        
        # Check if this is a compound row that needs explosion
        exploded = _try_explode_row(data, columns)
        
        if exploded:
            for exp_row in exploded:
                resolved_rows.append(ExcelRow(
                    data=exp_row,
                    is_total=_is_total_row(exp_row),
                    is_header=False
                ))
        else:
            # Clean and validate data
            cleaned_data = _clean_row_data(data, columns)
            resolved_rows.append(ExcelRow(
                data=cleaned_data,
                is_total=_is_total_row(cleaned_data),
                is_header=False
            ))
    
    return resolved_rows


def _try_explode_row(data: Dict[str, Any], columns: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """
    Try to explode a compound row into multiple logical rows.
    
    Example: "Salary Provident Fund 8,18,25,263 51,45,525"
    → [{"Description": "Salary", "Amount": 81825263}, 
       {"Description": "Provident Fund", "Amount": 5145525}]
    """
    # Find description and numeric columns
    desc_col = None
    num_cols = []
    
    for col in columns:
        if col['data_type'] == 'string':
            desc_col = col['name']
        elif col['data_type'] == 'number':
            num_cols.append(col['name'])
    
    if not desc_col or not num_cols:
        return None
    
    desc_value = str(data.get(desc_col, ''))
    
    # Check if description contains multiple items and numbers
    # Pattern: multiple words followed by multiple numbers
    words = re.split(r'\s+', desc_value)
    
    # Extract all numbers from description
    numbers_in_desc = re.findall(r'[\d,]+(?:\.\d+)?', desc_value)
    
    if len(numbers_in_desc) > 1:
        # This might be a compound row
        # Extract text parts (non-numeric)
        text_parts = re.split(r'[\d,]+(?:\.\d+)?', desc_value)
        text_parts = [t.strip() for t in text_parts if t.strip()]
        
        # If we have matching text and numbers, explode
        if len(text_parts) >= len(numbers_in_desc):
            exploded = []
            for i, num in enumerate(numbers_in_desc):
                row_data = {}
                if i < len(text_parts):
                    row_data[desc_col] = text_parts[i]
                else:
                    row_data[desc_col] = ""
                
                # Parse number
                parsed_num = _parse_number(num)
                if num_cols:
                    row_data[num_cols[0]] = parsed_num
                
                exploded.append(row_data)
            
            if len(exploded) > 1:
                return exploded
    
    return None


def _clean_row_data(data: Dict[str, Any], columns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Clean and validate row data according to column types.
    For financial tables, preserve string values that look like numbers
    but keep them readable."""
    cleaned = {}
    
    for col in columns:
        name = col['name']
        dtype = col['data_type']
        value = data.get(name, '')
        
        if value is None:
            cleaned[name] = '' if dtype == 'string' else None
        elif dtype == 'number' or dtype == 'currency':
            # Try to parse as number, but keep string if it fails
            parsed = _parse_indian_number(value)
            cleaned[name] = parsed if parsed is not None else str(value).strip()
        else:
            cleaned[name] = str(value).strip() if value else ''
    
    return cleaned


def _parse_indian_number(value: Any) -> Optional[float]:
    """
    Parse a number from Indian format (e.g., 18,18,25,263).
    Returns float for valid numbers, None for invalid.
    """
    if value is None or value == '':
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    value = str(value).strip()
    
    # Skip if clearly not a number
    if not value or value in ['-', 'nil', 'Nil', 'NIL']:
        return None
    
    # Remove currency symbols, spaces, and common prefixes
    value = re.sub(r'[₹$€£¥\s]', '', value)
    value = value.replace('Rs.', '').replace('RS.', '').replace('rs.', '')
    
    # Handle parentheses for negative numbers
    is_negative = value.startswith('(') and value.endswith(')')
    if is_negative:
        value = value[1:-1]
    
    # Handle Indian number format (e.g., 18,18,25,263)
    # Remove all commas
    value = value.replace(',', '')
    
    # Handle trailing .00 or .P (paisa)
    value = re.sub(r'\.P$', '', value, flags=re.IGNORECASE)
    
    try:
        result = float(value)
        return -result if is_negative else result
    except ValueError:
        return None


def _is_total_row(data: Dict[str, Any]) -> bool:
    """Check if a row is a total/summary row"""
    for key, value in data.items():
        if isinstance(value, str):
            value_lower = value.lower()
            if any(word in value_lower for word in ['total', 'grand total', 'sum', 'subtotal']):
                return True
    return False


# -------------------- Noise Finalization --------------------

def _finalize_noise(rows: List[ExcelRow]) -> List[ExcelRow]:
    """
    Finalize noise decisions - remove empty rows and clean up.
    """
    clean_rows = []
    
    for row in rows:
        # Skip completely empty rows
        if all(v in [None, '', 0, 0.0] for v in row.data.values()):
            continue
        
        # Skip rows that are just noise text
        text_values = [str(v) for v in row.data.values() if isinstance(v, str)]
        if text_values:
            combined = ' '.join(text_values).lower()
            noise_patterns = [
                'principal', 'correspondent', 'signature', 
                'auditor', 'place:', 'date:', 'page'
            ]
            if any(pattern in combined for pattern in noise_patterns):
                # Check if it's purely noise (no numbers)
                has_numbers = any(
                    isinstance(v, (int, float)) and v is not None and v != 0 
                    for v in row.data.values()
                )
                if not has_numbers:
                    continue
        
        clean_rows.append(row)
    
    return clean_rows


# -------------------- Validation --------------------

def _safe_numeric(value: Any) -> float:
    """Safely extract numeric value, returning 0 for non-numeric types"""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Try to parse string as number
        try:
            cleaned = value.replace(',', '').replace('₹', '').strip()
            return float(cleaned) if cleaned else 0.0
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def _validate_totals(rows: List[ExcelRow], columns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate that totals match sum of rows.
    """
    validation = {
        'totals_match': True,
        'total_rows_found': 0,
        'data_rows': len([r for r in rows if not r.is_total]),
        'discrepancies': [],
        'confidence': 0.9
    }
    
    # Find numeric columns
    num_columns = [c['name'] for c in columns if c['data_type'] in ('number', 'currency')]
    
    if not num_columns:
        validation['confidence'] = 0.5
        return validation
    
    # Calculate sums for each numeric column
    for col_name in num_columns:
        data_rows = [r for r in rows if not r.is_total]
        total_rows = [r for r in rows if r.is_total]
        
        # Sum data rows (safely handle mixed types)
        calculated_sum = sum(
            _safe_numeric(r.data.get(col_name, 0))
            for r in data_rows
        )
        
        # Check against total rows
        for total_row in total_rows:
            declared_total = _safe_numeric(total_row.data.get(col_name, 0))
            
            if declared_total > 0:
                validation['total_rows_found'] += 1
                
                # Allow 1% tolerance for rounding
                tolerance = declared_total * 0.01
                if abs(calculated_sum - declared_total) > tolerance:
                    validation['totals_match'] = False
                    validation['discrepancies'].append({
                        'column': col_name,
                        'calculated': calculated_sum,
                        'declared': declared_total,
                        'difference': calculated_sum - declared_total
                    })
    
    return validation


# -------------------- Excel Generation --------------------

def _generate_excel(tables: List[ExcelTable], metadata: Dict[str, Any]) -> io.BytesIO:
    """Generate Excel file with proper formatting"""
    wb = Workbook()
    
    # Remove default sheet
    if 'Sheet' in wb.sheetnames:
        del wb['Sheet']
    
    # Create metadata sheet first
    _create_metadata_sheet(wb, metadata)
    
    # Create table sheets
    for table in tables:
        _create_table_sheet(wb, table)
    
    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return output


def _create_metadata_sheet(wb: Workbook, metadata: Dict[str, Any]):
    """Create metadata sheet"""
    ws = wb.create_sheet("Metadata")
    
    # Styles
    header_font = Font(bold=True, size=12)
    header_fill = PatternFill(start_color="CCE5FF", end_color="CCE5FF", fill_type="solid")
    
    # Add title
    ws['A1'] = "Document Metadata"
    ws['A1'].font = Font(bold=True, size=14)
    
    row = 3
    for key, value in metadata.items():
        if value and key != 'confidence':
            # Format key
            formatted_key = key.replace('_', ' ').title()
            ws.cell(row=row, column=1, value=formatted_key)
            ws.cell(row=row, column=1).font = header_font
            
            # Format value
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            ws.cell(row=row, column=2, value=str(value))
            
            row += 1
    
    # Adjust column widths
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 50


def _create_table_sheet(wb: Workbook, table: ExcelTable):
    """Create a sheet for a single table"""
    ws = wb.create_sheet(table.sheet_name)
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    total_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    total_font = Font(bold=True)
    
    # Write headers
    for col_idx, column in enumerate(table.columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=column.name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # Write data rows
    for row_idx, row in enumerate(table.rows, start=2):
        for col_idx, column in enumerate(table.columns, start=1):
            value = row.data.get(column.name, '')
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            
            # Apply number formatting (Indian format: ##,##,##0.00)
            if column.data_type in ('number', 'currency') and isinstance(value, (int, float)):
                # Use Indian number format for large numbers
                cell.number_format = '[>=10000000]##\,##\,##\,##0;[>=100000]##\,##\,##0;#,##0'
            
            # Highlight total rows
            if row.is_total:
                cell.fill = total_fill
                cell.font = total_font
    
    # Adjust column widths
    for col_idx, column in enumerate(table.columns, start=1):
        # Calculate width based on header and data
        max_length = len(column.name)
        for row in table.rows:
            value = row.data.get(column.name, '')
            if value:
                max_length = max(max_length, len(str(value)))
        
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = min(max_length + 2, 50)
    
    # Freeze header row
    ws.freeze_panes = 'A2'


def _sanitize_sheet_name(name: str) -> str:
    """Sanitize name for Excel sheet (max 31 chars, no special chars)"""
    # Remove invalid characters
    invalid_chars = ['/', '\\', '?', '*', '[', ']', ':']
    for char in invalid_chars:
        name = name.replace(char, '-')
    
    # Truncate to 31 characters
    if len(name) > 31:
        name = name[:28] + '...'
    
    return name or "Sheet"
