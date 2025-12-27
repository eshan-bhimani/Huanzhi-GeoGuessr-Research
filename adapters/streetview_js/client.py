"""Street View host client (JSONL)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


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

    def _ensure_proc(self) -> None:
        if self._proc and self._proc.poll() is None:
            return
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

    def _read_response(self, req_id: int) -> Dict[str, Any]:
        assert self._proc and self._proc.stdout
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError("host_no_response")
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"host_invalid_response:{exc}") from exc
        if(payload.get("id") != req_id):
            raise RuntimeError("host_invalid_response_id")
        return payload
    
    def _request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        self._ensure_proc()
        assert self._proc and self._proc.stdin
        req_id = self._next_id
        self._next_id += 1
        payload = {"id": req_id, "method": method, "params": params or {}}
        self._proc.stdin.write(json.dumps(payload) + "\n")
        self._proc.stdin.flush()
        resp = self._read_response(req_id)
        if not resp.get("ok"):
            raise RuntimeError(resp.get("error") or "host_error")
        
        return resp.get("result")
    
    def start(self, api_key: Optional[str] = None) -> Any:
        params: Dict[str, Any] = {}
        if api_key:
            params["apiKey"] = api_key
        
        return self._request("start", params)
    
    def init(self, lat: float, lng: float, heading: float = 0.0, pitch: float = 0.0, zoom: float = 1.0) -> Any:
        return self._request("init", 
                             {
                                 "lat": lat, 
                                 "lng": lng, 
                                 "heading": heading, 
                                 "pitch": pitch, 
                                 "zoom": zoom
                                 },
                                )
    
    def get_state(self) -> Any:
        return self._request("getState")
    
    def set_pov(
            self,
            heading: Optional[float] = None,
            pitch: Optional[float] = None,
            zoom: Optional[float] = None) -> Any:
        return self._request("setPov", {"heading": heading, "pitch": pitch, "zoom": zoom})
    
    def set_pano(self, pano_id: str) -> Any:
        return self._request("setPano", {"panoId": pano_id})

    def set_position(self, lat: float, lng: float) -> Any:
        return self._request("setPosition", {"lat": lat, "lng": lng})
    

    def wait_for_stable(self, timeoutMs: int = 1500, debounceMs: int = 200) -> Any:
        return self._request("waitForStable", {"timeoutMs": timeoutMs, "debounceMs": debounceMs})
    
    def close(self) -> None:
        if not self._proc:
            return
        if self._proc.poll() is None:
            self._proc.terminate()
        self._proc = None


    def __enter__(self) -> "StreetViewHostClient":
        self._ensure_proc()
        return self
    
    def __exit__(self, exc_type, exc_val, tb) -> None:
        self.close()
        
    
        
