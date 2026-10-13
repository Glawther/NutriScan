import base64
from urllib.parse import quote
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.config import APP_NAME, APP_VERSION
from app.database import (
    add_diary_entry,
    delete_diary_entry,
    find_matching_food_by_visual_tags,
    get_7day_trends,
    get_cached_product,
    get_daily_micronutrients,
    get_diet_goals,
    get_diet_today_summary,
    get_metrics,
    get_taco_food_by_id,
    get_water_for_date,
    list_history,
    log_water,
    reset_water_for_date,
    save_product,
    search_taco_foods,
    update_diet_goals,
)
from app.engine.analyzer import compare_products
from app.engine.diet_exporter import (
    generate_diet_report_data,
    generate_diet_report_html,
    generate_plain_text_summary,
    generate_whatsapp_summary,
)
from app.engine.label_ocr import (
    SAMPLE_LABELS,
    extract_text_from_image_bytes,
    parse_nutrition_table_text,
)
from app.models.schemas import (
    ComparisonResponse,
    DailyMicronutrientsResponse,
    DietDiaryCreateRequest,
    DietDiaryEntry,
    DietGoals,
    DietGoalsUpdateRequest,
    DietTodaySummary,
    LabelParseResult,
    ProductAnalysis,
    WaterLogCreate,
    WaterLogResponse,
    WeeklyTrendsResponse,
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


@router.get("/foods/search")
async def search_taco_foods_endpoint(
    q: str = Query("", description="Termo de busca para alimento TACO (ex: arroz, frango, feijão)"),
    limit: int = Query(20, ge=1, le=100, description="Limite máximo de resultados"),
):
    """
    Busca alimentos na Tabela Brasileira de Composição de Alimentos (TACO/TBCA) offline.
    """
    return search_taco_foods(query=q, limit=limit)


@router.get("/foods/by-visual-tags")
async def get_foods_by_visual_tags_endpoint(
    color: str = Query(..., description="Cor visual (ex: green, white, brown, red, yellow)"),
    category: Optional[str] = Query(None, description="Categoria opcional"),
):
    """
    Filtra alimentos da base TACO pelas tags de cores visuais (ex: 'green' para hortaliças).
    """
    return find_matching_food_by_visual_tags(color=color, category=category)


@router.get("/foods/{food_id}")
async def get_taco_food_endpoint(food_id: int):
    """
    Retorna os detalhes nutricionais completos (macro e micronutrientes per 100g) de um alimento TACO.
    """
    food = get_taco_food_by_id(food_id)
    if not food:
        raise HTTPException(
            status_code=404,
            detail=f"Alimento TACO com ID {food_id} não encontrado no catálogo.",
        )
    return food


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
async def get_diet_today_endpoint(
    date: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
    date_str: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
):
    target = date or date_str
    return get_diet_today_summary(date_str=target)


@router.get("/diet/day", response_model=DietTodaySummary)
async def get_diet_day_endpoint(
    date: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
    date_str: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
):
    target = date or date_str
    return get_diet_today_summary(date_str=target)


@router.get("/diet/micronutrients", response_model=DailyMicronutrientsResponse)
async def get_diet_micronutrients_endpoint(
    date: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
    date_str: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
):
    target = date or date_str
    return get_daily_micronutrients(date_str=target)



@router.get("/diet/export")
async def export_diet_endpoint(
    date: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
    date_str: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
    format: str = Query("whatsapp", description="Formato: 'whatsapp', 'text', 'html' ou 'json'"),
):
    target = date or date_str
    diary_summary = get_diet_today_summary(date_str=target)
    water_data = get_water_for_date(date_str=target)

    fmt = (format or "whatsapp").lower().strip()
    diary_dict = diary_summary.model_dump()

    if fmt == "html":
        html_content = generate_diet_report_html(diary_dict, water_data=water_data)
        return HTMLResponse(content=html_content, status_code=200)

    if fmt == "json":
        return generate_diet_report_data(diary_dict, water_data=water_data)

    if fmt == "text":
        summary_text = generate_plain_text_summary(diary_dict, water_data=water_data)
    else:
        fmt = "whatsapp"
        summary_text = generate_whatsapp_summary(diary_dict, water_data=water_data)

    encoded_text = quote(summary_text)
    whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_text}"

    return {
        "date": diary_summary.date_str,
        "format": fmt,
        "text": summary_text,
        "whatsapp_url": whatsapp_url,
    }


@router.get("/diet/report")
async def get_diet_report_endpoint(
    date: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
    date_str: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
    format: str = Query("html", description="Formato: 'html' ou 'json'"),
    patient_name: Optional[str] = Query(None, description="Nome do paciente para o cabeçalho"),
):
    """
    Gera relatório executivo estruturado para impressão / download em PDF.
    format=html retorna documento completo standalone pronto para visualização e window.print().
    format=json retorna os dados limpos com KPIs calculados, refeições agrupadas e rodapé.
    """
    target = date or date_str
    diary_summary = get_diet_today_summary(date_str=target)
    water_data = get_water_for_date(date_str=target)
    diary_dict = diary_summary.model_dump()

    profile_data = None
    if patient_name:
        profile_data = {"name": patient_name.strip()}

    fmt = (format or "html").lower().strip()
    if fmt == "html":
        html_code = generate_diet_report_html(diary_dict, water_data=water_data, profile_data=profile_data)
        return HTMLResponse(content=html_code, status_code=200)

    return generate_diet_report_data(diary_dict, water_data=water_data, profile_data=profile_data)


@router.get("/diet/water", response_model=WaterLogResponse)
async def get_water_endpoint(
    date: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
    date_str: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
):
    target = date or date_str
    return get_water_for_date(date_str=target)


@router.post("/diet/water", response_model=WaterLogResponse)
async def log_water_endpoint(payload: WaterLogCreate):
    return log_water(amount_ml=payload.amount_ml, date_str=payload.date_str)


@router.delete("/diet/water")
async def delete_water_endpoint(
    date: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
    date_str: Optional[str] = Query(None, description="Data YYYY-MM-DD"),
):
    target = date or date_str
    reset_water_for_date(date_str=target)
    return {"reset": True, "date_str": target or "today"}


@router.get("/diet/trends", response_model=WeeklyTrendsResponse)
async def get_diet_trends_endpoint(
    end_date: Optional[str] = Query(None, description="Data final YYYY-MM-DD"),
    end_date_str: Optional[str] = Query(None, description="Data final YYYY-MM-DD"),
):
    target = end_date or end_date_str
    return get_7day_trends(end_date_str=target)


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
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        raw_text = str(body.get("raw_text") or "").strip() or None
        sample_id = str(body.get("sample_id") or "").strip() or None
        product_name = str(body.get("product_name") or "").strip() or None
        if body.get("portion_g") is not None:
            try:
                portion_g = float(body.get("portion_g") or 100.0)
            except (ValueError, TypeError):
                portion_g = 100.0
        image_base64 = body.get("image_base64")
        if image_base64 and not raw_text:
            try:
                encoded = str(image_base64).split(",")[-1]
                img_bytes = base64.b64decode(encoded)
                raw_text, ocr_engine, detected_id = extract_text_from_image_bytes(img_bytes, "upload.png")
                sample_id = sample_id or detected_id
            except Exception:
                pass
    else:
        try:
            form = await request.form()
        except Exception:
            form = {}
        if form.get("portion_g"):
            try:
                portion_g = float(str(form.get("portion_g")).replace(",", "."))
            except (ValueError, TypeError):
                portion_g = 100.0
        sample_id = str(form.get("sample_id") or "").strip() or None
        raw_text = str(form.get("raw_text") or "").strip() or None
        product_name = str(form.get("product_name") or "").strip() or None

        upload = form.get("file")
        if upload is not None and hasattr(upload, "read"):
            try:
                img_bytes = await upload.read()
                fname = getattr(upload, "filename", "rotulo.png") or "rotulo.png"
                extracted_text, ocr_engine, detected_id = extract_text_from_image_bytes(img_bytes, fname)
                if not raw_text:
                    raw_text = extracted_text
                if not sample_id and detected_id:
                    sample_id = detected_id
            except Exception:
                pass

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


from app.engine.plate_vision import (
    SAMPLE_PLATES,
    analyze_food_plate_image,
)
from app.models.schemas import PlateAnalysisResponse


@router.get("/plate-samples")
async def list_plate_samples_endpoint():
    items = []
    for key, spec in SAMPLE_PLATES.items():
        items.append({
            "sample_id": key,
            "plate_name": spec["plate_name"],
            "description": spec["description"],
            "plate_diameter_cm": spec["plate_diameter_cm"],
            "image_url": f"/static/samples/pratos/{spec['filename']}",
            "items_count": len(spec["items"]),
        })
    return items


@router.post("/scan-plate-photo", response_model=PlateAnalysisResponse)
async def scan_plate_photo_endpoint(request: Request):
    content_type = request.headers.get("content-type", "").lower()
    img_bytes: Optional[bytes] = None
    sample_id: Optional[str] = None

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        sample_id = str(body.get("sample_id") or "").strip() or None
        image_base64 = body.get("image_base64")
        if image_base64:
            try:
                encoded = str(image_base64).split(",")[-1]
                img_bytes = base64.b64decode(encoded)
            except Exception:
                img_bytes = None
    else:
        try:
            form = await request.form()
        except Exception:
            form = {}
        sample_id = str(form.get("sample_id") or "").strip() or None
        upload = form.get("file")
        if upload is not None and hasattr(upload, "read"):
            try:
                img_bytes = await upload.read()
            except Exception:
                img_bytes = None

    goals = get_diet_goals()
    daily_goals = {
        "daily_kcal_limit": goals.daily_kcal_limit,
        "carbs_limit_g": goals.carbs_limit_g,
        "proteins_limit_g": goals.proteins_limit_g,
        "fat_limit_g": goals.fat_limit_g,
        "sodium_limit_mg": goals.sodium_limit_mg,
    }

    result = analyze_food_plate_image(
        image_bytes=img_bytes,
        sample_id=sample_id,
        daily_goals=daily_goals,
    )
    return result