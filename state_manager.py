import threading

class StateManager:
    def __init__(self):
        # Default values (can be overwritten by init_env or user)
        self.width = 640
        self.height = 640
        self.latitude = 35.752099
        self.longitude = -83.964307
        self.heading = 151.78
        self.pitch = -0.76
        self.fov = 90
        self.pano_id = None
        self._observers = []
        self._lock = threading.Lock()

    def update(self, **kwargs):
        """Update state with new values and notify observers."""
        with self._lock:
            updated = False
            for key, value in kwargs.items():
                if hasattr(self, key):
                    old_value = getattr(self, key)
                    if old_value != value:
                        setattr(self, key, value)
                        updated = True
            
            if updated:
                self._notify_observers()

    def get_state(self):
        """Return a copy of the current state."""
        with self._lock:
            return {
                "width": self.width,
                "height": self.height,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "heading": self.heading,
                "pitch": self.pitch,
                "fov": self.fov,
                "pano_id": self.pano_id
            }

    def add_observer(self, callback):
        """Add a callback function that is called when state changes."""
        with self._lock:
            self._observers.append(callback)

    def _notify_observers(self):
        state = {
            "width": self.width,
            "height": self.height,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "heading": self.heading,
            "pitch": self.pitch,
            "fov": self.fov,
            "pano_id": self.pano_id
        }
        for callback in self._observers:
            try:
                callback(state)
            except Exception as e:
                print(f"Error in observer callback: {e}")

# Global instance
state = StateManager()
