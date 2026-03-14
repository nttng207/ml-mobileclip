from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
ORIGINALS_DIR = UPLOADS_DIR / "originals"
THUMBS_DIR = UPLOADS_DIR / "thumbs"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
CHECKPOINTS_DIR = BASE_DIR / "checkpoints/mobileclip"

MODEL_NAME = os.getenv("MOBILECLIP_MODEL_NAME", "mobileclip_s2")
MODEL_PATH = Path(
    os.getenv("MOBILECLIP_MODEL_PATH", str(CHECKPOINTS_DIR / "mobileclip_s2.pt"))
)

DB_PATH = DATA_DIR / "metadata.db"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"
THUMB_SIZE = (320, 320)
DEFAULT_TOP_K = 24
MAX_TOP_K = 96
PROMPT_TEMPLATE = os.getenv("RECALLLENS_PROMPT_TEMPLATE", "a photo of {}")


def ensure_dirs() -> None:
    for path in [
        DATA_DIR,
        UPLOADS_DIR,
        ORIGINALS_DIR,
        THUMBS_DIR,
        STATIC_DIR,
        TEMPLATES_DIR,
        CHECKPOINTS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
