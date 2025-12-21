
from fastapi import APIRouter, Body, HTTPException
from pydantic import ValidationError
from backend.models import EnvironmentStateModel
from backend.services import StepService

router = APIRouter()

step_service = StepService()


@router.post("/step", response_model=EnvironmentStateModel)
def step(payload: dict = Body(...)):
    """Handle a step payload from the UI/agent and refresh the session state."""
    try:
        return step_service.handle_step(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        # You can choose to fail or proceed without image; here we fail fast;
        raise HTTPException(status_code=502, detail=f"Image fetch failed: {exc}")
    


