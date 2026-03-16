from __future__ import annotations

import hashlib
import io
import mimetypes
import time
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import mobileclip
import numpy as np
import torch
from PIL import Image, UnidentifiedImageError

from config import (
    ORIGINALS_DIR,
    PROMPT_TEMPLATE,
    THUMBS_DIR,
    THUMB_SIZE,
    DEFAULT_MODEL_NAME,
    get_available_model_names,
    get_model_checkpoint_path,
    get_model_db_path,
    get_model_embeddings_path,
)
from database import count_images, get_image_by_sha1, get_images_by_rows, insert_image, list_recent_images, init_db

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


class RecallLensService:
    def __init__(self, model_name: str, model_path: Path, db_path: Path, embeddings_path: Path) -> None:
        if not model_path.exists():
            raise FileNotFoundError(
                f"Checkpoint not found at {model_path}. Put {model_name}.pt in checkpoints/mobileclip "
                "or configure MOBILECLIP_MODEL_PATH / MOBILECLIP_AVAILABLE_MODELS."
            )

        self.model_name = model_name
        self.model_path = model_path
        self.db_path = db_path
        self.embeddings_path = embeddings_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        init_db(self.db_path)

        self.model, _, self.preprocess = mobileclip.create_model_and_transforms(
            self.model_name,
            pretrained=str(self.model_path),
        )
        self.tokenizer = mobileclip.get_tokenizer(self.model_name)
        self.model.eval()
        self.model = self.model.to(self.device)
        self.embeddings = self._load_embeddings()

    def _load_embeddings(self) -> np.ndarray:
        if self.embeddings_path.exists():
            arr = np.load(self.embeddings_path)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            return arr.astype(np.float32)
        return np.zeros((0, 0), dtype=np.float32)

    def _save_embeddings(self) -> None:
        np.save(self.embeddings_path, self.embeddings)

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
        indexed: list[dict[str, Any]] = []
        duplicates: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []

        for item in files:
            filename = (item.get("filename") or "upload").strip() or "upload"
            content_type = item.get("content_type") or "application/octet-stream"
            raw: bytes = item["bytes"]

            sha1 = hashlib.sha1(raw).hexdigest()
            existing = get_image_by_sha1(self.db_path, sha1)
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

            if not original_abs.exists():
                with open(original_abs, "wb") as fh:
                    fh.write(raw)

            if not thumb_abs.exists():
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
            image_id = insert_image(self.db_path, record)
            record["id"] = image_id
            indexed.append(self._public_record(record, score=None))

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "ok": True,
            "model_name": self.model_name,
            "indexed": indexed,
            "duplicates": duplicates,
            "rejected": rejected,
            "total_images": count_images(self.db_path),
            "elapsed_ms": elapsed_ms,
        }

    def search(self, query: str, top_k: int) -> dict[str, Any]:
        query = query.strip()
        if not query:
            raise ValueError("Query must not be empty.")

        if self.embeddings.size == 0:
            return {
                "ok": True,
                "model_name": self.model_name,
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
        records = get_images_by_rows(self.db_path, top_rows)

        results = []
        for row in top_rows:
            record = records.get(int(row))
            if record is None:
                continue
            results.append(self._public_record(record, score=float(scores[row])))

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "ok": True,
            "model_name": self.model_name,
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
            "total_images": count_images(self.db_path),
            "embedding_rows": int(self.embeddings.shape[0]) if self.embeddings.size else 0,
            "recent": [self._public_record(item, score=None) for item in list_recent_images(self.db_path, limit=12)],
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


class RecallLensManager:
    def __init__(self) -> None:
        self.available_model_names = get_available_model_names()
        self.default_model_name = (
            DEFAULT_MODEL_NAME if DEFAULT_MODEL_NAME in self.available_model_names else self.available_model_names[0]
        )
        self.services: dict[str, RecallLensService] = {}
        self.service_errors: dict[str, str] = {}
        self.startup_error = None

        if not any(get_model_checkpoint_path(name).exists() for name in self.available_model_names):
            self.startup_error = (
                "No MobileCLIP checkpoints found. Put one or more *.pt files in checkpoints/mobileclip "
                "or set MOBILECLIP_MODEL_PATH / MOBILECLIP_AVAILABLE_MODELS."
            )

    def resolve_model_name(self, model_name: str | None) -> str:
        candidate = (model_name or self.default_model_name).strip()
        if candidate not in self.available_model_names:
            raise ValueError(f"Unknown model '{candidate}'.")
        return candidate

    def list_models(self) -> list[dict[str, Any]]:
        models: list[dict[str, Any]] = []
        for model_name in self.available_model_names:
            checkpoint_path = get_model_checkpoint_path(model_name)
            db_path = get_model_db_path(model_name)
            models.append(
                {
                    "name": model_name,
                    "checkpoint_path": str(checkpoint_path),
                    "checkpoint_exists": checkpoint_path.exists(),
                    "loaded": model_name in self.services,
                    "ready": checkpoint_path.exists() and model_name not in self.service_errors,
                    "error": self.service_errors.get(model_name),
                    "total_images": count_images(db_path) if db_path.exists() else 0,
                }
            )
        return models

    def get_service(self, model_name: str | None = None) -> RecallLensService:
        selected_model = self.resolve_model_name(model_name)
        if selected_model in self.services:
            return self.services[selected_model]

        model_path = get_model_checkpoint_path(selected_model)
        db_path = get_model_db_path(selected_model)
        embeddings_path = get_model_embeddings_path(selected_model)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            service = RecallLensService(
                model_name=selected_model,
                model_path=model_path,
                db_path=db_path,
                embeddings_path=embeddings_path,
            )
        except Exception as exc:
            self.service_errors[selected_model] = str(exc)
            raise

        self.services[selected_model] = service
        self.service_errors.pop(selected_model, None)
        return service

    def status(self, model_name: str | None = None) -> dict[str, Any]:
        selected_model = self.resolve_model_name(model_name)
        service = self.get_service(selected_model)
        payload = service.status()
        payload["selected_model"] = selected_model
        payload["default_model_name"] = self.default_model_name
        payload["models"] = self.list_models()
        return payload

    def error_payload(self, model_name: str, error: Exception) -> dict[str, Any]:
        return {
            "ok": False,
            "error": str(error),
            "selected_model": model_name,
            "default_model_name": self.default_model_name,
            "models": self.list_models(),
        }
