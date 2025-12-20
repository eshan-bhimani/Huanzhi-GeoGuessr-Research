from fastapi import APIRouter
from backend.models import AgentAction
from backend.state import global_env_state as env


router = APIRouter()

@router.post("/environment/action")
def apply_action(action: AgentAction):
    updated_state = env.apply_action(action.dict())
    return updated_state


