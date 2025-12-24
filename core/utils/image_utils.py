import os
from io import BytesIO

import requests
from PIL import Image


def zoom_to_fov(zoom, default=90):
    if zoom is None:
        return default
    try:
        z = float(zoom)
    except (TypeError, ValueError):
        return default
    
    fov = int(round(180.0 / (2**z)))
    return max(10, min(120, fov))

def fetch_image(
    pano_id,
    heading,
    pitch=0,
    zoom=None,
    size="640x640",
    fov=None,
) -> bytes:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY environment variable is not set")

    h = float(heading) if heading is not None else 0.0
    p = float(pitch) if pitch is not None else 0.0
    if fov is None:
        fov = zoom_to_fov(zoom)

    url = (
        "https://maps.googleapis.com/maps/api/streetview"
        f"?size={size}&pano={pano_id}"
        f"&heading={round(h)}&pitch={round(p)}&fov={fov}"
        f"&key={api_key}"
    )

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.content

def crop_google_logo(img_bytes: bytes, trim_bottom: int = 60) -> Image.Image:
    """Crop pixels off the bottom to remove the Google logo."""
    with Image.open(BytesIO(img_bytes)) as img:
        img.load()
        w, h = img.size
        new_h = max(h - int(trim_bottom), 1)
        return img.crop((0, 0, w, new_h)).copy()
