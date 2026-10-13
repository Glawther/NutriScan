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
    generate_diet_report_data,
    generate_diet_report_html,
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

    # Test compare same product A vs A
    comp_same = compare_products(prod_a, prod_a)
    assert all(d.diff == 0.0 for d in comp_same.deltas)
    assert all(d.favorable_barcode is None for d in comp_same.deltas)
    assert any("valores nutricionais idênticos" in note for note in comp_same.summary_notes)


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

    # 4. Test over-goal summary (bulking or binge day: 2600 kcal vs 2000 kcal goal)
    over_diary = {
        "date_str": "2026-10-14",
        "consumed": {"kcal": 2600, "proteins_g": 180, "carbohydrates_g": 300, "fat_g": 80, "sodium_mg": 2200},
        "goals": {"daily_kcal_limit": 2000},
        "entries": [],
    }
    over_wa = generate_whatsapp_summary(over_diary)
    assert "2600 / 2000 kcal (600 kcal acima da meta)" in over_wa


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

            # 4. Export in HTML format via /api/v1/diet/export?format=html
            r_export_html = client.get("/api/v1/diet/export?date_str=2026-10-15&format=html")
            assert r_export_html.status_code == 200
            assert "text/html" in r_export_html.headers.get("content-type", "")
            assert "NutriScan - Relatório da Dieta (15/10/2026)" in r_export_html.text
            assert "Arroz Integral" in r_export_html.text
            assert "Almoço" in r_export_html.text

            # 5. Export in JSON format via /api/v1/diet/export?format=json
            r_export_json = client.get("/api/v1/diet/export?date_str=2026-10-15&format=json")
            assert r_export_json.status_code == 200
            data_rep_json = r_export_json.json()
            assert data_rep_json["date_formatted"] == "15/10/2026"
            assert "kpis" in data_rep_json
            assert "meals" in data_rep_json
            assert "disclaimer" in data_rep_json

            # 6. Standalone report endpoint /api/v1/diet/report (HTML default)
            r_report_default = client.get("/api/v1/diet/report?date_str=2026-10-15&patient_name=Dr.+Silva")
            assert r_report_default.status_code == 200
            assert "text/html" in r_report_default.headers.get("content-type", "")
            assert "Dr. Silva" in r_report_default.text
            assert "Resumo Executivo dos KPIs Diários" in r_report_default.text
            assert "Aviso de Responsabilidade Nutricional" in r_report_default.text or "Aviso:" in r_report_default.text

            # 7. Standalone report endpoint with format=json
            r_report_json = client.get("/api/v1/diet/report?date_str=2026-10-15&format=json&patient_name=Mariana+Costa")
            assert r_report_json.status_code == 200
            data_rep = r_report_json.json()
            assert data_rep["patient"]["name"] == "Mariana Costa"
            assert data_rep["kpis"]["calories"]["consumed"] >= 130
            assert len(data_rep["meals"]) >= 4
        finally:
            client.delete(f"/api/v1/diet/diary/{created_id}")


def test_diet_report_generator_engine():
    diary_data = {
        "date_str": "2026-10-16",
        "consumed": {
            "kcal": 1850.0,
            "proteins_g": 140.0,
            "carbohydrates_g": 180.0,
            "fat_g": 55.0,
            "sodium_mg": 1400.0,
        },
        "goals": {
            "daily_kcal_limit": 2000.0,
            "proteins_limit_g": 150.0,
            "carbs_limit_g": 200.0,
            "fat_limit_g": 65.0,
            "sodium_limit_mg": 2000.0,
        },
        "entries": [
            {
                "meal_type": "Café da manhã",
                "product_name": "Omelete com Queijo",
                "portion_g": 120.0,
                "kcal": 220.0,
                "carbohydrates_g": 2.0,
                "proteins_g": 18.0,
                "fat_g": 16.0,
            },
            {
                "meal_type": "Almoço",
                "product_name": "Salmão com Legumes",
                "portion_g": 300.0,
                "kcal": 550.0,
                "carbohydrates_g": 25.0,
                "proteins_g": 45.0,
                "fat_g": 22.0,
            },
            {
                "meal_type": "Lanche",
                "product_name": "Iogurte Natural + Frutas",
                "portion_g": 200.0,
                "kcal": 180.0,
                "carbohydrates_g": 28.0,
                "proteins_g": 10.0,
                "fat_g": 3.0,
            },
            {
                "meal_type": "Jantar",
                "product_name": "Sopa de Frango com Legumes",
                "portion_g": 350.0,
                "kcal": 320.0,
                "carbohydrates_g": 20.0,
                "proteins_g": 35.0,
                "fat_g": 8.0,
            },
        ],
    }
    water_data = {"amount_ml": 2200, "goal_ml": 2800}
    profile_data = {
        "name": "Carlos Eduardo",
        "weight_kg": 80.0,
        "height_cm": 180.0,
        "age": 32,
        "goal_type": "cutting",
    }

    # Test structured data generation
    data = generate_diet_report_data(diary_data, water_data=water_data, profile_data=profile_data)
    assert data["date_formatted"] == "16/10/2026"
    assert data["patient"]["name"] == "Carlos Eduardo"
    assert "Peso: 80.0 kg" in data["patient"]["details_line"]
    assert "Emagrecimento" in data["patient"]["details_line"]
    assert data["kpis"]["calories"]["consumed"] == 1850
    assert data["kpis"]["calories"]["goal"] == 2000
    assert data["kpis"]["calories"]["remaining"] == 150
    assert data["kpis"]["hydration"]["consumed_ml"] == 2200
    assert data["kpis"]["hydration"]["goal_ml"] == 2800

    # Ensure all 4 meals are included
    meal_names = [m["meal_name"] for m in data["meals"]]
    assert "Café da manhã" in meal_names
    assert "Almoço" in meal_names
    assert "Lanche" in meal_names
    assert "Jantar" in meal_names

    # Test standalone HTML generation
    html = generate_diet_report_html(diary_data, water_data=water_data, profile_data=profile_data)
    assert "<!DOCTYPE html>" in html
    assert "NS" in html
    assert "NutriScan" in html
    assert "Carlos Eduardo" in html
    assert "16/10/2026" in html
    assert "Omelete com Queijo" in html
    assert "Salmão com Legumes" in html
    assert "Sopa de Frango com Legumes" in html
    assert "@media print" in html
    assert "Aviso:" in html or "Não substitui" in html






def test_plate_vision_engine_analysis():
    from app.engine.plate_vision import (
        ANVISA_IDR,
        SAMPLE_PLATES,
        TACO_DATABASE,
        analyze_food_plate_image,
        calculate_plate_composition,
        classify_color,
    )

    # 1. Test color classification heuristics
    assert classify_color(50, 150, 40) == "green"
    assert classify_color(220, 40, 30) == "red_orange"
    assert classify_color(240, 190, 30) == "yellow_gold"
    assert classify_color(60, 20, 70) == "purple_dark"
    assert classify_color(130, 80, 50) == "brown_dark"
    assert classify_color(245, 245, 240) in ("white_grain", "plate_background")

    # 2. Test TACO database and calculation
    items_weights = [("arroz_branco", 150.0), ("feijao_carioca", 100.0), ("frango_grelhado", 130.0), ("salada_verde", 60.0)]
    comp = calculate_plate_composition(items_weights)
    assert comp["total_weight_g"] == 440.0
    assert len(comp["items"]) == 4
    assert comp["totals"]["kcal"] > 400.0
    assert comp["totals"]["proteins_g"] > 45.0
    assert comp["micronutrients"]["potassium_mg"] > 500.0
    assert comp["anvisa_idr_impact_pct"]["kcal_pct"] > 0.0

    # 3. Test analysis with sample_id
    res_sample = analyze_food_plate_image(sample_id="omelete_fitness")
    assert res_sample["sample_id"] == "omelete_fitness"
    assert "Omelete" in res_sample["plate_name"]
    assert any(it["food_name"] == "Omelete de ovos inteiros" for it in res_sample["items"])
    assert any("Queijo" in it["food_name"] for it in res_sample["items"])

    # 4. Fallback without image
    res_empty = analyze_food_plate_image(image_bytes=None, sample_id=None)
    assert res_empty["sample_id"] == "prato_feito"
    assert res_empty["totals"]["kcal"] > 0


def test_fastapi_scan_plate_photo_endpoints():
    with TestClient(app) as client:
        # Test GET /api/v1/plate-samples
        r_list = client.get("/api/v1/plate-samples")
        assert r_list.status_code == 200
        samples = r_list.json()
        assert len(samples) >= 4
        sample_keys = [s["sample_id"] for s in samples]
        assert "prato_feito" in sample_keys
        assert "acai_banana" in sample_keys

        # Test POST /api/v1/scan-plate-photo with JSON sample_id
        r_plate = client.post(
            "/api/v1/scan-plate-photo",
            json={"sample_id": "salmao_legumes"},
        )
        assert r_plate.status_code == 200
        data = r_plate.json()
        assert "Salmão" in data["plate_name"]
        assert data["total_weight_g"] == 340.0
        assert data["confidence"] > 0.8
        assert data["micronutrients"]["vitamin_c_mg"] > 30.0

        # Test POST /api/v1/scan-plate-photo with multipart file upload
        from pathlib import Path
        img_path = Path("app/static/samples/pratos/prato_feito.png")
        if img_path.exists():
            with open(img_path, "rb") as f:
                r_file = client.post(
                    "/api/v1/scan-plate-photo",
                    files={"file": ("prato_teste.png", f, "image/png")},
                )
            assert r_file.status_code == 200
            file_data = r_file.json()
            assert "Prato Feito" in file_data["plate_name"]
            assert len(file_data["items"]) >= 3
            assert file_data["totals"]["kcal"] > 300


def test_taco_database_search_and_micronutrients():
    from app.database import (
        find_matching_food_by_visual_tags,
        get_taco_food_by_id,
        search_taco_foods,
    )
    from app.database.taco_foods import get_taco_catalog

    catalog = get_taco_catalog()
    assert len(catalog) >= 150, f"Catalog should contain 150+ foods, got {len(catalog)}"

    # 1. Test search_taco_foods for staple foods
    rice_results = search_taco_foods("arroz")
    assert len(rice_results) >= 2
    assert any("Arroz branco" in f["name"] for f in rice_results)

    bean_results = search_taco_foods("feijão")
    assert len(bean_results) >= 2
    assert any("Feijão carioca" in f["name"] for f in bean_results)

    chicken_results = search_taco_foods("frango")
    assert len(chicken_results) >= 2
    assert any("Peito de frango grelhado" in f["name"] for f in chicken_results)

    tilapia_results = search_taco_foods("tilápia")
    assert len(tilapia_results) >= 1

    sweet_potato_results = search_taco_foods("batata doce")
    assert len(sweet_potato_results) >= 1

    # 2. Test get_taco_food_by_id and micronutrient integrity
    first_food = rice_results[0]
    food_id = first_food["id"]
    food_by_id = get_taco_food_by_id(food_id)
    assert food_by_id is not None
    assert food_by_id["name"] == first_food["name"]

    # Verify all macronutrient and micronutrient fields exist and have proper types
    expected_fields = [
        "energy_kcal", "carbohydrates_g", "proteins_g", "fat_g", "fiber_g",
        "calcium_mg", "iron_mg", "sodium_mg", "potassium_mg",
        "magnesium_mg", "phosphorus_mg", "vitamin_c_mg", "zinc_mg",
        "visual_color_tags", "category"
    ]
    for field in expected_fields:
        assert field in food_by_id, f"Field '{field}' missing in TACO food"

    # Test nutrient ranges for chicken breast
    grilled_chicken = next(f for f in chicken_results if "Peito de frango grelhado" in f["name"])
    assert grilled_chicken["proteins_g"] > 25.0
    assert grilled_chicken["fat_g"] < 10.0
    assert grilled_chicken["potassium_mg"] > 200.0

    # 3. Test find_matching_food_by_visual_tags
    green_foods = find_matching_food_by_visual_tags("green")
    assert len(green_foods) >= 10
    green_names = [f["name"] for f in green_foods]
    assert any("Brócolis" in n or "Alface" in n or "Couve" in n for n in green_names)

    green_veggies = find_matching_food_by_visual_tags("green", category="Verduras e legumes")
    assert len(green_veggies) >= 5
    assert all(f["category"] == "Verduras e legumes" for f in green_veggies)

    white_foods = find_matching_food_by_visual_tags("white")
    assert len(white_foods) >= 10
    assert any("Arroz branco" in f["name"] for f in white_foods)


def test_fastapi_taco_foods_endpoints():
    with TestClient(app) as client:
        # 1. GET /api/v1/foods/search
        r_search = client.get("/api/v1/foods/search?q=banana")
        assert r_search.status_code == 200
        bananas = r_search.json()
        assert len(bananas) >= 2
        assert any("Banana prata" in b["name"] for b in bananas)

        # 2. GET /api/v1/foods/by-visual-tags
        r_tags = client.get("/api/v1/foods/by-visual-tags?color=purple")
        assert r_tags.status_code == 200
        purple_foods = r_tags.json()
        assert len(purple_foods) >= 1
        assert any("Açaí" in p["name"] or "Beterraba" in p["name"] or "Repolho roxo" in p["name"] for p in purple_foods)

        # 3. GET /api/v1/foods/{food_id}
        first_banana_id = bananas[0]["id"]
        r_food = client.get(f"/api/v1/foods/{first_banana_id}")
        assert r_food.status_code == 200
        banana_data = r_food.json()
        assert banana_data["id"] == first_banana_id
        assert "energy_kcal" in banana_data
        assert "potassium_mg" in banana_data
        assert banana_data["potassium_mg"] > 200.0

        # 4. Non-existent food_id returns 404
        r_not_found = client.get("/api/v1/foods/999999")
        assert r_not_found.status_code == 404


def test_micronutrient_aggregation_and_idr_engine():
    from app.database import add_diary_entry, get_daily_micronutrients, init_db
    from app.models.schemas import DietDiaryCreateRequest

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db = tmp.name

    try:
        init_db(test_db)
        test_date = "2026-10-15"

        # 1. Initially empty day has 0.0 totals and "Abaixo da meta" / "Excelente" (for sodium)
        empty_res = get_daily_micronutrients(date_str=test_date, db_path=test_db)
        assert empty_res["date_str"] == test_date
        assert empty_res["totals"]["calcium_mg"] == 0.0
        assert empty_res["totals"]["iron_mg"] == 0.0
        assert empty_res["totals"]["sodium_mg"] == 0.0
        assert len(empty_res["comparisons"]) == 8

        # 2. Add two balanced meals
        meal1 = DietDiaryCreateRequest(
            date_str=test_date,
            meal_type="Café da manhã",
            product_name="Iogurte com Aveia e Frutas",
            portion_g=200.0,
            kcal=250.0,
            calcium_mg=400.0,
            iron_mg=3.0,
            sodium_mg=150.0,
            potassium_mg=600.0,
            magnesium_mg=80.0,
            phosphorus_mg=250.0,
            vitamin_c_mg=45.0,
            zinc_mg=2.0,
        )
        add_diary_entry(meal1, db_path=test_db)

        meal2 = DietDiaryCreateRequest(
            date_str=test_date,
            meal_type="Almoço",
            product_name="Prato Feito Tradicional",
            portion_g=400.0,
            kcal=650.0,
            calcium_mg=650.0,
            iron_mg=12.0,
            sodium_mg=2100.0,
            potassium_mg=3000.0,
            magnesium_mg=200.0,
            phosphorus_mg=500.0,
            vitamin_c_mg=60.0,
            zinc_mg=5.5,
        )
        add_diary_entry(meal2, db_path=test_db)

        # 3. Aggregation check
        daily = get_daily_micronutrients(date_str=test_date, db_path=test_db)
        totals = daily["totals"]

        assert totals["calcium_mg"] == 1050.0
        assert totals["iron_mg"] == 15.0
        assert totals["sodium_mg"] == 2250.0
        assert totals["potassium_mg"] == 3600.0
        assert totals["magnesium_mg"] == 280.0
        assert totals["phosphorus_mg"] == 750.0
        assert totals["vitamin_c_mg"] == 105.0
        assert totals["zinc_mg"] == 7.5

        # 4. Check ANVISA IDR comparisons
        comps = {c["nutrient"]: c for c in daily["comparisons"]}

        # Cálcio: goal 1000 mg -> 1050 mg = 105.0% -> "Excelente"
        assert comps["Cálcio"]["idr_goal"] == 1000.0
        assert comps["Cálcio"]["consumed"] == 1050.0
        assert comps["Cálcio"]["pct_idr"] == 105.0
        assert comps["Cálcio"]["status"] == "Excelente"

        # Ferro: goal 14 mg -> 15 mg = 107.1% -> "Excelente"
        assert comps["Ferro"]["idr_goal"] == 14.0
        assert comps["Ferro"]["consumed"] == 15.0
        assert comps["Ferro"]["pct_idr"] == 107.1
        assert comps["Ferro"]["status"] == "Excelente"

        # Sódio: goal 2000 mg (limite máximo) -> 2250 mg = 112.5% -> "Atenção: Alto"
        assert comps["Sódio"]["idr_goal"] == 2000.0
        assert comps["Sódio"]["consumed"] == 2250.0
        assert comps["Sódio"]["pct_idr"] == 112.5
        assert comps["Sódio"]["status"] == "Atenção: Alto"

        # Potássio: goal 3500 mg -> 3600 mg = 102.9% -> "Excelente"
        assert comps["Potássio"]["idr_goal"] == 3500.0
        assert comps["Potássio"]["pct_idr"] == 102.9
        assert comps["Potássio"]["status"] == "Excelente"

        # Magnésio: goal 260 mg -> 280 mg = 107.7% -> "Excelente"
        assert comps["Magnésio"]["idr_goal"] == 260.0
        assert comps["Magnésio"]["pct_idr"] == 107.7
        assert comps["Magnésio"]["status"] == "Excelente"

        # Fósforo: goal 700 mg -> 750 mg = 107.1% -> "Excelente"
        assert comps["Fósforo"]["idr_goal"] == 700.0
        assert comps["Fósforo"]["pct_idr"] == 107.1
        assert comps["Fósforo"]["status"] == "Excelente"

        # Vitamina C: goal 100 mg -> 105 mg = 105.0% -> "Excelente"
        assert comps["Vitamina C"]["idr_goal"] == 100.0
        assert comps["Vitamina C"]["pct_idr"] == 105.0
        assert comps["Vitamina C"]["status"] == "Excelente"

        # Zinco: goal 7 mg -> 7.5 mg = 107.1% -> "Excelente"
        assert comps["Zinco"]["idr_goal"] == 7.0
        assert comps["Zinco"]["pct_idr"] == 107.1
        assert comps["Zinco"]["status"] == "Excelente"

        # 5. Test "Adequado" and "Abaixo da meta" statuses
        test_date2 = "2026-10-16"
        meal_partial = DietDiaryCreateRequest(
            date_str=test_date2,
            meal_type="Lanche",
            product_name="Lanche Leve",
            portion_g=100.0,
            kcal=180.0,
            calcium_mg=750.0,  # 75% da IDR -> "Adequado"
            iron_mg=5.0,       # 35.7% da IDR -> "Abaixo da meta"
            sodium_mg=1700.0,  # 85% do limite -> "Adequado"
            potassium_mg=1000.0,
            magnesium_mg=100.0,
            phosphorus_mg=200.0,
            vitamin_c_mg=20.0,
            zinc_mg=2.0,
        )
        add_diary_entry(meal_partial, db_path=test_db)
        daily2 = get_daily_micronutrients(date_str=test_date2, db_path=test_db)
        comps2 = {c["nutrient"]: c for c in daily2["comparisons"]}

        assert comps2["Cálcio"]["status"] == "Adequado"
        assert comps2["Ferro"]["status"] == "Abaixo da meta"
        assert comps2["Sódio"]["status"] == "Adequado"

    finally:
        if os.path.exists(test_db):
            os.remove(test_db)


def test_fastapi_diet_micronutrients_endpoint():
    with TestClient(app) as client:
        # 1. GET /api/v1/diet/micronutrients (default today)
        r = client.get("/api/v1/diet/micronutrients")
        assert r.status_code == 200
        data = r.json()
        assert "date_str" in data
        assert "totals" in data
        assert "comparisons" in data

        # Verify all 8 fields in totals
        expected_nutrients = [
            "calcium_mg", "iron_mg", "sodium_mg", "potassium_mg",
            "magnesium_mg", "phosphorus_mg", "vitamin_c_mg", "zinc_mg"
        ]
        for nutr in expected_nutrients:
            assert nutr in data["totals"]
            assert isinstance(data["totals"][nutr], (int, float))

        # Verify comparisons list has 8 items
        assert len(data["comparisons"]) == 8
        for comp in data["comparisons"]:
            assert "nutrient" in comp
            assert "unit" in comp
            assert "consumed" in comp
            assert "idr_goal" in comp
            assert "pct_idr" in comp
            assert comp["status"] in ("Excelente", "Adequado", "Abaixo da meta", "Atenção: Alto")

        # 2. GET /api/v1/diet/micronutrients with specific date
        test_date = "2026-10-20"
        r_date = client.get(f"/api/v1/diet/micronutrients?date={test_date}")
        assert r_date.status_code == 200
        data_date = r_date.json()
        assert data_date["date_str"] == test_date

        # 3. Add an entry via POST /api/v1/diet/diary and verify reflection in micronutrients
        meal_payload = {
            "date_str": test_date,
            "meal_type": "Almoço",
            "product_name": "Salmão com Brócolis e Batata",
            "source_type": "manual",
            "portion_g": 350.0,
            "kcal": 520.0,
            "carbohydrates_g": 35.0,
            "proteins_g": 42.0,
            "fat_g": 18.0,
            "fiber_g": 5.0,
            "sodium_mg": 450.0,
            "calcium_mg": 280.0,
            "iron_mg": 4.5,
            "potassium_mg": 850.0,
            "magnesium_mg": 95.0,
            "phosphorus_mg": 380.0,
            "vitamin_c_mg": 65.0,
            "zinc_mg": 2.2,
        }
        r_post = client.post("/api/v1/diet/diary", json=meal_payload)
        assert r_post.status_code == 200
        created_entry = r_post.json()
        assert created_entry["calcium_mg"] == 280.0
        assert created_entry["vitamin_c_mg"] == 65.0

        # Query micronutrients endpoint again for that date
        r_after = client.get(f"/api/v1/diet/micronutrients?date={test_date}")
        assert r_after.status_code == 200
        after_data = r_after.json()
        assert after_data["totals"]["calcium_mg"] >= 280.0
        assert after_data["totals"]["vitamin_c_mg"] >= 65.0
        assert after_data["totals"]["potassium_mg"] >= 850.0

        # Cleanup created entry
        client.delete(f"/api/v1/diet/diary/{created_entry['id']}")


def test_mifflin_st_jeor_backend_parity_and_safety_floors():
    from app.database import calculate_mifflin_goals

    # 1. Homem padrão (80kg, 180cm, 30 anos, sedentário, manutenção)
    # TMB = 10*80 + 6.25*180 - 5*30 + 5 = 800 + 1125 - 150 + 5 = 1780 kcal
    # TDEE = 1780 * 1.2 = 2136 kcal
    # Proteína: 1.6 g/kg * 80 = 128g; Gordura: 0.8 g/kg * 80 = 64g
    # Carbs: (2136 - 128*4 - 64*9) / 4 = (2136 - 512 - 576) / 4 = 1048 / 4 = 262g
    # Água: 80 * 35 = 2800 ml
    res_m = calculate_mifflin_goals(80.0, 180.0, 30, "sedentario", "manutencao", gender="masculino")
    assert res_m["tmb"] == 1780.0
    assert res_m["tdee"] == 2136.0
    assert res_m["daily_kcal_limit"] == 2136.0
    assert res_m["proteins_limit_g"] == 128.0
    assert res_m["fat_limit_g"] == 64.0
    assert res_m["carbs_limit_g"] == 262.0
    assert res_m["water_goal_ml"] == 2800.0

    # 2. Mulher padrão (60kg, 165cm, 25 anos, sedentário, manutenção)
    # TMB = 10*60 + 6.25*165 - 5*25 - 161 = 600 + 1031.25 - 125 - 161 = 1345.25 -> 1345 kcal
    # TDEE = 1345.25 * 1.2 = 1614.3 -> 1614 kcal
    res_f = calculate_mifflin_goals(60.0, 165.0, 25, "sedentario", "manutencao", gender="feminino")
    assert res_f["tmb"] == 1345.0
    assert res_f["tdee"] == 1614.0
    assert res_f["daily_kcal_limit"] == 1614.0
    assert res_f["water_goal_ml"] == 2100.0

    # 3. Piso de segurança nutricional para pessoas de baixo peso em cutting agressivo:
    # Mulher: 42kg, 150cm, 50 anos, sedentária, cutting (-400 kcal)
    # TMB = 946.5 kcal; TDEE = 1135.8 kcal. Sem piso daria ~736 kcal!
    # Piso obrigatório: 1200 kcal
    safe_f = calculate_mifflin_goals(42.0, 150.0, 50, "sedentario", "cutting", gender="feminino")
    assert safe_f["daily_kcal_limit"] == 1200.0
    assert safe_f["carbs_limit_g"] > 0.0

    # Homem: 48kg, 160cm, 50 anos, sedentário, cutting (-400 kcal)
    # TMB = 1235 kcal; TDEE = 1482 kcal. Sem piso daria ~1082 kcal!
    # Piso obrigatório: 1500 kcal
    safe_m = calculate_mifflin_goals(48.0, 160.0, 50, "sedentario", "cutting", gender="masculino")
    assert safe_m["daily_kcal_limit"] == 1500.0
    assert safe_m["carbs_limit_g"] > 0.0


def test_label_ocr_beverage_rdc429_detection():
    from app.engine.label_ocr import parse_nutrition_table_text

    raw_juice_label = (
        "INFORMAÇÃO NUTRICIONAL\n"
        "Produto: Néctar de Fruta Uva\n"
        "Porção de 200 ml (1 copo)\n"
        "Valor energético: 90 kcal\n"
        "Carboidratos: 22,0 g\n"
        "Açúcares totais: 20,0 g\n"
        "Proteínas: 0,0 g\n"
        "Gorduras totais: 0,0 g\n"
        "Gorduras saturadas: 0,0 g\n"
        "Fibra alimentar: 0,0 g\n"
        "Sódio: 15 mg"
    )
    res = parse_nutrition_table_text(raw_juice_label, portion_consumed_g=200.0)
    # 20g por 200ml equivale a 10g / 100ml.
    # Como é bebida, o limiar é 7.5g/100ml -> DEVE gerar ALTO EM AÇÚCAR
    assert res.anvisa.is_beverage is True
    assert res.anvisa.high_sugar is True
    assert "ALTO EM AÇÚCAR" in res.anvisa.warnings_list


def test_robustness_malformed_payloads_and_xss():
    with TestClient(app) as client:
        # 1. Invalid date in trends endpoint safely falls back to today's date (returns 200, no 500 crash)
        res_trends = client.get("/api/v1/diet/trends?end_date=invalid-date-format")
        assert res_trends.status_code == 200
        assert "days" in res_trends.json()
        assert len(res_trends.json()["days"]) == 7

        # 2. Water log with negative or excessive amounts via /api/v1/diet/water
        res_neg_water = client.post("/api/v1/diet/water", json={"date_str": "2026-10-13", "amount_ml": -500})
        assert res_neg_water.status_code == 200
        assert res_neg_water.json()["amount_ml"] >= 0

        # 3. Label photo endpoint with bad base64 safely handles error without 500
        res_bad_b64 = client.post("/api/v1/scan-label-photo", json={"image_base64": "!!!not-valid-base64!!!"})
        assert res_bad_b64.status_code == 200

        # 4. Plate photo endpoint with bad base64 safely handles error without 500
        res_bad_plate_b64 = client.post("/api/v1/scan-plate-photo", json={"image_base64": "invalid_base64"})
        assert res_bad_plate_b64.status_code == 200

        # 5. Search with potential XSS / script payload
        res_xss_search = client.get("/api/v1/search?q=<script>alert(1)</script>")
        assert res_xss_search.status_code == 200
        # Returns empty or safe list without unhandled 500 error
        assert isinstance(res_xss_search.json(), list)