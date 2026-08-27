import {
    CurrencyDollar,
    TrendUp,
    Warning,
    Lightning,
    ArrowUpRight,
    CalendarBlank,
    DownloadSimple,
    Sparkle,
} from "@phosphor-icons/react";
import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import { SectionCard } from "@/components/shared/SectionCard";
import { StatBadge } from "@/components/shared/StatBadge";
import { RevenueTrendChart } from "@/components/shared/RevenueTrendChart";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PAGE, OVERVIEW } from "@/constants/testIds";
import { useAuth } from "@/features/authentication/AuthContext";

const KPIS = [
    {
        slug: "recovered",
        label: "Revenue Recovered",
        value: "$1.24M",
        delta: "+18.2%",
        tone: "positive",
        hint: "vs. prior quarter",
        icon: CurrencyDollar,
    },
    {
        slug: "potential",
        label: "Potential Recovery",
        value: "$482K",
        delta: "+6.1%",
        tone: "positive",
        hint: "across 12 accounts",
        icon: TrendUp,
    },
    {
        slug: "leaks",
        label: "Active Profit Leaks",
        value: "27",
        delta: "-3",
        tone: "positive",
        hint: "closed this month",
        icon: Warning,
    },
    {
        slug: "actions",
        label: "High-Impact Actions",
        value: "9",
        delta: "3 new",
        tone: "warning",
        hint: "awaiting review",
        icon: Lightning,
    },
];

const ACTIVITY = [
    {
        id: "a1",
        title: "Duplicate vendor payments detected",
        source: "AP Ledger · Q1",
        amount: "$18,420",
        tone: "critical",
        badge: "Profit leak",
    },
    {
        id: "a2",
        title: "Unbilled services identified",
        source: "Client billing",
        amount: "$42,180",
        tone: "warning",
        badge: "Recovery",
    },
    {
        id: "a3",
        title: "Contract renewal price uplift",
        source: "Sales ops",
        amount: "$96,000",
        tone: "positive",
        badge: "Opportunity",
    },
    {
        id: "a4",
        title: "Payment terms drifting past 45d",
        source: "AR aging",
        amount: "$212,900",
        tone: "warning",
        badge: "Working capital",
    },
];

const toneClasses = {
    positive: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
    warning: "border-amber-500/20 bg-amber-500/10 text-amber-400",
    critical: "border-rose-500/20 bg-rose-500/10 text-rose-400",
};

export const OverviewPage = () => {
    const { user } = useAuth();
    const firstName = (user?.name || "Operator").split(" ")[0];

    return (
        <div
            data-testid={PAGE.overview}
            className="sp-fade-in space-y-8"
        >
            <PageHeader
                eyebrow="Overview"
                title={`Welcome back, ${firstName}.`}
                description="A live read on where your business is leaking profit and recovering revenue. Real analysis pipelines connect in Stage 2."
                actions={
                    <>
                        <Button
                            variant="outline"
                            size="sm"
                            data-testid={OVERVIEW.dateRangeButton}
                            className="border-border bg-background hover:bg-accent"
                        >
                            <CalendarBlank size={14} weight="duotone" />
                            Last 90 days
                        </Button>
                        <Button
                            size="sm"
                            data-testid={OVERVIEW.exportButton}
                            className="bg-primary text-primary-foreground hover:bg-primary/90"
                        >
                            <DownloadSimple size={14} weight="bold" />
                            Export brief
                        </Button>
                    </>
                }
            />

            <section
                aria-label="Key performance indicators"
                className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
            >
                {KPIS.map((k) => (
                    <KpiCard
                        key={k.slug}
                        testId={OVERVIEW.kpiCard(k.slug)}
                        label={k.label}
                        value={k.value}
                        delta={k.delta}
                        deltaTone={k.tone}
                        hint={k.hint}
                        icon={k.icon}
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
                            <Sparkle
                                size={10}
                                weight="fill"
                                className="mr-1"
                            />
                            Live in Stage 2
                        </Badge>
                    }
                    bodyClassName="pt-4"
                >
                    <RevenueTrendChart />
                </SectionCard>

                <SectionCard
                    title="Signal feed"
                    description="Latest anomalies and opportunities"
                    testId={OVERVIEW.activityFeed}
                    bodyClassName="p-0"
                >
                    <ul className="divide-y divide-border">
                        {ACTIVITY.map((row) => (
                            <li
                                key={row.id}
                                data-testid={OVERVIEW.activityItem(row.id)}
                                className="flex items-start justify-between gap-4 px-5 py-4 transition-colors hover:bg-accent/40"
                            >
                                <div className="min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span
                                            className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${toneClasses[row.tone]}`}
                                        >
                                            {row.badge}
                                        </span>
                                    </div>
                                    <p className="mt-2 truncate text-sm font-medium text-foreground">
                                        {row.title}
                                    </p>
                                    <p className="mt-0.5 text-xs text-muted-foreground">
                                        {row.source}
                                    </p>
                                </div>
                                <div className="text-right">
                                    <p className="font-mono text-sm font-medium tracking-tight text-foreground">
                                        {row.amount}
                                    </p>
                                    <button
                                        className="mt-1 inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-primary"
                                        aria-label={`Investigate ${row.title}`}
                                    >
                                        Investigate
                                        <ArrowUpRight
                                            size={11}
                                            weight="bold"
                                        />
                                    </button>
                                </div>
                            </li>
                        ))}
                    </ul>
                </SectionCard>
            </section>

            <section className="grid grid-cols-1 gap-6 md:grid-cols-3">
                {[
                    {
                        title: "Data quality",
                        value: "98.4%",
                        delta: "+0.6%",
                        tone: "positive",
                        hint: "Records reconciled",
                    },
                    {
                        title: "Coverage",
                        value: "6 / 8",
                        delta: "2 pending",
                        tone: "warning",
                        hint: "Systems connected",
                    },
                    {
                        title: "Analyst hours saved",
                        value: "142h",
                        delta: "+22h",
                        tone: "positive",
                        hint: "this quarter",
                    },
                ].map((s) => (
                    <div
                        key={s.title}
                        className="rounded-md border border-border bg-card p-5"
                    >
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                            {s.title}
                        </p>
                        <div className="mt-3 flex items-end justify-between">
                            <p className="font-mono text-2xl font-medium tracking-tight text-foreground">
                                {s.value}
                            </p>
                            <StatBadge tone={s.tone} value={s.delta} />
                        </div>
                        <p className="mt-2 text-xs text-muted-foreground">
                            {s.hint}
                        </p>
                    </div>
                ))}
            </section>
        </div>
    );
};

export default OverviewPage;
