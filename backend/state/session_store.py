from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class SessionState:
    session_id: str
    current_node_id: Optional[str] = None
    gps: Optional[Dict[str, float]] = None
    current_heading: Optional[float] = None
    available_moves: List[Dict[str, Any]] = field(default_factory=list)
    history: List[str] = field(default_factory=list)
    step_count: int = 0
    image: Optional[str] = None
    last_image: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=lambda: {"step_count": 0, "history": []})

    def update_from_observation(self, obs: Any) -> None:
        self.current_node_id = obs.current_node_id
        self.gps = obs.gps
        self.current_heading = obs.current_heading
        self.available_moves = [
            m.model_dump() if hasattr(m, "model_dump") else m
            for m in (obs.available_moves or [])
        ]
        meta = obs.meta.model_dump() if hasattr(obs.meta, "model_dump") else obs.meta
        meta = meta or {}
        meta.setdefault("step_count", 0)
        meta.setdefault("history", [])
        self.metadata = meta
        self.history = list(meta["history"])
        self.step_count = int(meta["step_count"])

    def set_image_data_url(self, data_url: str) -> None:
        self.image = data_url
        self.last_image = data_url

    def to_env_state(self) -> Dict[str, Any]:
        return {
            "current_node_id": self.current_node_id,
            "gps": self.gps,
            "current_heading": self.current_heading,
            "available_moves": self.available_moves,
            "image": self.image,
            "metadata": self.metadata,
        }


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}

    def get_or_create(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[SessionState]:
        return self._sessions.get(session_id)

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

# global singleton
global_session_store = SessionStore()
