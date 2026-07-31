from pathlib import Path

import uvicorn

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.dashboard import router

BASE_DIR = Path(__file__).resolve().parent

app_ = FastAPI(title="MathGM 2026", version="0.1.0")
app_.include_router(router)

app_.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

if __name__ == "__main__":
    uvicorn.run("run:app_", host="0.0.0.0", port=8000, reload=True)