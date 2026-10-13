from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.config import APP_NAME, APP_VERSION, HOST, PORT
from app.database import seed_demo_data_if_empty
from app.engine.label_ocr import ensure_sample_label_images

STATIC_DIR = Path(__file__).resolve().parent / "app" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_sample_label_images(STATIC_DIR)
    seed_demo_data_if_empty()
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "Controle de dieta diária, leitura de foto de ficha técnica nutricional (padrão ANVISA RDC 429/2020) "
        "e consulta de alimentos via Open Food Facts."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def root_index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/manifest.json", include_in_schema=False)
async def manifest_json():
    return FileResponse(str(STATIC_DIR / "manifest.json"))


@app.get("/sw.js", include_in_schema=False)
async def service_worker_js():
    return FileResponse(str(STATIC_DIR / "sw.js"), media_type="application/javascript")


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
