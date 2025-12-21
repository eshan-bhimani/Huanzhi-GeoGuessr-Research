from typing import Any, Callable, Dict

from .contracts import ToolContext, ToolError, ToolResult

ToolFn = Callable[[ToolContext, Dict[str, Any]], ToolResult]
_registry: Dict[str, ToolFn] = {}

def register_tool(name: str):
    def decorator(fn: ToolFn) -> ToolFn:
        _registry[name] = fn
        return fn
    return decorator


def register_tool_explicit(name: str, fn: ToolFn) -> None:
    _registry[name] = fn

def call_tool(name: str, ctx: ToolContext, args: Dict[str, Any] | None = None ) -> ToolResult:
    fn = _registry.get(name)
    if not fn:
        raise ToolError("tool_not_found", f"Unknown tool: {name}")
    return fn(ctx, args or {})
