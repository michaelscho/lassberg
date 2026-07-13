// Unit tests for js/explore/graph-core.js (Phase 7b.3 GraphRAG expansion functions), using a small
// fixture graph instead of the real corpus. Run with: node --test tests/test_graph_core.mjs
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  buildIndex,
  correspondenceContext,
  egoNetwork,
  neighbors,
  sharedMentions,
} from "../js/explore/graph-core.js";

// Fixture: 4 letters, 2 persons, 1 place, 1 work.
// - letter-A and letter-B: same correspondence (P1 -> P2), 10 days apart, share 2 mentions (W1, PL1)
// - letter-C: same correspondence, but 200 days after letter-A (outside a 90-day window)
// - letter-D: same correspondence but the *reply direction* (P2 -> P1, 31 days after letter-A) -
//   correspondenceContext matches a pair regardless of direction (per plan: "gleiches
//   Absender/Empfänger-Paar, beide Richtungen"), so it belongs together with A/B/C; it also
//   mentions W1 (1 shared mention with A/B, tested separately via sharedMentions).
const fixture = {
  nodes: [
    { key: "letter-A", attributes: { type: "letter", date: "1825-01-01" } },
    { key: "letter-B", attributes: { type: "letter", date: "1825-01-11" } },
    { key: "letter-C", attributes: { type: "letter", date: "1825-07-20" } },
    { key: "letter-D", attributes: { type: "letter", date: "1825-02-01" } },
    { key: "person-1", attributes: { type: "person", label: "P1" } },
    { key: "person-2", attributes: { type: "person", label: "P2" } },
    { key: "place-1", attributes: { type: "place", label: "PL1" } },
    { key: "work-1", attributes: { type: "work", label: "W1" } },
  ],
  edges: [
    { source: "letter-A", target: "person-1", attributes: { type: "SENT_BY" } },
    { source: "letter-A", target: "person-2", attributes: { type: "SENT_TO" } },
    { source: "letter-A", target: "work-1", attributes: { type: "MENTIONS" } },
    { source: "letter-A", target: "place-1", attributes: { type: "MENTIONS" } },

    { source: "letter-B", target: "person-1", attributes: { type: "SENT_BY" } },
    { source: "letter-B", target: "person-2", attributes: { type: "SENT_TO" } },
    { source: "letter-B", target: "work-1", attributes: { type: "MENTIONS" } },
    { source: "letter-B", target: "place-1", attributes: { type: "MENTIONS" } },

    { source: "letter-C", target: "person-1", attributes: { type: "SENT_BY" } },
    { source: "letter-C", target: "person-2", attributes: { type: "SENT_TO" } },

    { source: "letter-D", target: "person-2", attributes: { type: "SENT_BY" } },
    { source: "letter-D", target: "person-1", attributes: { type: "SENT_TO" } },
    { source: "letter-D", target: "work-1", attributes: { type: "MENTIONS" } },
  ],
};

test("neighbors returns directly connected entities with edge type", () => {
  const index = buildIndex(fixture);
  const result = neighbors(index, "letter-A");
  const ids = result.map((r) => r.id).sort();
  assert.deepEqual(ids, ["person-1", "person-2", "place-1", "work-1"]);
  const sentBy = result.find((r) => r.id === "person-1");
  assert.equal(sentBy.type, "SENT_BY");
});

test("sharedMentions finds letters with >= minShared overlapping mentions, excludes self", () => {
  const index = buildIndex(fixture);
  const result = sharedMentions(index, "letter-A", 2);
  assert.equal(result.length, 1);
  assert.equal(result[0].id, "letter-B");
  assert.equal(result[0].sharedCount, 2);
});

test("sharedMentions with minShared=1 also includes the single-overlap letter", () => {
  const index = buildIndex(fixture);
  const result = sharedMentions(index, "letter-A", 1);
  const ids = result.map((r) => r.id).sort();
  assert.deepEqual(ids, ["letter-B", "letter-D"]);
});

test("correspondenceContext finds same sender/recipient pair (either direction) within the time window", () => {
  const index = buildIndex(fixture);
  const result = correspondenceContext(index, "letter-A", 90);
  const ids = result.map((r) => r.id).sort();
  assert.deepEqual(ids, ["letter-B", "letter-D"]); // letter-C is 200 days out, excluded
});

test("correspondenceContext with a wider window includes the far letter too", () => {
  const index = buildIndex(fixture);
  const result = correspondenceContext(index, "letter-A", 250);
  const ids = result.map((r) => r.id).sort();
  assert.deepEqual(ids, ["letter-B", "letter-C", "letter-D"]);
});

test("egoNetwork at depth 1 includes only direct neighbors", () => {
  const index = buildIndex(fixture);
  const { nodes } = egoNetwork(index, "work-1", 1);
  const ids = nodes.map((n) => n.key).sort();
  // work-1 is mentioned by letter-A, letter-B, letter-D
  assert.deepEqual(ids, ["letter-A", "letter-B", "letter-D", "work-1"]);
});

test("egoNetwork at depth 2 expands one hop further (letters -> their other participants)", () => {
  const index = buildIndex(fixture);
  const { nodes } = egoNetwork(index, "work-1", 2);
  const ids = nodes.map((n) => n.key).sort();
  assert.deepEqual(
    ids,
    ["letter-A", "letter-B", "letter-D", "person-1", "person-2", "place-1", "work-1"]
  );
});
