// Thin axios-based API client with automatic bearer token attachment.
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

const STORAGE_KEY = "seekprofit.auth";

const client = axios.create({ baseURL: API_BASE });

client.interceptors.request.use((config) => {
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (raw) {
            const parsed = JSON.parse(raw);
            if (parsed?.token) {
                config.headers = config.headers || {};
                config.headers.Authorization = `Bearer ${parsed.token}`;
            }
        }
    } catch {
        /* ignore */
    }
    return config;
});

export const readSession = () => {
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
};

export const writeSession = (session) => {
    if (!session) {
        window.localStorage.removeItem(STORAGE_KEY);
    } else {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    }
};

// Extract a user-friendly error message from FastAPI's varied shapes.
export const apiError = (err) => {
    const detail = err?.response?.data?.detail;
    if (!detail) return err?.message || "Something went wrong.";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
        return detail
            .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
            .filter(Boolean)
            .join(" ");
    }
    if (detail && typeof detail.msg === "string") return detail.msg;
    return String(detail);
};

export default client;
