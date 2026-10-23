/**
 * Manuscripts: register manuscripts (lassberg-witness-NNNN) with their Handschriftenportal (HSP)
 * data. Static, loaded per manuscript: json/explore/manuscripts.json (small index) plus
 * json/hsp/<id>.json (public, licence-gated: description content only for freely licensed
 * descriptions). When the site is served locally with the gitignored full export present
 * (json/hsp-local/index.json), that ungated version is used instead - see
 * scripts/export_manuscripts.py. Data source: Handschriftenportal (snapshot, see fetched_at).
 */

let indexPromise = null;
let sourcePromise = null;

export function loadManuscriptIndex() {
  if (!indexPromise) indexPromise = fetch("../json/explore/manuscripts.json").then((r) => r.json());
  return indexPromise;
}

/** Checks once per session whether the local full version exists (at most one 404 on public hosts). */
export function manuscriptSource() {
  if (!sourcePromise) {
    sourcePromise = fetch("../json/hsp-local/index.json")
      .then((r) => (r.ok ? { dir: "hsp-local", local: true } : { dir: "hsp", local: false }))
      .catch(() => ({ dir: "hsp", local: false }));
  }
  return sourcePromise;
}

const norm = (s) => String(s || "").toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");

export async function findManuscripts(query, limit = 10) {
  const list = await loadManuscriptIndex();
  const q = norm(query).trim();
  if (!q) return [...list].sort((a, b) => b.n_letters - a.n_letters).slice(0, limit);
  const words = q.split(/\s+/).filter(Boolean);
  return list
    .map((m) => {
      const hay = norm([m.label, m.shelfmark, m.settlement, m.repository, m.hsp_id, m.id, m.search].join(" "));
      const score = words.every((w) => hay.includes(w)) ? words.reduce((s, w) => s + (norm(m.label).includes(w) ? 2 : 1), 0) : 0;
      return { m, score };
    })
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score || b.m.n_letters - a.m.n_letters)
    .slice(0, limit)
    .map((x) => x.m);
}

export async function getManuscript(id) {
  const { dir, local } = await manuscriptSource();
  const resp = await fetch(`../json/${dir}/${encodeURIComponent(id)}.json`);
  if (!resp.ok) throw new Error(`no manuscript data for ${id}`);
  const doc = await resp.json();
  doc._local = local;
  return doc;
}

// --- UI ----------------------------------------------------------------------------------------

function el(tag, attrs = {}, text) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text != null) node.textContent = text; // register/HSP text is untrusted data - never innerHTML
  return node;
}

const CORE_LABELS = [
  ["settlement-display", "Ort"], ["repository-display", "Bibliothek"], ["idno-display", "Signatur"],
  ["title-display", "Titel (HSP)"], ["orig-date-lang-display", "Datierung"], ["orig-place-display", "Entstehungsort"],
  ["leaves-count-display", "Umfang"], ["material-display", "Material"], ["dimensions-display", "Maße"],
];

function licenceLabel(d) {
  if (d.licence_status === "free") return "frei lizenziert";
  if (d.licence_status === "restricted") return "Lizenz eingeschränkt (urheberrechtlich geschützt)";
  return "Lizenz unbekannt";
}

function renderDescription(d) {
  const box = el("div", { class: "card mb-3" });
  const body = el("div", { class: "card-body" });
  body.append(el("h4", { class: "h6" }, d.citation || d.id));
  const meta = el("p", { class: "small text-muted mb-2" }, `${licenceLabel(d)} · Stand ${d.fetched_at || "?"} · `);
  const link = el("a", { href: d.portal_url, target: "_blank", rel: "noopener" }, "im Handschriftenportal");
  meta.append(link);
  if (d.licence_url) {
    meta.append(" · ", el("a", { href: d.licence_url, target: "_blank", rel: "noopener" }, "Lizenz"));
  }
  body.append(meta);
  const c = d.content;
  if (!c) {
    body.append(el("p", { class: "mb-0" }, "Der Beschreibungstext ist nicht frei lizenziert und wird hier nur zitiert und verlinkt."));
  } else {
    if (c.headline) body.append(el("p", { class: "fw-semibold" }, c.headline));
    if (c.summary) body.append(el("p", {}, c.summary));
    if (c.items?.length) {
      const ul = el("ul", { class: "small" });
      for (const it of c.items.slice(0, 40)) {
        ul.append(el("li", {}, [it.locus, it.author, it.title, it.incipit].filter(Boolean).join(" · ")));
      }
      body.append(el("h5", { class: "h6" }, "Inhalt"), ul);
    }
    if (c.history) body.append(el("h5", { class: "h6" }, "Geschichte"), el("p", { class: "small" }, c.history));
    if (c.fulltext) {
      const det = el("details", { class: "small" });
      det.append(el("summary", {}, "Volltext der Beschreibung"), el("p", {}, c.fulltext));
      body.append(det);
    }
  }
  box.append(body);
  return box;
}

export function renderManuscript(doc) {
  const root = el("div", { class: "manuscript-detail" });
  if (doc._local) {
    root.append(el("div", { class: "alert alert-warning small" },
      "Lokale Vollversion: enthält nicht frei lizenzierte HSP-Beschreibungen, nicht veröffentlichen."));
  }
  root.append(el("h3", { class: "h5" }, doc.label || doc.id));
  root.append(el("p", { class: "text-muted" },
    [doc.settlement, doc.repository, doc.shelfmark].filter(Boolean).join(", ") + (doc.provenance ? ` · ${doc.provenance}` : "")));
  if (doc.portal_url) {
    const p = el("p");
    p.append(el("a", { href: doc.portal_url, target: "_blank", rel: "noopener" }, "Handschriftenportal ↗"));
    root.append(p);
  }
  if (doc.hsp?.core) {
    const dl = el("dl", { class: "row small" });
    for (const [key, label] of CORE_LABELS) {
      let v = doc.hsp.core[key];
      if (Array.isArray(v)) v = v.join("; ");
      if (v) dl.append(el("dt", { class: "col-sm-3" }, label), el("dd", { class: "col-sm-9" }, v));
    }
    root.append(dl);
  }
  root.append(el("h4", { class: "h6 mt-3" }, `Briefe (${doc.letters.length})`));
  if (doc.letters.length) {
    const ul = el("ul", { class: "small" });
    for (const l of doc.letters) {
      const li = el("li");
      li.append(el("a", { href: `letters.html?q=${encodeURIComponent(l.id)}` }, l.id),
        ` · ${l.date || "o. D."} · ${l.sender || "?"} → ${l.recipient || "?"}`);
      ul.append(li);
    }
    root.append(ul);
  } else {
    root.append(el("p", { class: "small text-muted" }, "Noch in keinem ausgezeichneten Brief erwähnt."));
  }
  if (doc.descriptions.length) {
    root.append(el("h4", { class: "h6 mt-3" }, "Beschreibungen im Handschriftenportal"));
    for (const d of doc.descriptions) root.append(renderDescription(d));
  }
  const attribution = el("p", { class: "small text-muted" }, "Daten: ");
  attribution.append(
    el("a", { href: doc.attribution?.url || "https://handschriftenportal.de/", target: "_blank", rel: "noopener" }, "Handschriftenportal"),
    " (Momentaufnahme, s. „Stand“)");
  root.append(attribution);
  return root;
}

export async function initManuscriptsUI() {
  const input = document.getElementById("manuscripts-input");
  const results = document.getElementById("manuscripts-results");
  const detail = document.getElementById("manuscripts-detail");
  const status = document.getElementById("manuscripts-status");

  async function show(id) {
    status.textContent = "Lade …";
    try {
      detail.replaceChildren(renderManuscript(await getManuscript(id)));
      status.textContent = "";
      history.replaceState(null, "", `?ms=${encodeURIComponent(id)}`);
    } catch (err) {
      status.textContent = err.message;
    }
  }

  async function refresh() {
    const hits = await findManuscripts(input.value, 40);
    results.replaceChildren(...hits.map((m) => {
      const b = el("button", { type: "button", class: "list-group-item list-group-item-action" });
      b.append(el("strong", {}, m.label || m.id), ` · ${[m.settlement, m.shelfmark].filter(Boolean).join(", ")}`,
        m.n_letters ? ` · ${m.n_letters} Brief${m.n_letters > 1 ? "e" : ""}` : "");
      b.addEventListener("click", () => show(m.id));
      return b;
    }));
    status.textContent = hits.length ? "" : "Keine Treffer.";
  }

  input.addEventListener("input", refresh);
  await refresh();
  const wanted = new URLSearchParams(window.location.search).get("ms");
  if (wanted) await show(wanted);
}
