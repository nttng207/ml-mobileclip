from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import DEFAULT_TOP_K, MAX_TOP_K, MAX_UPLOAD_FILES, TEMPLATES_DIR, UPLOADS_DIR, ensure_dirs
from recall_service import RecallLensManager

ensure_dirs()

app = FastAPI(title="RecallLens", version="0.2.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
manager = RecallLensManager()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "startup_error": manager.startup_error,
            "default_top_k": DEFAULT_TOP_K,
            "max_top_k": MAX_TOP_K,
            "default_model_name": manager.default_model_name,
            "available_models": manager.list_models(),
        },
    )


@app.get("/api/models")
def api_models():
    return {
        "ok": True,
        "default_model_name": manager.default_model_name,
        "models": manager.list_models(),
    }


@app.get("/api/status")
def api_status(model_name: str | None = Query(default=None)):
    try:
        return manager.status(model_name=model_name)
    except Exception as exc:
        try:
            selected_model = manager.resolve_model_name(model_name)
        except Exception:
            selected_model = model_name or manager.default_model_name
        return JSONResponse(status_code=503, content=manager.error_payload(selected_model, exc))


@app.post("/api/upload")
async def api_upload(
    files: list[UploadFile] = File(...),
    model_name: str = Form(...),
):
    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files: {len(files)} submitted, maximum is {MAX_UPLOAD_FILES}.",
        )

    try:
        service = manager.get_service(model_name=model_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        selected_model = model_name or manager.default_model_name
        return JSONResponse(status_code=503, content=manager.error_payload(selected_model, exc))

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

    result = service.upload_files(payload)
    result["selected_model"] = service.model_name
    result["models"] = manager.list_models()
    return result


@app.post("/api/search")
def api_search(
    query: str = Form(...),
    top_k: int = Form(DEFAULT_TOP_K),
    model_name: str = Form(...),
):
    try:
        service = manager.get_service(model_name=model_name)
        result = service.search(query=query, top_k=min(max(int(top_k), 1), MAX_TOP_K))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        selected_model = model_name or manager.default_model_name
        return JSONResponse(status_code=503, content=manager.error_payload(selected_model, exc))

    result["selected_model"] = service.model_name
    result["models"] = manager.list_models()
    return result


@app.post("/api/search-by-image")
async def api_search_by_image(
    file: UploadFile = File(...),
    top_k: int = Form(DEFAULT_TOP_K),
    model_name: str = Form(...),
):
    try:
        service = manager.get_service(model_name=model_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        selected_model = model_name or manager.default_model_name
        return JSONResponse(status_code=503, content=manager.error_payload(selected_model, exc))

    raw = await file.read()
    try:
        result = service.search_by_image(raw=raw, top_k=min(max(int(top_k), 1), MAX_TOP_K))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result["selected_model"] = service.model_name
    result["models"] = manager.list_models()
    return result


class VisualizeIdsRequest(BaseModel):
    ids: list[int]
    model_name: str
    query: str | None = None


@app.post("/api/visualize-ids")
def api_visualize_ids(body: VisualizeIdsRequest):
    try:
        return manager.visualize_ids(ids=body.ids, model_name=body.model_name, query=body.query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        selected_model = body.model_name or manager.default_model_name
        return JSONResponse(status_code=503, content=manager.error_payload(selected_model, exc))


@app.get("/api/visualize")
def api_visualize(model_name: str | None = Query(default=None)):
    try:
        return manager.visualize(model_name=model_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        selected_model = model_name or manager.default_model_name
        return JSONResponse(status_code=503, content=manager.error_payload(selected_model, exc))


@app.get("/health")
def health():
    return {
        "ok": manager.startup_error is None,
        "startup_error": manager.startup_error,
        "default_model_name": manager.default_model_name,
        "models": manager.list_models(),
    }
