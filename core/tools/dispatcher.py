from core.tools import nav_tools
import re
from typing import List

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

def run_tool(ctx, name: str, args: dict):
    name = _normalize_tool_name(name)
    func = TOOL_IMPL.get(name)
    if not func:
        raise KeyError(f"unknown_tool:{name}")
    return func(ctx, args)


def llm_visible_tool_names() -> List[str]:
    return [name for name in TOOL_IMPL.keys() if name != "init_panorama"]
