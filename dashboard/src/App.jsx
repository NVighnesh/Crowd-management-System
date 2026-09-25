import { BrowserRouter, Navigate, Routes, Route, useLocation, useNavigate } from "react-router-dom";
import DashboardPage from "./DashboardPage";
import ConfigureCameras from "./ConfigureCameras";
import AdminDashboard from "./AdminDashboard";
import { useEffect, useState } from "react";
import {
    clearSession,
    getRole,
    getToken,
    getUsername,
    login,
    registerOperator,
} from "./auth";
import Icon from "./Icon";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

function getSourceBasename(source) {
    if (!source) {
        return "";
    }

    return String(source).split(/[\\/]/).pop() || "";
}

function LoginScreen({ onLogin }) {
    const navigate = useNavigate();
    const location = useLocation();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState("");
    const [message, setMessage] = useState(location.state?.message || "");

    async function submit(event) {
        event.preventDefault();
        setError("");
        setMessage("");
        try {
            const data = await login(username, password);
            onLogin(data);
        } catch (loginError) {
            setError(loginError.message);
        }
    }

    return (
        <main className="login-page">
            <section className="visual-panel" aria-label="Crowd Management System">
            </section>

            <section className="form-panel">
                <div className="form-wrap">
                    <div className="welcome-icon">👥</div>

                    <div className="form-heading">
                        <h2>
                            Welcome to
                            <br />
                            Crowd Management System
                        </h2>
                        <p>Sign in to monitor and manage your public spaces</p>
                    </div>

                    <form className="login-card" onSubmit={submit}>
                        <div className="field">
                            <label htmlFor="username">Username</label>
                            <div className="input-wrap">
                                <span className="input-icon">◌</span>
                                <input
                                    id="username"
                                    name="username"
                                    type="text"
                                    autoComplete="username"
                                    placeholder="Enter your username"
                                    value={username}
                                    onChange={(event) => setUsername(event.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        <div className="field">
                            <label htmlFor="password">Password</label>
                            <div className="input-wrap">
                                <span className="input-icon">◍</span>
                                <input
                                    id="password"
                                    name="password"
                                    type={showPassword ? "text" : "password"}
                                    autoComplete="current-password"
                                    placeholder="Enter your password"
                                    value={password}
                                    onChange={(event) => setPassword(event.target.value)}
                                    required
                                />
                                <button
                                    className="password-toggle"
                                    type="button"
                                    aria-label={showPassword ? "Hide password" : "Show password"}
                                    onClick={() => setShowPassword((value) => !value)}
                                >
                                    {showPassword ? "◉" : "◎"}
                                </button>
                            </div>
                        </div>

                        <div className="form-options">
                            <label className="remember">
                                <input type="checkbox" name="remember" />
                                <span>Remember me</span>
                            </label>
                            <a className="forgot" href="#">Forgot password?</a>
                        </div>

                        {error && <p className="form-message error" role="alert">{error}</p>}
                            {message && <p className="form-message success" role="status">{message}</p>}

                            <button className="sign-in" type="submit">
                            Sign In
                            <span className="sign-arrow">→</span>
                        </button>

                        <div className="divider">
                            <span>or</span>
                        </div>

                        <div className="register">
                            New to the system?
                            <button
                                type="button"
                                className="register-link"
                                onClick={() => navigate("/signup")}
                            >
                                Create an account
                            </button>
                        </div>
                    </form>

                    <div className="security-note">Secure access to the Crowd Management Monitoring System</div>
                </div>
            </section>
        </main>
    );
}

function SignupScreen() {
    const navigate = useNavigate();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [error, setError] = useState("");
    const [submitting, setSubmitting] = useState(false);

    async function submit(event) {
        event.preventDefault();
        setError("");
        if (password !== confirmPassword) {
            setError("Passwords do not match.");
            return;
        }

        setSubmitting(true);
        try {
            await registerOperator(username, password);
            navigate("/login", {
                replace: true,
                state: { message: "Operator account created. You can now sign in." },
            });
        } catch (registrationError) {
            setError(registrationError.message);
        } finally {
            setSubmitting(false);
        }

    }

    return (
        <main className="signup-page">
            <section className="signup-visual-panel" aria-label="Crowd Management System" />
            <section className="signup-form-panel">
                <form className="signup-card" onSubmit={submit}>
                    <div className="signup-icon">👥</div>
                    <h1>Create Operator Account</h1>
                    <p className="signup-subtitle">Join the Crowd Management System</p>

                    <div className="signup-field">
                        <label htmlFor="signup-username">Username</label>
                        <div className="signup-input-wrap">
                            <span className="signup-input-icon">♙</span>
                            <input
                                id="signup-username"
                                type="text"
                                autoComplete="username"
                                placeholder="Enter your username"
                                value={username}
                                onChange={(event) => setUsername(event.target.value)}
                                required
                            />
                        </div>
                    </div>

                    <div className="signup-field">
                        <label htmlFor="signup-password">Password</label>
                        <div className="signup-input-wrap">
                            <span className="signup-input-icon">▣</span>
                            <input
                                id="signup-password"
                                type={showPassword ? "text" : "password"}
                                autoComplete="new-password"
                                placeholder="Enter your password"
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                required
                            />
                            <button
                                className="signup-password-toggle"
                                type="button"
                                aria-label={showPassword ? "Hide password" : "Show password"}
                                onClick={() => setShowPassword((value) => !value)}
                            >
                                ◉
                            </button>
                        </div>
                    </div>

                    <div className="signup-field">
                        <label htmlFor="signup-confirm-password">Confirm Password</label>
                        <div className="signup-input-wrap">
                            <span className="signup-input-icon">▣</span>
                            <input
                                id="signup-confirm-password"
                                type={showConfirmPassword ? "text" : "password"}
                                autoComplete="new-password"
                                placeholder="Confirm your password"
                                value={confirmPassword}
                                onChange={(event) => setConfirmPassword(event.target.value)}
                                required
                            />
                            <button
                                className="signup-password-toggle"
                                type="button"
                                aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                                onClick={() => setShowConfirmPassword((value) => !value)}
                            >
                                ◉
                            </button>
                        </div>
                    </div>

                    {error && <p className="form-message error" role="alert">{error}</p>}

                    <button className="signup-submit" type="submit" disabled={submitting}>
                        {submitting ? "Creating Account..." : "Create Account"}
                        <span>→</span>
                    </button>

                    <div className="signup-divider"><span>or</span></div>

                    <button className="signup-login-link" type="button" onClick={() => navigate("/login")}>
                        Already have an account? <span>Sign in</span>
                    </button>
                </form>

                <footer className="signup-footer">
                    © 2026 Crowd Management System. All rights reserved.
                    <strong>Technology for a Safer Tomorrow</strong>
                </footer>
            </section>
        </main>
    );
}

function ProfileScreen() {
    const navigate = useNavigate();
    const [overview, setOverview] = useState(null);
    const [error, setError] = useState("");
    const [now, setNow] = useState(() => new Date());
    const [streamToken, setStreamToken] = useState("");
    const username = getUsername() || "User";
    const role = getRole() || "OPERATOR";
    const isAdmin = role === "ADMIN";

    useEffect(() => {
        let mounted = true;
        Promise.all([
            fetch(`${API_BASE_URL}/system/overview`),
            fetch(`${API_BASE_URL}/cameras`),
            fetch(`${API_BASE_URL}/auth/stream-token`, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${getToken() || ""}`,
                },
            }),
        ])
            .then(async ([overviewResponse, camerasResponse, tokenResponse]) => {
                if (!overviewResponse.ok || !camerasResponse.ok) {
                    throw new Error("Unable to load profile data.");
                }

                const [overviewData, camerasData, tokenData] =
                    await Promise.all([
                        overviewResponse.json(),
                        camerasResponse.json(),
                        tokenResponse.ok
                            ? tokenResponse.json()
                            : Promise.resolve({}),
                    ]);
                const configuredCameras = Array.isArray(camerasData.cameras)
                    ? camerasData.cameras
                    : [];
                const overviewCameras = Array.isArray(overviewData.cameras)
                    ? overviewData.cameras
                    : [];
                const mergedCameras = configuredCameras.map((camera) => ({
                    ...camera,
                    ...(overviewCameras.find(
                        (item) => item.camera_id === camera.camera_id
                    ) || {}),
                }));

                if (mounted) {
                    setOverview({
                        ...overviewData,
                        cameras: mergedCameras,
                    });
                    setStreamToken(tokenData.access_token || getToken() || "");
                }
            })
            .catch((loadError) => {
                if (mounted) {
                    setError(loadError.message);
                }
            });
        const timer = window.setInterval(() => setNow(new Date()), 1000);
        return () => {
            mounted = false;
            window.clearInterval(timer);
        };
    }, []);

    const cameras = Array.isArray(overview?.cameras) ? overview.cameras : [];
    const initials = username
        .split(/\s+/)
        .filter(Boolean)
        .map((part) => part[0])
        .join("")
        .slice(0, 2)
        .toUpperCase();

    function logout() {
        clearSession();
        navigate("/login", { replace: true });
    }

    function streamUrl(cameraId) {
        if (!streamToken || !cameraId) {
            return "";
        }

        return `${API_BASE_URL}/cameras/${encodeURIComponent(
            cameraId
        )}/stream?stream_token=${encodeURIComponent(streamToken)}`;
    }

    return (
        <div className="profile-shell">
            <aside className="profile-sidebar">
                <div className="profile-brand">
                    <span className="profile-brand-mark"><Icon name="shield" size={23} /></span>
                    <span><strong>Crowd Management</strong><strong>System</strong><small>Safer Spaces<br />Brighter Tomorrow</small></span>
                </div>
                <nav className="profile-nav" aria-label={`${isAdmin ? "Admin" : "Operator"} navigation`}>
                    <button type="button" onClick={() => navigate(isAdmin ? "/admin" : "/")}><Icon name="home" size={19} /> Dashboard</button>
                    <button type="button" onClick={() => navigate("/configure-cameras")}><Icon name="camera" size={19} /> Configure Cameras</button>
                    <button type="button" className="active" aria-current="page"><Icon name="user" size={19} /> Profile</button>
                </nav>
                <div className="profile-sidebar-footer">
                    <div>PEOPLE&nbsp; | &nbsp;SAFETY&nbsp; | &nbsp;SMARTER TOMORROW</div>
                    <button type="button" onClick={logout}><Icon name="logout" size={17} /> Logout</button>
                </div>
            </aside>

            <main className="profile-content">
                <header className="profile-header">
                    <div className="profile-heading">
                        <span className="profile-menu-icon"><Icon name="menu" size={21} /></span>
                        <div><h1>Profile</h1><p>View your account details and assigned cameras</p></div>
                    </div>
                    <div className="profile-header-tools">
                        <button type="button" aria-label="Notifications"><Icon name="bell" size={20} /></button>
                        <div className="profile-header-user">
                            <span className="profile-header-avatar">{initials}</span>
                            <span><strong>{username}</strong><small>{role}</small></span>
                            <Icon name="chevronDown" size={14} />
                        </div>
                    </div>
                </header>
                <div className="profile-date-time">
                    <span><Icon name="calendar" size={14} /> {now.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" })}</span>
                    <span><Icon name="clock" size={14} /> {now.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}</span>
                </div>

                <section className="profile-panels">
                    <article className="profile-details-card">
                        <div className="profile-large-avatar">{initials}</div>
                        <h2>{username}</h2>
                        <span className="profile-role-badge">{role}</span>
                        <p className="profile-description">Monitoring crowd activity and managing assigned cameras.</p>
                        <div className="profile-detail-list">
                            <div><Icon name="user" size={17} /><span>Username</span><strong>{username}</strong></div>
                            <div><Icon name="shield" size={17} /><span>Role</span><strong>{role}</strong></div>
                            <div><Icon name="camera" size={17} /><span>Assigned Cameras</span><strong>{cameras.length}</strong></div>
                            <div><Icon name="check" size={17} /><span>Status</span><strong className="profile-active-status"><i /> Authenticated</strong></div>
                        </div>
                    </article>

                    <article className="profile-cameras-card">
                        <div className="profile-card-heading">
                            <div><Icon name="camera" size={22} /><span><h2>Assigned Cameras</h2><p>Cameras currently assigned to your account</p></span></div>
                            <strong className="profile-camera-count">{cameras.length}<small>Total Cameras</small></strong>
                        </div>
                        {error && <p className="profile-error" role="alert">{error}</p>}
                        {!error && cameras.length === 0 && <div className="profile-empty-state">No cameras are currently assigned to this account.</div>}
                        {cameras.map((camera) => {
                            const cameraId = camera.camera_id || camera.id;
                            const zones = Array.isArray(camera.zones) ? camera.zones : [];
                            return (
                                <div className="profile-camera-row" key={cameraId}>
                                    <span className="profile-camera-thumbnail">
                                        {streamUrl(cameraId) ? (
                                            <img
                                                src={streamUrl(cameraId)}
                                                alt={`Preview of ${camera.camera_name || cameraId}`}
                                            />
                                        ) : (
                                            <Icon name="camera" size={24} />
                                        )}
                                    </span>
                                    <span className="profile-camera-copy">
                                        <strong>{camera.name || camera.camera_name || cameraId}</strong>
                                        <small>
                                            {camera.source_type || "Camera source"}
                                            {camera.source
                                                ? ` · ${getSourceBasename(camera.source)}`
                                                : ""}
                                            {camera.enabled === false ? " · Disabled" : " · Active"}
                                        </small>
                                        <em><i className={camera.enabled === false ? "inactive" : ""} />{camera.enabled === false ? "Inactive" : "Active"}</em>
                                    </span>
                                    <span className="profile-zone-count"><Icon name="pin" size={18} /> {zones.length}<small>Zones</small></span>
                                </div>
                            );
                        })}
                    </article>
                </section>
            </main>
        </div>
    );
}

function App() {
    const [securityEnabled, setSecurityEnabled] = useState(false);
    const [authenticated, setAuthenticated] = useState(Boolean(getToken()));
    const [role, setRole] = useState(getRole());

    useEffect(() => {
        fetch(`${API_BASE_URL}/auth/config`, { credentials: "include" })
            .then((response) => response.json())
            .then((data) => setSecurityEnabled(Boolean(data.enabled)))
            .catch(() => setSecurityEnabled(false));
        const expire = () => setAuthenticated(false);
        window.addEventListener("crowd-auth-expired", expire);
        return () => window.removeEventListener("crowd-auth-expired", expire);
    }, []);

    return (
        <BrowserRouter>
            <Routes>
                <Route
                    path="/login"
                    element={authenticated ? <Navigate to={role === "ADMIN" ? "/admin" : "/"} replace /> : <LoginScreen
                        onLogin={(data) => {
                            setRole(data.role || getRole());
                            setAuthenticated(true);
                        }}
                    />}
                />
                <Route
                    path="/signup"
                    element={authenticated ? <Navigate to={role === "ADMIN" ? "/admin" : "/"} replace /> : <SignupScreen />}
                />
                <Route
                    path="/camera-focus/:cameraId"
                    element={!authenticated
                        ? <Navigate to="/login" replace />
                        : role === "ADMIN"
                            ? <AdminDashboard />
                            : <DashboardPage />}
                />
                <Route
                    path="/profile"
                    element={!authenticated ? <Navigate to="/login" replace /> : <ProfileScreen />}
                />
                <Route
                    path="/"
                    element={!authenticated
                        ? <Navigate to="/login" replace />
                        : role === "ADMIN"
                            ? <AdminDashboard />
                            : <DashboardPage />}
                />

                <Route
                    path="/configure-cameras"
                    element={!authenticated
                        ? <Navigate to="/login" replace />
                        : role === "ADMIN" || role === "OPERATOR"
                            ? <ConfigureCameras />
                            : <DashboardPage />}
                />
                <Route
                    path="/admin"
                    element={!authenticated
                        ? <Navigate to="/login" replace />
                        : role === "ADMIN" ? <AdminDashboard /> : <Navigate to="/" replace />}
                />
                <Route path="*" element={<Navigate to={authenticated ? "/" : "/login"} replace />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;