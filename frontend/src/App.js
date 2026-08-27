import { useEffect } from "react";
import {
    BrowserRouter,
    Routes,
    Route,
    Navigate,
    useLocation,
} from "react-router-dom";
import "@/App.css";

import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/features/authentication/AuthContext";
import { LoginPage } from "@/features/authentication/LoginPage";
import { AuthCallbackPage } from "@/features/authentication/AuthCallbackPage";
import { AppShell } from "@/components/layout/AppShell";

import { OnboardingPage } from "@/features/onboarding/OnboardingPage";
import { OverviewPage } from "@/features/overview/OverviewPage";
import { RevenueRecoveryPage } from "@/features/revenue-recovery/RevenueRecoveryPage";
import { ProfitLeaksPage } from "@/features/profit-leaks/ProfitLeaksPage";
import { OpportunitiesPage } from "@/features/opportunities/OpportunitiesPage";
import { ActionCenterPage } from "@/features/action-center/ActionCenterPage";
import { DataSourcesPage } from "@/features/data-sources/DataSourcesPage";
import { ImportsPage } from "@/features/imports/ImportsPage";
import { AIAnalysisPage } from "@/features/ai-analysis/AIAnalysisPage";
import { ReportsPage } from "@/features/reports/ReportsPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { NotFoundPage } from "@/features/system/NotFoundPage";

const ScrollToTop = () => {
    const { pathname } = useLocation();
    useEffect(() => {
        window.scrollTo({ top: 0, behavior: "instant" });
    }, [pathname]);
    return null;
};

const DarkModeBoot = () => {
    useEffect(() => {
        document.documentElement.classList.add("dark");
    }, []);
    return null;
};

const RequireAuth = ({ children }) => {
    const { isAuthenticated, status } = useAuth();
    const location = useLocation();
    if (status === "checking") {
        return <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">Loading…</div>;
    }
    if (!isAuthenticated) {
        return <Navigate to="/login" replace state={{ from: location.pathname }} />;
    }
    return children;
};

const RequireOnboardedWorkspace = ({ children }) => {
    const { user } = useAuth();
    // Owner + industry not set → send to onboarding.
    const industry = user?.workspace?.industry;
    if (!industry) {
        return <Navigate to="/onboarding" replace />;
    }
    return children;
};

const RedirectIfAuthed = ({ children }) => {
    const { isAuthenticated, user, status } = useAuth();
    if (status === "checking") {
        return <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">Loading…</div>;
    }
    if (isAuthenticated) {
        const setupDone = Boolean(user?.workspace?.industry);
        return <Navigate to={setupDone ? "/app/overview" : "/onboarding"} replace />;
    }
    return children;
};

function App() {
    return (
        <div className="App min-h-screen bg-background text-foreground antialiased">
            <BrowserRouter>
                <AuthProvider>
                    <DarkModeBoot />
                    <ScrollToTop />
                    <Routes>
                        <Route path="/" element={<Navigate to="/app/overview" replace />} />
                        <Route
                            path="/login"
                            element={
                                <RedirectIfAuthed>
                                    <LoginPage />
                                </RedirectIfAuthed>
                            }
                        />
                        <Route path="/auth/callback" element={<AuthCallbackPage />} />

                        <Route
                            path="/onboarding"
                            element={
                                <RequireAuth>
                                    <OnboardingPage />
                                </RequireAuth>
                            }
                        />

                        <Route
                            path="/app"
                            element={
                                <RequireAuth>
                                    <RequireOnboardedWorkspace>
                                        <AppShell />
                                    </RequireOnboardedWorkspace>
                                </RequireAuth>
                            }
                        >
                            <Route index element={<Navigate to="overview" replace />} />
                            <Route path="overview" element={<OverviewPage />} />
                            <Route path="revenue-recovery" element={<RevenueRecoveryPage />} />
                            <Route path="profit-leaks" element={<ProfitLeaksPage />} />
                            <Route path="opportunities" element={<OpportunitiesPage />} />
                            <Route path="action-center" element={<ActionCenterPage />} />
                            <Route path="data-sources" element={<DataSourcesPage />} />
                            <Route path="imports" element={<ImportsPage />} />
                            <Route path="ai-analysis" element={<AIAnalysisPage />} />
                            <Route path="reports" element={<ReportsPage />} />
                            <Route path="settings" element={<SettingsPage />} />
                        </Route>

                        <Route path="*" element={<NotFoundPage />} />
                    </Routes>
                    <Toaster theme="dark" richColors position="top-right" />
                </AuthProvider>
            </BrowserRouter>
        </div>
    );
}

export default App;
