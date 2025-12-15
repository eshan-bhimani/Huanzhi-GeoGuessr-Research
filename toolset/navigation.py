import requests
from state_manager import state
from toolset import view
from constants import google_api_key

def pan(angle: int) -> str:
    """
    Pans the view horizontally by a custom input angle.

    Use this tool to adjust the horizontal orientation of the view.

    Args:
        angle (int): The angle in degrees to pan. Positive values pan right, negative values pan left.

    Returns:
        str: A description of the panning action performed.
    """
    current_heading = state.heading
    new_heading = current_heading + angle
    view.set_heading(new_heading)
    return f"Panned {angle} degrees. New heading: {state.heading}"

def tilt(degrees: int) -> str:
    """
    Tilts the view vertically by a custom input degree.

    Use this tool to adjust the vertical orientation of the view.

    Args:
        degrees (int): The degrees to tilt. Positive values tilt up, negative values tilt down.

    Returns:
        str: A description of the tilting action performed.
    """
    current_pitch = state.pitch
    new_pitch = current_pitch + degrees
    view.set_pitch(new_pitch)
    return f"Tilted {degrees} degrees. New pitch: {state.pitch}"

def zoom(rate: float) -> str:
    """
    Zooms the view in or out at a custom rate.

    Use this tool to adjust the zoom level of the view.

    Args:
        rate (float): The rate at which to zoom. Values greater than 1.0 zoom in, values less than 1.0 zoom out.
                      For example, 2.0 zooms in by a factor of 2, 0.5 zooms out by a factor of 2.

    Returns:
        str: A description of the zooming action performed.
    """
    current_fov = state.fov
    if rate <= 0:
        return "Zoom rate must be positive."
    new_fov = current_fov / rate
    view.set_fov(new_fov)
    return f"Zoomed by rate {rate}. New FOV: {state.fov}"

def get_possible_pathways() -> list[dict]:
    """
    Retrieves a list of valid navigable nodes around the current location.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents a nearby node
                    with information such as 'id', 'latitude', 'longitude', 'description'.
    """
    if state.latitude is None or state.longitude is None:
        return []

    lat, lng = state.latitude, state.longitude

    # Dummy nodes based on current location (since API doesn't easily give linked nodes)
    # IDs are encoded as "lat,lng" to make go_to_node stateless and simple.
    offset = 0.0005
    nodes = [
        {
            "id": f"{lat + offset},{lng}",
            "latitude": lat + offset, 
            "longitude": lng, 
            "description": "North"
        },
        {
            "id": f"{lat - offset},{lng}",
            "latitude": lat - offset, 
            "longitude": lng, 
            "description": "South"
        },
        {
            "id": f"{lat},{lng + offset}",
            "latitude": lat, 
            "longitude": lng + offset, 
            "description": "East"
        },
        {
            "id": f"{lat},{lng - offset}",
            "latitude": lat, 
            "longitude": lng - offset, 
            "description": "West"
        }
    ]
    return nodes

def go_to_node(node_id: str) -> str:
    """
    Navigates to a specified node (pathway) from the current location.

    Args:
        node_id (str): The identifier of the node to navigate to. 
                       Expected format: "lat,lng" or a pano_id (if supported).

    Returns:
        str: A description of the navigation action.
    """
    # 1. Try parsing basic coordinate string "lat,lng"
    if "," in node_id:
        try:
            parts = node_id.split(",")
            new_lat = float(parts[0].strip())
            new_lng = float(parts[1].strip())
            
            state.update(latitude=new_lat, longitude=new_lng)
            return f"Navigated to coordinates: {new_lat}, {new_lng}"
        except ValueError:
            pass # Continue to try other formats if this failed

    # 2. If it's not a coordinate string, we could assume it's a Pano ID and fetch it.
    # (Existing logic from previous implementation)
    url = f"https://maps.googleapis.com/maps/api/streetview/metadata?pano={node_id}&key={google_api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get("status") == "OK" and "location" in data:
            loc = data["location"]
            new_lat = loc["lat"]
            new_lng = loc["lng"]
            state.update(latitude=new_lat, longitude=new_lng, pano_id=node_id)
            return f"Navigated to Pano ID: {node_id} at ({new_lat}, {new_lng})"
        else:
            return f"Could not resolve node_id: {node_id}. Status: {data.get('status')}"
    except Exception as e:
        return f"Error connecting to API: {e}"

