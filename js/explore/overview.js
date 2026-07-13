/**
 * Overview tab: corpus-wide views built from register metadata (json/explore/overview.json,
 * scripts/export_overview.py) - unlike the embedding-based tools, this covers all 3,268 letters,
 * not just the full-text subset.
 *
 * Three components: a letters-per-year column chart with a correspondent filter (selected
 * correspondent's share stacked in the accent hue against a de-emphasized "all letters" track),
 * a correspondent table, and a Leaflet map of sending places. Everything links back into the
 * letters register (letters.html?q=...).
 */

let data = null;

const ACCENT = "#1d4e89";      // site --accent: the data hue
const TRACK = "#c9d5e3";       // lighter step of the same blue ramp: de-emphasized total
const SURFACE = "#ffffff";     // chart card surface (gaps/rings are drawn in this)

async function loadData() {
  if (!data) data = await (await fetch("../json/explore/overview.json")).json();
  return data;
}

function el(tag, attrs = {}, text) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text != null) node.textContent = text; // labels are untrusted data - never innerHTML
  return node;
}

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

// --- stat strip ---------------------------------------------------------------------------

function renderStats(container, totals) {
  container.textContent = "";
  const stats = [
    ["Letters in the register", totals.letters],
    ["With a date", totals.dated],
    ["Full text online", totals.fulltext],
    ["Reviewed editions", totals.published],
    ["Correspondents", totals.correspondents],
  ];
  for (const [label, value] of stats) {
    const tile = el("div", { class: "stat-tile" });
    tile.appendChild(el("div", { class: "stat-label" }, label));
    tile.appendChild(el("div", { class: "stat-value" }, value.toLocaleString("en-US")));
    container.appendChild(tile);
  }
}

// --- letters-per-year column chart --------------------------------------------------------

const CHART = { w: 900, h: 280, top: 16, right: 8, bottom: 24, left: 44 };

function renderTimeline(svg, tooltip, years, corrYears, corrLabel) {
  svg.textContent = "";
  const yearKeys = Object.keys(years).map(Number);
  const minYear = Math.min(...yearKeys);
  const maxYear = Math.max(...yearKeys);
  const span = maxYear - minYear + 1;

  const plotW = CHART.w - CHART.left - CHART.right;
  const plotH = CHART.h - CHART.top - CHART.bottom;
  const band = plotW / span;
  const barW = Math.min(24, Math.max(2, band - 2)); // ≤24px thick, 2px surface gap between bars
  const maxVal = Math.max(...Object.values(years));
  const yMax = Math.ceil(maxVal / 50) * 50; // clean tick numbers
  const y = (v) => CHART.top + plotH * (1 - v / yMax);
  const x = (year) => CHART.left + (year - minYear) * band + (band - barW) / 2;

  // recessive hairline gridlines + y ticks
  for (let v = 0; v <= yMax; v += yMax / 2) {
    svg.appendChild(svgEl("line", {
      x1: CHART.left, x2: CHART.w - CHART.right, y1: y(v), y2: y(v),
      stroke: "#e3e8ee", "stroke-width": 1,
    }));
    const tick = svgEl("text", { x: CHART.left - 6, y: y(v) + 4, "text-anchor": "end", class: "chart-tick" });
    tick.textContent = v.toLocaleString("en-US");
    svg.appendChild(tick);
  }
  // x ticks each decade
  for (let yr = Math.ceil(minYear / 10) * 10; yr <= maxYear; yr += 10) {
    const tick = svgEl("text", { x: x(yr) + barW / 2, y: CHART.h - 6, "text-anchor": "middle", class: "chart-tick" });
    tick.textContent = String(yr);
    svg.appendChild(tick);
  }

  // 4px rounded data-end, square baseline: path with rounded top corners only
  function barPath(px, py, w, h) {
    const r = Math.min(4, w / 2, h);
    const base = CHART.top + plotH;
    return `M${px},${base} L${px},${py + r} Q${px},${py} ${px + r},${py} L${px + w - r},${py} ` +
           `Q${px + w},${py} ${px + w},${py + r} L${px + w},${base} Z`;
  }

  const maxYearKey = yearKeys.find((yr) => years[yr] === maxVal);

  for (const yr of yearKeys.sort((a, b) => a - b)) {
    const total = years[yr];
    const sel = corrYears ? (corrYears[yr] || 0) : null;
    const g = svgEl("g", { class: "year-band", tabindex: "0", role: "img" });

    if (corrYears) {
      // filtered: de-emphasized total track + accent share, 2px surface gap between segments
      if (total > 0) g.appendChild(svgEl("path", { d: barPath(x(yr), y(total), barW, plotH * total / yMax), fill: TRACK }));
      if (sel > 0) {
        const h = plotH * sel / yMax;
        const gapped = svgEl("path", { d: barPath(x(yr), y(sel), barW, h), fill: ACCENT, stroke: SURFACE, "stroke-width": 2 });
        g.appendChild(gapped);
      }
    } else if (total > 0) {
      g.appendChild(svgEl("path", { d: barPath(x(yr), y(total), barW, plotH * total / yMax), fill: ACCENT }));
    }

    // selective direct label: the maximum year only
    if (!corrYears && yr === maxYearKey) {
      const lbl = svgEl("text", { x: x(yr) + barW / 2, y: y(total) - 5, "text-anchor": "middle", class: "chart-label" });
      lbl.textContent = total.toLocaleString("en-US");
      svg.appendChild(lbl);
    }

    // hit target: the full band, wider than the mark
    const hit = svgEl("rect", {
      x: CHART.left + (yr - minYear) * band, y: CHART.top, width: band, height: plotH,
      fill: "transparent", "data-year": yr,
    });
    hit.addEventListener("pointermove", (e) => {
      tooltip.textContent = "";
      tooltip.appendChild(el("strong", {}, String(yr)));
      tooltip.appendChild(el("div", {}, `${total.toLocaleString("en-US")} letters`));
      if (corrYears) tooltip.appendChild(el("div", {}, `${(sel || 0).toLocaleString("en-US")} with ${corrLabel}`));
      tooltip.style.display = "block";
      const box = svg.closest(".chart-card").getBoundingClientRect();
      tooltip.style.left = `${Math.min(e.clientX - box.left + 14, box.width - 170)}px`;
      tooltip.style.top = `${e.clientY - box.top + 14}px`;
    });
    hit.addEventListener("pointerleave", () => { tooltip.style.display = "none"; });
    hit.addEventListener("click", () => {
      window.location.href = `letters.html?q=${yr}`;
    });
    hit.style.cursor = "pointer";
    g.appendChild(hit);
    svg.appendChild(g);
  }
}

function renderTable(container, years, corrYears, corrLabel) {
  container.textContent = "";
  const table = el("table", { class: "overview-table" });
  const head = el("tr");
  head.appendChild(el("th", {}, "Year"));
  head.appendChild(el("th", {}, "Letters"));
  if (corrYears) head.appendChild(el("th", {}, corrLabel));
  table.appendChild(head);
  for (const yr of Object.keys(years)) {
    const tr = el("tr");
    tr.appendChild(el("td", {}, yr));
    tr.appendChild(el("td", {}, String(years[yr])));
    if (corrYears) tr.appendChild(el("td", {}, String(corrYears[yr] || 0)));
    table.appendChild(tr);
  }
  container.appendChild(table);
}

// --- correspondent table --------------------------------------------------------------------

function renderCorrespondents(container, correspondents) {
  container.textContent = "";
  const table = el("table", { class: "overview-table" });
  const head = el("tr");
  for (const h of ["Correspondent", "Letters", "Active"]) head.appendChild(el("th", {}, h));
  table.appendChild(head);
  for (const c of correspondents) {
    const tr = el("tr");
    const td = el("td");
    const a = el("a", { href: `letters.html?q=${encodeURIComponent(c.label)}` }, c.label);
    td.appendChild(a);
    tr.appendChild(td);
    tr.appendChild(el("td", {}, String(c.letters)));
    tr.appendChild(el("td", {}, c.from ? (c.from === c.to ? String(c.from) : `${c.from}–${c.to}`) : "—"));
    table.appendChild(tr);
  }
  container.appendChild(table);
}

// --- mention tables (historical/contemporary persons, works) ---------------------------------

function renderMentionTable(container, rows, { entityHeader, registerPage, countLabel }) {
  container.textContent = "";
  if (!rows || rows.length === 0) {
    container.appendChild(el("p", { class: "status" }, "Nothing linked yet."));
    return;
  }
  const table = el("table", { class: "overview-table" });
  const head = el("tr");
  for (const h of [entityHeader, countLabel]) head.appendChild(el("th", {}, h));
  table.appendChild(head);
  for (const r of rows) {
    const tr = el("tr");
    const td = el("td");
    if (registerPage) {
      td.appendChild(el("a", { href: `${registerPage}?q=${encodeURIComponent(r.label)}` }, r.label));
    } else {
      td.appendChild(document.createTextNode(r.label));
    }
    td.appendChild(document.createTextNode(" "));
    td.appendChild(el("a", { href: `explore.html?node=${encodeURIComponent(r.id)}`, class: "badge", title: "Show network graph" }, "graph"));
    tr.appendChild(td);
    tr.appendChild(el("td", {}, `${r.letters} ${r.letters === 1 ? "letter" : "letters"}`));
    table.appendChild(tr);
  }
  container.appendChild(table);
}

// --- map: sending places + mentioned places ---------------------------------------------------

const MENTIONED = "#8a3a91"; // matches the rs-place underline and the letter-page map

async function renderMap(container, sendingPlaces, mentionedPlaces) {
  try {
    // Leaflet JS from CDN, loaded only when the Overview tab initializes. The CSS is a static
    // <link> in explore.html's head - injecting it here raced the map render and left the panes
    // unpositioned (markers invisible, giant attribution flag).
    if (!window.L) {
      await new Promise((resolve, reject) => {
        const js = document.createElement("script");
        js.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
        js.onload = resolve;
        js.onerror = () => reject(new Error("Leaflet could not be loaded from unpkg.com"));
        document.head.appendChild(js);
      });
    }
    const map = L.map(container).setView([47.8, 8.8], 6);
    // Same muted CARTO basemap as the letter pages
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://carto.com/attributions">CARTO</a> &copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
      subdomains: "abcd",
      maxZoom: 19,
    }).addTo(map);
    // guard against the container having been laid out late (grid, cached CSS): re-measure once
    setTimeout(() => map.invalidateSize(), 250);

    function layerOf(places, color, verb) {
      const maxN = Math.max(...places.map((p) => p.letters));
      const layer = L.layerGroup();
      for (const p of places) {
        const radius = 4 + 16 * Math.sqrt(p.letters / maxN);
        const marker = L.circleMarker([p.lat, p.lon], {
          radius, color: SURFACE, weight: 2, fillColor: color, fillOpacity: 0.75,
        }).addTo(layer);
        const popup = el("div");
        popup.appendChild(el("strong", {}, p.label));
        popup.appendChild(el("div", {}, `${verb} ${p.letters.toLocaleString("en-US")} ${p.letters === 1 ? "letter" : "letters"}`));
        popup.appendChild(el("a", { href: `places.html?q=${encodeURIComponent(p.label)}` }, "Show in register"));
        marker.bindPopup(popup);
      }
      return layer;
    }

    const sending = layerOf(sendingPlaces, ACCENT, "sent from here:");
    const mentioned = layerOf(mentionedPlaces || [], MENTIONED, "mentioned in");
    sending.addTo(map); // mentioned layer starts off to keep the initial view readable
    L.control.layers(null, {
      "Sending places": sending,
      "Places mentioned in letters": mentioned,
    }, { collapsed: false }).addTo(map);
  } catch (err) {
    // never fail silently: an empty gray box is indistinguishable from "no data"
    container.textContent = "";
    container.appendChild(el("p", { class: "status" }, `Map could not be initialized: ${err.message}`));
    console.error("overview map failed:", err);
  }
}

// --- init -----------------------------------------------------------------------------------

export async function initOverviewUI() {
  const d = await loadData();

  renderStats(document.getElementById("overview-stats"), d.totals);

  const svg = document.getElementById("timeline-svg");
  const tooltip = document.getElementById("timeline-tooltip");
  const tableBox = document.getElementById("timeline-table");
  const legend = document.getElementById("timeline-legend");
  const select = document.getElementById("overview-correspondent");

  select.appendChild(el("option", { value: "" }, "All correspondents"));
  for (const c of d.correspondents) {
    select.appendChild(el("option", { value: c.id }, `${c.label} (${c.letters})`));
  }

  function draw() {
    const corr = d.correspondents.find((c) => c.id === select.value);
    renderTimeline(svg, tooltip, d.years, corr ? corr.years : null, corr?.label);
    renderTable(tableBox, d.years, corr ? corr.years : null, corr?.label);
    legend.textContent = "";
    if (corr) {
      // two series on screen -> legend present; identity never rides on color alone
      for (const [color, label] of [[ACCENT, corr.label], [TRACK, "All letters"]]) {
        const item = el("span", { class: "legend-item" });
        const swatch = el("span", { class: "legend-swatch" });
        swatch.style.background = color;
        item.appendChild(swatch);
        item.appendChild(document.createTextNode(label));
        legend.appendChild(item);
      }
    }
  }
  select.addEventListener("change", draw);
  draw();

  renderCorrespondents(document.getElementById("overview-correspondents"), d.correspondents);
  renderMentionTable(document.getElementById("overview-historical"), d.historical_persons,
    { entityHeader: "Person", registerPage: "persons.html", countLabel: "Discussed in" });
  renderMentionTable(document.getElementById("overview-contemporary"), d.contemporary_persons,
    { entityHeader: "Person", registerPage: "persons.html", countLabel: "Mentioned in" });
  renderMentionTable(document.getElementById("overview-works"), d.works,
    { entityHeader: "Work", registerPage: null, countLabel: "Discussed in" });
  await renderMap(document.getElementById("overview-map"), d.places, d.mentioned_places);
}
