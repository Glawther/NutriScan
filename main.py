from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.config import APP_NAME, APP_VERSION, HOST, PORT
from app.database import seed_demo_data_if_empty

STATIC_DIR = Path(__file__).resolve().parent / "app" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_demo_data_if_empty()
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Consulta nutricional de alimentos via Open Food Facts com avaliação de rotulagem frontal ANVISA RDC 429/2020, classificação NOVA e Nutri-Score.",
    lifespan=lifespan,
)

app.include_router(api_router)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def root_index():
    return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
