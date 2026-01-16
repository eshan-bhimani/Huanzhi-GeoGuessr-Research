from core.tools import nav_tools
import re
import time
from typing import Dict, Any

# ----------------------------
# 1) Tool registry (name -> fn)
# ----------------------------

TOOL_IMPL =  {
    "init_panorama": nav_tools.init_panorama,
    "check_available_moves": nav_tools.check_available_moves,
    "check_direction": nav_tools.check_direction,
    "move_north": nav_tools.move_north,
    "move_northeast": nav_tools.move_northeast,
    "move_east": nav_tools.move_east,
    "move_southeast": nav_tools.move_southeast,
    "move_south": nav_tools.move_south,
    "move_southwest": nav_tools.move_southwest,
    "move_west": nav_tools.move_west,
    "move_northwest": nav_tools.move_northwest,
    "scroll_left": nav_tools.scroll_left,
    "scroll_right": nav_tools.scroll_right,
    "scroll_up": nav_tools.scroll_up,
    "scroll_down": nav_tools.scroll_down,
    "zoom_in": nav_tools.zoom_in,
    "zoom_out": nav_tools.zoom_out,
}
_SHORT = {
    "n": "north", "e": "east", "s": "south", "w": "west",
    "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest",
}

# 2) Policies (robustness + access control)
# - llm_visible=False means: runner can call it, LLM cannot
# - require_image=True means: must produce updates["image_path"]
# ----------------------------
TOOL_POLICY = {
    "init_panorama": {"retries": 0, "backoff_s": 0.10, "require_image": True,  "llm_visible": False},
    "check_available_moves": {"retries": 0, "backoff_s": 0.00, "require_image": False, "llm_visible": True},
    "check_direction": {"retries": 0, "backoff_s": 0.00, "require_image": False, "llm_visible": True},

    # Action tools: allow retries; require image for vision loop
    "move_north": {"retries": 2, "backoff_s": 0.25, "require_image": True, "llm_visible": True},
    "move_northeast": {"retries": 2, "backoff_s": 0.25, "require_image": True, "llm_visible": True},
    "move_east": {"retries": 2, "backoff_s": 0.25, "require_image": True, "llm_visible": True},
    "move_southeast": {"retries": 2, "backoff_s": 0.25, "require_image": True, "llm_visible": True},
    "move_south": {"retries": 2, "backoff_s": 0.25, "require_image": True, "llm_visible": True},
    "move_southwest": {"retries": 2, "backoff_s": 0.25, "require_image": True, "llm_visible": True},
    "move_west": {"retries": 2, "backoff_s": 0.25, "require_image": True, "llm_visible": True},
    "move_northwest": {"retries": 2, "backoff_s": 0.25, "require_image": True, "llm_visible": True},

    "scroll_left": {"retries": 1, "backoff_s": 0.15, "require_image": True, "llm_visible": True},
    "scroll_right": {"retries": 1, "backoff_s": 0.15, "require_image": True, "llm_visible": True},
    "scroll_up": {"retries": 1, "backoff_s": 0.15, "require_image": True, "llm_visible": True},
    "scroll_down": {"retries": 1, "backoff_s": 0.15, "require_image": True, "llm_visible": True},

    "zoom_in": {"retries": 1, "backoff_s": 0.15, "require_image": True, "llm_visible": True},
    "zoom_out": {"retries": 1, "backoff_s": 0.15, "require_image": True, "llm_visible": True},
}

def _normalize_tool_name(name: str) -> str:
    raw = (name or "").strip().lower()
    raw = re.sub(r"[^\w_]", "", raw)  # remove ?, commas, etc.
    if raw.startswith("move_"):
        short = {"n": "north", "e": "east", "s": "south", "w": "west",
                 "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest"}
        suffix = raw[5:]
        if suffix in short:
            return f"move_{short[suffix]}"
    return raw
def _policy_for(tool_name: str) ->  Dict[str, Any]:
    # default policy for unknown tools in registry
    return TOOL_POLICY.get(tool_name, {"retries": 0, "backoff_s": 0.10, "require_image": True, "llm_visible": True})

def _is_llm_call(ctx) -> bool:
    """
    Runner should set:
      ctx.meta["caller"] = "llm"   when dispatching model tool calls
      ctx.meta["caller"] = "runner" when doing internal init/reset
    """
    try:
        return (ctx.meta or {}).get("caller") == "llm"
    except Exception:
        return False
    
 
# ----------------------------
# 4) Main dispatcher: wrapper lives HERE
# ----------------------------
def run_tool(ctx, name: str, args: dict):
    tool_name = _normalize_tool_name(name)
    func = TOOL_IMPL.get(tool_name)
    if not func:
        raise KeyError(f"unknown_tool:{tool_name}")

    policy = _policy_for(tool_name)

    # Block internal-only tools from LLM
    if policy.get("llm_visible") is False and _is_llm_call(ctx):
        raise PermissionError(f"tool_not_allowed_for_llm:{tool_name}")

    retries = int(policy.get("retries", 0))
    backoff_s = float(policy.get("backoff_s", 0.10))
    require_image = bool(policy.get("require_image", True))

    last_res = None
    last_exc = None

    for attempt in range(retries + 1):
        try:
            last_res = func(ctx, args)  # keep your existing tool signature

            # Enforce image presence for action tools (vision loop)
            if require_image:
                updates = getattr(last_res, "updates", None) or {}
                image_path = updates.get("image_path")
                ok = bool(getattr(last_res, "ok", False))
                if not ok or not image_path:
                    time.sleep(backoff_s * (attempt + 1))
                    continue

            return last_res

        except Exception as exc:
            last_exc = exc
            time.sleep(backoff_s * (attempt + 1))

    # If all retries failed, re-raise with context (or return last_res if you prefer)
    if last_exc is not None:
        raise RuntimeError(f"tool_failed:{tool_name} after {retries+1} attempts: {last_exc}") from last_exc
    return last_res

# ----------------------------
# 5) Helper for building LLM-visible tool list
# (Use this when generating tools schema for the model)
# ----------------------------
def llm_visible_tool_names():
    return [name for name in TOOL_IMPL.keys() if _policy_for(name).get("llm_visible") is not False]