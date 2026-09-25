from pathlib import Path
import os

import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "app.yaml"
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:4173,http://127.0.0.1:4173"
)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return config


def resolve_path(path: str) -> Path:
    """
    Resolve a project-relative path against PROJECT_ROOT.

    Absolute paths are returned unchanged.
    """

    path_obj = Path(path)

    if path_obj.is_absolute():
        return path_obj

    return PROJECT_ROOT / path_obj


def get_cors_origins() -> list[str]:
    """Return configured browser origins without changing local defaults."""

    configured = os.getenv(
        "CROWD_CORS_ORIGINS",
        DEFAULT_CORS_ORIGINS,
    )

    return [
        origin.strip()
        for origin in configured.split(",")
        if origin.strip()
    ]