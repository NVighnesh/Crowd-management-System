# Local setup

This guide runs the current Crowd Management AI project on a Windows CPU
development machine. Run commands from the project root (the directory
containing this file).

## Prerequisites

- Windows 10 or newer
- Python 3.12 recommended
- Node.js and npm
- Git (optional)
- The repository files, including `yolo26n.pt` and `videos\crowd.mp4`

No GPU, Docker, cloud account, or external camera is required. A PostgreSQL
database is required for local startup and tests.

## Python virtual environment

Create the environment if it does not exist:

```powershell
py -m venv .venv
```

Install the current backend and test dependencies from `requirements.txt`, or
use an existing environment that already contains them. Use its interpreter
directly so the backend and tests use the same environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Start the backend

From the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`. Interactive API
documentation is at `http://127.0.0.1:8000/docs`.

## Start the dashboard

In a second terminal, from the project root:

```powershell
Set-Location .\dashboard
npm install
npm run dev
```

The Vite dashboard is normally available at `http://127.0.0.1:5173`.

## Current configuration

The backend loads [configs/app.yaml](configs/app.yaml) using the repository
root derived from `src/config/settings.py`; the current working directory does
not need to be the directory containing the configuration file.

Important local settings:

- `inference.device: auto` remains CPU-compatible and configuration-driven.
- `inference.model: yolo26n.pt`
- File cameras use `videos/crowd.mp4`.
- Authentication is disabled by default for local development.
- Processing and recovery settings are in the `processing` section.

## Persistent data

Set `CROWD_DATABASE_URL` to the PostgreSQL connection string for the database
used by this environment. Startup initializes the PostgreSQL schema
idempotently and does not delete or reset existing data.

For tests, create a separate PostgreSQL database and set
`CROWD_TEST_DATABASE_URL` in the process environment. Database-backed tests
refuse to use `CROWD_DATABASE_URL` or values loaded from `.env`; the test
fixture truncates only the explicitly configured test database before and
after each test.

```powershell
$env:CROWD_TEST_DATABASE_URL = "postgresql://user:password@localhost:5432/crowd_management_test"
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:CROWD_TEST_DATABASE_URL
```

## Model

The configured model is:

```text
yolo26n.pt
```

It is resolved relative to the project root. The inference device remains
`auto`; do not change it for the CPU local setup.

## Camera and video setup

The sample file camera is configured as:

```text
videos\crowd.mp4
```

Uploaded camera videos are stored under:

```text
data\camera_uploads\
```

The directory is created on demand by the existing multipart upload flow.
Supported upload extensions are `.mp4`, `.avi`, `.mov`, `.mkv`, `.m4v`, and
`.webm`. RTSP and drone settings remain available through the existing camera
configuration and API.

Zone files referenced by the sample configuration are under:

```text
configs\zones_cam001.json
configs\zones_cam002.json
```

## Local verification

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q src
npm --prefix dashboard run build
```
