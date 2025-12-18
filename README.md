# GeoGuessr Research Playground

A small playground for experimenting with GeoGuessr-style Street View navigation. It has:
- A FastAPI backend that keeps shared environment state, fetches Street View images, and exposes simple endpoints for UI/agents.
- A lightweight Google Maps frontend (`maps-ui/`) for manual or automated navigation.
- An MCP server (`mcp_server/`) that can drive the frontend by pushing navigation instructions through the backend.

## Project layout
- `backend/` – FastAPI app and utility code (state store, Street View fetch, image persistence).
- `maps-ui/` – Plain JS/HTML UI that renders Street View, shows available moves, and talks to the backend.
- `mcp_server/` – FastMCP tool definitions that read state and push instructions.
- `.env` – Set `GOOGLE_MAPS_API_KEY` for both JS Maps and backend static image fetches.

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
```
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
Images fetched from Street View are saved under `E:\GeoMap\images` (see `backend/utils/storage.py`).

### Key endpoints
- `GET /environment/state` – Current environment snapshot.
- `POST /environment/update` – Replace state from a UI/agent observation.
- `POST /step` – Validate an observation, fetch a fresh Street View image, update state.
- `POST /instruction/push` / `GET /instruction/next` – Push/pop a pending instruction for the UI.
- `POST /environment/action` – Apply an action to the in-memory environment store.

## Run the MCP server (optional agent control)
Start after the backend is running so instructions/state calls succeed:
```
python -m mcp_server.run
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
