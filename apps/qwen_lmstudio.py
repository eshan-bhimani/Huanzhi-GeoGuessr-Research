"""
LM Studio API for vision+tools pipeline

What this version does:
- True Chat Completions tool loop:
  1) model -> tool_call(s)
  2) execute tool
  3) append role="tool" message with tool_call_id + JSON output
  4) append next role="user" message that includes the *latest* image (base64 data URL)
  5) call model again

-  When history grows, summarize older messages into ONE summary message,
  while keeping the most recent turns verbatim.
- Base64 is still sent ONLY for the latest frame (each step's user message).
- available_moves preserved from tool updates.
- Logs under ./runs/<session_id>/events.jsonl
- Images under ./images/<session_id>/... (your tool host controls actual filenames)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from dotenv import load_dotenv
from openai import OpenAI

# ---- your repo imports ----
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapters.streetview_js.client import StreetViewHostClient
from core.tools.contracts import ToolContext, ToolResult
from core.tools.dispatcher import run_tool, llm_visible_tool_names
from core.tools.registry import TOOL_SPECS


# ===========================
# Configuration Constants
# ===========================
DEFAULT_MAX_STEPS = 50
DEFAULT_ZOOM_DELTA = 30
DEFAULT_RETRIES = 4
DEFAULT_RETRY_BACKOFF_S = 0.25

# Reasoning validation
MIN_REASONING_FIELD_LENGTH = 5
REQUIRED_REASONING_FIELDS = ["observation", "progress", "uncertainty", "intent"]
VALID_PROGRESS_VALUES = {"forward", "backward", "no_progress"}

# Summarization thresholds
DEFAULT_SUMMARIZE_MSG_THRESHOLD = 40
DEFAULT_SUMMARIZE_CHARS_THRESHOLD = 30000
DEFAULT_KEEP_LAST_MESSAGES = 14
MAX_SUMMARY_TRANSCRIPT_CHARS = 6000

# Image trimming (referenced in comments, defined here for completeness)
IMAGE_TRIM_BOTTOM_PX = 60  # Remove Google logo


# ===========================
# Configuration Models
# ===========================
@dataclass
class EpisodeConfig:
    """Configuration for a single episode run"""
    lat: float
    lng: float
    question: str
    max_steps: int = DEFAULT_MAX_STEPS

    # Summarization
    summarize_when_msgs_over: int = DEFAULT_SUMMARIZE_MSG_THRESHOLD
    summarize_when_chars_over: int = DEFAULT_SUMMARIZE_CHARS_THRESHOLD
    keep_last_for_summary: int = DEFAULT_KEEP_LAST_MESSAGES

    # Paths
    run_id: str = None
    out_root: Path = Path("runs")
    images_root: Path = Path("images")

    # LM Studio config
    endpoint: str = None
    api_key: str = None
    model: str = "qwen2.5-vl-7b-instruct"

    def __post_init__(self):
        """Generate run_id if not provided"""
        if self.run_id is None:
            self.run_id = f"session_{int(time.time())}"

        # Ensure Path objects
        if not isinstance(self.out_root, Path):
            self.out_root = Path(self.out_root)
        if not isinstance(self.images_root, Path):
            self.images_root = Path(self.images_root)

    @property
    def run_dir(self) -> Path:
        """Computed property for run directory"""
        return self.out_root / self.run_id

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "EpisodeConfig":
        """Create config from parsed CLI arguments"""
        return cls(
            lat=args.lat,
            lng=args.lng,
            question=args.question,
            max_steps=args.max_steps,
            summarize_when_msgs_over=args.summarize_when_msgs_over,
            summarize_when_chars_over=args.summarize_when_chars_over,
            keep_last_for_summary=args.keep_last_for_summary,
            run_id=args.run_id,
            out_root=Path(args.out_root),
            images_root=Path(args.images_root),
            endpoint=args.endpoint,
            api_key=args.api_key,
            model=args.model,
        )


# ===========================
# Prompts
# ===========================
SYSTEM_PROMPT = """You navigate Street View to answer the Task using visual evidence from the images.

Goal: identify the correct answer by moving and looking for signs, landmarks, road features, and building names. Use only what you can see.

Available moves are provided in the user message each step. When moving, choose a move action that matches the available moves.

Tools: rotate/scroll, zoom, move, final_answer.

For every action, include a reasoning object:
- observation: what is visible in the image
- progress: forward | backward | no_progress
- uncertainty: what is unclear
- intent: what you want to learn next

IMPORTANT STRATEGY:
- ALWAYS explore your surroundings BEFORE moving (scroll/rotate 360° to see all directions)
- Use SMALL scroll deltas (15-30 degrees) to carefully scan - large jumps (45°+) miss important details
- Look for signs, landmarks, distance markers, and informational boards
- Zoom in to read text on signs and plaques when you spot them
- Only move when you have a clear reason based on visual evidence
- Avoid repeatedly moving in the same direction without gathering new information

When you are confident, use final_answer(answer="...").
Return exactly ONE tool call.
"""

SUMMARY_SYSTEM = """You are a summarizer for an agentic Street View navigation run.
Summarize the conversation so far into a compact, factual memory the agent should keep.
Keep it short and actionable: what was tried, what was seen, what remains uncertain, and current hypothesis.
Do NOT invent signs/landmarks. If unknown, say unknown.
"""

# ===========================
# User text builder
# ===========================
def build_user_text(
    question: str,
    step: int,
    available_moves: Optional[List[str]],
    recent_context_lines: Optional[List[str]] = None,
) -> str:
    moves_block = ""
    if available_moves:
        moves_block = "Available moves now: " + ", ".join(available_moves)

    ctx_block = ""
    if recent_context_lines:
        ctx_block = "Recent context:\n" + "\n".join(f"- {x}" for x in recent_context_lines)

    return f"""Task: {question}
Step: {step}

{moves_block}
{ctx_block}

Return exactly ONE tool call.
- Use a navigation tool (scroll/zoom/move) to gather evidence, OR
- Use final_answer(answer="...") when you are confident.
"""



# ===========================
# Logging
# ===========================
def log_event(log_path: Path, event: dict) -> None:
    event["ts"] = time.time()
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


# ===========================
# Image encoding (base64 URL)
# ===========================
def encode_image_data_url(image_path: str) -> str:
    p = Path(image_path)
    suffix = p.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


# ===========================
# Tool spec filtering + reasoning injection
# ===========================
def inject_reasoning_into_tools(specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add a required `reasoning` object to EACH tool schema the LLM can call.
    IMPORTANT:
      - This does NOT affect available_moves (that comes from tool updates).
      - We also make 'reasoning' required at the TOP LEVEL of tool parameters.
    """
    patched: List[Dict[str, Any]] = []
    for spec in specs:
        fn = spec.get("function", {})
        params = fn.get("parameters", {}) or {}
        props = params.get("properties", {}) or {}

        props["reasoning"] = {
            "type": "object",
            "properties": {
                "observation": {"type": "string", "minLength": 5},
                "progress": {"type": "string", "enum": ["forward", "backward", "no_progress"]},
                "uncertainty": {"type": "string", "minLength": 5},
                "intent": {"type": "string", "minLength": 5},
            },
            "required": ["observation", "progress", "uncertainty", "intent"],
            "additionalProperties": False,
        }

        # Make reasoning required at top-level
        req = params.get("required")
        if not isinstance(req, list):
            req = []
        if "reasoning" not in req:
            req.append("reasoning")

        params["properties"] = props
        params["required"] = req
        fn["parameters"] = params
        spec["function"] = fn
        patched.append(spec)

    return patched


def llm_tool_specs() -> List[Dict[str, Any]]:
    allowed = set(llm_visible_tool_names())  # excludes init_panorama
    specs = [s for s in TOOL_SPECS if s.get("function", {}).get("name") in allowed]
    return inject_reasoning_into_tools(specs)


# ===========================
# Map Environment
# ===========================
class MapEnv:
    def __init__(self, host: StreetViewHostClient, session_id: str, image_root: str) -> None:
        self._ctx = ToolContext(
            session_id=session_id,
            meta={
                "host_client": host,
                "image_root": image_root,   # base folder e.g. "images"
                "image_step": 1,
                "caller": "runner",
            },
        )

    def init_panorama(self, lat: float, lng: float, heading: float = 0.0, pitch: float = 0.0, zoom: float = 1.0) -> ToolResult:
        self._ctx.meta["caller"] = "runner"
        return run_tool(
            self._ctx,
            "init_panorama",
            {"lat": lat, "lng": lng, "heading": heading, "pitch": pitch, "zoom": zoom},
        )

    def call_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> ToolResult:
        self._ctx.meta["caller"] = "llm"
        return run_tool(self._ctx, tool_name, tool_args)


# ===========================
# Helpers
# ===========================
def safe_model_dump(msg: Any) -> Dict[str, Any]:
    """
    openai python types usually provide .model_dump().
    fallback: try dict().
    """
    if hasattr(msg, "model_dump"):
        return msg.model_dump()
    try:
        return dict(msg)
    except Exception:
        # last resort: keep minimal fields
        return {"role": getattr(msg, "role", "assistant"), "content": getattr(msg, "content", None)}


def extract_available_moves(updates: Optional[Dict[str, Any]]) -> Optional[List[str]]:
    if not updates:
        return None
    moves = updates.get("available_moves")
    if not isinstance(moves, list):
        return None
    return [str(x).strip().lower() for x in moves if str(x).strip()]


def move_name_from_tool(tool_name: str) -> Optional[str]:
    if tool_name.startswith("move_"):
        return tool_name.replace("move_", "", 1)
    return None


def _final_from_tool_call(tool_name: str, tool_args: Dict[str, Any]) -> Optional[str]:
    normalized = (tool_name or "").strip().lower()
    if normalized not in {"final", "final_answer"}:
        return None
    if isinstance(tool_args, dict):
        for key in ("answer", "final", "text", "content"):
            value = tool_args.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


# ===========================
# Reasoning Validation
# ===========================
class ReasoningValidator:
    """Validates LLM reasoning objects according to schema requirements"""

    @staticmethod
    def is_valid(reasoning: Any) -> bool:
        """
        Check if reasoning object meets all requirements.

        Args:
            reasoning: Reasoning object to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(reasoning, dict):
            return False

        # Check required fields present
        for field in REQUIRED_REASONING_FIELDS:
            if field not in reasoning:
                return False

        # Check field lengths
        if len(str(reasoning["observation"]).strip()) < MIN_REASONING_FIELD_LENGTH:
            return False
        if len(str(reasoning["uncertainty"]).strip()) < MIN_REASONING_FIELD_LENGTH:
            return False
        if len(str(reasoning["intent"]).strip()) < MIN_REASONING_FIELD_LENGTH:
            return False

        # Check progress value
        if str(reasoning["progress"]).strip() not in VALID_PROGRESS_VALUES:
            return False

        return True

    @staticmethod
    def get_error_message(reasoning: Any) -> str:
        """
        Return descriptive error message for invalid reasoning.

        Args:
            reasoning: Reasoning object that failed validation

        Returns:
            Human-readable error message
        """
        if not isinstance(reasoning, dict):
            return "Reasoning must be a dictionary object"

        missing = [f for f in REQUIRED_REASONING_FIELDS if f not in reasoning]
        if missing:
            return f"Missing required fields: {', '.join(missing)}"

        for field in ["observation", "uncertainty", "intent"]:
            if len(str(reasoning.get(field, "")).strip()) < MIN_REASONING_FIELD_LENGTH:
                return f"Field '{field}' is too short (minimum {MIN_REASONING_FIELD_LENGTH} characters)"

        if str(reasoning.get("progress", "")).strip() not in VALID_PROGRESS_VALUES:
            return f"Field 'progress' must be one of: {', '.join(VALID_PROGRESS_VALUES)}"

        return "Unknown validation error"


def invalid_reasoning(r: Any) -> bool:
    """
    DEPRECATED: Use ReasoningValidator.is_valid() instead.

    Check if reasoning object is invalid.

    Args:
        r: Reasoning object to validate

    Returns:
        True if reasoning is invalid, False otherwise
    """
    return not ReasoningValidator.is_valid(r)


# ===========================
# Enforce "only proceed when there is an image"
# ===========================
def exec_tool_until_image(
    env: MapEnv,
    tool_name: str,
    tool_args: Dict[str, Any],
    *,
    retries: int = 4,
    backoff_s: float = 0.25,
    last_image_path: Optional[str] = None,
) -> Tuple[bool, str, Dict[str, Any], Any]:
    """
    Returns: (ok, image_path, updates, debug)
    Guarantees: image_path is never None (fallback to last_image_path).
    """
    last_updates: Dict[str, Any] = {}
    last_debug: Any = None
    last_ok: bool = False

    for attempt in range(retries + 1):
        result = env.call_tool(tool_name, tool_args)
        last_ok = bool(result.ok)
        last_updates = result.updates or {}
        last_debug = result.debug

        image_path = last_updates.get("image_path")
        if image_path:
            return last_ok, image_path, last_updates, last_debug

        time.sleep(backoff_s * (attempt + 1))

    if last_image_path:
        return False, last_image_path, last_updates, {"note": "no new image after retries; using fallback frame", "debug": last_debug}

    raise RuntimeError(
        f"Tool '{tool_name}' failed to produce an image after {retries} retries, "
        f"and no fallback image is available. Check Street View host connection and Google Maps API."
    )


# ===========================
# True chat history: message builders
# ===========================
def make_user_msg_with_image(
    question: str,
    step: int,
    image_path: str,
    available_moves: Optional[List[str]],
    recent_context_lines: Optional[List[str]] = None,
) -> Dict[str, Any]:
    text = build_user_text(question, step, available_moves, recent_context_lines=recent_context_lines)
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": encode_image_data_url(image_path)}},
        ],
    }


def make_tool_msg(tool_call_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": json.dumps(payload, ensure_ascii=False),
    }


# ===========================
#  Summarization
# ===========================
def build_transcript_from_messages(messages: List[Dict[str, Any]]) -> str:
    """
    Extract text content from message history for summarization.

    Args:
        messages: List of chat messages (excludes system prompt)

    Returns:
        Formatted transcript string with role labels
    """
    transcript_lines: List[str] = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")

        if isinstance(content, list):
            # Extract text from multimodal content
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
            content_str = "\n".join([t for t in text_parts if t])
        else:
            content_str = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)

        # Include tool calls if present
        tool_calls = m.get("tool_calls")
        if tool_calls:
            try:
                content_str += "\nTOOL_CALLS=" + json.dumps(tool_calls, ensure_ascii=False)
            except Exception:
                content_str += "\nTOOL_CALLS=[unserializable]"

        if content_str.strip():
            transcript_lines.append(f"{role.upper()}: {content_str.strip()}")

    transcript = "\n\n".join(transcript_lines)

    # Hard cap to avoid huge summary prompt
    if len(transcript) > MAX_SUMMARY_TRANSCRIPT_CHARS:
        transcript = transcript[-MAX_SUMMARY_TRANSCRIPT_CHARS:]

    return transcript


def summarize_history_inplace(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, Any]],
    *,
    keep_last: int = DEFAULT_KEEP_LAST_MESSAGES,
) -> List[Dict[str, Any]]:
    """
    Summarize older messages into ONE compact summary message.

    Args:
        client: OpenAI client instance
        model: Model name for summarization
        messages: Full message history (includes system prompt at index 0)
        keep_last: Number of recent messages to preserve verbatim

    Returns:
        New message list: [system, summary, ...kept_messages]

    Notes:
        - Keeps the initial system prompt (messages[0])
        - Replaces older content (excluding last `keep_last`) with an assistant summary message
        - Does NOT include images in the summarization call (we summarize text/JSON only)
        - Preserves message structure integrity (tool messages must follow assistant tool_calls)
    """
    if len(messages) <= 1 + keep_last:
        return messages

    system = messages[0]

    # Find a safe split point that doesn't break tool call/result pairs
    # Start from the desired split point and move backward until we find a safe boundary
    split_idx = len(messages) - keep_last

    # If the message at split_idx is a tool result, we need to include the preceding assistant message
    # Move the split point backward to include complete assistant+tool pairs
    while split_idx > 1:
        msg = messages[split_idx]
        role = msg.get("role")

        # Safe to split at: user message or assistant without tool_calls
        if role == "user":
            break
        elif role == "assistant" and not msg.get("tool_calls"):
            break

        # Not safe: tool message or assistant with tool_calls
        # Move backward to find a safe boundary
        split_idx -= 1

    # Ensure we keep at least one message
    if split_idx <= 1:
        split_idx = 1

    older = messages[1:split_idx]
    tail = messages[split_idx:]

    transcript = build_transcript_from_messages(older)

    summary_resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM},
            {"role": "user", "content": transcript},
        ],
    )
    summary_text = (summary_resp.choices[0].message.content or "").strip()
    if not summary_text:
        summary_text = "Summary unavailable (empty)."

    summary_msg = {
        "role": "assistant",
        "content": "Conversation summary so far:\n" + summary_text,
    }

    # New message list: system + summary + tail
    return [system, summary_msg, *tail]


def approx_message_chars(messages: List[Dict[str, Any]]) -> int:
    total = 0
    for m in messages:
        c = m.get("content")
        if isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += len(part.get("text", "") or "")
        elif isinstance(c, str):
            total += len(c)
        else:
            try:
                total += len(json.dumps(c, ensure_ascii=False))
            except Exception:
                pass
        # tool calls can add weight
        tc = m.get("tool_calls")
        if tc:
            try:
                total += len(json.dumps(tc, ensure_ascii=False))
            except Exception:
                total += 200
    return total


# ===========================
# Episode Initialization
# ===========================
def initialize_episode(
    env: MapEnv,
    lat: float,
    lng: float,
    question: str,
    log_path: Path,
) -> Tuple[str, Optional[List[str]]]:
    """
    Initialize panorama and return starting image path and available moves.

    Args:
        env: Map environment wrapping StreetView host
        lat: Starting latitude
        lng: Starting longitude
        question: Question to answer
        log_path: Path to events log file

    Raises:
        RuntimeError: If initialization fails

    Returns:
        Tuple of (image_path, available_moves)
    """
    init = env.init_panorama(lat, lng)
    if not init.ok:
        raise RuntimeError(
            f"Failed to initialize Street View panorama at ({lat}, {lng}). "
            f"Details: {init.debug}. Check that coordinates are valid and Google Maps API key is set."
        )

    updates0 = init.updates or {}
    current_image_path = updates0.get("image_path")
    if not current_image_path:
        raise RuntimeError(
            "init_panorama succeeded but returned no image_path. "
            "This indicates an issue with the image capture pipeline."
        )

    available_moves = extract_available_moves(updates0)

    log_event(log_path, {
        "step": 0,
        "type": "init",
        "lat": lat,
        "lng": lng,
        "question": question,
        "ok": init.ok,
        "image_path": current_image_path,
        "available_moves": available_moves,
    })

    return current_image_path, available_moves


# ===========================
# Tool Call Processing
# ===========================
def process_tool_call(
    env: MapEnv,
    messages: List[Dict[str, Any]],
    tool_calls: List[Any],
    available_moves: Optional[List[str]],
    current_image_path: str,
    log_path: Path,
    step: int,
) -> Tuple[bool, str, Optional[str], Optional[List[str]], List[str], Optional[Dict[str, Any]]]:
    """
    Process a single tool call from the model.

    Args:
        env: Map environment
        messages: Chat message history
        tool_calls: List of tool calls from model
        available_moves: Currently available navigation moves
        current_image_path: Path to current image
        log_path: Path to events log
        step: Current step number

    Returns:
        Tuple of (should_continue, new_image_path, final_answer, new_moves, context_lines, reasoning)
        - should_continue: False if episode should end (final answer given)
        - new_image_path: Path to the newly captured image
        - final_answer: Non-None if final_answer tool was called
        - new_moves: Updated available moves after tool execution
        - context_lines: Context for next user message
        - reasoning: The reasoning dict from the tool call (or None)
    """
    tc = tool_calls[0]
    tool_call_id = tc.id
    tool_name = tc.function.name
    raw_args = tc.function.arguments or "{}"

    try:
        tool_args = json.loads(raw_args)
    except Exception:
        tool_args = {}

    log_event(log_path, {
        "step": step,
        "type": "model",
        "tool": tool_name,
        "raw_args": raw_args,
        "available_moves": available_moves,
    })

    # Default delta behavior
    if tool_name.startswith(("scroll_", "zoom_")) and "delta" not in tool_args:
        tool_args = dict(tool_args)
        tool_args["delta"] = DEFAULT_ZOOM_DELTA

    # Check for final answer
    final_from_tool = _final_from_tool_call(tool_name, tool_args)
    if final_from_tool is not None:
        final_text = final_from_tool or "(final_answer tool call without payload)"
        log_event(log_path, {"step": step, "type": "final", "answer": final_text})
        return False, current_image_path, final_text, available_moves, [], None

    # Validate reasoning
    reasoning = tool_args.get("reasoning")
    if invalid_reasoning(reasoning):
        log_event(log_path, {
            "step": step,
            "type": "error",
            "reason": "invalid_reasoning",
            "tool": tool_name,
            "reasoning": reasoning,
        })
        # Remove the assistant message that was just added since we're rejecting the tool call
        messages.pop()
        # Add user correction message
        messages.append({
            "role": "user",
            "content": "Your last tool call was rejected because `reasoning` was missing or too vague. "
                       "Try again with concrete visual reasoning (observation/progress/uncertainty/intent). "
                       "Return exactly ONE tool call.",
        })
        return True, current_image_path, None, available_moves, [], None

    # Validate move
    requested_move = move_name_from_tool(tool_name)
    invalid_move = False
    if requested_move and available_moves:
        # Case-insensitive comparison since backend returns uppercase (move_N) but tools use lowercase (move_north)
        if requested_move.lower() not in {m.lower() for m in available_moves}:
            invalid_move = True

    # Execute tool
    tool_exec_args = dict(tool_args)
    tool_exec_args.pop("reasoning", None)

    ok, new_image_path, upd, dbg = exec_tool_until_image(
        env,
        tool_name,
        tool_exec_args,
        retries=DEFAULT_RETRIES,
        backoff_s=DEFAULT_RETRY_BACKOFF_S,
        last_image_path=current_image_path,
    )

    new_moves = extract_available_moves(upd)

    # Log execution
    log_event(log_path, {
        "step": step,
        "type": "tool",
        "tool": tool_name,
        "ok": ok,
        "invalid_move": invalid_move,
        "available_moves": upd.get("available_moves"),
        "available_moves_after": new_moves,
        "debug": dbg,
        "updates": upd,
        "reasoning": reasoning,
    })

    # Append tool result message
    tool_payload = {
        "ok": ok,
        "invalid_move": invalid_move,
        "updates": upd,
        "debug": dbg,
    }
    messages.append(make_tool_msg(tool_call_id, tool_payload))

    # Build context lines for next user message
    context_lines = []
    if invalid_move and available_moves:
        context_lines.append(f"Note: requested move '{requested_move}' was not in previous available moves.")
    if not ok:
        context_lines.append("Note: tool reported failure; try recovery (scroll/zoom) or a different move.")
    if new_moves:
        context_lines.append("Moves now: " + ", ".join(new_moves))

    return True, new_image_path, None, new_moves, context_lines, reasoning


# ===========================
# Episode runner (TRUE history)
# ===========================
def run_episode(
    env: MapEnv,
    client: OpenAI,
    model: str,
    lat: float,
    lng: float,
    question: str,
    run_dir: Path,
    max_steps: int,
    *,
    summarize_when_msgs_over: int = 40,
    summarize_when_chars_over: int = 30000,
    keep_last_for_summary: int = 14,
) -> None:
    log_path = run_dir / "events.jsonl"
    tools = llm_tool_specs()

    # Step 0: Initialize panorama
    current_image_path, available_moves = initialize_episode(
        env=env,
        lat=lat,
        lng=lng,
        question=question,
        log_path=log_path,
    )

    # TRUE chat history starts here:
    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    # include first user message with the starting image
    messages.append(make_user_msg_with_image(
        question=question,
        step=0,
        image_path=current_image_path,
        available_moves=available_moves,
        recent_context_lines=None,
    ))

    # Track recent actions to detect repetitive behavior
    recent_actions = []  # List of (tool_name, step, reasoning) tuples

    for step in range(1, max_steps + 1):
        # summarize older history when it gets large
        if len(messages) > summarize_when_msgs_over or approx_message_chars(messages) > summarize_when_chars_over:
            before_len = len(messages)
            messages = summarize_history_inplace(
                client=client,
                model=model,
                messages=messages,
                keep_last=keep_last_for_summary,
            )
            log_event(log_path, {
                "step": step,
                "type": "summarize",
                "before_len": before_len,
                "after_len": len(messages),
            })

        # Call model with full history
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="required",
        )

        assistant_msg_obj = resp.choices[0].message
        messages.append(assistant_msg_obj.model_dump())

        # Extract and process tool call
        tool_calls = assistant_msg_obj.tool_calls or []
        if not tool_calls:
            # Safety fallback: treat as final text
            final_text = (assistant_msg_obj.content or "").strip()
            print("\n=== FINAL (no tool call) ===")
            print(final_text)
            log_event(log_path, {"step": step, "type": "final", "answer": final_text})
            return

        should_continue, new_image_path, final_answer, new_moves, context_lines, reasoning = process_tool_call(
            env=env,
            messages=messages,
            tool_calls=tool_calls,
            available_moves=available_moves,
            current_image_path=current_image_path,
            log_path=log_path,
            step=step,
        )

        if not should_continue:
            print(f"\n=== FINAL ===\n{final_answer}")
            return

        # Update state
        current_image_path = new_image_path
        available_moves = new_moves

        # Track action and detect repetitive behavior
        tool_name = tool_calls[0].function.name
        recent_actions.append((tool_name, step, reasoning))

        # Keep only last 8 actions for better pattern detection
        if len(recent_actions) > 8:
            recent_actions.pop(0)

        # Check for repetitive behavior (same move 3+ times in last 5 actions)
        if len(recent_actions) >= 3:
            move_actions = [(t, s, r) for t, s, r in recent_actions if t.startswith("move_")]
            if len(move_actions) >= 3:
                # Check if mostly the same move
                last_move = move_actions[-1][0]
                same_move_count = sum(1 for m, _, _ in move_actions[-3:] if m == last_move)
                if same_move_count >= 3:
                    context_lines.append(
                        f"WARNING: You've used {last_move} {same_move_count} times recently. "
                        "Consider exploring with scroll/zoom before moving again."
                    )

        # Check for repetitive scrolling without progress
        if len(recent_actions) >= 5:
            scroll_actions = [(t, s, r) for t, s, r in recent_actions if t.startswith("scroll_")]
            if len(scroll_actions) >= 5:
                # Check for same scroll action repeated
                last_scroll = scroll_actions[-1][0]
                recent_scroll_count = sum(1 for t, _, _ in scroll_actions[-5:] if t == last_scroll)

                # Check for "no_progress" in reasoning
                no_progress_count = sum(
                    1 for _, _, r in scroll_actions[-5:]
                    if isinstance(r, dict) and r.get("progress") == "no_progress"
                )

                if recent_scroll_count >= 4:
                    context_lines.append(
                        f"WARNING: You've scrolled {recent_scroll_count} times in a row with the same action. "
                        "If you're not finding useful information, try MOVING to a new location instead."
                    )
                elif no_progress_count >= 4:
                    context_lines.append(
                        f"WARNING: You've reported 'no_progress' {no_progress_count} times recently. "
                        "Consider trying a different strategy - MOVE to explore a new area instead of just scrolling."
                    )

        # Add next user message with latest image
        messages.append(make_user_msg_with_image(
            question=question,
            step=step,
            image_path=current_image_path,
            available_moves=available_moves,
            recent_context_lines=context_lines if context_lines else None,
        ))

        print(f"[step {step:02d}] tool={tool_name} image={new_image_path}")

    print("\n=== STOP (max_steps reached) ===")
    log_event(log_path, {"type": "stop", "reason": "max_steps"})


# ===========================
# Main
# ===========================
def main() -> None:
    load_dotenv(ROOT / ".env")

    p = argparse.ArgumentParser(description="LM Studio vision+tools Street View navigator")

    # Required args
    p.add_argument("--lat", type=float, required=True, help="Starting latitude")
    p.add_argument("--lng", type=float, required=True, help="Starting longitude")
    p.add_argument("--question", type=str, required=True, help="Question to answer")

    # Optional args
    p.add_argument("--max_steps", type=int, default=DEFAULT_MAX_STEPS, help="Maximum navigation steps")
    p.add_argument("--run_id", type=str, default=None, help="Session ID (auto-generated if not provided)")
    p.add_argument("--out_root", type=str, default="runs", help="Output directory for logs")
    p.add_argument("--images_root", type=str, default="images", help="Base directory for images")

    # LM Studio config
    p.add_argument("--endpoint", type=str, default=os.getenv("LMSTUDIO_BASE_URL"),
                   help="LM Studio endpoint URL")
    p.add_argument("--api_key", type=str, default=os.getenv("LMSTUDIO_API_KEY"),
                   help="LM Studio API key")
    p.add_argument("--model", type=str, default=os.getenv("LMSTUDIO_MODEL", "qwen2.5-vl-7b-instruct"),
                   help="Model/deployment name")

    # Summarization controls
    p.add_argument("--summarize_when_msgs_over", type=int, default=DEFAULT_SUMMARIZE_MSG_THRESHOLD,
                   help="Summarize when message count exceeds this threshold")
    p.add_argument("--summarize_when_chars_over", type=int, default=DEFAULT_SUMMARIZE_CHARS_THRESHOLD,
                   help="Summarize when character count exceeds this threshold")
    p.add_argument("--keep_last_for_summary", type=int, default=DEFAULT_KEEP_LAST_MESSAGES,
                   help="Number of recent messages to keep verbatim during summarization")

    args = p.parse_args()

    # Validate environment
    maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not maps_key:
        raise RuntimeError(
            "GOOGLE_MAPS_API_KEY not set in environment. "
            "Add it to .env file or set as environment variable."
        )

    if not args.endpoint:
        raise RuntimeError(
            "LMSTUDIO_BASE_URL not set. "
            "Provide via --endpoint or set in .env file."
        )

    # Create configuration
    config = EpisodeConfig.from_args(args)

    # Setup directories
    config.run_dir.mkdir(parents=True, exist_ok=True)
    config.images_root.mkdir(parents=True, exist_ok=True)

    # Initialize OpenAI client
    client = OpenAI(
        base_url=config.endpoint,
        api_key=config.api_key,
    )

    # Run episode
    host = StreetViewHostClient()
    try:
        host.start(config.run_id, api_key=maps_key)

        env = MapEnv(
            host,
            session_id=config.run_id,
            image_root=str(config.images_root),
        )

        run_episode(
            env=env,
            client=client,
            model=config.model,
            lat=config.lat,
            lng=config.lng,
            question=config.question,
            run_dir=config.run_dir,
            max_steps=config.max_steps,
            summarize_when_msgs_over=config.summarize_when_msgs_over,
            summarize_when_chars_over=config.summarize_when_chars_over,
            keep_last_for_summary=config.keep_last_for_summary,
        )
    finally:
        host.close()


if __name__ == "__main__":
    main()
