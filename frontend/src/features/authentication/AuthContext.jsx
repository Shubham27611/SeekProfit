import { createContext, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "seekprofit.auth";

const AuthContext = createContext(null);

// Foundation-stage auth: a lightweight, purely client-side identity model.
// Real credential-backed authentication will be layered in during Stage 2 via
// the platform's auth integration playbook.
export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(() => {
        try {
            const raw = window.localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    });

    useEffect(() => {
        try {
            if (user) {
                window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
            } else {
                window.localStorage.removeItem(STORAGE_KEY);
            }
        } catch {
            /* ignore storage errors */
        }
    }, [user]);

    const value = useMemo(
        () => ({
            user,
            isAuthenticated: Boolean(user),
            signIn: ({ email }) => {
                const name = email
                    ? email.split("@")[0].replace(/[._-]+/g, " ")
                    : "Operator";
                const workspace = "Acme Financials";
                setUser({
                    email: email || "demo@seekprofit.app",
                    name: name
                        .split(" ")
                        .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
                        .join(" "),
                    workspace,
                });
            },
            signOut: () => setUser(null),
        }),
        [user]
    );

    return (
        <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
    );
};

export const useAuth = () => {
    const ctx = useContext(AuthContext);
    if (!ctx) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return ctx;
};
