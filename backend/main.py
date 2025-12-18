from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from api.state import router as state_router
from api.update import router as update_router
from api.actions import router as action_router
from api.step import router as step_router
from api.instruction import router as instruction_router
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from utils.storage import MEDIA_ROOT

# Load .env relative to project root to ensure GOOGLE_MAPS_API_KEY is available
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

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
