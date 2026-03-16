from __future__ import annotations

import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DATA_DIR = DATA_DIR / "models"
UPLOADS_DIR = BASE_DIR / "uploads"
ORIGINALS_DIR = UPLOADS_DIR / "originals"
THUMBS_DIR = UPLOADS_DIR / "thumbs"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
CHECKPOINTS_DIR = BASE_DIR / "checkpoints/mobileclip"
LEGACY_DB_PATH = DATA_DIR / "metadata.db"
LEGACY_EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"

DEFAULT_MODEL_NAME = os.getenv("MOBILECLIP_MODEL_NAME", "mobileclip_s2").strip() or "mobileclip_s2"
DEFAULT_MODEL_PATH_ENV = os.getenv("MOBILECLIP_MODEL_PATH", "").strip()
AVAILABLE_MODELS_ENV = os.getenv("MOBILECLIP_AVAILABLE_MODELS", "").strip()

THUMB_SIZE = (320, 320)
DEFAULT_TOP_K = 24
MAX_TOP_K = 96
PROMPT_TEMPLATE = os.getenv("RECALLLENS_PROMPT_TEMPLATE", "a photo of {}")


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def slugify_model_name(model_name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", model_name.strip())
    return value or "model"


def get_model_checkpoint_path(model_name: str) -> Path:
    if model_name == DEFAULT_MODEL_NAME and DEFAULT_MODEL_PATH_ENV:
        return Path(DEFAULT_MODEL_PATH_ENV)
    return CHECKPOINTS_DIR / f"{model_name}.pt"


def get_available_model_names() -> list[str]:
    names: list[str] = []

    if DEFAULT_MODEL_NAME:
        names.append(DEFAULT_MODEL_NAME)

    if AVAILABLE_MODELS_ENV:
        names.extend(part.strip() for part in AVAILABLE_MODELS_ENV.split(","))

    if CHECKPOINTS_DIR.exists():
        names.extend(path.stem for path in sorted(CHECKPOINTS_DIR.glob("*.pt")))

    return _unique_preserve_order(names) or [DEFAULT_MODEL_NAME]


def get_model_data_dir(model_name: str) -> Path:
    return MODELS_DATA_DIR / slugify_model_name(model_name)


def get_model_db_path(model_name: str) -> Path:
    model_db_path = get_model_data_dir(model_name) / "metadata.db"
    if model_name == DEFAULT_MODEL_NAME and LEGACY_DB_PATH.exists() and not model_db_path.exists():
        return LEGACY_DB_PATH
    return model_db_path


def get_model_embeddings_path(model_name: str) -> Path:
    model_embeddings_path = get_model_data_dir(model_name) / "embeddings.npy"
    if model_name == DEFAULT_MODEL_NAME and LEGACY_EMBEDDINGS_PATH.exists() and not model_embeddings_path.exists():
        return LEGACY_EMBEDDINGS_PATH
    return model_embeddings_path


def ensure_dirs() -> None:
    for path in [
        DATA_DIR,
        MODELS_DATA_DIR,
        UPLOADS_DIR,
        ORIGINALS_DIR,
        THUMBS_DIR,
        STATIC_DIR,
        TEMPLATES_DIR,
        CHECKPOINTS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)

    for model_name in get_available_model_names():
        get_model_data_dir(model_name).mkdir(parents=True, exist_ok=True)
