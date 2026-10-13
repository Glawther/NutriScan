import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.config import DATABASE_PATH
from app.models.schemas import (
    DailyTrendItem,
    DietDiaryCreateRequest,
    DietDiaryEntry,
    DietGoals,
    DietGoalsUpdateRequest,
    DietTodaySummary,
    ProductAnalysis,
    WaterLogCreate,
    WaterLogResponse,
    WeeklyTrendsResponse,
)
from app.services.openfoodfacts import get_fallback_catalog

_db_lock = threading.Lock()


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _get_connection(db_path: str = DATABASE_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DATABASE_PATH) -> None:
    with _db_lock:
        conn = _get_connection(db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS products_history (
                    barcode TEXT PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    nutriscore_grade TEXT NOT NULL,
                    nova_group INTEGER NOT NULL,
                    anvisa_warnings_count INTEGER NOT NULL,
                    energy_kcal REAL NOT NULL,
                    sugars_g REAL NOT NULL,
                    saturated_fat_g REAL NOT NULL,
                    sodium_mg REAL NOT NULL,
                    payload_json TEXT NOT NULL,
                    scanned_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS diet_goals (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    goal_type TEXT NOT NULL DEFAULT 'cutting',
                    weight_kg REAL NOT NULL DEFAULT 78.0,
                    height_cm REAL NOT NULL DEFAULT 176.0,
                    age INTEGER NOT NULL DEFAULT 29,
                    activity_level TEXT NOT NULL DEFAULT 'moderado',
                    daily_kcal_limit REAL NOT NULL DEFAULT 2000.0,
                    carbs_limit_g REAL NOT NULL DEFAULT 200.0,
                    proteins_limit_g REAL NOT NULL DEFAULT 150.0,
                    fat_limit_g REAL NOT NULL DEFAULT 65.0,
                    sodium_limit_mg REAL NOT NULL DEFAULT 2000.0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS diet_diary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_str TEXT NOT NULL,
                    meal_type TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    portion_g REAL NOT NULL,
                    kcal REAL NOT NULL,
                    carbohydrates_g REAL NOT NULL,
                    proteins_g REAL NOT NULL,
                    fat_g REAL NOT NULL,
                    fiber_g REAL NOT NULL,
                    sodium_mg REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS diet_water (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_str TEXT,
                    amount_ml INTEGER,
                    created_at TEXT
                )
                """
            )
            row = conn.execute("SELECT id FROM diet_goals WHERE id = 1").fetchone()
            if not row:
                conn.execute(
                    """
                    INSERT INTO diet_goals (
                        id, goal_type, weight_kg, height_cm, age, activity_level,
                        daily_kcal_limit, carbs_limit_g, proteins_limit_g, fat_limit_g, sodium_limit_mg
                    ) VALUES (1, 'cutting', 78.0, 176.0, 29, 'moderado', 2000.0, 200.0, 150.0, 65.0, 2000.0)
                    """
                )
            conn.commit()
        finally:
            conn.close()


def save_product(product: ProductAnalysis, db_path: str = DATABASE_PATH) -> None:
    now_iso = product.scanned_at or datetime.now(timezone.utc).isoformat()
    product.scanned_at = now_iso
    payload_str = json.dumps(product.model_dump(), ensure_ascii=False)

    with _db_lock:
        conn = _get_connection(db_path)
        try:
            conn.execute(
                """
                INSERT INTO products_history (
                    barcode, product_name, brand, nutriscore_grade, nova_group,
                    anvisa_warnings_count, energy_kcal, sugars_g, saturated_fat_g,
                    sodium_mg, payload_json, scanned_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(barcode) DO UPDATE SET
                    product_name = excluded.product_name,
                    brand = excluded.brand,
                    nutriscore_grade = excluded.nutriscore_grade,
                    nova_group = excluded.nova_group,
                    anvisa_warnings_count = excluded.anvisa_warnings_count,
                    energy_kcal = excluded.energy_kcal,
                    sugars_g = excluded.sugars_g,
                    saturated_fat_g = excluded.saturated_fat_g,
                    sodium_mg = excluded.sodium_mg,
                    payload_json = excluded.payload_json,
                    scanned_at = excluded.scanned_at
                """,
                (
                    product.barcode,
                    product.product_name,
                    product.brand,
                    product.nutriscore_grade,
                    product.nova_group,
                    product.anvisa.warnings_count,
                    product.nutrition.energy_kcal,
                    product.nutrition.sugars_g,
                    product.nutrition.saturated_fat_g,
                    product.nutrition.sodium_mg,
                    payload_str,
                    now_iso,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def get_cached_product(barcode: str, db_path: str = DATABASE_PATH) -> Optional[ProductAnalysis]:
    with _db_lock:
        conn = _get_connection(db_path)
        try:
            row = conn.execute(
                "SELECT payload_json FROM products_history WHERE barcode = ?",
                (barcode.strip(),),
            ).fetchone()
            if not row:
                return None
            return ProductAnalysis(**json.loads(row["payload_json"]))
        finally:
            conn.close()


def list_history(limit: int = 50, db_path: str = DATABASE_PATH) -> List[ProductAnalysis]:
    with _db_lock:
        conn = _get_connection(db_path)
        try:
            rows = conn.execute(
                "SELECT payload_json FROM products_history ORDER BY scanned_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [ProductAnalysis(**json.loads(r["payload_json"])) for r in rows]
        finally:
            conn.close()


def get_metrics(db_path: str = DATABASE_PATH) -> Dict[str, object]:
    with _db_lock:
        conn = _get_connection(db_path)
        try:
            total = conn.execute("SELECT COUNT(*) AS c FROM products_history").fetchone()["c"]
            ultraprocessed = conn.execute(
                "SELECT COUNT(*) AS c FROM products_history WHERE nova_group = 4"
            ).fetchone()["c"]
            with_anvisa_alerts = conn.execute(
                "SELECT COUNT(*) AS c FROM products_history WHERE anvisa_warnings_count > 0"
            ).fetchone()["c"]
            in_natura = conn.execute(
                "SELECT COUNT(*) AS c FROM products_history WHERE nova_group = 1"
            ).fetchone()["c"]
            grade_rows = conn.execute(
                "SELECT nutriscore_grade, COUNT(*) AS c FROM products_history GROUP BY nutriscore_grade"
            ).fetchall()
            grades = {r["nutriscore_grade"]: r["c"] for r in grade_rows}
            return {
                "total_products": total,
                "ultraprocessed_nova4": ultraprocessed,
                "with_anvisa_alerts": with_anvisa_alerts,
                "in_natura_nova1": in_natura,
                "nutriscore_distribution": grades,
            }
        finally:
            conn.close()


def get_diet_goals(db_path: str = DATABASE_PATH) -> DietGoals:
    init_db(db_path)
    with _db_lock:
        conn = _get_connection(db_path)
        try:
            row = conn.execute("SELECT * FROM diet_goals WHERE id = 1").fetchone()
            return DietGoals(**dict(row))
        finally:
            conn.close()


def calculate_mifflin_goals(
    weight_kg: float,
    height_cm: float,
    age: int,
    activity_level: str,
    goal_type: str,
) -> Dict[str, float]:
    bmr = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age + 5.0
    multipliers = {
        "sedentario": 1.2,
        "leve": 1.375,
        "moderado": 1.55,
        "intenso": 1.725,
    }
    tdee = bmr * multipliers.get(activity_level, 1.55)

    if goal_type == "cutting":
        kcal = max(1200.0, round(tdee - 450.0, -1))
        prot = round(weight_kg * 2.0)
        fat = round(weight_kg * 0.85)
    elif goal_type == "bulking":
        kcal = round(tdee + 350.0, -1)
        prot = round(weight_kg * 2.0)
        fat = round(weight_kg * 1.0)
    else:
        kcal = round(tdee, -1)
        prot = round(weight_kg * 1.8)
        fat = round(weight_kg * 0.9)

    remaining_kcal_for_carbs = max(200.0, kcal - (prot * 4.0) - (fat * 9.0))
    carbs = round(remaining_kcal_for_carbs / 4.0)

    return {
        "daily_kcal_limit": float(kcal),
        "carbs_limit_g": float(carbs),
        "proteins_limit_g": float(prot),
        "fat_limit_g": float(fat),
        "sodium_limit_mg": 2000.0,
    }


def update_diet_goals(req: DietGoalsUpdateRequest, db_path: str = DATABASE_PATH) -> DietGoals:
    current = get_diet_goals(db_path=db_path)

    if req.auto_calculate:
        calc = calculate_mifflin_goals(
            weight_kg=req.weight_kg,
            height_cm=req.height_cm,
            age=req.age,
            activity_level=req.activity_level,
            goal_type=req.goal_type,
        )
        kcal_limit = calc["daily_kcal_limit"]
        carbs_limit = calc["carbs_limit_g"]
        prot_limit = calc["proteins_limit_g"]
        fat_limit = calc["fat_limit_g"]
        sod_limit = req.sodium_limit_mg if req.sodium_limit_mg is not None else calc["sodium_limit_mg"]
    else:
        kcal_limit = req.daily_kcal_limit if req.daily_kcal_limit is not None else current.daily_kcal_limit
        carbs_limit = req.carbs_limit_g if req.carbs_limit_g is not None else current.carbs_limit_g
        prot_limit = req.proteins_limit_g if req.proteins_limit_g is not None else current.proteins_limit_g
        fat_limit = req.fat_limit_g if req.fat_limit_g is not None else current.fat_limit_g
        sod_limit = req.sodium_limit_mg if req.sodium_limit_mg is not None else current.sodium_limit_mg

    with _db_lock:
        conn = _get_connection(db_path)
        try:
            conn.execute(
                """
                UPDATE diet_goals SET
                    goal_type = ?,
                    weight_kg = ?,
                    height_cm = ?,
                    age = ?,
                    activity_level = ?,
                    daily_kcal_limit = ?,
                    carbs_limit_g = ?,
                    proteins_limit_g = ?,
                    fat_limit_g = ?,
                    sodium_limit_mg = ?
                WHERE id = 1
                """,
                (
                    req.goal_type,
                    req.weight_kg,
                    req.height_cm,
                    req.age,
                    req.activity_level,
                    kcal_limit,
                    carbs_limit,
                    prot_limit,
                    fat_limit,
                    sod_limit,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    return get_diet_goals(db_path=db_path)


def add_diary_entry(req: DietDiaryCreateRequest, db_path: str = DATABASE_PATH) -> DietDiaryEntry:
    init_db(db_path)
    d_str = req.date_str or today_str()
    now_iso = datetime.now(timezone.utc).isoformat()

    with _db_lock:
        conn = _get_connection(db_path)
        try:
            cur = conn.execute(
                """
                INSERT INTO diet_diary (
                    date_str, meal_type, product_name, source_type, portion_g,
                    kcal, carbohydrates_g, proteins_g, fat_g, fiber_g, sodium_mg, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    d_str,
                    req.meal_type,
                    req.product_name,
                    req.source_type,
                    round(req.portion_g, 1),
                    round(req.kcal, 1),
                    round(req.carbohydrates_g, 1),
                    round(req.proteins_g, 1),
                    round(req.fat_g, 1),
                    round(req.fiber_g, 1),
                    round(req.sodium_mg, 1),
                    now_iso,
                ),
            )
            conn.commit()
            entry_id = cur.lastrowid
            row = conn.execute("SELECT * FROM diet_diary WHERE id = ?", (entry_id,)).fetchone()
            return DietDiaryEntry(**dict(row))
        finally:
            conn.close()


def delete_diary_entry(entry_id: int, db_path: str = DATABASE_PATH) -> bool:
    init_db(db_path)
    with _db_lock:
        conn = _get_connection(db_path)
        try:
            cur = conn.execute("DELETE FROM diet_diary WHERE id = ?", (entry_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def get_diet_today_summary(date_str: Optional[str] = None, db_path: str = DATABASE_PATH) -> DietTodaySummary:
    init_db(db_path)
    target_date = date_str or today_str()
    goals = get_diet_goals(db_path=db_path)

    with _db_lock:
        conn = _get_connection(db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM diet_diary WHERE date_str = ? ORDER BY id ASC",
                (target_date,),
            ).fetchall()
            entries = [DietDiaryEntry(**dict(r)) for r in rows]
        finally:
            conn.close()

    consumed = {
        "kcal": round(sum(e.kcal for e in entries), 1),
        "carbohydrates_g": round(sum(e.carbohydrates_g for e in entries), 1),
        "proteins_g": round(sum(e.proteins_g for e in entries), 1),
        "fat_g": round(sum(e.fat_g for e in entries), 1),
        "fiber_g": round(sum(e.fiber_g for e in entries), 1),
        "sodium_mg": round(sum(e.sodium_mg for e in entries), 1),
    }

    remaining = {
        "kcal": round(goals.daily_kcal_limit - consumed["kcal"], 1),
        "carbohydrates_g": round(goals.carbs_limit_g - consumed["carbohydrates_g"], 1),
        "proteins_g": round(goals.proteins_limit_g - consumed["proteins_g"], 1),
        "fat_g": round(goals.fat_limit_g - consumed["fat_g"], 1),
        "sodium_mg": round(goals.sodium_limit_mg - consumed["sodium_mg"], 1),
    }

    def _pct(val: float, limit_val: float) -> float:
        if limit_val <= 0:
            return 0.0
        return round((val / limit_val) * 100.0, 1)

    percentages = {
        "kcal": _pct(consumed["kcal"], goals.daily_kcal_limit),
        "carbohydrates_g": _pct(consumed["carbohydrates_g"], goals.carbs_limit_g),
        "proteins_g": _pct(consumed["proteins_g"], goals.proteins_limit_g),
        "fat_g": _pct(consumed["fat_g"], goals.fat_limit_g),
        "sodium_mg": _pct(consumed["sodium_mg"], goals.sodium_limit_mg),
    }

    within_limit = consumed["kcal"] <= goals.daily_kcal_limit
    if within_limit:
        status_label = f"Dentro do limite diário (restam {remaining['kcal']:.0f} kcal)"
    else:
        excesso = abs(remaining["kcal"])
        status_label = f"Limite diário excedido em {excesso:.0f} kcal"

    return DietTodaySummary(
        date_str=target_date,
        goals=goals,
        consumed=consumed,
        remaining=remaining,
        percentages=percentages,
        status_label=status_label,
        within_kcal_limit=within_limit,
        entries=entries,
    )


def get_water_for_date(date_str: Optional[str] = None, db_path: str = DATABASE_PATH) -> dict:
    init_db(db_path)
    d_str = date_str or today_str()
    goals = get_diet_goals(db_path=db_path)
    if goals.weight_kg and goals.weight_kg > 0:
        goal_ml = round(goals.weight_kg * 35)
    else:
        goal_ml = 2500

    with _db_lock:
        conn = _get_connection(db_path)
        try:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount_ml), 0) AS total, MAX(id) AS last_id FROM diet_water WHERE date_str = ?",
                (d_str,),
            ).fetchone()
            total_ml = int(row["total"] or 0)
            last_id = int(row["last_id"] or 0)
        finally:
            conn.close()

    remaining_ml = max(0, goal_ml - total_ml)
    pct = round((total_ml / goal_ml) * 100.0, 1) if goal_ml > 0 else 0.0

    return {
        "id": last_id,
        "date_str": d_str,
        "amount_ml": total_ml,
        "goal_ml": goal_ml,
        "remaining_ml": remaining_ml,
        "pct": pct,
    }


def log_water(amount_ml: int, date_str: Optional[str] = None, db_path: str = DATABASE_PATH) -> dict:
    init_db(db_path)
    d_str = date_str or today_str()
    now_iso = datetime.now(timezone.utc).isoformat()

    with _db_lock:
        conn = _get_connection(db_path)
        try:
            conn.execute(
                """
                INSERT INTO diet_water (date_str, amount_ml, created_at)
                VALUES (?, ?, ?)
                """,
                (d_str, amount_ml, now_iso),
            )
            conn.commit()
        finally:
            conn.close()

    return get_water_for_date(date_str=d_str, db_path=db_path)


def reset_water_for_date(date_str: Optional[str] = None, db_path: str = DATABASE_PATH) -> bool:
    init_db(db_path)
    d_str = date_str or today_str()

    with _db_lock:
        conn = _get_connection(db_path)
        try:
            cur = conn.execute("DELETE FROM diet_water WHERE date_str = ?", (d_str,))
            conn.commit()
            return cur.rowcount >= 0
        finally:
            conn.close()


def get_7day_trends(end_date_str: Optional[str] = None, db_path: str = DATABASE_PATH) -> dict:
    init_db(db_path)
    if end_date_str:
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    else:
        end_dt = datetime.now()

    goals = get_diet_goals(db_path=db_path)
    kcal_limit = goals.daily_kcal_limit

    # Last 7 days in chronological order: end_dt - 6 days up to end_dt
    date_strs = [(end_dt - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    weekday_map = {
        0: "Seg",
        1: "Ter",
        2: "Qua",
        3: "Qui",
        4: "Sex",
        5: "Sáb",
        6: "Dom",
    }

    days_data: List[DailyTrendItem] = []
    total_water_ml_sum = 0
    total_kcal_sum = 0.0
    met_goal_count = 0

    with _db_lock:
        conn = _get_connection(db_path)
        try:
            for d in date_strs:
                cur_dt = datetime.strptime(d, "%Y-%m-%d")
                weekday_short = weekday_map.get(cur_dt.weekday(), "")

                # Diary macros
                row_diary = conn.execute(
                    """
                    SELECT
                        COALESCE(SUM(kcal), 0) AS total_kcal,
                        COALESCE(SUM(proteins_g), 0) AS total_prot,
                        COALESCE(SUM(carbohydrates_g), 0) AS total_carbs,
                        COALESCE(SUM(fat_g), 0) AS total_fat
                    FROM diet_diary
                    WHERE date_str = ?
                    """,
                    (d,),
                ).fetchone()

                day_kcal = round(float(row_diary["total_kcal"] or 0.0), 1)
                day_prot = round(float(row_diary["total_prot"] or 0.0), 1)
                day_carbs = round(float(row_diary["total_carbs"] or 0.0), 1)
                day_fat = round(float(row_diary["total_fat"] or 0.0), 1)

                # Water
                row_water = conn.execute(
                    "SELECT COALESCE(SUM(amount_ml), 0) AS total_water FROM diet_water WHERE date_str = ?",
                    (d,),
                ).fetchone()
                day_water_ml = int(row_water["total_water"] or 0)

                pct_kcal = round((day_kcal / kcal_limit) * 100.0, 1) if kcal_limit > 0 else 0.0
                met_goal = (day_kcal <= kcal_limit) if day_kcal > 0 else True
                if met_goal:
                    met_goal_count += 1

                total_water_ml_sum += day_water_ml
                total_kcal_sum += day_kcal

                days_data.append(
                    DailyTrendItem(
                        date_str=d,
                        weekday_short=weekday_short,
                        total_kcal=day_kcal,
                        kcal_limit=kcal_limit,
                        pct_kcal=pct_kcal,
                        total_prot=day_prot,
                        total_carbs=day_carbs,
                        total_fat=day_fat,
                        total_water_ml=day_water_ml,
                        met_goal=met_goal,
                    )
                )
        finally:
            conn.close()

    avg_kcal = round(total_kcal_sum / 7.0, 1)
    compliance_rate = round((met_goal_count / 7.0) * 100.0, 1)
    total_water_liters = round(total_water_ml_sum / 1000.0, 2)

    return {
        "days": [item.model_dump() for item in days_data],
        "avg_kcal": avg_kcal,
        "compliance_rate": compliance_rate,
        "total_water_liters": total_water_liters,
    }



def seed_demo_data_if_empty(db_path: str = DATABASE_PATH) -> None:
    init_db(db_path)
    existing = list_history(limit=5, db_path=db_path)
    if not existing:
        for prod in get_fallback_catalog():
            save_product(prod, db_path=db_path)

    today = today_str()
    today_dt = datetime.now()
    summary = get_diet_today_summary(date_str=today, db_path=db_path)
    if not summary.entries:
        demo_meals = [
            DietDiaryCreateRequest(
                date_str=today,
                meal_type="Café da manhã",
                product_name="Pão de Forma 100% Integral + 2 Ovos Mexidos",
                source_type="foto_ficha",
                portion_g=150.0,
                kcal=268.0,
                carbohydrates_g=19.0,
                proteins_g=18.6,
                fat_g=11.8,
                fiber_g=4.2,
                sodium_mg=335.0,
            ),
            DietDiaryCreateRequest(
                date_str=today,
                meal_type="Almoço",
                product_name="Arroz Branco + Peito de Frango Grelhado + Feijão",
                source_type="manual",
                portion_g=380.0,
                kcal=620.0,
                carbohydrates_g=64.0,
                proteins_g=52.0,
                fat_g=14.2,
                fiber_g=7.5,
                sodium_mg=480.0,
            ),
            DietDiaryCreateRequest(
                date_str=today,
                meal_type="Lanche",
                product_name="Whey Protein Concentrado 80% + Aveia em Flocos",
                source_type="foto_ficha",
                portion_g=70.0,
                kcal=258.0,
                carbohydrates_g=26.0,
                proteins_g=29.7,
                fat_g=4.7,
                fiber_g=3.6,
                sodium_mg=55.0,
            ),
            DietDiaryCreateRequest(
                date_str=today,
                meal_type="Jantar",
                product_name="Iogurte Desnatado Proteico 15g + Pasta de Amendoim",
                source_type="foto_ficha",
                portion_g=192.0,
                kcal=194.0,
                carbohydrates_g=9.1,
                proteins_g=19.6,
                fat_g=8.3,
                fiber_g=1.3,
                sodium_mg=74.0,
            ),
        ]
        for meal in demo_meals:
            add_diary_entry(meal, db_path=db_path)

    # Seed past 6 days if empty
    past_days_templates = [
        # (days_ago, water_ml, [meals])
        (
            1,
            2400,
            [
                ("Café da manhã", "Tapioca com Queijo Minas Frescal", 160.0, 310.0, 32.0, 16.0, 11.0, 1.2, 280.0),
                ("Almoço", "Filé de Salmão com Purê de Batata e Brócolis", 400.0, 680.0, 45.0, 48.0, 24.0, 6.0, 490.0),
                ("Lanche", "Barra de Proteína Crisp", 45.0, 185.0, 15.0, 14.0, 6.5, 3.0, 110.0),
                ("Jantar", "Omelete de 3 Ovos com Espinafre e Tomate", 220.0, 340.0, 5.0, 24.0, 22.0, 2.5, 390.0),
            ],
        ),
        (
            2,
            2750,
            [
                ("Café da manhã", "Overnight Oats com Frutas Vermelhas", 250.0, 340.0, 48.0, 18.0, 7.5, 6.5, 80.0),
                ("Almoço", "Patinho Moído com Mandioca Cozida e Salada", 420.0, 650.0, 55.0, 50.0, 16.0, 8.0, 520.0),
                ("Lanche", "Iogurte Grego com Granola Zero", 180.0, 220.0, 22.0, 16.0, 5.0, 3.5, 75.0),
                ("Jantar", "Sopa de Frango com Legumes", 350.0, 320.0, 25.0, 32.0, 8.0, 4.0, 450.0),
            ],
        ),
        (
            3,
            2100,
            [
                ("Café da manhã", "Panqueca de Banana com Aveia e Canela", 180.0, 290.0, 42.0, 15.0, 5.5, 5.0, 60.0),
                ("Almoço", "Peito de Frango com Macarrão Integral e Molho", 400.0, 690.0, 68.0, 54.0, 12.0, 7.0, 510.0),
                ("Lanche", "Mix de Castanhas e Uvas Passas", 50.0, 260.0, 18.0, 6.0, 17.0, 3.0, 10.0),
                ("Jantar", "Salada Caesar com Tiras de Frango Grelhado", 280.0, 380.0, 12.0, 36.0, 18.0, 4.0, 480.0),
            ],
        ),
        (
            4,
            2600,
            [
                ("Café da manhã", "Pão Francês na Chapa com Requeijão Light + Café", 120.0, 260.0, 30.0, 8.0, 9.0, 1.5, 340.0),
                ("Almoço", "Feijoada Light com Arroz e Couve Refogada", 450.0, 720.0, 58.0, 46.0, 22.0, 11.0, 650.0),
                ("Lanche", "Smoothie de Whey com Morango e Leite Desnatado", 300.0, 210.0, 16.0, 27.0, 2.0, 2.0, 90.0),
                ("Jantar", "Sanduíche Natural de Atum com Cenoura", 200.0, 360.0, 34.0, 28.0, 9.0, 4.0, 420.0),
            ],
        ),
        (
            5,
            2800,
            [
                ("Café da manhã", "Crepioca com Queijo Cottage e Orégano", 160.0, 270.0, 24.0, 20.0, 8.0, 1.0, 290.0),
                ("Almoço", "Filé Mignon Suíno com Batata Doce Assada", 380.0, 630.0, 48.0, 49.0, 18.0, 6.0, 460.0),
                ("Lanche", "Maçã com Pasta de Amendoim Integral", 150.0, 240.0, 22.0, 7.0, 12.0, 4.5, 20.0),
                ("Jantar", "Tilápia Grelhada com Legumes ao Vapor", 300.0, 330.0, 10.0, 42.0, 7.0, 5.0, 380.0),
            ],
        ),
        (
            6,
            2500,
            [
                ("Café da manhã", "Torradas Integrais com Ovos Poché e Abacate", 190.0, 350.0, 26.0, 17.0, 17.0, 5.0, 310.0),
                ("Almoço", "Arroz Integral, Lentilha e Sobrecoxa Assada", 420.0, 670.0, 60.0, 47.0, 21.0, 9.0, 520.0),
                ("Lanche", "Whey Protein Isolado com Água de Coco", 300.0, 170.0, 11.0, 26.0, 0.5, 0.5, 70.0),
                ("Jantar", "Wrap Integral de Frango com Ricota", 210.0, 350.0, 28.0, 31.0, 9.0, 3.5, 410.0),
            ],
        ),
    ]

    for days_ago, water_ml, meals in past_days_templates:
        p_date = (today_dt - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        # Check if meals exist for p_date
        past_summary = get_diet_today_summary(date_str=p_date, db_path=db_path)
        if not past_summary.entries:
            for m_type, p_name, portion, kcal, carbs, prot, fat, fiber, sod in meals:
                add_diary_entry(
                    DietDiaryCreateRequest(
                        date_str=p_date,
                        meal_type=m_type,
                        product_name=p_name,
                        source_type="manual",
                        portion_g=portion,
                        kcal=kcal,
                        carbohydrates_g=carbs,
                        proteins_g=prot,
                        fat_g=fat,
                        fiber_g=fiber,
                        sodium_mg=sod,
                    ),
                    db_path=db_path,
                )
        # Check if water exists for p_date
        water_stat = get_water_for_date(date_str=p_date, db_path=db_path)
        if water_stat["amount_ml"] == 0:
            log_water(amount_ml=water_ml, date_str=p_date, db_path=db_path)

    # Check today's water as well
    today_water = get_water_for_date(date_str=today, db_path=db_path)
    if today_water["amount_ml"] == 0:
        log_water(amount_ml=1250, date_str=today, db_path=db_path)

