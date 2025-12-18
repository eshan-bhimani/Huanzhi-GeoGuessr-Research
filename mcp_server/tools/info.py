import asyncio
from typing import Dict, Any

from mcp_server.backend_client import BackendClient


class InfoTools:
    def __init__(self, backend_client: BackendClient | None = None) -> None:
        self.backend = backend_client or BackendClient()

    async def get_image(self):
        state = await asyncio.to_thread(self.backend.get_state)
        data_url = state.get("image")
        if not data_url or  "," not in data_url:
            return {"error": "no image in state"}
        

        header, b64 = data_url.split(",", 1)
        mime = header.split(";", 1)[0].split(":", 1)[1]
        return {"mime": mime, "data_url": data_url, "base64": b64, "state": state}
    
    async def describe_scene(self) -> str:
        """Describe the current scene in detail."""
        return "A detailed description of the current scene."

    async def get_observation(self) -> Dict[str, Any]:
        """
        Fetch the latest environment state from the FastAPI backend.

        This calls GET /environment/state on BACKEND_BASE_URL (defaults to localhost:8000).
        """
        return await asyncio.to_thread(self.backend.get_state)

    async def survey_environment_plan(self) -> Dict[str, Any]:
        """
        Recommend a 360-degree scanning plan without modifying the UI.
        """
        return {
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
        }
