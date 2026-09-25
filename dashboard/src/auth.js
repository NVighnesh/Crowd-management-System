const API_BASE_URL = "http://127.0.0.1:8000";
const TOKEN_KEY = "crowd_access_token";
const ROLE_KEY = "crowd_role";
const USERNAME_KEY = "crowd_username";
const OPERATOR_CONTEXT_KEY = "crowd_selected_operator";

export function getToken() {
    return sessionStorage.getItem(TOKEN_KEY);
}

export function getRole() {
    return sessionStorage.getItem(ROLE_KEY);
}

export function saveSession(data) {
    sessionStorage.setItem(TOKEN_KEY, data.access_token);
    sessionStorage.setItem(ROLE_KEY, data.role);
}

export function clearSession() {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(ROLE_KEY);
    sessionStorage.removeItem(USERNAME_KEY);
    setSelectedOperator("");
}

export function getUsername() {
    return sessionStorage.getItem(USERNAME_KEY) || "";
}

export function getSelectedOperator() {
    return sessionStorage.getItem(OPERATOR_CONTEXT_KEY) || "";
}

export function setSelectedOperator(username) {
    if (username) {
        sessionStorage.setItem(OPERATOR_CONTEXT_KEY, username);
    } else {
        sessionStorage.removeItem(OPERATOR_CONTEXT_KEY);
    }
    window.dispatchEvent(new Event("crowd-operator-context"));
}

export async function login(username, password) {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, password }),
    });
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        if (response.status === 403 && data.detail === "Your account is inactive. Please contact admin.") {
            throw new Error(data.detail);
        }
        throw new Error("Invalid credentials");
    }
    const data = await response.json();
    saveSession(data);
    sessionStorage.setItem(USERNAME_KEY, username);
    return data;
}

export async function registerOperator(username, password) {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, password }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.detail || "Unable to register operator.");
    }
    return data;
}

export function installAuthFetch() {
    if (window.__crowdAuthFetchInstalled) {
        return;
    }
    const originalFetch = window.fetch.bind(window);
    window.fetch = (input, init = {}) => {
        const url = typeof input === "string" ? input : input.url;
        const headers = new Headers(init.headers || {});
        const token = getToken();
        if (token && url.startsWith(API_BASE_URL)) {
            headers.set("Authorization", `Bearer ${token}`);
        }
        const selectedOperator = getSelectedOperator();
        if (getRole() === "ADMIN" && selectedOperator && url.startsWith(API_BASE_URL)) {
            headers.set("X-Operator-Username", selectedOperator);
        }
        return originalFetch(input, {
            ...init,
            headers,
            credentials: "include",
        }).then((response) => {
            if (response.status === 401) {
                clearSession();
                window.dispatchEvent(new Event("crowd-auth-expired"));
            }
            return response;
        });
    };
    window.__crowdAuthFetchInstalled = true;
}
