/**
 * Minimal multi-provider chat adapter for the GraphRAG agent (agent.js). One function,
 * chat(messages, config) -> assistant text, over four wire formats:
 *
 *   - "openai" kind: POST {endpoint}/chat/completions - used by SAIA (AcademicCloud),
 *     OpenAI, and any OpenAI-compatible endpoint (local proxies, vLLM, Ollama, ...)
 *   - "anthropic" kind: POST {endpoint}/v1/messages with the CORS opt-in header
 *     anthropic-dangerous-direct-browser-access (Anthropic supports browser calls with it)
 *   - "google" kind: POST {endpoint}/v1beta/models/{model}:generateContent?key=...
 *
 * Browser-CORS status (verified 2026-07-12): Anthropic, OpenAI, and Google Gemini accept
 * direct browser requests. SAIA sends Access-Control-Allow-Origin: * but answers the
 * preflight OPTIONS with 401, so direct calls fail until GWDG fixes that - the SAIA entry
 * stays selectable (it works the moment they fix it, or via a proxy URL in the endpoint
 * field), and the UI explains the failure.
 *
 * Keys are user-supplied and stored in localStorage only. Messages: [{role, content}] with
 * roles "system" | "user" | "assistant" (translated per provider).
 */

export const PROVIDERS = {
  saia: {
    label: "SAIA (AcademicCloud)",
    kind: "openai",
    endpoint: "https://chat-ai.academiccloud.de/v1",
    defaultModel: "llama-3.3-70b-instruct",
    note: "SAIA's API currently rejects browser preflight requests (CORS) - direct calls fail until that is fixed on their side, or use a proxy endpoint.",
  },
  anthropic: {
    label: "Anthropic",
    kind: "anthropic",
    endpoint: "https://api.anthropic.com",
    defaultModel: "claude-opus-4-8",
  },
  openai: {
    label: "OpenAI",
    kind: "openai",
    endpoint: "https://api.openai.com/v1",
    defaultModel: "gpt-4o",
  },
  google: {
    label: "Google Gemini",
    kind: "google",
    endpoint: "https://generativelanguage.googleapis.com",
    defaultModel: "gemini-2.5-flash",
  },
  custom: {
    label: "Custom (OpenAI-compatible)",
    kind: "openai",
    endpoint: "",
    defaultModel: "",
  },
};

async function chatOpenAi(messages, { endpoint, key, model }) {
  const resp = await fetch(`${endpoint.replace(/\/$/, "")}/chat/completions`, {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model, messages, temperature: 0.2 }),
  });
  if (!resp.ok) throw new Error(`API error ${resp.status}: ${(await resp.text()).slice(0, 300)}`);
  const data = await resp.json();
  return data.choices?.[0]?.message?.content ?? "";
}

async function chatAnthropic(messages, { endpoint, key, model }) {
  const system = messages.filter((m) => m.role === "system").map((m) => m.content).join("\n\n");
  const turns = messages.filter((m) => m.role !== "system");
  const resp = await fetch(`${endpoint.replace(/\/$/, "")}/v1/messages`, {
    method: "POST",
    headers: {
      "x-api-key": key,
      "anthropic-version": "2023-06-01",
      // explicit opt-in for direct browser access with a user-supplied key
      "anthropic-dangerous-direct-browser-access": "true",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ model, max_tokens: 4096, system, messages: turns }),
  });
  if (!resp.ok) throw new Error(`API error ${resp.status}: ${(await resp.text()).slice(0, 300)}`);
  const data = await resp.json();
  if (data.stop_reason === "refusal") throw new Error("The model declined this request (refusal).");
  return (data.content || []).filter((b) => b.type === "text").map((b) => b.text).join("");
}

async function chatGoogle(messages, { endpoint, key, model }) {
  const system = messages.filter((m) => m.role === "system").map((m) => m.content).join("\n\n");
  const contents = messages
    .filter((m) => m.role !== "system")
    .map((m) => ({ role: m.role === "assistant" ? "model" : "user", parts: [{ text: m.content }] }));
  const url = `${endpoint.replace(/\/$/, "")}/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(key)}`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      systemInstruction: system ? { parts: [{ text: system }] } : undefined,
      contents,
      generationConfig: { temperature: 0.2 },
    }),
  });
  if (!resp.ok) throw new Error(`API error ${resp.status}: ${(await resp.text()).slice(0, 300)}`);
  const data = await resp.json();
  return (data.candidates?.[0]?.content?.parts || []).map((p) => p.text || "").join("");
}

/** Sends a chat and returns the assistant's text. config: {provider, endpoint, key, model}. */
export async function chat(messages, config) {
  const kind = PROVIDERS[config.provider]?.kind ?? "openai";
  if (kind === "anthropic") return chatAnthropic(messages, config);
  if (kind === "google") return chatGoogle(messages, config);
  return chatOpenAi(messages, config);
}

/**
 * Lists the models actually available for the given key, so users never have to guess model
 * IDs (a wrong ID is a 404). Returns an array of ID strings. All three provider list
 * endpoints accept direct browser calls (verified 2026-07-12).
 */
export async function listModels({ provider, endpoint, key }) {
  const kind = PROVIDERS[provider]?.kind ?? "openai";
  const base = endpoint.replace(/\/$/, "");

  if (kind === "google") {
    const resp = await fetch(`${base}/v1beta/models?pageSize=100&key=${encodeURIComponent(key)}`);
    if (!resp.ok) throw new Error(`API error ${resp.status}: ${(await resp.text()).slice(0, 200)}`);
    const data = await resp.json();
    return (data.models || [])
      .filter((m) => (m.supportedGenerationMethods || []).includes("generateContent"))
      .map((m) => m.name.replace(/^models\//, ""))
      .sort();
  }

  if (kind === "anthropic") {
    const resp = await fetch(`${base}/v1/models?limit=100`, {
      headers: {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true",
      },
    });
    if (!resp.ok) throw new Error(`API error ${resp.status}: ${(await resp.text()).slice(0, 200)}`);
    const data = await resp.json();
    return (data.data || []).map((m) => m.id).sort();
  }

  // OpenAI-compatible. SAIA's docs specify POST /v1/models, so fall back to POST if GET fails.
  const headers = { Authorization: `Bearer ${key}` };
  let resp = await fetch(`${base}/models`, { headers });
  if (!resp.ok && resp.status !== 401 && resp.status !== 403) {
    resp = await fetch(`${base}/models`, { method: "POST", headers });
  }
  if (!resp.ok) throw new Error(`API error ${resp.status}: ${(await resp.text()).slice(0, 200)}`);
  const data = await resp.json();
  return (data.data || []).map((m) => m.id).sort();
}
