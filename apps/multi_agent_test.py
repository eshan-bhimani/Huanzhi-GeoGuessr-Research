from __future__ import annotations

import json
import os
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapters.streetview_js.client import StreetViewHostClient
from core.tools.contracts import ToolContext, ToolResult
from core.tools.dispatcher import run_tool

K_STEPS = 2
BASE_COORDS: List[Tuple[float, float]] = [
    (37.7749, -122.4194),
    (37.7750, -122.4189),
    (38.88918843, -77.02835864),
    (34.0522, -118.2437),
    (40.7128, -74.0060),
    (47.6062, -122.3321),
    (51.5074, -0.1278),
    (48.8566, 2.3522),
    (35.6895, 139.6917),
    (52.52, 13.4050),
]
OFFSETS = [i * 0.0001 for i in range(10)]
COORDS: List[Tuple[float, float]] = [
    (lat + delta, lng - delta) for (lat, lng) in BASE_COORDS for delta in OFFSETS
]
N_AGENTS = len(COORDS)


def _error_text(result: ToolResult) -> str:
    if result.ok:
        return ""
    if result.debug:
        try:
            return json.dumps(result.debug, ensure_ascii=True)
        except TypeError:
            return str(result.debug)
    return "error"


def _pick_move_action(move_actions: List[Dict[str, Any]]) -> Optional[str]:
    if not move_actions:
        return None
    for action in move_actions:
        name = (action.get("action") or "").lower()
        if name in ("move_n", "move_north"):
            return action.get("action")
    return move_actions[0].get("action")


def _run_agent(agent_id: int, lat: float, lng: float, host: StreetViewHostClient) -> Dict[str, Any]:
    summary = {
        "agent_id": agent_id,
        "steps_done": 0,
        "last_tool": "init_panorama",
        "ok": True,
        "error": "",
    }
    session_id = f"session_{agent_id}_{int(time.time())}"
    try:
        output_root = os.getenv("IMAGE_OUTPUT_DIR", "images")
        ctx = ToolContext(
            session_id=session_id,
            meta={
                "host_client": host,
                "image_root": str(Path(output_root) / f"agent_{agent_id}"),
                "image_step": 1,
            },
        )

        result = run_tool(
            ctx,
            "init_panorama",
            {"lat": lat, "lng": lng, "heading": 0, "pitch": 0, "zoom": 1},
        )
        summary["last_tool"] = "init_panorama"
        summary["ok"] = result.ok
        summary["error"] = _error_text(result)
        if not result.ok:
            return summary

        for _ in range(K_STEPS):
            result = run_tool(ctx, "check_available_moves", {})
            summary["last_tool"] = "check_available_moves"
            summary["ok"] = result.ok
            summary["error"] = _error_text(result)
            if not result.ok:
                break
            move_actions = (result.updates or {}).get("move_actions") or []
            tool_name = _pick_move_action(move_actions)
            if not tool_name:
                break
            result = run_tool(ctx, tool_name, {})
            summary["last_tool"] = tool_name
            summary["ok"] = result.ok
            summary["error"] = _error_text(result)
            if not result.ok:
                break
            summary["steps_done"] += 1
    except Exception as exc:
        summary["ok"] = False
        summary["error"] = f"exception:{exc}"
    finally:
        try:
            host.close_session(session_id)
        except Exception:
            pass
    return summary


def _render_table(rows: List[Dict[str, Any]]) -> None:
    columns = ["agent_id", "steps_done", "last_tool", "ok", "error"]
    widths: Dict[str, int] = {}
    for col in columns:
        widths[col] = len(col)
    for row in rows:
        for col in columns:
            widths[col] = max(widths[col], len(str(row.get(col, ""))))

    header = "  ".join(col.ljust(widths[col]) for col in columns)
    sep = "  ".join("-" * widths[col] for col in columns)
    print(header)
    print(sep)
    for row in sorted(rows, key=lambda r: r.get("agent_id", 0)):
        line = "  ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns)
        print(line)

def main() -> None:
    load_dotenv(ROOT / ".env")
    start_ts = time.perf_counter()
    tracemalloc.start()
    max_workers = int(os.getenv("AGENT_MAX_WORKERS", str(N_AGENTS)))
    max_workers = max(1, min(max_workers, N_AGENTS))
    rows: List[Dict[str, Any]] = []
    host = StreetViewHostClient()
    try:
        host.start("bootstrap", api_key=os.getenv("GOOGLE_MAPS_API_KEY"))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i in range(N_AGENTS):
                lat, lng = COORDS[i % len(COORDS)]
                futures.append(executor.submit(_run_agent, i, lat, lng, host))
            rows = []
            for future in as_completed(futures):
                rows.append(future.result())
    finally:
        host.close()
    _render_table(rows)
    elapsed = time.perf_counter() - start_ts
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"time_seconds: {elapsed:.2f}")
    print(f"py_mem_current_mb: {current / (1024 * 1024):.2f}")
    print(f"py_mem_peak_mb: {peak / (1024 * 1024):.2f}")


if __name__ == "__main__":
    main()
