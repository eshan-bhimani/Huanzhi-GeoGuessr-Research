from fastapi import APIRouter, Body, HTTPException
from pydantic import ValidationError
from backend.models import EnvironmentStateModel
from backend.services import StepService

router = APIRouter()
step_service = StepService()

@router.post("/environment/update", response_model=EnvironmentStateModel)
def update_from_ui(payload: dict = Body(...)):
    """Update environment state from the UI or agent."""
    try:
        return step_service.handle_update(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Image fetch failed: {exc}")


