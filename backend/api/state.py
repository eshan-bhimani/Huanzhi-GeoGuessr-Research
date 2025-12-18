from fastapi import APIRouter
from core.environment import global_env_state
from models.schema import EnvironmentStateModel


router = APIRouter()

@router.get("/environment/state", response_model=EnvironmentStateModel)
async def get_environment_state():
    """Get the current state of the environment."""
    return global_env_state.get_state()
