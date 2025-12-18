"""
Simple in-memory instruction store shared between MCP tools and the frontend.

MCP tools push the latest instruction here; the frontend polls and pops it.
"""

from typing import Any, Optional
from threading import Lock


class InstructionStore:
    def __init__(self):
        self._lock = Lock()
        self._pending: Optional[Any] = None

    def push(self, instruction: Any) -> None:
        with self._lock:
            self._pending = instruction

    def pop(self) -> Optional[Any]:
        with self._lock:
            instr = self._pending
            self._pending = None
            return instr


# Global instruction store instance
global_instruction_store = InstructionStore()
