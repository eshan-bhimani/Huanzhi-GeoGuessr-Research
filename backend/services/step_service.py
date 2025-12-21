import base64
from typing import Any, Dict

from backend.models import parse_observation_payload
from backend.utils import crop_google_logo, fetch_streetview_image, save_image
from backend.state import SessionStore, global_session_store
from backend.tools import ToolContext, call_tool

import backend.tools.nav_tools
import backend.tools.info_tools

class StepService:
    def __init__(self, store: SessionStore | None = None) -> None:
        self.store = store or global_session_store
    
    def _resolve_session_id(self, obs: Any, payload: Dict[str, Any]) -> str:
        if payload.get("session_id"):
            return str(payload["session_id"])
        return "default"
    
    def _fetch_image(self, obs: Any, crop_logo: bool) -> tuple[bytes, str]:
        img_bytes = fetch_streetview_image(
            pano_id=obs.current_node_id,
            heading=obs.current_heading or 0,
            pitch=getattr(obs, "pitch", 0) or 0,
            fov=90,
        )
        if crop_logo:
            img_bytes = crop_google_logo(img_bytes, trim_bottom=60)
        image_data_url = f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode()}"
        return img_bytes, image_data_url

    def _require_fields(self, obs: Any) -> None:
        required = [obs.current_node_id, obs.gps, obs.current_heading, obs.available_moves]
        if any(v is None for v in required):
            raise ValueError("Missing required observation fields")

    def handle_step(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        obs = parse_observation_payload(payload)
        session_id = self._resolve_session_id(obs, payload)

        session = self.store.get_or_create(session_id)
        session.update_from_observation(obs)

        img_bytes, image_data_url = self._fetch_image(obs, crop_logo=True)

        entry_id = session.history[0] if session.history else session_id
        save_image(entry_id, img_bytes)
        session.set_image_data_url(image_data_url)

        if payload.get("tool_name"):
            tool_meta = dict(session.metadata)
            tool_meta.update({
                "available_moves": session.available_moves,
                "image": session.image,
                "state": session.to_env_state(),
            })
            ctx = ToolContext(
                session_id=session_id,
                node_id=session.current_node_id,
                gps=session.gps,
                heading=session.current_heading,
                history=session.history,
                meta=tool_meta,
            )
            call_tool(payload["tool_name"], ctx, payload.get("tool_args") or {})

        return session.to_env_state()

    def handle_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        obs = parse_observation_payload(payload)
        self._require_fields(obs)
        session_id = self._resolve_session_id(obs, payload)

        session = self.store.get_or_create(session_id)
        session.update_from_observation(obs)

        _, image_data_url = self._fetch_image(obs, crop_logo=False)
        session.set_image_data_url(image_data_url)

        return session.to_env_state()
