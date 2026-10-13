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


def generate_diet_report_data(
    diary_data: Dict[str, Any],
    water_data: Optional[Dict[str, Any]] = None,
    profile_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Gera um relatório estruturado completo com KPIs executivos, refeições organizadas
    por grupo padrão, hidratação e metadados de emissão.
    """
    d_raw = diary_data.get("date_str") or diary_data.get("date")
    d_fmt = _format_date(d_raw)

    consumed_dict = diary_data.get("consumed") if isinstance(diary_data.get("consumed"), dict) else {}
    goals_dict = diary_data.get("goals") if isinstance(diary_data.get("goals"), dict) else {}
    remaining_dict = diary_data.get("remaining") if isinstance(diary_data.get("remaining"), dict) else {}

    c_kcal = float(consumed_dict.get("kcal") if consumed_dict.get("kcal") is not None else diary_data.get("consumed_kcal", 0.0))
    g_kcal = float(goals_dict.get("daily_kcal_limit") if goals_dict.get("daily_kcal_limit") is not None else diary_data.get("daily_kcal_limit", 2000.0))
    rem_kcal = float(remaining_dict.get("kcal") if remaining_dict.get("kcal") is not None else (g_kcal - c_kcal))

    prot_c = float(consumed_dict.get("proteins_g") if consumed_dict.get("proteins_g") is not None else diary_data.get("proteins_g", 0.0))
    prot_g = float(goals_dict.get("proteins_limit_g") if goals_dict.get("proteins_limit_g") is not None else diary_data.get("proteins_limit_g", 150.0))

    carb_c = float(consumed_dict.get("carbohydrates_g") if consumed_dict.get("carbohydrates_g") is not None else diary_data.get("carbohydrates_g", 0.0))
    carb_g = float(goals_dict.get("carbs_limit_g") if goals_dict.get("carbs_limit_g") is not None else diary_data.get("carbs_limit_g", 200.0))

    fat_c = float(consumed_dict.get("fat_g") if consumed_dict.get("fat_g") is not None else diary_data.get("fat_g", 0.0))
    fat_g = float(goals_dict.get("fat_limit_g") if goals_dict.get("fat_limit_g") is not None else diary_data.get("fat_limit_g", 65.0))

    sodium_c = float(consumed_dict.get("sodium_mg") if consumed_dict.get("sodium_mg") is not None else diary_data.get("sodium_mg", 0.0))
    sodium_g = float(goals_dict.get("sodium_limit_mg") if goals_dict.get("sodium_limit_mg") is not None else 2000.0)

    # Water
    water_info = water_data
    if water_info is None and isinstance(diary_data.get("water"), dict):
        water_info = diary_data["water"]
    w_consumed = int(round(float(water_info.get("amount_ml", 0)))) if water_info else 0
    w_goal = int(round(float(water_info.get("goal_ml", 2500)))) if water_info else 2500
    w_pct = round((w_consumed / w_goal) * 100.0, 1) if w_goal > 0 else 0.0

    # Patient / Profile info
    prof = profile_data or {}
    patient_name = prof.get("name") or "Usuário NutriScan"
    patient_details = []
    if prof.get("weight_kg"):
        patient_details.append(f"Peso: {prof['weight_kg']} kg")
    if prof.get("height_cm"):
        patient_details.append(f"Altura: {prof['height_cm']} cm")
    if prof.get("age"):
        patient_details.append(f"Idade: {prof['age']} anos")
    if prof.get("goal_type"):
        g_map = {"cutting": "Emagrecimento (Déficit)", "manutencao": "Manutenção", "bulking": "Hipertrofia (Superávit)"}
        patient_details.append(f"Foco: {g_map.get(prof['goal_type'], prof['goal_type'].capitalize())}")

    # Meals
    standard_order = ["Café da manhã", "Almoço", "Lanche", "Jantar"]
    grouped_meals: Dict[str, List[Dict[str, Any]]] = {m: [] for m in standard_order}
    extra_meals: Dict[str, List[Dict[str, Any]]] = {}

    raw_entries = diary_data.get("entries") or diary_data.get("items") or []
    for entry in raw_entries:
        if hasattr(entry, "model_dump"):
            item = entry.model_dump()
        elif hasattr(entry, "__dict__"):
            item = entry.__dict__
        elif isinstance(entry, dict):
            item = entry
        else:
            continue

        m_name = _normalize_meal(item.get("meal_type", "Lanche"))
        cleaned_item = {
            "name": str(item.get("product_name") or item.get("name") or "Alimento").strip(),
            "portion_g": float(item.get("portion_g") or 0.0),
            "kcal": float(item.get("kcal") or 0.0),
            "carbohydrates_g": float(item.get("carbohydrates_g") or 0.0),
            "proteins_g": float(item.get("proteins_g") or 0.0),
            "fat_g": float(item.get("fat_g") or 0.0),
        }
        if m_name in grouped_meals:
            grouped_meals[m_name].append(cleaned_item)
        else:
            extra_meals.setdefault(m_name, []).append(cleaned_item)

    meals_output = []
    for m in standard_order:
        items = grouped_meals[m]
        sub_kcal = sum(it["kcal"] for it in items)
        sub_prot = sum(it["proteins_g"] for it in items)
        sub_carb = sum(it["carbohydrates_g"] for it in items)
        sub_fat = sum(it["fat_g"] for it in items)
        meals_output.append({
            "meal_name": m,
            "items": items,
            "totals": {
                "kcal": round(sub_kcal, 1),
                "proteins_g": round(sub_prot, 1),
                "carbohydrates_g": round(sub_carb, 1),
                "fat_g": round(sub_fat, 1),
            },
        })

    for m, items in extra_meals.items():
        if items:
            sub_kcal = sum(it["kcal"] for it in items)
            sub_prot = sum(it["proteins_g"] for it in items)
            sub_carb = sum(it["carbohydrates_g"] for it in items)
            sub_fat = sum(it["fat_g"] for it in items)
            meals_output.append({
                "meal_name": m,
                "items": items,
                "totals": {
                    "kcal": round(sub_kcal, 1),
                    "proteins_g": round(sub_prot, 1),
                    "carbohydrates_g": round(sub_carb, 1),
                    "fat_g": round(sub_fat, 1),
                },
            })

    issued_at = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")

    return {
        "title": "Relatório Diário de Dieta e Nutrição",
        "date_formatted": d_fmt,
        "date_iso": str(d_raw) if d_raw else datetime.now().strftime("%Y-%m-%d"),
        "issued_at": issued_at,
        "patient": {
            "name": patient_name,
            "details_line": " • ".join(patient_details) if patient_details else "Perfil padrão configurado",
        },
        "kpis": {
            "calories": {
                "consumed": int(round(c_kcal)),
                "goal": int(round(g_kcal)),
                "remaining": int(round(rem_kcal)),
                "pct": round((c_kcal / g_kcal) * 100.0, 1) if g_kcal > 0 else 0.0,
                "status": "Dentro da meta" if rem_kcal >= 0 else f"{abs(int(round(rem_kcal)))} kcal acima da meta",
            },
            "proteins": {
                "consumed_g": round(prot_c, 1),
                "goal_g": round(prot_g, 1),
                "pct": round((prot_c / prot_g) * 100.0, 1) if prot_g > 0 else 0.0,
            },
            "carbohydrates": {
                "consumed_g": round(carb_c, 1),
                "goal_g": round(carb_g, 1),
                "pct": round((carb_c / carb_g) * 100.0, 1) if carb_g > 0 else 0.0,
            },
            "fat": {
                "consumed_g": round(fat_c, 1),
                "goal_g": round(fat_g, 1),
                "pct": round((fat_c / fat_g) * 100.0, 1) if fat_g > 0 else 0.0,
            },
            "sodium": {
                "consumed_mg": round(sodium_c, 1),
                "goal_mg": round(sodium_g, 1),
            },
            "hydration": {
                "consumed_ml": w_consumed,
                "goal_ml": w_goal,
                "pct": w_pct,
            },
        },
        "meals": meals_output,
        "disclaimer": (
            "Aviso: Este relatório é um documento informativo gerado pelo aplicativo NutriScan com base nos registros do usuário. "
            "Não substitui consulta, avaliação clínica individual ou prescrição de nutricionista ou profissional médico habilitado."
        ),
    }


def generate_diet_report_html(
    diary_data: Dict[str, Any],
    water_data: Optional[Dict[str, Any]] = None,
    profile_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Gera página HTML standalone profissional e minimalista pronta para impressão ou exportação em PDF.
    Possui cabeçalho executivo, grade de KPIs limpa, tabelas de refeições e rodapé de responsabilidade.
    """
    report = generate_diet_report_data(diary_data, water_data, profile_data)
    p = report["patient"]
    k = report["kpis"]

    # Constrói linhas das tabelas
    meals_html = []
    has_any_items = False
    for meal in report["meals"]:
        items = meal["items"]
        if not items:
            continue
        has_any_items = True
        m_name = meal["meal_name"]
        m_tot = meal["totals"]

        rows = []
        for it in items:
            p_g = _format_num(it["portion_g"])
            kc = _format_num(it["kcal"])
            cb = _format_num(it["carbohydrates_g"])
            pr = _format_num(it["proteins_g"])
            ft = _format_num(it["fat_g"])
            rows.append(f"""
                <tr>
                    <td style="font-weight: 500;">{it['name']}</td>
                    <td style="text-align: right; color: #4b5563;">{p_g}g</td>
                    <td style="text-align: right; font-weight: 600;">{kc} kcal</td>
                    <td style="text-align: right; color: #4b5563;">{cb}g</td>
                    <td style="text-align: right; color: #047857; font-weight: 600;">{pr}g</td>
                    <td style="text-align: right; color: #4b5563;">{ft}g</td>
                </tr>
            """)

        meals_html.append(f"""
        <div class="meal-section">
            <div class="meal-header">
                <h3 class="meal-title">{m_name}</h3>
                <span class="meal-subtotal">{_format_num(m_tot['kcal'])} kcal • P: {_format_num(m_tot['proteins_g'])}g • C: {_format_num(m_tot['carbohydrates_g'])}g • G: {_format_num(m_tot['fat_g'])}g</span>
            </div>
            <table class="report-table">
                <thead>
                    <tr>
                        <th style="width: 45%;">Alimento</th>
                        <th style="width: 11%; text-align: right;">Porção</th>
                        <th style="width: 14%; text-align: right;">Calorias</th>
                        <th style="width: 10%; text-align: right;">Carb</th>
                        <th style="width: 10%; text-align: right;">Prot</th>
                        <th style="width: 10%; text-align: right;">Gord</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """)

    if not has_any_items:
        meals_html.append("""
        <div class="empty-state">
            <p>Nenhuma refeição registrada para esta data.</p>
        </div>
        """)

    meals_markup = "\n".join(meals_html)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NutriScan - Relatório da Dieta ({report['date_formatted']})</title>
    <style>
        @page {{
            size: A4 portrait;
            margin: 15mm;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: #111827;
            background: #ffffff;
            font-size: 13px;
            line-height: 1.5;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        .report-page {{
            max-width: 800px;
            margin: 0 auto;
            padding: 24px;
        }}
        /* Header */
        .report-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 16px;
            margin-bottom: 20px;
        }}
        .brand-wrap {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .brand-badge {{
            width: 40px;
            height: 40px;
            background: #059669;
            color: #ffffff;
            font-weight: 800;
            font-size: 16px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            letter-spacing: -0.5px;
        }}
        .brand-title {{
            font-size: 20px;
            font-weight: 700;
            color: #111827;
            letter-spacing: -0.3px;
        }}
        .brand-sub {{
            font-size: 11px;
            color: #6b7280;
        }}
        .header-meta {{
            text-align: right;
        }}
        .report-date {{
            font-size: 16px;
            font-weight: 700;
            color: #059669;
        }}
        .patient-name {{
            font-size: 12px;
            font-weight: 600;
            color: #1f2937;
            margin-top: 2px;
        }}
        .patient-details {{
            font-size: 11px;
            color: #6b7280;
        }}

        /* Executive KPI Strip */
        .kpi-section-title {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #4b5563;
            margin-bottom: 8px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 10px 12px;
        }}
        .kpi-label {{
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            color: #6b7280;
            margin-bottom: 4px;
        }}
        .kpi-value {{
            font-size: 16px;
            font-weight: 700;
            color: #111827;
        }}
        .kpi-sub {{
            font-size: 11px;
            color: #6b7280;
            margin-top: 2px;
        }}
        .kpi-progress {{
            height: 4px;
            background: #e5e7eb;
            border-radius: 2px;
            margin-top: 6px;
            overflow: hidden;
        }}
        .kpi-fill {{
            height: 100%;
            border-radius: 2px;
        }}
        .fill-emerald {{ background: #059669; }}
        .fill-blue {{ background: #2563eb; }}
        .fill-amber {{ background: #d97706; }}
        .fill-rose {{ background: #e11d48; }}
        .fill-cyan {{ background: #0891b2; }}

        /* Meal sections */
        .meal-section {{
            margin-bottom: 20px;
            break-inside: avoid;
        }}
        .meal-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 6px;
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 4px;
        }}
        .meal-title {{
            font-size: 13px;
            font-weight: 700;
            color: #111827;
        }}
        .meal-subtotal {{
            font-size: 11px;
            color: #6b7280;
            font-weight: 500;
        }}
        .report-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}
        .report-table th {{
            background: #f9fafb;
            color: #4b5563;
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            padding: 6px 8px;
            border: 1px solid #e5e7eb;
        }}
        .report-table td {{
            padding: 6px 8px;
            border: 1px solid #e5e7eb;
            color: #1f2937;
        }}
        .report-table tbody tr:nth-child(even) {{
            background: #fbfcfd;
        }}
        .empty-state {{
            padding: 24px;
            text-align: center;
            background: #f9fafb;
            border: 1px dashed #d1d5db;
            border-radius: 8px;
            color: #6b7280;
            margin-bottom: 24px;
        }}

        /* Footer */
        .report-footer {{
            margin-top: 30px;
            padding-top: 14px;
            border-top: 1px solid #e5e7eb;
            font-size: 10px;
            color: #6b7280;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            break-inside: avoid;
        }}
        .disclaimer-text {{
            max-width: 75%;
            line-height: 1.4;
        }}
        .issue-text {{
            text-align: right;
            white-space: nowrap;
        }}

        /* Print actions bar (screen only) */
        .screen-actions {{
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .btn-action {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: #059669;
            color: #ffffff;
            border: none;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
        }}
        .btn-action:hover {{
            background: #047857;
        }}
        .btn-action.secondary {{
            background: #f3f4f6;
            color: #1f2937;
            border: 1px solid #d1d5db;
        }}
        .btn-action.secondary:hover {{
            background: #e5e7eb;
        }}

        @media print {{
            .screen-actions {{
                display: none !important;
            }}
            .report-page {{
                padding: 0 !important;
                max-width: 100% !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="report-page">
        <div class="screen-actions">
            <button class="btn-action" onclick="window.print()">🖨️ Imprimir / Salvar PDF</button>
            <a href="/" class="btn-action secondary">Voltar ao App</a>
        </div>

        <header class="report-header">
            <div class="brand-wrap">
                <div class="brand-badge">NS</div>
                <div>
                    <h1 class="brand-title">NutriScan</h1>
                    <p class="brand-sub">Controle Nutricional e Dieta Diária</p>
                </div>
            </div>
            <div class="header-meta">
                <div class="report-date">{report['date_formatted']}</div>
                <div class="patient-name">{p['name']}</div>
                <div class="patient-details">{p['details_line']}</div>
            </div>
        </header>

        <section>
            <div class="kpi-section-title">Resumo Executivo dos KPIs Diários</div>
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">Calorias</div>
                    <div class="kpi-value">{k['calories']['consumed']} <span style="font-size: 11px; font-weight: normal; color: #6b7280;">/ {k['calories']['goal']} kcal</span></div>
                    <div class="kpi-sub">{k['calories']['status']}</div>
                    <div class="kpi-progress">
                        <div class="kpi-fill fill-emerald" style="width: {min(100.0, k['calories']['pct'])}%;"></div>
                    </div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-label">Proteínas</div>
                    <div class="kpi-value">{k['proteins']['consumed_g']}g <span style="font-size: 11px; font-weight: normal; color: #6b7280;">/ {k['proteins']['goal_g']}g</span></div>
                    <div class="kpi-sub">{k['proteins']['pct']}% da meta</div>
                    <div class="kpi-progress">
                        <div class="kpi-fill fill-blue" style="width: {min(100.0, k['proteins']['pct'])}%;"></div>
                    </div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-label">Carboidratos</div>
                    <div class="kpi-value">{k['carbohydrates']['consumed_g']}g <span style="font-size: 11px; font-weight: normal; color: #6b7280;">/ {k['carbohydrates']['goal_g']}g</span></div>
                    <div class="kpi-sub">{k['carbohydrates']['pct']}% da meta</div>
                    <div class="kpi-progress">
                        <div class="kpi-fill fill-amber" style="width: {min(100.0, k['carbohydrates']['pct'])}%;"></div>
                    </div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-label">Gorduras Totais</div>
                    <div class="kpi-value">{k['fat']['consumed_g']}g <span style="font-size: 11px; font-weight: normal; color: #6b7280;">/ {k['fat']['goal_g']}g</span></div>
                    <div class="kpi-sub">{k['fat']['pct']}% da meta</div>
                    <div class="kpi-progress">
                        <div class="kpi-fill fill-rose" style="width: {min(100.0, k['fat']['pct'])}%;"></div>
                    </div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-label">Hidratação</div>
                    <div class="kpi-value">{k['hydration']['consumed_ml']} ml <span style="font-size: 11px; font-weight: normal; color: #6b7280;">/ {k['hydration']['goal_ml']} ml</span></div>
                    <div class="kpi-sub">{k['hydration']['pct']}% da meta</div>
                    <div class="kpi-progress">
                        <div class="kpi-fill fill-cyan" style="width: {min(100.0, k['hydration']['pct'])}%;"></div>
                    </div>
                </div>
            </div>
        </section>

        <section>
            <div class="kpi-section-title">Refeições do Dia</div>
            {meals_markup}
        </section>

        <footer class="report-footer">
            <div class="disclaimer-text">{report['disclaimer']}</div>
            <div class="issue-text">
                <div>Emissão: {report['issued_at']}</div>
                <div>NutriScan v1.0 • Padrão ANVISA</div>
            </div>
        </footer>
    </div>
</body>
</html>"""
    return html

