# Huanzhi GeoGuessr Research Environment

## Overview
This project serves as a research testbed for autonomous navigation agents and manual exploration within a controllable Google Street View environment. It bridges the gap between low-level API interactions and a visual, interactive GUI, allowing user agents (or humans) to navigate the world dynamically.

The system uses the **Google Street View Static API** to render panoramas and allows control via both standard keyboard inputs and a programmatic command terminal.

## Features
- **Visual Interface**: Real-time rendering of Street View panoramas.
- **Dual Control**: Navigate using typical gaming keys (WASD/Arrows) or sophisticated API function calls via an embedded terminal.
- **State Management**: Centralized state tracking for heading, pitch, FOV, and location.
- **Agent Toolset**: A decoupled `toolset` library (`navigation.py`, `view.py`) acting as the API surface for AI agents.

## Installation & Setup

### 1. Prerequisites
- Python 3.8+
- A Google Cloud Project with the following APIs enabled:
  - **Maps Static API**
  - **Street View Static API**

### 2. Environment Configuration
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Ensure `python-dotenv`, `requests`, and `pillow` are installed)*.
3. specific your API key:
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   ```

## Usage

Start the environment by running:
```bash
python init_env.py
```

### The GUI Interface
The window is split into two sections:
1. **Panorama View** (Top): Displays the current street view.
2. **Command Terminal** (Bottom): Logs actions and accepts specific function calls.

### Controls

#### Manual (Keyboard)
| Key | Action | Function Called |
| :--- | :--- | :--- |
| **Left Arrow** | Pan Left (15°) | `pan(-15)` |
| **Right Arrow** | Pan Right (15°) | `pan(15)` |
| **Up Arrow** | Tilt Up (10°) | `tilt(10)` |
| **Down Arrow** | Tilt Down (10°) | `tilt(-10)` |
| **Q** | Zoom Out | `zoom(0.8)` |
| **E** | Zoom In | `zoom(1.2)` |

#### Programmatic (Terminal)
You can type the following Python command in the bottom input box to control the agent directly:

- **`get_possible_pathways()`**
  - *Returns*: A list of dictionaries containing nearby nodes (ID, lat, lng).
  - *Use*: To find where you can move next.

- **`go_to_node(node_id)`**
  - *Args*: `node_id` (str) - Can be a `"lat,lng"` string or a specific Pano ID.
  - *Effect*: Teleports the agent to the new location.

- **`pan(angle: int)`**
  - Adjusts heading by `angle` degrees.

- **`tilt(degrees: int)`**
  - Adjusts pitch by `degrees`.

- **`zoom(rate: float)`**
  - Multiplies current FOV by `1/rate`. (Rate > 1.0 zooms in).

## Code Structure

### `init_env.py`
The main entry point. It sets up the Tkinter GUI, the event loop, and the integrated terminal. It observes the `state_manager` to redraw the screen whenever the state changes.

### `state_manager.py`
A singleton class that maintains the "Source of Truth" for the agent's content (Location, Heading, Pitch, FOV). It implements the Observer pattern so the GUI updates automatically when the state changes.

### `toolset/`
This directory contains the "tools" that an AI agent would access.
- **`navigation.py`**: Logic for high-level movement. Handles coordinate parsing and API logic for finding/moving to nodes.
- **`view.py`**: Logic for camera adjustments. Used by `navigation.py` to set specific view parameters on the state.

### `constants.py`
Handles safe loading of environment variables (API Keys).

## Troubleshooting
- **Black Screen / Image Not Loading**: Check your `GOOGLE_API_KEY` in `.env`. Ensure billing is enabled on your Google Cloud project.
- **"Module not found"**: Ensure you have installed all requirements.