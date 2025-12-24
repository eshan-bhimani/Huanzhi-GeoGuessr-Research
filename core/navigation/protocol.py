import json
from typing import Dict, Any

REQUIRED_STATE_KEYS = ("panoId", "pov", "links")
REQUIRED_POV_KEYS = ("heading", "pitch", "zoom")

def parse_state(state_json: str) -> Dict[str, Any]:
    # Parse and validate the state JSON
    try:
        state = json.loads(state_json)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_state_json") from exc

    if not isinstance(state, dict):
        raise ValueError("invalid_state")
    if not all(key in state for key in REQUIRED_STATE_KEYS):
        raise ValueError("missing_state_keys")

    pov = state.get("pov")
    if not isinstance(pov, dict):
        raise ValueError("invalid_pov")
    if not all(key in pov for key in REQUIRED_POV_KEYS):
        raise ValueError("missing_pov_keys")

    links = state.get("links")
    if not isinstance(links, list):
        raise ValueError("invalid_links")

    return state
    
    
def build_command(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    # Construct a JSON command payload
    if method is None or not isinstance(params, dict):
        raise ValueError("Invalid method or params  ")
    
    command = {
        "method": method,
        "params": params
    }
    return command

def dump_command(cmd: Dict[str, Any]) -> str:
    # Serialize a command payload to JSON
    if not isinstance(cmd, dict):
        raise ValueError("Invalid command format")
    if "method" not in cmd or "params" not in cmd:
        raise ValueError("Missing required command keys")
    
    return json.dumps(cmd, separators=(',', ':'))
