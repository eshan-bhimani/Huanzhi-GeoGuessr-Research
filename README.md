# GeoGuessr Research

CLI pipeline that drives Google Street View via a Playwright (Node) host and Python tooling, with optional image capture per step.

## Quickstart (Docker Compose)
1) Ensure Docker Desktop is running.
2) Provide a valid `GOOGLE_MAPS_API_KEY` (do not commit keys).
3) Build the image: `docker compose build`
4) Run the CLI: `docker compose run --rm geoguessr-worker`
5) Try commands like `init 37.7749 -122.4194`, `move north`, `state`, `exit`.

## Outputs
- Images are written to `/data/images` in the container and stored in a Compose volume.
- Each run creates `session_<timestamp>/` to avoid collisions.

## Docs
- `docs/Run-Instructions-CLI.md`
- `docs/Run-Instructions-Compose.md`

## Notes
- macOS is supported; Apple Silicon may require an arm64 Playwright image or emulation.
- Google Maps JS and Street View Static APIs must be enabled with billing.
