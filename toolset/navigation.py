import requests
import os
import json
import time
from state_manager import state
from toolset import view
from constants import google_api_key
from playwright.sync_api import sync_playwright

# Global browser instance
_playwright = None
_browser = None
_context = None
_page = None

def init_browser():
    """Initializes a persistent browser instance."""
    global _playwright, _browser, _context, _page
    if _playwright is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)
        _context = _browser.new_context()
        _page = _context.new_page()
        print("Playwright Browser Initialized.")

def close_browser():
    """Closes the persistent browser instance."""
    global _playwright, _browser, _context, _page
    if _page:
        _page.close()
    if _context:
        _context.close()
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()
    _playwright = _browser = _context = _page = None
    print("Playwright Browser Closed.")

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

def _get_links_via_playwright(pano_id: str, page=None) -> list[dict]:
    """Helper to fetch real Street View links using a persistent Playwright browser."""
    global _page
    target_page = page if page is not None else _page
    
    if target_page is None:
        init_browser()
        target_page = _page
    
    try:
        # Use the local helper HTML
        file_path = os.path.abspath("get_links.html")
        url = f"file:///{file_path}?pano={pano_id}&key={google_api_key}"
        
        target_page.goto(url)
        
        # Wait for results
        results = []
        max_wait = 10000 # 10 seconds
        try:
            # Wait for the #results element to have content other than "LOADING..."
            target_page.wait_for_function(
                "() => { const el = document.getElementById('results'); return el && el.innerText !== 'LOADING...' && el.innerText !== ''; }",
                timeout=max_wait
            )
            text = target_page.inner_text("#results")
            if text and not text.startswith("ERROR"):
                results = json.loads(text)
        except Exception as e:
            print(f"Playwright wait error: {e}")
            
        return results
    except Exception as e:
        print(f"Navigation Error (Playwright): {e}")
        return []

def get_possible_pathways(page=None) -> list[dict]:
    """
    Retrieves a list of valid navigable nodes around the current location.

    Args:
        page (playwright.sync_api.Page, optional): A persistent Playwright page instance.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents a nearby node
                    with information such as 'id', 'latitude', 'longitude', 'description'.
    """
    # 1. Ensure we have a Pano ID. 
    # If the state doesn't have one, fetch it from lat/lng.
    current_pano = state.pano_id
    if not current_pano:
        url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={state.latitude},{state.longitude}&key={google_api_key}"
        try:
            resp = requests.get(url).json()
            if resp.get("status") == "OK":
                current_pano = resp.get("pano_id")
                state.update(pano_id=current_pano)
        except:
            pass
    
    if not current_pano:
        return []

    # 2. Get real links
    links = _get_links_via_playwright(current_pano, page=page)
    
    if not links:
        # Fallback to dummy nodes if Playwright fails or no links found
        print("Navigation Error (Playwright): No links found. Using dummy nodes.")
        lat, lng = state.latitude, state.longitude
        offset = 0.0005
        return [
            {"id": f"{lat + offset},{lng}", "latitude": lat + offset, "longitude": lng, "description": "North (Fallback)"},
            {"id": f"{lat - offset},{lng}", "latitude": lat - offset, "longitude": lng, "description": "South (Fallback)"},
            {"id": f"{lat},{lng + offset}", "latitude": lat, "longitude": lng + offset, "description": "East (Fallback)"},
            {"id": f"{lat},{lng - offset}", "latitude": lat, "longitude": lng - offset, "description": "West (Fallback)"}
        ]

    # 3. Process links to include metadata (lat/lng)
    # We could fetch metadata for each, but that's slow. 
    # For now, we return Pano IDs which go_to_node can handle.
    return [{"id": l["id"], "description": l["description"], "heading": l["heading"]} for l in links]

def teleport(latitude: float, longitude: float) -> str:
    """
    Teleports the agent to a specific latitude and longitude.
    This resets the current panorama state to the new coordinates.

    Args:
        latitude (float): The latitude of the destination.
        longitude (float): The longitude of the destination.

    Returns:
        str: A description of the teleportation action.
    """
    state.update(latitude=latitude, longitude=longitude, pano_id=None)
    return f"Teleported to: {latitude}, {longitude}"

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

