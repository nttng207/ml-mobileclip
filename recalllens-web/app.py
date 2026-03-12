from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import DB_PATH, DEFAULT_TOP_K, MAX_TOP_K, TEMPLATES_DIR, UPLOADS_DIR, ensure_dirs
from database import init_db
from recall_service import RecallLensService

ensure_dirs()
init_db(DB_PATH)

app = FastAPI(title="RecallLens", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

service: RecallLensService | None = None
startup_error: str | None = None


@app.on_event("startup")
def startup_event() -> None:
    global service, startup_error
    try:
        service = RecallLensService()
        startup_error = None
    except Exception as exc:
        service = None
        startup_error = str(exc)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "startup_error": startup_error,
            "default_top_k": DEFAULT_TOP_K,
            "max_top_k": MAX_TOP_K,
        },
    )


@app.get("/api/status")
def api_status():
    if service is None:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": startup_error or "Service not ready."},
        )
    return service.status()


@app.post("/api/upload")
async def api_upload(files: list[UploadFile] = File(...)):
    if service is None:
        raise HTTPException(status_code=503, detail=startup_error or "Service not ready.")

    payload = []
    for file in files:
        raw = await file.read()
        payload.append(
            {
                "filename": file.filename or "upload",
                "content_type": file.content_type or "application/octet-stream",
                "bytes": raw,
            }
        )

    return service.upload_files(payload)


@app.post("/api/search")
def api_search(query: str = Form(...), top_k: int = Form(DEFAULT_TOP_K)):
    if service is None:
        raise HTTPException(status_code=503, detail=startup_error or "Service not ready.")
    try:
        result = service.search(query=query, top_k=min(top_k, MAX_TOP_K))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@app.get("/health")
def health():
    return {
        "ok": service is not None,
        "startup_error": startup_error,
    }
