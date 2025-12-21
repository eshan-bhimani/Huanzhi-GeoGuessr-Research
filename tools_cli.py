import argparse
import json
import sys
from typing import Any, Dict

import requests

from backend.tools import ToolContext, call_tool

# Register tool implementations.
import backend.tools.info_tools  # noqa: F401
import backend.tools.nav_tools  # noqa: F401


ALIASES: Dict[str, str] = {
    "move_north": "move_north",
    "move_south": "move_south",
    "move_east": "move_east",
    "move_west": "move_west",
    "move_northeast": "move_northeast",
    "move_northwest": "move_northwest",
    "move_southeast": "move_southeast",
    "move_southwest": "move_southwest",
    "north": "move_north",
    "south": "move_south",
    "east": "move_east",
    "west": "move_west",
    "ne": "move_northeast",
    "nw": "move_northwest",
    "se": "move_southeast",
    "sw": "move_southwest",
    "scroll_left": "scroll_left",
    "scroll_right": "scroll_right",
    "scroll_up": "scroll_up",
    "scroll_down": "scroll_down",
    "zoom_in": "zoom_in",
    "zoom_out": "zoom_out",
    "check_direction": "check_direction",
    "check_available_moves": "check_available_moves",
    "get_observation": "get_observation",
    "get_image": "get_image",
}


def normalize_command(text: str) -> str:
    return "_".join(text.strip().lower().split())


def fetch_state(api_base: str) -> Dict[str, Any]:
    resp = requests.get(f"{api_base}/environment/state", timeout=10)
    resp.raise_for_status()
    return resp.json()


def build_context(state: Dict[str, Any]) -> ToolContext:
    metadata = state.get("metadata") or {}
    history = list(metadata.get("history") or [])
    meta = dict(metadata)
    meta.update(
        {
            "available_moves": state.get("available_moves") or [],
            "image": state.get("image"),
            "state": state,
        }
    )
    return ToolContext(
        session_id="default",
        node_id=state.get("current_node_id"),
        gps=state.get("gps"),
        heading=state.get("current_heading"),
        history=history,
        meta=meta,
    )


def push_instruction(api_base: str, instruction: Dict[str, Any]) -> None:
    resp = requests.post(
        f"{api_base}/instruction/push", json=instruction, timeout=10
    )
    resp.raise_for_status()


def shorten(value: Any, max_len: int = 140) -> Any:
    if isinstance(value, str) and len(value) > max_len:
        return f"{value[:max_len]}... ({len(value)} chars)"
    return value


def scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return shorten(value)


def print_json(data: Any) -> None:
    print(json.dumps(scrub(data), indent=2))


def print_help() -> None:
    print("Commands:")
    print("  move north|south|east|west")
    print("  move ne|nw|se|sw")
    print("  scroll left|right|up|down")
    print("  zoom in|out")
    print("  check direction")
    print("  check available moves")
    print("  get observation")
    print("  get image")
    print("  state")
    print("  help")
    print("  exit")


def main() -> int:
    parser = argparse.ArgumentParser(description="CLI for backend navigation tools")
    parser.add_argument(
        "--api-base",
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    api_base = args.api_base.rstrip("/")
    print(f"Backend: {api_base}")
    print("Type 'help' for commands.")

    while True:
        try:
            raw = input("cmd> ")
        except EOFError:
            print()
            return 0

        cmd = normalize_command(raw)
        if not cmd:
            continue
        if cmd in ("exit", "quit"):
            return 0
        if cmd in ("help", "?"):
            print_help()
            continue
        if cmd in ("state", "env"):
            try:
                print_json(fetch_state(api_base))
            except Exception as exc:
                print(f"State error: {exc}")
            continue

        tool_name = ALIASES.get(cmd)
        if not tool_name:
            print("Unknown command. Type 'help' to list commands.")
            continue

        try:
            state = fetch_state(api_base)
            ctx = build_context(state)
            result = call_tool(tool_name, ctx, {})
        except Exception as exc:
            print(f"Tool error: {exc}")
            continue

        if result.instruction:
            try:
                push_instruction(api_base, result.instruction)
                print("Instruction pushed:")
                print_json(result.instruction)
            except Exception as exc:
                print(f"Push error: {exc}")
        else:
            payload = {
                "ok": result.ok,
                "updates": result.updates,
                "debug": result.debug,
            }
            print_json(payload)


if __name__ == "__main__":
    sys.exit(main())
