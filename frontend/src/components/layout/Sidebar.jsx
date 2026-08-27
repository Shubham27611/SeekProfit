import { NavLink } from "react-router-dom";
import { CaretRight } from "@phosphor-icons/react";
import { NAV_SECTIONS } from "@/config/navigation";
import { SHELL } from "@/constants/testIds";
import { cn } from "@/lib/utils";

const Brand = () => (
    <div
        data-testid={SHELL.sidebarBrand}
        className="flex items-center gap-2 px-6 pt-6"
    >
        <span className="inline-block h-2 w-2 rounded-full bg-primary" />
        <span className="font-heading text-base font-semibold tracking-tight text-foreground">
            SeekProfit
        </span>
    </div>
);

const NavGroup = ({ section, onNavigate }) => (
    <div className="px-3">
        <p className="px-3 pb-2 pt-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground/80">
            {section.label}
        </p>
        <ul className="space-y-0.5">
            {section.items.map((item) => {
                const Icon = item.icon;
                return (
                    <li key={item.slug}>
                        <NavLink
                            to={item.path}
                            end
                            onClick={onNavigate}
                            data-testid={SHELL.navItem(item.slug)}
                            className={({ isActive }) =>
                                cn(
                                    "group flex items-center justify-between gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                                    isActive
                                        ? "bg-accent text-foreground"
                                        : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                                )
                            }
                        >
                            {({ isActive }) => (
                                <>
                                    <span className="flex items-center gap-3">
                                        <Icon
                                            size={16}
                                            weight={isActive ? "fill" : "duotone"}
                                            className={cn(
                                                "shrink-0",
                                                isActive
                                                    ? "text-primary"
                                                    : "text-muted-foreground group-hover:text-foreground"
                                            )}
                                        />
                                        {item.label}
                                    </span>
                                    <CaretRight
                                        size={12}
                                        weight="bold"
                                        className={cn(
                                            "opacity-0 transition-opacity",
                                            isActive
                                                ? "opacity-100 text-primary"
                                                : "group-hover:opacity-60"
                                        )}
                                    />
                                </>
                            )}
                        </NavLink>
                    </li>
                );
            })}
        </ul>
    </div>
);

export const Sidebar = ({ onNavigate }) => {
    return (
        <nav
            data-testid={SHELL.sidebar}
            className="flex h-full w-full flex-col bg-[hsl(240_6%_4%)]"
            aria-label="Primary"
        >
            <Brand />

            <div className="mt-6 flex-1 overflow-y-auto pb-6">
                {NAV_SECTIONS.map((section) => (
                    <NavGroup
                        key={section.id}
                        section={section}
                        onNavigate={onNavigate}
                    />
                ))}
            </div>

            <div className="border-t border-border p-4">
                <div className="rounded-md border border-border bg-card p-3">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                        Foundation build
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                        Modules ship progressively — the shell is production-ready.
                    </p>
                </div>
            </div>
        </nav>
    );
};

export default Sidebar;
