import { useEffect, useState } from "react";
import {
    getSystemOverview,
    getCrowdHistory,
    getCameraZoneHistory,
    getCameraAlertHistory,
} from "./api";
import {
    CrowdHistoryChart,
    ZoneHistoryChart,
} from "./HistoryCharts";
import "./dashboard.css";
import { useNavigate, useParams } from "react-router-dom";
import { clearSession, getRole, getToken, getUsername } from "./auth";
import Icon from "./Icon";

const API_BASE_URL = "http://127.0.0.1:8000";

function App() {
    const [overview, setOverview] = useState(null);
    const [alerts, setAlerts] = useState([]);
    const [selectedCameraId, setSelectedCameraId] = useState(null);

    const [crowdHistory, setCrowdHistory] = useState([]);
    const [zoneHistories, setZoneHistories] = useState({});
    const [cameraAlertHistory, setCameraAlertHistory] = useState([]);

    const [historyLoading, setHistoryLoading] = useState(false);
    const [historyError, setHistoryError] = useState(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();
    const { cameraId: routeCameraId } = useParams();
    const [profileOpen, setProfileOpen] = useState(false);
    const [now, setNow] = useState(new Date());
    const [streamToken, setStreamToken] = useState("");

    useEffect(() => {
        let cancelled = false;

        fetch(`${API_BASE_URL}/auth/stream-token`, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${getToken() || ""}`,
            },
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Unable to authorize camera streams.");
                }
                return response.json();
            })
            .then((data) => {
                if (!cancelled) {
                    setStreamToken(data.access_token || "");
                }
            })
            .catch(() => {
                if (!cancelled) {
                    setStreamToken(getToken() || "");
                }
            });

        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        let isMounted = true;

        async function loadDashboardData() {
            try {
                const overviewData = await getSystemOverview();

                const cameras = overviewData.cameras || [];
                const liveAlerts = await loadAllLiveAlerts(cameras);

                /*
                 * The live overview may contain runtime zone results, while
                 * the zone-management API contains the saved zone definitions.
                 * Keep both sources together so the dashboard always displays
                 * every configured zone, even when a live result temporarily
                 * does not include its zone list.
                 */
                const zoneResponses = await Promise.all(
                    cameras.map(async (camera) => {
                        try {
                            const response = await fetch(
                                `${API_BASE_URL}/cameras/${camera.camera_id}/zones`
                            );

                            if (!response.ok) {
                                return {
                                    cameraId: camera.camera_id,
                                    zones: [],
                                };
                            }

                            const data = await response.json();

                            return {
                                cameraId: camera.camera_id,
                                zones: Array.isArray(data.zones)
                                    ? data.zones
                                    : [],
                            };
                        } catch {
                            return {
                                cameraId: camera.camera_id,
                                zones: [],
                            };
                        }
                    })
                );

                const configuredZoneMap = {};

                zoneResponses.forEach((item) => {
                    configuredZoneMap[item.cameraId] = item.zones;
                });

                const normalizedCameras = cameras.map((camera) => {
                    const runtimeZones = Array.isArray(camera.zones)
                        ? camera.zones
                        : [];

                    const configuredZones =
                        configuredZoneMap[camera.camera_id] || [];

                    const runtimeZoneMap = new Map(
                        runtimeZones.map((zone) => [
                            zone.zone_id,
                            zone,
                        ])
                    );

                    const mergedZones = configuredZones.map((zone) => {
                        const runtimeZone = runtimeZoneMap.get(
                            zone.zone_id
                        );

                        return {
                            ...zone,
                            name:
                                runtimeZone?.name ||
                                zone.zone_name ||
                                zone.name ||
                                zone.zone_id,
                            count:
                                runtimeZone?.count ??
                                zone.count ??
                                0,
                            threshold:
                                runtimeZone?.threshold ??
                                zone.threshold ??
                                0,
                            status:
                                runtimeZone?.status ||
                                zone.status ||
                                "GREEN",
                            enabled:
                                zone.enabled !== undefined
                                    ? zone.enabled
                                    : true,
                        };
                    });

                    /* Preserve any live zone result that is not yet present
                       in the saved configuration response. */
                    runtimeZones.forEach((runtimeZone) => {
                        if (
                            !mergedZones.some(
                                (zone) =>
                                    zone.zone_id ===
                                    runtimeZone.zone_id
                            )
                        ) {
                            mergedZones.push({
                                ...runtimeZone,
                                name:
                                    runtimeZone.name ||
                                    runtimeZone.zone_id,
                                count:
                                    runtimeZone.count ?? 0,
                                threshold:
                                    runtimeZone.threshold ?? 0,
                                status:
                                    runtimeZone.status ||
                                    "GREEN",
                            });
                        }
                    });

                    return {
                        ...camera,
                        zones: mergedZones,
                    };
                });

                const normalizedOverview = {
                    ...overviewData,
                    cameras: normalizedCameras,
                };

                if (isMounted) {
                    setOverview(normalizedOverview);
                    setAlerts(liveAlerts);
                    setError(null);
                    setLoading(false);
                }
            } catch (err) {
                if (isMounted) {
                    setError(err.message);
                    setLoading(false);
                }
            }
        }

        loadDashboardData();

        const intervalId = setInterval(
            loadDashboardData,
            2000
        );

        return () => {
            isMounted = false;
            clearInterval(intervalId);
        };
    }, []);

    useEffect(() => {
        const timer = setInterval(() => setNow(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    useEffect(() => {
        if (routeCameraId && overview?.cameras?.length) {
            const camera = overview.cameras.find(
                (item) => String(item.camera_id) === String(routeCameraId)
            );
            if (camera && selectedCameraId !== camera.camera_id) {
                setSelectedCameraId(camera.camera_id);
                loadCameraHistory(camera);
            }
        }
    }, [routeCameraId, overview]);

    async function loadCameraHistory(camera) {
        if (!camera) {
            return;
        }

        setHistoryLoading(true);
        setHistoryError(null);

        try {
            const crowdData = await getCrowdHistory(
                camera.camera_id,
                20
            );

            const cameraAlerts = (await loadAllLiveAlerts([camera]))
                .slice(0, 100);

            const zoneHistoryData = await getCameraZoneHistory(
                camera.camera_id,
                20
            );
            const zoneHistoryMap = Object.fromEntries(
                (zoneHistoryData.zones || []).map((zone) => [
                    zone.zone_id,
                    zone.history || [],
                ])
            );

            setCrowdHistory(
                crowdData.results || []
            );

            const databaseAlerts = await getCameraAlertHistory(
                camera.camera_id,
                100
            );

            setCameraAlertHistory(
                databaseAlerts.alerts || []
            );

            // Keep the focused camera's live alerts independent from the
            // dashboard-wide list so every zone for this camera is shown.
            setCameraAlertHistory((previous) =>
                previous.length > 0
                    ? previous
                    : cameraAlerts
            );

            setZoneHistories(
                zoneHistoryMap
            );
        } catch (err) {
            setHistoryError(err.message);
            setCrowdHistory([]);
            setCameraAlertHistory([]);
            setZoneHistories({});
        } finally {
            setHistoryLoading(false);
        }
    }

    function openCamera(cameraId) {
        setSelectedCameraId(cameraId);
        navigate(`/camera-focus/${encodeURIComponent(cameraId)}`);

        const camera =
            overview?.cameras?.find(
                (item) =>
                    item.camera_id ===
                    cameraId
            );

        loadCameraHistory(camera);
    }

    function closeCamera() {
        setSelectedCameraId(null);
        setCrowdHistory([]);
        setCameraAlertHistory([]);
        setZoneHistories({});
        setHistoryError(null);
        navigate("/");
    }

    function logout() {
        clearSession();
        navigate("/login", { replace: true });
    }

    function refreshDashboard() {
        window.location.reload();
    }

    function formatAlertTime(timestamp) {
        if (!timestamp) {
            return "-";
        }

        const date = new Date(timestamp);

        if (Number.isNaN(date.getTime())) {
            return timestamp;
        }

        return date.toLocaleTimeString();
    }

    function formatHistoryTime(timestamp) {
        if (!timestamp) {
            return "-";
        }

        const numericTimestamp = Number(timestamp);
        const date = Number.isFinite(numericTimestamp)
            ? new Date(
                numericTimestamp < 100000000000
                    ? numericTimestamp * 1000
                    : numericTimestamp
            )
            : new Date(timestamp);

        if (Number.isNaN(date.getTime())) {
            return timestamp;
        }

        return date.toLocaleTimeString();
    }

    function formatResultTime(timestamp) {
        if (!timestamp) {
            return "-";
        }

        const date = new Date(
            timestamp * 1000
        );

        if (Number.isNaN(date.getTime())) {
            return "-";
        }

        return date.toLocaleTimeString();
    }

    function streamUrl(cameraId) {
        const query = streamToken
            ? `?stream_token=${encodeURIComponent(streamToken)}`
            : "";
        return `${API_BASE_URL}/cameras/${cameraId}/stream${query}`;
    }

    async function loadAllLiveAlerts(cameras) {
        const responses = await Promise.all(
            cameras.map(async (camera) => {
                try {
                    const response = await fetch(
                        `${API_BASE_URL}/cameras/${camera.camera_id}/alerts`
                    );

                    if (!response.ok) {
                        return [];
                    }

                    const data = await response.json();
                    return Array.isArray(data.alerts)
                        ? data.alerts
                        : [];
                } catch {
                    return [];
                }
            })
        );

        const seen = new Set();
        return responses
            .flat()
            .filter((alert) => {
                const key =
                    alert.id ??
                    `${alert.camera_id}|${alert.zone_id}|${alert.timestamp}|${alert.alert_type}|${alert.count}`;

                if (seen.has(key)) {
                    return false;
                }

                seen.add(key);
                return true;
            })
            .sort(
                (a, b) =>
                    new Date(b.timestamp || 0).getTime() -
                    new Date(a.timestamp || 0).getTime()
            );
    }

    function formatAge(age) {
        if (
            age === null ||
            age === undefined
        ) {
            return "-";
        }

        if (age < 1) {
            return `${age.toFixed(2)}s`;
        }

        return `${age.toFixed(1)}s`;
    }

    function getAlertClass(alertType) {
        if (
            alertType ===
            "THRESHOLD_EXCEEDED"
        ) {
            return "alert-red";
        }

        if (
            alertType ===
            "THRESHOLD_REACHED"
        ) {
            return "alert-yellow";
        }

        if (
            alertType ===
                "THRESHOLD_RECOVERED" ||
            alertType ===
                "THRESHOLD_RECOVERING"
        ) {
            return "alert-green";
        }

        return "alert-neutral";
    }

    function getAlertTitle(alertType) {
        if (
            alertType ===
            "THRESHOLD_EXCEEDED"
        ) {
            return "Threshold Exceeded";
        }

        if (
            alertType ===
            "THRESHOLD_REACHED"
        ) {
            return "Threshold Reached";
        }

        if (
            alertType ===
            "THRESHOLD_RECOVERED"
        ) {
            return "Threshold Recovered";
        }

        if (
            alertType ===
            "THRESHOLD_RECOVERING"
        ) {
            return "Threshold Recovering";
        }

        return alertType;
    }

    function getHistoryStatusClass(status) {
        if (status === "GREEN") {
            return "history-status-green";
        }

        if (status === "YELLOW") {
            return "history-status-yellow";
        }

        if (status === "RED") {
            return "history-status-red";
        }

        return "";
    }

    function getSelectedCamera() {
        if (
            !selectedCameraId ||
            !overview
        ) {
            return null;
        }

        return (
            overview.cameras.find(
                (camera) =>
                    camera.camera_id ===
                    selectedCameraId
            ) || null
        );
    }

    function getCameraDisplayName(cameraId, alert = null) {
        if (alert?.camera_name) {
            return alert.camera_name;
        }

        const camera = overview?.cameras?.find(
            (item) =>
                String(item.camera_id).trim() ===
                String(cameraId).trim()
        );

        return (
            camera?.camera_name ||
            camera?.name ||
            cameraId
        );
    }

    const selectedCamera =
        getSelectedCamera();

    const selectedCameraAlerts =
        selectedCamera
            ? alerts
                  .filter(
                      (alert) =>
                          alert.camera_id ===
                          selectedCamera.camera_id
                  )
                  .reverse()
                  .slice(0, 10)
            : [];

    if (loading) {
        return (
            <div className="dashboard">
                <h1 className="dashboard-title">
                    Crowd Management Dashboard
                </h1>

                <p className="dashboard-subtitle">
                    Loading system data...
                </p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="dashboard">
                <h1 className="dashboard-title">
                    Crowd Management Dashboard
                </h1>

                <p className="dashboard-subtitle">
                    Error: {error}
                </p>
            </div>
        );
    }

    return (
        <div className={`operator-shell ${selectedCamera ? "is-focused" : ""}`}>
            <aside className="operator-sidebar">
                <div className="brand-lockup">
                    <div className="brand-shield"><Icon name="shield" size={22} /></div>
                    <div>
                        <strong>CROWD<br />MANAGEMENT</strong>
                        <span>SYSTEM</span>
                    </div>
                </div>
                <div className="brand-motto">SAFER SPACES<br /><b>BRIGHTER TOMORROW</b></div>
                <nav className="operator-nav" aria-label="Operator navigation">
                    <button className={!selectedCamera ? "active" : ""} onClick={() => navigate("/")}><Icon name="home" size={18} /> <span>Dashboard</span></button>
                    <button onClick={() => navigate("/configure-cameras")}><Icon name="camera" size={18} /> <span>Configure Cameras</span></button>
                    <button onClick={() => navigate("/profile")}><Icon name="user" size={18} /> <span>Profile</span></button>
                </nav>
                <div className="sidebar-footer">
                    <div className="skyline-art" aria-hidden="true">⌁⌁⌁⌁⌁</div>
                    <small>PEOPLE&nbsp; | &nbsp;SAFETY&nbsp; | &nbsp;SMARTER TOMORROW</small>
                    <button className="logout-button" onClick={logout}><Icon name="logout" size={18} /> <span>Logout</span></button>
                </div>
            </aside>
            <div className="operator-main">
                <header className="operator-header">
                    <div>
                        <p className="eyebrow">OPERATOR CONSOLE</p>
                        <h1>{selectedCamera ? "Camera Focus" : "Operator Dashboard"}</h1>
                        {!selectedCamera && <p className="operator-header-subtitle">Real-time crowd monitoring and camera status</p>}
                    </div>
                    <div className="header-tools">
                        <button className="notification-button" onClick={() => document.querySelector(".alerts-section")?.scrollIntoView({ behavior: "smooth" })} aria-label="View alerts">
                            <Icon name="bell" size={20} />{alerts.length > 0 && <span>{alerts.length}</span>}
                        </button>
                        <div className="operator-profile">
                            <button
                                className="profile-trigger"
                                onClick={() => setProfileOpen((value) => !value)}
                                aria-expanded={profileOpen}
                                aria-haspopup="menu"
                            >
                                <span className="avatar">{(getUsername() || "O").slice(0, 1).toUpperCase()}</span>
                                <span><b>{getUsername() || "Operator"}</b><small>Operator</small></span>
                                <Icon name="chevronDown" size={14} />
                            </button>
                            {profileOpen && <div className="profile-menu" role="menu">
                                <button className="profile-menu-button" onClick={() => { setProfileOpen(false); navigate("/profile"); }} role="menuitem">
                                    <Icon name="user" size={16} />
                                    <span>Profile</span>
                                </button>
                                <button className="profile-menu-button" onClick={logout} role="menuitem">
                                    <Icon name="logout" size={16} />
                                    <span>Logout</span>
                                </button>
                            </div>}
                        </div>
                        <div className="header-clock">
                            <span className="header-clock-line"><Icon name="calendar" size={13} /><b>{now.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}</b></span>
                            <span className="header-clock-line"><Icon name="clock" size={13} /><span>{now.toLocaleTimeString()}</span></span>
                        </div>
                    </div>
                </header>
                <div className="dashboard">
            <header className="dashboard-header">
                <h1 className="dashboard-title">
                    Crowd Management Dashboard
                </h1>

                <p className="dashboard-subtitle">
                    Real-time crowd monitoring and camera status
                </p>
            </header>

            <section className="overview-grid">
                <div className="overview-card">
                    <span className="overview-icon"><Icon name="camera" size={20} /></span>
                    <div className="overview-card-copy">
                        <p className="overview-label">Total Cameras</p>
                        <p className="overview-value">{overview.total_cameras}</p>
                        <span className="overview-support">Assigned to you</span>
                    </div>
                </div>

                <div className="overview-card">
                    <span className="overview-icon overview-icon-green"><Icon name="check" size={20} /></span>
                    <div className="overview-card-copy">
                        <p className="overview-label">Online Cameras</p>
                        <p className="overview-value">{overview.online_cameras}</p>
                        <span className="overview-support">{overview.online_cameras} cameras active</span>
                    </div>
                </div>

                <div className="overview-card">
                    <span className="overview-icon overview-icon-purple"><Icon name="users" size={20} /></span>
                    <div className="overview-card-copy">
                        <p className="overview-label">Total People</p>
                        <p className="overview-value">{overview.total_people}</p>
                        <span className="overview-support">Across your cameras</span>
                    </div>
                </div>

                <div className="overview-card">
                    <span className="overview-icon overview-icon-red"><Icon name="bell" size={20} /></span>
                    <div className="overview-card-copy">
                        <p className="overview-label">Total Alerts</p>
                        <p className="overview-value">{overview.total_alerts}</p>
                        <span className="overview-support">Today</span>
                    </div>
                </div>
            </section>

            {(getRole() === "ADMIN" || !sessionStorage.getItem("crowd_access_token")) && (
                <div className="dashboard-configure-actions">
                    <button
                        className="configure-cameras-button"
                        onClick={() =>
                            navigate("/configure-cameras")
                        }
                    >
                        <Icon name="settings" size={16} /> Configure Cameras
                    </button>
                </div>
            )}

            <section className="camera-section">
                <h2 className="camera-section-title">
                    Cameras
                </h2>

                <div className="camera-grid">
                    {overview.cameras.length === 0 ? (
                        <div className="camera-empty-state">
                            <Icon name="camera" size={28} />
                            <strong>No cameras assigned</strong>
                            <span>No cameras are currently assigned to this operator.</span>
                        </div>
                    ) : overview.cameras.map(
                        (camera) => (
                            <div
                                className="camera-card"
                                key={
                                    camera.camera_id
                                }
                            >
                                <div className="camera-card-header">
                                    <h3 className="camera-name">
                                        {
                                            camera.camera_name || camera.camera_id
                                        }
                                    </h3>

                                    <div className="camera-header-actions">
                                        <div
                                            className={`camera-status status-${camera.status.toLowerCase()}`}
                                        >
                                            <span className="status-dot"></span>
                                            {
                                                camera.status
                                            }
                                        </div>

                                        <button
                                            className="focus-button"
                                            onClick={() =>
                                                openCamera(
                                                    camera.camera_id
                                                )
                                            }
                                        >
                                            Focus
                                        </button>
                                    </div>
                                </div>

                                <div className="camera-video-container">
                                    {camera.status ===
                                    "ONLINE" ? (
                                        <img
                                            className="camera-video"
                                            src={streamUrl(camera.camera_id)}
                                            alt={`Live stream from ${camera.camera_id}`}
                                        />
                                    ) : (
                                        <div className="camera-video-unavailable">
                                            Camera unavailable
                                        </div>
                                    )}
                                </div>

                                <div className="camera-content">
                                    <p className="camera-count">
                                        Total People:{" "}
                                        {camera.total_people ??
                                            0}
                                    </p>

                                    <div className="camera-health">
                                        <div className="health-row">
                                            <span>
                                                Processing
                                            </span>

                                            <strong>
                                                {
                                                    camera.processing_status
                                                }
                                            </strong>
                                        </div>

                                        <div className="health-row">
                                            <span>
                                                Result
                                            </span>

                                            <strong
                                                className={
                                                    camera.fresh
                                                        ? "fresh-status"
                                                        : "stale-status"
                                                }
                                            >
                                                {camera.fresh
                                                    ? "FRESH"
                                                    : "STALE"}
                                            </strong>
                                        </div>

                                        <div className="health-row">
                                            <span>
                                                Result Age
                                            </span>

                                            <strong>
                                                {formatAge(
                                                    camera.age_seconds
                                                )}
                                            </strong>
                                        </div>

                                        <div className="health-row">
                                            <span>
                                                Last Result
                                            </span>

                                            <strong>
                                                {formatResultTime(
                                                    camera.result_timestamp
                                                )}
                                            </strong>
                                        </div>
                                    </div>

                                    {camera.last_error && (
                                        <div className="camera-error">
                                            <strong>
                                                Error:
                                            </strong>{" "}
                                            {
                                                camera.last_error
                                            }
                                        </div>
                                    )}

                                    <div className="zones-section">
                                        <h4 className="zones-title">
                                            Zone Monitoring
                                        </h4>

                                        {camera.zones
                                            .length ===
                                        0 ? (
                                            <p className="no-zones">
                                                No zones configured
                                            </p>
                                        ) : (
                                            <div className="zones-grid">
                                                {camera.zones.map(
                                                    (
                                                        zone
                                                    ) => (
                                                        <div
                                                            className={`zone-card zone-${zone.status.toLowerCase()}`}
                                                            key={
                                                                zone.zone_id
                                                            }
                                                        >
                                                            <div className="zone-header">
                                                                <div>
                                                                    <p className="zone-name">
                                                                        {
                                                                            zone.name
                                                                        }
                                                                    </p>

                                                                    <p className="zone-id">
                                                                        {
                                                                            zone.zone_id
                                                                        }
                                                                    </p>
                                                                </div>

                                                                <span className="zone-status">
                                                                    {
                                                                        zone.status
                                                                    }
                                                                </span>
                                                            </div>

                                                            <div className="zone-count">
                                                                {
                                                                    zone.count
                                                                }

                                                                <span>
                                                                    {" "}
                                                                    /{" "}
                                                                    {
                                                                        zone.threshold
                                                                    }
                                                                </span>
                                                            </div>

                                                            <p className="zone-threshold-label">
                                                                People / Threshold
                                                            </p>
                                                        </div>
                                                    )
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )
                    )}
                </div>
            </section>

            <aside className="operator-right-rail">
                <section className="alerts-section">
                    <div className="alerts-header">
                        <h2 className="camera-section-title">
                            All Alerts ({alerts.length})
                        </h2>

                        <span className="alerts-count">
                            All Cameras
                        </span>
                    </div>

                    {alerts.length === 0 ? (
                        <div className="empty-alerts">
                            No alerts recorded.
                        </div>
                    ) : (
                        <div className="alerts-list">
                            {[...alerts]
                                .reverse()
                                .slice(0, 20)
                                .map(
                                    (
                                        alert,
                                        index
                                    ) => (
                                        <div
                                            className={`alert-item ${getAlertClass(
                                                alert.alert_type
                                            )}`}
                                            key={`${alert.timestamp}-${index}`}
                                        >
                                            <div className="alert-main">
                                                <div className="alert-title-row">
                                                    <strong>
                                                        {getAlertTitle(
                                                            alert.alert_type
                                                        )}
                                                    </strong>

                                                    <span className="alert-time">
                                                        {formatAlertTime(
                                                            alert.timestamp
                                                        )}
                                                    </span>
                                                </div>

                                                <p className="alert-location">
                                                    {
                                                        getCameraDisplayName(
                                                            alert.camera_id,
                                                            alert
                                                        )
                                                    }
                                                    {" • "}
                                                    {
                                                        alert.zone_name
                                                    }
                                                </p>

                                                <p className="alert-transition">
                                                    {
                                                        alert.previous_status
                                                    }
                                                    {" → "}
                                                    {
                                                        alert.current_status
                                                    }
                                                </p>
                                            </div>

                                            <div className="alert-count">
                                                <strong>
                                                    {
                                                        alert.count
                                                    }
                                                </strong>

                                                <span>
                                                    /{" "}
                                                    {
                                                        alert.threshold
                                                    }
                                                </span>
                                            </div>
                                        </div>
                                    )
                                )}
                        </div>
                    )}
                </section>

                <section className="status-summary-section">
                    <div className="alerts-header">
                        <h2 className="camera-section-title">Camera Status Summary</h2>
                        <span className="summary-link">View All</span>
                    </div>
                    <div className="status-summary-table">
                        <div className="status-summary-row status-summary-heading">
                            <span>Camera</span><span>Status</span><span>People</span><span>Zones</span>
                        </div>
                        {overview.cameras.length === 0 ? (
                            <div className="summary-empty">No cameras assigned.</div>
                        ) : overview.cameras.map((camera) => (
                            <div className="status-summary-row" key={`summary-${camera.camera_id}`}>
                                <span>{camera.camera_name || camera.camera_id}</span>
                                <span className="summary-online">
                                    <i></i>{camera.status}
                                </span>
                                <span>{camera.total_people ?? 0}</span>
                                <span>{camera.zones?.length ?? 0}</span>
                            </div>
                        ))}
                    </div>
                </section>

                <section className="zone-summary-section">
                    <div className="alerts-header">
                        <h2 className="camera-section-title">Zone Status Overview</h2>
                    </div>
                    <div className="zone-summary-content">
                        {(() => {
                            const zones = overview.cameras.flatMap((camera) => camera.zones || []);
                            const counts = zones.reduce((result, zone) => {
                                const status = (zone.status || "UNKNOWN").toLowerCase();
                                result[status] = (result[status] || 0) + 1;
                                return result;
                            }, {});
                            return (
                                <>
                                    <div className="zone-summary-total"><strong>{zones.length}</strong><span>Total Zones</span></div>
                                    <div className="zone-summary-legend">
                                        <span><i className="zone-dot-red"></i>Red {counts.red || 0}</span>
                                        <span><i className="zone-dot-yellow"></i>Yellow {counts.yellow || 0}</span>
                                        <span><i className="zone-dot-green"></i>Green {counts.green || 0}</span>
                                    </div>
                                </>
                            );
                        })()}
                    </div>
                </section>
            </aside>

            {/* Existing Focus Modal - preserved */}
            {selectedCamera && (
                <div className="camera-modal-backdrop">
                    <div className="camera-modal">
                        <div className="camera-modal-header">
                            <div>
                                <h2>
                                    {
                                        selectedCamera.camera_id
                                    }
                                </h2>

                                <div
                                    className={`camera-status status-${selectedCamera.status.toLowerCase()}`}
                                >
                                    <span className="status-dot"></span>
                                    {
                                        selectedCamera.status
                                    }
                                </div>
                            </div>

                            <button
                                className="close-button"
                                onClick={
                                    closeCamera
                                }
                            >
                                ←
                            </button>
                        </div>

                        <div className="camera-modal-video">
                            {selectedCamera.status ===
                            "ONLINE" ? (
                                <img
                                    src={streamUrl(selectedCamera.camera_id)}
                                    alt={`Focused live stream from ${selectedCamera.camera_id}`}
                                />
                            ) : (
                                <div className="camera-video-unavailable">
                                    Camera unavailable
                                </div>
                            )}
                        </div>

                        <div className="camera-modal-content">
                            <div className="focused-summary">
                                <div>
                                    <span>
                                        Total People
                                    </span>

                                    <strong>
                                        {selectedCamera.total_people ??
                                            0}
                                    </strong>
                                </div>

                                <div>
                                    <span>
                                        Processing
                                    </span>

                                    <strong>
                                        {
                                            selectedCamera.processing_status
                                        }
                                    </strong>
                                </div>

                                <div>
                                    <span>
                                        Result
                                    </span>

                                    <strong
                                        className={
                                            selectedCamera.fresh
                                                ? "fresh-status"
                                                : "stale-status"
                                        }
                                    >
                                        {selectedCamera.fresh
                                            ? "FRESH"
                                            : "STALE"}
                                    </strong>
                                </div>

                                <div>
                                    <span>
                                        Result Age
                                    </span>

                                    <strong>
                                        {formatAge(
                                            selectedCamera.age_seconds
                                        )}
                                    </strong>
                                </div>
                            </div>

                            <div className="focused-zones">
                                <h3>
                                    Zone Monitoring
                                </h3>

                                <div className="zones-grid">
                                    {selectedCamera.zones.map(
                                        (zone) => (
                                            <div
                                                className={`zone-card zone-${zone.status.toLowerCase()}`}
                                                key={
                                                    zone.zone_id
                                                }
                                            >
                                                <div className="zone-header">
                                                    <div>
                                                        <p className="zone-name">
                                                            {
                                                                zone.name
                                                            }
                                                        </p>

                                                        <p className="zone-id">
                                                            {
                                                                zone.zone_id
                                                            }
                                                        </p>
                                                    </div>

                                                    <span className="zone-status">
                                                        {
                                                            zone.status
                                                        }
                                                    </span>
                                                </div>

                                                <div className="zone-count">
                                                    {
                                                        zone.count
                                                    }

                                                    <span>
                                                        {" "}
                                                        /{" "}
                                                        {
                                                            zone.threshold
                                                        }
                                                    </span>
                                                </div>

                                                <p className="zone-threshold-label">
                                                    People / Threshold
                                                </p>
                                            </div>
                                        )
                                    )}
                                </div>
                            </div>

                            <div className="focused-alerts">
                                <h3>
                                    Recent Camera Alerts
                                </h3>

                                {selectedCameraAlerts.length ===
                                0 ? (
                                    <p className="no-zones">
                                        No alerts for this camera.
                                    </p>
                                ) : (
                                    <div className="focused-alert-list">
                                        {selectedCameraAlerts.map(
                                            (
                                                alert,
                                                index
                                            ) => (
                                                <div
                                                    className={`focused-alert ${getAlertClass(
                                                        alert.alert_type
                                                    )}`}
                                                    key={`${alert.timestamp}-${index}`}
                                                >
                                                    <div>
                                                        <strong>
                                                            {getAlertTitle(
                                                                alert.alert_type
                                                            )}
                                                        </strong>

                                                        <span>
                                                            {
                                                                alert.zone_name
                                                            }{" "}
                                                            •{" "}
                                                            {
                                                                alert.zone_id
                                                            }
                                                        </span>
                                                    </div>

                                                    <div>
                                                        {
                                                            alert.count
                                                        }
                                                        /
                                                        {
                                                            alert.threshold
                                                        }
                                                    </div>
                                                </div>
                                            )
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* Historical Data remains INSIDE Focus modal */}
                            <div className="focused-history">
                                <div className="history-header">
                                    <h3>
                                        Camera &amp; Zone History
                                    </h3>

                                    <button
                                        className="focus-button"
                                        onClick={() =>
                                            loadCameraHistory(
                                                selectedCamera
                                            )
                                        }
                                        disabled={
                                            historyLoading
                                        }
                                    >
                                        {historyLoading
                                            ? "Loading..."
                                            : "Refresh History"}
                                    </button>
                                </div>

                                {historyError && (
                                    <div className="camera-error">
                                        <strong>
                                            History Error:
                                        </strong>{" "}
                                        {
                                            historyError
                                        }
                                    </div>
                                )}

                                {historyLoading ? (
                                    <div className="history-loading">
                                        Loading historical
                                        database records...
                                    </div>
                                ) : (
                                    <>
                                        <div className="history-charts">
                                            <CrowdHistoryChart
                                                history={
                                                    crowdHistory
                                                }
                                            />

                                            {selectedCamera.zones.map(
                                                (
                                                    zone
                                                ) => (
                                                    <ZoneHistoryChart
                                                        key={
                                                            zone.zone_id
                                                        }
                                                        zoneName={
                                                            zone.name
                                                        }
                                                        zoneId={
                                                            zone.zone_id
                                                        }
                                                        history={
                                                            zoneHistories[
                                                                zone
                                                                    .zone_id
                                                            ] ||
                                                            []
                                                        }
                                                    />
                                                )
                                            )}
                                        </div>

                                        <div className="history-block">
                                                    <h4>
                                                        Camera History · Total People by Time
                                            </h4>

                                            {crowdHistory.length ===
                                            0 ? (
                                                <p className="no-zones">
                                                    No crowd history
                                                    available.
                                                </p>
                                            ) : (
                                                <div className="history-table-wrapper">
                                                    <table className="history-table">
                                                        <thead>
                                                            <tr>
                                                                <th>
                                                                    Time
                                                                </th>

                                                                <th className="history-number">
                                                                    Total People
                                                                </th>
                                                            </tr>
                                                        </thead>

                                                        <tbody>
                                                            {crowdHistory.map(
                                                                (
                                                                    item
                                                                ) => (
                                                                    <tr
                                                                        key={
                                                                            item.id
                                                                        }
                                                                    >
                                                                        <td>
                                                                            {formatHistoryTime(
                                                                                item.result_timestamp
                                                                            )}
                                                                        </td>

                                                                        <td className="history-number">
                                                                            {item.total_people ?? 0}
                                                                        </td>
                                                                    </tr>
                                                                )
                                                            )}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            )}
                                        </div>

                                        <div className="history-block">
                                                    <h4>
                                                Zone History
                                            </h4>

                                            {selectedCamera.zones.map(
                                                (
                                                    zone
                                                ) => {
                                                    const results =
                                                        zoneHistories[
                                                            zone
                                                                .zone_id
                                                        ] ||
                                                        [];

                                                    return (
                                                        <div
                                                            className="history-zone-block"
                                                            key={
                                                                zone.zone_id
                                                            }
                                                        >
                                                            <div className="history-zone-header">
                                                                <strong>
                                                                    {
                                                                        zone.name ||
                                                                        zone.zone_id
                                                                    }
                                                                </strong>
                                                            </div>

                                                            {results.length ===
                                                            0 ? (
                                                                <p className="no-zones">
                                                                    No
                                                                    history
                                                                    available.
                                                                </p>
                                                            ) : (
                                                                <div className="history-table-wrapper">
                                                                    <table className="history-table">
                                                                        <thead>
                                                                            <tr>
                                                                                <th>
                                                                                    Time
                                                                                </th>

                                                                                <th className="history-number">
                                                                                    Count
                                                                                </th>

                                                                                <th className="history-number">
                                                                                    Threshold
                                                                                </th>

                                                                                <th className="history-status">
                                                                                    Status
                                                                                </th>
                                                                            </tr>
                                                                        </thead>

                                                                        <tbody>
                                                                            {results.map(
                                                                                (
                                                                                    item
                                                                                ) => (
                                                                                    <tr
                                                                                        key={
                                                                                            item.id
                                                                                        }
                                                                                    >
                                                                                        <td>
                                                                                            {formatHistoryTime(
                                                                                                item.result_timestamp
                                                                                            )}
                                                                                        </td>

                                                                                        <td className="history-number">
                                                                                            {
                                                                                                item.count
                                                                                            }
                                                                                        </td>

                                                                                        <td className="history-number">
                                                                                            {
                                                                                                item.threshold
                                                                                            }
                                                                                        </td>

                                                                                        <td
                                                                                            className={`history-status ${getHistoryStatusClass(
                                                                                                item.status
                                                                                            )}`}
                                                                                        >
                                                                                            {
                                                                                                item.status
                                                                                            }
                                                                                        </td>
                                                                                    </tr>
                                                                                )
                                                                            )}
                                                                        </tbody>
                                                                    </table>
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                }
                                            )}
                                        </div>

                                        <div className="history-block">
                                                    <h4>
                                                        Database Alert History
                                                    </h4>

                                            {cameraAlertHistory.length ===
                                            0 ? (
                                                <p className="no-zones">
                                                    No historical alerts
                                                    available.
                                                </p>
                                            ) : (
                                                <div className="focused-alert-list">
                                                    {cameraAlertHistory.map(
                                                        (
                                                            alert
                                                        ) => (
                                                            <div
                                                                className={`focused-alert ${getAlertClass(
                                                                    alert.alert_type
                                                                )}`}
                                                                key={
                                                                    alert.id
                                                                }
                                                            >
                                                                <div>
                                                                    <strong>
                                                                        {getAlertTitle(
                                                                            alert.alert_type
                                                                        )}
                                                                    </strong>

                                                                    <span>
                                                                        {
                                                                            alert.zone_name
                                                                        }{" "}
                                                                        •{" "}
                                                                        {
                                                                            alert.zone_id
                                                                        }{" "}
                                                                        •{" "}
                                                                        {formatHistoryTime(
                                                                            alert.alert_timestamp
                                                                        )}
                                                                    </span>
                                                                </div>

                                                                <div>
                                                                    {
                                                                        alert.count
                                                                    }
                                                                    /
                                                                    {
                                                                        alert.threshold
                                                                    }
                                                                </div>
                                                            </div>
                                                        )
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
                </div>
            </div>
    );
}

export default App;
