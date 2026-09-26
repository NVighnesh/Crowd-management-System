import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import "./CameraManagementSource.css";
import { API_BASE_URL } from "./apiBase";

function getSourceBasename(source) {
    if (!source) {
        return "";
    }

    return String(source).split(/[\\/]/).pop() || "";
}

const SUPPORTED_VIDEO_EXTENSIONS = [
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".m4v",
    ".webm",
];

const EMPTY_FORM = {
    camera_id: "",
    camera_name: "",
    source_type: "file",
    source: "",
    loop: true,
    enabled: true,
};

function getFileExtension(fileName) {
    const lastDot = fileName.lastIndexOf(".");
    return lastDot >= 0 ? fileName.slice(lastDot).toLowerCase() : "";
}

function isSupportedVideoFile(file) {
    return Boolean(file) &&
        SUPPORTED_VIDEO_EXTENSIONS.includes(getFileExtension(file.name));
}

function isValidRtspUrl(value) {
    return /^rtsps?:\/\/\S+$/i.test(value.trim());
}

function CameraManagement({ onCameraChanged }) {
    const [cameras, setCameras] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [editingCameraId, setEditingCameraId] = useState(null);
    const [selectedVideoFile, setSelectedVideoFile] = useState(null);

    const [form, setForm] = useState({
        ...EMPTY_FORM,
    });

    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);
    const [error, setError] = useState(null);

    const fileInputRef = useRef(null);

    async function loadCameras() {
        try {
            setError(null);

            const response = await fetch(`${API_BASE_URL}/cameras`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Failed to load cameras.");
            }

            setCameras(data.cameras || []);
        } catch (err) {
            setError(err.message);
        }
    }

    useEffect(() => {
        loadCameras();
    }, []);

    function resetForm() {
        setEditingCameraId(null);
        setSelectedVideoFile(null);
        setForm({ ...EMPTY_FORM });

        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    }

    function openAddForm() {
        resetForm();
        setMessage(null);
        setError(null);
        setShowForm(true);
    }

    function openEditForm(camera) {
        setEditingCameraId(camera.camera_id);

        setSelectedVideoFile(null);

        setForm({
            camera_id: camera.camera_id,
            camera_name: camera.camera_name || camera.camera_id,
            source_type: camera.source_type || "file",
            source: camera.source || "",
            loop: camera.loop !== undefined ? Boolean(camera.loop) : true,
            enabled: camera.enabled !== undefined ? Boolean(camera.enabled) : true,
        });

        setMessage(null);
        setError(null);
        setShowForm(true);
    }

    function closeForm() {
        setShowForm(false);
        resetForm();
        setMessage(null);
        setError(null);
    }

    function handleChange(event) {
        const { name, value, type, checked } = event.target;

        setForm((previous) => ({
            ...previous,
            [name]: type === "checkbox" ? checked : value,
        }));

        if (name === "source_type") {
            setSelectedVideoFile(null);

            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }

            setForm((previous) => ({
                ...previous,
                source_type: value,
                source: "",
            }));
        }
    }

    function handleVideoFileChange(event) {
        const file = event.target.files?.[0];

        if (!file) {
            setSelectedVideoFile(null);
            return;
        }

        if (!isSupportedVideoFile(file)) {
            setSelectedVideoFile(null);

            event.target.value = "";

            setError(
                `Unsupported video format. Supported formats: ${SUPPORTED_VIDEO_EXTENSIONS.join(", ")}`
            );

            return;
        }

        setError(null);
        setSelectedVideoFile(file);

        // Keep the selected filename visible while retaining the File for upload.
        setForm((previous) => ({
            ...previous,
            source: file.name,
        }));
    }

    async function handleSubmit(event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        if (loading) {
            return;
        }

        setLoading(true);
        setMessage(null);
        setError(null);

        try {
            if (!form.camera_id.trim()) {
                throw new Error("Camera ID is required.");
            }

            if (!form.camera_name.trim()) {
                throw new Error("Camera name is required.");
            }

            if (form.source_type === "file" || form.source_type === "drone") {
                if (!selectedVideoFile && !form.source.trim()) {
                    throw new Error("Select a supported video file.");
                }

                if (selectedVideoFile && !isSupportedVideoFile(selectedVideoFile)) {
                    throw new Error(
                        `Unsupported video format. Supported formats: ${SUPPORTED_VIDEO_EXTENSIONS.join(", ")}`
                    );
                }

                if (!selectedVideoFile && editingCameraId === null) {
                    throw new Error("Select a video file from your computer.");
                }
            }

            if (
                form.source_type === "rtsp" ||
                (
                    form.source_type === "drone" &&
                    /^rtsps?:\/\//i.test(form.source.trim())
                )
            ) {
                if (!isValidRtspUrl(form.source)) {
                    throw new Error(
                        "Enter a valid RTSP URL beginning with rtsp://"
                    );
                }
            }

            // Path-based sources use JSON; recorded videos use multipart upload.
            const isEditing = editingCameraId !== null;

            const url = isEditing
                ? `${API_BASE_URL}/cameras/${editingCameraId}`
                : `${API_BASE_URL}/cameras`;

            const method = isEditing ? "PUT" : "POST";

            const payload = {
                camera_id: form.camera_id.trim(),
                camera_name: form.camera_name.trim(),
                source_type: form.source_type,
                source: form.source.trim(),
                loop: form.loop,
                enabled: form.enabled,
            };

            const requestOptions = {
                method,
            };

            if (
                (form.source_type === "file" || form.source_type === "drone") &&
                selectedVideoFile
            ) {
                const formData = new FormData();

                if (!isEditing) {
                    formData.append("camera_id", payload.camera_id);
                }
                formData.append("camera_name", payload.camera_name);
                formData.append("source_type", payload.source_type);
                formData.append("source", payload.source);
                formData.append("loop", String(payload.loop));
                formData.append("enabled", String(payload.enabled));
                formData.append("video_file", selectedVideoFile);

                requestOptions.body = formData;
            } else {
                requestOptions.headers = {
                    "Content-Type": "application/json",
                };
                requestOptions.body = JSON.stringify(payload);
            }

            const response = await fetch(url, requestOptions);

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                throw new Error(
                    data.detail || "Camera operation failed."
                );
            }

            await loadCameras();

            // Close the form only after the backend confirms success.
            // Do not call closeForm() here because it clears the success message.
            setShowForm(false);
            resetForm();

            setMessage(
                isEditing
                    ? "Camera updated successfully."
                    : "Camera added successfully."
            );

            if (onCameraChanged) {
                onCameraChanged();
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    async function handleDelete(cameraId) {
        const confirmed = window.confirm(`Delete camera ${cameraId}?`);

        if (!confirmed) {
            return;
        }

        setLoading(true);
        setMessage(null);
        setError(null);

        try {
            const response = await fetch(
                `${API_BASE_URL}/cameras/${cameraId}`,
                {
                    method: "DELETE",
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Failed to delete camera."
                );
            }

            await loadCameras();

            setMessage("Camera deleted successfully.");

            if (onCameraChanged) {
                onCameraChanged();
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <section className="camera-management-section">
            <div className="camera-management-header">
                <div>
                    <h2 className="camera-section-title">
                        Camera Management
                    </h2>

                    <p className="camera-management-subtitle">
                        Add and configure cameras without changing backend
                        configuration files.
                    </p>
                </div>

                <button
                    className="camera-management-add-button"
                    onClick={openAddForm}
                    disabled={loading}
                >
                    + Add Camera
                </button>
            </div>

            {message && (
                <div className="camera-management-message success">
                    {message}
                </div>
            )}

            {error && (
                <div className="camera-management-message error">
                    {error}
                </div>
            )}

            <div className="camera-management-list">
                {cameras.length === 0 ? (
                    <div className="camera-management-empty">
                        No cameras configured.
                    </div>
                ) : (
                    cameras.map((camera) => (
                        <div
                            className="camera-management-item"
                            key={camera.camera_id}
                        >
                            <div className="camera-management-info">
                                <div>
                                    <strong>
                                        {camera.camera_name || camera.camera_id}
                                    </strong>

                                    <span>{camera.camera_id}</span>
                                </div>

                                <div className="camera-management-source">
                                    <span className="camera-source-badge">
                                        {camera.source_type === "rtsp"
                                            ? "RTSP"
                                            : "VIDEO"}
                                    </span>

                                    <span>
                                        {getSourceBasename(camera.source)}
                                    </span>
                                </div>
                            </div>

                            <div className="camera-management-status">
                                <span
                                    className={
                                        camera.enabled
                                            ? "camera-enabled"
                                            : "camera-disabled"
                                    }
                                >
                                    {camera.enabled ? "Enabled" : "Disabled"}
                                </span>

                                <button
                                    className="camera-management-edit"
                                    onClick={() => openEditForm(camera)}
                                    disabled={loading}
                                >
                                    Edit
                                </button>

                                <button
                                    className="camera-management-delete"
                                    onClick={() =>
                                        handleDelete(camera.camera_id)
                                    }
                                    disabled={loading}
                                >
                                    Delete
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {showForm && createPortal(
                <div
                    className="camera-management-modal-backdrop"
                    style={{ pointerEvents: "auto", zIndex: 99999 }}
                    onPointerDown={(event) => {
                        if (event.target === event.currentTarget) {
                            closeForm();
                        }
                    }}
                >
                    <div
                        className="camera-management-modal"
                        style={{ position: "relative", zIndex: 100000, pointerEvents: "auto" }}
                        onPointerDown={(event) => event.stopPropagation()}
                    >
                        <div className="camera-management-modal-header">
                            <div>
                                <h3>
                                    {editingCameraId
                                        ? "Edit Camera"
                                        : "Add Camera"}
                                </h3>

                                <p>
                                    Configure the camera source and runtime
                                    settings.
                                </p>
                            </div>

                            <button
                                className="camera-management-close"
                                onClick={closeForm}
                            >
                                ×
                            </button>
                        </div>

                        <form
                            onSubmit={handleSubmit}
                            className="camera-management-form"
                        >
                            <div className="camera-form-grid">
                                <label>
                                    <span>Camera ID</span>

                                    <input
                                        name="camera_id"
                                        value={form.camera_id}
                                        onChange={handleChange}
                                        placeholder="CAM_003"
                                        disabled={editingCameraId !== null}
                                        required
                                    />
                                </label>

                                <label>
                                    <span>Camera Name</span>

                                    <input
                                        name="camera_name"
                                        value={form.camera_name}
                                        onChange={handleChange}
                                        placeholder="Main Gate Camera"
                                        required
                                    />
                                </label>
                            </div>

                            <label>
                                <span>Camera Source</span>

                                <select
                                    name="source_type"
                                    value={form.source_type}
                                    onChange={handleChange}
                                >
                                    <option value="file">
                                        Recorded Video
                                    </option>

                                    <option value="rtsp">
                                        CCTV / RTSP Camera
                                    </option>

                                    <option value="drone">
                                        Drone / Aerial Camera
                                    </option>
                                </select>
                            </label>

                            {form.source_type === "file" ||
                            form.source_type === "drone" ? (
                                <div className="camera-file-picker">
                                    <span className="camera-file-picker-label">
                                        Recorded Video File
                                    </span>

                                    <div className="camera-file-picker-row">
                                        <input
                                            ref={fileInputRef}
                                            type="file"
                                            accept=".mp4,.avi,.mov,.mkv,.m4v,.webm,video/*"
                                            onChange={handleVideoFileChange}
                                            className="camera-file-input"
                                        />

                                        <button
                                            type="button"
                                            className="camera-file-browse-button"
                                            onClick={() =>
                                                fileInputRef.current?.click()
                                            }
                                        >
                                            Choose Video
                                        </button>
                                    </div>

                                    {selectedVideoFile ? (
                                        <div className="camera-file-selected">
                                            <strong>
                                                {selectedVideoFile.name}
                                            </strong>

                                            <span>
                                                {(selectedVideoFile.size /
                                                    (1024 * 1024)
                                                ).toFixed(1)}{" "}
                                                MB
                                            </span>
                                        </div>
                                    ) : editingCameraId !== null &&
                                      form.source ? (
                                        <div className="camera-file-current">
                                            Current source:{" "}
                                            <strong>{form.source}</strong>
                                        </div>
                                    ) : (
                                        <small className="camera-file-help">
                                            Supported: MP4, AVI, MOV, MKV, M4V
                                            and WebM
                                        </small>
                                    )}
                                </div>
                            ) : (
                                <label>
                                    <span>CCTV RTSP URL</span>

                                    <input
                                        name="source"
                                        value={form.source}
                                        onChange={handleChange}
                                        placeholder="rtsp://192.168.1.100:554/live"
                                        required
                                    />

                                    <small className="camera-source-help">
                                        Use an RTSP stream URL provided by the
                                        CCTV/NVR system.
                                    </small>
                                </label>
                            )}

                            {(form.source_type === "file" ||
                                form.source_type === "drone") && (
                                <label className="camera-form-checkbox">
                                    <input
                                        type="checkbox"
                                        name="loop"
                                        checked={form.loop}
                                        onChange={handleChange}
                                    />

                                    <span>Loop recorded video</span>
                                </label>
                            )}

                            <label className="camera-form-checkbox">
                                <input
                                    type="checkbox"
                                    name="enabled"
                                    checked={form.enabled}
                                    onChange={handleChange}
                                />

                                <span>Enable camera</span>
                            </label>

                            <div className="camera-management-form-actions">
                                <button
                                    type="button"
                                    className="camera-management-cancel"
                                    onClick={closeForm}
                                >
                                    Cancel
                                </button>

                                <button
                                    type="submit"
                                    className="camera-management-save"
                                    disabled={false}
                                    onClick={(event) => {
                                        event.preventDefault();
                                        event.stopPropagation();
                                        void handleSubmit(event);
                                    }}
                                    onPointerDown={(event) => {
                                        event.stopPropagation();
                                    }}
                                >
                                    {loading
                                        ? "Saving..."
                                        : editingCameraId
                                        ? "Update Camera"
                                        : "Add Camera"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>,
                document.body
            )}
        </section>
    );
}

export default CameraManagement;
