from typing import Any, Dict
from .contracts import ToolContext, ToolResult
from .registry import register_tool

@register_tool("get_observation")
def get_observation(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    return ToolResult(updates={"state": ctx.meta.get("state")})

@register_tool("get_image")
def get_image(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    data_url = ctx.meta.get("image")
    if not data_url or "," not in data_url:
        return ToolResult(ok=False, debug={"error": "no image in state"})
    header, b64 = data_url.split(",", 1)
    mime = header.split(";", 1)[0].split(":", 1)[1]
    return ToolResult(updates={"mime": mime, "data_url": data_url, "base64": b64})


@register_tool("describe_scene")
def describe_scene(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    return ToolResult(updates={"description": "A detailed description of the current scene."})

@register_tool("survey_environment_plan")
def survey_environment_plan(ctx: ToolContext, args: Dict[str, Any]) -> ToolResult:
    return ToolResult(updates={
        "type": "plan",
        "action": "survey_environment",
        "plan": [
            {"rotate": "N", "angle": 0},
            {"rotate": "E", "angle": 90},
            {"rotate": "S", "angle": 180},
            {"rotate": "W", "angle": 270},
            {"zoom_out": True},
            {"zoom_in": True},
        ],
        "note": "Execute these steps with the rotate_view() and zoom() tools.",
    })
