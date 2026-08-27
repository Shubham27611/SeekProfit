// Reusable SignalCard renderer used across Overview feed, category pages,
// AI Analysis, and detail views. Handles expansion (evidence + recommended
// action) inline.
import { useState } from "react";
import { CaretDown, ArrowUpRight, Check, X, Sparkle } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import api, { apiError } from "@/lib/api";

const toneClasses = {
    positive: "border-emerald-500/25 bg-emerald-500/10 text-emerald-400",
    warning: "border-amber-500/25 bg-amber-500/10 text-amber-400",
    critical: "border-rose-500/25 bg-rose-500/10 text-rose-400",
};

const amountTypeLabel = {
    measured: "Measured",
    estimated: "Estimated",
    potential: "Potential",
    count: "",
};

const urgencyBadge = {
    high: "bg-rose-500/10 text-rose-400 border-rose-500/25",
    medium: "bg-amber-500/10 text-amber-400 border-amber-500/25",
    low: "bg-muted text-muted-foreground border-border",
};

export const SignalCard = ({ signal, onStatusChange, defaultOpen = false, showActions = true }) => {
    const [open, setOpen] = useState(defaultOpen);
    const [busy, setBusy] = useState(false);
    const [status, setStatus] = useState(signal.status || "open");

    const doUpdate = async (next) => {
        setBusy(true);
        try {
            await api.post(`/signals/${signal.signal_id}/status`, { status: next });
            setStatus(next);
            toast.success(next === "resolved" ? "Marked as resolved." : next === "dismissed" ? "Signal dismissed." : "Signal updated.");
            onStatusChange?.(signal.signal_id, next);
        } catch (e) {
            toast.error(apiError(e));
        } finally {
            setBusy(false);
        }
    };

    const confidencePct = Math.round((signal.confidence || 0) * 100);

    return (
        <article
            data-testid={`signal-card-${signal.signal_id}`}
            className={cn(
                "rounded-md border border-border bg-card transition-colors",
                status === "resolved" && "opacity-70",
                status === "dismissed" && "opacity-50"
            )}
        >
            <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                data-testid={`signal-card-toggle-${signal.signal_id}`}
                className="flex w-full items-start justify-between gap-4 px-5 py-4 text-left hover:bg-accent/30"
            >
                <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className={cn(
                            "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium",
                            toneClasses[signal.tone] || toneClasses.warning
                        )}>
                            {signal.category_label}
                        </span>
                        <span className={cn(
                            "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium capitalize",
                            urgencyBadge[signal.urgency] || urgencyBadge.medium
                        )}>
                            {signal.urgency} urgency
                        </span>
                        {signal.ai_enriched && (
                            <span className="inline-flex items-center gap-1 rounded-full border border-primary/25 bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                                <Sparkle size={9} weight="fill" />
                                AI-enriched
                            </span>
                        )}
                        {status !== "open" && (
                            <span className="inline-flex items-center rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] font-medium capitalize text-muted-foreground">
                                {status.replace("_", " ")}
                            </span>
                        )}
                    </div>
                    <h3 className="mt-2 truncate text-sm font-medium text-foreground">{signal.title}</h3>
                    <div className="mt-1 flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
                        <span>
                            {amountTypeLabel[signal.amount_type] || ""}{" "}
                            <span className="font-mono tabular-nums text-foreground">{signal.impact_display}</span>
                        </span>
                        <span aria-hidden="true">·</span>
                        <span>Confidence <span className="font-mono text-foreground">{confidencePct}%</span></span>
                        <span aria-hidden="true">·</span>
                        <span>Priority <span className="font-mono text-foreground">{(signal.priority_score * 100).toFixed(0)}</span></span>
                    </div>
                </div>
                <CaretDown
                    size={14}
                    weight="bold"
                    className={cn(
                        "mt-1 shrink-0 text-muted-foreground transition-transform",
                        open && "rotate-180"
                    )}
                />
            </button>

            {open && (
                <div className="border-t border-border px-5 py-4">
                    <div className="grid gap-6 lg:grid-cols-5">
                        <div className="lg:col-span-3 space-y-4">
                            <div>
                                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Explanation</p>
                                <p className="mt-2 text-sm leading-relaxed text-foreground">
                                    {signal.explanation}
                                </p>
                            </div>
                            <div>
                                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-primary">Recommended action</p>
                                <p className="mt-2 text-sm leading-relaxed text-foreground">
                                    {signal.recommended_action}
                                </p>
                            </div>
                        </div>

                        <div className="lg:col-span-2">
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                Evidence · {signal.evidence?.length || 0} records
                            </p>
                            <ul className="mt-2 divide-y divide-border rounded-md border border-border">
                                {(signal.evidence || []).slice(0, 6).map((r) => (
                                    <li
                                        key={r.record_id}
                                        data-testid={`signal-evidence-${r.record_id}`}
                                        className="flex items-start justify-between gap-3 px-3 py-2 text-xs"
                                    >
                                        <div className="min-w-0">
                                            <p className="truncate text-foreground">
                                                <span className="text-muted-foreground uppercase">{r.type}</span>{" "}
                                                · {r.counterparty}
                                            </p>
                                            <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
                                                {r.memo || r.record_id}
                                            </p>
                                            <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                                                {r.record_id} · {new Date(r.date).toLocaleDateString()}
                                            </p>
                                        </div>
                                        <span className="shrink-0 font-mono text-xs tabular-nums text-foreground">
                                            {r.amount_display}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    {showActions && status === "open" && (
                        <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-border pt-4">
                            <Button
                                size="sm"
                                onClick={() => doUpdate("resolved")}
                                disabled={busy}
                                data-testid={`signal-resolve-${signal.signal_id}`}
                                className="bg-primary text-primary-foreground hover:bg-primary/90"
                            >
                                <Check size={14} weight="bold" />
                                Mark resolved
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => doUpdate("in_progress")}
                                disabled={busy}
                                data-testid={`signal-progress-${signal.signal_id}`}
                                className="border-border bg-transparent hover:bg-accent"
                            >
                                <ArrowUpRight size={14} weight="bold" />
                                Take action
                            </Button>
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => doUpdate("dismissed")}
                                disabled={busy}
                                data-testid={`signal-dismiss-${signal.signal_id}`}
                                className="text-muted-foreground hover:bg-accent hover:text-foreground"
                            >
                                <X size={14} weight="bold" />
                                Dismiss
                            </Button>
                        </div>
                    )}
                </div>
            )}
        </article>
    );
};

export default SignalCard;
