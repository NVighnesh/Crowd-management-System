import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import OperatorManagement from "./OperatorManagement";
import { clearSession } from "./auth";
import "./dashboard.css";
import "./AdminDashboard.css";
import Icon from "./Icon";
import { API_BASE_URL } from "./apiBase";

export default function AdminDashboard() {
    const navigate = useNavigate();
    const [now, setNow] = useState(() => new Date());
    const [alertCount, setAlertCount] = useState(null);

    useEffect(() => {
        const timer = window.setInterval(() => setNow(new Date()), 60000);
        return () => window.clearInterval(timer);
    }, []);

    useEffect(() => {
        let cancelled = false;
        fetch(`${API_BASE_URL}/admin/alerts/count`)
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Failed to fetch alert count: ${response.status}`);
                }
                return response.json();
            })
            .then((data) => {
                if (!cancelled) {
                    setAlertCount(Number.isFinite(data.count) ? data.count : 0);
                }
            })
            .catch((error) => {
                if (!cancelled) {
                    console.error(error);
                    setAlertCount(null);
                }
            });
        return () => {
            cancelled = true;
        };
    }, []);

    function logout() {
        clearSession();
        navigate("/login", { replace: true });
    }

    return (
        <div className="admin-dashboard-shell">
            <aside className="admin-sidebar">
                <div className="admin-brand">
                    <span className="admin-brand-mark"><Icon name="shield" size={23} /></span>
                    <span>
                        <strong>Crowd Management</strong>
                        <strong>System</strong>
                        <small>Safer Spaces<br />Brighter Tomorrow</small>
                    </span>
                </div>
                <nav className="admin-navigation" aria-label="Admin navigation">
                    <button className="admin-navigation-item active" type="button">
                        <Icon name="home" size={19} /> Admin Dashboard
                    </button>
                </nav>
                <div className="admin-sidebar-footer">
                    <div>PEOPLE&nbsp; | &nbsp;SAFETY&nbsp; | &nbsp;SMARTER TOMORROW</div>
                    <button type="button" onClick={logout}><Icon name="logout" size={16} /> Logout</button>
                </div>
            </aside>

            <main className="admin-dashboard-content">
                <header className="admin-content-header">
                    <div className="admin-header-title">
                        <span className="admin-menu-icon"><Icon name="menu" size={21} /></span>
                        <div>
                            <h1>Admin Dashboard</h1>
                            <p>Manage operators and oversee the crowd management system</p>
                        </div>
                    </div>
                    <div className="admin-header-actions">
                        <button className="admin-notification" type="button" aria-label="Notifications">
                            <Icon name="bell" size={20} />
                            {alertCount > 0 && <span>{alertCount}</span>}
                        </button>
                        <div className="admin-profile">
                            <span><Icon name="user" size={18} /></span>
                            <strong>Admin</strong>
                            <small>Administrator</small>
                            <b aria-hidden="true">⌄</b>
                        </div>
                    </div>
                </header>
                <div className="admin-date-time">
                    <span><Icon name="calendar" size={13} />{now.toLocaleDateString(undefined, { weekday: "short", day: "2-digit", month: "short", year: "numeric" })}</span>
                    <span><Icon name="clock" size={13} />{now.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}</span>
                </div>

                <section className="admin-welcome-banner">
                    <div>
                        <h2>Welcome, Admin</h2>
                        <p>Monitor, manage and ensure safer public spaces</p>
                    </div>
                </section>

                <OperatorManagement onManage={(username) => navigate(`/configure-cameras?operator=${encodeURIComponent(username)}`)} />

                <footer className="admin-footer">
                    <span>© 2026 Crowd Management System. All rights reserved.<br /><small>Technology for a Safer Tomorrow.</small></span>
                    <span>Version 1.0.0</span>
                </footer>
            </main>
        </div>
    );
}
