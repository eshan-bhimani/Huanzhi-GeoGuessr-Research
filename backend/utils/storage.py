import uuid
from pathlib import Path
from io import BytesIO
from PIL import Image
# Save images under the shared GeoMap/images folder.
MEDIA_ROOT = Path(r"E:\GeoMap\images")
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def save_image(entry_id: str, content: bytes, suffix: str = "jpg") -> Path:
    """
    Save image bytes to MEDIA_ROOT/<entry_id>/<uuid>.<suffix> and return the path.
    """
    safe_entry = entry_id or "default"
    image_id = f"{uuid.uuid4()}.{suffix}"

    folder = MEDIA_ROOT / safe_entry
    folder.mkdir(parents=True, exist_ok=True)

    path = folder / image_id
    path.write_bytes(content)
    return path

def crop_google_logo(img_bytes: bytes, trim_bottom: int = 60) -> bytes:
    """Crop pixels off the bottom to remove the Google logo."""
    with Image.open(BytesIO(img_bytes)) as img:
        w, h = img.size
        new_h = max(h-trim_bottom, 1)
        cropped = img.crop((0, 0, w, new_h))
        buf = BytesIO()
        cropped.save(buf, format="JPEG")
        return buf.getvalue()