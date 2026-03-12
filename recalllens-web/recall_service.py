from __future__ import annotations

import hashlib
import io
import mimetypes
import time
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image, UnidentifiedImageError

import mobileclip

from config import (
    DB_PATH,
    EMBEDDINGS_PATH,
    MODEL_NAME,
    MODEL_PATH,
    ORIGINALS_DIR,
    PROMPT_TEMPLATE,
    THUMBS_DIR,
    THUMB_SIZE,
)
from database import count_images, get_image_by_sha1, get_images_by_rows, insert_image, list_recent_images

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


class RecallLensService:
    def __init__(self) -> None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Checkpoint not found at {MODEL_PATH}. Run scripts/download_model.sh or set MOBILECLIP_MODEL_PATH."
            )

        self.model_name = MODEL_NAME
        self.model_path = MODEL_PATH
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _, self.preprocess = mobileclip.create_model_and_transforms(
            self.model_name,
            pretrained=str(self.model_path),
        )
        self.tokenizer = mobileclip.get_tokenizer(self.model_name)
        self.model.eval()
        self.model = self.model.to(self.device)
        self.embeddings = self._load_embeddings()

    def _load_embeddings(self) -> np.ndarray:
        if EMBEDDINGS_PATH.exists():
            arr = np.load(EMBEDDINGS_PATH)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            return arr.astype(np.float32)
        return np.zeros((0, 0), dtype=np.float32)

    def _save_embeddings(self) -> None:
        np.save(EMBEDDINGS_PATH, self.embeddings)

    def _autocast(self):
        if self.device == "cuda":
            return torch.cuda.amp.autocast(dtype=torch.float16)
        return nullcontext()

    def _encode_pil(self, image: Image.Image) -> np.ndarray:
        image = image.convert("RGB")
        batch = self.preprocess(image).unsqueeze(0).to(self.device)
        with torch.inference_mode(), self._autocast():
            features = self.model.encode_image(batch)
            features = features / features.norm(dim=-1, keepdim=True)
        return features.detach().float().cpu().numpy()[0]

    def _encode_text(self, query: str) -> np.ndarray:
        prompt = PROMPT_TEMPLATE.format(query.strip())
        tokens = self.tokenizer([prompt]).to(self.device)
        with torch.inference_mode(), self._autocast():
            features = self.model.encode_text(tokens)
            features = features / features.norm(dim=-1, keepdim=True)
        return features.detach().float().cpu().numpy()[0]

    def _append_embedding(self, vector: np.ndarray) -> int:
        vector = vector.astype(np.float32)
        if self.embeddings.size == 0:
            self.embeddings = vector.reshape(1, -1)
        else:
            self.embeddings = np.vstack([self.embeddings, vector.reshape(1, -1)])
        row = self.embeddings.shape[0] - 1
        self._save_embeddings()
        return int(row)

    def upload_files(self, files: list[dict[str, Any]]) -> dict[str, Any]:
        started = time.perf_counter()
        indexed = []
        duplicates = []
        rejected = []

        for item in files:
            filename = (item.get("filename") or "upload").strip() or "upload"
            content_type = item.get("content_type") or "application/octet-stream"
            raw: bytes = item["bytes"]
            sha1 = hashlib.sha1(raw).hexdigest()

            existing = get_image_by_sha1(DB_PATH, sha1)
            if existing:
                duplicates.append(self._public_record(existing, score=None))
                continue

            try:
                image = Image.open(io.BytesIO(raw)).convert("RGB")
            except UnidentifiedImageError:
                rejected.append({"filename": filename, "reason": "not a readable image"})
                continue
            except Exception as exc:
                rejected.append({"filename": filename, "reason": str(exc)})
                continue

            suffix = Path(filename).suffix.lower()
            if suffix not in SUPPORTED_EXTENSIONS:
                guessed = mimetypes.guess_extension(content_type or "") or ".jpg"
                suffix = guessed.lower() if guessed else ".jpg"
                if suffix == ".jpe":
                    suffix = ".jpg"
                if suffix not in SUPPORTED_EXTENSIONS:
                    suffix = ".jpg"

            original_name = f"{sha1}{suffix}"
            thumb_name = f"{sha1}.jpg"
            original_abs = ORIGINALS_DIR / original_name
            thumb_abs = THUMBS_DIR / thumb_name

            with open(original_abs, "wb") as fh:
                fh.write(raw)

            thumb = image.copy()
            thumb.thumbnail(THUMB_SIZE)
            thumb.save(thumb_abs, format="JPEG", quality=88)

            embedding_row = self._append_embedding(self._encode_pil(image))
            added_at = datetime.now(timezone.utc).isoformat()
            record = {
                "sha1": sha1,
                "filename": filename,
                "original_relpath": f"uploads/originals/{original_name}",
                "thumb_relpath": f"uploads/thumbs/{thumb_name}",
                "width": image.width,
                "height": image.height,
                "mime_type": content_type,
                "added_at": added_at,
                "embedding_row": embedding_row,
            }
            image_id = insert_image(DB_PATH, record)
            record["id"] = image_id
            indexed.append(self._public_record(record, score=None))

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "ok": True,
            "indexed": indexed,
            "duplicates": duplicates,
            "rejected": rejected,
            "total_images": count_images(DB_PATH),
            "elapsed_ms": elapsed_ms,
        }

    def search(self, query: str, top_k: int) -> dict[str, Any]:
        query = query.strip()
        if not query:
            raise ValueError("Query must not be empty.")
        if self.embeddings.size == 0:
            return {
                "ok": True,
                "query": query,
                "count": 0,
                "results": [],
                "elapsed_ms": 0.0,
            }

        started = time.perf_counter()
        text_vec = self._encode_text(query)
        scores = self.embeddings @ text_vec
        top_k = max(1, min(int(top_k), len(scores)))
        top_rows = np.argsort(-scores)[:top_k].astype(int).tolist()
        records = get_images_by_rows(DB_PATH, top_rows)

        results = []
        for row in top_rows:
            record = records.get(int(row))
            if record is None:
                continue
            results.append(self._public_record(record, score=float(scores[row])))

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "ok": True,
            "query": query,
            "count": len(results),
            "results": results,
            "elapsed_ms": elapsed_ms,
        }

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "model_name": self.model_name,
            "model_path": str(self.model_path),
            "device": self.device,
            "total_images": count_images(DB_PATH),
            "embedding_rows": int(self.embeddings.shape[0]) if self.embeddings.size else 0,
            "recent": [self._public_record(item, score=None) for item in list_recent_images(DB_PATH, limit=12)],
        }

    def _public_record(self, record: dict[str, Any], score: float | None) -> dict[str, Any]:
        return {
            "id": int(record["id"]),
            "filename": record["filename"],
            "width": int(record["width"]),
            "height": int(record["height"]),
            "added_at": record["added_at"],
            "score": score,
            "image_url": f"/{record['original_relpath']}",
            "thumb_url": f"/{record['thumb_relpath']}",
        }
