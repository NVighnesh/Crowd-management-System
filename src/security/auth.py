import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import threading
from collections import OrderedDict
from typing import Any
from dataclasses import dataclass


LOGGER = logging.getLogger(__name__)


class InactiveAccountError(Exception):
    """Raised only after a user's password has been verified."""


class LoginRateLimiter:
    def __init__(
        self,
        enabled: bool = True,
        max_failures: int = 5,
        window_seconds: int = 300,
        lockout_seconds: int = 300,
        max_entries: int = 1024,
    ):
        self.enabled = enabled
        self.max_failures = max(1, max_failures)
        self.window_seconds = max(1, window_seconds)
        self.lockout_seconds = max(1, lockout_seconds)
        self.max_entries = max(16, max_entries)
        self._entries: OrderedDict[str, tuple[int, float, float]] = OrderedDict()
        self._lock = threading.Lock()

    def _prune(self, now: float):
        for key, (_, last_failure, locked_until) in list(self._entries.items()):
            if locked_until <= now and last_failure + self.window_seconds <= now:
                self._entries.pop(key, None)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def allow(self, key: str, now: float | None = None) -> bool:
        if not self.enabled:
            return True
        now = now if now is not None else time.monotonic()
        with self._lock:
            self._prune(now)
            entry = self._entries.get(key)
            return not entry or entry[2] <= now

    def record_failure(self, key: str, now: float | None = None):
        if not self.enabled:
            return
        now = now if now is not None else time.monotonic()
        with self._lock:
            self._prune(now)
            failures, first_failure, _ = self._entries.get(
                key,
                (0, now, 0.0),
            )
            if now - first_failure > self.window_seconds:
                failures, first_failure = 0, now
            failures += 1
            locked_until = (
                now + self.lockout_seconds
                if failures >= self.max_failures
                else 0.0
            )
            self._entries[key] = (failures, first_failure, locked_until)
            self._entries.move_to_end(key)
            self._prune(now)

    def reset(self, key: str):
        with self._lock:
            self._entries.pop(key, None)


def hash_password(password: str, salt: bytes | None = None) -> str:
    if not password:
        raise ValueError("Password cannot be empty.")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        210_000,
    )
    return "pbkdf2_sha256$210000$%s$%s" % (
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt_text, digest_text = encoded.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(rounds),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _encode_part(value: dict) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(value, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")


def _decode_part(value: str) -> dict:
    padding = "=" * (-len(value) % 4)
    return json.loads(
        base64.urlsafe_b64decode((value + padding).encode("ascii"))
    )


@dataclass(frozen=True)
class AuthenticatedUser:
    username: str
    role: str
    scope: str = "api"
    user_id: str | None = None
    owner_id: str | None = None


class AuthService:
    def __init__(self, config: dict | None = None, database=None):
        config = config or {}
        self.enabled = bool(config.get("enabled", False))
        self.expiry_minutes = max(
            1,
            int(config.get("token_expiry_minutes", 60)),
        )
        self.stream_expiry_seconds = max(
            30,
            int(config.get("stream_token_expiry_seconds", 300)),
        )
        self.secret = (
            os.getenv("CROWD_AUTH_SECRET")
            or str(config.get("secret", ""))
        )
        self.username = (
            os.getenv("CROWD_ADMIN_USERNAME")
            or str(config.get("admin_username", ""))
        )
        password = os.getenv(
            "CROWD_ADMIN_PASSWORD",
            str(config.get("admin_password", "")),
        )
        configured_hash = os.getenv("CROWD_ADMIN_PASSWORD_HASH", "")
        self.password_hash = configured_hash or (
            hash_password(password) if password else ""
        )
        self.role = "ADMIN"
        rate_limit = config.get("login_rate_limit", {})
        self.login_limiter = LoginRateLimiter(
            enabled=bool(rate_limit.get("enabled", True)),
            max_failures=int(rate_limit.get("max_failures", 5)),
            window_seconds=int(rate_limit.get("window_seconds", 300)),
            lockout_seconds=int(rate_limit.get("lockout_seconds", 300)),
        )
        self.users: dict[str, tuple[str, str]] = {
            self.username: (self.password_hash, self.role)
        } if self.username and self.password_hash else {}
        self.active_users: dict[str, bool] = {
            name: True for name in self.users
        }
        self.database = database
        if database is not None:
            for account in database.fetch_all(
                "SELECT username, password_hash, role, active FROM users"
            ):
                if account["username"] != "system":
                    self.users[account["username"]] = (
                        account["password_hash"],
                        "OPERATOR" if str(account["role"]).upper() == "OWNER" else str(account["role"]).upper(),
                    )
                    self.active_users[account["username"]] = bool(account["active"])
        configured_users: Any = config.get("users", [])
        raw_users = os.getenv("CROWD_USERS_JSON", "")
        if raw_users:
            try:
                configured_users = json.loads(raw_users)
            except json.JSONDecodeError as exc:
                raise ValueError("CROWD_USERS_JSON must contain valid JSON.") from exc
        configured_usernames = set()
        for account in configured_users or []:
            name = str(account.get("username", ""))
            password_hash = str(account.get("password_hash", ""))
            if name and password_hash and name != self.username:
                # A configured account is only a seed for a missing row.
                # Existing database state, especially ``active``, is
                # authoritative and must survive application restarts.
                if name not in self.users:
                    self.users[name] = (password_hash, "OPERATOR")
                    self.active_users[name] = True
                configured_usernames.add(name)

        # Explicit administrator environment settings may refresh the
        # password, but must not reset a persisted active/inactive state.
        if self.username and self.password_hash:
            self.users[self.username] = (self.password_hash, "ADMIN")
            self.active_users.setdefault(self.username, True)

        if database is not None:
            for username in configured_usernames:
                password_hash, role = self.users[username]
                if not password_hash:
                    continue
                database.execute(
                    """
                    INSERT INTO users (
                        user_id, username, password_hash, role, active
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT(username) DO NOTHING
                    """,
                    (
                        username,
                        username,
                        password_hash,
                        role,
                        self.active_users.get(username, True),
                    ),
                )
            if self.username and self.password_hash:
                database.execute(
                    """
                    INSERT INTO users (
                        user_id, username, password_hash, role, active
                    )
                    VALUES (%s, %s, %s, 'ADMIN', TRUE)
                    ON CONFLICT(username) DO UPDATE SET
                        password_hash = excluded.password_hash,
                        role = 'ADMIN',
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        self.username,
                        self.username,
                        self.password_hash,
                    ),
                )

        if self.enabled and (
            len(self.secret) < 32
            or not self.username
            or not self.password_hash
        ):
            raise ValueError(
                "Security is enabled but CROWD_AUTH_SECRET, "
                "CROWD_ADMIN_USERNAME and a password/hash are not configured."
            )

    def authenticate(self, username: str, password: str) -> AuthenticatedUser | None:
        account = self.users.get(username)
        if self.database is not None:
            persisted = self.database.fetch_one(
                """
                SELECT password_hash, role, active
                FROM users
                WHERE username = %s
                """,
                (username,),
            )
            if persisted is None:
                return None
            account = (
                persisted["password_hash"],
                str(persisted["role"]).upper(),
            )
            self.users[username] = account
            self.active_users[username] = bool(persisted["active"])
        if not account:
            return None
        password_hash, role = account
        if not verify_password(password, password_hash):
            return None
        if not self.active_users.get(username, True):
            raise InactiveAccountError(username)
        if role not in {"ADMIN", "OPERATOR"}:
            return None
        owner_id = None if role == "ADMIN" else username
        return AuthenticatedUser(username, role, owner_id=owner_id)

    def register_operator(self, username: str, password: str) -> AuthenticatedUser:
        username = username.strip()
        if not username or not password:
            raise ValueError("Username and password are required.")
        if username in self.users:
            raise ValueError("Username already exists.")
        self.users[username] = (hash_password(password), "OPERATOR")
        self.active_users[username] = True
        if self.database is not None:
            self.database.execute(
                """
                INSERT INTO users (user_id, username, password_hash, role, active)
                VALUES (%s, %s, %s, 'OPERATOR', TRUE)
                """,
                (username, username, self.users[username][0]),
            )
        return AuthenticatedUser(username, "OPERATOR", owner_id=username)

    def list_users(self):
        if self.database is not None:
            return [
                {
                    "username": account["username"],
                    "role": str(account["role"]).upper(),
                    "active": bool(account["active"]),
                    "created_at": account.get("created_at"),
                    "camera_count": int(account.get("camera_count") or 0),
                    "zone_count": int(account.get("zone_count") or 0),
                }
                for account in self.database.fetch_all(
                    """
                    SELECT
                        u.username,
                        u.role,
                        u.active,
                        u.created_at,
                        COUNT(DISTINCT c.camera_id) AS camera_count,
                        COUNT(DISTINCT z.zone_id) AS zone_count
                    FROM users AS u
                    LEFT JOIN cameras AS c ON c.owner_id = u.user_id
                    LEFT JOIN zones AS z ON z.camera_id = c.camera_id
                    WHERE u.username <> 'system'
                    GROUP BY u.username, u.role, u.active, u.created_at
                    ORDER BY u.created_at ASC
                    """
                )
            ]
        return [
            {"username": username, "role": role, "active": self.active_users.get(username, True)}
            for username, (_, role) in self.users.items()
        ]

    def promote_user(self, username: str):
        account = self.users.get(username)
        if not account:
            raise KeyError(username)
        self.users[username] = (account[0], "ADMIN")
        if self.database is not None:
            self.database.execute(
                "UPDATE users SET role = 'ADMIN' WHERE username = %s",
                (username,),
            )
        return AuthenticatedUser(username, "ADMIN")

    def demote_user(self, username: str):
        account = self.users.get(username)
        if not account:
            raise KeyError(username)
        if account[1] != "ADMIN":
            return AuthenticatedUser(username, "OPERATOR", owner_id=username)
        active_admins = sum(
            1 for name, (_, role) in self.users.items()
            if role == "ADMIN" and self.active_users.get(name, True)
        )
        if self.active_users.get(username, True) and active_admins <= 1:
            raise ValueError("The final active administrator cannot be demoted.")
        self.users[username] = (account[0], "OPERATOR")
        if self.database is not None:
            self.database.execute(
                "UPDATE users SET role = 'OPERATOR' WHERE username = %s",
                (username,),
            )
        return AuthenticatedUser(username, "OPERATOR", owner_id=username)

    def set_user_active(self, username: str, active: bool):
        if username not in self.users:
            raise KeyError(username)
        if not active and self.users[username][1] == "ADMIN":
            active_admins = sum(
                1 for name, (_, role) in self.users.items()
                if role == "ADMIN" and self.active_users.get(name, True)
            )
            if active_admins <= 1:
                raise ValueError("The final active administrator cannot be disabled.")
        self.active_users[username] = active
        if self.database is not None:
            self.database.execute(
                "UPDATE users SET active = %s WHERE username = %s",
                (active, username),
            )

    def update_user(self, username: str, new_username: str | None = None):
        account = self.users.get(username)
        if not account:
            raise KeyError(username)
        target = (new_username or username).strip()
        if not target:
            raise ValueError("Username is required.")
        if target != username and target in self.users:
            raise ValueError("Username already exists.")
        if target != username:
            self.users[target] = account
            self.active_users[target] = self.active_users.get(username, True)
            del self.users[username]
            self.active_users.pop(username, None)
            if self.database is not None:
                self.database.execute(
                    "UPDATE users SET username = %s, user_id = %s WHERE username = %s",
                    (target, target, username),
                )
                self.database.execute(
                    "UPDATE cameras SET owner_id = %s WHERE owner_id = %s",
                    (target, username),
                )
        return AuthenticatedUser(target, account[1], owner_id=None if account[1] == "ADMIN" else target)

    def delete_user(self, username: str):
        account = self.users.get(username)
        if not account:
            raise KeyError(username)
        if account[1] == "ADMIN":
            raise ValueError("Administrators cannot be deleted.")
        if self.database is not None:
            with self.database.transaction() as connection:
                camera_rows = connection.execute(
                    "SELECT camera_id FROM cameras WHERE owner_id = %s",
                    (username,),
                ).fetchall()
                camera_ids = [row["camera_id"] for row in camera_rows]
                if camera_ids:
                    placeholders = ", ".join(["%s"] * len(camera_ids))
                    for table in ("alerts", "zone_results", "crowd_results", "zones"):
                        connection.execute(
                            f"DELETE FROM {table} WHERE camera_id IN ({placeholders})",
                            tuple(camera_ids),
                        )
                    connection.execute(
                        f"DELETE FROM cameras WHERE camera_id IN ({placeholders})",
                        tuple(camera_ids),
                    )
                connection.execute(
                    "DELETE FROM users WHERE username = %s AND role = 'OPERATOR'",
                    (username,),
                )
        self.users.pop(username, None)
        self.active_users.pop(username, None)
        return True

    def issue_token(
        self,
        user: AuthenticatedUser,
        stream_only: bool = False,
    ) -> str:
        now = int(time.time())
        expiry = now + (
            self.stream_expiry_seconds
            if stream_only
            else self.expiry_minutes * 60
        )
        header = _encode_part({"alg": "HS256", "typ": "JWT"})
        payload = _encode_part(
            {
                "sub": user.username,
                "role": user.role,
                "user_id": user.user_id,
                "owner_id": user.owner_id,
                "scope": "stream" if stream_only else "api",
                "iat": now,
                "exp": expiry,
            }
        )
        signing_input = f"{header}.{payload}".encode("ascii")
        signature = hmac.new(
            self.secret.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        return f"{header}.{payload}.{base64.urlsafe_b64encode(signature).decode('ascii').rstrip('=')}"

    def verify_token(self, token: str, stream_only: bool = False) -> AuthenticatedUser:
        try:
            header, payload, signature = token.split(".")
            signing_input = f"{header}.{payload}".encode("ascii")
            expected = hmac.new(
                self.secret.encode("utf-8"),
                signing_input,
                hashlib.sha256,
            ).digest()
            supplied = base64.urlsafe_b64decode(
                (signature + "=" * (-len(signature) % 4)).encode("ascii")
            )
            claims = _decode_part(payload)
            if not hmac.compare_digest(expected, supplied):
                raise ValueError("Invalid token signature")
            if int(claims["exp"]) <= int(time.time()):
                raise ValueError("Expired token")
            if stream_only and claims.get("scope") not in {"api", "stream"}:
                raise ValueError("Invalid stream scope")
            username = str(claims["sub"])
            role = str(claims["role"]).upper()
            if role not in {"ADMIN", "OPERATOR"}:
                raise ValueError("Invalid role")
            if username not in self.users or not self.active_users.get(username, False):
                raise ValueError("Inactive or unknown user")
            current_role = self.users[username][1]
            if current_role != role:
                raise ValueError("Stale token role")
            return AuthenticatedUser(
                username=username,
                role=role,
                scope=str(claims.get("scope", "api")),
                user_id=claims.get("user_id"),
                owner_id=claims.get("owner_id"),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid or expired token") from exc


def audit(action: str, username: str | None = None, success: bool = True):
    LOGGER.info(
        "security_audit action=%s user=%s success=%s",
        action,
        username or "-",
        success,
    )
