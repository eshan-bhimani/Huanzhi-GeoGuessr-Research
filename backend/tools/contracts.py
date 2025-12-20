from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ToolContext:
    session_id: str
    node_id: Optional[str]
    gps: Optional[Dict[str, float]]
    heading: Optional[float]
    history: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolResult:
    ok: bool = True
    updates: Dict[str, Any] = field(default_factory=dict)
    instruction: Optional[Dict[str, Any]] = None
    debug: Dict[str, Any] = field(default_factory = dict)

class ToolError(Exception):
    def __init__(self, code: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.messsage, "data": self.data}
    