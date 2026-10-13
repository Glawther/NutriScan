import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.config import DATABASE_PATH
from app.models.schemas import (
    DietDiaryCreateRequest,
    DietDiaryEntry,
    DietGoals,
    DietGoalsUpdateRequest,
    DietTodaySummary,
    ProductAnalysis,
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


def seed_demo_data_if_empty(db_path: str = DATABASE_PATH) -> None:
    init_db(db_path)
    existing = list_history(limit=5, db_path=db_path)
    if not existing:
        for prod in get_fallback_catalog():
            save_product(prod, db_path=db_path)

    today = today_str()
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
