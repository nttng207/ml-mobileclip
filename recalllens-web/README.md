RecallLens Web

RecallLens is a local-first web app that lets users upload images and search them with natural language using MobileCLIP.

Features
- Upload multiple images from the browser
- Folder upload on Chromium-based browsers with webkitdirectory
- Local thumbnail generation
- Local embedding storage
- Natural-language search like: black mug on desk
- Duplicate detection by SHA-1
- Click a result to open the full image

1) Install the official MobileCLIP package

git clone https://github.com/apple/ml-mobileclip.git
cd ml-mobileclip
python -m venv venv
source venv/bin/activate

2) Install this app

cd /path/to/recalllens-web
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

3) Download a MobileCLIP checkpoint

bash scripts/download_model.sh

4) Run the app

uvicorn app:app --reload --host 0.0.0.0 --port 8000

Open:
http://127.0.0.1:8000

Environment variables
export MOBILECLIP_MODEL_NAME=mobileclip_s0
export MOBILECLIP_MODEL_PATH=/absolute/path/to/mobileclip_s0.pt
export RECALLLENS_PROMPT_TEMPLATE='a photo of {}'
uvicorn app:app --reload

Notes
- This app is fully local.
- Search quality depends on the checkpoint and the text prompt.
- mobileclip_s0 is the best place to start for speed.
