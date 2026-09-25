CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADMIN', 'OPERATOR')),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cameras (
    camera_id TEXT PRIMARY KEY,
    camera_name TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL,
    source TEXT NOT NULL,
    loop BOOLEAN NOT NULL DEFAULT TRUE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    owner_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS zones (
    zone_id TEXT NOT NULL,
    camera_id TEXT NOT NULL,
    zone_name TEXT NOT NULL,
    polygon TEXT NOT NULL,
    threshold INTEGER NOT NULL,
    point TEXT NOT NULL DEFAULT 'bottom_center',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (camera_id, zone_id),
    FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
);

CREATE TABLE IF NOT EXISTS crowd_results (
    id BIGSERIAL PRIMARY KEY,
    camera_id TEXT NOT NULL,
    total_people INTEGER,
    result_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
);

CREATE TABLE IF NOT EXISTS zone_results (
    id BIGSERIAL PRIMARY KEY,
    camera_id TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    zone_name TEXT NOT NULL,
    count INTEGER NOT NULL,
    threshold INTEGER NOT NULL,
    status TEXT NOT NULL,
    result_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    camera_id TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    zone_name TEXT NOT NULL,
    previous_status TEXT,
    current_status TEXT NOT NULL,
    count INTEGER NOT NULL,
    threshold INTEGER NOT NULL,
    alert_type TEXT NOT NULL,
    alert_timestamp TIMESTAMPTZ NOT NULL,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_timestamp TIMESTAMPTZ,
    FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
);

CREATE INDEX IF NOT EXISTS idx_crowd_results_camera
ON crowd_results(camera_id);
CREATE INDEX IF NOT EXISTS idx_crowd_results_camera_timestamp
ON crowd_results(camera_id, result_timestamp DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_crowd_results_timestamp
ON crowd_results(result_timestamp);
CREATE INDEX IF NOT EXISTS idx_zone_results_camera
ON zone_results(camera_id);
CREATE INDEX IF NOT EXISTS idx_zone_results_camera_zone_timestamp
ON zone_results(camera_id, zone_id, result_timestamp DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_zone_results_timestamp
ON zone_results(result_timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_camera
ON alerts(camera_id);
CREATE INDEX IF NOT EXISTS idx_alerts_camera_timestamp
ON alerts(camera_id, alert_timestamp DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_timestamp
ON alerts(alert_timestamp);
CREATE INDEX IF NOT EXISTS idx_zones_camera
ON zones(camera_id);
