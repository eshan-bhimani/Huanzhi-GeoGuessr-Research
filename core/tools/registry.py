TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "init_panorama",
            "description": "Initialize the panorama session at a lat/lng.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number"},
                    "lng": {"type": "number"},
                    "heading": {"type": "number"},
                    "pitch": {"type": "number"},
                    "zoom": {"type": "number"},
                },
                "required": ["lat", "lng"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_available_moves",
            "description": "Return available movement directions.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_direction",
            "description": "Return the current facing direction.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function", 
        "function": {
            "name": "move_north", 
            "description": "Move north.", 
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False}
        },
    },
    
    {"type": "function", "function": {"name": "move_northeast", "description": "Move northeast.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "move_east", "description": "Move east.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "move_southeast", "description": "Move southeast.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "move_south", "description": "Move south.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "move_southwest", "description": "Move southwest.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "move_west", "description": "Move west.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "move_northwest", "description": "Move northwest.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},

    # scroll (require delta)
    {"type": "function", "function": {"name": "scroll_left", "description": "Scroll left by delta degrees.", "parameters": {"type": "object", "properties": {"delta": {"type": "number"}}, "required": ["delta"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "scroll_right", "description": "Scroll right by delta degrees.", "parameters": {"type": "object", "properties": {"delta": {"type": "number"}}, "required": ["delta"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "scroll_up", "description": "Scroll up by delta degrees.", "parameters": {"type": "object", "properties": {"delta": {"type": "number"}}, "required": ["delta"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "scroll_down", "description": "Scroll down by delta degrees.", "parameters": {"type": "object", "properties": {"delta": {"type": "number"}}, "required": ["delta"], "additionalProperties": False}}},

    # zoom (require delta)
    {"type": "function", "function": {"name": "zoom_in", "description": "Zoom in by delta.", "parameters": {"type": "object", "properties": {"delta": {"type": "number"}}, "required": ["delta"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "zoom_out", "description": "Zoom out by delta.", "parameters": {"type": "object", "properties": {"delta": {"type": "number"}}, "required": ["delta"], "additionalProperties": False}}},
]
