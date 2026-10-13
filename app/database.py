import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.config import DATABASE_PATH
from app.models.schemas import ProductAnalysis
from app.services.openfoodfacts import get_fallback_catalog

_db_lock = threading.Lock()


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


def seed_demo_data_if_empty(db_path: str = DATABASE_PATH) -> None:
    init_db(db_path)
    existing = list_history(limit=5, db_path=db_path)
    if existing:
        return
    for prod in get_fallback_catalog():
        save_product(prod, db_path=db_path)
