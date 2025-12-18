import os
from typing import Any, Dict, Optional

import requests


class BackendClient:
    """
    Minimal HTTP client for talking to the FastAPI backend.

    Defaults to http://127.0.0.1:8000 and can be overridden with BACKEND_BASE_URL.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0) -> None:
        self.base_url = (base_url or os.getenv("BACKEND_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.timeout = timeout

    def get_state(self) -> Dict[str, Any]:
        url = f"{self.base_url}/environment/state"
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            raise RuntimeError(f"Failed to fetch environment state from {url}: {exc}") from exc

    def push_instruction(self, instruction: Dict[str, Any]) -> None:
        """
        Push an instruction to the backend so the frontend can pick it up via polling.
        """
        url = f"{self.base_url}/instruction/push"
        try:
            resp = requests.post(url, json=instruction, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            # Do not hard-fail tool execution; treat as best-effort delivery.
            print(f"[backend_client] Failed to push instruction to {url}: {exc}")
