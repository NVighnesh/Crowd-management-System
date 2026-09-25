# Crowd Management AI

Crowd Management AI is a local multi-camera monitoring application that
detects and tracks people, counts crowds and zones, persists history and
alerts, exposes health/recovery information, and provides an annotated live
dashboard.

## Technologies

- Python, FastAPI, Uvicorn
- OpenCV and Ultralytics YOLO
- PostgreSQL via psycopg
- React and Vite
- Pytest

## Project structure

```text
configs/       Application and zone configuration
data/          Local camera uploads and generated runtime output (not committed)
dashboard/     React/Vite frontend
src/           FastAPI backend, processing pipeline, persistence, and tests
videos/        Optional local sample video sources
yolo26n.pt     Local model referenced by the default configuration
```

## Local setup

See [LOCAL_SETUP.md](LOCAL_SETUP.md) for Windows prerequisites, environment
setup, paths, camera/video setup, and startup commands.

Create a virtual environment and install the current backend/test dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Start the backend

Run from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`.

## Start the frontend

In a second terminal:

```powershell
npm --prefix dashboard install
npm --prefix dashboard run dev
```

The Vite dashboard is normally available at `http://127.0.0.1:5173`.

## Configuration and local data

The backend loads [configs/app.yaml](configs/app.yaml) and resolves relative
paths from the project root. The default configuration uses:

- `inference.model: yolo26n.pt`
- `inference.device: auto`
- sample file video `videos/crowd.mp4`
- zone files under `configs/`

PostgreSQL is configured with `CROWD_DATABASE_URL`. Runtime output, uploaded
videos, logs, generated output, and secrets are intentionally ignored by Git.
Copy [.env.example](.env.example) to `.env` only when environment
configuration is needed; never commit `.env`.

When authentication is enabled, the configured account is `ADMIN`; public
registration creates isolated `OPERATOR` accounts. Operators can manage only
their own cameras, zones, alerts, streams, and history. Admins have global
access and can manage operators.

## Testing

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q src
npm --prefix dashboard run build
```

The default local setup is CPU-compatible. GPU-specific acceleration remains
configuration-driven and is not required for tests.
