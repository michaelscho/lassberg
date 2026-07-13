# ONNX vs. server consistency test (Phase 7, mandatory pre-deployment gate)

Verifies that the browser-side BGE-M3 embedding path (Transformers.js, q8, `Xenova/bge-m3`, CLS
pooling + normalization - `js/explore/search.js`) stays close enough to the server-side path
(FlagEmbedding, `BAAI/bge-m3` - `scripts/embed.py`) that search results don't silently diverge
between the MCP tool and the deployed website.

## Method

`scripts/test_onnx_consistency.mjs` embeds the same 20 test queries used in
`scripts/export_frontend.py`'s matryoshka validation with the q8 ONNX model, retrieves the top-10
letters against the deployed corpus vectors (`json/explore/vectors_int8.bin`), and compares
against the top-10 retrieved by the server-side FlagEmbedding model for the same queries
(precomputed once into `/tmp/server_rankings.json` - see the one-off Python snippet below,
not checked in since it's just an intermediate scratch file).

```bash
# one-off: generate the server-side reference rankings (requires .venv-infra)
python3 -c "
import json, sys
sys.path.insert(0, 'scripts')
from export_frontend import TEST_QUERIES
from FlagEmbedding import BGEM3FlagModel
import numpy as np
from safetensors.numpy import load_file

model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=False)
ids = json.loads(open('embeddings/bge-m3/ids.json').read())
matrix = load_file('embeddings/bge-m3/letters.safetensors')['embeddings'].astype(np.float32)
results = {}
for q in TEST_QUERIES:
    vec = model.encode([q], return_dense=True, return_sparse=False, return_colbert_vecs=False)['dense_vecs'][0]
    vec = np.asarray(vec, dtype=np.float32); vec /= np.linalg.norm(vec)
    scores = matrix @ vec
    results[q] = [ids[i] for i in np.argsort(scores)[::-1][:10]]
json.dump(results, open('/tmp/server_rankings.json', 'w'))
"

# then, from scripts/ (needs @huggingface/transformers + onnxruntime-node, see scripts/package.json):
node scripts/test_onnx_consistency.mjs
```

## Result (2026-07-11)

**Average top-10 overlap: 90.5%** (20/20 queries, individual overlaps ranged 80-100%) - above the
plan's 90% bar, so **q8 stays the primary browser quantization**; the HF-API fallback remains
available in the UI for users who prefer not to download the ~560MB model, but isn't required for
consistency reasons.

Recorded in `json/explore/vectors_meta.json` under `onnx_consistency_test` (written
automatically by `scripts/test_onnx_consistency.mjs` on each run).

## Separate live cross-check: MCP tool vs. browser, identical query

As an additional sanity check (not the formal 20-query gate above, but a real end-to-end check of
the actual deployed UI), the same query string was run through both paths:

Query: `"Handschrift des Tristan"`

| Rank | `mcp_server` (`semantic_search`, FlagEmbedding) | Browser (`js/explore/search.js`, Transformers.js q8) |
|---|---|---|
| 1 | lassberg-letter-1247 (0.4884) | lassberg-letter-1247 (0.481) |
| 2 | lassberg-letter-1231 (0.4707) | lassberg-letter-1231 (0.462) |
| 3 | lassberg-letter-1222 (0.4645) | lassberg-letter-1222 (0.457) |
| 4 | lassberg-letter-1369 (0.4628) | lassberg-letter-1369 (0.453) |
| 5 | lassberg-letter-1455 (0.4556) | lassberg-letter-1323 (0.449) |

Top-5 overlap: 4/5 - meets the plan's acceptance bar ("Top-5-Overlap >= 4"), tested via a real
headless-browser run against `html/explore.html` served statically (`python -m http.server`).
