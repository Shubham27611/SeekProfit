import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import {
    Sheet,
    SheetContent,
    SheetTitle,
} from "@/components/ui/sheet";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { SHELL } from "@/constants/testIds";

export const AppShell = () => {
    const [mobileOpen, setMobileOpen] = useState(false);
    const location = useLocation();

    // Close the mobile sheet whenever the user navigates.
    useEffect(() => {
        setMobileOpen(false);
    }, [location.pathname]);

    return (
        <div
            data-testid={SHELL.root}
            className="flex min-h-screen bg-background text-foreground"
        >
            {/* Desktop sidebar */}
            <aside className="hidden w-64 shrink-0 border-r border-border lg:block">
                <div className="sticky top-0 h-screen">
                    <Sidebar />
                </div>
            </aside>

            {/* Mobile sidebar */}
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
                <SheetContent
                    side="left"
                    data-testid={SHELL.mobileNav}
                    className="w-72 border-r border-border bg-[hsl(240_6%_4%)] p-0"
                >
                    <SheetTitle className="sr-only">Navigation</SheetTitle>
                    <Sidebar onNavigate={() => setMobileOpen(false)} />
                </SheetContent>
            </Sheet>

            <div className="flex min-w-0 flex-1 flex-col">
                <Header onOpenMobileNav={() => setMobileOpen(true)} />
                <main
                    data-testid={SHELL.mainContent}
                    className="flex-1 px-4 py-6 md:px-8 md:py-10"
                >
                    <div className="mx-auto w-full max-w-7xl">
                        <Outlet />
                    </div>
                </main>
            </div>
        </div>
    );
};

export default AppShell;
