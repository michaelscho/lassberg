# file_selection.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import os
import re
import requests

from InquirerPy import inquirer

# --- Configuration expectations ------------------------------------------------
# Re-use your existing config.py values:
#   config.transkribus_user : str
#   config.transkribus_pw   : str
#   config.collection_id    : int | str
# Optionally allow overriding via function parameters.
import config


# --- Public data model ---------------------------------------------------------

@dataclass
class DocumentInfo:
    """Lightweight representation of a server-side document."""
    id: int
    title: str
    pages: Optional[int] = None
    # Add more fields later if needed (status, updatedAt, etc.)


# --- Backend interfaces --------------------------------------------------------

class BackendClient:
    """Abstract base for backends. Add new methods here if the pipeline grows."""
    def list_documents(self) -> List[DocumentInfo]:
        raise NotImplementedError


class TranskribusClient(BackendClient):
    """
    Minimal Transkribus client for listing documents in a collection.

    Auth: stores the JSESSIONID cookie in a requests.Session.
    Docs list endpoint (legacy): GET /TrpServer/rest/collections/{collectionId}/list
    """
    BASE = "https://transkribus.eu/TrpServer/rest"

    def __init__(
        self,
        user: Optional[str] = None,
        pw: Optional[str] = None,
        collection_id: Optional[str | int] = None,
        session: Optional[requests.Session] = None,
    ):
        self.user = user or config.transkribus_user
        self.pw = pw or config.transkribus_pw
        self.collection_id = str(collection_id or config.collection_id)
        self.session = session or requests.Session()
        self._login()

    def _login(self) -> None:
        resp = self.session.post(f"{self.BASE}/auth/login", data={"user": self.user, "pw": self.pw})
        resp.raise_for_status()

    def list_documents(self) -> List[DocumentInfo]:
        url = f"{self.BASE}/collections/{self.collection_id}/list"
        r = self.session.get(url)
        r.raise_for_status()
        data = r.json()  # list of documents
        docs: List[DocumentInfo] = []
        for d in data:
            # Common keys in the legacy response:
            #   docId (int), title (str), nrOfPages (int), ...
            docs.append(
                DocumentInfo(
                    id=int(d.get("docId")),
                    title=str(d.get("title") or ""),
                    pages=d.get("nrOfPages"),
                )
            )
        return docs


class EScriptoriumClient(BackendClient):
    """
    Placeholder for eScriptorium. Keep signature compatible with TranskribusClient.
    Later, implement auth + project/document listing as needed.
    """
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("eScriptorium backend is not implemented yet.")


# --- Selection helpers ---------------------------------------------------------

def _sort_documents(
    docs: List[DocumentInfo],
    sort_by: str = "id",
    reverse: bool = False,
) -> List[DocumentInfo]:
    """
    Sort documents before showing them in the TUI.

    Parameters
    ----------
    docs : list of DocumentInfo
        The documents to sort.
    sort_by : {'id', 'title', 'pages'}
        Field to sort by. Default = 'id'.
    reverse : bool
        If True, sort in descending order.

    Returns
    -------
    List[DocumentInfo]
        Sorted list of documents.
    """
    key_funcs = {
        "id": lambda d: d.id,
        "title": lambda d: (d.title or "").lower(),
        "pages": lambda d: d.pages if d.pages is not None else 0,
    }
    if sort_by not in key_funcs:
        raise ValueError(f"sort_by must be one of {list(key_funcs)}")
    return sorted(docs, key=key_funcs[sort_by], reverse=reverse)


def _filter_done_prefix(
    docs: List[DocumentInfo],
    *,
    exclude_done: bool = False,
    only_done: bool = False,
) -> List[DocumentInfo]:
    """
    Filter documents by 'done_' title prefix.
    Exactly one of exclude_done/only_done may be True; both False keeps all.
    """
    if exclude_done and only_done:
        raise ValueError("exclude_done and only_done are mutually exclusive.")
    if only_done:
        return [d for d in docs if (d.title or "").startswith("done_")]
    if exclude_done:
        return [d for d in docs if not (d.title or "").startswith("done_")]
    return docs


def _apply_text_filter(docs: List[DocumentInfo], text_filter: Optional[str]) -> List[DocumentInfo]:
    """
    Case-insensitive substring filter over title and id string.
    Empty/None filter returns original list.
    """
    if not text_filter:
        return docs
    pat = text_filter.strip().lower()
    return [d for d in docs if pat in (d.title or "").lower() or pat in str(d.id).lower()]


def _format_choice_label(d: DocumentInfo) -> str:
    """
    Human-friendly label for a document choice row, shown in the TUI.
    Adds a '[DONE]' badge for titles with 'done_' prefix and shows id/pages.
    """
    title = d.title or ""
    pages = d.pages if d.pages is not None else "-"
    badge = " [DONE]" if title.startswith("done_") else ""
    short = (title[:90] + "…") if len(title) > 90 else title
    return f"{short}{badge} — id:{d.id}  pages:{pages}"


def _coerce_selection_to_docs(
    selection: Any,
    docs: List[DocumentInfo],
) -> List[DocumentInfo]:
    """
    Ensure we return a List[DocumentInfo] even if the TUI returns strings.

    - If items are already DocumentInfo: pass-through.
    - If strings: try exact match on label, else extract id with regex r'id:(\\d+)'.
    """
    if selection is None:
        return []
    items = selection if isinstance(selection, list) else [selection]
    # Build label and id maps for fallback resolution
    label_map = {_format_choice_label(d): d for d in docs}
    id_map = {d.id: d for d in docs}

    out: List[DocumentInfo] = []
    for item in items:
        if isinstance(item, DocumentInfo):
            out.append(item)
        elif isinstance(item, str):
            # try label match first
            cand = label_map.get(item)
            if cand:
                out.append(cand); continue
            # then extract id
            m = re.search(r"id:(\d+)", item)
            if m:
                di = id_map.get(int(m.group(1)))
                if di:
                    out.append(di); continue
        else:
            # If InquirerPy returns dict-like structures in some envs (unlikely)
            try:
                # Try to interpret as DocumentInfo-ish
                if hasattr(item, "id") and hasattr(item, "title"):
                    out.append(item)  # type: ignore
                    continue
            except Exception:
                pass
    return out


# --- InquirerPy-powered interactive selector ----------------------------------

def select_documents_interactive(
    backend: str = "transkribus",
    *,
    transkribus_kwargs: Optional[Dict[str, Any]] = None,
    exclude_done: bool = False,
    only_done: bool = False,
    text_filter: Optional[str] = None,
    sort_by: str = "id",
    descending: bool = False,
    page_size: int = 15,
) -> List[DocumentInfo]:
    """
    Interactive multi-select using InquirerPy with fuzzy search.

    Flow
    ----
    1) Fetch list of documents from the chosen backend.
    2) OPTIONAL: filter by 'done_' prefix (exclude or only).
    3) OPTIONAL: pre-filter by a case-insensitive substring on title/id.
    4) OPTIONAL: sort by id/title/pages (asc/desc).
    5) Present a fuzzy multi-select prompt (type to search; Tab to toggle).
    6) Return the selected DocumentInfo objects.

    Keybindings (InquirerPy fuzzy multiselect)
    ------------------------------------------
    - Type to fuzzy-search
    - Up/Down to navigate
    - Tab to toggle selection
    - Enter to confirm
    - Ctrl+A to toggle all
    """
    # 1) backend
    if backend == "transkribus":
        client = TranskribusClient(**(transkribus_kwargs or {}))
    elif backend == "escriptorium":
        client = EScriptoriumClient(**(transkribus_kwargs or {}))  # will raise for now
    else:
        raise ValueError("backend must be 'transkribus' or 'escriptorium'.")

    docs = client.list_documents()
    if not docs:
        print("No documents found for the given collection.")
        return []

    # 2) 'done_' filter
    docs = _filter_done_prefix(docs, exclude_done=exclude_done, only_done=only_done)
    if not docs:
        print("No documents after 'done_' filtering.")
        return []

    # 3) optional pre-filter
    docs = _apply_text_filter(docs, text_filter=text_filter)
    if not docs:
        print("No documents matched the text filter.")
        return []

    # 4) sorting
    docs = _sort_documents(docs, sort_by=sort_by, reverse=descending)

    # 5) fuzzy multi-select prompt
    # Use dict choices so InquirerPy reliably returns .value (DocumentInfo)
    choices = [{"name": _format_choice_label(d), "value": d} for d in docs]

    selection = inquirer.fuzzy(
        message="Select documents (type to search, Tab to toggle, Enter to confirm):",
        choices=choices,
        multiselect=True,
        validate=lambda sel: True if sel else "Please select at least one document.",
        height=page_size,
    ).execute()

    return _coerce_selection_to_docs(selection, docs)


# --- File-based selection (TXT) -----------------------------------------------

def select_documents_from_file(
    path_to_txt: str,
    backend: str = "transkribus",
    *,
    transkribus_kwargs: Optional[Dict[str, Any]] = None,
    match_on: str = "title",
    case_sensitive: bool = False,
    sort_by: str = "id",
    descending: bool = False,
) -> List[DocumentInfo]:
    """
    Non-interactive selection: read desired document names/ids from a TXT file
    (one per line) and resolve them against the backend's document list.

    The file typically contains document **titles** (default). You can set
    match_on='id' to treat each line as a numeric docId instead.
    """
    if backend == "transkribus":
        client = TranskribusClient(**(transkribus_kwargs or {}))
    elif backend == "escriptorium":
        client = EScriptoriumClient(**(transkribus_kwargs or {}))  # will raise for now
    else:
        raise ValueError("backend must be 'transkribus' or 'escriptorium'.")

    docs = client.list_documents()
    by_id: Dict[str, DocumentInfo] = {str(d.id): d for d in docs}
    by_title: Dict[str, DocumentInfo]
    if case_sensitive:
        by_title = {d.title: d for d in docs}
    else:
        by_title = {(d.title or "").lower(): d for d in docs}

    if not os.path.exists(path_to_txt):
        raise FileNotFoundError(f"List file not found: {path_to_txt}")

    selected: List[DocumentInfo] = []
    with open(path_to_txt, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if match_on == "id":
                doc = by_id.get(line)
                if not doc:
                    raise ValueError(f"Document id not found in collection: {line}")
                selected.append(doc)
            elif match_on == "title":
                key = line if case_sensitive else line.lower()
                doc = by_title.get(key)
                if not doc:
                    raise ValueError(f"Document title not found in collection: {line}")
                selected.append(doc)
            else:
                raise ValueError("match_on must be 'title' or 'id'.")

    # Optional sort of the resolved selection
    selected = _sort_documents(selected, sort_by=sort_by, reverse=descending)
    return selected
