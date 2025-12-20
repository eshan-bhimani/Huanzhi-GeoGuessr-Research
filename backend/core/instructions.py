"""
Simple in-memory instruction store shared between MCP tools and the frontend.

MCP tools push the latest instruction here; the frontend polls and pops it.
"""

from typing import Any, Optional
from threading import Condition, Lock


class InstructionStore:
    def __init__(self):
        self._lock = Lock()
        self._condition = Condition(self._lock)
        self._pending: Optional[Any] = None

    def push(self, instruction: Any) -> None:
        with self._condition:
            self._pending = instruction
            self._condition.notify_all()

    def pop(self) -> Optional[Any]:
        with self._condition:
            instr = self._pending
            self._pending = None
            return instr

    def wait_for_instruction(self, timeout: float) -> Optional[Any]:
        with self._condition:
            if self._pending is None:
                self._condition.wait(timeout=timeout)
            instr = self._pending
            self._pending = None
            return instr


# Global instruction store instance
global_instruction_store = InstructionStore()
