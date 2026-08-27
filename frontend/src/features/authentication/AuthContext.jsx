import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
} from "react";
import api, { readSession, writeSession, apiError } from "@/lib/api";

const AuthContext = createContext(null);

/**
 * Real auth backed by /api/auth/*. Persists `{ token, user }` in localStorage
 * under `seekprofit.auth`. On mount we re-verify the token by calling /me so
 * a stale token bounces the user back to /login cleanly.
 */
export const AuthProvider = ({ children }) => {
    const initial = readSession();
    const [token, setToken] = useState(initial?.token || null);
    const [user, setUser] = useState(initial?.user || null);
    const [status, setStatus] = useState(initial?.token ? "checking" : "ready");
    const [error, setError] = useState(null);

    // Persist on change
    useEffect(() => {
        if (token && user) {
            writeSession({ token, user });
        } else {
            writeSession(null);
        }
    }, [token, user]);

    // Verify token on boot
    useEffect(() => {
        if (!token) return;
        // Skip verification if we're in the middle of the OAuth callback
        if (window.location.hash?.includes("session_id=")) {
            setStatus("ready");
            return;
        }
        (async () => {
            try {
                const { data } = await api.get("/auth/me");
                setUser(data);
                setStatus("ready");
            } catch {
                setToken(null);
                setUser(null);
                setStatus("ready");
            }
        })();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const applySession = useCallback((session) => {
        setToken(session.token);
        setUser(session.user);
        setError(null);
        setStatus("ready");
    }, []);

    const signIn = useCallback(async ({ email, password }) => {
        setError(null);
        try {
            const { data } = await api.post("/auth/login", { email, password });
            applySession(data);
            return data.user;
        } catch (e) {
            const msg = apiError(e);
            setError(msg);
            throw new Error(msg);
        }
    }, [applySession]);

    const signUp = useCallback(async ({ email, password, name }) => {
        setError(null);
        try {
            const { data } = await api.post("/auth/register", { email, password, name });
            applySession(data);
            return data.user;
        } catch (e) {
            const msg = apiError(e);
            setError(msg);
            throw new Error(msg);
        }
    }, [applySession]);

    const completeGoogleCallback = useCallback(async (sessionId) => {
        setError(null);
        try {
            const { data } = await api.post("/auth/google/callback", { session_id: sessionId });
            applySession(data);
            return data.user;
        } catch (e) {
            const msg = apiError(e);
            setError(msg);
            throw new Error(msg);
        }
    }, [applySession]);

    const signOut = useCallback(() => {
        setToken(null);
        setUser(null);
    }, []);

    const refreshMe = useCallback(async () => {
        const { data } = await api.get("/auth/me");
        setUser(data);
        return data;
    }, []);

    const value = useMemo(
        () => ({
            user,
            token,
            status,
            error,
            isAuthenticated: Boolean(token && user),
            signIn,
            signUp,
            signOut,
            completeGoogleCallback,
            refreshMe,
        }),
        [user, token, status, error, signIn, signUp, signOut, completeGoogleCallback, refreshMe]
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
    return ctx;
};
