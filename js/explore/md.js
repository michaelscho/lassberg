/**
 * Minimal, safe Markdown renderer for LLM output in the GraphRAG chat.
 *
 * Model output is untrusted, so this never feeds raw text to innerHTML: the whole input is
 * HTML-escaped first, and only a whitelist of our own tags is then injected (strong/em/code/
 * pre/lists/headings, http(s) links). Covers the Markdown that chat models actually emit -
 * bold, italics, inline code, fenced code, headings, ordered/unordered lists, paragraphs.
 *
 * Letter IDs (lassberg-letter-NNNN) are turned into links: to the letter page when one exists
 * (the caller passes the set of full-text letter IDs), otherwise into the letters register via
 * the ?q= deep link.
 */

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function renderInline(escaped, letterHref) {
  let s = escaped;
  s = s.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[\s(>])\*([^*\n]+)\*/g, "$1<em>$2</em>");
  s = s.replace(/(^|[\s(>])_([^_\n]+)_/g, "$1<em>$2</em>");
  // markdown links - http(s) targets only (everything else stays escaped text)
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  // letter IDs -> edition links (skip ones that already ended up inside an <a> from the step above)
  s = s.replace(/(lassberg-letter-\d{3,4})(?![^<]*<\/a>)/g,
    (id) => `<a href="${letterHref(id)}" target="_blank" rel="noopener">${id}</a>`);
  return s;
}

/** Renders markdown-ish text to a DOM element. letterPageIds: Set of IDs that have a page. */
export function renderMarkdown(text, letterPageIds = new Set()) {
  const letterHref = (id) =>
    letterPageIds.has(id) ? `letters/${id}.html` : `letters.html?q=${encodeURIComponent(id)}`;

  const lines = escapeHtml(String(text ?? "")).split("\n");
  const html = [];
  let list = null; // "ul" | "ol" | null
  let para = [];
  let inFence = false;
  let fence = [];

  const flushPara = () => {
    if (para.length) {
      html.push(`<p>${para.map((l) => renderInline(l, letterHref)).join("<br>")}</p>`);
      para = [];
    }
  };
  const flushList = () => {
    if (list) {
      html.push(`</${list}>`);
      list = null;
    }
  };

  for (const raw of lines) {
    const line = raw.trimEnd();

    if (line.trim().startsWith("```")) {
      flushPara(); flushList();
      if (inFence) {
        html.push(`<pre><code>${fence.join("\n")}</code></pre>`);
        fence = [];
      }
      inFence = !inFence;
      continue;
    }
    if (inFence) { fence.push(line); continue; }

    const heading = line.match(/^(#{1,4})\s+(.*)/);
    const bullet = line.match(/^\s*[-*•]\s+(.*)/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)/);

    if (heading) {
      flushPara(); flushList();
      html.push(`<h4>${renderInline(heading[2], letterHref)}</h4>`);
    } else if (bullet || numbered) {
      flushPara();
      const want = bullet ? "ul" : "ol";
      if (list !== want) { flushList(); html.push(`<${want}>`); list = want; }
      html.push(`<li>${renderInline((bullet || numbered)[1], letterHref)}</li>`);
    } else if (line.trim() === "") {
      flushPara(); flushList();
    } else {
      flushList();
      para.push(line);
    }
  }
  if (inFence && fence.length) html.push(`<pre><code>${fence.join("\n")}</code></pre>`);
  flushPara(); flushList();

  const el = document.createElement("div");
  el.className = "md";
  el.innerHTML = html.join(""); // safe: input fully escaped above, tags are our own whitelist
  return el;
}
