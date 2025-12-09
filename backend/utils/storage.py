import uuid 
from pathlib import Path
from typing import Tuple 

MEDIA_ROOT = Path("images")

def save_image(entry_id: str, content: bytes, suffix: str = "jpg") -> Tuple[str, str]:
    """
    Save image bytes under images/<entry_id>/<uuid>/suffix.
    Returns (path, url) where url is served at /media/images
    """

    image_id = f"{uuid.uuid4()}.{suffix}"
    folder = MEDIA_ROOT/entry_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder/image_id
    path.write_bytes(content)
    url = f"/media/images/{entry_id}/{image_id}"
    return str(path), url