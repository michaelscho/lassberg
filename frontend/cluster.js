/**
 * Phase 7: static cluster-map visualization. Reads the precomputed UMAP 2D projection and HDBSCAN
 * cluster assignments (clustering/umap_2d.json, clusters.json, copied by export_frontend.py) and
 * draws a canvas scatterplot - no model download, works fully offline, the entry point for users
 * without a token/model.
 */

const PALETTE = [
  "#1d4e89", "#8a6f45", "#3f6b5c", "#a13d3d", "#6a4c93", "#c97b2a",
  "#2a6f6f", "#8c5b8a", "#4a7c3f", "#b0552f", "#4361ee", "#e07a5f",
  "#3d5a80", "#98723a", "#588157", "#9d4edd", "#e63946", "#457b9d",
];
const NOISE_COLOR = "#b8bfc9";

function colorFor(clusterLabel) {
  const n = Number(clusterLabel);
  if (n === -1) return NOISE_COLOR;
  return PALETTE[n % PALETTE.length];
}

export async function initClusterUI() {
  const [coordsResp, clustersResp, indexResp] = await Promise.all([
    fetch("data/umap_2d.json"),
    fetch("data/clusters.json"),
    fetch("data/letters_index.json"),
  ]);
  const coords = await coordsResp.json();
  const { clusters, assignments } = await clustersResp.json();
  const lettersById = Object.fromEntries((await indexResp.json()).map((l) => [l.id, l]));

  const canvas = document.getElementById("cluster-canvas");
  const tooltip = document.getElementById("cluster-tooltip");
  const legend = document.getElementById("cluster-legend");
  const ctx = canvas.getContext("2d");

  const ids = Object.keys(coords);
  const xs = ids.map((id) => coords[id][0]);
  const ys = ids.map((id) => coords[id][1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const pad = 30;
  const w = canvas.width - 2 * pad;
  const h = canvas.height - 2 * pad;

  function project(x, y) {
    const px = pad + ((x - minX) / (maxX - minX || 1)) * w;
    const py = pad + (1 - (y - minY) / (maxY - minY || 1)) * h;
    return [px, py];
  }

  const points = ids.map((id) => {
    const [px, py] = project(...coords[id]);
    return { id, px, py, cluster: assignments[id] };
  });

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const p of points) {
      ctx.beginPath();
      ctx.arc(p.px, p.py, 5, 0, 2 * Math.PI);
      ctx.fillStyle = colorFor(p.cluster);
      ctx.globalAlpha = p.cluster === -1 ? 0.5 : 0.85;
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
  draw();

  // legend, sorted by cluster size descending
  const sortedLabels = Object.entries(clusters).sort((a, b) => b[1].size - a[1].size);
  legend.innerHTML = sortedLabels
    .map(([label, info]) => {
      const terms = info.top_terms.slice(0, 4).join(", ");
      return `<div><span class="swatch" style="background:${colorFor(label)}"></span>
        Cluster ${label} (${info.size}): ${terms}</div>`;
    })
    .join("") + `<div><span class="swatch" style="background:${NOISE_COLOR}"></span>Noise (unclustered)</div>`;

  canvas.addEventListener("mousemove", (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const hit = points.find((p) => Math.hypot(p.px - mx, p.py - my) < 6);
    if (hit) {
      const letter = lettersById[hit.id];
      tooltip.style.display = "block";
      tooltip.style.left = `${e.clientX + 12}px`;
      tooltip.style.top = `${e.clientY + 12}px`;
      tooltip.innerHTML = `<strong>${hit.id}</strong><br>${letter?.date || ""} - ${letter?.sender || "?"} &rarr; ${letter?.recipient || "?"}<br>${(letter?.incipit || "").slice(0, 120)}...`;
      canvas.style.cursor = "pointer";
      canvas.dataset.hoverId = hit.id;
    } else {
      tooltip.style.display = "none";
      canvas.style.cursor = "crosshair";
      delete canvas.dataset.hoverId;
    }
  });

  canvas.addEventListener("click", () => {
    const id = canvas.dataset.hoverId;
    if (id) window.open(`../html/letters/${id}.html`, "_blank");
  });
}
