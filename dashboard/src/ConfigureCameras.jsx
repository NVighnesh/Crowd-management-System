import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import CameraManagement from "./CameraManagement";
import ZoneManagementTab from "./ZoneManagementTab";
import { clearSession, getRole, getUsername, setSelectedOperator } from "./auth";
import Icon from "./Icon";
import "./dashboard.css";
import "./AdminDashboard.css";
import "./ConfigureCameras.css";
import "./ZoneManagement.css";

function ConfigureCameras({ showOperatorTab = true }) {
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState(() =>
        window.localStorage.getItem("configureCameras.activeSection") ||
        "camera"
    );
    const [now, setNow] = useState(() => new Date());
    const role = getRole();
    const username = getUsername();
    const isAdmin = role === "ADMIN";

    useEffect(() => {
        window.localStorage.setItem(
            "configureCameras.activeSection",
            activeTab
        );
    }, [activeTab]);

    useEffect(() => {
        const selectedOperator = new URLSearchParams(window.location.search).get("operator");
        if (isAdmin && selectedOperator) {
            setSelectedOperator(selectedOperator);
        }
        const timer = window.setInterval(() => setNow(new Date()), 60000);
        return () => window.clearInterval(timer);
    }, [isAdmin]);

    function logout() {
        clearSession();
        navigate("/login", { replace: true });
    }

    const dateLabel = now.toLocaleDateString(undefined, {
        weekday: "short",
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
    const timeLabel = now.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
    });

    return (
        <div className="admin-dashboard-shell configure-shell">
            <aside className="admin-sidebar">
                <div className="admin-brand">
                    <span className="admin-brand-mark"><Icon name="shield" size={23} /></span>
                    <span>
                        <strong>Crowd Management</strong>
                        <strong>System</strong>
                        <small>Safer Spaces<br />Brighter Tomorrow</small>
                    </span>
                </div>
                <nav className="admin-navigation" aria-label={`${isAdmin ? "Admin" : "Operator"} navigation`}>
                    <button type="button" className="admin-navigation-item" onClick={() => navigate("/")}>
                        <Icon name="home" size={19} /> {isAdmin ? "Admin Dashboard" : "Dashboard"}
                    </button>
                    {!isAdmin && (
                        <>
                            <button type="button" className="admin-navigation-item active">
                                <Icon name="camera" size={19} /> Configure Cameras
                            </button>
                            <button type="button" className="admin-navigation-item" onClick={() => navigate("/profile")}>
                                <Icon name="user" size={19} /> Profile
                            </button>
                        </>
                    )}
                </nav>
                <div className="admin-sidebar-footer">
                    <div>PEOPLE&nbsp; | &nbsp;SAFETY&nbsp; | &nbsp;SMARTER TOMORROW</div>
                    <button type="button" onClick={logout}><Icon name="logout" size={16} /> Logout</button>
                </div>
            </aside>

            <main className="admin-dashboard-content configure-content">
                <header className="admin-content-header configure-content-header">
                    <div className="admin-header-title">
                        <span className="admin-menu-icon"><Icon name="menu" size={21} /></span>
                        <div>
                            <h1>Configure Cameras</h1>
                            <p>Manage cameras, video sources, and monitoring zones</p>
                        </div>
                    </div>
                    <div className="admin-header-actions">
                        <button className="admin-notification" type="button" aria-label="Notifications">
                            <Icon name="bell" size={20} />
                        </button>
                        <div className="admin-profile">
                            <span><Icon name="user" size={18} /></span>
                            <strong>{isAdmin ? "Admin" : username || "Operator"}</strong>
                            <small>{isAdmin ? "Administrator" : "Operator"}</small>
                            <b aria-hidden="true"><Icon name="chevronDown" size={14} /></b>
                        </div>
                    </div>
                </header>
                <div className="admin-date-time configure-date-time">
                    <span><Icon name="calendar" size={13} />{dateLabel}</span>
                    <span><Icon name="clock" size={13} />{timeLabel}</span>
                </div>

                <div className="configure-workspace">
                    <div className="configure-main-tabs">
                <button
                    type="button"
                    className={`configure-main-tab ${
                        activeTab === "camera" ? "active" : ""
                    }`}
                    onClick={() => setActiveTab("camera")}
                >
                    <span className="configure-main-tab-icon"><Icon name="camera" size={18} /></span>
                    <span>
                        <strong>Camera Management</strong>
                        <small>Add, edit, or delete cameras</small>
                    </span>
                </button>

                <button
                    type="button"
                    className={`configure-main-tab ${
                        activeTab === "zone" ? "active" : ""
                    }`}
                    onClick={() => setActiveTab("zone")}
                >
                    <span className="configure-main-tab-icon"><Icon name="zones" size={18} /></span>
                    <span>
                        <strong>Zone Management</strong>
                        <small>Define and manage monitoring zones</small>
                    </span>
                </button>

            </div>

            {activeTab === "camera" && (
                <CameraManagement onCameraChanged={() => {}} />
            )}

            {activeTab === "zone" && (
                <ZoneManagementTab
                    onCameraManagement={() => setActiveTab("camera")}
                />
            )}
            </div>
            </main>
        </div>
    );
}

export default ConfigureCameras;
