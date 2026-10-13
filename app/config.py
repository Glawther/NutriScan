import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

APP_NAME = os.getenv("APP_NAME", "NutriScan")
APP_VERSION = "1.0.0"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8096"))
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "nutriscan.db"))

OFF_PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
OFF_SEARCH_URL = "https://br.openfoodfacts.org/cgi/search.pl"
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "5.5"))
USER_AGENT = "NutriScan/1.0 (https://github.com/Glawther/NutriScan)"
