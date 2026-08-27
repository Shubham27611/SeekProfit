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
import { AuthProvider } from "@/features/authentication/AuthContext";
import { RequireAuth } from "@/features/authentication/RequireAuth";
import { LoginPage } from "@/features/authentication/LoginPage";
import { AppShell } from "@/components/layout/AppShell";

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
    // Ensure the dark theme is always applied at the html root regardless of
    // system preference. SeekProfit is dark-first by design.
    useEffect(() => {
        document.documentElement.classList.add("dark");
    }, []);
    return null;
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
                        <Route path="/login" element={<LoginPage />} />

                        <Route
                            path="/app"
                            element={
                                <RequireAuth>
                                    <AppShell />
                                </RequireAuth>
                            }
                        >
                            <Route index element={<Navigate to="overview" replace />} />
                            <Route path="overview" element={<OverviewPage />} />
                            <Route
                                path="revenue-recovery"
                                element={<RevenueRecoveryPage />}
                            />
                            <Route path="profit-leaks" element={<ProfitLeaksPage />} />
                            <Route
                                path="opportunities"
                                element={<OpportunitiesPage />}
                            />
                            <Route
                                path="action-center"
                                element={<ActionCenterPage />}
                            />
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
