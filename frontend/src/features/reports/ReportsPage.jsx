import { useEffect, useState } from "react";
import {
    FileText,
    Printer,
    ArrowRight,
    CircleNotch,
    Sparkle,
    TrendUp,
    Warning,
    Lightbulb,
    ArrowsClockwise,
} from "@phosphor-icons/react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { RevenueTrendChart } from "@/components/shared/RevenueTrendChart";
import { Button } from "@/components/ui/button";
import { PAGE } from "@/constants/testIds";
import api, { apiError } from "@/lib/api";
import { cn } from "@/lib/utils";

const CATEGORY_TONE = {
    revenue_recovery: "border-amber-500/25 bg-amber-500/10 text-amber-400",
    profit_leak: "border-rose-500/25 bg-rose-500/10 text-rose-400",
    opportunity: "border-emerald-500/25 bg-emerald-500/10 text-emerald-400",
};

const CATEGORY_ICON = {
    revenue_recovery: ArrowsClockwise,
    profit_leak: Warning,
    opportunity: Lightbulb,
};

const fmtDate = (iso) =>
    iso
        ? new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })
        : "";

export const ReportsPage = () => {
    const [data, setData] = useState(null);
    const [status, setStatus] = useState("loading");
    const [errMsg, setErrMsg] = useState("");

    const load = async () => {
        setStatus("loading");
        try {
            const { data } = await api.get("/reports/executive");
            setData(data);
            setStatus("ready");
        } catch (e) {
            setErrMsg(apiError(e));
            setStatus("error");
        }
    };

    useEffect(() => { load(); }, []);

    return (
        <div data-testid={PAGE.reports} className="sp-fade-in space-y-8 print:space-y-6">
            <PageHeader
                eyebrow="Insights"
                title="Executive brief"
                description="A board-ready snapshot of recovered dollars, open pipeline and the highest-priority actions in your workspace."
                actions={
                    <>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={load}
                            className="border-border bg-background hover:bg-accent print:hidden"
                            data-testid="report-refresh"
                        >
                            <ArrowsClockwise size={14} weight="duotone" />
                            Refresh
                        </Button>
                        <Button
                            size="sm"
                            onClick={() => window.print()}
                            data-testid="report-print"
                            className="bg-primary text-primary-foreground hover:bg-primary/90 print:hidden"
                        >
                            <Printer size={14} weight="bold" />
                            Print / Save PDF
                        </Button>
                    </>
                }
            />

            {status === "loading" && <LoadingState rows={6} testId="report-loading" />}
            {status === "error" && <ErrorState title="Couldn't load report" description={errMsg} onRetry={load} />}

            {status === "ready" && data && (
                <div data-testid="report-body" className="space-y-8 print:space-y-5">
                    {/* HEADLINE */}
                    <section className="rounded-md border border-border bg-card p-6 print:border-black print:bg-white print:text-black">
                        <div className="flex flex-wrap items-start justify-between gap-4">
                            <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-primary print:text-black">
                                    SeekProfit executive brief
                                </p>
                                <h2 className="mt-2 font-heading text-2xl font-medium tracking-tight text-foreground print:text-black">
                                    {data.workspace.name}
                                </h2>
                                <p className="mt-1 text-xs text-muted-foreground print:text-black/70">
                                    {data.workspace.industry || "—"} · {data.workspace.currency} · {data.period_label} · Generated {fmtDate(data.generated_at)}
                                </p>
                            </div>
                            <p className="rounded-md border border-primary/30 bg-primary/10 px-3 py-1.5 text-[11px] font-medium text-primary print:hidden">
                                <Sparkle size={10} weight="fill" className="mr-1 inline-block" />
                                Live · derived from {data.headline.records_analyzed.toLocaleString()} records
                            </p>
                        </div>

                        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
                            <div>
                                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground print:text-black/70">Revenue recovered</p>
                                <p className="mt-2 font-mono text-3xl font-medium tracking-tight text-foreground print:text-black">
                                    {data.headline.revenue_recovered_display}
                                </p>
                                <p className="mt-1 text-xs text-muted-foreground print:text-black/70">Captured or baseline retained</p>
                            </div>
                            <div>
                                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground print:text-black/70">Open pipeline</p>
                                <p className="mt-2 font-mono text-3xl font-medium tracking-tight text-foreground print:text-black">
                                    {data.headline.open_pipeline_display}
                                </p>
                                <p className="mt-1 text-xs text-muted-foreground print:text-black/70">
                                    Across {data.headline.open_signal_count} open cases
                                </p>
                            </div>
                            <div>
                                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground print:text-black/70">Records analyzed</p>
                                <p className="mt-2 font-mono text-3xl font-medium tracking-tight text-foreground print:text-black">
                                    {data.headline.records_analyzed.toLocaleString()}
                                </p>
                                <p className="mt-1 text-xs text-muted-foreground print:text-black/70">
                                    Invoices, payments, vendor bills, contracts
                                </p>
                            </div>
                        </div>
                    </section>

                    {/* CATEGORIES */}
                    <section>
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground print:text-black/70">
                            By category
                        </p>
                        <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-3">
                            {data.category_totals.map((c) => {
                                const Icon = CATEGORY_ICON[c.category] || TrendUp;
                                return (
                                    <div
                                        key={c.category}
                                        data-testid={`report-category-${c.category}`}
                                        className="rounded-md border border-border bg-card p-5 print:border-black print:bg-white print:text-black"
                                    >
                                        <div className="flex items-center gap-2">
                                            <Icon size={14} weight="duotone" className="text-primary print:text-black" />
                                            <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium print:border-black print:bg-white print:text-black", CATEGORY_TONE[c.category])}>
                                                {c.label}
                                            </span>
                                        </div>
                                        <p className="mt-4 font-mono text-2xl font-medium tracking-tight text-foreground print:text-black">
                                            {c.open_impact_display}
                                        </p>
                                        <p className="mt-1 text-xs text-muted-foreground print:text-black/70">
                                            {c.open_count} open · {c.resolved_impact_display} resolved
                                        </p>
                                    </div>
                                );
                            })}
                        </div>
                    </section>

                    {/* TREND */}
                    <SectionCard
                        title="Recovered vs. potential"
                        description="Cumulative $ recovered against outstanding opportunity"
                        bodyClassName="pt-4 print:bg-white"
                    >
                        <RevenueTrendChart data={data.trend} />
                    </SectionCard>

                    {/* TOP ACTIONS */}
                    <SectionCard
                        title="Top actions"
                        description="Highest-priority findings ready for owner sign-off"
                        bodyClassName="p-0"
                    >
                        <div className="overflow-x-auto">
                            <table className="w-full min-w-[720px] border-collapse text-left text-sm print:min-w-0">
                                <thead>
                                    <tr className="border-b border-border text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground print:border-black print:text-black/70">
                                        <th className="px-5 py-3">Signal</th>
                                        <th className="px-3 py-3">Category</th>
                                        <th className="px-3 py-3 text-right">Impact</th>
                                        <th className="px-3 py-3">Owner</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.top_actions.map((a) => (
                                        <tr key={a.signal_id} data-testid={`report-action-${a.signal_id}`} className="border-b border-border print:border-black/30">
                                            <td className="px-5 py-3">
                                                <p className="font-medium text-foreground print:text-black">{a.title}</p>
                                                {a.recommended_action && (
                                                    <p className="mt-1 max-w-lg text-[11px] text-muted-foreground print:text-black/70">
                                                        {a.recommended_action}
                                                    </p>
                                                )}
                                            </td>
                                            <td className="px-3 py-3">
                                                <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium print:border-black print:bg-white print:text-black", CATEGORY_TONE[a.category])}>
                                                    {a.category_label}
                                                </span>
                                                <p className="mt-1 text-[10px] uppercase text-muted-foreground print:text-black/70">{a.urgency}</p>
                                            </td>
                                            <td className="px-3 py-3 text-right">
                                                <p className="font-mono text-sm text-foreground print:text-black">{a.impact_display}</p>
                                                <p className="text-[10px] uppercase text-muted-foreground print:text-black/70">{a.amount_type}</p>
                                            </td>
                                            <td className="px-3 py-3">
                                                <p className="text-xs text-foreground print:text-black">
                                                    {a.owner_email ? a.owner_email : <span className="text-muted-foreground print:text-black/70">Unassigned</span>}
                                                </p>
                                                {a.due_date && (
                                                    <p className="mt-0.5 font-mono text-[10px] text-muted-foreground print:text-black/70">
                                                        due {fmtDate(a.due_date)}
                                                    </p>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                    {data.top_actions.length === 0 && (
                                        <tr>
                                            <td colSpan={4} className="px-5 py-6 text-center text-sm text-muted-foreground print:text-black/70">
                                                No open actions — the workspace is clean.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </SectionCard>

                    {/* COUNTERPARTIES */}
                    <div className="grid gap-6 md:grid-cols-2">
                        <SectionCard title="Top customers" description="By invoiced $" bodyClassName="p-0">
                            <ul className="divide-y divide-border">
                                {data.top_counterparties.customers.map((c) => (
                                    <li key={c.name} className="flex items-center justify-between gap-4 px-5 py-3 text-sm">
                                        <span className="text-foreground print:text-black">{c.name}</span>
                                        <span className="text-right">
                                            <span className="font-mono text-foreground print:text-black">{c.invoiced_display}</span>
                                            {c.outstanding > 0 && (
                                                <span className="ml-2 rounded-full border border-amber-500/25 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-400 print:border-black print:bg-white print:text-black">
                                                    {c.outstanding_display} outstanding
                                                </span>
                                            )}
                                        </span>
                                    </li>
                                ))}
                                {data.top_counterparties.customers.length === 0 && (
                                    <li className="px-5 py-6 text-sm text-muted-foreground">No customer data yet.</li>
                                )}
                            </ul>
                        </SectionCard>
                        <SectionCard title="Top vendors" description="By spend" bodyClassName="p-0">
                            <ul className="divide-y divide-border">
                                {data.top_counterparties.vendors.map((v) => (
                                    <li key={v.name} className="flex items-center justify-between gap-4 px-5 py-3 text-sm">
                                        <span className="text-foreground print:text-black">{v.name}</span>
                                        <span className="font-mono text-foreground print:text-black">{v.spend_display}</span>
                                    </li>
                                ))}
                                {data.top_counterparties.vendors.length === 0 && (
                                    <li className="px-5 py-6 text-sm text-muted-foreground">No vendor data yet.</li>
                                )}
                            </ul>
                        </SectionCard>
                    </div>

                    {/* RESOLVED WINS */}
                    {data.resolved_wins.length > 0 && (
                        <SectionCard title="Recent wins" description="Signals closed with impact captured" bodyClassName="p-0">
                            <ul className="divide-y divide-border">
                                {data.resolved_wins.map((w) => (
                                    <li key={w.signal_id} className="flex items-center justify-between gap-4 px-5 py-3 text-sm">
                                        <div>
                                            <p className="text-foreground print:text-black">{w.title}</p>
                                            <p className="mt-0.5 text-[11px] text-muted-foreground print:text-black/70">
                                                {w.category_label} · resolved {fmtDate(w.resolved_at)}
                                            </p>
                                        </div>
                                        <span className="font-mono text-emerald-400 print:text-black">{w.impact_display}</span>
                                    </li>
                                ))}
                            </ul>
                        </SectionCard>
                    )}

                    <p className="text-center text-[11px] text-muted-foreground print:text-black/60">
                        SeekProfit · Find the money your business is missing.
                    </p>
                </div>
            )}
        </div>
    );
};

export default ReportsPage;
