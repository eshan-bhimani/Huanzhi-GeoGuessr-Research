import os, requests
from dotenv import load_dotenv

# Ensure .env is loaded even if caller hasn't yet
load_dotenv()

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_MAPS_API_KEY not set in environment")


def fetch_streetview_image(pano_id: str, heading: float, pitch: float = 0, fov: int = 90, size: str = "420x420") -> bytes:
    url = (
        "https://maps.googleapis.com/maps/api/streetview"
        f"?size={size}&pano={pano_id}"
        f"&heading={round(heading)}&pitch={round(pitch)}&fov={fov}"
        f"&key={API_KEY}"
    )

    resp = requests.get(url, timeout = 10)
    resp.raise_for_status()
    return resp.content
