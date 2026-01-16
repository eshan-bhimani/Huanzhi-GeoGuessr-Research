import os
import re
from pathlib import Path

from openai import OpenAI

def build_filename(pano_id, heading, pitch, zoom, ext=".jpg", step=None):
    h = float(heading) if heading is not None else 0.0
    p = float(pitch) if pitch is not None else 0.0
    z = "na" if zoom is None else str(zoom)
    safe_pano = re.sub(r"[^A-Za-z0-9_-]", "_", str(pano_id))
    prefix = f"step_{step:04d}_" if step is not None else ""
    return f"{prefix}pano_{safe_pano}_h{h:.1f}_p{p:.1f}_z{z}{ext}"

def save_image(
    img,
    root_dir,
    session_id,
    pano_id,
    heading,
    pitch,
    zoom,
    overwrite=False,
    step=None,
) -> str:
    session_dir = os.path.join(root_dir, session_id)
    os.makedirs(session_dir, exist_ok=True)

    filename = build_filename(pano_id, heading, pitch, zoom, step=step)
    path = os.path.join(session_dir, filename)

    if not overwrite:
        if os.path.exists(path):
            base, ext = os.path.splitext(filename)
            i = 1
            while os.path.exists(path):
                path = os.path.join(session_dir, f"{base}_{i}{ext}")
                i += 1
    

    img.save(path, format="JPEG", quality=95)
    return path


def create_openai_file(
    file_path: str | os.PathLike,
    purpose: str = "vision",
    api_key: str | None = None,
) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    client = OpenAI(api_key=api_key) if api_key else OpenAI()
    with path.open("rb") as file_content:
        result = client.files.create(file=file_content, purpose=purpose)
    return result.id

