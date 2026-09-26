from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
import os
import logging
import re

from src.config.settings import load_config
from src.config.settings import PROJECT_ROOT
from src.config.settings import get_cors_origins
from src.config.validator import ConfigValidator
from src.video.camera_manager import CameraManager
from src.video.multi_camera_manager import MultiCameraManager
from src.video.frame_streamer import FrameStreamer
from src.alerts.alert_serializer import AlertSerializer
from src.system.overview_service import SystemOverviewService
from src.system.health_service import SystemHealthService
from src.database.database_service import DatabaseService
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.security.auth import (
    AuthService,
    audit,
    AuthenticatedUser,
    InactiveAccountError,
)
from src.storage.supabase_storage import SupabaseStorage, SupabaseStorageError


camera_manager = None
multi_camera_manager = None
system_overview_service = None
database_service = None
system_health_service = None
auth_service = None
storage_service = None
LOGGER = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".m4v",
    ".webm",
}

class CameraCreateRequest(BaseModel):
    camera_id: str
    camera_name: str
    source_type: str
    source: str
    loop: bool = True
    enabled: bool = True


class CameraUpdateRequest(BaseModel):
    camera_name: str
    source_type: str
    source: str
    loop: bool = True
    enabled: bool = True


class ZoneCreateRequest(BaseModel):
    zone_id: str
    zone_name: str
    polygon: list[list[float]]
    threshold: int
    point: str = "bottom_center"
    enabled: bool = True


class ZoneUpdateRequest(BaseModel):
    zone_name: str
    polygon: list[list[float]]
    threshold: int
    point: str = "bottom_center"
    enabled: bool = True


class LoginRequest(BaseModel):
    username: str
    password: str


class RegistrationRequest(BaseModel):
    username: str
    password: str


class OperatorCreateRequest(BaseModel):
    username: str
    password: str


class OperatorUpdateRequest(BaseModel):
    username: str | None = None


def _parse_bool(value, default: bool = True) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return bool(value)

    normalized = str(value).strip().lower()

    if normalized in {"true", "1", "yes", "on"}:
        return True

    if normalized in {"false", "0", "no", "off"}:
        return False

    return default


def _safe_upload_filename(camera_id: str, filename: str) -> str:
    original_name = Path(filename).name
    stem = Path(original_name).stem
    suffix = Path(original_name).suffix.lower()

    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._")
    safe_camera_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", camera_id).strip("._")

    if not safe_stem:
        safe_stem = "video"

    if not safe_camera_id:
        safe_camera_id = "camera"

    return f"{safe_camera_id}_{safe_stem}{suffix}"


async def _save_uploaded_camera_video(camera_id: str, upload) -> str:
    filename = getattr(upload, "filename", "") or ""
    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported video format. Supported formats: "
                f"{', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}"
            ),
        )

    content = await upload.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded video file is empty.",
        )

    if storage_service is None:
        raise HTTPException(status_code=503, detail="Storage service is not available.")
    try:
        return storage_service.upload_file(
            camera_id=camera_id,
            filename=filename,
            content=content,
            content_type=getattr(upload, "content_type", None) or "application/octet-stream",
        )
    except SupabaseStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


async def _read_camera_update_payload(
    camera_id: str,
    request: Request,
    existing: dict,
) -> dict:
    content_type = request.headers.get(
        "content-type",
        "",
    ).lower()

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        source_type = str(
            form.get(
                "source_type",
                existing["source_type"],
            )
        ).strip()
        raw_source = form.get("source")
        upload = form.get("video_file")

        if (
            source_type in {"file", "drone"}
            and upload is not None
            and getattr(upload, "filename", "")
        ):
            source = await _save_uploaded_camera_video(
                camera_id,
                upload,
            )
        elif raw_source is None or not str(raw_source).strip():
            if source_type == existing["source_type"]:
                source = existing["source"]
            else:
                source = ""
        else:
            source = str(raw_source).strip()

        return {
            "camera_name": str(
                form.get(
                    "camera_name",
                    existing.get("camera_name") or camera_id,
                )
            ).strip(),
            "source_type": source_type,
            "source": source,
            "loop": _parse_bool(
                form.get("loop"),
                bool(existing.get("loop", 1)),
            ),
            "enabled": _parse_bool(
                form.get("enabled"),
                bool(existing.get("enabled", 1)),
            ),
        }

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid camera update request.",
        )

    source_type = str(
        data.get(
            "source_type",
            existing["source_type"],
        )
    ).strip()
    raw_source = data.get("source")

    if raw_source is None or not str(raw_source).strip():
        if source_type == existing["source_type"]:
            source = existing["source"]
        else:
            source = ""
    else:
        source = str(raw_source).strip()

    return {
        "camera_name": str(
            data.get(
                "camera_name",
                existing.get("camera_name") or camera_id,
            )
        ).strip(),
        "source_type": source_type,
        "source": source,
        "loop": _parse_bool(
            data.get("loop"),
            bool(existing.get("loop", 1)),
        ),
        "enabled": _parse_bool(
            data.get("enabled"),
            bool(existing.get("enabled", 1)),
        ),
    }


async def _read_camera_create_payload(request: Request) -> dict:
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        camera_id = str(form.get("camera_id", "")).strip()
        source_type = str(form.get("source_type", "file")).strip().lower()
        upload = form.get("video_file")
        raw_source = form.get("source")

        if (
            source_type in {"file", "drone"}
            and upload is not None
            and getattr(upload, "filename", "")
        ):
            source = await _save_uploaded_camera_video(camera_id, upload)
        else:
            source = str(raw_source or "").strip()

        return {
            "camera_id": camera_id,
            "camera_name": str(form.get("camera_name", "")).strip(),
            "source_type": source_type,
            "source": source,
            "loop": _parse_bool(form.get("loop"), True),
            "enabled": _parse_bool(form.get("enabled"), True),
        }

    try:
        payload = CameraCreateRequest(**await request.json())
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid camera creation request.",
        ) from None
    return payload.model_dump()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global camera_manager
    global multi_camera_manager
    global system_overview_service
    global database_service
    global system_health_service
    global auth_service
    global storage_service

    config = load_config()

    ConfigValidator.validate(config)

    security_config = dict(config.get("security", {}))
    if "CROWD_SECURITY_ENABLED" in os.environ:
        security_config["enabled"] = (
            os.environ["CROWD_SECURITY_ENABLED"].strip().lower()
            in {"1", "true", "yes", "on"}
        )
    database_service = DatabaseService()
    storage_service = SupabaseStorage()
    auth_service = AuthService(security_config, database_service.database)

    # PostgreSQL is the runtime source of truth for cameras. Empty databases
    # remain empty until an authenticated user creates a camera.
    stored_cameras = database_service.get_cameras()

    runtime_cameras = [
        {
            "id": camera["camera_id"],
            "name": camera.get(
                "camera_name",
                camera["camera_id"],
            ),
            "source_type": camera["source_type"],
            "source": camera["source"],
            "loop": bool(camera.get("loop", 1)),
            "enabled": bool(camera.get("enabled", 1)),
            "owner_id": camera.get("owner_id"),
        }
        for camera in stored_cameras
    ]

    camera_manager = CameraManager(
        runtime_cameras
    )

    multi_camera_manager = MultiCameraManager(
        cameras=runtime_cameras,
        inference_config=config["inference"],
        tracking_config=config["tracking"],
        counting_config=config["counting"],
        processing_config=config["processing"],
        camera_manager=camera_manager,
        storage_service=storage_service,
    )

    multi_camera_manager.setup()

    system_overview_service = SystemOverviewService(
        camera_manager=camera_manager,
        multi_camera_manager=multi_camera_manager,
        database_service=database_service,
    )
    system_health_service = SystemHealthService(
        camera_manager=camera_manager,
        multi_camera_manager=multi_camera_manager,
        database=database_service.database,
    )

    print(
        f"Crowd Management API started with "
        f"{len(camera_manager.get_enabled_cameras())} camera(s)."
    )

    yield

    if multi_camera_manager is not None:
        multi_camera_manager.release()

    system_health_service = None
    auth_service = None
    storage_service = None

    print("Crowd Management API stopped.")

app = FastAPI(
    title="Crowd Management API",
    version="1.0",
    lifespan=lifespan,
)


def _json_safe_validation_value(value):
    if isinstance(value, bytes):
        return (
            f"<binary request data: {len(value)} bytes>"
        )
    if isinstance(value, dict):
        return {
            str(key): _json_safe_validation_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [
            _json_safe_validation_value(item)
            for item in value
        ]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content={
            "detail": _json_safe_validation_value(exc.errors()),
        },
    )


def _required_role(path: str, method: str) -> str | None:
    if path in {
        "/health",
        "/auth/config",
        "/auth/login",
        "/auth/register",
        "/docs",
        "/redoc",
        "/openapi.json",
    }:
        return None
    if path.startswith("/auth/"):
        return "AUTHENTICATED"
    if path.startswith("/admin/"):
        return "ADMIN"
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        return "AUTHENTICATED"
    return "AUTHENTICATED"


def _role_allows(user: AuthenticatedUser, required: str) -> bool:
    if required == "AUTHENTICATED":
        return user.role in {"ADMIN", "OPERATOR"}
    if required == "ADMIN":
        return user.role == "ADMIN"
    return user.role in {"ADMIN", "OPERATOR"}


def _current_user(request: Request) -> AuthenticatedUser | None:
    return getattr(request.state, "user", None)


def _resource_owner_id(request: Request) -> str | None:
    user = _current_user(request)
    if not user:
        return None
    if user.role == "OPERATOR":
        return user.owner_id or user.username
    selected = request.headers.get("X-Operator-Username", "").strip()
    return selected or None


def _validate_selected_operator(request: Request):
    user = _current_user(request)
    selected = request.headers.get("X-Operator-Username", "").strip()
    if not selected:
        return
    if user is None or user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Operator context is restricted to administrators.")
    if auth_service is None or not auth_service.active_users.get(selected, False):
        raise HTTPException(status_code=404, detail="Selected operator is not available.")
    account = auth_service.users.get(selected)
    if account is None or account[1] != "OPERATOR":
        raise HTTPException(status_code=400, detail="Selected account is not an operator.")


def _owner_can_access_camera(request: Request, camera_id: str):
    user = _current_user(request)
    owner_id = _resource_owner_id(request)
    if owner_id is None or not database_service:
        return
    camera = database_service.get_camera(camera_id)
    if camera is None or camera.get("owner_id", "system") != owner_id:
        raise HTTPException(status_code=404, detail=f"Camera not found: {camera_id}")


def _visible_camera_ids(request: Request) -> set[str] | None:
    user = _current_user(request)
    owner_id = _resource_owner_id(request)
    if owner_id is None or not database_service:
        return None
    return {
        camera["camera_id"]
        for camera in database_service.get_cameras()
        if camera.get("owner_id", "system") == owner_id
    }


@app.middleware("http")
async def authentication_middleware(request: Request, call_next):
    service = auth_service
    if service is None or not service.enabled:
        return await call_next(request)

    required = _required_role(request.url.path, request.method)
    if required is None:
        return await call_next(request)

    authorization = request.headers.get("Authorization", "")
    token = (
        authorization[7:].strip()
        if authorization.lower().startswith("bearer ")
        else ""
    )
    if not token:
        token = request.cookies.get("crowd_access_token")
    if not token and request.url.path.endswith("/stream"):
        token = request.query_params.get("stream_token", "")

    if not token:
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = service.verify_token(
            token,
            stream_only=request.url.path.endswith("/stream"),
        )
    except ValueError:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not _role_allows(user, required):
        return JSONResponse(
            status_code=403,
            content={"detail": "Insufficient permissions."},
        )

    request.state.user = user
    try:
        _validate_selected_operator(request)
        path_parts = [part for part in request.url.path.split("/") if part]
        if "cameras" in path_parts:
            camera_index = path_parts.index("cameras")
            is_collection_health = (
                len(path_parts) == camera_index + 2
                and path_parts[camera_index + 1] == "health"
            )
            if len(path_parts) > camera_index + 1 and not is_collection_health:
                _owner_can_access_camera(request, path_parts[camera_index + 1])
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    response = await call_next(request)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        audit(request.url.path, user.username, response.status_code < 400)
    return response


@app.get("/auth/config")
async def auth_config():
    service = auth_service
    return {
        "enabled": bool(service and service.enabled),
        "token_expiry_minutes": service.expiry_minutes if service else 60,
    }


@app.post("/auth/login")
async def login(request: Request, payload: LoginRequest):
    service = auth_service
    if service is None or not service.enabled:
        raise HTTPException(
            status_code=409,
            detail="Authentication is disabled.",
        )
    client_key = request.client.host if request.client else "unknown"
    rate_key = f"{client_key}:{payload.username}"
    if not service.login_limiter.allow(rate_key):
        audit("login_rate_limited", success=False)
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Try again later.",
        )
    try:
        user = service.authenticate(payload.username, payload.password)
    except InactiveAccountError:
        audit("login_inactive", success=False)
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive. Please contact admin.",
        ) from None
    if user is None:
        service.login_limiter.record_failure(rate_key)
        audit("login", success=False)
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    service.login_limiter.reset(rate_key)
    audit("login", user.username)
    access_token = service.issue_token(user)
    response = JSONResponse(
        content={
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "expires_in": service.expiry_minutes * 60,
        }
    )
    response.set_cookie(
        "crowd_access_token",
        access_token,
        max_age=service.expiry_minutes * 60,
        httponly=True,
        secure=False,
        samesite="lax",
    )
    return response


@app.post("/auth/register")
async def register_operator(payload: RegistrationRequest):
    service = auth_service
    if service is None or not service.enabled:
        raise HTTPException(status_code=409, detail="Authentication is disabled.")
    try:
        user = service.register_operator(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "Operator account created.", "username": user.username, "role": "OPERATOR"}


@app.get("/admin/operators")
async def list_operators():
    if auth_service is None:
        raise HTTPException(status_code=503, detail="Authentication is not available.")
    return {"operators": [u for u in auth_service.list_users() if u["role"] == "OPERATOR"]}


@app.get("/admin/alerts/count")
async def admin_alert_count():
    if database_service is None:
        raise HTTPException(status_code=503, detail="Database service is not available.")
    return {"count": database_service.get_unresolved_alert_count()}


@app.post("/admin/operators")
async def create_operator(payload: OperatorCreateRequest):
    try:
        user = auth_service.register_operator(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"username": user.username, "role": user.role, "active": True}


@app.get("/admin/operators/{username}")
async def get_operator(username: str):
    operator = next(
        (item for item in auth_service.list_users() if item["username"] == username),
        None,
    )
    if operator is None:
        raise HTTPException(status_code=404, detail="Operator not found.")
    return operator


@app.patch("/admin/operators/{username}")
async def update_operator(username: str, payload: OperatorUpdateRequest):
    try:
        user = auth_service.update_user(username, payload.username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Operator not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "username": user.username,
        "role": user.role,
        "active": next(
            item["active"]
            for item in auth_service.list_users()
            if item["username"] == user.username
        ),
    }


@app.post("/admin/operators/{username}/promote")
async def promote_operator(username: str):
    try:
        user = auth_service.promote_user(username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Operator not found.") from exc
    return {"username": user.username, "role": user.role}


@app.post("/admin/operators/{username}/demote")
async def demote_operator(username: str):
    try:
        user = auth_service.demote_user(username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Operator not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"username": user.username, "role": user.role}


@app.post("/admin/operators/{username}/disable")
async def disable_operator(username: str):
    try:
        auth_service.set_user_active(username, False)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Operator not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"username": username, "active": False}


@app.post("/admin/operators/{username}/activate")
async def activate_operator(username: str):
    try:
        auth_service.set_user_active(username, True)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Operator not found.") from exc
    return {"username": username, "active": True}


@app.delete("/admin/operators/{username}")
async def delete_operator(username: str):
    try:
        auth_service.delete_user(username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Operator not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"username": username, "deleted": True}


@app.post("/auth/stream-token")
async def stream_token(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    service = auth_service
    return {
        "access_token": service.issue_token(user, stream_only=True),
        "token_type": "bearer",
        "expires_in": service.stream_expiry_seconds,
    }


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# SYSTEM / LIVE API
# ==================================================


@app.get("/health")
def health():

    if system_health_service is None:
        return {
            "status": "UP",
            "service": "crowd-management-api",
        }
    return system_health_service.get_health()


@app.get("/system/health")
def get_system_health(request: Request):
    if system_health_service is None:
        raise HTTPException(
            status_code=503,
            detail="System health service is not available.",
        )
    health = system_health_service.get_health()
    user = _current_user(request)
    owner_id = _resource_owner_id(request)
    if owner_id is not None:
        health["cameras"] = [
            item for item in health.get("cameras", [])
            if item.get("owner_id", "system") == owner_id
        ]
        enabled = [item for item in health["cameras"] if item.get("enabled")]
        health["summary"] = {
            "configured": len(health["cameras"]),
            "enabled": len(enabled),
            "healthy": sum(
                1 for item in enabled
                if item.get("status") == "ONLINE"
                and item.get("processing_status") == "HEALTHY"
            ),
            "unhealthy": sum(
                1 for item in enabled
                if not (
                    item.get("status") == "ONLINE"
                    and item.get("processing_status") == "HEALTHY"
                )
            ),
        }
    return health


@app.get("/cameras/health")
def get_cameras_health(request: Request):
    if system_health_service is None:
        raise HTTPException(
            status_code=503,
            detail="System health service is not available.",
        )
    health = system_health_service.get_health()
    owner_id = _resource_owner_id(request)
    cameras = health["cameras"]
    if owner_id is not None:
        cameras = [item for item in cameras if item.get("owner_id", "system") == owner_id]
        enabled = [item for item in cameras if item.get("enabled")]
        health["summary"] = {
            "configured": len(cameras),
            "enabled": len(enabled),
            "healthy": sum(
                1 for item in enabled
                if item.get("status") == "ONLINE"
                and item.get("processing_status") == "HEALTHY"
            ),
            "unhealthy": sum(
                1 for item in enabled
                if not (
                    item.get("status") == "ONLINE"
                    and item.get("processing_status") == "HEALTHY"
                )
            ),
        }
    return {"cameras": cameras, "summary": health["summary"]}


@app.get("/cameras/{camera_id}/health")
def get_camera_health(camera_id: str):
    if system_health_service is None:
        raise HTTPException(
            status_code=503,
            detail="System health service is not available.",
        )
    camera = system_health_service.get_camera_health(camera_id)
    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )
    return camera


@app.get("/cameras")

def get_cameras(request: Request):

    if camera_manager is None or multi_camera_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Camera manager is not available.",
        )

    cameras = camera_manager.get_all_cameras()
    owner_id = _resource_owner_id(request)
    if owner_id is not None:
        cameras = [camera for camera in cameras if camera.get("owner_id", "system") == owner_id]

    return {
        "count": len(cameras),
        "cameras": [
            {
                "camera_id": camera["id"],
                "camera_name": camera.get(
                    "name",
                    camera["id"],
                ),
                "source_type": camera["source_type"],
                "source": camera["source"],
                "loop": camera.get("loop", False),
                "enabled": camera.get("enabled", True),
                "status": multi_camera_manager.workers[camera["id"]].get_status()["status"] if camera["id"] in multi_camera_manager.workers else "DISABLED",
                "processing_status": multi_camera_manager.workers[camera["id"]].get_status()["processing_status"] if camera["id"] in multi_camera_manager.workers else "DISABLED",
            }
            for camera in cameras
        ]
    }

@app.get("/cameras/{camera_id}/status")
def get_camera_status(camera_id: str):

    if multi_camera_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Camera manager is not available.",
        )

    worker = multi_camera_manager.workers.get(
        camera_id
    )

    if worker is None:
        camera = camera_manager.get_camera(camera_id)
        if camera is not None and not camera.get("enabled", True):
            return {
                "camera_id": camera_id,
                "status": "DISABLED",
                "processing_status": "DISABLED",
                "last_error": None,
                "last_frame_time": None,
                "last_inference_time": None,
            }
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    return {
        "camera_id": camera_id,
        **worker.get_status(),
    }


@app.get("/cameras/{camera_id}/result")
def get_camera_result(camera_id: str):

    if multi_camera_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Camera manager is not available.",
        )

    worker = multi_camera_manager.workers.get(
        camera_id
    )

    if worker is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    result_entry = (
        multi_camera_manager
        .get_latest_result_with_timestamp(
            camera_id
        )
    )

    if result_entry is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No result available for camera: "
                f"{camera_id}"
            ),
        )

    result = result_entry["result"]
    result_timestamp = result_entry["timestamp"]

    import time

    age_seconds = (
        time.time()
        - result_timestamp
    )

    status = worker.get_status()

    camera_status = status["status"]
    processing_status = status[
        "processing_status"
    ]

    max_result_age = (
        multi_camera_manager
        .processing_config[
            "max_result_age_seconds"
        ]
    )

    fresh = (
        camera_status == "ONLINE"
        and processing_status
        not in {
            "ERROR",
            "STARTING",
        }
        and age_seconds
        <= max_result_age
    )

    return {
        "camera_id": result.camera_id,
        "camera_status": camera_status,
        "processing_status": processing_status,
        "last_error": status["last_error"],
        "last_frame_time": status["last_frame_time"],
        "last_inference_time": status["last_inference_time"],
        "total_people": result.total_people,
        "zones": [
            {
                "zone_id": zone.zone_id,
                "name": zone.name,
                "count": zone.count,
                "threshold": zone.threshold,
                "status": zone.status,
            }
            for zone in result.zones
        ],
        "result_timestamp": result_timestamp,
        "age_seconds": age_seconds,
        "fresh": fresh,
    }


@app.get("/cameras/{camera_id}/overview")

def get_camera_overview(camera_id: str):

    if multi_camera_manager is None:
        raise HTTPException(status_code=503, detail="Camera manager is not available.")

    worker = multi_camera_manager.workers.get(camera_id)

    if worker is None:
        raise HTTPException(status_code=404, detail=f"Camera not found: {camera_id}")

    status = worker.get_status()

    result_entry = multi_camera_manager.get_latest_result_with_timestamp(camera_id)

    result = None
    result_timestamp = None
    age_seconds = None
    fresh = False

    if result_entry is not None:
        result = result_entry["result"]
        result_timestamp = result_entry["timestamp"]
        import time
        age_seconds = time.time() - result_timestamp
        max_result_age = multi_camera_manager.processing_config["max_result_age_seconds"]
        fresh = (status["status"] == "ONLINE" and status["processing_status"] not in {"ERROR", "STARTING"} and age_seconds <= max_result_age)

    zones = []
    if result is not None:
        zones = [{"zone_id": zone.zone_id, "name": zone.name, "count": zone.count, "threshold": zone.threshold, "status": zone.status} for zone in result.zones]

    return {"camera_id": camera_id, "camera_status": status["status"], "processing_status": status["processing_status"], "last_error": status["last_error"], "last_frame_time": status["last_frame_time"], "last_inference_time": status["last_inference_time"], "result_timestamp": result_timestamp, "age_seconds": age_seconds, "fresh": fresh, "total_people": result.total_people if result is not None else None, "frame_available": worker.get_latest_annotated_frame() is not None, "frame_endpoint": f"/cameras/{camera_id}/frame", "zones": zones}


@app.get("/cameras/{camera_id}/frame")
def get_camera_frame(camera_id: str):

    if multi_camera_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Camera manager is not available.",
        )

    worker = multi_camera_manager.workers.get(
        camera_id
    )

    if worker is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    frame = worker.get_latest_annotated_frame()

    if frame is None:
        raise HTTPException(
            status_code=503,
            detail="Annotated frame is not available yet.",
        )

    import cv2

    success, encoded_frame = cv2.imencode(
        ".jpg",
        frame,
        [
            cv2.IMWRITE_JPEG_QUALITY,
            80,
        ],
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to encode frame.",
        )

    return StreamingResponse(
        iter([encoded_frame.tobytes()]),
        media_type="image/jpeg",
    )


@app.get("/cameras/{camera_id}/stream")
def get_camera_stream(camera_id: str):

    if multi_camera_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Camera manager is not available.",
        )

    worker = multi_camera_manager.workers.get(
        camera_id
    )

    if worker is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    status = worker.get_status()

    if status["status"] not in {
        "ONLINE",
        "STARTING",
    }:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Camera {camera_id} "
                f"is not available."
            ),
        )

    if worker.get_latest_annotated_frame() is None:
        raise HTTPException(
            status_code=503,
            detail="Annotated frame is not available yet.",
        )

    processing_config = getattr(
        multi_camera_manager,
        "processing_config",
        {},
    )
    streamer = FrameStreamer(
        worker=worker,
        jpeg_quality=int(
            processing_config.get("jpeg_quality", 80)
        ),
        stream_fps=float(
            processing_config.get("stream_fps", 10)
        ),
    )

    return StreamingResponse(
        streamer.generate(),
        media_type=(
            "multipart/x-mixed-replace; "
            "boundary=frame"
        ),
        headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )


# ==================================================
# LIVE ALERT API
# ==================================================


@app.get("/alerts")
def get_alerts(request: Request = None):

    if multi_camera_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Camera manager is not available.",
        )

    alerts = (
        multi_camera_manager.get_all_alerts()
    )
    visible = _visible_camera_ids(request) if request is not None else None
    if visible is not None:
        alerts = [alert for alert in alerts if alert.camera_id in visible]

    return {
        "count": len(alerts),
        "alerts": AlertSerializer.to_list(alerts),
    }


@app.get("/alerts/latest")
def get_latest_alert(request: Request):

    if multi_camera_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Camera manager is not available.",
        )

    visible = _visible_camera_ids(request)
    alert = multi_camera_manager.get_latest_alert()
    if alert is not None and visible is not None and alert.camera_id not in visible:
        alert = next(
            (item for item in multi_camera_manager.get_all_alerts() if item.camera_id in visible),
            None,
        )

    if alert is None:
        raise HTTPException(
            status_code=404,
            detail="No alerts available.",
        )

    return AlertSerializer.to_dict(alert)


@app.get("/cameras/{camera_id}/alerts")
def get_camera_alerts(camera_id: str):

    if multi_camera_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Camera manager is not available.",
        )

    worker = multi_camera_manager.workers.get(
        camera_id
    )

    if worker is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    alerts = (
        multi_camera_manager.get_camera_alerts(
            camera_id
        )
    )

    return {
        "camera_id": camera_id,
        "count": len(alerts),
        "alerts": AlertSerializer.to_list(alerts),
    }


@app.get(
    "/cameras/{camera_id}/zones/{zone_id}/alerts"
)
def get_zone_alerts(
    camera_id: str,
    zone_id: str,
):

    if multi_camera_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Camera manager is not available.",
        )

    worker = multi_camera_manager.workers.get(
        camera_id
    )

    if worker is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    alerts = (
        multi_camera_manager.get_zone_alerts(
            camera_id=camera_id,
            zone_id=zone_id,
        )
    )

    return {
        "camera_id": camera_id,
        "zone_id": zone_id,
        "count": len(alerts),
        "alerts": AlertSerializer.to_list(
            alerts
        ),
    }


# ==================================================
# SYSTEM OVERVIEW
# ==================================================


@app.get("/system/overview")
def get_system_overview(request: Request):

    if system_overview_service is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "System overview service "
                "is not available."
            ),
        )

    overview = (
        system_overview_service.get_overview()
    )

    cameras = overview.cameras
    owner_id = _resource_owner_id(request)
    if owner_id is not None:
        cameras = [camera for camera in cameras if camera.get("owner_id", "system") == owner_id]
    visible_ids = {camera.get("camera_id", camera.get("id")) for camera in cameras}
    alerts = [
        alert for alert in overview.alerts
        if owner_id is None or alert.get("camera_id") in visible_ids
    ]
    return {
        "total_cameras": len(cameras),
        "online_cameras": sum(
            1 for camera in cameras
            if str(camera.get("status", "")).upper() == "ONLINE"
        ),
        "offline_cameras": sum(
            1 for camera in cameras
            if str(camera.get("status", "")).upper() not in {"ONLINE", "STALE"}
        ),
        "stale_cameras": sum(
            1 for camera in cameras
            if str(camera.get("status", "")).upper() == "STALE"
        ),
        "total_people": overview.total_people,
        "total_alerts": len(alerts) if owner_id is not None else overview.total_alerts,
        "cameras": cameras,
        "alerts": alerts,
    }


# ==================================================
# DATABASE / HISTORICAL API
# ==================================================

def _validate_history_query(
    limit: int,
    start_timestamp: str | None,
    end_timestamp: str | None,
):
    if limit < 1 or limit > 5000:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 5000.",
        )

    if start_timestamp and end_timestamp:
        if start_timestamp > end_timestamp:
            raise HTTPException(
                status_code=400,
                detail="start_timestamp must be before end_timestamp.",
            )


@app.get("/database/cameras")
def get_database_cameras(request: Request):

    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    cameras = database_service.get_cameras()
    visible = _visible_camera_ids(request)
    if visible is not None:
        cameras = [camera for camera in cameras if camera["camera_id"] in visible]
    return {"cameras": cameras}


@app.get("/database/cameras/{camera_id}")
def get_database_camera(
    camera_id: str,
):

    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    camera = database_service.get_camera(
        camera_id
    )

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    return {
        "camera": camera
    }


@app.get("/database/cameras/{camera_id}/crowd")
def get_database_crowd(
    camera_id: str,
    limit: int = 100,
    start_timestamp: str | None = None,
    end_timestamp: str | None = None,
):

    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    camera = database_service.get_camera(
        camera_id
    )

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    _validate_history_query(
        limit,
        start_timestamp,
        end_timestamp,
    )

    results = (
        database_service.get_crowd_history(
            camera_id,
            start_timestamp,
            end_timestamp,
            limit,
        )
        if start_timestamp or end_timestamp
        else database_service.get_recent_crowd(
            camera_id=camera_id,
            limit=limit,
        )
    )

    return {
        "camera_id": camera_id,
        "results": results,
    }


@app.get("/database/cameras/{camera_id}/history")
def get_database_history(
    camera_id: str,
    zone_id: str | None = None,
    start_timestamp: str | None = None,
    end_timestamp: str | None = None,
    limit: int = 1000,
):
    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    if database_service.get_camera(camera_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    _validate_history_query(
        limit,
        start_timestamp,
        end_timestamp,
    )

    if zone_id:
        results = database_service.get_zone_history(
            camera_id,
            zone_id,
            start_timestamp,
            end_timestamp,
            limit,
        )
        analytics = database_service.get_zone_analytics(
            camera_id,
            zone_id,
            start_timestamp,
            end_timestamp,
        )
        history_type = "zone"
    else:
        results = database_service.get_crowd_history(
            camera_id,
            start_timestamp,
            end_timestamp,
            limit,
        )
        analytics = database_service.get_crowd_analytics(
            camera_id,
            start_timestamp,
            end_timestamp,
        )
        history_type = "camera"

    return {
        "camera_id": camera_id,
        "zone_id": zone_id,
        "type": history_type,
        "count": len(results),
        "results": results,
        "analytics": analytics,
    }


@app.get("/database/cameras/{camera_id}/analytics")
def get_database_analytics(
    camera_id: str,
    zone_id: str | None = None,
    start_timestamp: str | None = None,
    end_timestamp: str | None = None,
):
    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    if database_service.get_camera(camera_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    _validate_history_query(
        1,
        start_timestamp,
        end_timestamp,
    )

    if zone_id:
        analytics = database_service.get_zone_analytics(
            camera_id,
            zone_id,
            start_timestamp,
            end_timestamp,
        )
    else:
        analytics = database_service.get_crowd_analytics(
            camera_id,
            start_timestamp,
            end_timestamp,
        )

    return {
        "camera_id": camera_id,
        "zone_id": zone_id,
        "analytics": analytics,
    }


@app.get(
    "/database/cameras/{camera_id}/zones/{zone_id}"
)
def get_database_zone(
    camera_id: str,
    zone_id: str,
    limit: int = 100,
    start_timestamp: str | None = None,
    end_timestamp: str | None = None,
):

    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    camera = database_service.get_camera(
        camera_id
    )

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    _validate_history_query(
        limit,
        start_timestamp,
        end_timestamp,
    )

    results = (
        database_service.get_zone_history(
            camera_id,
            zone_id,
            start_timestamp,
            end_timestamp,
            limit,
        )
        if start_timestamp or end_timestamp
        else database_service.get_recent_zone(
            camera_id=camera_id,
            zone_id=zone_id,
            limit=limit,
        )
    )

    return {
        "camera_id": camera_id,
        "zone_id": zone_id,
        "count": len(results),
        "results": results,
    }


@app.get("/database/cameras/{camera_id}/zone-history")
def get_database_camera_zone_history(
    camera_id: str,
    limit: int = 20,
):
    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    if database_service.get_camera(camera_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    _validate_history_query(limit, None, None)

    results = database_service.get_recent_zone_history(
        camera_id,
        limit_per_zone=limit,
    )
    grouped = {}
    for result in results:
        grouped.setdefault(result["zone_id"], []).append(result)

    return {
        "camera_id": camera_id,
        "zones": [
            {
                "zone_id": zone_id,
                "history": history,
            }
            for zone_id, history in grouped.items()
        ],
    }


@app.get("/database/alerts")
def get_database_alerts(
    request: Request,
    limit: int = 100,
):

    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    if limit < 1 or limit > 5000:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 5000.",
        )

    alerts = database_service.get_alerts(limit=limit)
    visible = _visible_camera_ids(request)
    if visible is not None:
        alerts = [alert for alert in alerts if alert["camera_id"] in visible]
    return {"alerts": alerts}


@app.get("/database/cameras/{camera_id}/alerts")
def get_database_camera_alerts(
    camera_id: str,
    limit: int = 100,
):

    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    camera = database_service.get_camera(
        camera_id
    )

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    if limit < 1 or limit > 5000:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 5000.",
        )

    return {
        "camera_id": camera_id,
        "alerts": database_service.get_camera_alerts(
            camera_id=camera_id,
            limit=limit,
        ),
    }


@app.get(
    "/database/cameras/{camera_id}/zones/"
    "{zone_id}/alerts"
)
def get_database_zone_alerts(
    camera_id: str,
    zone_id: str,
    limit: int = 100,
):

    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    camera = database_service.get_camera(
        camera_id
    )

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    if limit < 1 or limit > 5000:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 5000.",
        )

    alerts = database_service.get_zone_alerts(
        camera_id=camera_id,
        zone_id=zone_id,
        limit=limit,
    )

    return {
        "camera_id": camera_id,
        "zone_id": zone_id,
        "count": len(alerts),
        "alerts": alerts,
    }
# ==================================================
# Dynamic Zone Management
# ==================================================


def _validate_zone_request(
    zone_id: str,
    zone_name: str,
    polygon: list[list[float]],
    threshold: int,
    point: str,
):
    if not zone_id.strip():
        raise HTTPException(
            status_code=400,
            detail="zone_id cannot be empty.",
        )

    if not zone_name.strip():
        raise HTTPException(
            status_code=400,
            detail="zone_name cannot be empty.",
        )

    if len(polygon) < 3:
        raise HTTPException(
            status_code=400,
            detail="polygon must contain at least 3 points.",
        )

    for index, coordinate in enumerate(polygon):
        if len(coordinate) != 2:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"polygon point {index + 1} "
                    "must contain exactly [x, y]."
                ),
            )

        try:
            float(coordinate[0])
            float(coordinate[1])
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"polygon point {index + 1} "
                    "contains invalid coordinates."
                ),
            )

    if threshold <= 0:
        raise HTTPException(
            status_code=400,
            detail="threshold must be greater than zero.",
        )

    if point not in {
        "bottom_center",
        "center",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "point must be 'bottom_center' "
                "or 'center'."
            ),
        )


def _serialize_zone(zone):
    return {
        "zone_id": zone["zone_id"],
        "camera_id": zone["camera_id"],
        "zone_name": zone["zone_name"],
        "polygon": zone["polygon"],
        "threshold": zone["threshold"],
        "point": zone["point"],
        "enabled": zone["enabled"],
        "created_at": zone["created_at"],
        "updated_at": zone["updated_at"],
    }


@app.get("/cameras/{camera_id}/zones")
def get_camera_zones(camera_id: str):
    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    camera = database_service.get_camera(camera_id)

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    zones = database_service.zone_repository.get_by_camera(
        camera_id
    )

    return {
        "camera_id": camera_id,
        "count": len(zones),
        "zones": [
            _serialize_zone(zone)
            for zone in zones
        ],
    }


@app.post("/cameras/{camera_id}/zones")
def create_camera_zone(
    camera_id: str,
    request: ZoneCreateRequest,
):
    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    camera = database_service.get_camera(camera_id)

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    _validate_zone_request(
        zone_id=request.zone_id,
        zone_name=request.zone_name,
        polygon=request.polygon,
        threshold=request.threshold,
        point=request.point,
    )

    existing = database_service.zone_repository.get(
        camera_id=camera_id,
        zone_id=request.zone_id,
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Zone already exists: {request.zone_id}",
        )

    database_service.zone_repository.save(
        zone_id=request.zone_id.strip(),
        camera_id=camera_id,
        zone_name=request.zone_name.strip(),
        polygon=request.polygon,
        threshold=request.threshold,
        point=request.point,
        enabled=request.enabled,
    )

    zone = database_service.zone_repository.get(
        camera_id=camera_id,
        zone_id=request.zone_id.strip(),
    )

    # Refresh the running pipeline so the new zone becomes active immediately.
    if multi_camera_manager is not None:
        if camera_id in multi_camera_manager.pipelines:
            try:
                multi_camera_manager.refresh_camera_zones(
                    camera_id
                )
            except Exception:
                LOGGER.warning(
                    "Zone %s was saved, but the running pipeline could not be refreshed.",
                    request.zone_id,
                    exc_info=True,
                )

    return {
        "message": "Zone created successfully.",
        "zone": _serialize_zone(zone),
    }


@app.put("/cameras/{camera_id}/zones/{zone_id}")
def update_camera_zone(
    camera_id: str,
    zone_id: str,
    request: ZoneUpdateRequest,
):
    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    camera = database_service.get_camera(camera_id)

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    existing = database_service.zone_repository.get(
        camera_id=camera_id,
        zone_id=zone_id,
    )

    if existing is None:
        raise HTTPException(
            status_code=404,
            detail=f"Zone not found: {zone_id}",
        )

    _validate_zone_request(
        zone_id=zone_id,
        zone_name=request.zone_name,
        polygon=request.polygon,
        threshold=request.threshold,
        point=request.point,
    )

    database_service.zone_repository.update(
        camera_id=camera_id,
        zone_id=zone_id,
        zone_name=request.zone_name.strip(),
        polygon=request.polygon,
        threshold=request.threshold,
        point=request.point,
        enabled=request.enabled,
    )

    zone = database_service.zone_repository.get(
        camera_id=camera_id,
        zone_id=zone_id,
    )

    # Refresh the running pipeline so the updated zone becomes active immediately.
    if multi_camera_manager is not None:
        if camera_id in multi_camera_manager.pipelines:
            try:
                multi_camera_manager.refresh_camera_zones(
                    camera_id
                )
            except Exception:
                LOGGER.warning(
                    "Zone %s was updated, but the running pipeline could not be refreshed.",
                    zone_id,
                    exc_info=True,
                )

    return {
        "message": "Zone updated successfully.",
        "zone": _serialize_zone(zone),
    }


@app.delete("/cameras/{camera_id}/zones/{zone_id}")
def delete_camera_zone(
    camera_id: str,
    zone_id: str,
):
    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    camera = database_service.get_camera(camera_id)

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    existing = database_service.zone_repository.get(
        camera_id=camera_id,
        zone_id=zone_id,
    )

    if existing is None:
        raise HTTPException(
            status_code=404,
            detail=f"Zone not found: {zone_id}",
        )

    database_service.zone_repository.delete(
        camera_id=camera_id,
        zone_id=zone_id,
    )

    # Refresh the running pipeline so the deleted zone stops being monitored immediately.
    if multi_camera_manager is not None:
        if camera_id in multi_camera_manager.pipelines:
            try:
                multi_camera_manager.refresh_camera_zones(camera_id)
            except Exception:
                LOGGER.warning(
                    "Zone %s for camera %s was deleted, but the running pipeline could not be refreshed.",
                    zone_id,
                    camera_id,
                    exc_info=True,
                )

    return {
        "message": "Zone deleted successfully.",
        "camera_id": camera_id,
        "zone_id": zone_id,
    }


@app.delete("/cameras/{camera_id}/zones")
def delete_camera_zones(camera_id: str):
    if database_service is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not available.",
        )

    camera = database_service.get_camera(camera_id)

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    database_service.zone_repository.delete_by_camera(camera_id)

    if multi_camera_manager is not None:
        if camera_id in multi_camera_manager.pipelines:
            try:
                multi_camera_manager.refresh_camera_zones(camera_id)
            except Exception:
                LOGGER.warning(
                    "Zones for camera %s were deleted, but the running pipeline could not be refreshed.",
                    camera_id,
                    exc_info=True,
                )

    return {
        "message": "All zones deleted successfully.",
        "camera_id": camera_id,
        "count": 0,
    }


# ==================================================
# Dynamic Camera Management
# ==================================================


@app.post("/cameras")
async def create_camera(http_request: Request):

    request = await _read_camera_create_payload(http_request)

    if multi_camera_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Camera manager is not available.",
        )

    if request["source_type"] not in {
        "file",
        "rtsp",
        "drone",
    }:
        raise HTTPException(
            status_code=400,
            detail="source_type must be 'file', 'rtsp' or 'drone'.",
        )

    camera_id = request["camera_id"]

    if not camera_id:
        raise HTTPException(
            status_code=400,
            detail="camera_id cannot be empty.",
        )

    if not request["source"]:
        raise HTTPException(
            status_code=400,
            detail="source cannot be empty.",
        )

    existing = (
        multi_camera_manager.camera_repository.get(
            camera_id
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Camera already exists: {camera_id}",
        )

    owner_id = _resource_owner_id(http_request)
    if not owner_id:
        raise HTTPException(
            status_code=400,
            detail="Select an operator before creating a camera.",
        )

    camera = {
        "id": camera_id,
        "name": request["camera_name"],
        "source_type": request["source_type"],
        "source": request["source"],
        "loop": request["loop"],
        "enabled": request["enabled"],
        "owner_id": owner_id,
    }

    try:
        multi_camera_manager.add_camera(
            camera
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start camera: {exc}",
        )

    return {
        "message": "Camera created successfully.",
        "camera": {
            "camera_id": camera_id,
            "camera_name": request["camera_name"],
            "source_type": request["source_type"],
            "source": request["source"],
            "loop": request["loop"],
            "enabled": request["enabled"],
            "owner_id": camera["owner_id"],
        },
    }


@app.put("/cameras/{camera_id}")
async def update_camera(
    camera_id: str,
    request: Request,
):

    if multi_camera_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Camera manager is not available.",
        )

    existing = (
        multi_camera_manager.camera_repository.get(
            camera_id
        )
    )

    if existing is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    payload = await _read_camera_update_payload(
        camera_id=camera_id,
        request=request,
        existing=existing,
    )

    if payload["source_type"] not in {
        "file",
        "rtsp",
        "drone",
    }:
        raise HTTPException(
            status_code=400,
            detail="source_type must be 'file', 'rtsp' or 'drone'.",
        )

    if not payload["camera_name"]:
        raise HTTPException(
            status_code=400,
            detail="camera_name cannot be empty.",
        )

    if not payload["source"]:
        raise HTTPException(
            status_code=400,
            detail="source cannot be empty.",
        )

    camera = {
        "id": camera_id,
        "name": payload["camera_name"],
        "source_type": payload["source_type"],
        "source": payload["source"],
        "loop": payload["loop"],
        "enabled": payload["enabled"],
    }

    try:
        multi_camera_manager.update_camera(
            camera
        )
    except SupabaseStorageError as exc:
        LOGGER.warning(
            "Camera %s update failed while accessing Supabase Storage: %s",
            camera_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail="Camera video storage is unavailable.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update camera: {exc}",
        )

    if (
        storage_service is not None
        and existing.get("source") != payload["source"]
        and storage_service.is_storage_source(existing.get("source"))
    ):
        try:
            storage_service.delete(existing["source"])
        except SupabaseStorageError:
            LOGGER.warning(
                "Camera %s was updated, but its previous storage object could not be deleted.",
                camera_id,
                exc_info=True,
            )

    return {
        "message": "Camera updated successfully.",
        "camera": {
            "camera_id": camera_id,
            "camera_name": payload["camera_name"],
            "source_type": payload["source_type"],
            "source": payload["source"],
            "loop": payload["loop"],
            "enabled": payload["enabled"],
        },
    }


@app.delete("/cameras/{camera_id}")
def delete_camera(camera_id: str):

    if multi_camera_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Camera manager is not available.",
        )

    existing = (
        multi_camera_manager.camera_repository.get(
            camera_id
        )
    )

    if existing is None:
        raise HTTPException(
            status_code=404,
            detail=f"Camera not found: {camera_id}",
        )

    try:
        multi_camera_manager.delete_camera(
            camera_id
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete camera: {exc}",
        )

    if storage_service is not None and storage_service.is_storage_source(existing.get("source")):
        try:
            storage_service.delete(existing["source"])
        except SupabaseStorageError:
            LOGGER.error(
                "Camera %s was deleted, but its storage object could not be deleted.",
                camera_id,
                exc_info=True,
            )

    return {
        "message": "Camera deleted successfully.",
        "camera_id": camera_id,
    }


@app.post("/cameras/{camera_id}/enable")
def enable_camera(camera_id: str):
    if multi_camera_manager is None:
        raise HTTPException(status_code=503, detail="Camera manager is not available.")
    try:
        multi_camera_manager.enable_camera(camera_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to enable camera: {exc}")
    return {"message": "Camera enabled successfully.", "camera_id": camera_id}


@app.post("/cameras/{camera_id}/disable")
def disable_camera(camera_id: str):
    if multi_camera_manager is None:
        raise HTTPException(status_code=503, detail="Camera manager is not available.")
    try:
        multi_camera_manager.disable_camera(camera_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to disable camera: {exc}")
    return {"message": "Camera disabled successfully.", "camera_id": camera_id}


@app.post("/cameras/{camera_id}/restart")
def restart_camera(camera_id: str):
    if multi_camera_manager is None:
        raise HTTPException(status_code=503, detail="Camera manager is not available.")
    try:
        multi_camera_manager.restart_camera(camera_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to restart camera: {exc}")
    return {"message": "Camera restarted successfully.", "camera_id": camera_id}
