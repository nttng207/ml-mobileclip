#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT_DIR/checkpoints/mobileclip"
mkdir -p "$OUT_DIR"

BASE_URL="https://docs-assets.developer.apple.com/ml-research/datasets/mobileclip"

MODELS=(
mobileclip_s0.pt
mobileclip_s1.pt
mobileclip_s2.pt
mobileclip_b.pt
)

for MODEL in "${MODELS[@]}"; do
    URL="$BASE_URL/$MODEL"
    OUT_FILE="$OUT_DIR/$MODEL"

    printf "Downloading %s\n" "$URL"
    curl -L -C - "$URL" -o "$OUT_FILE"

    printf "Saved to %s\n\n" "$OUT_FILE"
done

echo "All MobileCLIP models downloaded."