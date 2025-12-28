# Huanzhi GeoGuessr Research Environment

## Overview
This project serves as a research testbed for autonomous navigation agents and manual exploration within a controllable Google Street View environment. It bridges the gap between low-level API interactions and a visual, interactive interface, allowing agents (or humans) to navigate the world dynamically.

The system uses the **Google Street View Static API** for rendering and **Playwright** for pathway discovery. It supports both a Tkinter-based GUI and a terminal-based CLI for interaction.

## Features
- **Visual GUI**: Real-time rendering of Street View panoramas with an integrated terminal.
- **CLI Mode**: A lightweight terminal interface for headless or script-based interaction.
- **Automatic Saving**: Panorama images are automatically saved to the `img/` folder upon movement or orientation changes (CLI only).
- **Dual Control**: Navigate using keyboard shortcuts (GUI) or programmatic API calls (GUI & CLI).
- **State Management**: Centralized `state_manager.py` for consistent position and orientation tracking.
- **Agent Toolset**: Decoupled `navigation.py` and `view.py` for easy integration with AI agents.

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
   python -m playwright install chromium
   ```
3. Configure your API key:
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   ```

## Usage

### 1. GUI Interface (Recommended for Manual Use)
Start the GUI by running:
```bash
python init_env.py
```
- **Top Section**: Displays the current Street View panorama.
- **Bottom Section**: An integrated terminal for calling tools directly.
- **Keyboard Shortcuts**:
  - `Left/Right Arrow` or `A/D`: Pan (15°)
  - `Up/Down Arrow` or `W/S`: Tilt (10°)
  - `Q/E`: Zoom Out/In

### 2. CLI Interface (Recommended for Research/Agents)
Start the CLI by running:
```bash
python cli_example.py
```
- Accepts the same programmatic commands as the GUI terminal.
- Automatically saves every viewed panorama to the `img/` folder with naming format: `{pano_id}_{lat}_{lng}_h{heading}_p{pitch}.jpg`.

## Programmatic Control (Terminal/CLI)
Both interfaces support direct Python-like function calls:

- **`get_possible_pathways()`**
  - *Returns*: A list of nearby navigable nodes (ID, description, heading).
- **`go_to_node(node_id)`**
  - *Args*: `node_id` (str) - A Pano ID or `"lat,lng"` string.
  - *Effect*: Navigates to the specified location.
- **`pan(angle: int)`**
  - Adjusts heading relative to the current view.
- **`tilt(degrees: int)`**
  - Adjusts pitch relative to the current view.
- **`zoom(rate: float)`**
  - Zooms in (Rate > 1.0) or out (Rate < 1.0).
- **`teleport(lat, lng)`**
  - Instantly moves to the specified coordinates.
- **`save_panorama(...)`**
  - Manually trigger a panorama save (handled automatically in CLI).

## Code Structure

### Core Environment
- **`init_env.py`**: The Tkinter GUI entry point.
- **`cli_example.py`**: The CLI entry point with auto-image saving.
- **`state_manager.py`**: The central "Source of Truth" for agent state. Default resolution is 640x640.
- **`constants.py`**: Loads environment variables and API keys.

### Toolset (`toolset/`)
- **`navigation.py`**: High-level movement logic, pathway discovery (Playwright integration), and coordinate parsing.
- **`view.py`**: Camera adjustment logic and panorama fetching/saving.

### Assets
- **`img/`**: Stores saved panorama images.
- **`get_links.html`**: Helper file for Playwright to interact with the Street View API.

## Troubleshooting
- **Black Screen**: Check your `GOOGLE_API_KEY` and ensure billing is enabled.
- **Playwright Errors**: Run `python -m playwright install chromium` to ensure the browser is installed.