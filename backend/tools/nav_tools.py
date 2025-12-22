from typing import Any, Dict, List
from .contracts import ToolContext, ToolResult
from .registry import register_tool



SCROLL_ROTATE_STEP = 30.0  # degrees
SCROLL_UP_PITCH_STEP = 15.0  # degrees (optional)
ZOOM_STEP = 0.5

# heading cones
DIR_CONES = {
    "N":  [(337.5, 360.0), (0.0, 22.5)],
    "NE": [(22.5, 67.5)],
    "E":  [(67.5, 112.5)],
    "SE": [(112.5, 157.5)],
    "S":  [(157.5, 202.5)],
    "SW": [(202.5, 247.5)],
    "W":  [(247.5, 292.5)],
    "NW": [(292.5, 337.5)],
}
def helper_heading_to_direction(angle: float) -> str:
    """
    Convert a compass heading angle (0-360) into
    one of 8 direction labels: N, NE, E, SE, S, SW, W, NW.
    """
    angle = angle % 360  # normalize

    if (angle >= 337.5) or (angle < 22.5):
        return "N"
    elif 22.5 <= angle < 67.5:
        return "NE"
    elif 67.5 <= angle < 112.5:
        return "E"
    elif 112.5 <= angle < 157.5:
        return "SE"
    elif 157.5 <= angle < 202.5:
        return "S"
    elif 202.5 <= angle < 247.5:
        return "SW"
    elif 247.5 <= angle < 292.5:
        return "W"
    elif 292.5 <= angle < 337.5:
        return "NW"
    return "N"

def _in_cone(h: float, cones: List[tuple[float, float]]) -> bool:
    """Return True if a heading is within any cone range."""
    h = h % 360
    for lo, hi in cones:
        if lo <= hi and lo <= h <= hi:
            return True
        if lo > hi and (h >= lo or h <= hi):  # wrap
            return True
    return False

def _get_moves(ctx: ToolContext) -> List[Dict[str, Any]]:
    return ctx.meta.get("available_moves", []) or []

def _current_heading(ctx: ToolContext) -> float:
    return float(ctx.heading or 0.0)

@register_tool("check_direction")
def check_direction(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    heading = _current_heading(ctx)
    compass = helper_heading_to_direction(heading)
    return ToolResult(updates={
        "heading": heading,
        "direction": compass,
        "description": f"Facing {compass} ({heading:.1f} deg)",
    })

@register_tool("check_available_moves")
def check_available_moves(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    current_heading = _current_heading(ctx)
    moves = _get_moves(ctx)
    move_actions = []
    for m in moves:
        move_heading = float(m["heading"])
        rel = (move_heading - current_heading + 360) % 360
        direction = helper_heading_to_direction(move_heading)
        move_actions.append({
            "action": f"move_{direction}",
            "target_pano_id": m["next_node_id"],
            "move_heading": move_heading,
            "relative_heading": rel,
            "compass": direction,
        })
    universal_actions = [
        {"action": "scroll_up"},
        {"action": "scroll_left"},
        {"action": "scroll_right"},
        {"action": "scroll_down"},
        {"action": "zoom_in"},
        {"action": "zoom_out"},
    ]
    return ToolResult(updates={
        "universal_actions": universal_actions,
        "move_actions": move_actions,
        "total_actions": len(universal_actions) + len(move_actions),
    })



def _move_and_instruct(ctx: ToolContext, direction_key: str) -> ToolResult:
    moves = _get_moves(ctx)
    if not moves:
        return ToolResult(ok=False, debug={"error": "no available moves"})
    
    candidates = [m for m in moves if _in_cone (m["heading"], DIR_CONES[direction_key])]
    if not candidates:
        return  ToolResult(ok=False, debug={"error": f"no moves in {direction_key} cone"})
    
    target = candidates[0]
    target_heading = float(target["heading"])
    current_heading = _current_heading(ctx)

    instruction = {
        "action": "move",
        "direction": direction_key,
        "target_pano_id": target["next_node_id"],
        "move_heading": target_heading,
        "relative_heading": (target_heading - current_heading) % 360,
    }
    return ToolResult(instruction=instruction)

@register_tool("move_north")
def move_north(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    return _move_and_instruct(ctx, "N")

@register_tool("move_northeast")
def move_northeast(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    return _move_and_instruct(ctx, "NE")

@register_tool("move_east")
def move_east(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    return _move_and_instruct(ctx, "E")

@register_tool("move_southeast")
def move_southeast(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    return _move_and_instruct(ctx, "SE")

@register_tool("move_south")
def move_south(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    return _move_and_instruct(ctx, "S")

@register_tool("move_southwest")
def move_southwest(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    return _move_and_instruct(ctx, "SW")

@register_tool("move_west")
def move_west(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    return _move_and_instruct(ctx, "W")

@register_tool("move_northwest")
def move_northwest(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    return _move_and_instruct(ctx, "NW")

@register_tool("scroll_left")
def scroll_left(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    current = _current_heading(ctx)
    new_heading = (current - SCROLL_ROTATE_STEP) % 360
    return ToolResult(instruction= {
        "type": "scroll",
        "axis": "heading",
        "old": current, 
        "new": new_heading,
        "delta": -SCROLL_ROTATE_STEP,
    })

@register_tool("scroll_right")
def scroll_right(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    """Rotate the view right by a fixed heading step."""
    current = _current_heading(ctx)
    new_heading = (current + SCROLL_ROTATE_STEP) % 360
    return ToolResult(instruction= {
        "type": "scroll",
        "axis": "heading",
        "old": current, 
        "new": new_heading,
        "delta": SCROLL_ROTATE_STEP,
    })

@register_tool("scroll_up")
def scroll_up(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    """Tilt the view up by a fixed pitch step."""
    current = float(ctx.meta.get("pitch", 0.0))
    new_pitch = min(current + SCROLL_UP_PITCH_STEP, 90.0)
    return ToolResult(instruction ={
        "type": "scroll",
        "axis": "pitch",
        "old": current,
        "new": new_pitch,
        "delta": SCROLL_UP_PITCH_STEP,
    })

@register_tool("scroll_down")
def scroll_down(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    """Tilt the view down by a fixed pitch step."""
    current = float(ctx.meta.get("pitch", 0.0))
    new_pitch = max(current - SCROLL_UP_PITCH_STEP, -90.0)
    return ToolResult(instruction ={
        "type": "scroll",
        "axis": "pitch",
        "old": current,
        "new": new_pitch,
        "delta": -SCROLL_UP_PITCH_STEP,
    })

@register_tool("zoom_in")
def zoom_in(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    current = float(ctx.meta.get("zoom", 1.0))
    new_zoom = current + ZOOM_STEP
    return ToolResult(instruction={
        "type": "zoom",
        "old": current,
        "new": new_zoom,
        "delta": ZOOM_STEP,
    })

@register_tool("zoom_out")
def zoom_out(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    current = float(ctx.meta.get("zoom", 1.0))
    new_zoom = max(current - ZOOM_STEP, 0.0)
    return ToolResult(instruction={
        "type": "zoom",
        "old": current,
        "new": new_zoom,
        "delta": -ZOOM_STEP,
    }) 
