# RecallLens Web

RecallLens is a self-hosted image search web app powered by MobileCLIP. Index your local image collection and search it with natural language or a query image — all running on your own machine.

## Features

- Upload images individually or as a whole folder (Chromium-based browsers)
- **Text search** — find images by natural language description (e.g. `black mug on desk`)
- **Image search** — find visually similar images by uploading a query image
- **3D embedding visualizer** — explore your indexed images in an interactive Three.js scatter plot (PCA-reduced to 3D)
- **Multi-model support** — switch between multiple MobileCLIP checkpoints
- Batch upload up to 1,000 images at a time
- Duplicate detection via SHA-1
- Local thumbnail generation and embedding storage
- Fully local — no cloud, no telemetry

## Quick Start (Docker)

```bash
docker pull vnk8071/recalllens:latest
docker run -p 8000:8000 vnk8071/recalllens:latest
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

To persist indexed data across container restarts:

```bash
docker run -p 8000:8000 \
  -v "$PWD/checkpoints:/app/checkpoints" \
  -v "$PWD/data:/app/data" \
  -v "$PWD/uploads:/app/uploads" \
  vnk8071/recalllens:latest
```

## Local Development

### 1. Install the MobileCLIP package

From the repo root:

```bash
conda create -n clipenv python=3.10
conda activate clipenv
pip install -e .
```

### 2. Install app dependencies

```bash
cd recalllens-web
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### 3. Download a MobileCLIP checkpoint

```bash
bash scripts/download_model.sh
```

This downloads `mobileclip_s0`, `mobileclip_s1`, `mobileclip_s2`, and `mobileclip_b` into `checkpoints/mobileclip/`.

### 4. Run the app

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000).

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MOBILECLIP_MODEL_NAME` | `mobileclip_s0` | Default model to load on startup |
| `MOBILECLIP_MODEL_PATH` | *(auto)* | Explicit path to the default model checkpoint |
| `MOBILECLIP_AVAILABLE_MODELS` | *(auto)* | Comma-separated list of additional model names |
| `RECALLLENS_PROMPT_TEMPLATE` | `a photo of {}` | Prompt template wrapping text queries |

Example with custom model:

```bash
export MOBILECLIP_MODEL_NAME=mobileclip_s2
export MOBILECLIP_MODEL_PATH=/absolute/path/to/mobileclip_s2.pt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## Dataset Preparation

If your images are organized in subfolders, flatten them into a single directory:

```bash
python scripts/flatten_dataset.py \
  --src /path/to/dataset \
  --dst /path/to/flat_output
```

## Build Docker Image

```bash
# From the ml-mobileclip repo root
docker build -f recalllens-web/docker/Dockerfile -t recalllens .
docker run -p 8000:8000 recalllens
```

or

```bash
docker run -p 8000:8000 vnk8071/recalllens:latest
```

## Notes

- Search quality depends on the checkpoint and the prompt template.
- `mobileclip_s0` is the best starting point for speed; `mobileclip_s2` gives better accuracy.
- The app uses CPU-only PyTorch — no GPU required.
