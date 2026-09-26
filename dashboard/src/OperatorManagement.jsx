import { useEffect, useMemo, useState } from "react";
import { setSelectedOperator } from "./auth";
import Icon from "./Icon";
import { API_BASE_URL } from "./apiBase";

export default function OperatorManagement({ onManage }) {
    const [operators, setOperators] = useState([]);
    const [cameraCount, setCameraCount] = useState(0);
    const [error, setError] = useState("");
    const [search, setSearch] = useState("");
    const [loading, setLoading] = useState(true);

    async function loadData() {
        setLoading(true);
        setError("");
        try {
            const [operatorResponse, cameraResponse] = await Promise.all([
                fetch(`${API_BASE_URL}/admin/operators`),
                fetch(`${API_BASE_URL}/cameras`),
            ]);
            const operatorData = await operatorResponse.json().catch(() => ({}));
            if (!operatorResponse.ok) {
                throw new Error(operatorData.detail || `Unable to load operators (HTTP ${operatorResponse.status}).`);
            }
            setOperators(Array.isArray(operatorData) ? operatorData : operatorData.operators || []);
            if (cameraResponse.ok) {
                const cameraData = await cameraResponse.json();
                setCameraCount(Array.isArray(cameraData) ? cameraData.length : Number(cameraData.count ?? (cameraData.cameras || []).length));
            } else {
                setCameraCount(0);
            }
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadData().catch((err) => setError(err.message || "Unable to load operators."));
    }, []);

    async function setActive(username, active) {
        const action = active ? "activate" : "disable";
        const response = await fetch(`${API_BASE_URL}/admin/operators/${encodeURIComponent(username)}/${action}`, { method: "POST" });
        if (!response.ok) {
            setError(`Failed to ${active ? "activate" : "deactivate"} operator.`);
            return;
        }
        loadData().catch((err) => setError(err.message));
    }

    async function deleteOperator(username) {
        if (!window.confirm(`Delete operator ${username}?`)) return;
        const response = await fetch(`${API_BASE_URL}/admin/operators/${encodeURIComponent(username)}`, { method: "DELETE" });
        if (!response.ok) {
            setError(`Failed to delete ${username}.`);
            return;
        }
        loadData().catch((err) => setError(err.message));
    }

    const filteredOperators = useMemo(() => {
        const query = search.trim().toLowerCase();
        return operators.filter((operator) => !query || operator.username.toLowerCase().includes(query));
    }, [operators, search]);
    const activeCount = operators.filter((operator) => operator.active === true).length;

    return (
        <section className="admin-operators-section">
            <div className="admin-statistics-grid">
                <StatCard icon="users" label="Total Operators" value={operators.length} accent="blue" />
                <StatCard icon="check" label="Active Operators" value={activeCount} accent="green" />
                <StatCard icon="pause" label="Inactive Operators" value={operators.length - activeCount} accent="orange" />
                <StatCard icon="camera" label="Total Cameras" value={cameraCount} accent="purple" />
            </div>

            <section className="admin-operators-card">
                <div className="admin-operators-heading">
                    <div>
                        <h2><Icon name="users" size={19} /> Operators</h2>
                        <p>View and manage all registered operators</p>
                    </div>
                    <label className="admin-search">
                        <Icon name="search" size={16} />
                        <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search operators..." />
                    </label>
                </div>
                {error && <p className="admin-error" role="alert">{error} <button type="button" onClick={() => loadData().catch((err) => setError(err.message || "Unable to load operators."))}>Retry</button></p>}
                <div className="admin-table-wrap">
                    <table className="admin-operators-table">
                        <thead>
                            <tr><th>#</th><th>Operator Name</th><th>Username</th><th>Status</th><th>Cameras</th><th>Zones</th><th>Created On</th><th>Actions</th></tr>
                        </thead>
                        <tbody>
                            {loading && <tr><td className="admin-empty" colSpan="8">Loading operators...</td></tr>}
                            {!loading && filteredOperators.map((operator, index) => (
                                <tr key={operator.username}>
                                    <td>{index + 1}</td>
                                    <td><span className="admin-operator-avatar">{operator.username.slice(0, 1).toUpperCase()}</span><strong>{operator.username}</strong></td>
                                    <td>{operator.username}</td>
                                    <td><span className={`admin-status ${operator.active ? "active" : "inactive"}`}><i />{operator.active ? "Active" : "Inactive"}</span></td>
                                    <td>{Number(operator.camera_count ?? 0)}</td>
                                    <td>{Number(operator.zone_count ?? 0)}</td>
                                    <td>{operator.created_at ? new Date(operator.created_at).toLocaleDateString() : "—"}</td>
                                    <td>
                                        <div className="admin-row-actions">
                                            <button type="button" onClick={() => setActive(operator.username, !operator.active)}>{operator.active ? "Deactivate" : "Activate"}</button>
                                            <button type="button" onClick={() => { setSelectedOperator(operator.username); onManage(operator.username); }}>Manage</button>
                                            <button className="danger" type="button" onClick={() => deleteOperator(operator.username)}>Delete</button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {!loading && !filteredOperators.length && <tr><td className="admin-empty" colSpan="8">{error ? "Unable to load operators." : "No operators found."}</td></tr>}
                        </tbody>
                    </table>
                </div>
                <div className="admin-pagination"><span>Showing {filteredOperators.length ? 1 : 0} to {filteredOperators.length} of {filteredOperators.length} operators</span><div><button type="button" disabled>Previous</button><b>1</b><button type="button" disabled>Next</button></div></div>
            </section>
        </section>
    );
}

function StatCard({ icon, label, value, accent }) {
    return <article className={`admin-stat-card ${accent}`}><span className="admin-stat-icon"><Icon name={icon} size={21} /></span><div><p>{label}</p><strong>{value}</strong><small>Updated from live data</small></div></article>;
}
