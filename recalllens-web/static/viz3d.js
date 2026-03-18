/* 3-D embedding visualizer — Three.js r165 via CDN */
(function () {
  const THREE_CDN = "https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js";

  const vizBtn      = document.getElementById("visualizeBtn");
  const vizDialog   = document.getElementById("vizDialog");
  const closeVizBtn = document.getElementById("closeVizBtn");
  const vizCanvas   = document.getElementById("vizCanvas");
  const vizTooltip  = document.getElementById("vizTooltip");
  const vizThumb    = document.getElementById("vizThumb");
  const vizLabel    = document.getElementById("vizLabel");
  const vizTitle    = document.getElementById("vizTitle");

  let THREE = null;
  let renderer = null, scene = null, camera = null;
  let pointsMesh = null;
  let animId = null;
  let allPoints = [];

  // Orbit state
  const orbit = { active: false, lastX: 0, lastY: 0 };
  let rotX = 0.3, rotY = 0.4, zoom = 1;

  async function loadThree() {
    if (THREE) return THREE;
    THREE = await import(THREE_CDN);
    return THREE;
  }

  // Extract the species prefix: everything before the first `_<digit>` segment.
  // e.g. "acinonyx-jubatus_0_052c1ab2.jpg"  →  "acinonyx-jubatus"
  //      "random_photo.jpg"                  →  "random_photo"  (fallback: full stem)
  function getPrefix(filename) {
    const stem = filename.replace(/\.[^.]+$/, ""); // strip extension
    const m = stem.match(/^(.+?)_\d/);
    return m ? m[1] : stem;
  }

  // Assign a visually distinct HSL color to each label index.
  // Uses the golden-angle trick for maximum hue separation.
  function labelColor(index, total) {
    const hue = (index * 137.508) % 360;
    const sat = 72 + (index % 3) * 8;        // 72–88 %
    const lit = 55 + (index % 5) * 4;        // 55–71 %
    return `hsl(${hue.toFixed(1)},${sat}%,${lit}%)`;
  }

  function hslToRgb(hslStr) {
    // Parse hsl(H,S%,L%) and return [r,g,b] in 0-1 range
    const m = hslStr.match(/hsl\(([\d.]+),([\d.]+)%,([\d.]+)%\)/);
    if (!m) return [1, 1, 1];
    const h = parseFloat(m[1]) / 360;
    const s = parseFloat(m[2]) / 100;
    const l = parseFloat(m[3]) / 100;
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    return [hue2rgb(p, q, h + 1/3), hue2rgb(p, q, h), hue2rgb(p, q, h - 1/3)];
  }

  function hue2rgb(p, q, t) {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1/6) return p + (q - p) * 6 * t;
    if (t < 1/2) return q;
    if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
    return p;
  }

  function buildScene(T, data, queryPoint) {
    if (renderer) { renderer.dispose(); renderer = null; }
    cancelAnimationFrame(animId);

    const w = vizCanvas.clientWidth;
    const h = vizCanvas.clientHeight;

    renderer = new T.WebGLRenderer({ canvas: vizCanvas, antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(w, h, false);
    renderer.setClearColor(0x080c12);

    scene = new T.Scene();
    camera = new T.PerspectiveCamera(60, w / h, 0.01, 1000);
    camera.position.set(0, 0, 3);

    // --- label → color map (use server-provided group, fall back to filename prefix) ---
    const getLabel = (p) => p.group || getPrefix(p.filename);
    const labels = [...new Set(data.map(getLabel))].sort();
    const colorMap = new Map(labels.map((lbl, i) => [lbl, labelColor(i, labels.length)]));

    // Normalize coords to [-1, 1]
    const xs = data.map(p => p.x), ys = data.map(p => p.y), zs = data.map(p => p.z);
    const cx = (Math.max(...xs) + Math.min(...xs)) / 2;
    const cy = (Math.max(...ys) + Math.min(...ys)) / 2;
    const cz = (Math.max(...zs) + Math.min(...zs)) / 2;
    const span = Math.max(
      Math.max(...xs) - Math.min(...xs),
      Math.max(...ys) - Math.min(...ys),
      Math.max(...zs) - Math.min(...zs),
    ) || 1;

    const positions = new Float32Array(data.length * 3);
    const colors    = new Float32Array(data.length * 3);

    for (let i = 0; i < data.length; i++) {
      positions[i * 3]     = (data[i].x - cx) / span * 2;
      positions[i * 3 + 1] = (data[i].y - cy) / span * 2;
      positions[i * 3 + 2] = (data[i].z - cz) / span * 2;

      const prefix = getLabel(data[i]);
      const [r, g, b] = hslToRgb(colorMap.get(prefix));
      colors[i * 3]     = r;
      colors[i * 3 + 1] = g;
      colors[i * 3 + 2] = b;
    }

    const geo = new T.BufferGeometry();
    geo.setAttribute("position", new T.BufferAttribute(positions, 3));
    geo.setAttribute("color",    new T.BufferAttribute(colors, 3));

    const mat = new T.PointsMaterial({ vertexColors: true, size: 0.035, sizeAttenuation: true });
    pointsMesh = new T.Points(geo, mat);
    scene.add(pointsMesh);
    scene.add(new T.AxesHelper(1.2));

    // Query point — large bright white star
    if (queryPoint) {
      const qnx = (queryPoint.x - cx) / span * 2;
      const qny = (queryPoint.y - cy) / span * 2;
      const qnz = (queryPoint.z - cz) / span * 2;

      const qgeo = new T.BufferGeometry();
      qgeo.setAttribute("position", new T.BufferAttribute(new Float32Array([qnx, qny, qnz]), 3));
      const qmat = new T.PointsMaterial({ color: 0xffffff, size: 0.12, sizeAttenuation: true });
      const qmesh = new T.Points(qgeo, qmat);
      scene.add(qmesh);

      // Store for hover detection
      allPoints.push({
        id: -1,
        filename: window._lastSearchQuery ? ("Query: \"" + window._lastSearchQuery + "\"") : "Query",
        label: "query",
        color: "#ffffff",
        thumb_url: "",
        image_url: "",
        nx: qnx, ny: qny, nz: qnz,
        isQuery: true,
      });
    }

    allPoints = data.map((p, i) => ({
      ...p,
      label: getLabel(p),
      color: colorMap.get(getLabel(p)),
      nx: positions[i * 3],
      ny: positions[i * 3 + 1],
      nz: positions[i * 3 + 2],
    }));

    // Build legend (capped at 30 entries to avoid overflow)
    buildLegend(colorMap, labels.length);
  }

  // --- Legend ---
  function buildLegend(colorMap, total) {
    let legend = document.getElementById("vizLegend");
    if (!legend) {
      legend = document.createElement("div");
      legend.id = "vizLegend";
      legend.className = "viz-legend";
      vizDialog.querySelector(".viz-shell").appendChild(legend);
    }
    legend.innerHTML = "";

    const MAX_SHOWN = 30;
    const entries = [...colorMap.entries()].slice(0, MAX_SHOWN);
    for (const [label, color] of entries) {
      const row = document.createElement("div");
      row.className = "viz-legend-row";
      row.innerHTML = `<span class="viz-legend-dot" style="background:${color}"></span><span>${label}</span>`;
      legend.appendChild(row);
    }
    if (total > MAX_SHOWN) {
      const more = document.createElement("div");
      more.className = "viz-legend-row viz-legend-more";
      more.textContent = `+${total - MAX_SHOWN} more`;
      legend.appendChild(more);
    }
  }

  function animate() {
    animId = requestAnimationFrame(animate);
    if (!renderer) return;

    const w = vizCanvas.clientWidth;
    const h = vizCanvas.clientHeight;
    if (renderer.domElement.width !== w * window.devicePixelRatio) {
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }

    scene.children.forEach(c => { c.rotation.x = rotX; c.rotation.y = rotY; });
    camera.position.z = 3 / zoom;
    renderer.render(scene, camera);
  }

  // Raycasting for hover
  function getHovered(mouseX, mouseY) {
    if (!renderer || !allPoints.length) return null;

    const rect = vizCanvas.getBoundingClientRect();
    const nx = ((mouseX - rect.left) / rect.width) * 2 - 1;
    const ny = -((mouseY - rect.top) / rect.height) * 2 + 1;

    const vec  = new THREE.Vector3();
    const mat4 = new THREE.Matrix4();
    mat4.makeRotationX(rotX).multiply(new THREE.Matrix4().makeRotationY(rotY));

    let best = null, bestDist = 0.025;
    const fovRad = (60 * Math.PI) / 180;
    const halfH  = Math.tan(fovRad / 2);

    for (const p of allPoints) {
      vec.set(p.nx, p.ny, p.nz).applyMatrix4(mat4);
      const pz  = vec.z - camera.position.z;
      const sx  = vec.x / (-pz * halfH * camera.aspect);
      const sy  = vec.y / (-pz * halfH);
      const d   = Math.hypot(sx - nx, sy - ny);
      if (d < bestDist) { bestDist = d; best = p; }
    }
    return best;
  }

  vizCanvas.addEventListener("mousemove", (e) => {
    if (orbit.active) {
      rotY += (e.clientX - orbit.lastX) * 0.008;
      rotX += (e.clientY - orbit.lastY) * 0.008;
      orbit.lastX = e.clientX;
      orbit.lastY = e.clientY;
      return;
    }

    const hovered = getHovered(e.clientX, e.clientY);
    if (hovered) {
      vizThumb.hidden = !!hovered.isQuery;
      if (!hovered.isQuery) vizThumb.src = hovered.thumb_url;
      vizLabel.textContent = hovered.isQuery ? hovered.filename : (hovered.label + " \u00b7 " + hovered.filename);
      vizLabel.style.color = hovered.color;
      vizTooltip.hidden = false;
    } else {
      vizTooltip.hidden = true;
    }
  });

  vizCanvas.addEventListener("mousedown", (e) => {
    orbit.active = true;
    orbit.lastX = e.clientX;
    orbit.lastY = e.clientY;
  });
  window.addEventListener("mouseup", () => { orbit.active = false; });

  vizCanvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    zoom = Math.max(0.2, Math.min(10, zoom * (e.deltaY < 0 ? 1.1 : 0.9)));
  }, { passive: false });

  vizCanvas.addEventListener("click", (e) => {
    const hovered = getHovered(e.clientX, e.clientY);
    if (hovered) {
      const previewImage   = document.getElementById("previewImage");
      const previewCaption = document.getElementById("previewCaption");
      const previewDialog  = document.getElementById("previewDialog");
      previewImage.src     = hovered.image_url;
      previewImage.alt     = hovered.filename;
      previewCaption.textContent = `${hovered.filename} · ${hovered.label}`;
      previewDialog.showModal();
    }
  });

  async function openViz() {
    vizBtn.disabled = true;
    const modelName = document.getElementById("modelSelect")?.value || "";
    const url = `/api/visualize?model_name=${encodeURIComponent(modelName)}`;

    try {
      const [T, resp] = await Promise.all([loadThree(), fetch(url)]);
      const data = await resp.json();

      if (!resp.ok || !data.ok) throw new Error(data.detail || data.error || "Visualize failed.");
      if (!data.points.length) { alert("No indexed images to visualize yet."); return; }

      const groupCount = new Set(data.points.map(p => p.group || getPrefix(p.filename))).size;
      vizTitle.textContent = `Embedding space · ${data.model_name} · ${data.points.length} images · ${groupCount} groups (3D PCA)`;
      buildScene(T, data.points);
      vizDialog.showModal();
      animate();
    } catch (err) {
      console.error(err);
      alert("Visualization error: " + err.message);
    } finally {
      vizBtn.disabled = false;
    }
  }

  function closeViz() {
    vizDialog.close();
    cancelAnimationFrame(animId);
    animId = null;
    vizTooltip.hidden = true;
    if (renderer) { renderer.dispose(); renderer = null; }
  }

  async function openVizFromResults() {
    const ids = window._lastSearchIds;
    const label = window._lastSearchLabel || 'search results';
    if (!ids || !ids.length) {
      alert('No search results to visualize. Run a search first.');
      return;
    }
    vizBtn.disabled = true;
    const modelName = document.getElementById('modelSelect')?.value || '';
    try {
      const [T, resp] = await Promise.all([
        loadThree(),
        fetch('/api/visualize-ids', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids, model_name: modelName, query: window._lastSearchQuery || null }),
        }),
      ]);
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.detail || data.error || 'Visualize failed.');
      if (!data.points.length) { alert('No points to visualize.'); return; }
      const groupCount = new Set(data.points.map(p => p.group || getPrefix(p.filename))).size;
      vizTitle.textContent = 'Results for ' + label + ' \u00b7 ' + data.points.length + ' images \u00b7 ' + groupCount + ' groups (3D PCA)';
      buildScene(T, data.points, data.query_point);
      vizDialog.showModal();
      animate();
    } catch (err) {
      console.error(err);
      alert('Visualization error: ' + err.message);
    } finally {
      vizBtn.disabled = false;
    }
  }

  vizBtn.addEventListener("click", openVizFromResults);
  document.getElementById("visualizeBtnModel")?.addEventListener("click", openViz);
  closeVizBtn.addEventListener("click", closeViz);
  vizDialog.addEventListener("click", (e) => {
    const rect = vizDialog.getBoundingClientRect();
    const inside =
      rect.top <= e.clientY && e.clientY <= rect.top + rect.height &&
      rect.left <= e.clientX && e.clientX <= rect.left + rect.width;
    if (!inside) closeViz();
  });
})();
