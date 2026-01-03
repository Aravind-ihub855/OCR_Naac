"""
Document Reasoning Models - Layer 5
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List
from enum import Enum


class DocumentArchetype(Enum):
    """Financial document archetypes"""
    INCOME_EXPENDITURE = "income_expenditure"
    BALANCE_SHEET = "balance_sheet"
    FIXED_ASSETS = "fixed_assets"
    GENERAL_TABLE = "general_table"


ARCHETYPE_SCHEMAS = {
    DocumentArchetype.INCOME_EXPENDITURE: {
        "description": "Income and Expenditure Account",
        "columns": [
            {"name": "Expenditure", "type": "string"},
            {"name": "Expenditure Amount (Rs.)", "type": "currency"},
            {"name": "Income", "type": "string"},
            {"name": "Income Amount (Rs.)", "type": "currency"}
        ]
    },
    DocumentArchetype.BALANCE_SHEET: {
        "description": "Balance Sheet",
        "columns": [
            {"name": "Liabilities", "type": "string"},
            {"name": "Liabilities Amount (Rs.)", "type": "currency"},
            {"name": "Assets", "type": "string"},
            {"name": "Assets Amount (Rs.)", "type": "currency"}
        ]
    },
    DocumentArchetype.FIXED_ASSETS: {
        "description": "Fixed Assets Schedule",
        "columns": [
            {"name": "Sl. No.", "type": "number"},
            {"name": "Description of Assets", "type": "string"},
            {"name": "WDV Opening", "type": "currency"},
            {"name": "Additions", "type": "currency"},
            {"name": "Deletions", "type": "currency"},
            {"name": "Total", "type": "currency"},
            {"name": "Rate %", "type": "number"},
            {"name": "Depreciation", "type": "currency"},
            {"name": "WDV Closing", "type": "currency"}
        ]
    }
}


@dataclass
class ReasonedTable:
    """A table reconstructed by the reasoning layer"""
    table_name: str
    archetype: str
    columns: List[Dict[str, Any]]
    rows: List[Dict[str, Any]]
    constraints_validated: Dict[str, Any]
    confidence: float
    reasoning_notes: List[str]
    page_number: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentReasoning:
    """Complete document reasoning output"""
    document_type: str
    archetype: str
    organization: str
    period: str
    tables: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    reasoning_chain: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
