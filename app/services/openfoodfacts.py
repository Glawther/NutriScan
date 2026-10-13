from typing import Dict, List, Optional
import httpx

from app.config import HTTP_TIMEOUT_SECONDS, OFF_PRODUCT_URL, OFF_SEARCH_URL, USER_AGENT
from app.engine.analyzer import analyze_raw_product
from app.models.schemas import ProductAnalysis

FALLBACK_PRODUCTS: Dict[str, dict] = {
    "3017620422003": {
        "code": "3017620422003",
        "product_name_pt": "Creme de Avelã com Cacau Nutella",
        "brands": "Ferrero",
        "quantity": "350g",
        "categories": "Pastas para barrar, Cremes de avelã e cacau",
        "is_beverage": False,
        "nutriscore_grade": "E",
        "nova_group": 4,
        "ingredients_text_pt": "Açúcar, óleo de palma, avelãs (13%), leite desnatado em pó (8,7%), cacau magro (7,4%), emulsificante lecitinas (soja), vanilina.",
        "allergens_tags": ["en:milk", "en:nuts", "en:soybeans"],
        "additives_tags": ["en:e322"],
        "nutriments": {
            "energy-kcal_100g": 539.0,
            "carbohydrates_100g": 57.5,
            "sugars_100g": 56.3,
            "fat_100g": 30.9,
            "saturated-fat_100g": 10.6,
            "proteins_100g": 6.3,
            "fiber_100g": 3.4,
            "sodium_100g": 0.042,
            "salt_100g": 0.107,
        },
    },
    "7894900011517": {
        "code": "7894900011517",
        "product_name_pt": "Refrigerante Coca-Cola Original",
        "brands": "Coca-Cola",
        "quantity": "350ml",
        "categories": "Bebidas, Refrigerantes de cola",
        "is_beverage": True,
        "nutriscore_grade": "E",
        "nova_group": 4,
        "ingredients_text_pt": "Água gaseificada, açúcar, extrato de noz de cola, cafeína, corante caramelo IV (INS 150d), acidulante ácido fosfórico (INS 338) e aroma natural.",
        "allergens_tags": [],
        "additives_tags": ["en:e290", "en:e150d", "en:e338"],
        "nutriments": {
            "energy-kcal_100g": 42.0,
            "carbohydrates_100g": 10.6,
            "sugars_100g": 10.6,
            "fat_100g": 0.0,
            "saturated-fat_100g": 0.0,
            "proteins_100g": 0.0,
            "fiber_100g": 0.0,
            "sodium_100g": 0.005,
            "salt_100g": 0.013,
        },
    },
    "7622210691071": {
        "code": "7622210691071",
        "product_name_pt": "Wafer Recheado e Coberto Bis Ao Leite",
        "brands": "Lacta",
        "quantity": "126g",
        "categories": "Biscoitos e wafers cobertos com chocolate",
        "is_beverage": False,
        "nutriscore_grade": "E",
        "nova_group": 4,
        "ingredients_text_pt": "Açúcar, farinha de trigo enriquecida com ferro e ácido fólico, gordura vegetal hidrogenada, soro de leite em pó, cacau em pó, massa de cacau, manteiga de cacau, emulsificantes lecitina de soja e polirricinoleato de poliglicerol, fermento químico bicarbonato de sódio.",
        "allergens_tags": ["en:gluten", "en:wheat", "en:milk", "en:soybeans"],
        "additives_tags": ["en:e322", "en:e476", "en:e500"],
        "nutriments": {
            "energy-kcal_100g": 507.0,
            "carbohydrates_100g": 63.0,
            "sugars_100g": 52.0,
            "fat_100g": 24.5,
            "saturated-fat_100g": 14.5,
            "proteins_100g": 5.9,
            "fiber_100g": 1.8,
            "sodium_100g": 0.132,
            "salt_100g": 0.33,
        },
    },
    "7892840222949": {
        "code": "7892840222949",
        "product_name_pt": "Salgadinho de Milho Doritos Queijo Nacho",
        "brands": "Elma Chips",
        "quantity": "140g",
        "categories": "Salgadinhos de milho, Tortilhas",
        "is_beverage": False,
        "nutriscore_grade": "D",
        "nova_group": 4,
        "ingredients_text_pt": "Milho, óleo vegetal de palma, preparado para salgadinho sabor queijo nacho (soro de leite, sal, cloreto de potássio, realçador de sabor glutamato monossódico, corantes artificiais tartrazina e amarelo crepúsculo).",
        "allergens_tags": ["en:milk", "en:soybeans"],
        "additives_tags": ["en:e621", "en:e102", "en:e110"],
        "nutriments": {
            "energy-kcal_100g": 496.0,
            "carbohydrates_100g": 58.0,
            "sugars_100g": 2.4,
            "fat_100g": 26.0,
            "saturated-fat_100g": 11.2,
            "proteins_100g": 6.4,
            "fiber_100g": 4.0,
            "sodium_100g": 0.648,
            "salt_100g": 1.62,
        },
    },
    "7891000053508": {
        "code": "7891000053508",
        "product_name_pt": "Aveia em Flocos Finos Integral",
        "brands": "Quaker",
        "quantity": "165g",
        "categories": "Cereais matinais, Aveia em flocos",
        "is_beverage": False,
        "nutriscore_grade": "A",
        "nova_group": 1,
        "ingredients_text_pt": "Aveia em flocos finos 100% integral.",
        "allergens_tags": ["en:gluten", "en:oats"],
        "additives_tags": [],
        "nutriments": {
            "energy-kcal_100g": 346.0,
            "carbohydrates_100g": 57.0,
            "sugars_100g": 1.0,
            "fat_100g": 7.3,
            "saturated-fat_100g": 1.5,
            "proteins_100g": 14.3,
            "fiber_100g": 9.1,
            "sodium_100g": 0.0,
            "salt_100g": 0.0,
        },
    },
    "7891025101604": {
        "code": "7891025101604",
        "product_name_pt": "Iogurte Natural Integral (2 Ingredientes)",
        "brands": "Danone",
        "quantity": "170g",
        "categories": "Laticínios, Iogurtes naturais",
        "is_beverage": False,
        "nutriscore_grade": "A",
        "nova_group": 1,
        "ingredients_text_pt": "Leite integral e fermento lácteo.",
        "allergens_tags": ["en:milk"],
        "additives_tags": [],
        "nutriments": {
            "energy-kcal_100g": 62.0,
            "carbohydrates_100g": 4.8,
            "sugars_100g": 4.8,
            "fat_100g": 3.2,
            "saturated-fat_100g": 2.1,
            "proteins_100g": 4.1,
            "fiber_100g": 0.0,
            "sodium_100g": 0.052,
            "salt_100g": 0.13,
        },
    },
    "7891910000197": {
        "code": "7891910000197",
        "product_name_pt": "Arroz Branco Longo Fino Tipo 1",
        "brands": "Camil",
        "quantity": "1kg",
        "categories": "Grãos e cereais, Arroz branco",
        "is_beverage": False,
        "nutriscore_grade": "A",
        "nova_group": 1,
        "ingredients_text_pt": "Arroz longo fino polido tipo 1.",
        "allergens_tags": [],
        "additives_tags": [],
        "nutriments": {
            "energy-kcal_100g": 348.0,
            "carbohydrates_100g": 78.0,
            "sugars_100g": 0.2,
            "fat_100g": 0.8,
            "saturated-fat_100g": 0.2,
            "proteins_100g": 7.2,
            "fiber_100g": 1.6,
            "sodium_100g": 0.001,
            "salt_100g": 0.0,
        },
    },
}


def get_fallback_catalog() -> List[ProductAnalysis]:
    return [analyze_raw_product(raw, source="catálogo_local") for raw in FALLBACK_PRODUCTS.values()]


async def fetch_product_by_barcode(barcode: str) -> Optional[ProductAnalysis]:
    clean_code = barcode.strip()
    if clean_code in FALLBACK_PRODUCTS:
        return analyze_raw_product(FALLBACK_PRODUCTS[clean_code], source="openfoodfacts_br")

    url = OFF_PRODUCT_URL.format(barcode=clean_code)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                payload = resp.json()
                if payload.get("status") == 1 and payload.get("product"):
                    product_data = payload["product"]
                    product_data["code"] = clean_code
                    return analyze_raw_product(product_data, source="openfoodfacts_api")
    except Exception:
        pass

    return None


async def search_openfoodfacts(query: str, limit: int = 8) -> List[ProductAnalysis]:
    q_lower = query.strip().lower()
    results: List[ProductAnalysis] = []
    seen_codes = set()

    # Filtra primeiro no catálogo de referência brasileiro para resposta imediata
    for code, raw in FALLBACK_PRODUCTS.items():
        haystack = f"{code} {raw.get('product_name_pt', '')} {raw.get('brands', '')} {raw.get('categories', '')}".lower()
        if not q_lower or q_lower in haystack:
            results.append(analyze_raw_product(raw, source="openfoodfacts_br"))
            seen_codes.add(code)

    if len(results) >= limit or not q_lower:
        return results[:limit]

    params = {
        "search_terms": query.strip(),
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": limit,
    }
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
            resp = await client.get(OFF_SEARCH_URL, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("products", []):
                    code = str(item.get("code") or "").strip()
                    if not code or code in seen_codes:
                        continue
                    if not (item.get("product_name_pt") or item.get("product_name")):
                        continue
                    seen_codes.add(code)
                    results.append(analyze_raw_product(item, source="openfoodfacts_api"))
                    if len(results) >= limit:
                        break
    except Exception:
        pass

    return results
