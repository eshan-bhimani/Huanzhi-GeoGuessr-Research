# GeoGuessr Research Playground

A small playground for experimenting with GeoGuessr-style Street View navigation. It has:
- A FastAPI backend that keeps shared environment state, fetches Street View images, and exposes simple endpoints for UI/agents.
- A lightweight Google Maps frontend (`maps-ui/`) for manual or automated navigation.
- MCP tool code (deferred) under `integrations/mcp_server/` for later re-integration.

## Project layout
- `backend/` - FastAPI app and utility code (state store, Street View fetch, image persistence).
- `maps-ui/` - Plain JS/HTML UI that renders Street View, shows available moves, and talks to the backend.
- `integrations/mcp_server/` - FastMCP tool definitions (deferred) that read state and push instructions.
- `.env` - Set `GOOGLE_MAPS_API_KEY` for both JS Maps and backend static image fetches.

## Prerequisites
- Python 3.10+.
- A Google Maps API key with Street View Static API access (`GOOGLE_MAPS_API_KEY`).

## Setup
1) Create a virtual environment and install dependencies:
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
2) Copy `.env` (already present) and ensure `GOOGLE_MAPS_API_KEY` is set. The backend loads it on startup.

## Run the FastAPI backend
From the backend folder:
```
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

From the repo root (alternate):
```
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.
Images fetched from Street View are saved under `E:\GeoMap\images` (see `backend/utils/storage.py`).

### Key endpoints
- `GET /environment/state` ??? Current environment snapshot.
- `POST /environment/update` - Replace state from a UI/agent observation.
- `POST /step` - Validate an observation, fetch a fresh Street View image, update state.
- `POST /instruction/push` / `GET /instruction/next` - Push/pop a pending instruction for the UI.
- `POST /environment/action` - Apply an action to the in-memory environment store.

## MCP server (deferred)
MCP is intentionally deferred for this milestone. Tool logic lives in `backend/tools`, and the backend is the only required runtime dependency.
If you still want to run MCP for experiments, start it after the backend is running:
```
python -m integrations.mcp_server.run
```
The MCP tools expose navigation helpers (move N/NE/E/etc., scroll, zoom) and state readers.

## Run the frontend
Serve `maps-ui/` locally (to avoid CORS/file:// issues):
```
cd maps-ui
python -m http.server 3000
```
Then open `http://localhost:3000` and the page will talk to the backend at `http://localhost:8000`.

## Notes
- The frontend polls the backend for MCP-pushed instructions every second and applies them.
- Adjust hard-coded paths/ports as needed if your environment differs.

Quick Test (CLI + UI)

Prereqs
- Python 3.10+
- Google Maps JavaScript API key with Maps JavaScript API enabled
- Backend running on localhost:8000

1) Start the backend
```
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

2) Start the UI
```
cd maps-ui
python -m http.server 5500
```

3) Open the UI in your browser
- http://localhost:5500
- If the map is blank, open DevTools Console and check for a Google Maps API key error.

4) Start the CLI (new terminal)
```
cd E:\GeoMap\GeoGuessr-Research
python tools_cli.py
```

5) Run commands in the CLI
```
move north
move east
scroll left
zoom in
check direction
state
```

Expected results
- move/scroll/zoom: the Street View panorama changes within ~1 second.
- check direction: prints current heading info.
- state: prints current backend environment state.

Notes for different localhost ports
- If you run the UI on a different port (for example 5501), open:
  http://localhost:5501
- Make sure your Google Maps API key allows that referrer:
  http://localhost:5501/*
- If your backend is not on http://localhost:8000, update
  the apiBase in maps-ui/index.html before starting the UI.
