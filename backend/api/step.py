
import base64
from fastapi.encoders import jsonable_encoder
from utils.streetview import fetch_streetview_image
from utils.storage import save_image, crop_google_logo

from fastapi import APIRouter, Body, HTTPException
from pydantic import ValidationError
from core.environment import global_env_state
from models.schema import parse_observation_payload, EnvironmentStateModel
from fastapi.encoders import jsonable_encoder

router = APIRouter()



@router.post("/step", response_model=EnvironmentStateModel)
def step(payload: dict = Body(...)):
    """Handle a step payload from the UI/agent and refresh the global state."""
    try:
        print(payload)
        obs = parse_observation_payload(payload)
        img_bytes = fetch_streetview_image(
            pano_id=obs.current_node_id,
            heading=obs.current_heading or 0,
            pitch=getattr(obs, "pitch", 0) or 0,
            fov=90
        )
        img_bytes = crop_google_logo(img_bytes, trim_bottom=60)
        image_data_url = f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode()}"
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())
    except Exception as exc:
        # You can choose to fail or proceed without image; here we fail fast;
        raise HTTPException(status_code=502, detail=f"Image fetch failed: {exc}")

    # Optional: persist the image (disabled by default to avoid dev hot-reload churn)
   
    entry_id = obs.meta.history[0] 
    save_image(entry_id, img_bytes)
        

    global_env_state.update_state(
        current_node_id=obs.current_node_id,
        gps=obs.gps,
        current_heading=obs.current_heading,
        available_moves=obs.available_moves,
        image=image_data_url,
        metadata=obs.meta,
    )

    return jsonable_encoder(global_env_state.get_state())
    
