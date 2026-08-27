import { useState } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { ArrowRight, GoogleLogo, Sparkle } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { useAuth } from "@/features/authentication/AuthContext";
import { AUTH } from "@/constants/testIds";

export const LoginPage = () => {
    const { signIn, signUp } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [mode, setMode] = useState("signin");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [name, setName] = useState("");
    const [busy, setBusy] = useState(false);
    const [errMsg, setErrMsg] = useState("");

    const redirectTo = location.state?.from || "/app/overview";

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (busy) return;
        setBusy(true);
        setErrMsg("");
        try {
            const user = mode === "signin"
                ? await signIn({ email, password })
                : await signUp({ email, password, name });
            // If workspace isn't set up yet, land in onboarding.
            const setupDone = Boolean(user?.workspace?.industry);
            navigate(setupDone ? redirectTo : "/onboarding", { replace: true });
        } catch (err) {
            setErrMsg(err.message);
            toast.error(err.message);
        } finally {
            setBusy(false);
        }
    };

    const handleGoogle = () => {
        // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
        const redirectUrl = window.location.origin + "/auth/callback";
        window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
    };

    return (
        <div className="relative min-h-screen bg-background">
            <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[1.05fr_1fr]">
                <aside className="relative hidden overflow-hidden border-r border-border lg:flex lg:flex-col lg:justify-between lg:p-12">
                    <div className="sp-grid-bg pointer-events-none absolute inset-0 opacity-40" />
                    <div className="pointer-events-none absolute -left-24 top-1/3 h-72 w-72 rounded-full bg-primary/10 blur-3xl" />

                    <div className="relative z-10 flex items-center gap-2">
                        <span className="inline-block h-2 w-2 rounded-full bg-primary" />
                        <span className="font-heading text-lg font-semibold tracking-tight text-foreground">
                            SeekProfit
                        </span>
                    </div>

                    <div className="relative z-10 max-w-md space-y-6">
                        <p className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-primary">
                            <Sparkle size={12} weight="fill" />
                            Financial intelligence
                        </p>
                        <h1 className="font-heading text-4xl font-medium leading-tight tracking-tight text-foreground md:text-[44px]">
                            Find the money your business is missing.
                        </h1>
                        <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
                            SeekProfit surfaces profit leaks, revenue recovery opportunities and high-impact actions across your financial data — with the rigor of an analyst and the speed of software.
                        </p>
                    </div>

                    <div className="relative z-10 grid grid-cols-3 gap-6 border-t border-border pt-8">
                        <div>
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Grounded</p>
                            <p className="mt-1 text-sm font-medium text-foreground">Every finding cites source records</p>
                        </div>
                        <div>
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Deterministic</p>
                            <p className="mt-1 text-sm font-medium text-foreground">Financial math never hallucinates</p>
                        </div>
                        <div>
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Actionable</p>
                            <p className="mt-1 text-sm font-medium text-foreground">Every signal has an owned next step</p>
                        </div>
                    </div>
                </aside>

                <main className="flex items-center justify-center p-6 md:p-12">
                    <div className="w-full max-w-sm">
                        <div className="mb-8 flex items-center gap-2 lg:hidden">
                            <span className="inline-block h-2 w-2 rounded-full bg-primary" />
                            <span className="font-heading text-lg font-semibold tracking-tight text-foreground">SeekProfit</span>
                        </div>

                        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                            {mode === "signin" ? "Welcome back" : "Create your account"}
                        </p>
                        <h2 className="mt-2 font-heading text-3xl font-medium tracking-tight text-foreground">
                            {mode === "signin" ? "Sign in to SeekProfit" : "Start finding missing money"}
                        </h2>
                        <p className="mt-2 text-sm text-muted-foreground">
                            {mode === "signin"
                                ? "Use your email and password, or continue with Google."
                                : "60 seconds to your first insight — with a seeded demo dataset ready to explore."}
                        </p>

                        <div className="mt-6">
                            <Button
                                type="button"
                                variant="outline"
                                onClick={handleGoogle}
                                data-testid={AUTH.ssoButton}
                                className="h-11 w-full border-border bg-transparent hover:bg-accent"
                            >
                                <GoogleLogo size={16} weight="duotone" />
                                Continue with Google
                            </Button>
                        </div>

                        <div className="my-6 flex items-center gap-3 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                            <span className="h-px flex-1 bg-border" />
                            or with email
                            <span className="h-px flex-1 bg-border" />
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            {mode === "signup" && (
                                <div className="space-y-2">
                                    <Label htmlFor="name" className="text-xs font-medium text-muted-foreground">Full name</Label>
                                    <Input
                                        id="name"
                                        placeholder="Alex Morgan"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        data-testid="auth-name-input"
                                        className="h-11 border-border bg-card"
                                        autoComplete="name"
                                    />
                                </div>
                            )}
                            <div className="space-y-2">
                                <Label htmlFor="email" className="text-xs font-medium text-muted-foreground">Work email</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    required
                                    autoComplete="email"
                                    placeholder="you@company.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    data-testid={AUTH.emailInput}
                                    className="h-11 border-border bg-card"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="password" className="text-xs font-medium text-muted-foreground">Password</Label>
                                <Input
                                    id="password"
                                    type="password"
                                    required
                                    minLength={6}
                                    autoComplete={mode === "signin" ? "current-password" : "new-password"}
                                    placeholder="At least 6 characters"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    data-testid={AUTH.passwordInput}
                                    className="h-11 border-border bg-card"
                                />
                            </div>

                            {errMsg && (
                                <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                                    {errMsg}
                                </p>
                            )}

                            <Button
                                type="submit"
                                disabled={busy}
                                data-testid={AUTH.submitButton}
                                className="h-11 w-full bg-primary text-primary-foreground hover:bg-primary/90"
                            >
                                {busy ? "Working…" : mode === "signin" ? "Sign in" : "Create account"}
                                <ArrowRight size={16} weight="bold" />
                            </Button>
                        </form>

                        <p className="mt-6 text-center text-xs text-muted-foreground">
                            {mode === "signin" ? "New to SeekProfit?" : "Already have an account?"}{" "}
                            <button
                                type="button"
                                data-testid={AUTH.switchModeButton}
                                onClick={() => { setMode((m) => (m === "signin" ? "signup" : "signin")); setErrMsg(""); }}
                                className="font-medium text-primary hover:underline"
                            >
                                {mode === "signin" ? "Create an account" : "Sign in instead"}
                            </button>
                        </p>
                    </div>
                </main>
            </div>
        </div>
    );
};

export default LoginPage;
