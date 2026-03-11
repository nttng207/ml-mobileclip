from __future__ import annotations

import time
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from PIL import Image

from mobileclip import create_model_and_transforms, get_tokenizer
from mobileclip.modules.common.mobileone import reparameterize_model


@dataclass
class RadarConfig:
    model_name: str = "mobileclip_s0"
    model_path: str = "checkpoints/mobileclip_s0.pt"
    grid_rows: int = 3
    grid_cols: int = 3
    overlap: float = 0.20
    prompt_template: str = "a photo of {}"

class MobileCLIPRadarService:
    def __init__(self, config: RadarConfig):
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _, self.preprocess = create_model_and_transforms(
            config.model_name,
            pretrained=config.model_path,
        )
        self.tokenizer = get_tokenizer(config.model_name)
        self.model.eval()
        # self.model = reparameterize_model(self.model)
        self.model = self.model.to(self.device)
        self._query = "black mug"
        self._text_features: torch.Tensor | None = None
        self.set_query(self._query)

    @property
    def query(self) -> str:
        return self._query

    def set_query(self, query: str) -> None:
        query = query.strip()
        if not query:
            raise ValueError("Query must not be empty.")
        self._query = query
        prompt = self.config.prompt_template.format(query)
        tokens = self.tokenizer([prompt]).to(self.device)
        with torch.inference_mode(), self._autocast():
            text_features = self.model.encode_text(tokens)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        self._text_features = text_features

    def infer_image(self, image: Image.Image) -> dict[str, Any]:
        if self._text_features is None:
            self.set_query(self._query)

        image = image.convert("RGB")
        width, height = image.size
        crops, cells = self._build_crops(image)
        batch = torch.stack([self.preprocess(crop) for crop in crops]).to(self.device)

        started = time.perf_counter()
        with torch.inference_mode(), self._autocast():
            image_features = self.model.encode_image(batch)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            similarities = (image_features @ self._text_features.T).squeeze(-1)
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        similarity_values = similarities.detach().float().cpu().tolist()
        results: list[dict[str, Any]] = []
        for cell, score in zip(cells, similarity_values):
            results.append({**cell, "score": float(score)})

        best = max(results, key=lambda item: item["score"])
        return {
            "query": self._query,
            "model_name": self.config.model_name,
            "image_width": width,
            "image_height": height,
            "inference_ms": elapsed_ms,
            "cells": results,
            "best_cell": best,
            "hint": self._direction_hint(best),
        }

    def _build_crops(self, image: Image.Image) -> tuple[list[Image.Image], list[dict[str, Any]]]:
        width, height = image.size
        rows = self.config.grid_rows
        cols = self.config.grid_cols
        overlap = self.config.overlap
        base_cell_w = width / cols
        base_cell_h = height / rows
        crops: list[Image.Image] = []
        cells: list[dict[str, Any]] = []

        for row in range(rows):
            for col in range(cols):
                x1 = col * base_cell_w
                y1 = row * base_cell_h
                x2 = x1 + base_cell_w
                y2 = y1 + base_cell_h

                expand_x = base_cell_w * overlap / 2.0
                expand_y = base_cell_h * overlap / 2.0

                left = max(0, int(round(x1 - expand_x)))
                top = max(0, int(round(y1 - expand_y)))
                right = min(width, int(round(x2 + expand_x)))
                bottom = min(height, int(round(y2 + expand_y)))

                crop = image.crop((left, top, right, bottom))
                crops.append(crop)
                cells.append(
                    {
                        "row": row,
                        "col": col,
                        "x": left,
                        "y": top,
                        "width": right - left,
                        "height": bottom - top,
                        "normalized": {
                            "x": left / width,
                            "y": top / height,
                            "width": (right - left) / width,
                            "height": (bottom - top) / height,
                        },
                    }
                )
        return crops, cells

    def _direction_hint(self, best: dict[str, Any]) -> str:
        rows = self.config.grid_rows
        cols = self.config.grid_cols
        row = int(best["row"])
        col = int(best["col"])

        horizontal = "keep center horizontally"
        vertical = "keep center vertically"
        if col == 0:
            horizontal = "move camera left"
        elif col == cols - 1:
            horizontal = "move camera right"

        if row == 0:
            vertical = "tilt camera up"
        elif row == rows - 1:
            vertical = "tilt camera down"

        return f"{horizontal}; {vertical}."

    def _autocast(self):
        if self.device == "cuda":
            return torch.cuda.amp.autocast(dtype=torch.float16)
        return nullcontext()


def validate_paths(config: RadarConfig) -> None:
    model_path = Path(config.model_path)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Checkpoint not found at {model_path}. Download one with scripts/download_model.sh or set MOBILECLIP_MODEL_PATH."
        )