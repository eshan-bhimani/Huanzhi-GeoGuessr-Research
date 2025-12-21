from fastapi import APIRouter
from backend.state import global_session_store
from backend.models import EnvironmentStateModel


router = APIRouter()

@router.get("/environment/state", response_model=EnvironmentStateModel)
async def get_environment_state():
    """Get the current state of the environment."""
    session = global_session_store.get_or_create("default")
    return session.to_env_state()


