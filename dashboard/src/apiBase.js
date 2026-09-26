const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

if (import.meta.env.PROD && !configuredApiBaseUrl) {
    throw new Error("VITE_API_BASE_URL is required in production");
}

export const API_BASE_URL = configuredApiBaseUrl || "http://127.0.0.1:8000";
