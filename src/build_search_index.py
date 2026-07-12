"""
Builds json/search_index.json for the MiniSearch-powered search box shared by the three register
pages (html/letters.html, html/persons.html, html/places.html).

Walks data/register/lassberg-letters.xml (the master letter register) plus, where available,
the individual data/letters/*.xml files (for summary/transcription text and mentioned-entity
names) and the three content registers (persons/places/literature) plus the manuscripts
register, emitting one flat JSON array of records:

    {"kind": "letter"|"person"|"place"|"literature"|"manuscript",
     "id": "...", "title": "...", "date": "...", "text": "...", "url": "...", "external": "..."}

`kind` and `id` let the frontend build a stable per-record key; `text` is the blob MiniSearch
indexes. Every record has a real, navigable `url` (js/search.js just does
`window.location.href = url`, no page-specific fallback logic needed). URLs are relative to the
html/ directory, since that's where all three consumer pages (letters.html, persons.html,
places.html) live:
- published letters -> their own page (letters/<id>.html)
- unpublished letters -> letters.html?q=<id>, which js/letters.js picks up on load and
  pre-filters the table to
- persons/places -> their own register page, deep-linked the same way
  (persons.html?q=<name> / places.html?q=<name>)
- literature/manuscripts -> letters.html?q=<title>, since there's no dedicated register page
  for them yet
`external` is an optional GND/Wikidata/idno link shown as "more info" for register entries.

Usage: python3 src/build_search_index.py [--out json/search_index.json]
"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import quote

from lxml import etree

NS = {"t": "http://www.tei-c.org/ns/1.0"}
REPO_ROOT = Path(__file__).resolve().parent.parent


def text_of(el):
    return " ".join(el.itertext()).strip() if el is not None else ""


def strip_tags_text(el):
    if el is None:
        return ""
    return re.sub(r"\s+", " ", " ".join(el.itertext())).strip()


def load_letters_register():
    tree = etree.parse(str(REPO_ROOT / "data/register/lassberg-letters.xml"))
    return tree.findall(".//t:correspDesc", NS)


def load_letter_file(letter_id):
    path = REPO_ROOT / "data/letters" / f"{letter_id}.xml"
    if not path.exists():
        return None
    try:
        return etree.parse(str(path))
    except etree.XMLSyntaxError:
        return None


def build_letter_records():
    records = []
    for cd in load_letters_register():
        letter_id = cd.get("key")
        if not letter_id:
            continue
        sent = cd.find('t:correspAction[@type="sent"]', NS)
        received = cd.find('t:correspAction[@type="received"]', NS)
        sender = text_of(sent.find("t:persName", NS)) if sent is not None else ""
        recipient = text_of(received.find("t:persName", NS)) if received is not None else ""
        place = text_of(sent.find("t:placeName", NS)) if sent is not None else ""
        date = ""
        if sent is not None:
            date_el = sent.find("t:date", NS)
            if date_el is not None:
                date = date_el.get("when") or text_of(date_el)

        online = cd.get("change") == "online"
        url = f"letters/{letter_id}.html" if online else f"letters.html?q={quote(letter_id)}"

        summary_text = ""
        transcription_text = ""
        mentioned_names = []

        letter_doc = load_letter_file(letter_id)
        if letter_doc is not None:
            summary_div = letter_doc.find('.//t:div[@type="summary"]', NS)
            summary_text = strip_tags_text(summary_div)

            transcription_div = letter_doc.find('.//t:div[@type="original"]', NS)
            if transcription_div is None:
                transcription_div = letter_doc.find('.//t:div[@type="print"]', NS)
            transcription_text = strip_tags_text(transcription_div)

            for ref in letter_doc.findall('.//t:note[@type="mentioned"]/t:ref', NS):
                rs = ref.find("t:rs", NS)
                if rs is not None and rs.text:
                    mentioned_names.append(rs.text.strip())

        text_blob = " ".join(
            filter(None, [sender, recipient, place, date, summary_text, transcription_text, " ".join(mentioned_names)])
        )

        title = f"{sender} → {recipient}" + (f" ({date})" if date else "")

        records.append({
            "kind": "letter",
            "id": letter_id,
            "title": title,
            "date": date,
            "text": text_blob,
            "url": url,
        })
    return records


def build_person_records():
    tree = etree.parse(str(REPO_ROOT / "data/register/lassberg-persons.xml"))
    records = []
    for person in tree.findall(".//t:person", NS) + tree.findall(".//t:personGrp", NS):
        pid = person.get("{http://www.w3.org/XML/1998/namespace}id")
        name_el = person.find('t:persName[@type="main"]', NS)
        name = text_of(name_el) or text_of(person.find("t:persName", NS))
        if not pid or not name:
            continue
        gnd = person.get("ref") or ""
        wiki_ref = person.find("t:ref[@target]", NS)
        wiki = wiki_ref.get("target") if wiki_ref is not None else ""
        extra = " ".join(filter(None, [text_of(person.find("t:occupation", NS)), text_of(person.find("t:education", NS))]))
        records.append({
            "kind": "person",
            "id": pid,
            "title": name,
            "date": "",
            "text": " ".join(filter(None, [name, extra])),
            "url": f"persons.html?q={quote(name)}",
            "external": gnd or wiki or "",
        })
    return records


def build_place_records():
    tree = etree.parse(str(REPO_ROOT / "data/register/lassberg-places.xml"))
    records = []
    for place in tree.findall(".//t:place", NS):
        pid = place.get("{http://www.w3.org/XML/1998/namespace}id")
        name_el = place.find("t:placeName", NS)
        name = text_of(name_el)
        if not pid or not name:
            continue
        wikidata = name_el.get("ref") if name_el is not None else ""
        desc = text_of(place.find("t:desc", NS))
        records.append({
            "kind": "place",
            "id": pid,
            "title": name,
            "date": "",
            "text": " ".join(filter(None, [name, desc])),
            "url": f"places.html?q={quote(name)}",
            "external": wikidata or "",
        })
    return records


def build_literature_records():
    tree = etree.parse(str(REPO_ROOT / "data/register/lassberg-literature.xml"))
    records = []
    for bibl in tree.findall(".//t:bibl", NS):
        bid = bibl.get("{http://www.w3.org/XML/1998/namespace}id")
        title = text_of(bibl.find("t:title", NS))
        if not bid or not title:
            continue
        author = text_of(bibl.find("t:author", NS))
        date = text_of(bibl.find("t:date", NS))
        idno = bibl.find("t:idno", NS)
        idno_text = text_of(idno) if idno is not None else ""
        display_title = f"{author}: {title}" if author else title
        records.append({
            "kind": "literature",
            "id": bid,
            "title": display_title,
            "date": date,
            "text": " ".join(filter(None, [author, title, date])),
            "url": f"letters.html?q={quote(title)}",
            "external": idno_text if idno_text.startswith("http") else "",
        })
    return records


def build_manuscript_records():
    path = REPO_ROOT / "data/register/lassberg-manuscripts.xml"
    if not path.exists():
        return []
    tree = etree.parse(str(path))
    records = []
    for witness in tree.findall(".//t:witness", NS):
        wid = witness.get("{http://www.w3.org/XML/1998/namespace}id")
        bibl = witness.find("t:bibl", NS)
        if not wid or bibl is None:
            continue
        settlement = text_of(bibl.find("t:settlement", NS))
        repository = text_of(bibl.find("t:repository", NS))
        signature = text_of(bibl.find('t:idno[@type="signature"]', NS))
        title = ", ".join(filter(None, [settlement, repository, signature])) or wid
        records.append({
            "kind": "manuscript",
            "id": wid,
            "title": title,
            "date": "",
            "text": title,
            "url": f"letters.html?q={quote(title)}",
            "external": "",
        })
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="json/search_index.json")
    args = parser.parse_args()

    records = (
        build_letter_records()
        + build_person_records()
        + build_place_records()
        + build_literature_records()
        + build_manuscript_records()
    )

    out_path = REPO_ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Wrote {len(records)} records to {out_path}")


if __name__ == "__main__":
    main()
