"""
NutriScan Diet Exporter
Geração de resumos da dieta para WhatsApp, Clipboard e Impressão / PDF.
Em conformidade com regras no-ai-slop: texto direto, natural e objetivo.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def _format_num(val: Any) -> str:
    """Formata número de forma limpa: sem decimais se for inteiro, ou 1 decimal."""
    try:
        f_val = round(float(val), 1)
        if f_val.is_integer():
            return str(int(f_val))
        return f"{f_val:.1f}"
    except (ValueError, TypeError):
        return "0"


def _format_date(date_val: Optional[str]) -> str:
    """Converte 'YYYY-MM-DD' para 'DD/MM/AAAA'. Se nulo, usa a data atual."""
    if not date_val:
        return datetime.now().strftime("%d/%m/%Y")
    clean = str(date_val).strip()
    if "/" in clean:
        return clean
    try:
        dt = datetime.strptime(clean, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return clean


def _normalize_meal(meal_name: str) -> str:
    """Normaliza o nome da refeição para os 4 grupos padrão ou mantém capitalizado."""
    m = str(meal_name or "").strip().lower()
    if "caf" in m or "manh" in m:
        return "Café da manhã"
    if "almoc" in m or "almoç" in m:
        return "Almoço"
    if "lanche" in m:
        return "Lanche"
    if "jant" in m:
        return "Jantar"
    return meal_name.strip() if meal_name else "Lanche"


def _extract_summary_parts(
    diary_data: Dict[str, Any],
    water_data: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, str, Optional[str], List[Tuple[str, List[Tuple[str, str, str]]]]]:
    """Extrai e calcula os componentes do resumo diário."""
    # Data
    d_raw = diary_data.get("date_str") or diary_data.get("date")
    d_fmt = _format_date(d_raw)

    # Consumo e Metas
    consumed_dict = diary_data.get("consumed") if isinstance(diary_data.get("consumed"), dict) else {}
    goals_dict = diary_data.get("goals") if isinstance(diary_data.get("goals"), dict) else {}
    remaining_dict = diary_data.get("remaining") if isinstance(diary_data.get("remaining"), dict) else {}

    consumed_kcal = consumed_dict.get("kcal")
    if consumed_kcal is None:
        consumed_kcal = diary_data.get("consumed_kcal", diary_data.get("kcal", 0.0))

    goal_kcal = goals_dict.get("daily_kcal_limit")
    if goal_kcal is None:
        goal_kcal = diary_data.get("daily_kcal_limit", diary_data.get("goal_kcal", 2000.0))

    diff_kcal = remaining_dict.get("kcal")
    if diff_kcal is None:
        diff_kcal = float(goal_kcal) - float(consumed_kcal)

    c_int = int(round(float(consumed_kcal)))
    g_int = int(round(float(goal_kcal)))
    diff_int = int(round(float(diff_kcal)))
    if diff_int >= 0:
        diff_str = f"{diff_int} kcal restantes"
    else:
        diff_str = f"{abs(diff_int)} kcal acima da meta"

    totals_line = f"🔥 Calorias: {c_int} / {g_int} kcal ({diff_str})"

    # Macros
    prot = consumed_dict.get("proteins_g")
    if prot is None:
        prot = diary_data.get("proteins_g", diary_data.get("protein", 0.0))

    carbs = consumed_dict.get("carbohydrates_g")
    if carbs is None:
        carbs = diary_data.get("carbohydrates_g", diary_data.get("carbs", 0.0))

    fat = consumed_dict.get("fat_g")
    if fat is None:
        fat = diary_data.get("fat_g", 0.0)

    sodium = consumed_dict.get("sodium_mg")
    if sodium is None:
        sodium = diary_data.get("sodium_mg", diary_data.get("sodium", 0.0))

    macros_line = (
        f"💪 Proteína: {_format_num(prot)}g | "
        f"🌾 Carbs: {_format_num(carbs)}g | "
        f"🥑 Gordura: {_format_num(fat)}g | "
        f"🧂 Sódio: {_format_num(sodium)}mg"
    )

    # Hidratação
    water_info = water_data
    if water_info is None and isinstance(diary_data.get("water"), dict):
        water_info = diary_data["water"]

    water_line = None
    if water_info is not None:
        w_consumed = int(round(float(water_info.get("amount_ml", 0))))
        w_goal = int(round(float(water_info.get("goal_ml", 2500))))
        water_line = f"💧 Água: {w_consumed} ml / {w_goal} ml"

    # Refeições agrupadas
    raw_entries = diary_data.get("entries") or diary_data.get("items") or []
    groups: Dict[str, List[Tuple[str, str, str]]] = {
        "Café da manhã": [],
        "Almoço": [],
        "Lanche": [],
        "Jantar": [],
    }
    extra_groups: Dict[str, List[Tuple[str, str, str]]] = {}

    for entry in raw_entries:
        if hasattr(entry, "model_dump"):
            item = entry.model_dump()
        elif hasattr(entry, "__dict__"):
            item = entry.__dict__
        elif isinstance(entry, dict):
            item = entry
        else:
            continue

        raw_meal = item.get("meal_type", "Lanche")
        meal_name = _normalize_meal(raw_meal)
        p_name = str(item.get("product_name") or item.get("name") or "Alimento").strip()
        p_portion = _format_num(item.get("portion_g", 100))
        p_kcal = _format_num(item.get("kcal", 0))

        entry_tuple = (p_name, p_portion, p_kcal)
        if meal_name in groups:
            groups[meal_name].append(entry_tuple)
        else:
            extra_groups.setdefault(meal_name, []).append(entry_tuple)

    ordered_sections: List[Tuple[str, List[Tuple[str, str, str]]]] = []
    standard_order = ["Café da manhã", "Almoço", "Lanche", "Jantar"]

    for m in standard_order:
        if groups[m]:
            ordered_sections.append((m, groups[m]))

    for m, items in extra_groups.items():
        if items:
            ordered_sections.append((m, items))

    return d_fmt, totals_line, macros_line, water_line, ordered_sections


def generate_whatsapp_summary(
    diary_data: Dict[str, Any],
    water_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Gera resumo formatado para WhatsApp com negritos e emojis nativos."""
    d_fmt, totals_line, macros_line, water_line, meals = _extract_summary_parts(diary_data, water_data)

    lines: List[str] = [
        f"🥗 *NutriScan - Resumo da Dieta ({d_fmt})*",
        "",
        totals_line,
        macros_line,
    ]

    if water_line:
        lines.append(water_line)

    if not meals:
        lines.append("")
        lines.append("*Refeições:* Nenhuma refeição registrada.")
    else:
        for meal_name, items in meals:
            lines.append("")
            lines.append(f"*{meal_name}*")
            for name, portion, kcal in items:
                lines.append(f"• {name} ({portion}g) - {kcal} kcal")

    return "\n".join(lines)


def generate_plain_text_summary(
    diary_data: Dict[str, Any],
    water_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Gera texto puro sem asteriscos de markdown para área de transferência ou SMS."""
    d_fmt, totals_line, macros_line, water_line, meals = _extract_summary_parts(diary_data, water_data)

    lines: List[str] = [
        f"🥗 NutriScan - Resumo da Dieta ({d_fmt})",
        "",
        totals_line,
        macros_line,
    ]

    if water_line:
        lines.append(water_line)

    if not meals:
        lines.append("")
        lines.append("Refeições: Nenhuma refeição registrada.")
    else:
        for meal_name, items in meals:
            lines.append("")
            lines.append(f"{meal_name}:")
            for name, portion, kcal in items:
                lines.append(f"• {name} ({portion}g) - {kcal} kcal")

    return "\n".join(lines)
