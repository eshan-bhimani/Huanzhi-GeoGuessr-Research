"""Street View host client (JSONL)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from core.exceptions import HostTimeoutError, HostResponseError, MissingContextError

logger = logging.getLogger(__name__)

class StreetViewHostClient:
    def __init__(
        self,
        node_path: Optional[str] = None,
        host_path: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        resolved_node = None
        if node_path:
            resolved_node = shutil.which(node_path) or node_path
        else:
            resolved_node = (
                shutil.which("node")
                or os.getenv("NODE_PATH")
                or os.getenv("NODEJS_PATH")
            )
            if not resolved_node:
                candidate = r"C:\Program Files\nodejs\node.exe"
                if os.path.exists(candidate):
                    resolved_node = candidate
        self.node_path = resolved_node or "node"
        self.host_path = host_path or str(Path(__file__).resolve().parent / "host.js")
        self.env = env or os.environ.copy()
        self._proc: Optional[subprocess.Popen[str]] = None
        self._next_id = 1
        self._pending: Dict[int, Dict[str, Any]] = {}
        self._pending_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reader = threading.Event()

    def _ensure_proc(self) -> None:
        if self._proc and self._proc.poll() is None:
            return
        self._stop_reader.clear()
        self._proc = subprocess.Popen(
            [self.node_path, self.host_path],
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=self.env,
        )
        logger.debug("Started host process: pid=%s", self._proc.pid)
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    def _reader_loop(self) -> None:
        assert self._proc and self._proc.stdout
        while not self._stop_reader.is_set():
            line = self._proc.stdout.readline()
            if not line:
                break
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            logger.debug("Received response: id=%s", payload.get("id"))
            req_id = payload.get("id")
            if req_id is None:
                continue
            with self._pending_lock:
                entry = self._pending.get(req_id)
                if entry:
                    entry["response"] = payload
                    entry["event"].set()
    
    def _request(
        self,
        method: str,
        session_id: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if not session_id:
            raise MissingContextError("session_id")
        self._ensure_proc()
        assert self._proc and self._proc.stdin
        with self._pending_lock:
            req_id = self._next_id
            self._next_id += 1
            event = threading.Event()
            self._pending[req_id] = {"event": event, "response": None}
        payload = {
            "id": req_id,
            "session_id": session_id,
            "method": method,
            "params": params or {},
        }
        logger.debug("Sending request: id=%d method=%s session=%s", req_id, method, session_id)
        with self._write_lock:
            self._proc.stdin.write(json.dumps(payload) + "\n")
            self._proc.stdin.flush()
        
        timed_out = not event.wait(timeout=30)

        with self._pending_lock:
            entry = self._pending.pop(req_id, None)
        if timed_out or not entry or not entry.get("response"):
            logger.error("Request failed: id=%d method=%s timeout=%s", req_id, method, timed_out)
            raise HostTimeoutError(method=method, timeout=30, req_id=req_id)
        
        resp = entry["response"]
        if not resp.get("ok"):
             raise HostResponseError(error=resp.get("error") or "unknown", method=method)
        
        return resp.get("result")
    
    def start(self, session_id: str, api_key: Optional[str] = None) -> Any:
        params: Dict[str, Any] = {}
        if api_key:
            params["apiKey"] = api_key
        
        return self._request("start", session_id, params)
    
    def init(
        self,
        session_id: str,
        lat: float,
        lng: float,
        heading: float = 0.0,
        pitch: float = 0.0,
        zoom: float = 1.0,
    ) -> Any:
        return self._request(
            "init",
            session_id,
            {
                "lat": lat,
                "lng": lng,
                "heading": heading,
                "pitch": pitch,
                "zoom": zoom,
            },
        )
    
    def get_state(self, session_id: str) -> Any:
        return self._request("getState", session_id)
    
    def set_pov(
            self,
            session_id: str,
            heading: Optional[float] = None,
            pitch: Optional[float] = None,
            zoom: Optional[float] = None) -> Any:
        return self._request(
            "setPov",
            session_id,
            {"heading": heading, "pitch": pitch, "zoom": zoom},
        )
    
    def set_pano(self, session_id: str, pano_id: str) -> Any:
        return self._request("setPano", session_id, {"panoId": pano_id})

    def set_position(self, session_id: str, lat: float, lng: float) -> Any:
        return self._request("setPosition", session_id, {"lat": lat, "lng": lng})
    
    def wait_for_stable(
        self,
        session_id: str,
        timeoutMs: int = 1500,
        debounceMs: int = 200,
    ) -> Any:
        return self._request(
            "waitForStable",
            session_id,
            {"timeoutMs": timeoutMs, "debounceMs": debounceMs},
        )

    def close_session(self, session_id: str) -> Any:
        logger.debug("Terminating host process: pid=%s", self._proc.pid)
        return self._request("closeSession", session_id, {})
    
    def close(self) -> None:
        if not self._proc:
            return
        self._stop_reader.set()
        if self._proc.poll() is None:
            self._proc.terminate()
        with self._pending_lock:
            for req_id, entry in self._pending.items():
                entry["response"] = {
                    "id": req_id,
                    "ok": False,
                    "error": "host_closed",
                }
                entry["event"].set()
        self._proc = None

    def __enter__(self) -> "StreetViewHostClient":
        self._ensure_proc()
        return self
    
    def __exit__(self, exc_type, exc_val, tb) -> None:
        self.close()
        
    
        
