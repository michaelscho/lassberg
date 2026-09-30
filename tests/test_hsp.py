"""HSP client, description parsing, local index and licence-safety tests.

Offline tests use self-built minimal TEI (never check in real HSP descriptions: licences).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "manuscripts"))

import lib_hsp as hsp  # noqa: E402

TEI = "http://www.tei-c.org/ns/1.0"


def desc_xml(status: str, licence: str, extra_id: str = "HSP-desc-1") -> bytes:
    return f"""<TEI xmlns="{TEI}"><teiHeader><fileDesc>
<titleStmt><title>Beschreibung von Testort, Testbibliothek, Cod. Test 1 (Katalog X)</title></titleStmt>
<publicationStmt><availability status="{status}"><licence target="{licence}"><p>x</p></licence></availability></publicationStmt>
</fileDesc></teiHeader><text><body>
<msDesc type="hsp:description"><msIdentifier><settlement>Testort</settlement><repository>Testbibliothek</repository>
<idno>Cod. Test 1</idno>
<altIdentifier type="former"><idno>Alt. Sign. 77</idno></altIdentifier></msIdentifier>
<head><title>Testlieder</title><note type="headline">Pergament · 10 Bl.</note></head>
<msContents><summary>Eine Sammlung erfundener Lieder.</summary>
<msItem><note type="text">1r-5v</note><author>Erfundener Dichter</author><title>Das Testlied</title><incipit>Ez was ein tac</incipit></msItem></msContents>
<history><p>Geschichte: im Besitz von Freiherr Testmann.</p></history>
</msDesc></body></text></TEI>""".encode()


def kod_xml(ids) -> bytes:
    idx = "".join(f'<index copyOf="#{i}" indexName="norm_title"/>' for i in ids)
    return f"""<TEI xmlns="{TEI}"><teiHeader><fileDesc><publicationStmt>
<availability status="free"><licence target="https://creativecommons.org/publicdomain/zero/1.0/deed.de"/></availability>
</publicationStmt></fileDesc></teiHeader><text><body><msDesc><msIdentifier><idno>Cod. Test 1</idno>
<altIdentifier type="former"><idno>Alt. Sign. 77</idno></altIdentifier></msIdentifier><head>{idx}</head></msDesc></body></text></TEI>""".encode()


def test_licence_of():
    free = hsp.licence_of(kod_xml([]))
    assert free == {"status": "free", "url": "https://creativecommons.org/publicdomain/zero/1.0/deed.de"}
    restricted = hsp.licence_of(desc_xml("restricted", "http://rightsstatements.org/vocab/InC/1.0/"))
    assert restricted["status"] == "restricted"
    # "free" status alone is not enough: the URL must be on the positive list
    assert hsp.licence_of(desc_xml("free", "https://example.org/some-licence"))["status"] == "unknown"
    assert hsp.is_free_licence("https://creativecommons.org/licenses/by/4.0/")
    assert not hsp.is_free_licence(None) and not hsp.is_free_licence("http://rightsstatements.org/vocab/InC/1.0/")


def test_description_ids_deduplicated():
    assert hsp.description_ids(kod_xml(["HSP-a", "HSP-b", "HSP-a"])) == ["HSP-a", "HSP-b"]


def test_parse_description():
    d = hsp.parse_description(desc_xml("restricted", "http://rightsstatements.org/vocab/InC/1.0/"))
    assert d["citation"].startswith("Beschreibung von Testort")
    assert d["licence_status"] == "restricted"
    assert d["msidentifier"]["shelfmark"] == "Cod. Test 1"
    assert d["msidentifier"]["former_shelfmarks"] == ["Alt. Sign. 77"]
    assert d["head"] == "Testlieder" and d["headline"] == "Pergament · 10 Bl."
    assert d["summary"] == "Eine Sammlung erfundener Lieder."
    assert d["items"][0]["title"] == "Das Testlied" and d["items"][0]["incipit"] == "Ez was ein tac"
    assert "Testmann" in d["history"] and "Testmann" in d["fulltext"]


def test_clean_kod_title():
    assert hsp.clean_kod_title("‘Kolmarer Liederhandschrift’") == "Kolmarer Liederhandschrift"
    assert hsp.clean_kod_title("›Weingartner Liederhandschrift‹") == "Weingartner Liederhandschrift"


@pytest.fixture
def mini_mirror(tmp_path, monkeypatch):
    import build_hsp_index as bi
    hid = "HSP-kod-1"
    (tmp_path / "kod").mkdir()
    (tmp_path / "desc").mkdir()
    (tmp_path / "kod" / f"{hid}.json").write_text(
        '{"id": "HSP-kod-1", "idno-display": "Cod. Test 1", "title-display": "‘Testlieder’", '
        '"orig-date-lang-display": ["13. Jh."], "orig-place-display": "Testort"}', encoding="utf-8")
    (tmp_path / "kod" / f"{hid}.xml").write_bytes(kod_xml(["HSP-desc-1"]))
    (tmp_path / "desc" / "HSP-desc-1.xml").write_bytes(
        desc_xml("restricted", "http://rightsstatements.org/vocab/InC/1.0/"))
    reg = tmp_path / "reg.xml"
    reg.write_text(f"""<TEI xmlns="{TEI}"><text><body><listBibl>
<msDesc xml:id="lassberg-witness-0001"><msIdentifier><settlement>Testort</settlement><repository>Testbibliothek</repository>
<idno type="shelfmark">Cod. Test 1</idno><altIdentifier type="hsp"><idno>{hid}</idno></altIdentifier></msIdentifier></msDesc>
</listBibl></body></text></TEI>""", encoding="utf-8")
    monkeypatch.setattr(hsp, "HSP_DIR", tmp_path)
    monkeypatch.setattr(hsp, "INDEX_DB", tmp_path / "index.sqlite")
    assert bi.build(reg) == 1
    return tmp_path


def test_local_search_signature_former_and_fulltext(mini_mirror):
    by_sig = hsp.local_search("Cod. Test 1")
    assert by_sig and by_sig[0]["witness_id"] == "lassberg-witness-0001" and by_sig[0]["snippet"] == "signature match"
    assert hsp.local_search("Alt. Sign. 77")[0]["hsp_id"] == "HSP-kod-1"      # former shelfmark
    hit = hsp.local_search("Testmann")[0]                                    # provenance text (prefix search)
    assert hit["hsp_id"] == "HSP-kod-1"
    assert hsp.local_search("Nibelungen") == []


def test_local_search_without_index_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(hsp, "INDEX_DB", tmp_path / "missing.sqlite")
    assert hsp.local_search("anything") == []


def test_no_restricted_hsp_data_is_tracked_by_git():
    out = subprocess.run(["git", "ls-files", "data/hsp", "json/hsp-local"], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout.strip()
    assert out == "", f"licence-restricted HSP data must never be committed: {out}"


@pytest.mark.network
def test_live_kolmar_lookup():
    """Live HSP API; the ID is test data here (never hard-coded in scripts/mcp_server/js)."""
    kod_id = "HSP-666242f4-0675-3121-b0d6-be697c7a9b20"
    assert hsp.get_kod(kod_id)["idno-display"] == "Cgm 4997"
    assert hsp.description_ids(hsp.get_tei(kod_id))
    assert any(k["id"] == kod_id for k in hsp.search("Kolmarer Liederhandschrift", rows=5))


def test_licence_gate_public_export_has_no_restricted_content(mini_mirror):
    import export_manuscripts as ex
    e = {"id": "lassberg-witness-0001", "label": "Test", "hsp_id": "HSP-kod-1", "signature": "Cod. Test 1"}
    public = ex.witness_doc("lassberg-witness-0001", e, [], gate=True, manifest={})
    assert public["descriptions"] and public["descriptions"][0]["content"] is None
    assert public["descriptions"][0]["licence_status"] == "restricted"
    assert "Testmann" not in str(public) and "erfundener" not in str(public).lower()
    local = ex.witness_doc("lassberg-witness-0001", e, [], gate=False, manifest={})
    assert "Testmann" in str(local["descriptions"][0]["content"])


def test_licence_gate_lets_free_descriptions_through(mini_mirror):
    import export_manuscripts as ex
    (mini_mirror / "desc" / "HSP-desc-1.xml").write_bytes(
        desc_xml("free", "https://creativecommons.org/publicdomain/zero/1.0/deed.de"))
    e = {"id": "lassberg-witness-0001", "hsp_id": "HSP-kod-1"}
    public = ex.witness_doc("lassberg-witness-0001", e, [], gate=True, manifest={})
    assert "Testmann" in str(public["descriptions"][0]["content"])
