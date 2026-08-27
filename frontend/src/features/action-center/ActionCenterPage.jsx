import { useEffect, useState, Fragment } from "react";
import {
    Target,
    User,
    Calendar,
    Warning,
    CircleNotch,
    Check,
    ArrowUpRight,
    X,
    Clock,
} from "@phosphor-icons/react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import api, { apiError } from "@/lib/api";
import { useAuth } from "@/features/authentication/AuthContext";
import { PAGE } from "@/constants/testIds";
import { cn } from "@/lib/utils";

const CATEGORY_TONE = {
    revenue_recovery: "border-amber-500/25 bg-amber-500/10 text-amber-400",
    profit_leak: "border-rose-500/25 bg-rose-500/10 text-rose-400",
    opportunity: "border-emerald-500/25 bg-emerald-500/10 text-emerald-400",
};

const URGENCY_TONE = {
    high: "border-rose-500/25 bg-rose-500/10 text-rose-400",
    medium: "border-amber-500/25 bg-amber-500/10 text-amber-400",
    low: "border-border bg-muted text-muted-foreground",
};

const SLA_LABEL = {
    overdue: { label: "Overdue", cls: "border-rose-500/30 bg-rose-500/15 text-rose-400" },
    due_soon: { label: "Due soon", cls: "border-amber-500/30 bg-amber-500/15 text-amber-400" },
    on_track: { label: "On track", cls: "border-emerald-500/25 bg-emerald-500/10 text-emerald-400" },
};

const FILTERS = [
    { id: "queue", label: "Queue", params: { status: "open" } },
    { id: "in_progress", label: "In progress", params: { status: "in_progress" } },
    { id: "mine", label: "Assigned to me", params: { owner: "me" } },
    { id: "resolved", label: "Resolved", params: { status: "resolved" } },
];

const fmtDate = (iso) =>
    iso ? new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "—";

const daysUntil = (iso) => {
    if (!iso) return null;
    const d = new Date(iso).getTime() - Date.now();
    return Math.round(d / 86_400_000);
};

const AssignMenu = ({ signal, members, onAssigned }) => {
    const handle = async (email) => {
        try {
            await api.post(`/signals/${signal.signal_id}/assign`, {
                owner_email: email || null,
            });
            toast.success(email ? `Assigned to ${email}.` : "Unassigned.");
            onAssigned?.();
        } catch (e) {
            toast.error(apiError(e));
        }
    };
    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <button
                    type="button"
                    data-testid={`action-assign-${signal.signal_id}`}
                    className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2 py-1 text-xs text-foreground hover:bg-accent"
                >
                    <User size={12} weight="duotone" />
                    {signal.owner_email ? signal.owner_email.split("@")[0] : "Assign"}
                </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56 border-border bg-popover">
                <DropdownMenuLabel className="text-xs">Assign owner</DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-border" />
                {members.map((m) => (
                    <DropdownMenuItem
                        key={m.email}
                        onSelect={() => handle(m.email)}
                        data-testid={`action-assign-option-${m.email}`}
                        className="cursor-pointer text-xs"
                    >
                        <User size={12} weight="duotone" />
                        <span className="truncate">{m.email}</span>
                        <span className="ml-auto text-[10px] uppercase text-muted-foreground">{m.role}</span>
                    </DropdownMenuItem>
                ))}
                {signal.owner_email && (
                    <>
                        <DropdownMenuSeparator className="bg-border" />
                        <DropdownMenuItem
                            onSelect={() => handle(null)}
                            data-testid={`action-unassign-${signal.signal_id}`}
                            className="cursor-pointer text-xs text-muted-foreground"
                        >
                            <X size={12} weight="bold" />
                            Unassign
                        </DropdownMenuItem>
                    </>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
};

const StatusButtons = ({ signal, onChanged }) => {
    const [busy, setBusy] = useState(false);
    const doStatus = async (next) => {
        setBusy(true);
        try {
            await api.post(`/signals/${signal.signal_id}/status`, { status: next });
            toast.success(next === "resolved" ? "Marked resolved." : "Signal dismissed.");
            onChanged?.();
        } catch (e) {
            toast.error(apiError(e));
        } finally {
            setBusy(false);
        }
    };
    if (signal.status === "resolved" || signal.status === "dismissed") {
        return null;
    }
    return (
        <div className="flex items-center gap-1">
            <button
                type="button"
                onClick={() => doStatus("resolved")}
                disabled={busy}
                data-testid={`action-resolve-${signal.signal_id}`}
                className="inline-flex items-center gap-1 rounded-md border border-primary/30 bg-primary/10 px-2 py-1 text-xs font-medium text-primary hover:bg-primary/20"
            >
                <Check size={12} weight="bold" />
                Resolve
            </button>
            <button
                type="button"
                onClick={() => doStatus("dismissed")}
                disabled={busy}
                data-testid={`action-dismiss-${signal.signal_id}`}
                className="inline-flex items-center rounded-md border border-border bg-transparent px-2 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
            >
                <X size={12} weight="bold" />
            </button>
        </div>
    );
};

export const ActionCenterPage = () => {
    const { user } = useAuth();
    const [tab, setTab] = useState("queue");
    const [signals, setSignals] = useState([]);
    const [members, setMembers] = useState([]);
    const [status, setStatus] = useState("loading");
    const [errMsg, setErrMsg] = useState("");
    const [expanded, setExpanded] = useState(null);

    const load = async () => {
        setStatus("loading");
        try {
            const filter = FILTERS.find((f) => f.id === tab)?.params || {};
            const [{ data: sigData }, { data: memData }] = await Promise.all([
                api.get("/signals", { params: { ...filter, limit: 100 } }),
                api.get("/signals/members"),
            ]);
            setSignals(sigData.signals);
            setMembers(memData.members);
            setStatus("ready");
        } catch (e) {
            setErrMsg(apiError(e));
            setStatus("error");
        }
    };

    useEffect(() => {
        load();
    }, [tab]); // eslint-disable-line react-hooks/exhaustive-deps

    // Compute stat strip from current view.
    const stat = {
        total: signals.length,
        overdue: signals.filter((s) => s.sla_status === "overdue").length,
        due_soon: signals.filter((s) => s.sla_status === "due_soon").length,
        mine: signals.filter((s) => s.owner_email === user?.email).length,
    };

    return (
        <div data-testid={PAGE.actionCenter} className="sp-fade-in space-y-8">
            <PageHeader
                eyebrow="Workspace"
                title="Action Center"
                description="One queue for every open finding. Assign an owner, set a due date, and close the loop with impact captured at resolution."
            />

            <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {[
                    { k: "In view", v: stat.total, icon: Target, tone: "text-foreground" },
                    { k: "Overdue", v: stat.overdue, icon: Warning, tone: "text-rose-400" },
                    { k: "Due soon", v: stat.due_soon, icon: Clock, tone: "text-amber-400" },
                    { k: "Assigned to me", v: stat.mine, icon: User, tone: "text-primary" },
                ].map((s) => (
                    <div key={s.k} className="rounded-md border border-border bg-card p-4">
                        <div className="flex items-center justify-between">
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{s.k}</p>
                            <s.icon size={14} weight="duotone" className={s.tone} />
                        </div>
                        <p className="mt-3 font-mono text-2xl font-medium tracking-tight text-foreground">{s.v}</p>
                    </div>
                ))}
            </section>

            <SectionCard
                title="Signal queue"
                description="Ordered by Impact × Confidence × Urgency"
                actions={
                    <Tabs value={tab} onValueChange={setTab}>
                        <TabsList className="flex flex-wrap gap-1 bg-background sm:flex-nowrap">
                            {FILTERS.map((f) => (
                                <TabsTrigger
                                    key={f.id}
                                    value={f.id}
                                    data-testid={`action-tab-${f.id}`}
                                    className="text-xs data-[state=active]:bg-accent"
                                >
                                    {f.label}
                                </TabsTrigger>
                            ))}
                        </TabsList>
                    </Tabs>
                }
                bodyClassName="p-0"
            >
                {status === "loading" && <div className="p-5"><LoadingState rows={5} /></div>}
                {status === "error" && (
                    <div className="p-5">
                        <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                            {errMsg}
                        </p>
                    </div>
                )}
                {status === "ready" && signals.length === 0 && (
                    <div className="p-5">
                        <EmptyState
                            icon={Target}
                            title="Nothing in this queue"
                            description="Nothing matches this filter — try another tab or refresh from AI Analysis."
                            testId="action-empty"
                        />
                    </div>
                )}
                {status === "ready" && signals.length > 0 && (
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[900px] border-collapse text-left text-sm">
                            <thead>
                                <tr className="border-b border-border text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                    <th className="px-5 py-3">Signal</th>
                                    <th className="px-3 py-3">Category</th>
                                    <th className="px-3 py-3">Urgency</th>
                                    <th className="px-3 py-3 text-right">Impact</th>
                                    <th className="px-3 py-3">Owner</th>
                                    <th className="px-3 py-3">Due</th>
                                    <th className="px-3 py-3 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {signals.map((s) => {
                                    const isOpen = expanded === s.signal_id;
                                    const sla = SLA_LABEL[s.sla_status];
                                    const daysLeft = daysUntil(s.due_date);
                                    return (
                                        <Fragment key={s.signal_id}>
                                            <tr
                                                data-testid={`action-row-${s.signal_id}`}
                                                className={cn(
                                                    "border-b border-border transition-colors hover:bg-accent/30",
                                                    isOpen && "bg-accent/20"
                                                )}
                                            >
                                                <td className="px-5 py-3">
                                                    <button
                                                        type="button"
                                                        onClick={() => setExpanded(isOpen ? null : s.signal_id)}
                                                        data-testid={`action-expand-${s.signal_id}`}
                                                        className="text-left"
                                                    >
                                                        <p className="font-medium text-foreground">{s.title}</p>
                                                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                                                            {s.evidence?.length || 0} evidence records
                                                        </p>
                                                    </button>
                                                </td>
                                                <td className="px-3 py-3">
                                                    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium", CATEGORY_TONE[s.category])}>
                                                        {s.category_label}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3">
                                                    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium capitalize", URGENCY_TONE[s.urgency])}>
                                                        {s.urgency}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3 text-right">
                                                    <p className="font-mono text-sm text-foreground">{s.impact_display}</p>
                                                    <p className="text-[10px] uppercase text-muted-foreground">{s.amount_type}</p>
                                                </td>
                                                <td className="px-3 py-3">
                                                    <AssignMenu signal={s} members={members} onAssigned={load} />
                                                </td>
                                                <td className="px-3 py-3">
                                                    {s.due_date ? (
                                                        <div className="flex flex-col gap-1">
                                                            <span className="inline-flex items-center gap-1 font-mono text-xs text-foreground">
                                                                <Calendar size={11} weight="duotone" className="text-muted-foreground" />
                                                                {fmtDate(s.due_date)}
                                                            </span>
                                                            {sla && (
                                                                <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium", sla.cls)}>
                                                                    {sla.label}{daysLeft !== null ? ` · ${daysLeft > 0 ? `${daysLeft}d` : `${Math.abs(daysLeft)}d late`}` : ""}
                                                                </span>
                                                            )}
                                                        </div>
                                                    ) : (
                                                        <span className="text-xs text-muted-foreground">Not set</span>
                                                    )}
                                                </td>
                                                <td className="px-3 py-3">
                                                    <div className="flex items-center justify-end">
                                                        <StatusButtons signal={s} onChanged={load} />
                                                    </div>
                                                </td>
                                            </tr>
                                            {isOpen && (
                                                <tr className="border-b border-border bg-background">
                                                    <td colSpan={7} className="px-5 py-4">
                                                        <div className="grid gap-4 lg:grid-cols-2">
                                                            <div>
                                                                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Explanation</p>
                                                                <p className="mt-2 text-sm leading-relaxed text-foreground">{s.explanation}</p>
                                                            </div>
                                                            <div>
                                                                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-primary">Recommended action</p>
                                                                <p className="mt-2 text-sm leading-relaxed text-foreground">{s.recommended_action}</p>
                                                            </div>
                                                        </div>
                                                        <div className="mt-4 border-t border-border pt-3">
                                                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Evidence · {s.evidence?.length || 0}</p>
                                                            <ul className="mt-2 grid gap-2 md:grid-cols-2">
                                                                {(s.evidence || []).slice(0, 6).map((r) => (
                                                                    <li key={r.record_id} className="flex items-start justify-between gap-3 rounded-md border border-border bg-card px-3 py-2 text-xs">
                                                                        <div className="min-w-0">
                                                                            <p className="truncate text-foreground">
                                                                                <span className="uppercase text-muted-foreground">{r.type}</span> · {r.counterparty}
                                                                            </p>
                                                                            <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{r.memo || r.record_id}</p>
                                                                            <p className="mt-0.5 font-mono text-[10px] text-primary">{r.record_id}</p>
                                                                        </div>
                                                                        <span className="font-mono tabular-nums text-foreground">{r.amount_display}</span>
                                                                    </li>
                                                                ))}
                                                            </ul>
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                        </Fragment>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </SectionCard>
        </div>
    );
};

export default ActionCenterPage;
