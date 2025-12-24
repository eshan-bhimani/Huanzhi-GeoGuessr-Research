from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class ToolContext:
    session_id: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    ok: bool = True
    updates: Dict[str, Any] = field(default_factory=dict)
    instruction: Optional[Dict[str, Any]] = None
    debug: Dict[str, Any] = field(default_factory=dict)

    