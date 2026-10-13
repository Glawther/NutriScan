from typing import List
from fastapi import APIRouter, HTTPException, Query

from app.config import APP_NAME, APP_VERSION
from app.database import get_cached_product, get_metrics, list_history, save_product
from app.engine.analyzer import compare_products
from app.models.schemas import ComparisonResponse, ProductAnalysis
from app.services.openfoodfacts import fetch_product_by_barcode, search_openfoodfacts

router = APIRouter(prefix="/api/v1", tags=["nutriscan"])


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "regulations": ["ANVISA RDC 429/2020", "IN 75/2020", "NOVA USP", "Nutri-Score"],
    }


@router.get("/metrics")
async def metrics_endpoint():
    return get_metrics()


@router.get("/history", response_model=List[ProductAnalysis])
async def history_endpoint(limit: int = Query(50, ge=1, le=200)):
    return list_history(limit=limit)


@router.get("/search", response_model=List[ProductAnalysis])
async def search_endpoint(q: str = Query("", description="Nome, marca ou código EAN-13 do alimento")):
    query_clean = q.strip()
    if query_clean.isdigit() and len(query_clean) >= 8:
        product = await fetch_product_by_barcode(query_clean)
        if product:
            save_product(product)
            return [product]
    results = await search_openfoodfacts(query_clean, limit=10)
    for item in results:
        save_product(item)
    return results


@router.get("/product/{barcode}", response_model=ProductAnalysis)
async def get_product_endpoint(barcode: str, refresh: bool = Query(False)):
    clean_code = barcode.strip()
    if not refresh:
        cached = get_cached_product(clean_code)
        if cached:
            return cached

    product = await fetch_product_by_barcode(clean_code)
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Produto com código EAN '{clean_code}' não encontrado na base Open Food Facts.",
        )
    save_product(product)
    return product


@router.get("/compare", response_model=ComparisonResponse)
async def compare_endpoint(
    barcode_a: str = Query(..., description="Código de barras do primeiro produto"),
    barcode_b: str = Query(..., description="Código de barras do segundo produto"),
):
    prod_a = get_cached_product(barcode_a) or await fetch_product_by_barcode(barcode_a)
    if not prod_a:
        raise HTTPException(status_code=404, detail=f"Produto A ({barcode_a}) não encontrado.")

    prod_b = get_cached_product(barcode_b) or await fetch_product_by_barcode(barcode_b)
    if not prod_b:
        raise HTTPException(status_code=404, detail=f"Produto B ({barcode_b}) não encontrado.")

    save_product(prod_a)
    save_product(prod_b)
    return compare_products(prod_a, prod_b)
