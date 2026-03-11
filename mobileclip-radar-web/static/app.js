const video = document.getElementById("video");
const overlay = document.getElementById("overlay");
const captureCanvas = document.getElementById("captureCanvas");
const queryInput = document.getElementById("queryInput");
const applyQueryBtn = document.getElementById("applyQueryBtn");
const liveQuery = document.getElementById("liveQuery");
const latencyEl = document.getElementById("latencyMs");
const bestCellEl = document.getElementById("bestCell");
const hintEl = document.getElementById("hint");

const overlayCtx = overlay.getContext("2d");
const captureCtx = captureCanvas.getContext("2d");

const state = {
  active: true,
  busy: false,
  lastResult: null,
};

async function boot() {
  await setupCamera();
  bindEvents();
  loop();
}

async function setupCamera() {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: {
      facingMode: "environment",
      width: { ideal: 1280 },
      height: { ideal: 720 },
    },
    audio: false,
  });
  video.srcObject = stream;
  await video.play();
  resizeCanvases();
  window.addEventListener("resize", resizeCanvases);
}

function bindEvents() {
  applyQueryBtn.addEventListener("click", async () => {
    await updateQuery(queryInput.value);
  });

  queryInput.addEventListener("keydown", async (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      await updateQuery(queryInput.value);
    }
  });

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", async () => {
      queryInput.value = chip.dataset.query;
      await updateQuery(chip.dataset.query);
    });
  });
}

async function updateQuery(query) {
  const formData = new FormData();
  formData.append("query", query);
  const response = await fetch("/api/query", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const data = await response.json();
    alert(data.detail || "Failed to update query.");
    return;
  }
  const data = await response.json();
  liveQuery.textContent = data.query;
}

function resizeCanvases() {
  const width = video.videoWidth || 960;
  const height = video.videoHeight || 540;
  overlay.width = width;
  overlay.height = height;
  captureCanvas.width = width;
  captureCanvas.height = height;
}

async function loop() {
  while (state.active) {
    if (!state.busy && video.readyState >= 2) {
      await inferFrame();
    }
    await sleep(280);
  }
}

async function inferFrame() {
  state.busy = true;
  resizeCanvases();
  captureCtx.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
  const blob = await new Promise((resolve) => captureCanvas.toBlob(resolve, "image/jpeg", 0.82));
  const formData = new FormData();
  formData.append("file", blob, "frame.jpg");

  try {
    const response = await fetch("/api/infer", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "Inference failed.");
    }
    state.lastResult = await response.json();
    paintResult(state.lastResult);
  } catch (error) {
    hintEl.textContent = error.message;
  } finally {
    state.busy = false;
  }
}

function paintResult(result) {
  overlayCtx.clearRect(0, 0, overlay.width, overlay.height);
  liveQuery.textContent = result.query;
  latencyEl.textContent = `${result.inference_ms.toFixed(1)} ms`;
  bestCellEl.textContent = `r${result.best_cell.row + 1} c${result.best_cell.col + 1} (${result.best_cell.score.toFixed(3)})`;
  hintEl.textContent = result.hint;

  const scores = result.cells.map((cell) => cell.score);
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const range = Math.max(max - min, 1e-5);

  result.cells.forEach((cell) => {
    const n = (cell.score - min) / range;
    const alpha = 0.12 + n * 0.42;
    overlayCtx.fillStyle = `rgba(255, 80, 80, ${alpha.toFixed(3)})`;
    overlayCtx.strokeStyle = `rgba(255,255,255, ${(0.18 + n * 0.55).toFixed(3)})`;
    overlayCtx.lineWidth = 2;
    overlayCtx.fillRect(cell.x, cell.y, cell.width, cell.height);
    overlayCtx.strokeRect(cell.x, cell.y, cell.width, cell.height);
  });

  const best = result.best_cell;
  overlayCtx.strokeStyle = "rgba(80, 255, 140, 0.95)";
  overlayCtx.lineWidth = 4;
  overlayCtx.strokeRect(best.x, best.y, best.width, best.height);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

boot().catch((error) => {
  hintEl.textContent = error.message;
});