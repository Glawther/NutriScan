import re
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from app.models.schemas import (
    AdditiveItem,
    AnvisaAlerts,
    ComparisonResponse,
    NutrientDelta,
    NutritionPer100g,
    ProductAnalysis,
)

NOVA_LABELS: Dict[int, str] = {
    1: "In natura ou minimamente processado",
    2: "Ingrediente culinário processado",
    3: "Alimento processado",
    4: "Ultraprocessado",
}

ADDITIVE_CATALOG: Dict[str, Tuple[str, str]] = {
    "E102": ("Tartrazina", "Corante artificial"),
    "E110": ("Amarelo crepúsculo", "Corante artificial"),
    "E129": ("Vermelho allura AC", "Corante artificial"),
    "E150A": ("Caramelo I simples", "Corante"),
    "E150C": ("Caramelo III amônia", "Corante"),
    "E150D": ("Corante caramelo IV", "Corante sulfito-amônia"),
    "E200": ("Ácido sórbico", "Conservante"),
    "E202": ("Sorbato de potássio", "Conservante"),
    "E211": ("Benzoato de sódio", "Conservante"),
    "E220": ("Dióxido de enxofre", "Conservante / antioxidante"),
    "E250": ("Nitrito de sódio", "Conservante"),
    "E290": ("Dióxido de carbono", "Gaseificante"),
    "E300": ("Ácido ascórbico", "Antioxidante"),
    "E322": ("Lecitina de soja", "Emulsificante"),
    "E330": ("Ácido cítrico", "Acidulante"),
    "E331": ("Citrato de sódio", "Regulador de acidez"),
    "E338": ("Ácido fosfórico", "Acidulante"),
    "E407": ("Carragena", "Espessante"),
    "E412": ("Goma guar", "Espessante"),
    "E414": ("Goma arábica", "Estabilizante"),
    "E415": ("Goma xantana", "Espessante"),
    "E471": ("Mono e diglicerídeos de ácidos graxos", "Emulsificante"),
    "E476": ("Polirricinoleato de poliglicerol (PGPR)", "Emulsificante"),
    "E500": ("Bicarbonato de sódio", "Fermento químico"),
    "E503": ("Bicarbonato de amônio", "Fermento químico"),
    "E621": ("Glutamato monossódico", "Realçador de sabor"),
    "E950": ("Acessulfame de potássio", "Edulcorante artificial"),
    "E951": ("Aspartame", "Edulcorante artificial"),
    "E952": ("Ciclamato de sódio", "Edulcorante artificial"),
    "E954": ("Sacarina sódica", "Edulcorante artificial"),
    "E955": ("Sucralose", "Edulcorante artificial"),
}

ALLERGEN_TRANSLATIONS: Dict[str, str] = {
    "milk": "Leite e derivados",
    "leite": "Leite e derivados",
    "soybeans": "Soja",
    "soja": "Soja",
    "nuts": "Castanhas / nozes / avelãs",
    "hazelnuts": "Avelãs",
    "avela": "Avelãs",
    "gluten": "Glúten",
    "wheat": "Trigo",
    "trigo": "Trigo",
    "oats": "Aveia",
    "aveia": "Aveia",
    "peanuts": "Amendoim",
    "eggs": "Ovos",
}


def get_nova_label(nova_group: int) -> str:
    group = int(nova_group) if nova_group in (1, 2, 3, 4) else 3
    return NOVA_LABELS[group]


def evaluate_anvisa_rdc429(nutrition: NutritionPer100g, is_beverage: bool = False) -> AnvisaAlerts:
    """
    Avalia os limites de rotulagem nutricional frontal estabelecidos pela
    ANVISA RDC 429/2020 e IN 75/2020.
    - Sólidos/semissólidos (por 100g): açúcares >= 15g, gord. saturada >= 6g, sódio >= 600mg
    - Líquidos (por 100ml): açúcares >= 7.5g, gord. saturada >= 3g, sódio >= 300mg
    """
    sugar_limit = 7.5 if is_beverage else 15.0
    sat_fat_limit = 3.0 if is_beverage else 6.0
    sodium_limit = 300.0 if is_beverage else 600.0

    high_sugar = nutrition.sugars_g >= sugar_limit
    high_sat_fat = nutrition.saturated_fat_g >= sat_fat_limit
    high_sodium = nutrition.sodium_mg >= sodium_limit

    warnings: List[str] = []
    if high_sugar:
        warnings.append("ALTO EM AÇÚCAR")
    if high_sat_fat:
        warnings.append("ALTO EM GORDURA SATURADA")
    if high_sodium:
        warnings.append("ALTO EM SÓDIO")

    return AnvisaAlerts(
        is_beverage=is_beverage,
        high_sugar=high_sugar,
        high_saturated_fat=high_sat_fat,
        high_sodium=high_sodium,
        warnings_count=len(warnings),
        warnings_list=warnings,
        thresholds_used={
            "sugars_g": sugar_limit,
            "saturated_fat_g": sat_fat_limit,
            "sodium_mg": sodium_limit,
            "reference_unit": "100ml" if is_beverage else "100g",
        },
    )


def normalize_additive_code(raw_tag: str) -> str:
    cleaned = raw_tag.strip().lower()
    if ":" in cleaned:
        cleaned = cleaned.split(":", 1)[1]
    cleaned = cleaned.upper()
    match = re.match(r"^(E\d{3,4}[A-D]?)", cleaned)
    if match:
        return match.group(1)
    return cleaned


def parse_additives(raw_tags: List[str]) -> List[AdditiveItem]:
    seen = set()
    items: List[AdditiveItem] = []
    for raw in raw_tags or []:
        code = normalize_additive_code(str(raw))
        if not code or not code.startswith("E") or code in seen:
            continue
        seen.add(code)
        base_code = re.sub(r"[I]+$", "", code)
        if code in ADDITIVE_CATALOG:
            name, func = ADDITIVE_CATALOG[code]
        elif base_code in ADDITIVE_CATALOG:
            name, func = ADDITIVE_CATALOG[base_code]
            code = base_code
        else:
            name, func = f"Aditivo alimentar {code}", "Aditivo tecnológico"

        # Format display code with lowercase suffix when applicable (e.g. E150d)
        display_code = code[:-1] + code[-1].lower() if code[-1].isalpha() else code
        items.append(AdditiveItem(code=display_code, name=name, function=func))
    return items


def parse_allergens(raw_tags: List[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for tag in raw_tags or []:
        clean = str(tag).lower().split(":")[-1].strip()
        if not clean:
            continue
        label = ALLERGEN_TRANSLATIONS.get(clean, clean.capitalize())
        if label not in seen:
            seen.add(label)
            result.append(label)
    return result


def normalize_nutriscore(raw_grade: str, nutrition: NutritionPer100g, is_beverage: bool) -> str:
    if raw_grade and str(raw_grade).strip().upper() in ("A", "B", "C", "D", "E"):
        return str(raw_grade).strip().upper()

    # Cálculo simplificado quando o registro não traz a letra calculada
    points = 0
    if nutrition.energy_kcal > 350:
        points += 4
    elif nutrition.energy_kcal > 180:
        points += 2
    if nutrition.sugars_g >= (7.5 if is_beverage else 15.0):
        points += 4
    elif nutrition.sugars_g >= 5.0:
        points += 2
    if nutrition.saturated_fat_g >= (3.0 if is_beverage else 6.0):
        points += 4
    elif nutrition.saturated_fat_g >= 2.0:
        points += 2
    if nutrition.sodium_mg >= (300.0 if is_beverage else 600.0):
        points += 4
    if nutrition.fiber_g >= 3.5:
        points -= 2
    if nutrition.proteins_g >= 8.0:
        points -= 2

    if is_beverage and nutrition.sugars_g > 9.0:
        return "E"
    if points <= 0:
        return "A"
    if points <= 3:
        return "B"
    if points <= 7:
        return "C"
    if points <= 11:
        return "D"
    return "E"


def detect_is_beverage(raw_product: dict) -> bool:
    if "is_beverage" in raw_product:
        return bool(raw_product["is_beverage"])
    quantity = str(raw_product.get("quantity", "")).lower()
    categories = str(raw_product.get("categories", "")).lower()
    name = str(raw_product.get("product_name", "")).lower()
    beverage_keywords = ("bebida", "refrigerante", "suco", "beverage", "soda", "drink", "néctar", "agua", "água")
    if any(k in categories or k in name for k in beverage_keywords):
        return True
    if ("ml" in quantity or "l" in quantity) and "g" not in quantity:
        return True
    return False


def analyze_raw_product(raw_product: dict, source: str = "openfoodfacts") -> ProductAnalysis:
    nutriments = raw_product.get("nutriments", {}) or {}

    energy_kcal = float(
        nutriments.get("energy-kcal_100g")
        or nutriments.get("energy-kcal")
        or (float(nutriments.get("energy_100g", 0.0) or 0.0) / 4.184)
    )
    carbohydrates_g = float(nutriments.get("carbohydrates_100g", 0.0) or 0.0)
    sugars_g = float(nutriments.get("sugars_100g", 0.0) or 0.0)
    fat_g = float(nutriments.get("fat_100g", 0.0) or 0.0)
    saturated_fat_g = float(nutriments.get("saturated-fat_100g", 0.0) or 0.0)
    proteins_g = float(nutriments.get("proteins_100g", 0.0) or 0.0)
    fiber_g = float(nutriments.get("fiber_100g", 0.0) or 0.0)

    # Open Food Facts armazena sodium_100g em gramas; convertemos para mg se < 20
    raw_sodium = nutriments.get("sodium_100g")
    raw_salt = float(nutriments.get("salt_100g", 0.0) or 0.0)
    if raw_sodium is not None:
        val_sod = float(raw_sodium or 0.0)
        sodium_mg = val_sod * 1000.0 if val_sod < 15.0 else val_sod
    elif raw_salt > 0:
        sodium_mg = (raw_salt / 2.5) * 1000.0
    else:
        sodium_mg = 0.0

    salt_g = raw_salt if raw_salt > 0 else round((sodium_mg / 1000.0) * 2.5, 2)

    nutrition = NutritionPer100g(
        energy_kcal=round(energy_kcal, 1),
        carbohydrates_g=round(carbohydrates_g, 1),
        sugars_g=round(sugars_g, 1),
        fat_g=round(fat_g, 1),
        saturated_fat_g=round(saturated_fat_g, 1),
        proteins_g=round(proteins_g, 1),
        fiber_g=round(fiber_g, 1),
        sodium_mg=round(sodium_mg, 1),
        salt_g=round(salt_g, 2),
    )

    is_beverage = detect_is_beverage(raw_product)
    anvisa = evaluate_anvisa_rdc429(nutrition, is_beverage=is_beverage)
    additives = parse_additives(raw_product.get("additives_tags", []))
    allergens = parse_allergens(raw_product.get("allergens_tags", []))

    raw_nova = raw_product.get("nova_group") or nutriments.get("nova-group")
    if raw_nova in (1, 2, 3, 4, "1", "2", "3", "4"):
        nova_group = int(raw_nova)
    else:
        nova_group = 4 if len(additives) >= 2 else (3 if anvisa.warnings_count > 0 else 1)

    nova_label = get_nova_label(nova_group)
    nutriscore_grade = normalize_nutriscore(
        raw_product.get("nutriscore_grade", ""),
        nutrition,
        is_beverage=is_beverage,
    )

    product_name = (
        raw_product.get("product_name_pt")
        or raw_product.get("product_name")
        or "Produto sem nome cadastrado"
    ).strip()
    brand = (raw_product.get("brands") or "Marca não informada").split(",")[0].strip()
    quantity = (raw_product.get("quantity") or ("350ml" if is_beverage else "100g")).strip()
    categories = (raw_product.get("categories") or "Alimentos e bebidas").strip()
    ingredients_text = (
        raw_product.get("ingredients_text_pt")
        or raw_product.get("ingredients_text")
        or "Lista de ingredientes não informada na base."
    ).strip()

    return ProductAnalysis(
        barcode=str(raw_product.get("code") or raw_product.get("barcode") or ""),
        product_name=product_name,
        brand=brand,
        quantity=quantity,
        categories=categories,
        is_beverage=is_beverage,
        nutriscore_grade=nutriscore_grade,
        nova_group=nova_group,
        nova_label=nova_label,
        ingredients_text=ingredients_text,
        allergens=allergens,
        additives=additives,
        nutrition=nutrition,
        anvisa=anvisa,
        source=source,
        scanned_at=datetime.now(timezone.utc).isoformat(),
    )


def compare_products(prod_a: ProductAnalysis, prod_b: ProductAnalysis) -> ComparisonResponse:
    specs = [
        ("energy_kcal", "Valor energético", "kcal", prod_a.nutrition.energy_kcal, prod_b.nutrition.energy_kcal, True),
        ("sugars_g", "Açúcares totais", "g", prod_a.nutrition.sugars_g, prod_b.nutrition.sugars_g, True),
        (
            "saturated_fat_g",
            "Gorduras saturadas",
            "g",
            prod_a.nutrition.saturated_fat_g,
            prod_b.nutrition.saturated_fat_g,
            True,
        ),
        ("sodium_mg", "Sódio", "mg", prod_a.nutrition.sodium_mg, prod_b.nutrition.sodium_mg, True),
        ("proteins_g", "Proteínas", "g", prod_a.nutrition.proteins_g, prod_b.nutrition.proteins_g, False),
        ("fiber_g", "Fibras alimentares", "g", prod_a.nutrition.fiber_g, prod_b.nutrition.fiber_g, False),
        ("additives_count", "Aditivos identificados", "un", float(len(prod_a.additives)), float(len(prod_b.additives)), True),
    ]

    deltas: List[NutrientDelta] = []
    for metric, label, unit, val_a, val_b, lower_is_better in specs:
        diff = round(val_a - val_b, 2)
        if abs(diff) < 0.01:
            fav = None
        elif lower_is_better:
            fav = prod_a.barcode if val_a < val_b else prod_b.barcode
        else:
            fav = prod_a.barcode if val_a > val_b else prod_b.barcode

        deltas.append(
            NutrientDelta(
                metric=metric,
                label=label,
                unit=unit,
                value_a=val_a,
                value_b=val_b,
                diff=diff,
                lower_is_better=lower_is_better,
                favorable_barcode=fav,
            )
        )

    notes: List[str] = []
    if prod_a.anvisa.warnings_count != prod_b.anvisa.warnings_count:
        less_warn = prod_a if prod_a.anvisa.warnings_count < prod_b.anvisa.warnings_count else prod_b
        more_warn = prod_b if less_warn == prod_a else prod_a
        notes.append(
            f"{less_warn.product_name} tem {less_warn.anvisa.warnings_count} alerta(s) frontal(is) ANVISA, "
            f"enquanto {more_warn.product_name} apresenta {more_warn.anvisa.warnings_count}."
        )
    else:
        notes.append(
            f"Ambos os produtos possuem {prod_a.anvisa.warnings_count} alerta(s) frontal(is) pela regra da ANVISA."
        )

    sugar_diff = abs(round(prod_a.nutrition.sugars_g - prod_b.nutrition.sugars_g, 1))
    if sugar_diff > 0:
        higher_sugar = prod_a if prod_a.nutrition.sugars_g > prod_b.nutrition.sugars_g else prod_b
        notes.append(f"{higher_sugar.product_name} contém +{sugar_diff}g de açúcares por 100g/ml na comparação direta.")

    if len(prod_a.additives) != len(prod_b.additives):
        more_add = prod_a if len(prod_a.additives) > len(prod_b.additives) else prod_b
        less_add = prod_b if more_add == prod_a else prod_a
        notes.append(
            f"{more_add.product_name} lista {len(more_add.additives)} aditivo(s) químico(s) contra "
            f"{len(less_add.additives)} em {less_add.product_name}."
        )

    return ComparisonResponse(
        product_a=prod_a,
        product_b=prod_b,
        deltas=deltas,
        summary_notes=notes,
    )
