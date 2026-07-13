/**
 * Phase 7b.2: in-browser SPARQL console using Oxigraph-WASM (the `oxigraph` npm package's own
 * browser build - not bundled via jsdelivr's `+esm` since that would break the package's relative
 * fetch of its .wasm file; the package's native web.js already handles that correctly when served
 * from a CDN). Loads json/explore/edition.ttl (a synced copy of rdf/edition.ttl,
 * scripts/export_frontend.py) into an in-memory store on first use.
 *
 * Same Turtle dump that feeds the local Docker Oxigraph endpoint (scripts/load_oxigraph.py) - one
 * modelling, two runtimes, no drift. See tests/test_sparql_queries.md for the three smoke queries
 * this must reproduce identically.
 */

const EXAMPLE_QUERIES = {
  "Letters to a person (Pupikofer)": `PREFIX csvoc: <https://lod.academy/correspsearch/vocab/terms#>
SELECT ?letter WHERE {
  ?letter csvoc:hasCorrespAction ?action .
  ?action csvoc:hasParticipant <https://michaelscho.github.io/lassberg/person/lassberg-correspondent-0179> .
} LIMIT 20`,
  "Letters mentioning a place (Eppishausen)": `PREFIX csvoc: <https://lod.academy/correspsearch/vocab/terms#>
SELECT ?letter WHERE {
  ?letter csvoc:mentions <https://michaelscho.github.io/lassberg/place/lassberg-place-0043> .
} LIMIT 20`,
  "Letters per year": `PREFIX csvoc: <https://lod.academy/correspsearch/vocab/terms#>
SELECT ?year (COUNT(?letter) AS ?n) WHERE {
  ?letter csvoc:hasCorrespAction ?action .
  ?action csvoc:hasTimespan ?ts .
  ?ts csvoc:startsOn ?date .
  BIND(SUBSTR(STR(?date), 1, 4) AS ?year)
} GROUP BY ?year ORDER BY ?year`,
  "All persons with a GND link": `PREFIX csvoc: <https://lod.academy/correspsearch/vocab/terms#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?person ?label ?gnd WHERE {
  ?person a csvoc:Person ; rdfs:label ?label ; owl:sameAs ?gnd .
  FILTER(CONTAINS(STR(?gnd), "d-nb.info"))
} LIMIT 20`,
};

let store = null;

async function loadStore(onProgress) {
  if (store) return store;
  onProgress?.("Loading Oxigraph-WASM...");
  const oxigraph = await import("https://cdn.jsdelivr.net/npm/oxigraph@0.5.9/web.js");
  await oxigraph.default();
  onProgress?.("Loading edition.ttl...");
  const ttl = await (await fetch("../json/explore/edition.ttl")).text();
  store = new oxigraph.Store();
  store.load(ttl, { format: "text/turtle" });
  onProgress?.(`Ready (${store.size} triples).`);
  return store;
}

/**
 * Runs a SPARQL query against the edition store and returns plain rows
 * ([{var: value, ...}]) or a boolean for ASK queries. Used by the SPARQL console
 * below and as a tool by the GraphRAG agent (agent.js).
 */
export async function runSparql(query, { maxRows = 50, onProgress } = {}) {
  const s = await loadStore(onProgress);
  const result = s.query(query);
  if (typeof result === "boolean") return result;
  return result.slice(0, maxRows).map((binding) => {
    const row = {};
    for (const [k, v] of binding) row[k] = v?.value ?? String(v);
    return row;
  });
}

function renderResults(bindings, container) {
  if (!bindings || bindings.length === 0) {
    container.innerHTML = '<p class="status">No results.</p>';
    return;
  }
  const vars = [...bindings[0].keys()];
  const rows = bindings
    .map((b) => `<tr>${vars.map((v) => `<td>${b.get(v)?.value ?? ""}</td>`).join("")}</tr>`)
    .join("");
  container.innerHTML = `<table class="sparql-results"><thead><tr>${vars
    .map((v) => `<th>${v}</th>`)
    .join("")}</tr></thead><tbody>${rows}</tbody></table>`;
}

export function initSparqlUI() {
  const select = document.getElementById("sparql-examples");
  const textarea = document.getElementById("sparql-input");
  const form = document.getElementById("sparql-form");
  const status = document.getElementById("sparql-status");
  const results = document.getElementById("sparql-results");

  for (const name of Object.keys(EXAMPLE_QUERIES)) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    select.appendChild(opt);
  }
  select.addEventListener("change", () => {
    textarea.value = EXAMPLE_QUERIES[select.value] || "";
  });
  textarea.value = EXAMPLE_QUERIES[Object.keys(EXAMPLE_QUERIES)[0]];

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = textarea.value.trim();
    if (!query) return;
    try {
      const s = await loadStore((msg) => { status.textContent = msg; });
      const result = s.query(query);
      if (typeof result === "boolean") {
        status.textContent = `ASK result: ${result}`;
        results.innerHTML = "";
      } else {
        status.textContent = `${result.length} result(s).`;
        renderResults(result, results);
      }
    } catch (err) {
      status.textContent = `Error: ${err.message}`;
      console.error(err);
    }
  });
}
