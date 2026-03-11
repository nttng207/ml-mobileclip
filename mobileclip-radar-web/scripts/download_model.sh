#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT_DIR/checkpoints"

MODEL_URL="${MODEL_URL:-https://docs-assets.developer.apple.com/ml-research/datasets/mobileclip/mobileclip_s0.pt}"
OUT_FILE="${OUT_FILE:-$ROOT_DIR/checkpoints/mobileclip_s0.pt}"

printf 'Downloading %s\n' "$MODEL_URL"
curl -L "$MODEL_URL" -o "$OUT_FILE"
printf 'Saved checkpoint to %s\n' "$OUT_FILE"