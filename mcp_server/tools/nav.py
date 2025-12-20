from typing import Any, Dict, List
import asyncio
from mcp_server.backend_client import BackendClient



SCROLL_ROTATE_STEP = 30.0  # degrees
SCROLL_BACK_ROTATION = 180.0  # degrees
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

class NavTools:
    """Navigation helpers that emit backend instructions."""
    def __init__(self, backend_client: BackendClient | None = None) -> None:
        """Create a NavTools instance with an optional backend client."""
        self.backend = backend_client or BackendClient()
    
    def _deliver_instruction(self, instr: Dict[str, Any]) -> None:
        """
        Best-effort push of the instruction to the backend for the frontend to poll.
        """
        try:
            self.backend.push_instruction(instr)
        except Exception as exc:
            # Log and continue; we still return the instruction to the caller.
            print(f"[NavTools] Failed to deliver instruction: {exc}")
    
    async def _get_state(self) -> Dict[str, Any]:
        """Fetch the latest state snapshot from the backend."""
        return await asyncio.to_thread(self.backend.get_state)
    
    # State helpers
    async def check_direction(self):
        """Return the current heading and compass direction."""
        state = await self._get_state()
        heading = float(state.get("current_heading", 0.0))
        compass = helper_heading_to_direction(heading)
        return {"heading": heading, "direction": compass, "description": f"Facing {compass} ({heading:.1f} deg)"}
    
    async def check_available_moves(self):
        """List available move actions plus universal scroll/zoom actions."""
        state = await self._get_state()
        current_heading = float(state.get("current_heading", 0.0))
        available_steps = state.get("available_moves", [])
        move_actions = []
        for m in available_steps:
            move_heading = m["heading"]
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
        return {
            "universal_actions": universal_actions,
            "move_actions": move_actions,
            "total_actions": len(universal_actions) + len(move_actions),
        }

    # Move helpers (instructions only)
    async def _move_and_instruct(self, direction_key: str):
        """Pick a move in the given cone and emit an instruction."""
        state = await self._get_state()
        moves = state.get("available_moves", [])
        cones = DIR_CONES[direction_key]
        candidates = [m for m in moves if _in_cone(m["heading"], cones)]

        if not candidates:
            return {"error": f"no moves in {direction_key} cone"}

        target = candidates[0]
        target_pano = target["next_node_id"]
        target_heading = target["heading"]
        result = {
            "action": "move",
            "direction": direction_key,
            "target_pano_id": target_pano,
            "move_heading": target_heading,
            "relative_heading": (target_heading - float(state.get("current_heading", 0))) % 360,
            "note": "Frontend must call AgentEnv.moveToPano(target_pano_id, move_heading) then POST the new observation to /step to refresh state/image."
        }
        await asyncio.to_thread(self._deliver_instruction, result)
        return result
    
    async def move_north(self):
        """Move to a pano in the N cone."""
        return await self._move_and_instruct("N")
    async def move_northeast(self):
        """Move to a pano in the NE cone."""
        return await self._move_and_instruct("NE")
    async def move_east(self):
        """Move to a pano in the E cone."""
        return await self._move_and_instruct("E")
    async def move_southeast(self):
        """Move to a pano in the SE cone."""
        return await self._move_and_instruct("SE")
    async def move_south(self):
        """Move to a pano in the S cone."""
        return await self._move_and_instruct("S")
    async def move_southwest(self):
        """Move to a pano in the SW cone."""
        return await self._move_and_instruct("SW")
    async def move_west(self):
        """Move to a pano in the W cone."""
        return await self._move_and_instruct("W")
    async def move_northwest(self):
        """Move to a pano in the NW cone."""
        return await self._move_and_instruct("NW")


    # Scroll functions
    async def scroll_left(self):
        """Rotate the view left by a fixed heading step."""
        state = await self._get_state()
        current = float(state.get("current_heading", 0.0))
        new_heading = (current - SCROLL_ROTATE_STEP) % 360
        result = {
            "type": "scroll",
            "axis": "heading",
            "old": current,
            "new": new_heading,
            "delta": -SCROLL_ROTATE_STEP,
            "note": "Frontend: set POV heading to new, same pano; then POST observation to /step to refresh."
        }
        await asyncio.to_thread(self._deliver_instruction, result)
        return result
    
    async def scroll_right(self):
        """Rotate the view right by a fixed heading step."""
        state = await self._get_state()
        current = float(state.get("current_heading", 0.0))
        new_heading = (current + SCROLL_ROTATE_STEP) % 360
        result = {
            "type": "scroll",
            "axis": "heading",
            "old": current,
            "new": new_heading,
            "delta": SCROLL_ROTATE_STEP,
            "note": "Frontend: set POV heading to new, same pano; then POST observation to /step to refresh."
        }
        await asyncio.to_thread(self._deliver_instruction, result)
        return result

    async def scroll_up(self):
        """Tilt the view up by a fixed pitch step."""
        state = await self._get_state()
        current = float(state.get("pitch", 0.0))
        new_pitch = min(current + SCROLL_UP_PITCH_STEP, 90.0)
        result = {
            "type": "scroll",
            "axis": "pitch",
            "old": current,
            "new": new_pitch,
            "delta": SCROLL_UP_PITCH_STEP,
            "note": "Frontend: set POV pitch to new, same pano; then POST observation to /step to refresh."
        }
        await asyncio.to_thread(self._deliver_instruction, result)
        return result

    async def scroll_down(self):
        """Tilt the view down by a fixed pitch step."""
        state = await self._get_state()
        current = float(state.get("pitch", 0.0))
        new_pitch = max(current - SCROLL_UP_PITCH_STEP, -90.0)
        result = {
            "type": "scroll",
            "axis": "pitch",
            "old": current,
            "new": new_pitch,
            "delta": -SCROLL_UP_PITCH_STEP,
            "note": "Frontend: set POV pitch to new, same pano; then POST observation to /step to refresh."

        }
        await asyncio.to_thread(self._deliver_instruction, result)
        return result

    # Zoom functions

    async def zoom_in(self):
        """Zoom in by a fixed step."""
        state = await self._get_state()
        current = float(state.get("zoom", 1.0))
        new_zoom = current + ZOOM_STEP
        result = {
            "type": "zoom",
            "old": current,
            "new": new_zoom,
            "delta": ZOOM_STEP,
            "note": "Frontend: set zoom to new; POST observation to /step to refresh."
        }
        await asyncio.to_thread(self._deliver_instruction, result)
        return result

    async def zoom_out(self):
        """Zoom out by a fixed step, clamped at zero."""
        state = await self._get_state()
        current = float(state.get("zoom", 1.0))
        new_zoom = max(current - ZOOM_STEP, 0.0)
        result = {
            "type": "zoom",
            "old": current,
            "new": new_zoom,
            "delta": -ZOOM_STEP,
            "note": "Frontend: set zoom to new; POST observation to /step to refresh."
        }
        await asyncio.to_thread(self._deliver_instruction, result)
        return result
