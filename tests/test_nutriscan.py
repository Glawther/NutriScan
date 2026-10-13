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


