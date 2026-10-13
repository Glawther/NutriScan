"""
TACO (Tabela Brasileira de Composição de Alimentos - UNICAMP / TBCA) Foods Module.
Provides structured data, helper lookup, and fallback dataset for Brazilian dietary staples.
"""
from pathlib import Path
import json
from typing import List, Dict, Any, Optional

CATALOG_PATH = Path(__file__).parent / "taco_catalog.json"

_cached_catalog: Optional[List[Dict[str, Any]]] = None


def get_taco_catalog() -> List[Dict[str, Any]]:
    """Loads and caches the compiled TACO food catalog."""
    global _cached_catalog
    if _cached_catalog is None:
        if CATALOG_PATH.exists():
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                _cached_catalog = json.load(f)
        else:
            _cached_catalog = []
    return _cached_catalog


# Expose raw list for direct imports if required
TACO_FOODS: List[Dict[str, Any]] = get_taco_catalog()
