# API security

Authentication is configuration-driven. Local development keeps authentication
disabled by default in `configs/app.yaml`; production should set
`security.enabled: true` and provide the environment variables below.

## Roles

- `ADMIN`: global access, camera/zone CRUD, operator management, and monitoring.
- `OPERATOR`: isolated access to the operator's cameras, zones, streams, alerts, and
  historical analytics.

Administrators can select an active operator in the existing Operator Management
screen. The dashboard sends the selected context using `X-Operator-Username`;
the API validates that context server-side before applying it. An operator's
own `X-Operator-Username` value is ignored for authorization and cannot change
their ownership scope.

Operator deletion is a safe deactivation operation. It preserves cameras,
zones, alerts, uploads, and historical records. At least one active `ADMIN`
must always remain, so the final administrator cannot be demoted, deactivated,
or deleted.

Public registration always creates an `OPERATOR`. The configured initial account
is always an administrator. Passwords are verified using PBKDF2-HMAC-SHA256
and are never stored or logged in plaintext.

## Environment variables

- `CROWD_SECURITY_ENABLED`: optional override for `security.enabled`.
- `CROWD_AUTH_SECRET`: at least 32 random characters used to sign tokens.
- `CROWD_ADMIN_USERNAME`: initial account name.
- `CROWD_ADMIN_PASSWORD`: initial password, or use
  `CROWD_ADMIN_PASSWORD_HASH` with a precomputed PBKDF2 hash.
- `CROWD_ADMIN_ROLE`: accepted for backwards-compatible configuration but the
  configured initial account is always `ADMIN`.
- `CROWD_USERS_JSON`: optional additional pre-hashed OPERATOR accounts.

`POST /auth/login` accepts `username` and `password` and returns a bearer
token. `POST /auth/stream-token` exchanges an authenticated API token for a
short-lived stream token. The dashboard uses this token for browser MJPEG
streams because an `<img>` element cannot attach an Authorization header.

Token expiration is configured by `security.token_expiry_minutes`; stream
tokens use `security.stream_token_expiry_seconds`. Authentication failures
return `401`, while authenticated users without the required role receive
`403`.

When authentication is disabled, the application is intentionally local/development
mode and administrative routes remain available for backward compatibility.
