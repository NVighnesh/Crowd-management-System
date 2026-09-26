import { useEffect, useRef, useState } from "react";
import { getToken } from "./auth";
import Icon from "./Icon";
import { API_BASE_URL } from "./apiBase";

const EMPTY_FORM = {
    zone_id: "",
    zone_name: "",
    threshold: 5,
    point: "bottom_center",
    enabled: true,
};

const ZONE_COLORS = [
    "#facc15",
    "#22c55e",
    "#38bdf8",
    "#a78bfa",
    "#fb7185",
    "#f97316",
];

const SELECTED_CAMERA_STORAGE_KEY =
    "configureCameras.selectedCameraId";
const ZONE_VIEW_STORAGE_KEY =
    "configureCameras.zoneView";

function authenticatedHeaders(contentType = false) {
    const token = getToken();
    const headers = {};

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    if (contentType) {
        headers["Content-Type"] = "application/json";
    }

    return headers;
}

function ZoneManagementTab({ onCameraManagement, initialCameraId = "" }) {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);

    const [cameras, setCameras] = useState([]);
    const [selectedCameraId, setSelectedCameraId] = useState(
        () =>
            initialCameraId ||
            window.localStorage.getItem(
                SELECTED_CAMERA_STORAGE_KEY
            ) ||
            ""
    );
    const [zones, setZones] = useState([]);

    const [search, setSearch] = useState("");
    const [activeView, setActiveView] = useState(
        () =>
            window.localStorage.getItem(
                ZONE_VIEW_STORAGE_KEY
            ) || "editor"
    );

    const [editingZoneId, setEditingZoneId] = useState(null);
    const [form, setForm] = useState({ ...EMPTY_FORM });
    const [points, setPoints] = useState([]);

    const [drawMode, setDrawMode] = useState(true);
    const [xValue, setXValue] = useState("");
    const [yValue, setYValue] = useState("");

    const [loading, setLoading] = useState(false);
    const [cameraLoading, setCameraLoading] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [isFullscreenFormOpen, setIsFullscreenFormOpen] =
        useState(false);
    const [message, setMessage] = useState(null);
    const [error, setError] = useState(null);
    const [streamToken, setStreamToken] = useState("");
    const [isResetZonesDialogOpen, setIsResetZonesDialogOpen] =
        useState(false);

    useEffect(() => {
        if (selectedCameraId) {
            window.localStorage.setItem(
                SELECTED_CAMERA_STORAGE_KEY,
                selectedCameraId
            );
        } else {
            window.localStorage.removeItem(
                SELECTED_CAMERA_STORAGE_KEY
            );
        }
    }, [selectedCameraId]);

    useEffect(() => {
        window.localStorage.setItem(
            ZONE_VIEW_STORAGE_KEY,
            activeView
        );
    }, [activeView]);

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

    function streamUrl(cameraId) {
        if (!streamToken || !cameraId) {
            return "";
        }

        return `${API_BASE_URL}/cameras/${encodeURIComponent(
            cameraId
        )}/stream?stream_token=${encodeURIComponent(streamToken)}`;
    }

    async function loadCameras() {
        setCameraLoading(true);
        setError(null);

        try {
            const [overviewResponse, camerasResponse] =
                await Promise.all([
                    fetch(`${API_BASE_URL}/system/overview`, {
                        headers: authenticatedHeaders(),
                        credentials: "include",
                    }),
                        fetch(`${API_BASE_URL}/cameras`, {
                            headers: authenticatedHeaders(),
                            credentials: "include",
                        }),
                    ]);

            const overviewData = await overviewResponse.json();
            const camerasData = await camerasResponse.json();

            if (!overviewResponse.ok) {
                throw new Error(
                    overviewData.detail ||
                        "Failed to load system overview."
                );
            }

            if (!camerasResponse.ok) {
                throw new Error(
                    camerasData.detail ||
                        "Failed to load cameras."
                );
            }

            const overviewCameras =
                overviewData.cameras || [];
            const configuredCameras =
                camerasData.cameras || [];

            const cameraList = overviewCameras.map(
                (overviewCamera) => {
                    const configuredCamera =
                        configuredCameras.find(
                            (camera) =>
                                camera.camera_id ===
                                overviewCamera.camera_id
                        );

                    return {
                        ...configuredCamera,
                        ...overviewCamera,
                        camera_id:
                            overviewCamera.camera_id,
                        source_type:
                            configuredCamera?.source_type ||
                            overviewCamera.source_type ||
                            "file",
                        source:
                            overviewCamera.source ||
                            configuredCamera?.source ||
                            "",
                        zones:
                            Array.isArray(
                                overviewCamera.zones
                            )
                                ? overviewCamera.zones
                                : [],
                    };
                }
            );

            setCameras(cameraList);

            if (cameraList.length === 0) {
                setSelectedCameraId("");
                return;
            }

            const preferredCameraId =
                initialCameraId || selectedCameraId;

            if (
                preferredCameraId &&
                cameraList.some(
                    (camera) =>
                        camera.camera_id ===
                        preferredCameraId
                )
            ) {
                setSelectedCameraId(preferredCameraId);
            } else if (
                !selectedCameraId ||
                !cameraList.some(
                    (camera) =>
                        camera.camera_id ===
                        selectedCameraId
                )
            ) {
                setSelectedCameraId(
                    cameraList[0].camera_id
                );
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setCameraLoading(false);
        }
    }

    async function loadZones(cameraId) {
        if (!cameraId) {
            setZones([]);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const response = await fetch(
                `${API_BASE_URL}/cameras/${encodeURIComponent(cameraId)}/zones`,
                {
                    headers: authenticatedHeaders(),
                    credentials: "include",
                }
            );
            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Failed to load camera zones."
                );
            }

            const databaseZones = Array.isArray(data.zones)
                ? data.zones
                : [];

            const camera = cameras.find(
                (item) =>
                    item.camera_id === cameraId
            );

            const runtimeZones = Array.isArray(
                camera?.zones
            )
                ? camera.zones
                : [];

            const mergedZones = databaseZones.map((zone) => {
                const runtimeZone = runtimeZones.find(
                    (item) => item.zone_id === zone.zone_id
                );

                return {
                    ...zone,
                    count: runtimeZone?.count ?? zone.count ?? 0,
                    status:
                        runtimeZone?.status ||
                        zone.status ||
                        "GREEN",
                };
            });

            setZones(mergedZones);
            setCameras((previous) =>
                previous.map((camera) =>
                    camera.camera_id === cameraId
                        ? {
                              ...camera,
                              zones: mergedZones,
                              zone_count: mergedZones.length,
                          }
                        : camera
                )
            );
        } catch (err) {
            setZones([]);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadCameras();
    }, []);

    useEffect(() => {
        if (selectedCameraId) {
            loadZones(selectedCameraId);
        } else {
            setZones([]);
        }

        resetEditor();
    }, [selectedCameraId]);

    const selectedCamera =
        cameras.find(
            (camera) =>
                camera.camera_id === selectedCameraId
        ) || null;

    const filteredCameras = cameras.filter((camera) => {
        const query = search.trim().toLowerCase();

        if (!query) {
            return true;
        }

        return `${camera.camera_id} ${
            camera.camera_name || ""
        }`
            .toLowerCase()
            .includes(query);
    });

    function createNextZoneId(zoneList = zones) {
        const numbers = zoneList
            .map((zone) => {
                const match = String(
                    zone.zone_id || ""
                ).match(/(\d+)$/);

                return match ? Number(match[1]) : 0;
            })
            .filter(Number.isFinite);

        const next =
            numbers.length > 0
                ? Math.max(...numbers) + 1
                : 1;

        return `ZONE_${String(next).padStart(3, "0")}`;
    }

    function resetEditor() {
        setEditingZoneId(null);
        setForm({ ...EMPTY_FORM });
        setPoints([]);
        setXValue("");
        setYValue("");
        setDrawMode(true);
        setMessage(null);
    }

    function openAddZone() {
        setEditingZoneId(null);
        setForm({
            ...EMPTY_FORM,
            zone_id: createNextZoneId(),
        });
        setPoints([]);
        setXValue("");
        setYValue("");
        setDrawMode(true);
        setMessage(null);
        setError(null);
        setActiveView("editor");
    }

    function openEditZone(zone) {
        setEditingZoneId(zone.zone_id);

        setForm({
            zone_id: zone.zone_id || "",
            zone_name:
                zone.zone_name ||
                zone.name ||
                "",
            threshold: zone.threshold ?? 5,
            point:
                zone.point ||
                "bottom_center",
            enabled:
                zone.enabled !== undefined
                    ? Boolean(zone.enabled)
                    : true,
        });

        setPoints(
            Array.isArray(zone.polygon)
                ? zone.polygon.map((point) => [
                      Number(point[0]),
                      Number(point[1]),
                  ])
                : []
        );

        setXValue("");
        setYValue("");
        setDrawMode(true);
        setMessage(null);
        setError(null);
        setActiveView("editor");
    }

    function handleFormChange(event) {
        const {
            name,
            value,
            type,
            checked,
        } = event.target;

        setForm((previous) => ({
            ...previous,
            [name]:
                type === "checkbox"
                    ? checked
                    : value,
        }));
    }

    function addCoordinatePoint() {
        if (xValue === "" || yValue === "") {
            setError("Enter both X and Y values.");
            return;
        }

        const x = Number(xValue);
        const y = Number(yValue);

        if (
            !Number.isFinite(x) ||
            !Number.isFinite(y) ||
            x < 0 ||
            y < 0
        ) {
            setError(
                "X and Y must be valid non-negative numbers."
            );
            return;
        }

        setPoints((previous) => [
            ...previous,
            [Math.round(x), Math.round(y)],
        ]);

        setXValue("");
        setYValue("");
        setError(null);
    }

    function removePoint(index) {
        setPoints((previous) =>
            previous.filter(
                (_, pointIndex) =>
                    pointIndex !== index
            )
        );
    }

    function clearPoints() {
        setPoints([]);
        setError(null);
    }

    function requestResetAllZones() {
        if (!selectedCameraId || zones.length === 0) {
            setPoints([]);
            setError(null);
            return;
        }

        setIsResetZonesDialogOpen(true);
    }

    async function resetAllZones() {
        setIsResetZonesDialogOpen(false);
        setLoading(true);
        setMessage(null);
        setError(null);

        try {
            const response = await fetch(
                `${API_BASE_URL}/cameras/${encodeURIComponent(
                    selectedCameraId
                )}/zones`,
                {
                    method: "DELETE",
                    headers: authenticatedHeaders(),
                    credentials: "include",
                }
            );
            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Failed to reset zones."
                );
            }

            await loadZones(selectedCameraId);
            setPoints([]);
            setEditingZoneId(null);
            setForm({
                ...EMPTY_FORM,
                zone_id: createNextZoneId([]),
            });
            setXValue("");
            setYValue("");
            setDrawMode(true);
            setMessage("All zones reset successfully.");
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    function syncCanvasSize() {
        const canvas = canvasRef.current;
        const video = videoRef.current;

        if (!canvas || !video) {
            return;
        }

        const width =
            video.naturalWidth ||
            video.videoWidth ||
            video.clientWidth;

        const height =
            video.naturalHeight ||
            video.videoHeight ||
            video.clientHeight;

        if (!width || !height) {
            return;
        }

        canvas.width = width;
        canvas.height = height;
    }

    function getCanvasCoordinates(event) {
        const canvas = canvasRef.current;

        if (!canvas) {
            return null;
        }

        const rect =
            canvas.getBoundingClientRect();

        const scaleX =
            canvas.width / rect.width;
        const scaleY =
            canvas.height / rect.height;

        return [
            Math.round(
                (event.clientX - rect.left) *
                    scaleX
            ),
            Math.round(
                (event.clientY - rect.top) *
                    scaleY
            ),
        ];
    }

    function handleCanvasClick(event) {
        if (!drawMode) {
            return;
        }

        const coordinate =
            getCanvasCoordinates(event);

        if (!coordinate) {
            return;
        }

        setPoints((previous) => [
            ...previous,
            coordinate,
        ]);

        setError(null);
    }

    useEffect(() => {
        const canvas = canvasRef.current;

        if (!canvas) {
            return;
        }

        const context =
            canvas.getContext("2d");

        if (!context) {
            return;
        }

        context.clearRect(
            0,
            0,
            canvas.width,
            canvas.height
        );

        zones.forEach((zone, zoneIndex) => {
            const polygon = Array.isArray(
                zone.polygon
            )
                ? zone.polygon
                : [];

            if (polygon.length < 3) {
                return;
            }

            const color =
                ZONE_COLORS[
                    zoneIndex %
                        ZONE_COLORS.length
                ];

            context.beginPath();

            polygon.forEach(
                ([x, y], index) => {
                    if (index === 0) {
                        context.moveTo(x, y);
                    } else {
                        context.lineTo(x, y);
                    }
                }
            );

            context.closePath();

            context.fillStyle =
                `${color}24`;
            context.fill();

            context.strokeStyle = color;
            context.lineWidth = 3;
            context.stroke();

            const first = polygon[0];

            if (first) {
                context.fillStyle = color;
                context.font =
                    "700 13px Arial";
                context.fillText(
                    zone.zone_id ||
                        `ZONE_${zoneIndex + 1}`,
                    first[0] + 8,
                    first[1] - 8
                );
            }
        });

        if (points.length > 0) {
            context.beginPath();

            points.forEach(
                ([x, y], index) => {
                    if (index === 0) {
                        context.moveTo(x, y);
                    } else {
                        context.lineTo(x, y);
                    }
                }
            );

            if (points.length >= 3) {
                context.closePath();
                context.fillStyle =
                    "rgba(37, 99, 235, 0.16)";
                context.fill();
            }

            context.strokeStyle =
                "#2563eb";
            context.lineWidth = 3;
            context.stroke();

            points.forEach(
                ([x, y], index) => {
                    context.beginPath();
                    context.arc(
                        x,
                        y,
                        6,
                        0,
                        Math.PI * 2
                    );

                    context.fillStyle =
                        "#ffffff";
                    context.fill();

                    context.strokeStyle =
                        "#2563eb";
                    context.lineWidth = 2;
                    context.stroke();

                    context.fillStyle =
                        "#1d4ed8";
                    context.font =
                        "700 12px Arial";
                    context.fillText(
                        String(index + 1),
                        x + 9,
                        y - 9
                    );
                }
            );
        }
    }, [points, zones]);

    async function handleSubmit(
        event,
        { closeAfterSave = false } = {}
    ) {
        event.preventDefault();

        if (!selectedCameraId) {
            setError("Select a camera first.");
            return;
        }

        if (points.length < 3) {
            setError(
                "A zone must contain at least 3 points."
            );
            return;
        }

        const threshold =
            Number(form.threshold);

        if (
            !Number.isInteger(threshold) ||
            threshold < 0
        ) {
            setError(
                "Threshold must be a valid whole number."
            );
            return;
        }

        if (!form.zone_id.trim()) {
            setError("Zone ID is required.");
            return;
        }

        if (!form.zone_name.trim()) {
            setError("Zone name is required.");
            return;
        }

        setLoading(true);
        setMessage(null);
        setError(null);

        try {
            const isEditing =
                editingZoneId !== null;

            const url = isEditing
                ? `${API_BASE_URL}/cameras/${selectedCameraId}/zones/${editingZoneId}`
                : `${API_BASE_URL}/cameras/${selectedCameraId}/zones`;

            const method = isEditing
                ? "PUT"
                : "POST";

            const payload = {
                zone_id:
                    form.zone_id.trim(),
                zone_name:
                    form.zone_name.trim(),
                polygon: points,
                threshold,
                point: form.point,
                enabled: form.enabled,
            };

            const response = await fetch(url, {
                method,
                headers: authenticatedHeaders(true),
                credentials: "include",
                body: JSON.stringify(payload),
            });

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Failed to save zone."
                );
            }

            const savedZone = {
                ...payload,
                polygon: payload.polygon.map(
                    ([x, y]) => [x, y]
                ),
            };

            await loadZones(selectedCameraId);

            setMessage(
                isEditing
                    ? "Zone updated successfully."
                    : "Zone added successfully."
            );

            if (isFullscreen) {
                setIsFullscreenFormOpen(false);
                setEditingZoneId(null);
                setForm({
                    ...EMPTY_FORM,
                    zone_id: createNextZoneId([
                        ...zones,
                        savedZone,
                    ]),
                });
                setPoints([]);
                setXValue("");
                setYValue("");
                setDrawMode(true);

                if (closeAfterSave) {
                    setIsFullscreen(false);
                }
            } else {
                resetEditor();
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    async function handleDeleteZone(zoneId) {
        if (
            !window.confirm(
                `Delete zone ${zoneId}?`
            )
        ) {
            return;
        }

        setLoading(true);
        setMessage(null);
        setError(null);

        try {
            const response = await fetch(
                `${API_BASE_URL}/cameras/${encodeURIComponent(selectedCameraId)}/zones/${encodeURIComponent(zoneId)}`,
                {
                    method: "DELETE",
                    headers: authenticatedHeaders(),
                    credentials: "include",
                }
            );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                        "Failed to delete zone."
                );
            }

            await loadZones(selectedCameraId);

            if (editingZoneId === zoneId) {
                resetEditor();
            }

            setMessage(
                "Zone deleted successfully."
            );
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    function openFullscreenDraw() {
        setForm((previous) => ({
            ...previous,
            zone_id:
                previous.zone_id.trim() ||
                createNextZoneId(),
            zone_name:
                previous.zone_name.trim() ||
                `${selectedCamera?.camera_name || selectedCameraId} Zone`,
        }));
        setDrawMode(true);
        setIsFullscreen(true);
        setIsFullscreenFormOpen(false);
        setError(null);
    }

    function closeFullscreenDraw() {
        if (points.length > 0) {
            const shouldClose = window.confirm(
                "This polygon has not been saved. Close the drawing editor and discard it?"
            );

            if (!shouldClose) {
                return;
            }
        }

        setIsFullscreen(false);
        setIsFullscreenFormOpen(false);
    }

    function finishFullscreenDraw() {
        if (points.length >= 3) {
            handleSubmit(
                { preventDefault() {} },
                { closeAfterSave: true }
            );
            return;
        }

        if (points.length > 0) {
            const shouldClose = window.confirm(
                "This polygon has fewer than 3 points and cannot be saved. Close the drawing editor and discard it?"
            );

            if (!shouldClose) {
                return;
            }
        }

        setIsFullscreen(false);
        setIsFullscreenFormOpen(false);
    }

    function openFullscreenSaveForm() {
        if (points.length < 3) {
            setError("A zone must contain at least 3 points.");
            return;
        }

        setError(null);
        setIsFullscreenFormOpen(true);
    }

    useEffect(() => {
        if (!isFullscreen) {
            return undefined;
        }

        const handleKeyDown = (event) => {
            if (event.key === "Escape") {
                closeFullscreenDraw();
            }
        };

        window.addEventListener("keydown", handleKeyDown);

        const timer = window.setTimeout(() => {
            syncCanvasSize();
        }, 80);

        return () => {
            window.removeEventListener("keydown", handleKeyDown);
            window.clearTimeout(timer);
        };
    }, [isFullscreen]);

    return (
        <>
        <section className="zone-management-tab">
            <div className="zone-management-heading-row">
                <div>
                    <h2 className="zone-management-title">
                        Zone Management
                    </h2>

                    <p className="zone-management-subtitle">
                        Define and manage monitoring
                        zones for each camera.
                    </p>
                </div>

                <button
                    type="button"
                    className="zone-management-camera-button"
                    onClick={onCameraManagement}
                >
                    + Manage Cameras
                </button>
            </div>

            {message && (
                <div className="zone-management-message success">
                    {message}
                </div>
            )}

            {error && (
                <div className="zone-management-message error">
                    {error}
                </div>
            )}

            {cameraLoading ? (
                <div className="zone-management-loading">
                    Loading cameras...
                </div>
            ) : cameras.length === 0 ? (
                <div className="zone-management-empty">
                    <strong>No cameras configured</strong>
                    <span>
                        Add a camera from Camera
                        Management to create
                        monitoring zones.
                    </span>
                </div>
            ) : (
                <div className="zone-management-workspace">
                    <aside className="zone-camera-sidebar">
                        <div className="zone-sidebar-header">
                            <div>
                                <h3>Select Camera</h3>
                                <p>
                                    Choose a camera
                                    to manage its
                                    zones
                                </p>
                            </div>
                        </div>

                        <div className="zone-camera-search">
                            <span>⌕</span>
                            <input
                                value={search}
                                onChange={(event) =>
                                    setSearch(
                                        event.target
                                            .value
                                    )
                                }
                                placeholder="Search cameras..."
                            />
                        </div>

                        <div className="zone-camera-list">
                            {filteredCameras.map(
                                (camera) => {
                                    const selected =
                                        camera.camera_id ===
                                        selectedCameraId;

                                    return (
                                        <button
                                            type="button"
                                            className={`zone-camera-card ${
                                                selected
                                                    ? "active"
                                                    : ""
                                            }`}
                                            key={
                                                camera.camera_id
                                            }
                                            onClick={() =>
                                                setSelectedCameraId(
                                                    camera.camera_id
                                                )
                                            }
                                        >
                                            {streamToken ? (
                                                <img
                                                    src={streamUrl(camera.camera_id)}
                                                    alt={`Preview of ${camera.camera_name || camera.camera_id}`}
                                                />
                                            ) : (
                                                <span className="zone-camera-thumbnail-placeholder">
                                                    <Icon name="camera" size={24} />
                                                </span>
                                            )}

                                            <div className="zone-camera-card-content">
                                                <div className="zone-camera-name-row">
                                                    <strong>
                                                        {
                                                            camera.camera_name ||
                                                            camera.camera_id
                                                        }
                                                    </strong>

                                                    <span
                                                        className={
                                                            camera.enabled
                                                                ? "zone-online-badge"
                                                                : "zone-disabled-badge"
                                                        }
                                                    >
                                                        {camera.enabled
                                                            ? "Enabled"
                                                            : "Disabled"}
                                                    </span>
                                                </div>

                                                <div className="zone-camera-meta">
                                                    <span>
                                                        ▣{" "}
                                                        {camera.source_type ===
                                                        "rtsp"
                                                            ? "RTSP"
                                                            : "VIDEO"}
                                                    </span>

                                                    <span>
                                                        ◇{" "}
                                                        {Array.isArray(camera.zones)
                                                            ? camera.zones.length
                                                            : camera.camera_id === selectedCameraId
                                                            ? zones.length
                                                            : 0}{" "}
                                                        Zones
                                                    </span>
                                                </div>
                                            </div>
                                        </button>
                                    );
                                }
                            )}
                        </div>
                    </aside>

                    <main className="zone-editor-main">
                        {selectedCamera && (
                            <>
                                <div className="zone-selected-camera-header">
                                    <div>
                                        <div className="zone-selected-title-row">
                                            <h3>
                                                {selectedCamera.camera_name ||
                                                    selectedCamera.camera_id}
                                            </h3>

                                            <span className="zone-online-badge">
                                                ● Enabled
                                            </span>
                                        </div>

                                        <p>
                                            ▣{" "}
                                            {selectedCamera.source_type ===
                                            "rtsp"
                                                ? "RTSP"
                                                : "VIDEO"}{" "}
                                            <span>
                                                {
                                                    selectedCamera.source
                                                }
                                            </span>
                                        </p>
                                    </div>

                                    <div className="zone-selected-actions">
                                        <button
                                            type="button"
                                            onClick={
                                                onCameraManagement
                                            }
                                        >
                                            ✎ Edit Camera
                                        </button>

                                        <button
                                            type="button"
                                            className="danger"
                                            onClick={
                                                onCameraManagement
                                            }
                                        >
                                            ▣ Delete Camera
                                        </button>
                                    </div>
                                </div>

                                <div className="zone-editor-tabs">
                                    <button
                                        type="button"
                                        className={
                                            activeView ===
                                            "editor"
                                                ? "active"
                                                : ""
                                        }
                                        onClick={() =>
                                            setActiveView(
                                                "editor"
                                            )
                                        }
                                    >
                                        ✎
                                        <span>
                                            <strong>
                                                Zone Editor
                                            </strong>
                                            <small>
                                                Create and
                                                edit zones
                                            </small>
                                        </span>
                                    </button>

                                    <button
                                        type="button"
                                        className={
                                            activeView ===
                                            "list"
                                                ? "active"
                                                : ""
                                        }
                                        onClick={() =>
                                            setActiveView(
                                                "list"
                                            )
                                        }
                                    >
                                        ☷
                                        <span>
                                            <strong>
                                                Zone List
                                            </strong>
                                            <small>
                                                View and
                                                manage
                                                zones
                                            </small>
                                        </span>

                                        <b>
                                            {
                                                zones.length
                                            }
                                        </b>
                                    </button>
                                </div>

                                {activeView ===
                                    "editor" && (
                                    <div className="zone-editor-layout">
                                        <div className="zone-video-panel">
                                            <div className="zone-panel-header">
                                                <div>
                                                    <h3>
                                                        Camera
                                                        View
                                                    </h3>
                                                    <span>
                                                        Draw
                                                        zones
                                                        directly
                                                        on the
                                                        video
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="zone-video-wrapper">
                                                {streamToken && <img
                                                    ref={
                                                        videoRef
                                                    }
                                                    className="zone-editor-video"
                                                    src={streamUrl(selectedCamera.camera_id)}
                                                    alt={`Zone editor for ${selectedCamera.camera_id}`}
                                                    onLoad={
                                                        syncCanvasSize
                                                    }
                                                />}

                                                <canvas
                                                    ref={
                                                        canvasRef
                                                    }
                                                    className={`zone-drawing-canvas ${
                                                        drawMode
                                                            ? "drawing-active"
                                                            : ""
                                                    }`}
                                                    onClick={
                                                        handleCanvasClick
                                                    }
                                                />
                                            </div>

                                            <div className="zone-drawing-controls">
                                                <button
                                                    type="button"
                                                    className={
                                                        drawMode
                                                            ? "zone-tool-button active"
                                                            : "zone-tool-button"
                                                    }
                                                    onClick={
                                                        openFullscreenDraw
                                                    }
                                                >
                                                    ↖ Draw
                                                </button>

                                                <button
                                                    type="button"
                                                    className="zone-tool-button"
                                                    onClick={() =>
                                                        setDrawMode(
                                                            false
                                                        )
                                                    }
                                                >
                                                    ✋ Select
                                                </button>

                                                <button
                                                    type="button"
                                                    className="zone-tool-button secondary"
                                                    onClick={
                                                        clearPoints
                                                    }
                                                    disabled={
                                                        points.length ===
                                                        0
                                                    }
                                                >
                                                    ▣ Clear
                                                </button>

                                                <button
                                                    type="button"
                                                    className="zone-tool-button secondary"
                                                    onClick={
                                                        requestResetAllZones
                                                    }
                                                >
                                                    ↶ Reset All Zones
                                                </button>
                                            </div>
                                        </div>

                                        <div className="zone-editor-form-panel">
                                            <div className="zone-panel-header">
                                                <div>
                                                    <h3>
                                                        {editingZoneId
                                                            ? "Edit Zone"
                                                            : "Create / Edit Zone"}
                                                    </h3>

                                                    <span>
                                                        Configure zone
                                                        details and
                                                        crowd
                                                        threshold.
                                                    </span>
                                                </div>
                                            </div>

                                            <form
                                                onSubmit={
                                                    handleSubmit
                                                }
                                                className="zone-editor-form"
                                            >
                                                <div className="zone-form-row">
                                                    <label>
                                                        <span>
                                                            Zone ID
                                                        </span>

                                                        <input
                                                            name="zone_id"
                                                            value={
                                                                form.zone_id
                                                            }
                                                            onChange={
                                                                handleFormChange
                                                            }
                                                            disabled={
                                                                editingZoneId !==
                                                                null
                                                            }
                                                            placeholder="ZONE_003"
                                                            required
                                                        />
                                                    </label>

                                                    <label>
                                                        <span>
                                                            Zone Name
                                                        </span>

                                                        <input
                                                            name="zone_name"
                                                            value={
                                                                form.zone_name
                                                            }
                                                            onChange={
                                                                handleFormChange
                                                            }
                                                            placeholder="Main Gate Zone"
                                                            required
                                                        />
                                                    </label>
                                                </div>

                                                <div className="zone-form-row">
                                                    <label>
                                                        <span>
                                                            Threshold
                                                        </span>

                                                        <input
                                                            type="number"
                                                            name="threshold"
                                                            min="0"
                                                            value={
                                                                form.threshold
                                                            }
                                                            onChange={
                                                                handleFormChange
                                                            }
                                                            required
                                                        />
                                                    </label>

                                                    <label>
                                                        <span>
                                                            Counting
                                                            Point
                                                        </span>

                                                        <select
                                                            name="point"
                                                            value={
                                                                form.point
                                                            }
                                                            onChange={
                                                                handleFormChange
                                                            }
                                                        >
                                                            <option value="bottom_center">
                                                                Bottom Center
                                                            </option>
                                                            <option value="center">
                                                                Center
                                                            </option>
                                                        </select>
                                                    </label>
                                                </div>

                                                <div className="zone-entry-tabs">
                                                    <button
                                                        type="button"
                                                        className={
                                                            drawMode
                                                                ? "active"
                                                                : ""
                                                        }
                                                        onClick={
                                                            openFullscreenDraw
                                                        }
                                                    >
                                                        Draw on
                                                        Video
                                                    </button>

                                                    <button
                                                        type="button"
                                                        className={
                                                            !drawMode
                                                                ? "active"
                                                                : ""
                                                        }
                                                        onClick={() =>
                                                            setDrawMode(
                                                                false
                                                            )
                                                        }
                                                    >
                                                        Enter
                                                        Coordinates
                                                    </button>
                                                </div>

                                                {!drawMode && (
                                                    <div className="zone-coordinate-editor">
                                                        <div className="zone-coordinate-header">
                                                            <strong>
                                                                Add
                                                                Points
                                                                Manually
                                                            </strong>

                                                            <span>
                                                                Point{" "}
                                                                {points.length +
                                                                    1}
                                                            </span>
                                                        </div>

                                                        <div className="zone-coordinate-inputs">
                                                            <label>
                                                                <span>
                                                                    X
                                                                </span>

                                                                <input
                                                                    type="number"
                                                                    value={
                                                                        xValue
                                                                    }
                                                                    onChange={(
                                                                        event
                                                                    ) =>
                                                                        setXValue(
                                                                            event
                                                                                .target
                                                                                .value
                                                                        )
                                                                    }
                                                                    placeholder="e.g. 100"
                                                                />
                                                            </label>

                                                            <label>
                                                                <span>
                                                                    Y
                                                                </span>

                                                                <input
                                                                    type="number"
                                                                    value={
                                                                        yValue
                                                                    }
                                                                    onChange={(
                                                                        event
                                                                    ) =>
                                                                        setYValue(
                                                                            event
                                                                                .target
                                                                                .value
                                                                        )
                                                                    }
                                                                    placeholder="e.g. 200"
                                                                />
                                                            </label>

                                                            <button
                                                                type="button"
                                                                className="zone-add-point-button"
                                                                onClick={
                                                                    addCoordinatePoint
                                                                }
                                                            >
                                                                + Add Point
                                                            </button>
                                                        </div>
                                                    </div>
                                                )}

                                                <div className="zone-points-section">
                                                    <div className="zone-points-header">
                                                        <strong>
                                                            Points List
                                                        </strong>

                                                        <span>
                                                            (
                                                            {
                                                                points.length
                                                            }{" "}
                                                            points
                                                            )
                                                        </span>
                                                    </div>

                                                    {points.length ===
                                                    0 ? (
                                                        <div className="zone-no-points">
                                                            No points
                                                            added
                                                            yet.
                                                        </div>
                                                    ) : (
                                                        <div className="zone-points-list">
                                                            {points.map(
                                                                (
                                                                    point,
                                                                    index
                                                                ) => (
                                                                    <div
                                                                        className="zone-point-row"
                                                                        key={`${point[0]}-${point[1]}-${index}`}
                                                                    >
                                                                        <span className="zone-point-number">
                                                                            {
                                                                                index +
                                                                                1
                                                                            }
                                                                        </span>

                                                                        <span>
                                                                            X:{" "}
                                                                            <strong>
                                                                                {
                                                                                    point[0]
                                                                                }
                                                                            </strong>
                                                                        </span>

                                                                        <span>
                                                                            Y:{" "}
                                                                            <strong>
                                                                                {
                                                                                    point[1]
                                                                                }
                                                                            </strong>
                                                                        </span>

                                                                        <button
                                                                            type="button"
                                                                            onClick={() =>
                                                                                removePoint(
                                                                                    index
                                                                                )
                                                                            }
                                                                        >
                                                                            ×
                                                                        </button>
                                                                    </div>
                                                                )
                                                            )}
                                                        </div>
                                                    )}
                                                </div>

                                                <label className="zone-enabled-checkbox">
                                                    <input
                                                        type="checkbox"
                                                        name="enabled"
                                                        checked={
                                                            form.enabled
                                                        }
                                                        onChange={
                                                            handleFormChange
                                                        }
                                                    />

                                                    <span>
                                                        Enable zone
                                                    </span>
                                                </label>

                                                <div className="zone-editor-form-actions">
                                                    <button
                                                        type="button"
                                                        className="zone-cancel-button"
                                                        onClick={
                                                            resetEditor
                                                        }
                                                    >
                                                        Cancel
                                                    </button>

                                                    <button
                                                        type="submit"
                                                        className="zone-save-button"
                                                        disabled={
                                                            loading
                                                        }
                                                    >
                                                        {loading
                                                            ? "Saving..."
                                                            : "Save Zone"}
                                                    </button>
                                                </div>
                                            </form>
                                        </div>
                                    </div>
                                )}

                                {activeView ===
                                    "list" && (
                                    <div className="zone-list-view">
                                        <div className="zone-list-view-header">
                                            <div>
                                                <h3>
                                                    Configured
                                                    Zones
                                                </h3>
                                                <p>
                                                    Manage zones
                                                    for{" "}
                                                    <strong>
                                                        {
                                                            selectedCamera.camera_id
                                                        }
                                                    </strong>
                                                </p>
                                            </div>

                                            <button
                                                type="button"
                                                className="zone-add-new-button"
                                                onClick={
                                                    openAddZone
                                                }
                                            >
                                                + Add Zone
                                            </button>
                                        </div>

                                        {zones.length ===
                                        0 ? (
                                            <div className="zone-management-empty small">
                                                No zones
                                                configured
                                                for this
                                                camera.
                                            </div>
                                        ) : (
                                            <div className="configured-zones-grid">
                                                {zones.map(
                                                    (
                                                        zone
                                                    ) => (
                                                        <div
                                                            className="configured-zone-card"
                                                            key={
                                                                zone.zone_id
                                                            }
                                                        >
                                                            <div className="configured-zone-card-header">
                                                                <div>
                                                                    <h4>
                                                                        {
                                                                            zone.zone_name
                                                                        }
                                                                    </h4>
                                                                    <span>
                                                                        {
                                                                            zone.zone_id
                                                                        }
                                                                    </span>
                                                                </div>

                                                                <span
                                                                    className={
                                                                        zone.enabled
                                                                            ? "zone-enabled-badge"
                                                                            : "zone-disabled-badge"
                                                                    }
                                                                >
                                                                    {zone.enabled
                                                                        ? "Enabled"
                                                                        : "Disabled"}
                                                                </span>
                                                            </div>

                                                            <div className="configured-zone-details">
                                                                <div>
                                                                    <span>
                                                                        Threshold
                                                                    </span>
                                                                    <strong>
                                                                        {
                                                                            zone.threshold
                                                                        }
                                                                    </strong>
                                                                </div>

                                                                <div>
                                                                    <span>
                                                                        Points
                                                                    </span>
                                                                    <strong>
                                                                        {Array.isArray(
                                                                            zone.polygon
                                                                        )
                                                                            ? zone
                                                                                  .polygon
                                                                                  .length
                                                                            : 0}
                                                                    </strong>
                                                                </div>

                                                                <div>
                                                                    <span>
                                                                        Counting
                                                                        Point
                                                                    </span>
                                                                    <strong>
                                                                        {zone.point ===
                                                                        "center"
                                                                            ? "Center"
                                                                            : "Bottom Center"}
                                                                    </strong>
                                                                </div>
                                                            </div>

                                                            <div className="configured-zone-actions">
                                                                <button
                                                                    type="button"
                                                                    className="zone-edit-button"
                                                                    onClick={() =>
                                                                        openEditZone(
                                                                            zone
                                                                        )
                                                                    }
                                                                >
                                                                    Edit
                                                                </button>

                                                                <button
                                                                    type="button"
                                                                    className="zone-delete-button"
                                                                    onClick={() =>
                                                                        handleDeleteZone(
                                                                            zone.zone_id
                                                                        )
                                                                    }
                                                                >
                                                                    Delete
                                                                </button>
                                                            </div>
                                                        </div>
                                                    )
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </>
                        )}
                    </main>
                </div>
            )}
        </section>

        {isFullscreen && selectedCamera && (
            <div className="zone-fullscreen-overlay" role="dialog" aria-modal="true">
                <div className="zone-fullscreen-header">
                    <div>
                        <strong>
                            Draw Zone — {selectedCamera.camera_name || selectedCamera.camera_id}
                        </strong>
                        <span>Click on the camera image to add polygon points.</span>
                    </div>

                    <button
                        type="button"
                        className="zone-fullscreen-close"
                        onClick={closeFullscreenDraw}
                        aria-label="Close full screen zone editor"
                    >
                        ×
                    </button>
                </div>

                <div className="zone-fullscreen-stage">
                    <div className="zone-fullscreen-media">
                        {streamToken && <img
                            ref={videoRef}
                            className="zone-fullscreen-video"
                            src={streamUrl(selectedCamera.camera_id)}
                            alt={`Full screen zone editor for ${selectedCamera.camera_id}`}
                            onLoad={syncCanvasSize}
                        />}

                        <canvas
                            ref={canvasRef}
                            className="zone-fullscreen-canvas"
                            onClick={handleCanvasClick}
                        />
                    </div>

                    {isFullscreenFormOpen && (
                        <form
                            className="zone-fullscreen-form"
                            onSubmit={(event) =>
                                handleSubmit(event)
                            }
                        >
                            <div className="zone-fullscreen-form-header">
                                <strong>Save Zone</strong>
                                <button
                                    type="button"
                                    onClick={() =>
                                        setIsFullscreenFormOpen(false)
                                    }
                                    aria-label="Close save zone form"
                                >
                                    ×
                                </button>
                            </div>

                            <label>
                                <span>Zone ID</span>
                                <input
                                    name="zone_id"
                                    value={form.zone_id}
                                    onChange={handleFormChange}
                                    disabled={editingZoneId !== null}
                                    required
                                />
                            </label>

                            <label>
                                <span>Zone Name</span>
                                <input
                                    name="zone_name"
                                    value={form.zone_name}
                                    onChange={handleFormChange}
                                    required
                                />
                            </label>

                            <div className="zone-fullscreen-form-row">
                                <label>
                                    <span>Threshold</span>
                                    <input
                                        type="number"
                                        name="threshold"
                                        min="0"
                                        value={form.threshold}
                                        onChange={handleFormChange}
                                        required
                                    />
                                </label>

                                <label>
                                    <span>Counting Point</span>
                                    <select
                                        name="point"
                                        value={form.point}
                                        onChange={handleFormChange}
                                    >
                                        <option value="bottom_center">
                                            Bottom Center
                                        </option>
                                        <option value="center">
                                            Center
                                        </option>
                                    </select>
                                </label>
                            </div>

                            <button
                                type="submit"
                                className="zone-fullscreen-form-save"
                                disabled={loading}
                            >
                                {loading ? "Saving..." : "Save Zone"}
                            </button>
                        </form>
                    )}
                </div>

                <div className="zone-fullscreen-toolbar">
                    <div className="zone-fullscreen-point-count">
                        <strong>{points.length}</strong> points selected
                    </div>

                    <button
                        type="button"
                        className="zone-fullscreen-tool secondary"
                        onClick={clearPoints}
                        disabled={points.length === 0}
                    >
                        Clear Points
                    </button>

                    <button
                        type="button"
                        className="zone-fullscreen-tool"
                        onClick={requestResetAllZones}
                    >
                        Reset All Zones
                    </button>

                    <button
                        type="button"
                        className="zone-fullscreen-tool"
                        onClick={openFullscreenSaveForm}
                        disabled={loading}
                    >
                        Save Zone
                    </button>

                    <button
                        type="button"
                        className="zone-fullscreen-done"
                        onClick={finishFullscreenDraw}
                    >
                        Done Drawing
                    </button>
                </div>
            </div>
        )}

        {isResetZonesDialogOpen && (
            <div
                className="zone-reset-modal-backdrop"
                role="presentation"
                onClick={() => setIsResetZonesDialogOpen(false)}
            >
                <div
                    className="zone-reset-modal"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="zone-reset-title"
                    onClick={(event) => event.stopPropagation()}
                >
                    <h3 id="zone-reset-title">Reset all zones?</h3>
                    <p>
                        This will permanently delete all saved zones for
                        {` ${selectedCamera?.camera_name || selectedCameraId}`}.
                    </p>
                    <div className="zone-reset-modal-actions">
                        <button
                            type="button"
                            className="zone-reset-cancel"
                            onClick={() =>
                                setIsResetZonesDialogOpen(false)
                            }
                        >
                            Cancel
                        </button>
                        <button
                            type="button"
                            className="zone-reset-confirm"
                            onClick={resetAllZones}
                            disabled={loading}
                        >
                            {loading ? "Resetting..." : "Reset All Zones"}
                        </button>
                    </div>
                </div>
            </div>
        )}
        </>
    );
}

export default ZoneManagementTab;
