import json
from typing import Dict, Any
from core.exceptions import InvalidStateError, InvalidCommandError

REQUIRED_STATE_KEYS = ("panoId", "pov", "links")
REQUIRED_POV_KEYS = ("heading", "pitch", "zoom")

def parse_state(state_json: str) -> Dict[str, Any]:
    # Parse and validate the state JSON
    try:
        state = json.loads(state_json)
    except json.JSONDecodeError as exc:
        raise InvalidStateError("invalid_state_json") from exc

    if not isinstance(state, dict):
        raise InvalidStateError("invalid_state")
    if not all(key in state for key in REQUIRED_STATE_KEYS):
        raise InvalidStateError("missing_state_keys")

    pov = state.get("pov")
    if not isinstance(pov, dict):
        raise InvalidStateError("invalid_pov")
    if not all(key in pov for key in REQUIRED_POV_KEYS):
        raise InvalidStateError("missing_pov_keys")

    links = state.get("links")
    if not isinstance(links, list):
        raise InvalidStateError("invalid_links")

    return state
    
    
def build_command(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    # Construct a JSON command payload
    if method is None or not isinstance(params, dict):
        raise InvalidCommandError("Invalid method or params  ")
    
    command = {
        "method": method,
        "params": params
    }
    return command

def dump_command(cmd: Dict[str, Any]) -> str:
    # Serialize a command payload to JSON
    if not isinstance(cmd, dict):
        raise InvalidCommandError("Invalid command format")
    if "method" not in cmd or "params" not in cmd:
        raise InvalidCommandError("Missing required command keys")
    
    return json.dumps(cmd, separators=(',', ':'))
