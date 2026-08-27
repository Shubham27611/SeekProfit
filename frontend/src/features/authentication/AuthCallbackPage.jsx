import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/features/authentication/AuthContext";
import { CircleNotch, WarningCircle } from "@phosphor-icons/react";

/**
 * Handles the return from Emergent Google Auth. Reads `session_id` from the
 * URL fragment, exchanges it via /api/auth/google/callback and redirects the
 * user to onboarding (first sign-in) or the app.
 */
export const AuthCallbackPage = () => {
    const { completeGoogleCallback } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [error, setError] = useState(null);
    const processed = useRef(false);

    useEffect(() => {
        if (processed.current) return;
        processed.current = true;

        const hash = location.hash || window.location.hash;
        const match = hash?.match(/session_id=([^&]+)/);
        const sessionId = match ? decodeURIComponent(match[1]) : null;
        if (!sessionId) {
            setError("Missing sign-in token. Please try signing in again.");
            return;
        }
        (async () => {
            try {
                const user = await completeGoogleCallback(sessionId);
                // Clear the hash to keep the URL clean
                window.history.replaceState({}, "", "/auth/callback");
                const setupDone = Boolean(user?.workspace?.industry);
                navigate(setupDone ? "/app/overview" : "/onboarding", { replace: true });
            } catch (e) {
                setError(e.message || "Google sign-in failed.");
            }
        })();
    }, [completeGoogleCallback, location.hash, navigate]);

    return (
        <div className="flex min-h-screen items-center justify-center bg-background px-6">
            <div className="w-full max-w-sm rounded-md border border-border bg-card p-8 text-center">
                {error ? (
                    <>
                        <WarningCircle size={28} weight="duotone" className="mx-auto mb-3 text-destructive" />
                        <h1 className="font-heading text-lg font-medium text-foreground">Sign-in error</h1>
                        <p className="mt-2 text-sm text-muted-foreground">{error}</p>
                        <button
                            onClick={() => navigate("/login", { replace: true })}
                            data-testid="auth-callback-retry"
                            className="mt-4 rounded-md border border-border bg-transparent px-3 py-1.5 text-xs font-medium text-foreground hover:bg-accent"
                        >
                            Back to sign in
                        </button>
                    </>
                ) : (
                    <>
                        <CircleNotch size={28} weight="bold" className="mx-auto mb-3 animate-spin text-primary" />
                        <h1 className="font-heading text-lg font-medium text-foreground">Finishing sign-in…</h1>
                        <p className="mt-2 text-sm text-muted-foreground">
                            Securely establishing your SeekProfit session.
                        </p>
                    </>
                )}
            </div>
        </div>
    );
};

export default AuthCallbackPage;
