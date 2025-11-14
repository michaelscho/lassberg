# exporters.py
"""
Back-end export helpers for downloading PageXML from a repository.

- TranskribusExporter: implemented with legacy Laßberg naming and default export
  to config.export_folder
    Folder: <config.export_folder>/lassberg-letter-<NNNN>/
    Files : lassberg-letter-<NNNN>-<i>.xml   (i starts at 1, no zero padding)

- EScriptoriumExporter: stub (same interface; implement later)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Iterable
import os
import re
import time
import zipfile
from pathlib import Path

import requests
import config  # <-- default export folder comes from here

# Reuse your types/client
from file_selection import DocumentInfo, TranskribusClient


@dataclass
class ExportResult:
    """Summary of one document export."""
    document: DocumentInfo
    dest_dir: Path                   # destination directory for this document’s PAGE-XML (legacy path)
    pagexml_files: List[Path]        # list of extracted PAGE-XML files


class BaseExporter:
    """Abstract interface for PageXML exporters."""
    def export_documents(self, documents: Iterable[DocumentInfo]) -> List[ExportResult]:
        raise NotImplementedError


def _derive_letter_id_from_title(title: Optional[str], fallback_numeric: int) -> str:
    """
    Extract the numeric letter id from a Transkribus title like:
        'lassberg-letter-1151' or 'done_lassberg-letter-42'
    Returns a 4-digit zero-padded string ('1151', '0042').
    If not found, falls back to the numeric arg (docId) zero-padded.
    """
    t = (title or "").lower().replace("done_", "")
    m = re.search(r"lassberg[-_ ]letter[-_ ](\d+)", t)
    num = m.group(1) if m else str(fallback_numeric)
    return str(int(num)).zfill(4)


class TranskribusExporter(BaseExporter):
    """
    Export PageXML from Transkribus for one or more documents.

    Legacy Laßberg naming is enforced:
      dest_dir = <dest_root>/lassberg-letter-<NNNN>/
      files    = lassberg-letter-<NNNN>-<i>.xml   (i = 1..N, no zero padding)

    By default, dest_root is taken from config.export_folder.
    """

    BASE = "https://transkribus.eu/TrpServer/rest"

    def __init__(
        self,
        collection_id: str | int,
        *,
        user: Optional[str] = None,
        pw: Optional[str] = None,
        dest_root: Optional[str | os.PathLike] = None,
        overwrite: bool = True,
        rename_files: bool = True,
        poll_interval_s: float = 5.0,
        job_timeout_s: int = 30 * 60,
        session: Optional[requests.Session] = None,
    ):
        # Destination root: default to config.export_folder
        root = dest_root if dest_root is not None else config.export_folder
        self.dest_root = Path(root)
        self.dest_root.mkdir(parents=True, exist_ok=True)

        self.collection_id = str(collection_id)
        self.overwrite = overwrite
        self.rename_files = rename_files
        self.poll_interval_s = poll_interval_s
        self.job_timeout_s = job_timeout_s

        # Reuse TranskribusClient for login + session
        self._client = TranskribusClient(
            user=user,
            pw=pw,
            collection_id=self.collection_id,
            session=session,
        )
        self.session: requests.Session = self._client.session

    # ---------- public helpers (used by main_export.py for checks) ----------

    def planned_dest_dir(self, doc: DocumentInfo) -> Path:
        """
        Return the legacy Laßberg folder where PAGE-XML will be written:
            <dest_root>/lassberg-letter-<NNNN>/
        """
        letter_id = _derive_letter_id_from_title(doc.title, doc.id)
        return self.dest_root / f"lassberg-letter-{letter_id}"

    # ---------- export pipeline ----------

    def export_documents(self, documents: Iterable[DocumentInfo]) -> List[ExportResult]:
        results: List[ExportResult] = []
        for doc in documents:
            res = self._export_single_document(doc)
            results.append(res)
        return results

    def _export_single_document(self, doc: DocumentInfo) -> ExportResult:
        job_id = self._start_export_job(doc_id=doc.id)
        result_url = self._wait_for_job_and_get_result(job_id)
        zip_path = self._download_zip(result_url, doc)
        dest_dir = self._extract_pagexml(zip_path, doc)   # legacy folder path
        pagexml_files = sorted(dest_dir.glob("*.xml"), key=lambda p: p.name.lower())
        if self.rename_files:
            pagexml_files = self._rename_pagexml_files(dest_dir, doc, pagexml_files)
        return ExportResult(document=doc, dest_dir=dest_dir, pagexml_files=pagexml_files)

    # ---------- Transkribus REST ----------

    def _start_export_job(self, doc_id: int) -> str:
        url = f"{self.BASE}/collections/{self.collection_id}/{doc_id}/export"
        export_conf = {
            "commonPars": {
                "doExportDocMetadata": True,
                "doWriteMets": True,
                "doWriteImages": False,
                "doExportPageXml": True,
                "doExportAltoXml": False,
                "doExportSingleTxtFiles": False,
                "doWritePdf": False,
                "doWriteTei": False,
                "doWriteDocx": False,
                "doWriteOneTxt": False,
                "doOverwrite": True,
                "useHttps": True,
                "useOcrMasterDir": True,
                "fileNamePattern": "${filename}",
                "pageDirName": "page",
                "updatePageXmlImageDimensions": False,
                "exportTranscriptMetadata": True,
                "useVersionStatus": "Latest version",
            }
        }
        r = self.session.post(url, json=export_conf, timeout=60)
        r.raise_for_status()
        job_id = r.text.strip().strip('"')
        if not job_id:
            raise RuntimeError("Transkribus export did not return a job id.")
        return job_id

    def _wait_for_job_and_get_result(self, job_id: str) -> str:
        url = f"{self.BASE}/jobs/{job_id}"
        deadline = time.time() + self.job_timeout_s
        while True:
            if time.time() > deadline:
                raise TimeoutError(f"Export job {job_id} timed out.")
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            state = data.get("state")
            if state == "FINISHED":
                result_url = data.get("result")
                if not result_url:
                    raise RuntimeError(f"Job {job_id} finished but has no 'result' URL.")
                return result_url
            if state in {"FAILED", "CANCELED"}:
                raise RuntimeError(f"Export job {job_id} failed with state '{state}'.")
            time.sleep(self.poll_interval_s)

    # ---------- IO helpers ----------

    def _download_zip(self, result_url: str, doc: DocumentInfo) -> Path:
        """
        Download the ZIP produced by the export job into the legacy folder:
            <dest_root>/lassberg-letter-<NNNN>/export.zip
        """
        dest_dir = self.planned_dest_dir(doc)
        dest_dir.mkdir(parents=True, exist_ok=True)

        zip_path = dest_dir / "export.zip"
        if zip_path.exists() and self.overwrite:
            zip_path.unlink(missing_ok=True)

        with self.session.get(result_url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return zip_path

    def _extract_pagexml(self, zip_path: Path, doc: DocumentInfo) -> Path:
        """
        Extract only files under a 'page/' folder into the legacy folder:
            <dest_root>/lassberg-letter-<NNNN>/
        (We flatten: write *.xml directly into that folder.)
        """
        dest_dir = self.planned_dest_dir(doc)

        # Clean existing *.xml to avoid stale files if overwriting
        if dest_dir.exists() and self.overwrite:
            for p in dest_dir.glob("*.xml"):
                p.unlink(missing_ok=True)
        dest_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.namelist():
                # Only extract PAGE-XML files from any 'page/' subfolder
                if "/page/" in member and member.lower().endswith(".xml"):
                    filename = os.path.basename(member)
                    with z.open(member, "r") as src, open(dest_dir / filename, "wb") as dst:
                        dst.write(src.read())

        return dest_dir

    def _rename_pagexml_files(
        self,
        dest_dir: Path,
        doc: DocumentInfo,
        files: List[Path],
    ) -> List[Path]:
        """
        Rename extracted PAGE-XML files to the legacy pattern:

            lassberg-letter-<NNNN>-<i>.xml

        where <i> starts at 1 and is not zero-padded.
        """
        if not files:
            return files

        letter_id = _derive_letter_id_from_title(doc.title, doc.id)
        base = f"lassberg-letter-{letter_id}"

        files_sorted = sorted(files, key=lambda p: p.name.lower())
        new_files: List[Path] = []
        for i, p in enumerate(files_sorted, start=1):
            target = dest_dir / f"{base}-{i}.xml"
            if target != p:
                if target.exists() and self.overwrite:
                    target.unlink(missing_ok=True)
                p.rename(target)
            new_files.append(target)
        return new_files


class EScriptoriumExporter(BaseExporter):
    """Stub to keep the interface stable; implement later."""
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("EScriptoriumExporter is not implemented yet.")
