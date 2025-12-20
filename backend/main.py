from pathlib import Path
import sys
from dotenv import load_dotenv

# Allow running `uvicorn main:app` from the backend/ folder.
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent.parent))

# Load .env relative to project root before importing modules that read env at import time.
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.api.actions import router as action_router
from backend.api.instruction import router as instruction_router
from backend.api.state import router as state_router
from backend.api.step import router as step_router
from backend.api.update import router as update_router
from backend.utils.storage import MEDIA_ROOT

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # allow all for local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Serve stored images from MEDIA_ROOT (GeoMap/images)
app.mount("/media/images", StaticFiles(directory=MEDIA_ROOT), name="images")

app.include_router(state_router)
app.include_router(update_router)
app.include_router(action_router)
app.include_router(step_router)
app.include_router(instruction_router)
