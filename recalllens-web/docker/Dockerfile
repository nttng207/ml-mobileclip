FROM python:3.10-slim

# ── system deps ──────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── install torch CPU-only first (keeps image small, no CUDA bloat) ──────────
RUN pip install --no-cache-dir \
    torch==2.2.2+cpu \
    torchvision==0.17.2+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# ── install mobileclip and its runtime deps (torch already pinned to CPU) ─────
COPY mobileclip/      /tmp/mobileclip_pkg/mobileclip/
COPY setup.py         /tmp/mobileclip_pkg/setup.py
COPY requirements.txt /tmp/mobileclip_pkg/requirements.txt
COPY README.md        /tmp/mobileclip_pkg/README.md
RUN pip install --no-cache-dir \
    timm>=0.9.5 \
    open-clip-torch>=2.20.0 \
    && pip install --no-cache-dir --no-deps /tmp/mobileclip_pkg \
    && rm -rf /tmp/mobileclip_pkg

# ── install web-app python deps ───────────────────────────────────────────────
COPY recalllens-web/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ── copy web-app source ───────────────────────────────────────────────────────
COPY recalllens-web/ .

# ── runtime dirs ─────────────────────────────────────────────────────────────
RUN mkdir -p uploads/originals uploads/thumbs data checkpoints/mobileclip

# ── expose & launch ──────────────────────────────────────────────────────────
EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
