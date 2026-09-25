"""Safety fixtures for PostgreSQL-backed pytest runs.

Database-backed tests must opt into a dedicated test database.  The application
loads ``.env`` during import, so relying on ``CROWD_DATABASE_URL`` alone can
silently run tests against a production database.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import psycopg
import pytest


_DATABASE_TEST_MODULES = {
    "test_api.py",
    "test_camera_frame_api.py",
    "test_camera_overview.py",
    "test_phase16_security.py",
    "test_phase_authorization.py",
    "test_phase20_deployment.py",
    "test_phase6_camera_lifecycle.py",
    "test_overview_api.py",
    "test_alert_api.py",
}


def _test_database_url() -> str:
    url = os.getenv("CROWD_TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip(
            "Database-backed tests require CROWD_TEST_DATABASE_URL; "
            "refusing to use CROWD_DATABASE_URL or .env"
        )
    configured_url = os.getenv("CROWD_DATABASE_URL", "").strip()
    if configured_url and configured_url == url:
        pytest.fail(
            "CROWD_TEST_DATABASE_URL must be different from "
            "CROWD_DATABASE_URL to prevent production writes"
        )
    return url


def _truncate_test_database(test_url: str) -> None:
    with psycopg.connect(test_url, autocommit=True) as connection:
        tables = connection.execute(
            """
            SELECT tablename
            FROM pg_catalog.pg_tables
            WHERE schemaname = 'public'
              AND tablename NOT LIKE 'spatial_%'
            """
        ).fetchall()
        if tables:
            identifiers = ", ".join(
                f'"public"."{row[0].replace(chr(34), chr(34) * 2)}"'
                for row in tables
            )
            connection.execute(
                f"TRUNCATE TABLE {identifiers} RESTART IDENTITY CASCADE"
            )


@pytest.fixture
def unique_id() -> str:
    """Provide collision-resistant IDs for database-backed test records."""
    return f"test-{uuid.uuid4().hex}"


@pytest.fixture(autouse=True)
def isolated_postgresql(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """Route DB tests to a dedicated URL and clear only that test database."""

    module_name = Path(str(request.path)).name
    database_test = module_name in _DATABASE_TEST_MODULES
    if module_name == "test_phase16_security.py":
        database_test = request.node.name in {
            "test_login_and_role_protection",
            "test_stream_token_endpoint_returns_short_lived_token",
            "test_owner_read_scope_is_authenticated",
            "test_owner_can_read_and_is_authenticated",
            "test_route_authentication_matrix",
            "test_login_rate_limit_lockout_and_reset",
            "test_login_endpoint_rate_limit_and_success_reset",
            "test_admin_is_authorized_for_mutation_routes",
            "test_stream_requires_cookie_and_preserves_mjpeg",
            "test_invalid_token_is_rejected",
            "test_secrets_are_not_logged",
        }
    if not database_test:
        yield
        return

    test_url = _test_database_url()
    monkeypatch.setenv("CROWD_DATABASE_URL", test_url)
    _truncate_test_database(test_url)
    yield

    # Every application operation commits independently.  Cleanup therefore
    # happens after the test, in the isolated database only, with FK cascades.
    _truncate_test_database(test_url)
