import requests
import os
import json
import io


from PIL import Image
from state_manager import StateManager
from toolset.browser_manager import browser_manager
from constants import google_api_key

class StreetViewInstance:
    def __init__(self, output_dir="img"):
        self.state = StateManager()
        self.output_dir = output_dir
        self.page = browser_manager.get_new_page()
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        # Initial save/update
        self._ensure_pano_id()

    def get_state(self):
        return self.state.get_state()

    def _ensure_pano_id(self):
        """Internal helper to ensure current state has a pano_id."""
        if not self.state.pano_id or self.state.pano_id == "Start":
            url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={self.state.latitude},{self.state.longitude}&key={google_api_key}"
            try:
                resp = requests.get(url).json()
                if resp.get("status") == "OK":
                    self.state.update(pano_id=resp.get("pano_id"))
            except Exception as e:
                print(f"Error fetching metadata: {e}")

    def pan(self, angle: int) -> str:
        current_heading = self.state.heading
        new_heading = (current_heading + angle) % 360
        self.state.update(heading=new_heading)
        return f"Panned {angle} degrees. New heading: {self.state.heading}"

    def tilt(self, degrees: int) -> str:
        current_pitch = self.state.pitch
        new_pitch = current_pitch + degrees
        if new_pitch > 90: new_pitch = 90
        if new_pitch < -90: new_pitch = -90
        self.state.update(pitch=new_pitch)
        return f"Tilted {degrees} degrees. New pitch: {self.state.pitch}"

    def zoom(self, rate: float) -> str:
        if rate <= 0:
            return "Zoom rate must be positive."
        current_fov = self.state.fov
        new_fov = current_fov / rate
        if new_fov < 10: new_fov = 10
        if new_fov > 120: new_fov = 120
        self.state.update(fov=new_fov)
        return f"Zoomed by rate {rate}. New FOV: {self.state.fov}"

    def teleport(self, latitude: float, longitude: float) -> str:
        self.state.update(latitude=latitude, longitude=longitude, pano_id=None)
        self._ensure_pano_id()
        return f"Teleported to: {latitude}, {longitude}"

    def go_to_node(self, node_id: str) -> str:
        if "," in node_id:
            try:
                parts = node_id.split(",")
                new_lat = float(parts[0].strip())
                new_lng = float(parts[1].strip())
                self.state.update(latitude=new_lat, longitude=new_lng, pano_id=None)
                self._ensure_pano_id()
                return f"Navigated to coordinates: {new_lat}, {new_lng}"
            except ValueError:
                pass

        url = f"https://maps.googleapis.com/maps/api/streetview/metadata?pano={node_id}&key={google_api_key}"
        try:
            response = requests.get(url)
            data = response.json()
            if data.get("status") == "OK" and "location" in data:
                loc = data["location"]
                self.state.update(latitude=loc["lat"], longitude=loc["lng"], pano_id=node_id)
                return f"Navigated to Pano ID: {node_id}"
            else:
                return f"Could not resolve node_id: {node_id}"
        except Exception as e:
            return f"Error connecting to API: {e}"

    def get_possible_pathways(self) -> list[dict]:
        self._ensure_pano_id()
        pano_id = self.state.pano_id
        if not pano_id: return []

        try:
            # Get the path to get_links.html in the project root
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(root_dir, "get_links.html")
            url = f"file:///{file_path}?pano={pano_id}&key={google_api_key}"
            self.page.goto(url)
            
            self.page.wait_for_function(
                "() => { const el = document.getElementById('results'); return el && el.innerText !== 'LOADING...' && el.innerText !== ''; }",
                timeout=10000
            )
            text = self.page.inner_text("#results")
            if text and not text.startswith("ERROR"):
                links = json.loads(text)
                return [{"id": l["id"], "description": l["description"], "heading": l["heading"]} for l in links]
        except Exception as e:
            print(f"Navigation Error: {e}")
        
        return []

    def save_panorama(self) -> str:
        self.state.steps += 1
        s = self.state.get_state()
        url = f"https://maps.googleapis.com/maps/api/streetview?size={s['width']}x{s['height']}&location={s['latitude']},{s['longitude']}&heading={s['heading']}&pitch={s['pitch']}&fov={s['fov']}&key={google_api_key}"
        
        response = requests.get(url)
        if response.status_code != 200:
            return f"Error: {response.status_code}"

        img = Image.open(io.BytesIO(response.content))
        filename = f"{s['steps']}_{s['pano_id']}_{s['latitude']}_{s['longitude']}_h{s['heading']}_p{s['pitch']}_fov{s['fov']}.jpg"
        filepath = os.path.join(self.output_dir, filename)
        img.save(filepath)
        return filepath

    def close(self):
        """Closes the page associated with this instance."""
        if self.page:
            self.page.close()
            self.page = None
