const API_BASE_URL = "http://127.0.0.1:8000";

async function fetchJson(url, errorMessage) {
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(
            `${errorMessage}: ${response.status}`
        );
    }

    return response.json();
}

export async function getSystemOverview() {
    return fetchJson(
        `${API_BASE_URL}/system/overview`,
        "Failed to fetch system overview"
    );
}

export async function getAlerts() {
    return fetchJson(
        `${API_BASE_URL}/alerts`,
        "Failed to fetch alerts"
    );
}

// Historical database APIs

export async function getDatabaseCameras() {
    return fetchJson(
        `${API_BASE_URL}/database/cameras`,
        "Failed to fetch database cameras"
    );
}

export async function getDatabaseCamera(cameraId) {
    return fetchJson(
        `${API_BASE_URL}/database/cameras/${cameraId}`,
        "Failed to fetch database camera"
    );
}

export async function getCrowdHistory(cameraId, limit = 100) {
    return fetchJson(
        `${API_BASE_URL}/database/cameras/${cameraId}/crowd?limit=${limit}`,
        "Failed to fetch crowd history"
    );
}

export async function getZoneHistory(
    cameraId,
    zoneId,
    limit = 100
) {
    return fetchJson(
        `${API_BASE_URL}/database/cameras/${cameraId}/zones/${zoneId}?limit=${limit}`,
        "Failed to fetch zone history"
    );
}

export async function getCameraZoneHistory(
    cameraId,
    limit = 20
) {
    return fetchJson(
        `${API_BASE_URL}/database/cameras/${cameraId}/zone-history?limit=${limit}`,
        "Failed to fetch camera zone history"
    );
}

export async function getHistoricalAnalytics(
    cameraId,
    zoneId = null,
    startTimestamp = null,
    endTimestamp = null,
    limit = 100
) {
    const params = new URLSearchParams({
        limit: String(limit),
    });

    if (zoneId) {
        params.set("zone_id", zoneId);
    }

    if (startTimestamp) {
        params.set("start_timestamp", startTimestamp);
    }

    if (endTimestamp) {
        params.set("end_timestamp", endTimestamp);
    }

    return fetchJson(
        `${API_BASE_URL}/database/cameras/${cameraId}/history?${params}`,
        "Failed to fetch historical analytics"
    );
}

export async function getDatabaseAlerts(limit = 100) {
    return fetchJson(
        `${API_BASE_URL}/database/alerts?limit=${limit}`,
        "Failed to fetch database alerts"
    );
}

export async function getCameraAlertHistory(
    cameraId,
    limit = 100
) {
    return fetchJson(
        `${API_BASE_URL}/database/cameras/${cameraId}/alerts?limit=${limit}`,
        "Failed to fetch camera alert history"
    );
}

export async function getZoneAlertHistory(
    cameraId,
    zoneId,
    limit = 100
) {
    return fetchJson(
        `${API_BASE_URL}/database/cameras/${cameraId}/zones/${zoneId}/alerts?limit=${limit}`,
        "Failed to fetch zone alert history"
    );
}