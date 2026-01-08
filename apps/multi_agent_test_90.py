from __future__ import annotations

import json
import os
import psutil
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
COORDS: List[Tuple[float, float]] = [
    (38.88918843, -77.02835864),
    (40.741, -73.9896),
    (33.9857, -118.4732),
    (41.8827, -87.6233),
    (37.8024, -122.4183),
    (33.749, -84.388),
    (47.6101, -122.3422),
    (29.9572, -90.0644),
    (42.3467, -71.0972),
    (36.1127, -115.1729),
    (30.2747, -97.7404),
    (39.9496, -75.1503),
    (39.7392, -104.9903),
    (36.1627, -86.7816),
    (25.7814, -80.1309),
    (45.5202, -122.6742),
    (21.2793, -157.8293),
    (32.0809, -81.0912),
    (48.8606, 2.3376),
    (51.5055, -0.0754),
    (41.4036, 2.1744),
    (41.8902, 12.4922),
    (52.3676, 4.9041),
    (37.9715, 23.7266),
    (41.0055, 28.9769),
    (55.7539, 37.6208),
    (53.2236, -4.1981),
    (66.5432, 25.8467),
    (51.5628, -1.7715),
    (52.5163, 13.3777),
    (50.0865, 14.4114),
    (48.2085, 16.3738),
    (45.4341, 12.3388),
    (53.3445, -6.2673),
    (55.6795, 12.5892),
    (50.8467, 4.3525),
    (35.6598, 139.7006),
    (25.1972, 55.2744),
    (1.2868, 103.8545),
    (13.75, 100.4915),
    (22.2793, 114.1628),
    (31.2397, 121.4993),
    (37.5795, 126.977),
    (18.922, 72.8347),
    (35.0117, 135.7681),
    (25.033, 121.5654),
    (3.1579, 101.7116),
    (-6.1751, 106.865),
    (21.0285, 105.8542),
    (28.6562, 77.241),
    (14.5932, 120.9825),
    (36.0544, -112.1401),
    (44.428, -110.5885),
    (37.7459, -119.5332),
    (43.8791, -103.4591),
    (40.6892, -74.0445),
    (43.0828, -79.0742),
    (38.7331, -109.5925),
    (37.8199, -122.4783),
    (44.5902, -104.7151),
    (-45.874, 170.5036),
    (35.9992, -78.91),
    (35.7521, -83.9643),
    (69.6492, 18.9553),
    (-54.8019, -68.303),
    (78.2232, 15.6267),
    (-23.698, 133.8807),
    (64.1466, -21.9426),
    (-43.5321, 172.6362),
    (-3.7437, -73.2516),
    (64.1814, -51.6941),
    (61.2181, -149.9003),
    (64.8378, -147.7164),
    (45.677, -111.0429),
    (46.8772, -96.7898),
    (44.4759, -73.2121),
    (43.263, -2.935),
    (41.1579, -8.6291),
    (50.0647, 19.945),
    (59.437, 24.7536),
    (56.9496, 24.1052),
    (54.6872, 25.2797),
    (46.0569, 14.5058),
    (42.6507, 18.0944),
    (43.8563, 18.4131),
    (41.7151, 44.8271),
    (27.7172, 85.324),
    (47.8864, 106.9057),
    (-0.1807, -78.4678),
    (-16.5, -68.15),
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
            for agent_id, (lat, lng) in enumerate(COORDS):
                futures.append(executor.submit(_run_agent, agent_id, lat, lng, host))
            rows = []
            for future in as_completed(futures):
                rows.append(future.result())
    finally:
        host.close()
    _render_table(rows)
    total_steps = sum(int(row.get("steps_done") or 0) for row in rows)
    ok_agents = sum(1 for row in rows if row.get("ok"))
    print(f"agents_total: {N_AGENTS}")
    print(f"agents_completed: {len(rows)}")
    print(f"agents_ok: {ok_agents}")
    print(f"steps_total: {total_steps}")
    elapsed = time.perf_counter() - start_ts
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"time_seconds: {elapsed:.2f}")
    print(f"py_mem_current_mb: {current / (1024 * 1024):.2f}")
    print(f"py_mem_peak_mb: {peak / (1024 * 1024):.2f}")
    process = psutil.Process(os.getpid())
    print(f"rss_mb: {process.memory_info().rss / (1024 * 1024):.2f}")


if __name__ == "__main__":
    main()
