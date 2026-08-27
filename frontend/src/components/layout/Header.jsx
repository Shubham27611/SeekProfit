import { useNavigate } from "react-router-dom";
import { List, MagnifyingGlass, Bell, SignOut, User } from "@phosphor-icons/react";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useAuth } from "@/features/authentication/AuthContext";
import { SHELL } from "@/constants/testIds";

const initialsFor = (name) =>
    (name || "SP")
        .split(" ")
        .map((p) => p.charAt(0).toUpperCase())
        .slice(0, 2)
        .join("");

export const Header = ({ onOpenMobileNav, avatarUrl }) => {
    const { user, signOut } = useAuth();
    const navigate = useNavigate();

    const handleSignOut = () => {
        signOut();
        navigate("/login", { replace: true });
    };

    return (
        <header
            data-testid={SHELL.header}
            className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-background/90 px-4 backdrop-blur-md md:px-6"
        >
            <Button
                variant="ghost"
                size="icon"
                onClick={onOpenMobileNav}
                data-testid={SHELL.mobileMenuButton}
                className="text-muted-foreground hover:bg-accent hover:text-foreground lg:hidden"
                aria-label="Open navigation"
            >
                <List size={18} weight="bold" />
            </Button>

            <div
                data-testid={SHELL.workspaceSwitcher}
                className="hidden items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground md:flex"
            >
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary" />
                <span className="font-medium text-foreground">
                    {user?.workspace || "Acme Financials"}
                </span>
                <span className="text-muted-foreground/70">/ Production</span>
            </div>

            <div className="ml-auto flex flex-1 items-center justify-end gap-2">
                <div className="relative hidden w-full max-w-xs md:block">
                    <MagnifyingGlass
                        size={14}
                        weight="bold"
                        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                    />
                    <Input
                        placeholder="Search anomalies, accounts, actions…"
                        data-testid={SHELL.searchInput}
                        className="h-9 border-border bg-card pl-8 text-sm placeholder:text-muted-foreground/70"
                    />
                </div>

                <Button
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:bg-accent hover:text-foreground"
                    aria-label="Notifications"
                    data-testid="app-header-notifications"
                >
                    <Bell size={16} weight="duotone" />
                </Button>

                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <button
                            data-testid={SHELL.userMenuTrigger}
                            className="flex items-center gap-2 rounded-md border border-border bg-card px-2 py-1 text-left text-sm hover:bg-accent"
                        >
                            <Avatar className="h-6 w-6">
                                {avatarUrl ? (
                                    <AvatarImage src={avatarUrl} alt="" />
                                ) : null}
                                <AvatarFallback className="bg-primary/15 text-[10px] font-medium text-primary">
                                    {initialsFor(user?.name)}
                                </AvatarFallback>
                            </Avatar>
                            <span className="hidden text-xs font-medium text-foreground md:inline">
                                {user?.name || "Operator"}
                            </span>
                        </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                        align="end"
                        data-testid={SHELL.userMenu}
                        className="w-56 border-border bg-popover"
                    >
                        <DropdownMenuLabel className="text-xs font-medium text-muted-foreground">
                            {user?.email || "demo@seekprofit.app"}
                        </DropdownMenuLabel>
                        <DropdownMenuSeparator className="bg-border" />
                        <DropdownMenuItem
                            onSelect={() => navigate("/app/settings")}
                            className="cursor-pointer"
                        >
                            <User size={14} weight="duotone" />
                            Account settings
                        </DropdownMenuItem>
                        <DropdownMenuSeparator className="bg-border" />
                        <DropdownMenuItem
                            onSelect={handleSignOut}
                            data-testid={SHELL.logoutMenuItem}
                            className="cursor-pointer text-rose-400 focus:text-rose-400"
                        >
                            <SignOut size={14} weight="duotone" />
                            Sign out
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </header>
    );
};

export default Header;
