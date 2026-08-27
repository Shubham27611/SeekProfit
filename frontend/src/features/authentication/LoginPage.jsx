import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, LockKey, Sparkle } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/features/authentication/AuthContext";
import { AUTH } from "@/constants/testIds";

export const LoginPage = () => {
    const { signIn } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [mode, setMode] = useState("signin"); // signin | signup

    const redirectTo = location.state?.from || "/app/overview";

    const handleSubmit = (e) => {
        e.preventDefault();
        signIn({ email: email || "demo@seekprofit.app" });
        navigate(redirectTo, { replace: true });
    };

    const handleDemo = () => {
        signIn({ email: "demo@seekprofit.app" });
        navigate("/app/overview", { replace: true });
    };

    return (
        <div className="relative min-h-screen bg-background">
            <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[1.05fr_1fr]">
                {/* Left — brand panel */}
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
                            SeekProfit surfaces profit leaks, revenue recovery
                            opportunities and high-impact actions across your
                            financial data — with the rigor of an analyst and
                            the speed of software.
                        </p>
                    </div>

                    <div className="relative z-10 grid grid-cols-3 gap-6 border-t border-border pt-8">
                        {[
                            { k: "Recovered", v: "$1.2M" },
                            { k: "Anomalies", v: "384" },
                            { k: "Actions", v: "27" },
                        ].map((s) => (
                            <div key={s.k}>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                    {s.k}
                                </p>
                                <p className="mt-1 font-mono text-lg font-medium tracking-tight text-foreground">
                                    {s.v}
                                </p>
                            </div>
                        ))}
                    </div>
                </aside>

                {/* Right — form */}
                <main className="flex items-center justify-center p-6 md:p-12">
                    <div className="w-full max-w-sm">
                        <div className="mb-8 flex items-center gap-2 lg:hidden">
                            <span className="inline-block h-2 w-2 rounded-full bg-primary" />
                            <span className="font-heading text-lg font-semibold tracking-tight text-foreground">
                                SeekProfit
                            </span>
                        </div>

                        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                            {mode === "signin" ? "Welcome back" : "Get started"}
                        </p>
                        <h2 className="mt-2 font-heading text-3xl font-medium tracking-tight text-foreground">
                            {mode === "signin"
                                ? "Sign in to your workspace"
                                : "Create your workspace"}
                        </h2>
                        <p className="mt-2 text-sm text-muted-foreground">
                            Use any email to explore the foundation shell. Real
                            authentication ships in Stage 2.
                        </p>

                        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
                            <div className="space-y-2">
                                <Label
                                    htmlFor="email"
                                    className="text-xs font-medium text-muted-foreground"
                                >
                                    Work email
                                </Label>
                                <Input
                                    id="email"
                                    type="email"
                                    autoComplete="email"
                                    placeholder="you@company.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    data-testid={AUTH.emailInput}
                                    className="h-11 border-border bg-card"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label
                                    htmlFor="password"
                                    className="text-xs font-medium text-muted-foreground"
                                >
                                    Password
                                </Label>
                                <Input
                                    id="password"
                                    type="password"
                                    autoComplete={
                                        mode === "signin"
                                            ? "current-password"
                                            : "new-password"
                                    }
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) =>
                                        setPassword(e.target.value)
                                    }
                                    data-testid={AUTH.passwordInput}
                                    className="h-11 border-border bg-card"
                                />
                            </div>

                            <Button
                                type="submit"
                                data-testid={AUTH.submitButton}
                                className="h-11 w-full bg-primary text-primary-foreground hover:bg-primary/90"
                            >
                                {mode === "signin" ? "Sign in" : "Create workspace"}
                                <ArrowRight size={16} weight="bold" />
                            </Button>

                            <Button
                                type="button"
                                variant="outline"
                                onClick={handleDemo}
                                data-testid={AUTH.demoLoginButton}
                                className="h-11 w-full border-border bg-transparent hover:bg-accent"
                            >
                                <LockKey size={16} weight="duotone" />
                                Continue as demo operator
                            </Button>
                        </form>

                        <p className="mt-6 text-center text-xs text-muted-foreground">
                            {mode === "signin"
                                ? "New to SeekProfit?"
                                : "Already have an account?"}{" "}
                            <button
                                type="button"
                                data-testid={AUTH.switchModeButton}
                                onClick={() =>
                                    setMode((m) =>
                                        m === "signin" ? "signup" : "signin"
                                    )
                                }
                                className="font-medium text-primary hover:underline"
                            >
                                {mode === "signin"
                                    ? "Create a workspace"
                                    : "Sign in instead"}
                            </button>
                        </p>
                    </div>
                </main>
            </div>
        </div>
    );
};

export default LoginPage;
