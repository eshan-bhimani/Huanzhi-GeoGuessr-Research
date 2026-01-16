TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "init_panorama",
            "description": "Initialize the Geoguessr session at a specific latitude/longitude. Returns the initial panorama image and available directions to move.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude in decimal degrees."},
                    "lng": {"type": "number", "description": "Longitude in decimal degrees."},
                    "heading": {"type": "number", "description": "Initial camera heading in degrees (0=North, 90=East)."},
                    "pitch": {"type": "number", "description": "Initial camera pitch (0=Horizon)."},
                    "zoom": {"type": "number", "description": "Initial zoom level (usually 0 or 1)."},
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
            "description": "Checks which compass directions allow valid movement from the current location. Use this if you are stuck or unsure if a road continues in a specific direction.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_direction",
            "description": "Returns the agent's current compass heading. Use this to orient yourself (e.g., to find the position of the sun for hemisphere detection).",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    # MOVEMENT TOOLS - exploration logic applied
    {
        "type": "function",
        "function": {
            "name": "move_north",
            "description": "Moves the player North. Use this to approach distant objects, follow a road North, or investigate signs and landmarks currently too far away to read.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_northeast",
            "description": "Moves the player Northeast. Use this if the road or path of interest follows a diagonal trajectory between North and East.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_east",
            "description": "Moves the player East. Use this to approach distant objects, follow a road East, or investigate signs and landmarks currently too far away to read.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_southeast",
            "description": "Moves the player Southeast. Use this if the road or path of interest follows a diagonal trajectory between South and East.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_south",
            "description": "Moves the player South. Use this to approach distant objects, follow a road South, or investigate signs and landmarks currently too far away to read.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_southwest",
            "description": "Moves the player Southwest. Use this if the road or path of interest follows a diagonal trajectory between South and West.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_west",
            "description": "Moves the player West. Use this to approach distant objects, follow a road West, or investigate signs and landmarks currently too far away to read.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_northwest",
            "description": "Moves the player Northwest. Use this if the road or path of interest follows a diagonal trajectory between North and West.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    # CAMERA TOOLS - scanning logic applied
    {
        "type": "function",
        "function": {
            "name": "scroll_left",
            "description": "Rotates the camera view to the left. Use this to scan surroundings for clues outside the left edge of the frame without moving location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delta": {
                        "type": "number",
                        "description": "Degrees to rotate. Use 15-30 for careful scanning to avoid missing details. Use 45-90 only for quick turns."
                    }
                },
                "required": ["delta"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll_right",
            "description": "Rotates the camera view to the right. Use this to scan surroundings for clues outside the right edge of the frame without moving location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delta": {
                        "type": "number",
                        "description": "Degrees to rotate. Use 15-30 for careful scanning to avoid missing details. Use 45-90 only for quick turns."
                    }
                },
                "required": ["delta"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll_up",
            "description": "Tilts the camera view up. Use this to observe the sun position, tree tops, or tall architecture.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delta": {
                        "type": "number",
                        "description": "Degrees to tilt up. Try 30 to see the sky."
                    }
                },
                "required": ["delta"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll_down",
            "description": "Tilts the camera view down. Use this to inspect the ground (road lines, shadows) or the 'Google Car' hood for meta-clues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delta": {
                        "type": "number",
                        "description": "Degrees to tilt down. Try 30 to see the road."
                    }
                },
                "required": ["delta"],
                "additionalProperties": False,
            },
        },
    },
    # ZOOM TOOLS - detail logic applied
    {
        "type": "function",
        "function": {
            "name": "zoom_in",
            "description": "Magnifies the view. Use this ONLY when you are centered on a specific object (sign, plate, bollard) and need to read text or see fine details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delta": {
                        "type": "number",
                        "description": "Zoom increment. 1 for slight zoom, 2 for max detail."
                    }
                },
                "required": ["delta"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "zoom_out",
            "description": "Resets the view to a wider perspective. Use this after inspecting a detail to regain situational awareness.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delta": {
                        "type": "number",
                        "description": "Zoom decrement."
                    }
                },
                "required": ["delta"],
                "additionalProperties": False,
            },
        },
    },
    {
    "type": "function",
    "function": {
        "name": "final_answer",
        "description": "Finish the episode with the final answer.",
        "parameters": {
        "type": "object",
        "properties": {
            "answer": { "type": "string" }
        },
        "required": ["answer"]
        }
    }
    }
]