# RadarCam Web for MobileCLIP

A web-Python adaptation of the MobileCLIP iOS demo idea: open your browser, enter a natural-language query such as `black mug`, stream webcam frames to a Python backend, score a 3x3 crop grid with MobileCLIP, and render a heatmap over the strongest semantic match.

## What this project is

This is **not** a line-by-line rewrite of Apple’s original iOS app. It is a web adaptation of the same core interaction model:

- text prompt → text embedding  
- camera frame → image embeddings  
- cosine similarity → zero-shot matching  
- live UI overlay → best semantic region  

## Requirements

- Ubuntu 22.04+ or a similar Linux distribution
- Python 3.10+
- A webcam
- A MobileCLIP checkpoint
- The official `mobileclip` Python package from the Apple repository

---

## 1. Clone the repository

```bash
git clone https://github.com/nttng207/ml-mobileclip
cd ml-mobileclip
```

## 2. Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install the `mobileclip` Python package
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Download a MobileCLIP checkpoint
```bash
bash download_checkpoint.sh
```

## 5. Run the web server
```bash
cd mobileclip-radar-web
uvicorn app:app --reload
```


## 6. Notes:

```bash
export PYTHONPATH=/home/forge/ml-mobileclip:$PYTHONPATH
```