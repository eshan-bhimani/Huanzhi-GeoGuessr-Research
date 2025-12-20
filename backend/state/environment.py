
class EnvironmentState:
    def __init__(self):
        self.current_node_id = None
        self.gps = None
        self.current_heading = None
        self.available_moves = []
        self.image = None # base64 string
        self.metadata = {}

    def get_state(self):
        # Normalize metadata and moves to plain dicts for response_model validation
        meta = self.metadata
        if hasattr(meta, "model_dump"):
            meta = meta.model_dump()

        moves = []
        for m in self.available_moves or []:
            if hasattr(m, "model_dump"):
                moves.append(m.model_dump())
            else:
                moves.append(m)

        return {
            "current_node_id": self.current_node_id,
            "gps": self.gps,
            "current_heading": self.current_heading,
            "available_moves": moves,
            "image": self.image,
            "metadata": meta,
        }
    
    def update_state(self, current_node_id, gps, current_heading, available_moves, image, metadata):
        self.current_node_id = current_node_id
        self.gps = gps
        self.current_heading = current_heading
        # Store plain move dicts for consistent serialization
        if available_moves:
            self.available_moves = [
                m.model_dump() if hasattr(m, "model_dump") else m
                for m in available_moves
            ]
        else:
            self.available_moves = []
        self.image = image
        # Store plain metadata dict for consistent serialization
        if hasattr(metadata, "model_dump"):
            self.metadata = metadata.model_dump()
        else:
            self.metadata = metadata


#  Global environment instance
global_env_state = EnvironmentState()
