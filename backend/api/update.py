import base64
from fastapi.encoders import jsonable_encoder
from utils.streetview import fetch_streetview_image
from fastapi import APIRouter, Body, HTTPException
from pydantic import ValidationError
from core.environment import global_env_state
from models.schema import parse_observation_payload, EnvironmentStateModel

router = APIRouter()

@router.post("/environment/update", response_model=EnvironmentStateModel)
def update_from_ui(payload: dict = Body(...)):
    """Update environment state from the UI or agent."""
    try:
        obs = parse_observation_payload(payload)
        img_bytes = fetch_streetview_image(
            pano_id=obs.current_node_id,
            heading=obs.current_heading or 0,
            pitch=getattr(obs, "pitch", 0) or 0,
            fov=90
        )
        image_data_url = f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode()}"
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())
    
    required = [obs.current_node_id, obs.gps, obs.current_heading, obs.available_moves]
    if any(v is None for v in required):
        raise HTTPException(status_code=422, detail="Missing required observation fields")
    global_env_state.update_state(
        current_node_id=obs.current_node_id,
        gps=obs.gps,
        current_heading=obs.current_heading,
        available_moves=obs.available_moves,
        image=image_data_url,
        metadata=obs.meta,
    )
    return global_env_state.get_state()
