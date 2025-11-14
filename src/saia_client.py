# saia_client.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import os
import json
import time
import requests
import config

@dataclass
class ChatCompletion:
    content: str
    raw: Dict[str, Any]

class SaiaChatClient:
    """
    Minimal OpenAI-compatible chat client for SAIA.

    SAIA specifics:
      - Base URL: https://chat-ai.academiccloud.de/v1
      - Chat path: /chat/completions
      - Auth: Bearer <API_KEY>
      - /models uses POST per SAIA docs.

    Env/config:
      SAIA_BASE_URL (default: https://chat-ai.academiccloud.de/v1)
      SAIA_API_KEY  (required)
      SAIA_MODEL    (default: llama-3.3-70b-instruct)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        *,
        chat_path: str = "/chat/completions",
        models_path: str = "/models",
        timeout: int = 8000,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("SAIA_BASE_URL") or "https://chat-ai.academiccloud.de/v1").rstrip("/")
        self.api_key = config.saia_api_key
        self.model = model or os.environ.get("SAIA_MODEL") or "llama-3.3-70b-instruct"
        self.chat_url = f"{self.base_url}{chat_path}"
        self.models_url = f"{self.base_url}{models_path}"
        self.timeout = timeout
        self.session = session or requests.Session()

        if not self.api_key:
            raise ValueError("SAIA_API_KEY is not set (env or pass in).")

    # ---------- low-level ----------

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ---------- high-level ----------

    def list_models(self) -> Dict[str, Any]:
        """SAIA uses POST /v1/models."""
        resp = self.session.post(self.models_url, headers=self._headers(), json={}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        top_p: Optional[float] = None,
        response_format_json: bool = False,
        extra: Optional[Dict[str, Any]] = None,
        retry: int = 2,
        retry_backoff_s: float = 1.0,
    ) -> ChatCompletion:
        """
        Send a chat completion request (OpenAI-compatible).
        messages: [{"role":"system"|"user"|"assistant","content":"..."}]
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if top_p is not None:
            payload["top_p"] = top_p
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}
        if extra:
            payload.update(extra)

        last_err = None
        for attempt in range(retry + 1):
            try:
                resp = self.session.post(
                    self.chat_url,
                    headers=self._headers(),
                    json=payload,
                    timeout=self.timeout,
                )
                # Handle throttling with simple backoff
                if resp.status_code == 429 and attempt < retry:
                    time.sleep(retry_backoff_s * (attempt + 1))
                    continue
                resp.raise_for_status()
                data = resp.json()
                # Some SAIA/Azure responses include content_filter_results; we ignore it here.
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return ChatCompletion(content=content, raw=data)
            except Exception as e:
                last_err = e
                if attempt < retry:
                    time.sleep(retry_backoff_s * (attempt + 1))
                else:
                    raise

        # Shouldn’t get here
        raise RuntimeError(f"Chat failed: {last_err}")

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        top_p: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Request JSON-only output and parse it."""
        cc = self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            response_format_json=True,
            extra=extra,
        )
        try:
            return json.loads(cc.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Model did not return valid JSON: {e}\n---\n{cc.content}")
