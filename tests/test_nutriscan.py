import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from app.database import get_cached_product, get_metrics, init_db, list_history, save_product
from app.engine.analyzer import (
    analyze_raw_product,
    compare_products,
    evaluate_anvisa_rdc429,
    get_nova_label,
    parse_additives,
)
from app.engine.diet_exporter import (
    generate_plain_text_summary,
    generate_whatsapp_summary,
)
from app.models.schemas import NutritionPer100g
from main import app


def test_anvisa_solid_thresholds():
    nutrition = NutritionPer100g(
        energy_kcal=510.0,
        sugars_g=15.0,
        saturated_fat_g=6.5,
        sodium_mg=590.0,
    )
    alerts = evaluate_anvisa_rdc429(nutrition, is_beverage=False)
    assert alerts.high_sugar is True
    assert alerts.high_saturated_fat is True
    assert alerts.high_sodium is False
    assert alerts.warnings_count == 2
    assert "ALTO EM AÇÚCAR" in alerts.warnings_list
    assert "ALTO EM GORDURA SATURADA" in alerts.warnings_list


def test_anvisa_liquid_beverage_thresholds():
    nutrition = NutritionPer100g(
        energy_kcal=42.0,
        sugars_g=10.6,
        saturated_fat_g=0.0,
        sodium_mg=5.0,
    )
    # 10.6g seria abaixo do limite de sólidos (15g), mas acima do limite de líquidos (7.5g)
    alerts = evaluate_anvisa_rdc429(nutrition, is_beverage=True)
    assert alerts.is_beverage is True
    assert alerts.high_sugar is True
    assert alerts.high_saturated_fat is False
    assert alerts.warnings_list == ["ALTO EM AÇÚCAR"]


def test_anvisa_high_sodium_solid():
    nutrition = NutritionPer100g(
        energy_kcal=496.0,
        sugars_g=2.0,
        saturated_fat_g=11.2,
        sodium_mg=648.0,
    )
    alerts = evaluate_anvisa_rdc429(nutrition, is_beverage=False)
    assert alerts.high_sodium is True
    assert alerts.high_saturated_fat is True
    assert "ALTO EM SÓDIO" in alerts.warnings_list


def test_parse_additives_and_nova_labels():
    tags = ["en:e322", "en:e150d", "en:e338", "en:e950"]
    parsed = parse_additives(tags)
    codes = [item.code for item in parsed]
    assert codes == ["E322", "E150d", "E338", "E950"]
    assert parsed[0].name == "Lecitina de soja"
    assert parsed[1].name == "Corante caramelo IV"
    assert get_nova_label(1) == "In natura ou minimamente processado"
    assert get_nova_label(4) == "Ultraprocessado"


def test_compare_products_deltas():
    raw_a = {
        "code": "3017620422003",
        "product_name_pt": "Nutella",
        "brands": "Ferrero",
        "nutriscore_grade": "E",
        "nova_group": 4,
        "additives_tags": ["en:e322"],
        "nutriments": {
            "energy-kcal_100g": 539.0,
            "sugars_100g": 56.3,
            "saturated-fat_100g": 10.6,
            "proteins_100g": 6.3,
            "fiber_100g": 3.4,
            "sodium_100g": 0.042,
        },
    }
    raw_b = {
        "code": "7891000053508",
        "product_name_pt": "Aveia Quaker",
        "brands": "Quaker",
        "nutriscore_grade": "A",
        "nova_group": 1,
        "additives_tags": [],
        "nutriments": {
            "energy-kcal_100g": 346.0,
            "sugars_100g": 1.0,
            "saturated-fat_100g": 1.5,
            "proteins_100g": 14.3,
            "fiber_100g": 9.1,
            "sodium_100g": 0.0,
        },
    }
    prod_a = analyze_raw_product(raw_a)
    prod_b = analyze_raw_product(raw_b)
    comp = compare_products(prod_a, prod_b)

    sugar_delta = next(d for d in comp.deltas if d.metric == "sugars_g")
    assert sugar_delta.diff == 55.3
    assert sugar_delta.favorable_barcode == "7891000053508"

    protein_delta = next(d for d in comp.deltas if d.metric == "proteins_g")
    assert protein_delta.diff == -8.0
    assert protein_delta.favorable_barcode == "7891000053508"


def test_sqlite_storage_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = os.path.join(tmpdir, "test_nutriscan.db")
        init_db(db_file)
        prod = analyze_raw_product(
            {
                "code": "7891025101604",
                "product_name_pt": "Iogurte Natural",
                "brands": "Danone",
                "nutriscore_grade": "A",
                "nova_group": 1,
                "nutriments": {"energy-kcal_100g": 62.0, "sugars_100g": 4.8},
            }
        )
        save_product(prod, db_path=db_file)
        cached = get_cached_product("7891025101604", db_path=db_file)
        assert cached is not None
        assert cached.product_name == "Iogurte Natural"

        history = list_history(db_path=db_file)
        assert len(history) == 1

        metrics = get_metrics(db_path=db_file)
        assert metrics["total_products"] == 1
        assert metrics["in_natura_nova1"] == 1


def test_fastapi_endpoints():
    with TestClient(app) as client:
        r_health = client.get("/api/v1/health")
        assert r_health.status_code == 200
        assert r_health.json()["status"] == "ok"

        r_prod = client.get("/api/v1/product/3017620422003")
        assert r_prod.status_code == 200
        body = r_prod.json()
        assert body["barcode"] == "3017620422003"
        assert body["anvisa"]["high_sugar"] is True
        assert body["anvisa"]["high_saturated_fat"] is True

        r_comp = client.get("/api/v1/compare?barcode_a=3017620422003&barcode_b=7891000053508")
        assert r_comp.status_code == 200
        comp_data = r_comp.json()
        assert comp_data["product_a"]["barcode"] == "3017620422003"
        assert comp_data["product_b"]["barcode"] == "7891000053508"
        assert len(comp_data["deltas"]) == 7

        r_search = client.get("/api/v1/search?q=coca")
        assert r_search.status_code == 200
        assert len(r_search.json()) >= 1

        r_hist = client.get("/api/v1/history")
        assert r_hist.status_code == 200
        assert len(r_hist.json()) >= 6


def test_nutriscore_fallback_and_allergens():
    raw_item = {
        "code": "7890000000001",
        "product_name_pt": "Biscoito Integral Teste",
        "brands": "Marca Teste",
        "allergens_tags": ["en:milk", "en:wheat", "en:soybeans"],
        "nutriments": {
            "energy-kcal_100g": 140.0,
            "sugars_100g": 2.0,
            "saturated-fat_100g": 0.8,
            "proteins_100g": 9.5,
            "fiber_100g": 5.2,
            "sodium_100g": 0.08,
        },
    }
    analyzed = analyze_raw_product(raw_item)
    assert analyzed.nutriscore_grade == "A"
    assert "Leite e derivados" in analyzed.allergens
    assert "Trigo" in analyzed.allergens
    assert "Soja" in analyzed.allergens


def test_label_ocr_parsing():
    from app.engine.label_ocr import parse_nutrition_table_text

    raw_label = (
        "INFORMAÇÃO NUTRICIONAL\n"
        "Produto: Whey Protein Isolado\n"
        "Porção de 30g (2 dosadores)\n"
        "Valor energético: 110 kcal\n"
        "Carboidratos: 1,5 g\n"
        "Açúcares totais: 0,5 g\n"
        "Proteínas: 26,0 g\n"
        "Gorduras totais: 0,5 g\n"
        "Gorduras saturadas: 0,2 g\n"
        "Fibra alimentar: 0,0 g\n"
        "Sódio: 45 mg"
    )
    res = parse_nutrition_table_text(raw_label, portion_consumed_g=45.0)
    assert res.product_name == "Whey Protein Isolado"
    assert res.portion_label_g == 30.0
    assert res.portion_consumed_g == 45.0
    assert res.scale_factor == 1.5
    assert res.consumed_macros["kcal"] == 165.0
    assert res.consumed_macros["proteins_g"] == 39.0
    assert res.consumed_macros["carbohydrates_g"] == 2.2
    assert res.consumed_macros["sodium_mg"] == 67.5


def test_diet_tracker_and_photo_endpoints():
    with TestClient(app) as client:
        # Test label photo endpoint
        r_ocr = client.post(
            "/api/v1/scan-label-photo",
            json={"sample_id": "rotulo_whey", "portion_g": 60.0},
        )
        assert r_ocr.status_code == 200
        ocr_data = r_ocr.json()
        assert ocr_data["portion_consumed_g"] == 60.0
        assert ocr_data["consumed_macros"]["kcal"] == 240.0
        assert ocr_data["consumed_macros"]["proteins_g"] == 48.0

        # Test diet goals
        r_goals = client.put(
            "/api/v1/diet/goals",
            json={
                "goal_type": "bulking",
                "daily_kcal_limit": 2500,
                "proteins_limit_g": 180,
                "carbs_limit_g": 300,
                "fat_limit_g": 70,
                "sodium_limit_mg": 2200,
            },
        )
        assert r_goals.status_code == 200
        assert r_goals.json()["daily_kcal_limit"] == 2500

        # Test diary entry creation and today summary
        r_entry = client.post(
            "/api/v1/diet/diary",
            json={
                "meal_type": "Lanche",
                "product_name": "Whey Protein Teste",
                "source_type": "foto_ficha",
                "portion_g": 60,
                "kcal": 240,
                "carbohydrates_g": 6.4,
                "proteins_g": 48.0,
                "fat_g": 3.6,
                "fiber_g": 0.0,
                "sodium_mg": 110,
            },
        )
        assert r_entry.status_code == 200
        entry_id = r_entry.json()["id"]

        r_today = client.get("/api/v1/diet/today")
        assert r_today.status_code == 200
        today_data = r_today.json()
        assert today_data["consumed"]["kcal"] >= 240
        assert any(e["id"] == entry_id for e in today_data["entries"])

        # Delete entry
        r_del = client.delete(f"/api/v1/diet/diary/{entry_id}")
        assert r_del.status_code == 200


def test_water_tracking_and_trends():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = os.path.join(tmpdir, "test_water.db")
        init_db(db_file)

        from app.database import (
            get_7day_trends,
            get_water_for_date,
            log_water,
            reset_water_for_date,
        )

        test_date = "2026-10-10"

        # Initial water check: default goal 78kg * 35 = 2730 ml
        w0 = get_water_for_date(test_date, db_path=db_file)
        assert w0["amount_ml"] == 0
        assert w0["goal_ml"] == 2730
        assert w0["remaining_ml"] == 2730
        assert w0["pct"] == 0.0

        # Log 500 ml
        w1 = log_water(500, test_date, db_path=db_file)
        assert w1["amount_ml"] == 500
        assert w1["remaining_ml"] == 2230
        assert w1["pct"] == round((500 / 2730) * 100.0, 1)

        # Log another 250 ml
        w2 = log_water(250, test_date, db_path=db_file)
        assert w2["amount_ml"] == 750
        assert w2["remaining_ml"] == 1980

        # Reset water
        res = reset_water_for_date(test_date, db_path=db_file)
        assert res is True
        w3 = get_water_for_date(test_date, db_path=db_file)
        assert w3["amount_ml"] == 0
        assert w3["remaining_ml"] == 2730

        # Trends test
        trends = get_7day_trends(end_date_str="2026-10-10", db_path=db_file)
        assert len(trends["days"]) == 7
        assert trends["days"][-1]["date_str"] == "2026-10-10"
        assert "avg_kcal" in trends
        assert "compliance_rate" in trends
        assert "total_water_liters" in trends


def test_fastapi_water_and_trends_endpoints():
    with TestClient(app) as client:
        # GET /api/v1/diet/water
        r_get = client.get("/api/v1/diet/water")
        assert r_get.status_code == 200
        water_info = r_get.json()
        assert "amount_ml" in water_info
        assert "goal_ml" in water_info
        assert "remaining_ml" in water_info
        assert "pct" in water_info

        # POST /api/v1/diet/water
        r_post = client.post("/api/v1/diet/water", json={"amount_ml": 250})
        assert r_post.status_code == 200
        updated = r_post.json()
        assert updated["amount_ml"] >= 250

        # DELETE /api/v1/diet/water
        r_del = client.delete("/api/v1/diet/water")
        assert r_del.status_code == 200
        assert r_del.json()["reset"] is True

        # Check water after reset
        r_after = client.get("/api/v1/diet/water")
        assert r_after.status_code == 200
        assert r_after.json()["amount_ml"] == 0

        # GET /api/v1/diet/trends
        r_trends = client.get("/api/v1/diet/trends")
        assert r_trends.status_code == 200
        t_data = r_trends.json()
        assert len(t_data["days"]) == 7
        assert "avg_kcal" in t_data
        assert "compliance_rate" in t_data
        assert "total_water_liters" in t_data
        assert t_data["days"][0]["weekday_short"] != ""

        # Test date navigation on /diet/today and /diet/day
        past_date = "2026-10-01"
        r_day = client.get(f"/api/v1/diet/today?date={past_date}")
        assert r_day.status_code == 200
        assert r_day.json()["date_str"] == past_date

        r_day2 = client.get(f"/api/v1/diet/day?date={past_date}")
        assert r_day2.status_code == 200
        assert r_day2.json()["date_str"] == past_date


def test_generate_whatsapp_and_plain_text_summary():
    diary_data = {
        "date_str": "2026-10-13",
        "goals": {
            "daily_kcal_limit": 2000.0,
            "proteins_limit_g": 150.0,
            "carbs_limit_g": 200.0,
            "fat_limit_g": 65.0,
            "sodium_limit_mg": 2000.0,
        },
        "consumed": {
            "kcal": 1450.0,
            "proteins_g": 120.0,
            "carbohydrates_g": 150.0,
            "fat_g": 42.0,
            "sodium_mg": 1350.0,
        },
        "remaining": {
            "kcal": 550.0,
            "proteins_g": 30.0,
            "carbohydrates_g": 50.0,
            "fat_g": 23.0,
            "sodium_mg": 650.0,
        },
        "entries": [
            {
                "meal_type": "Café da manhã",
                "product_name": "Pão Integral",
                "portion_g": 50.0,
                "kcal": 120.0,
            },
            {
                "meal_type": "Café da manhã",
                "product_name": "Ovos Mexidos",
                "portion_g": 100.0,
                "kcal": 150.0,
            },
            {
                "meal_type": "Almoço",
                "product_name": "Frango Grelhado",
                "portion_g": 150.0,
                "kcal": 220.0,
            },
            {
                "meal_type": "Lanche",
                "product_name": "Whey Protein Concentrado",
                "portion_g": 30.0,
                "kcal": 120.0,
            },
        ],
    }
    water_data = {
        "amount_ml": 1800,
        "goal_ml": 2500,
        "remaining_ml": 700,
    }

    # 1. WhatsApp Summary Formatting
    wa_text = generate_whatsapp_summary(diary_data, water_data=water_data)

    assert "🥗 *NutriScan - Resumo da Dieta (13/10/2026)*" in wa_text
    assert "🔥 Calorias: 1450 / 2000 kcal (550 kcal restantes)" in wa_text
    assert "💪 Proteína: 120g | 🌾 Carbs: 150g | 🥑 Gordura: 42g | 🧂 Sódio: 1350mg" in wa_text
    assert "💧 Água: 1800 ml / 2500 ml" in wa_text
    assert "*Café da manhã*" in wa_text
    assert "• Pão Integral (50g) - 120 kcal" in wa_text
    assert "• Ovos Mexidos (100g) - 150 kcal" in wa_text
    assert "*Almoço*" in wa_text
    assert "• Frango Grelhado (150g) - 220 kcal" in wa_text
    assert "*Lanche*" in wa_text
    assert "• Whey Protein Concentrado (30g) - 120 kcal" in wa_text

    # 2. Plain Text Summary Formatting (No markdown asterisks)
    plain_text = generate_plain_text_summary(diary_data, water_data=water_data)

    assert "*" not in plain_text
    assert "🥗 NutriScan - Resumo da Dieta (13/10/2026)" in plain_text
    assert "🔥 Calorias: 1450 / 2000 kcal (550 kcal restantes)" in plain_text
    assert "💪 Proteína: 120g | 🌾 Carbs: 150g | 🥑 Gordura: 42g | 🧂 Sódio: 1350mg" in plain_text
    assert "💧 Água: 1800 ml / 2500 ml" in plain_text
    assert "Café da manhã:" in plain_text
    assert "• Pão Integral (50g) - 120 kcal" in plain_text

    # 3. Test empty entries handling
    empty_diary = {
        "date_str": "2026-10-14",
        "consumed": {"kcal": 0, "proteins_g": 0, "carbohydrates_g": 0, "fat_g": 0, "sodium_mg": 0},
        "goals": {"daily_kcal_limit": 2000},
        "entries": [],
    }
    empty_wa = generate_whatsapp_summary(empty_diary)
    assert "(14/10/2026)" in empty_wa
    assert "Nenhuma refeição registrada" in empty_wa


def test_fastapi_diet_export_endpoint():
    with TestClient(app) as client:
        # Create a test diary entry first
        r_entry = client.post(
            "/api/v1/diet/diary",
            json={
                "date_str": "2026-10-15",
                "meal_type": "Almoço",
                "product_name": "Arroz Integral",
                "source_type": "manual",
                "portion_g": 100,
                "kcal": 130,
                "carbohydrates_g": 28,
                "proteins_g": 3,
                "fat_g": 1,
                "fiber_g": 2,
                "sodium_mg": 5,
            },
        )
        assert r_entry.status_code == 200
        created_id = r_entry.json()["id"]

        try:
            # 1. Export in WhatsApp format (default)
            r_export_wa = client.get("/api/v1/diet/export?date_str=2026-10-15")
            assert r_export_wa.status_code == 200
            data_wa = r_export_wa.json()
            assert data_wa["date"] == "2026-10-15"
            assert data_wa["format"] == "whatsapp"
            assert "🥗 *NutriScan - Resumo da Dieta (15/10/2026)*" in data_wa["text"]
            assert "Arroz Integral (100g) - 130 kcal" in data_wa["text"]
            assert data_wa["whatsapp_url"].startswith("https://api.whatsapp.com/send?text=")
            assert "NutriScan" in data_wa["whatsapp_url"] or "%20" in data_wa["whatsapp_url"]

            # 2. Export in Plain Text format
            r_export_txt = client.get("/api/v1/diet/export?date_str=2026-10-15&format=text")
            assert r_export_txt.status_code == 200
            data_txt = r_export_txt.json()
            assert data_txt["format"] == "text"
            assert "*" not in data_txt["text"]
            assert "🥗 NutriScan - Resumo da Dieta (15/10/2026)" in data_txt["text"]

            # 3. Export with today's date omitted (should default to current date)
            r_export_today = client.get("/api/v1/diet/export")
            assert r_export_today.status_code == 200
            data_today = r_export_today.json()
            assert data_today["format"] == "whatsapp"
            assert "NutriScan - Resumo da Dieta" in data_today["text"]
            assert data_today["whatsapp_url"].startswith("https://api.whatsapp.com/send?text=")
        finally:
            client.delete(f"/api/v1/diet/diary/{created_id}")




