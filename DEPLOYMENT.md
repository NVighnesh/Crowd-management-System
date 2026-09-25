# Backend deployment (Phase 20)

## Selected platform

Render is the selected free web-service platform for the backend because it
supports a public HTTP service and a configurable Python start command.

The backend is **not yet deployed**. Render's free web service filesystem is
ephemeral, so uploaded camera videos are not durable. PostgreSQL must be
provided as a managed persistent dependency.

## Production start command

```text
uvicorn src.api:app --host 0.0.0.0 --port $PORT
```

The command uses Render's assigned `PORT` and does not hard-code port 8000.

## Build/install command

```text
python -m pip install -r requirements.txt
```

The repository does not require Docker for the selected deployment shape.

## Required environment variables

At minimum, production authentication should configure:

```text
CROWD_SECURITY_ENABLED=true
CROWD_AUTH_SECRET=<random-secret-at-least-32-characters>
CROWD_ADMIN_USERNAME=<admin-username>
CROWD_ADMIN_PASSWORD=<strong-password>
CROWD_CORS_ORIGINS=https://<deployed-frontend-origin>
```

Do not commit these values. Use Render's environment-variable secret store.

The database connection is configured with:

```text
CROWD_DATABASE_URL=<managed-postgresql-connection-string>
```

## Health endpoints

- `GET /health` — lightweight service health response.
- `GET /system/health` — application and camera health; requires the
  application services to have initialized.
- `POST /auth/login` — authentication availability check using configured
  credentials.

## Required deployment steps after persistent storage is available

1. Provide a managed PostgreSQL database.
3. Configure Render environment variables without committing secrets.
4. Create a Render web service from this repository.
5. Set the build and start commands above.
6. Confirm `/health`, `/system/health`, and `/auth/login` from the public URL.
7. Verify database writes and restart persistence before using the service.

## Current platform limitations

The free Render tier is not suitable for claiming continuous CCTV/RTSP
processing:

- filesystem contents may be lost on restart or replacement;
- free services may sleep and have cold starts;
- CPU and memory are limited;
- YOLO inference is CPU-based with `inference.device: auto`;
- uploaded videos are not durable without persistent storage;
- RTSP connectivity and long-running camera workers are not guaranteed;
- free-tier restarts can interrupt workers and in-memory runtime state.

The existing inference and camera architecture is intentionally unchanged in
this phase. The service can expose the API after the database requirement is
resolved, but this phase does not claim a live production deployment.
