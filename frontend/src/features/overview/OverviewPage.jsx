import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    CurrencyDollar,
    TrendUp,
    Warning,
    Lightning,
    ArrowUpRight,
    CalendarBlank,
    DownloadSimple,
    Sparkle,
    Database,
} from "@phosphor-icons/react";
import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import { SectionCard } from "@/components/shared/SectionCard";
import { RevenueTrendChart } from "@/components/shared/RevenueTrendChart";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PAGE, OVERVIEW } from "@/constants/testIds";
import { useAuth } from "@/features/authentication/AuthContext";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";

const KPI_ICONS = {
    recovered: CurrencyDollar,
    potential: TrendUp,
    leaks: Warning,
    actions: Lightning,
};

const KPI_TONE = {
    recovered: "positive",
    potential: "warning",
    leaks: "critical",
    actions: "warning",
};

const toneClasses = {
    positive: "border-emerald-500/25 bg-emerald-500/10 text-emerald-400",
    warning: "border-amber-500/25 bg-amber-500/10 text-amber-400",
    critical: "border-rose-500/25 bg-rose-500/10 text-rose-400",
};

export const OverviewPage = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [status, setStatus] = useState("loading");
    const [errMsg, setErrMsg] = useState("");

    const load = async () => {
        setStatus("loading");
        try {
            const { data } = await api.get("/overview");
            setData(data);
            setStatus("ready");
        } catch (e) {
            setErrMsg(apiError(e));
            setStatus("error");
        }
    };

    useEffect(() => {
        load();
    }, []);

    const firstName = (user?.name || "Operator").split(" ")[0];

    return (
        <div data-testid={PAGE.overview} className="sp-fade-in space-y-8">
            <PageHeader
                eyebrow="Overview"
                title={`Welcome back, ${firstName}.`}
                description="A live read on where your business is leaking profit and recovering revenue — every number is computed from the records in your workspace."
                actions={
                    <>
                        <Button
                            variant="outline"
                            size="sm"
                            data-testid={OVERVIEW.dateRangeButton}
                            className="border-border bg-background hover:bg-accent"
                        >
                            <CalendarBlank size={14} weight="duotone" />
                            Last 8 months
                        </Button>
                        <Button
                            size="sm"
                            data-testid={OVERVIEW.exportButton}
                            className="bg-primary text-primary-foreground hover:bg-primary/90"
                            onClick={() => toast.info("Exports arrive in the next release.")}
                        >
                            <DownloadSimple size={14} weight="bold" />
                            Export brief
                        </Button>
                    </>
                }
            />

            {status === "loading" && <LoadingState rows={5} testId="overview-loading" />}

            {status === "error" && (
                <ErrorState
                    title="Couldn't load your overview"
                    description={errMsg}
                    onRetry={load}
                    testId="overview-error"
                />
            )}

            {status === "ready" && data && (
                <>
                    {data.workspace?.data_source === "demo" && (
                        <div className="flex items-start gap-3 rounded-md border border-primary/25 bg-primary/5 px-4 py-3">
                            <Sparkle size={16} weight="fill" className="mt-0.5 shrink-0 text-primary" />
                            <div className="flex-1">
                                <p className="text-sm font-medium text-foreground">
                                    Viewing seeded demo data
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    Every KPI, chart and signal is computed from a demo dataset in MongoDB. Replace it with your own CSV under <span className="text-foreground">Data Sources</span>.
                                </p>
                            </div>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => navigate("/app/data-sources")}
                                data-testid="overview-manage-data-source"
                                className="border-border bg-transparent hover:bg-accent"
                            >
                                <Database size={14} weight="duotone" />
                                Manage
                            </Button>
                        </div>
                    )}

                    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                        {data.kpis.map((k) => (
                            <KpiCard
                                key={k.slug}
                                testId={OVERVIEW.kpiCard(k.slug)}
                                label={k.label}
                                value={k.value_display}
                                delta={k.slug === "leaks" ? k.supporting_amount : (k.amount_type === "measured" ? "measured" : k.amount_type === "potential" ? "potential" : "")}
                                deltaTone={KPI_TONE[k.slug]}
                                hint={k.hint}
                                icon={KPI_ICONS[k.slug]}
                            />
                        ))}
                    </section>

                    <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                        <SectionCard
                            className="lg:col-span-2"
                            title="Revenue recovery vs. potential"
                            description="Cumulative $ recovered against outstanding opportunity"
                            actions={
                                <Badge
                                    variant="outline"
                                    className="border-primary/30 bg-primary/10 text-primary"
                                >
                                    <Sparkle size={10} weight="fill" className="mr-1" />
                                    Live
                                </Badge>
                            }
                            bodyClassName="pt-4"
                        >
                            <RevenueTrendChart data={data.trend} />
                        </SectionCard>

                        <SectionCard
                            title="Signal feed"
                            description={`${data.counts.signals_open} open findings`}
                            testId={OVERVIEW.activityFeed}
                            bodyClassName="p-0"
                            actions={
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => navigate("/app/ai-analysis")}
                                    data-testid="overview-view-all-signals"
                                    className="text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
                                >
                                    View all
                                    <ArrowUpRight size={12} weight="bold" />
                                </Button>
                            }
                        >
                            {data.feed.length === 0 && (
                                <p className="px-5 py-6 text-sm text-muted-foreground">
                                    No open signals — your workspace looks clean.
                                </p>
                            )}
                            <ul className="divide-y divide-border">
                                {data.feed.map((row) => (
                                    <li
                                        key={row.id}
                                        data-testid={OVERVIEW.activityItem(row.id)}
                                        className="flex items-start justify-between gap-4 px-5 py-4 transition-colors hover:bg-accent/40"
                                    >
                                        <div className="min-w-0">
                                            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${toneClasses[row.tone] || toneClasses.warning}`}>
                                                {row.badge}
                                            </span>
                                            <p className="mt-2 truncate text-sm font-medium text-foreground">
                                                {row.title}
                                            </p>
                                            <p className="mt-0.5 text-xs text-muted-foreground">{row.source}</p>
                                        </div>
                                        <div className="text-right">
                                            <p className="font-mono text-sm font-medium tracking-tight text-foreground">
                                                {row.amount_display}
                                            </p>
                                            <button
                                                type="button"
                                                onClick={() => navigate("/app/ai-analysis")}
                                                className="mt-1 inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-primary"
                                            >
                                                Investigate
                                                <ArrowUpRight size={11} weight="bold" />
                                            </button>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        </SectionCard>
                    </section>

                    <section className="grid grid-cols-1 gap-6 md:grid-cols-3">
                        <div className="rounded-md border border-border bg-card p-5">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Records</p>
                            <p className="mt-3 font-mono text-2xl font-medium tracking-tight text-foreground">
                                {data.counts.records.toLocaleString()}
                            </p>
                            <p className="mt-2 text-xs text-muted-foreground">
                                across invoices, payments, vendor bills, contracts
                            </p>
                        </div>
                        <div className="rounded-md border border-border bg-card p-5">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Data source</p>
                            <p className="mt-3 font-mono text-2xl font-medium tracking-tight text-foreground capitalize">
                                {data.workspace.data_source || "empty"}
                            </p>
                            <p className="mt-2 text-xs text-muted-foreground">
                                Replace with CSV under Data Sources
                            </p>
                        </div>
                        <div className="rounded-md border border-border bg-card p-5">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Open signals</p>
                            <p className="mt-3 font-mono text-2xl font-medium tracking-tight text-foreground">
                                {data.counts.signals_open} / {data.counts.signals_total}
                            </p>
                            <p className="mt-2 text-xs text-muted-foreground">
                                open vs. total findings across categories
                            </p>
                        </div>
                    </section>
                </>
            )}
        </div>
    );
};

export default OverviewPage;
