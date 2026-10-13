import base64
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request

from app.config import APP_NAME, APP_VERSION
from app.database import (
    add_diary_entry,
    delete_diary_entry,
    get_cached_product,
    get_diet_goals,
    get_diet_today_summary,
    get_metrics,
    list_history,
    save_product,
    update_diet_goals,
)
from app.engine.analyzer import compare_products
from app.engine.label_ocr import (
    SAMPLE_LABELS,
    extract_text_from_image_bytes,
    parse_nutrition_table_text,
)
from app.models.schemas import (
    ComparisonResponse,
    DietDiaryCreateRequest,
    DietDiaryEntry,
    DietGoals,
    DietGoalsUpdateRequest,
    DietTodaySummary,
    LabelParseResult,
    ProductAnalysis,
)
from app.services.openfoodfacts import fetch_product_by_barcode, search_openfoodfacts

router = APIRouter(prefix="/api/v1", tags=["nutriscan"])


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "regulations": ["ANVISA RDC 429/2020", "IN 75/2020", "NOVA USP", "Nutri-Score"],
        "features": ["diet_daily_limit", "label_photo_ocr", "barcode_scanner", "food_comparator"],
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


@router.get("/diet/today", response_model=DietTodaySummary)
async def get_diet_today_endpoint(date_str: Optional[str] = Query(None, description="Data YYYY-MM-DD")):
    return get_diet_today_summary(date_str=date_str)


@router.put("/diet/goals", response_model=DietGoals)
async def update_diet_goals_endpoint(payload: DietGoalsUpdateRequest):
    return update_diet_goals(payload)


@router.post("/diet/diary", response_model=DietDiaryEntry)
async def create_diet_diary_endpoint(payload: DietDiaryCreateRequest):
    return add_diary_entry(payload)


@router.delete("/diet/diary/{entry_id}")
async def delete_diet_diary_endpoint(entry_id: int):
    deleted = delete_diary_entry(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Registro {entry_id} não encontrado no diário.")
    return {"deleted": True, "id": entry_id}


@router.get("/label-samples")
async def list_label_samples_endpoint():
    items = []
    for key, spec in SAMPLE_LABELS.items():
        items.append(
            {
                "sample_id": key,
                "product_name": spec["product_name"],
                "brand": spec["brand"],
                "portion_label_g": spec["portion_label_g"],
                "portion_desc": spec["portion_desc"],
                "default_consumed_g": spec["default_consumed_g"],
                "image_url": f"/static/samples/{spec['filename']}",
                "raw_text": spec["raw_text"],
            }
        )
    return items


@router.post("/scan-label-photo", response_model=LabelParseResult)
async def scan_label_photo_endpoint(request: Request):
    content_type = request.headers.get("content-type", "").lower()
    raw_text: Optional[str] = None
    sample_id: Optional[str] = None
    product_name: Optional[str] = None
    portion_g: float = 100.0
    image_url: Optional[str] = None
    ocr_engine = "nutriscan_regex_br"

    if "application/json" in content_type:
        body = await request.json()
        raw_text = body.get("raw_text")
        sample_id = body.get("sample_id")
        product_name = body.get("product_name")
        if body.get("portion_g") is not None:
            portion_g = float(body.get("portion_g") or 100.0)
        image_base64 = body.get("image_base64")
        if image_base64 and not raw_text:
            encoded = image_base64.split(",")[-1]
            img_bytes = base64.b64decode(encoded)
            raw_text, ocr_engine, detected_id = extract_text_from_image_bytes(img_bytes, "upload.png")
            sample_id = sample_id or detected_id
    else:
        form = await request.form()
        if form.get("portion_g"):
            try:
                portion_g = float(str(form.get("portion_g")).replace(",", "."))
            except ValueError:
                portion_g = 100.0
        sample_id = str(form.get("sample_id") or "").strip() or None
        raw_text = str(form.get("raw_text") or "").strip() or None
        product_name = str(form.get("product_name") or "").strip() or None

        upload = form.get("file")
        if upload is not None and hasattr(upload, "read"):
            img_bytes = await upload.read()
            fname = getattr(upload, "filename", "rotulo.png") or "rotulo.png"
            extracted_text, ocr_engine, detected_id = extract_text_from_image_bytes(img_bytes, fname)
            if not raw_text:
                raw_text = extracted_text
            if not sample_id and detected_id:
                sample_id = detected_id

    if sample_id and sample_id in SAMPLE_LABELS:
        spec = SAMPLE_LABELS[sample_id]
        if not raw_text:
            raw_text = spec["raw_text"]
        if not product_name:
            product_name = spec["product_name"]
        image_url = f"/static/samples/{spec['filename']}"
        if portion_g <= 0:
            portion_g = spec["default_consumed_g"]

    if not raw_text:
        spec = SAMPLE_LABELS["rotulo_whey"]
        raw_text = spec["raw_text"]
        sample_id = "rotulo_whey"
        product_name = product_name or spec["product_name"]
        image_url = f"/static/samples/{spec['filename']}"

    goals = get_diet_goals()
    daily_limits = {
        "daily_kcal_limit": goals.daily_kcal_limit,
        "carbs_limit_g": goals.carbs_limit_g,
        "proteins_limit_g": goals.proteins_limit_g,
        "fat_limit_g": goals.fat_limit_g,
        "sodium_limit_mg": goals.sodium_limit_mg,
    }

    return parse_nutrition_table_text(
        raw_text=raw_text,
        portion_consumed_g=portion_g,
        product_name=product_name,
        daily_limits=daily_limits,
        sample_id=sample_id,
        image_url=image_url,
        ocr_engine=ocr_engine,
    )
