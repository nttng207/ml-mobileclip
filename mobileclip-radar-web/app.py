from __future__ import annotations

import io
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image

from mobileclip_service import MobileCLIPRadarService, RadarConfig, validate_paths

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

config = RadarConfig(
    model_name=os.getenv("MOBILECLIP_MODEL_NAME", "mobileclip_s0"),
    model_path=os.getenv("MOBILECLIP_MODEL_PATH", str(BASE_DIR / "checkpoints" / "mobileclip_s0.pt")),
    grid_rows=int(os.getenv("RADAR_GRID_ROWS", "3")),
    grid_cols=int(os.getenv("RADAR_GRID_COLS", "3")),
    overlap=float(os.getenv("RADAR_OVERLAP", "0.20")),
)
service: MobileCLIPRadarService | None = None
startup_error: str | None = None

app = FastAPI(title="RadarCam Web", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.on_event("startup")
def load_model():
    global service, startup_error
    try:
        validate_paths(config)
        service = MobileCLIPRadarService(config)
        startup_error = None
    except Exception as exc:
        service = None
        startup_error = str(exc)


def require_service() -> MobileCLIPRadarService:
    if service is None:
        raise HTTPException(status_code=503, detail=startup_error or "Model service is not ready.")
    return service

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    current_query = service.query if service else "black mug"
    return TEMPLATES.TemplateResponse(
        "index.html",
        {
            "request": request,
            "query": current_query,
            "model_name": config.model_name,
            "grid_rows": config.grid_rows,
            "grid_cols": config.grid_cols,
            "startup_error": startup_error,
        },
    )


@app.get("/api/config")
def get_config():
    current_service = require_service()
    return {
        "query": current_service.query,
        "model_name": config.model_name,
        "grid_rows": config.grid_rows,
        "grid_cols": config.grid_cols,
        "overlap": config.overlap,
    }


@app.post("/api/query")
def set_query(query: str = Form(...)):
    current_service = require_service()
    try:
        current_service.set_query(query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "query": current_service.query}


@app.post("/api/infer")
async def infer_frame(file: UploadFile = File(...)):
    current_service = require_service()
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload must be an image.")

    raw = await file.read()
    try:
        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not decode image.") from exc

    result = current_service.infer_image(image)
    return JSONResponse(result)


@app.get("/health")
def health():
    return {
        "status": "ok" if service else "degraded",
        "query": service.query if service else None,
        "model": config.model_name,
        "startup_error": startup_error,
    }