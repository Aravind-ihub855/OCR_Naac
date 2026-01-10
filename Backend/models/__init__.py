from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

@dataclass
class ExcelColumn:
    """A validated Excel column"""
    name: str
    data_type: str  # "string", "number", "currency"
    width: int = 15

@dataclass
class ExcelRow:
    """A validated Excel row"""
    data: Dict[str, Any]
    is_total: bool = False
    is_header: bool = False

@dataclass
class ExcelTable:
    """Excel-ready table structure"""
    table_name: str
    sheet_name: str
    columns: List[ExcelColumn]
    rows: List[ExcelRow]
    validation: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "sheet_name": self.sheet_name,
            "columns": [asdict(c) for c in self.columns],
            "rows": [asdict(r) for r in self.rows],
            "validation": self.validation
        }

@dataclass
class MappingOutput:
    """Complete output of Data Mapper"""
    tables: List[Dict[str, Any]]
    metadata_sheet: Dict[str, Any]
    validation_summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
