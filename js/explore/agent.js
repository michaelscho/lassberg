/**
 * LLM-orchestrated GraphRAG: instead of a fixed retrieve-then-summarize pipeline, the LLM
 * itself formulates the queries - semantic (BGE-M3 embedding search), formal (SPARQL over the
 * edition RDF), and graph traversals - observes the results, iterates, and synthesizes a cited
 * answer. Runs entirely in the browser against the same static artifacts as the rest of the
 * Explore page; the only network calls are to the user's chosen LLM API (llm-providers.js).
 *
 * Protocol: provider-agnostic JSON actions (works with SAIA's open models as well as
 * Anthropic/OpenAI/Gemini, without three different native tool-calling wire formats).
 * Each assistant turn must be one JSON object: {"tool": name, "args": {...}} or
 * {"answer": "..."}; tool results are fed back as user messages. runAgent() is an async
 * generator so the UI can render each step as it happens - the visible tool trace is the
 * methodological documentation of how the answer was produced.
 */

import { search } from "./search.js";
import { neighbors, sharedMentions, correspondenceContext } from "./graph-core.js";
import { loadGraphIndex } from "./graphrag.js";
import { runSparql } from "./sparql.js";
import { chat } from "./llm-providers.js";

const MAX_STEPS = 8;
const MAX_TEXT_CHARS = 3000;

// --- tools -----------------------------------------------------------------------------------

const TOOLS = {
  lookup_entity: {
    doc: 'lookup_entity {"name": string} - resolve a person/place/work/letter name to IDs. Always use this first when the question names an entity.',
    required: ["name"],
    run: async ({ name }) => {
      const index = await loadGraphIndex();
      const q = String(name || "").toLowerCase();
      const matchAll = (needle) => {
        const starts = [];
        const contains = [];
        for (const [key, node] of index.nodesByKey) {
          const label = (node.attributes.label || key).toLowerCase();
          if (label.startsWith(needle) || key.toLowerCase() === needle) starts.push(node);
          else if (label.includes(needle)) contains.push(node);
          if (starts.length >= 8) break;
        }
        return [...starts, ...contains];
      };
      let hits = matchAll(q);
      if (hits.length === 0) {
        // fall back to individual words ("Kolmarer Liederhandschrift" -> "kolmarer", "liederhandschrift")
        for (const word of q.split(/\s+/).filter((w) => w.length > 3)) {
          hits = hits.concat(matchAll(word));
        }
      }
      const seen = new Set();
      const rows = hits.filter((n) => !seen.has(n.key) && seen.add(n.key)).slice(0, 8)
        .map((n) => ({ id: n.key, type: n.attributes.type, label: n.attributes.label }));
      return rows.length ? rows
        : "no match in the registers - the entity may not be linked yet; try semantic_search over the letter texts instead";
    },
  },

  semantic_search: {
    doc: 'semantic_search {"query": string, "top_k": number=8} - embedding search by MEANING over the 170 full-text letters (German queries work best). Use for thematic questions; it does NOT know names reliably.',
    required: ["query"],
    run: async ({ query, top_k }) => {
      const hits = await search(String(query), { topK: Math.min(Number(top_k) || 8, 15) });
      return hits.map((r) => ({
        id: r.id, score: Number(r.score.toFixed(3)), date: r.date,
        sender: r.sender, recipient: r.recipient, incipit: (r.incipit || "").slice(0, 160),
      }));
    },
  },

  get_letter: {
    doc: 'get_letter {"id": "lassberg-letter-XXXX"} - full metadata + text (truncated) of one letter, including the entities it mentions.',
    required: ["id"],
    run: async ({ id }) => {
      const index = await loadGraphIndex();
      const node = index.nodesByKey.get(String(id));
      if (!node || node.attributes.type !== "letter") return `unknown letter id: ${id}`;
      const a = node.attributes;
      const mentions = (index.outEdges.get(node.key) || [])
        .filter((e) => e.type === "MENTIONS")
        .map((e) => {
          const m = index.nodesByKey.get(e.target);
          return { id: e.target, type: m?.attributes?.type, label: m?.attributes?.label };
        })
        .slice(0, 25);
      return {
        id: node.key, date: a.date, status: a.publication_status,
        text: a.text ? a.text.slice(0, MAX_TEXT_CHARS) : "(no full text - register-only letter)",
        mentions,
      };
    },
  },

  graph_neighbors: {
    doc: 'graph_neighbors {"id": string} - direct knowledge-graph neighbours of a letter or entity (senders, recipients, mentions, mentioning letters).',
    required: ["id"],
    run: async ({ id }) => {
      const index = await loadGraphIndex();
      if (!index.nodesByKey.has(String(id))) return `unknown id: ${id}`;
      return neighbors(index, String(id)).slice(0, 30)
        .map((x) => ({ id: x.id, edge: x.type, type: x.node?.attributes?.type, label: x.node?.attributes?.label }));
    },
  },

  shared_mentions: {
    doc: 'shared_mentions {"letter_id": string, "min_shared": number=2} - letters sharing >= min_shared mentioned register entities with the given letter.',
    required: ["letter_id"],
    run: async ({ letter_id, min_shared }) => {
      const index = await loadGraphIndex();
      return sharedMentions(index, String(letter_id), Number(min_shared) || 2).slice(0, 15)
        .map((x) => ({ id: x.id, shared: x.sharedCount }));
    },
  },

  correspondence_context: {
    doc: 'correspondence_context {"letter_id": string, "window_days": number=90} - letters of the same sender/recipient pair within the time window.',
    required: ["letter_id"],
    run: async ({ letter_id, window_days }) => {
      const index = await loadGraphIndex();
      return correspondenceContext(index, String(letter_id), Number(window_days) || 90).slice(0, 20);
    },
  },

  sparql: {
    doc: 'sparql {"query": string} - SPARQL over the edition RDF (all 3,268 letters). Use for exact/structural questions: counts, letters per year, everything sent by X, all letters mentioning Y.',
    required: ["query"],
    run: async ({ query }) => {
      const rows = await runSparql(String(query), { maxRows: 40 });
      if (rows === true || rows === false) return { ask: rows };
      return rows.length ? rows : "empty result - check URIs and vocabulary against the examples in your instructions";
    },
  },
};

// --- system prompt ---------------------------------------------------------------------------

const SYSTEM_PROMPT = `You are the research agent of the digital edition of Joseph von Lassberg's correspondence (1770-1855). Corpus: 3,268 letters catalogued with full metadata; 170 of them with full text and linked entities. Every letter involves Lassberg himself - his ID is lassberg-correspondent-0373, so to find a correspondence you only need to query for the OTHER person's ID (never guess IDs; resolve them with lookup_entity). ID schemes: letters lassberg-letter-NNNN, persons lassberg-correspondent-NNNN, places lassberg-place-NNNN, works lassberg-literature-NNNN.

You answer questions by orchestrating tools over the edition's embeddings, knowledge graph, and RDF store. On EVERY turn reply with EXACTLY ONE JSON object and nothing else (no prose, no code fences):
  {"tool": "<name>", "args": {...}}   to call a tool
  {"answer": "<final answer>"}        when you can answer

Tools:
${Object.values(TOOLS).map((t) => "- " + t.doc).join("\n")}

SPARQL reference (endpoint holds the whole corpus):
PREFIX csvoc: <https://lod.academy/correspsearch/vocab/terms#>
PREFIX schema1: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
Entity URIs: <https://michaelscho.github.io/lassberg/letter/{letter-id}>, .../person/{person-id}, .../place/{place-id}, .../work/{work-id}
Letter properties: a csvoc:Letter ; schema1:dateCreated "YYYY-MM-DD" ; schema1:text "..." (only full-text letters) ; csvoc:mentions <entity-uri> ; csvoc:hasCorrespAction <letter-uri>/sent and <letter-uri>/received .
CorrespAction: <letter-uri>/sent a csvoc:Sent ; csvoc:hasParticipant <person-uri> ; csvoc:tookPlaceAt <place-uri> ; csvoc:hasTimespan ?ts . ?ts csvoc:startsOn ?date . (<letter-uri>/received likewise, a csvoc:Received.)
IMPORTANT: ?date is a typed xsd:date literal - always wrap in STR() for string ops: FILTER(STRSTARTS(STR(?date), "1830")).
Entities: rdfs:label "..." ; owl:sameAs <GND/Wikidata URI>.
Example - all letters sent by a person in 1830:
SELECT ?letter ?date WHERE { ?letter csvoc:hasCorrespAction ?a . ?a a csvoc:Sent ; csvoc:hasParticipant <https://michaelscho.github.io/lassberg/person/lassberg-correspondent-0179> ; csvoc:hasTimespan ?ts . ?ts csvoc:startsOn ?date . FILTER(STRSTARTS(STR(?date), "1830")) }

Method - combine BOTH evidence layers, that is the point of this system:
1. Resolve names with lookup_entity first (never guess IDs).
2. Structural skeleton via sparql (who, when, how many - covers all 3,268 letters).
3. Content evidence: for any question about topics, motives, or content, run semantic_search with your own thematic query (German) AND read the key letters with get_letter before making claims.
4. Widen context from good hits with shared_mentions / correspondence_context / graph_neighbors - these often surface related letters that neither search found.
An empty sparql result usually means a wrong URI or a filter on a typed literal without STR() - fix and retry once, don't repeat the same query. You have at most ${MAX_STEPS} tool calls - plan them.

Answer rules: cite every claim with letter IDs in square brackets, e.g. [lassberg-letter-0952]. Distinguish clearly between the 170 full-text letters and metadata-only evidence. If the sources do not answer the question, say so plainly. Answer in the language of the user's question.`;

// --- JSON action parsing -----------------------------------------------------------------------

/**
 * Normalizes model output quirks: args serialized as a JSON string, or tool arguments placed
 * at the top level instead of nested under "args" ({"tool": "sparql", "query": "..."}). Seen
 * in practice with smaller models - without this, tools ran with empty args and produced
 * garbage (semantic_search embedding the literal string "undefined").
 */
function normalizeAction(action) {
  if (!action || typeof action !== "object") return action;
  if (typeof action.args === "string") {
    try { action.args = JSON.parse(action.args); } catch { /* leave as-is; validation will catch it */ }
  }
  if (action.tool && (action.args === undefined || action.args === null)) {
    const extras = { ...action };
    delete extras.tool;
    delete extras.args;
    delete extras.answer;
    if (Object.keys(extras).length) action.args = extras;
  }
  return action;
}

function parseAction(text) {
  let t = String(text || "").trim();
  const fence = t.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fence) t = fence[1].trim();
  const start = t.indexOf("{");
  if (start === -1) return { answer: t }; // no JSON at all -> treat as answer
  // find the matching closing brace of the first object
  let depth = 0;
  let inStr = false;
  let esc = false;
  for (let i = start; i < t.length; i++) {
    const c = t[i];
    if (esc) { esc = false; continue; }
    if (c === "\\") { esc = true; continue; }
    if (c === '"') inStr = !inStr;
    if (inStr) continue;
    if (c === "{") depth++;
    if (c === "}") {
      depth--;
      if (depth === 0) {
        try {
          return JSON.parse(t.slice(start, i + 1));
        } catch {
          return { answer: t };
        }
      }
    }
  }
  return { answer: t };
}

// --- agent loop --------------------------------------------------------------------------------

/**
 * Runs one agent turn. history: [{role: "user"|"assistant", content}] of previous Q&A pairs.
 * Yields {type: "tool_call"|"tool_result"|"answer"|"error", ...} events as they happen.
 */
export async function* runAgent(question, history, llmConfig) {
  const messages = [
    { role: "system", content: SYSTEM_PROMPT },
    ...history,
    { role: "user", content: question },
  ];

  for (let step = 0; step <= MAX_STEPS; step++) {
    let reply;
    try {
      reply = await chat(messages, llmConfig);
    } catch (err) {
      yield { type: "error", message: err.message };
      return;
    }
    messages.push({ role: "assistant", content: reply });

    const action = normalizeAction(parseAction(reply));

    if (action.answer !== undefined || step === MAX_STEPS) {
      yield { type: "answer", text: action.answer ?? String(reply) };
      return;
    }

    const tool = TOOLS[action.tool];
    if (!tool) {
      messages.push({ role: "user", content: `TOOL ERROR: unknown tool "${action.tool}". Reply with one valid JSON action.` });
      continue;
    }

    const args = action.args && typeof action.args === "object" ? action.args : {};
    const missing = (tool.required || []).filter(
      (k) => args[k] === undefined || args[k] === null || String(args[k]).trim() === ""
    );
    if (missing.length) {
      // reject before running: a tool executed with missing args returns garbage, not an error
      messages.push({
        role: "user",
        content: `TOOL ERROR: ${action.tool} is missing required argument(s): ${missing.join(", ")}. Usage: ${tool.doc} Reply with one corrected JSON action.`,
      });
      continue;
    }

    yield { type: "tool_call", name: action.tool, args };
    let result;
    try {
      result = await tool.run(args);
    } catch (err) {
      result = `TOOL ERROR: ${err.message}`;
    }
    const serialized = typeof result === "string" ? result : JSON.stringify(result);
    yield { type: "tool_result", name: action.tool, preview: serialized.slice(0, 200), size: serialized.length };

    const stepsLeft = MAX_STEPS - step - 1;
    messages.push({
      role: "user",
      content: `TOOL RESULT (${action.tool}):\n${serialized.slice(0, 12000)}\n\n(${stepsLeft} tool calls left. Next: one JSON action, or {"answer": ...}.)`,
    });
  }
}
