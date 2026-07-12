#!/usr/bin/env python3
"""
Phase 5 of the KI-Infrastruktur pipeline: exports the JSON intermediate layer as RDF/Turtle
(`rdf/edition.ttl`) using the correspSearch/CMIF vocabulary, and optionally a classic CMIF-TEI
dump (`rdf/cmif.xml`) for correspSearch submission.

--- Vocabulary choice (verified 2026-07-11, per plan instruction not to invent one) ---
correspSearch itself does NOT publish a plain schema:sender/schema:recipient mapping - its actual
RDF output (via lod.academy, converted from CMIF) uses a small reified-event vocabulary at
https://lod.academy/correspsearch/vocab/terms# ("csvoc"): a Letter hasCorrespAction a
Sent/Received correspAction, which hasParticipant an Actor (Person/Institution/Group), tookPlaceAt
a Place, and hasTimespan a Day/Timespan with startsOn/endsOn. csvoc also already defines
`mentions` directly on Letter, so no separate schema.org term is needed for that. schema.org
covers what csvoc doesn't: geo-coordinates, literary works/witnesses, and the extended entity
metadata added 2026-07-11 (gender, occupation, author/pubPlace relationships, ...). A handful of
fields have no fitting standard term at all (person_type contemporary/historical, lit_type, ana,
witness_type/settlement/repository) - those get a small project-local vocabulary under
`<base_uri>vocab/` rather than being force-fit into schema.org/csvoc or dropped.

RDF model (extended 2026-07-11 to match scripts/lib_pipeline.py's entity property builders, shared
with export_cypher.py/export_graph_json.py so all three runtimes carry the same metadata):
  <letter/ID>            a csvoc:Letter ; rdfs:label ; csvoc:hasCorrespAction <letter/ID/sent|received> ;
                          csvoc:mentions <person|place|work|witness/ID> .
  <letter/ID/sent>       a csvoc:correspAction, csvoc:Sent ;
                          csvoc:hasParticipant <person/ID> ; csvoc:tookPlaceAt <place/ID> ;
                          csvoc:hasTimespan <letter/ID/sent/date> .
  <letter/ID/sent/date>  a csvoc:Day|csvoc:ApproxTimespan ; csvoc:startsOn "..."^^xsd:date|gYearMonth|gYear .
  <letter/ID/received>   a csvoc:correspAction, csvoc:Received ; csvoc:hasParticipant <person/ID> .
  <person/ID>            a csvoc:Person|csvoc:Institution|csvoc:Group ; rdfs:label ;
                          owl:sameAs <gnd-or-wikidata> ; rdfs:seeAlso <other-url> ;
                          schema:gender ; schema:jobTitle* (occupation) ; schema:birthDate ;
                          schema:deathDate ; voc:personType ; voc:education* .
  <place/ID>              a csvoc:Place ; rdfs:label ; owl:sameAs <wikidata> ; rdfs:seeAlso <other-url> ;
                          schema:description ; schema:geo [ schema:latitude; schema:longitude ] .
  <work/ID>               a schema:CreativeWork ; rdfs:label ; voc:litType ; voc:ana ;
                          schema:dateCreated ; dcterms:identifier* (idno) ;
                          schema:author <person/ID>|Literal ; schema:locationCreated <place/ID>|Literal .
  <witness/ID>            a schema:CreativeWork ; rdfs:label ; schema:exampleOfWork <work/ID> ;
                          voc:witnessType ; voc:settlement ; voc:repository ; dcterms:identifier (signature) ;
                          schema:description (note) .

Letter resources additionally carry flat literal properties (not just the reified correspAction
structure above) for easy SPARQL access: schema:dateCreated, schema:abstract (incipit),
schema:text (full text, full-text letters only), schema:inLanguage, voc:publicationStatus
(in_register|in_oxygen_done|online, from the register's @change), voc:reviewStatus (raw|reviewed|
register-only), voc:hasFulltext, voc:harrisNumber, voc:journalNumber, voc:repositoryPlace,
voc:repositoryInstitution, dcterms:identifier (archival signature), dcterms:bibliographicCitation
+ dcterms:source (the "published in" citation text + its URL), rdfs:comment, voc:facsimileUrl,
voc:iiifManifest, voc:iiifCanvas - see add_letter_metadata() and parse_tei.py:parse_register_notes
for the source fields (only populated from the overall register, lassberg-letters.xml).

The SENT_FROM place-under-received corpus quirk (see lib_pipeline.effective_sent_place) applies
here too: tookPlaceAt on the Sent correspAction uses the resolved place, not the raw sent.place.

Usage:
    python scripts/export_rdf.py [--repo-root PATH] [--cmif]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from rdflib.namespace import DCTERMS, OWL

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_pipeline import (  # noqa: E402
    effective_sent_place,
    entity_relationships,
    label_for_id,
    load_config,
    load_entities,
    load_letters,
)

CSVOC = Namespace("https://lod.academy/correspsearch/vocab/terms#")
SCHEMA = Namespace("http://schema.org/")

# Entity kind -> RDF path segment, matching entity_relationships()'s Neo4j-label naming.
KIND_BY_LABEL = {"Person": "person", "Place": "place", "Work": "work", "Witness": "witness"}
# Relationship type (from lib_pipeline.entity_relationships) -> RDF predicate.
RELATIONSHIP_PREDICATES = {
    "AUTHORED_BY": SCHEMA.author,
    "PUBLISHED_AT": SCHEMA.locationCreated,
    "WITNESS_OF": SCHEMA.exampleOfWork,
}


def entity_uri(base: Namespace, kind: str, entity_id: str) -> URIRef:
    return base[f"{kind}/{entity_id}"]


def add_entities(g: Graph, base: Namespace, voc: Namespace, entities: dict):
    for eid, ent in entities["persons"].items():
        uri = entity_uri(base, "person", eid)
        if ent["corporate_body"]:
            rdf_type = CSVOC.Institution
        elif ent["kind"] == "personGrp":
            rdf_type = CSVOC.Group
        else:
            rdf_type = CSVOC.Person
        g.add((uri, RDF.type, rdf_type))
        g.add((uri, RDFS.label, Literal(ent["label"])))
        gnd = ent["normdaten"].get("gnd")
        wikidata = ent["normdaten"].get("wikidata")
        other = ent["normdaten"].get("other")
        if gnd:
            g.add((uri, OWL.sameAs, URIRef(gnd)))
        if wikidata:
            g.add((uri, OWL.sameAs, URIRef(wikidata)))
        if other:
            g.add((uri, RDFS.seeAlso, URIRef(other)))
        if ent.get("person_type"):
            g.add((uri, voc.personType, Literal(ent["person_type"])))
        if ent.get("gender"):
            g.add((uri, SCHEMA.gender, Literal(ent["gender"])))
        for occupation in ent.get("occupation") or []:
            g.add((uri, SCHEMA.jobTitle, Literal(occupation)))
        for education in ent.get("education") or []:
            g.add((uri, voc.education, Literal(education)))
        if ent.get("birth"):
            g.add((uri, SCHEMA.birthDate, Literal(ent["birth"])))
        if ent.get("death"):
            g.add((uri, SCHEMA.deathDate, Literal(ent["death"])))

    for eid, ent in entities["places"].items():
        uri = entity_uri(base, "place", eid)
        g.add((uri, RDF.type, CSVOC.Place))
        g.add((uri, RDFS.label, Literal(ent["label"])))
        wikidata = ent["normdaten"].get("wikidata")
        gnd = ent["normdaten"].get("gnd")
        other = ent["normdaten"].get("other")
        if wikidata:
            g.add((uri, OWL.sameAs, URIRef(wikidata)))
        if gnd:
            g.add((uri, OWL.sameAs, URIRef(gnd)))
        if other:
            g.add((uri, RDFS.seeAlso, URIRef(other)))
        if ent.get("desc"):
            g.add((uri, SCHEMA.description, Literal(ent["desc"])))
        if ent["coords"]:
            geo = BNode()
            g.add((uri, SCHEMA.geo, geo))
            g.add((geo, RDF.type, SCHEMA.GeoCoordinates))
            g.add((geo, SCHEMA.latitude, Literal(ent["coords"]["lat"])))
            g.add((geo, SCHEMA.longitude, Literal(ent["coords"]["lon"])))

    for eid, ent in entities["works"].items():
        uri = entity_uri(base, "work", eid)
        g.add((uri, RDF.type, SCHEMA.CreativeWork))
        g.add((uri, RDFS.label, Literal(ent["label"])))
        if ent.get("lit_type"):
            g.add((uri, voc.litType, Literal(ent["lit_type"])))
        if ent.get("ana"):
            g.add((uri, voc.ana, Literal(ent["ana"])))
        if ent.get("date"):
            g.add((uri, SCHEMA.dateCreated, Literal(ent["date"])))
        for idno in ent.get("idno") or []:
            if idno.get("type") and idno.get("value"):
                g.add((uri, DCTERMS.identifier, Literal(f"{idno['type']}:{idno['value']}")))
        # AUTHORED_BY/PUBLISHED_AT relationships added below via entity_relationships(); the
        # free-text label fallback (no linked register id) is added here since it's a plain
        # literal, not a relationship.
        author = ent.get("author")
        if author and not author.get("key") and author.get("label"):
            g.add((uri, SCHEMA.author, Literal(author["label"])))
        pub_place = ent.get("pub_place")
        if pub_place and not pub_place.get("key") and pub_place.get("label"):
            g.add((uri, SCHEMA.locationCreated, Literal(pub_place["label"])))

    for eid, ent in entities["witnesses"].items():
        uri = entity_uri(base, "witness", eid)
        g.add((uri, RDF.type, SCHEMA.CreativeWork))
        label = ent["label"] or ent["repository"] or ent["signature"] or eid
        g.add((uri, RDFS.label, Literal(label)))
        if ent.get("witness_type"):
            g.add((uri, voc.witnessType, Literal(ent["witness_type"])))
        if ent.get("settlement"):
            g.add((uri, voc.settlement, Literal(ent["settlement"])))
        if ent.get("repository"):
            g.add((uri, voc.repository, Literal(ent["repository"])))
        if ent.get("signature"):
            g.add((uri, DCTERMS.identifier, Literal(ent["signature"])))
        if ent.get("note"):
            g.add((uri, SCHEMA.description, Literal(ent["note"])))
        # WITNESS_OF (schema:exampleOfWork) is added below via entity_relationships().


def add_entity_relationships(g: Graph, base: Namespace, entities: dict):
    """AUTHORED_BY/PUBLISHED_AT/WITNESS_OF - same underlying data as the Neo4j export
    (lib_pipeline.entity_relationships), mapped to schema.org predicates here."""
    for rel in entity_relationships(entities):
        predicate = RELATIONSHIP_PREDICATES[rel["type"]]
        source_kind = KIND_BY_LABEL[label_for_id(rel["source"])]
        target_kind = KIND_BY_LABEL[label_for_id(rel["target"])]
        g.add((
            entity_uri(base, source_kind, rel["source"]),
            predicate,
            entity_uri(base, target_kind, rel["target"]),
        ))


def date_literal(when: str, precision: str):
    if precision == "day":
        return Literal(when, datatype=XSD.date)
    if precision == "month":
        return Literal(when, datatype=XSD.gYearMonth)
    if precision == "year":
        return Literal(when, datatype=XSD.gYear)
    return Literal(when)


def add_letter_metadata(g: Graph, base: Namespace, voc: Namespace, letter: dict):
    """Flat literal properties on the letter resource itself - date/text/incipit are also
    reachable via the reified csvoc:hasCorrespAction/hasTimespan structure, but a flat
    schema:dateCreated/schema:text lets simple SPARQL queries skip that traversal. register_meta
    fields (harris_number, signature, published_in, IIIF links, ...) only exist in the overall
    register (lassberg-letters.xml) - see parse_tei.py:parse_register_notes."""
    letter_uri = entity_uri(base, "letter", letter["id"])
    date = letter["sent"]["date"] or letter["received"]["date"]
    if date:
        g.add((letter_uri, SCHEMA.dateCreated, Literal(date)))
    if letter.get("incipit"):
        g.add((letter_uri, SCHEMA.abstract, Literal(letter["incipit"])))
    if letter.get("text"):
        g.add((letter_uri, SCHEMA.text, Literal(letter["text"])))
    if letter.get("lang"):
        g.add((letter_uri, SCHEMA.inLanguage, Literal(letter["lang"])))
    if letter.get("publication_status"):
        g.add((letter_uri, voc.publicationStatus, Literal(letter["publication_status"])))
    if letter.get("status"):
        g.add((letter_uri, voc.reviewStatus, Literal(letter["status"])))
    g.add((letter_uri, voc.hasFulltext, Literal(letter["has_fulltext"])))

    meta = letter.get("register_meta") or {}
    if meta.get("harris_number"):
        g.add((letter_uri, voc.harrisNumber, Literal(meta["harris_number"])))
    if meta.get("journal_number"):
        g.add((letter_uri, voc.journalNumber, Literal(meta["journal_number"])))
    if meta.get("repository_place"):
        g.add((letter_uri, voc.repositoryPlace, Literal(meta["repository_place"])))
    if meta.get("repository_institution"):
        g.add((letter_uri, voc.repositoryInstitution, Literal(meta["repository_institution"])))
    if meta.get("signature"):
        g.add((letter_uri, DCTERMS.identifier, Literal(meta["signature"])))
    if meta.get("published_in"):
        g.add((letter_uri, DCTERMS.bibliographicCitation, Literal(meta["published_in"])))
    if meta.get("published_in_url"):
        g.add((letter_uri, DCTERMS.source, URIRef(meta["published_in_url"])))
    if meta.get("comment"):
        g.add((letter_uri, RDFS.comment, Literal(meta["comment"])))
    if meta.get("facsimile_url"):
        g.add((letter_uri, voc.facsimileUrl, URIRef(meta["facsimile_url"])))
    if meta.get("iiif_manifest"):
        g.add((letter_uri, voc.iiifManifest, URIRef(meta["iiif_manifest"])))
    if meta.get("iiif_canvas"):
        g.add((letter_uri, voc.iiifCanvas, URIRef(meta["iiif_canvas"])))


def add_letters(g: Graph, base: Namespace, voc: Namespace, letters: list[dict]):
    label_map = {"persons": "person", "places": "place", "works": "work", "witnesses": "witness"}
    for letter in letters:
        letter_uri = entity_uri(base, "letter", letter["id"])
        g.add((letter_uri, RDF.type, CSVOC.Letter))
        g.add((letter_uri, RDFS.label, Literal(letter["id"])))
        add_letter_metadata(g, base, voc, letter)

        sent = letter["sent"]
        received = letter["received"]
        place = effective_sent_place(letter)

        if sent["person"] or place or sent["date"]:
            sent_uri = URIRef(f"{letter_uri}/sent")
            g.add((letter_uri, CSVOC.hasCorrespAction, sent_uri))
            g.add((sent_uri, RDF.type, CSVOC.correspAction))
            g.add((sent_uri, RDF.type, CSVOC.Sent))
            if sent["person"]:
                g.add((sent_uri, CSVOC.hasParticipant, entity_uri(base, "person", sent["person"])))
            if place:
                g.add((sent_uri, CSVOC.tookPlaceAt, entity_uri(base, "place", place)))
            if sent["date"]:
                date_uri = URIRef(f"{sent_uri}/date")
                g.add((sent_uri, CSVOC.hasTimespan, date_uri))
                g.add((date_uri, RDF.type, CSVOC.Day if sent["date_precision"] == "day" else CSVOC.ApproxTimespan))
                g.add((date_uri, CSVOC.startsOn, date_literal(sent["date"], sent["date_precision"])))

        if received["person"]:
            recv_uri = URIRef(f"{letter_uri}/received")
            g.add((letter_uri, CSVOC.hasCorrespAction, recv_uri))
            g.add((recv_uri, RDF.type, CSVOC.correspAction))
            g.add((recv_uri, RDF.type, CSVOC.Received))
            g.add((recv_uri, CSVOC.hasParticipant, entity_uri(base, "person", received["person"])))

        for bucket, kind in label_map.items():
            for eid in letter["mentions"][bucket]:
                g.add((letter_uri, CSVOC.mentions, entity_uri(base, kind, eid)))


def write_cmif_xml(repo_root: Path, base: Namespace, letters: list[dict], entities: dict):
    """Classic TEI-CMIF export, superseding data/register/register_cmif_output.xml (kept as-is,
    not deleted - see README "superseded by" note)."""
    from lxml import etree

    persons = entities["persons"]
    places = entities["places"]

    TEI_NS = "http://www.tei-c.org/ns/1.0"
    nsmap = {None: TEI_NS}
    root = etree.Element("TEI", nsmap=nsmap)
    header = etree.SubElement(root, "teiHeader")
    file_desc = etree.SubElement(header, "fileDesc")
    title_stmt = etree.SubElement(file_desc, "titleStmt")
    etree.SubElement(title_stmt, "title").text = "Laßberg Letters - CMIF export"
    profile_desc = etree.SubElement(header, "profileDesc")

    for letter in letters:
        cd = etree.SubElement(profile_desc, "correspDesc")
        cd.set("key", letter["id"])
        cd.set("ref", f"{base}letter/{letter['id']}")

        sent = letter["sent"]
        place = effective_sent_place(letter)
        sent_action = etree.SubElement(cd, "correspAction")
        sent_action.set("type", "sent")
        if sent["person"] and sent["person"] in persons:
            pn = etree.SubElement(sent_action, "persName")
            pn.set("key", sent["person"])
            gnd = persons[sent["person"]]["normdaten"].get("gnd")
            if gnd:
                pn.set("ref", gnd)
            pn.text = persons[sent["person"]]["label"]
        if place and place in places:
            pl = etree.SubElement(sent_action, "placeName")
            pl.set("key", place)
            pl.text = places[place]["label"]
        if sent["date"]:
            etree.SubElement(sent_action, "date", when=sent["date"]).text = sent["date"]

        received = letter["received"]
        if received["person"]:
            recv_action = etree.SubElement(cd, "correspAction")
            recv_action.set("type", "received")
            if received["person"] in persons:
                pn = etree.SubElement(recv_action, "persName")
                pn.set("key", received["person"])
                gnd = persons[received["person"]]["normdaten"].get("gnd")
                if gnd:
                    pn.set("ref", gnd)
                pn.text = persons[received["person"]]["label"]

    tree = etree.ElementTree(root)
    out_path = repo_root / "rdf" / "cmif.xml"
    tree.write(str(out_path), pretty_print=True, xml_declaration=True, encoding="UTF-8")
    print(f"Wrote {out_path} ({len(letters)} correspDesc entries)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--cmif", action="store_true", help="also write rdf/cmif.xml")
    args = parser.parse_args()

    repo_root: Path = args.repo_root
    config = load_config(repo_root)
    base = Namespace(config["rdf"]["base_uri"])
    voc = Namespace(f"{config['rdf']['base_uri']}vocab/")

    entities = load_entities(repo_root)
    letters = load_letters(repo_root)

    g = Graph()
    g.bind("csvoc", CSVOC)
    g.bind("schema", SCHEMA)
    g.bind("dcterms", DCTERMS)
    g.bind("lassberg", base)
    g.bind("voc", voc)

    add_entities(g, base, voc, entities)
    add_entity_relationships(g, base, entities)
    add_letters(g, base, voc, letters)

    rdf_dir = repo_root / "rdf"
    rdf_dir.mkdir(exist_ok=True)
    out_path = rdf_dir / "edition.ttl"
    g.serialize(destination=str(out_path), format="turtle")
    print(f"Wrote {out_path}: {len(g)} triples")

    # Round-trip parse check (acceptance criterion: edition.ttl parses error-free)
    check = Graph()
    check.parse(str(out_path), format="turtle")
    assert len(check) == len(g), "round-trip triple count mismatch"
    print(f"Round-trip parse OK: {len(check)} triples")

    if args.cmif:
        write_cmif_xml(repo_root, base, letters, entities)


if __name__ == "__main__":
    main()
