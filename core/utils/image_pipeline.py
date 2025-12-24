from __future__ import annotations

from typing import Any, Dict

from core.utils.image_store import save_image
from core.utils.image_utils import crop_google_logo, fetch_image


def capture_state_image(
    state: Dict[str, Any],
    session_id: str,
    root_dir: str,
    step: int | None = None,
    trim_bottom: int = 60,
    size: str = "640x640",
) -> str:
    pano_id = state["panoId"]
    pov = state["pov"]
    heading = pov.get("heading", 0.0)
    pitch = pov.get("pitch", 0.0)
    zoom = pov.get("zoom", 1.0)

    img_bytes = fetch_image(
        pano_id=pano_id,
        heading=heading,
        pitch=pitch,
        zoom=zoom,
        size=size,
    )
    cropped = crop_google_logo(img_bytes, trim_bottom=trim_bottom)
    return save_image(
        cropped,
        root_dir=root_dir,
        session_id=session_id,
        pano_id=pano_id,
        heading=heading,
        pitch=pitch,
        zoom=zoom,
        step=step,
    )
