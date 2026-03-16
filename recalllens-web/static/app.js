const filePicker = document.getElementById("filePicker");
const folderPicker = document.getElementById("folderPicker");
const modelSelect = document.getElementById("modelSelect");
const modelHint = document.getElementById("modelHint");
const uploadForm = document.getElementById("uploadForm");
const uploadBtn = document.getElementById("uploadBtn");
const uploadSummary = document.getElementById("uploadSummary");
const searchForm = document.getElementById("searchForm");
const queryInput = document.getElementById("queryInput");
const topKInput = document.getElementById("topKInput");
const statusPill = document.getElementById("statusPill");
const resultsGrid = document.getElementById("resultsGrid");
const resultsMeta = document.getElementById("resultsMeta");
const previewDialog = document.getElementById("previewDialog");
const previewImage = document.getElementById("previewImage");
const previewCaption = document.getElementById("previewCaption");
const closePreviewBtn = document.getElementById("closePreviewBtn");

function setStatus(text, tone = "neutral") {
  statusPill.textContent = text;
  statusPill.dataset.tone = tone;
}

function getSelectedModel() {
  return modelSelect?.value || "";
}

function getSelectedFiles() {
  const files = [];
  for (const file of filePicker.files || []) files.push(file);
  for (const file of folderPicker.files || []) files.push(file);
  return files;
}

function updateUploadSummary() {
  const files = getSelectedFiles();
  if (!files.length) {
    uploadSummary.textContent = "No files selected yet.";
    return;
  }

  const totalMB = files.reduce((sum, file) => sum + file.size, 0) / (1024 * 1024);
  uploadSummary.textContent = `${files.length} file(s) selected · ${totalMB.toFixed(2)} MB total`;
}

function syncModelOptions(models, preferredModel) {
  if (!modelSelect || !Array.isArray(models) || !models.length) return;

  const targetModel = preferredModel || getSelectedModel() || modelSelect.value;
  modelSelect.innerHTML = "";

  for (const model of models) {
    const option = document.createElement("option");
    option.value = model.name;
    option.textContent = model.name;
    option.dataset.totalImages = String(model.total_images ?? 0);
    option.dataset.checkpointExists = String(Boolean(model.checkpoint_exists));
    option.dataset.checkpointPath = model.checkpoint_path || "";
    option.dataset.error = model.error || "";
    if (model.name === targetModel) {
      option.selected = true;
    }
    modelSelect.appendChild(option);
  }

  if (!modelSelect.value && models[0]) {
    modelSelect.value = models[0].name;
  }

  updateModelHint();
}

function updateModelHint() {
  if (!modelSelect || !modelHint) return;

  const option = modelSelect.selectedOptions[0];
  if (!option) {
    modelHint.textContent = "Choose a MobileCLIP checkpoint.";
    return;
  }

  const totalImages = Number(option.dataset.totalImages || "0");
  const checkpointExists = option.dataset.checkpointExists === "true";
  const error = option.dataset.error || "";

  if (!checkpointExists) {
    modelHint.textContent = `${option.value} has no checkpoint yet. Add ${option.value}.pt before indexing or searching.`;
    return;
  }

  if (error) {
    modelHint.textContent = `${option.value} failed to load: ${error}`;
    return;
  }

  modelHint.textContent = `${option.value} currently has ${totalImages} indexed image(s). Uploads and searches both use this model.`;
}

async function fetchStatus() {
  const selectedModel = getSelectedModel();
  const url = `/api/status?model_name=${encodeURIComponent(selectedModel)}`;
  const response = await fetch(url);
  const data = await response.json();

  if (data.models) {
    syncModelOptions(data.models, data.selected_model || selectedModel);
  }

  if (!response.ok) {
    throw new Error(data.error || "Service is not ready.");
  }

  setStatus(`${data.total_images} indexed · ${data.selected_model}`, "good");

  if (data.recent?.length) {
    renderResults(data.recent, `Recent images for ${data.selected_model} (${data.recent.length})`);
  } else {
    resultsGrid.classList.add("empty-state");
    resultsGrid.innerHTML = '<div class="empty-card">No images indexed for this model yet.</div>';
    resultsMeta.textContent = `No images indexed for ${data.selected_model} yet.`;
  }
}

filePicker.addEventListener("change", updateUploadSummary);
folderPicker.addEventListener("change", updateUploadSummary);
modelSelect?.addEventListener("change", async () => {
  setStatus("Loading model…", "busy");
  try {
    await fetchStatus();
  } catch (error) {
    console.error(error);
    setStatus("Error", "bad");
    resultsMeta.textContent = error.message;
  }
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const files = getSelectedFiles();
  if (!files.length) {
    alert("Select at least one image first.");
    return;
  }

  const formData = new FormData();
  formData.append("model_name", getSelectedModel());
  for (const file of files) {
    formData.append("files", file, file.name);
  }

  uploadBtn.disabled = true;
  setStatus("Uploading…", "busy");

  try {
    const response = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (data.models) {
      syncModelOptions(data.models, data.selected_model || getSelectedModel());
    }

    if (!response.ok) {
      throw new Error(data.detail || data.error || "Upload failed.");
    }

    const indexed = data.indexed?.length || 0;
    const duplicates = data.duplicates?.length || 0;
    const rejected = data.rejected?.length || 0;

    setStatus(`${data.total_images} indexed · ${data.selected_model}`, "good");
    uploadSummary.textContent = `Indexed ${indexed}, duplicates ${duplicates}, rejected ${rejected} in ${data.elapsed_ms.toFixed(1)} ms.`;

    if (data.indexed?.length) {
      renderResults(data.indexed, `Recently indexed ${data.indexed.length} image(s) with ${data.selected_model}`);
    } else {
      resultsMeta.textContent = `No new images were indexed for ${data.selected_model}.`;
    }
  } catch (error) {
    console.error(error);
    setStatus("Error", "bad");
    uploadSummary.textContent = error.message;
  } finally {
    uploadBtn.disabled = false;
  }
});

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const query = queryInput.value.trim();
  if (!query) {
    alert("Enter a search query first.");
    return;
  }

  setStatus("Searching…", "busy");
  const formData = new FormData();
  formData.append("query", query);
  formData.append("top_k", topKInput.value || "24");
  formData.append("model_name", getSelectedModel());

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (data.models) {
      syncModelOptions(data.models, data.selected_model || getSelectedModel());
    }

    if (!response.ok) {
      throw new Error(data.detail || data.error || "Search failed.");
    }

    renderResults(
      data.results || [],
      `Found ${data.count} result(s) for “${data.query}” with ${data.selected_model} in ${data.elapsed_ms.toFixed(1)} ms`
    );
    setStatus(`Ready · ${data.selected_model}`, "good");
  } catch (error) {
    console.error(error);
    setStatus("Error", "bad");
    resultsMeta.textContent = error.message;
  }
});

document.querySelectorAll(".chip").forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = button.dataset.query;
    searchForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
  });
});

function renderResults(items, metaText) {
  resultsMeta.textContent = metaText;
  resultsGrid.innerHTML = "";
  resultsGrid.classList.remove("empty-state");

  if (!items.length) {
    resultsGrid.classList.add("empty-state");
    resultsGrid.innerHTML = '<div class="empty-card">No matching images found.</div>';
    return;
  }

  for (const item of items) {
    const card = document.createElement("article");
    card.className = "result-card";
    card.innerHTML = `
      <button class="thumb-button" type="button">
        <img src="${item.thumb_url}" alt="${escapeHtml(item.filename)}" loading="lazy" />
      </button>
      <div class="card-body">
        <div class="filename" title="${escapeHtml(item.filename)}">${escapeHtml(item.filename)}</div>
        <div class="meta-row">
          <span>${item.width}×${item.height}</span>
          ${item.score == null ? "" : `<span class="score">${Number(item.score).toFixed(3)}</span>`}
        </div>
      </div>
    `;

    card.querySelector(".thumb-button").addEventListener("click", () => {
      previewImage.src = item.image_url;
      previewImage.alt = item.filename;
      previewCaption.textContent = `${item.filename}${item.score == null ? "" : ` · score ${Number(item.score).toFixed(3)}`}`;
      previewDialog.showModal();
    });

    resultsGrid.appendChild(card);
  }
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

closePreviewBtn.addEventListener("click", () => previewDialog.close());
previewDialog.addEventListener("click", (event) => {
  const rect = previewDialog.getBoundingClientRect();
  const inside =
    rect.top <= event.clientY &&
    event.clientY <= rect.top + rect.height &&
    rect.left <= event.clientX &&
    event.clientX <= rect.left + rect.width;

  if (!inside) previewDialog.close();
});

async function bootstrap() {
  setStatus("Loading…", "busy");
  updateModelHint();

  try {
    await fetchStatus();
  } catch (error) {
    console.error(error);
    setStatus("Startup error", "bad");
    resultsMeta.textContent = error.message;
  }
}

bootstrap();
