import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Database, ArrowsClockwise, ArrowRight, CircleNotch, CheckCircle } from "@phosphor-icons/react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import api, { apiError } from "@/lib/api";
import { PAGE } from "@/constants/testIds";

const CONNECTORS = [
    { id: "stripe", name: "Stripe", note: "Payments + invoices", status: "Planned" },
    { id: "quickbooks", name: "QuickBooks", note: "AP / AR ledgers", status: "Planned" },
    { id: "tally", name: "Tally", note: "India-first ERP", status: "Planned" },
    { id: "razorpay", name: "Razorpay", note: "Payments + subscriptions", status: "Planned" },
    { id: "gmail", name: "Gmail", note: "Invoice + receipt inbox", status: "Planned" },
];

export const DataSourcesPage = () => {
    const navigate = useNavigate();
    const [workspace, setWorkspace] = useState(null);
    const [reseeding, setReseeding] = useState(false);

    const load = () => api.get("/workspace/me").then(({ data }) => setWorkspace(data));

    useEffect(() => { load(); }, []);

    const handleReseed = async () => {
        if (reseeding) return;
        setReseeding(true);
        try {
            const { data } = await api.post("/workspace/reseed");
            toast.success(`Demo workspace refreshed — ${data.seeded_records} records loaded.`);
            await load();
        } catch (e) {
            toast.error(apiError(e));
        } finally {
            setReseeding(false);
        }
    };

    const src = workspace?.workspace?.data_source;

    return (
        <div data-testid={PAGE.dataSources} className="sp-fade-in space-y-8">
            <PageHeader
                eyebrow="Data"
                title="Data Sources"
                description="Where SeekProfit reads from. Every KPI, chart, signal and AI answer is computed from the connected dataset — never from hardcoded UI values."
            />

            <div className="grid gap-6 lg:grid-cols-2">
                <SectionCard
                    title="Demo dataset"
                    description={src === "demo" ? "Currently active — 200+ realistic records" : "Ready to load into your workspace"}
                    bodyClassName="space-y-3"
                    actions={src === "demo" ? (
                        <span className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                            <CheckCircle size={10} weight="fill" />
                            Active
                        </span>
                    ) : null}
                >
                    <p className="text-sm text-muted-foreground">
                        Invoices, payments, vendor bills and contracts with pre-baked leaks and opportunities — all clearly tagged as demo data in MongoDB.
                    </p>
                    <div className="flex flex-wrap gap-2 pt-2">
                        <Button
                            onClick={handleReseed}
                            disabled={reseeding}
                            data-testid="data-source-reseed"
                            className="bg-primary text-primary-foreground hover:bg-primary/90"
                        >
                            {reseeding ? (
                                <><CircleNotch size={14} weight="bold" className="animate-spin" />Refreshing…</>
                            ) : (
                                <><ArrowsClockwise size={14} weight="bold" />Refresh demo dataset</>
                            )}
                        </Button>
                    </div>
                </SectionCard>

                <SectionCard
                    title="Your CSV"
                    description={src === "csv" ? "Currently active — imported dataset" : "Replace the demo with your own data"}
                    bodyClassName="space-y-3"
                    actions={src === "csv" ? (
                        <span className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                            <CheckCircle size={10} weight="fill" />
                            Active
                        </span>
                    ) : null}
                >
                    <p className="text-sm text-muted-foreground">
                        Drop a CSV of your invoices, payments and vendor bills. SeekProfit re-runs the deterministic detectors + AI enrichment against your records.
                    </p>
                    <div className="flex flex-wrap gap-2 pt-2">
                        <Button
                            onClick={() => navigate("/app/imports")}
                            data-testid="data-source-upload-csv"
                            variant="outline"
                            className="border-border bg-transparent hover:bg-accent"
                        >
                            <Database size={14} weight="duotone" />
                            Upload CSV
                            <ArrowRight size={14} weight="bold" />
                        </Button>
                    </div>
                </SectionCard>
            </div>

            <SectionCard
                title="Native connectors"
                description="Direct integrations planned next — read-only, granular scopes"
                bodyClassName="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
            >
                {CONNECTORS.map((c) => (
                    <div key={c.id} className="rounded-md border border-border bg-background p-4">
                        <div className="flex items-start justify-between gap-2">
                            <div>
                                <p className="text-sm font-medium text-foreground">{c.name}</p>
                                <p className="mt-0.5 text-xs text-muted-foreground">{c.note}</p>
                            </div>
                            <span className="inline-flex items-center rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                                {c.status}
                            </span>
                        </div>
                    </div>
                ))}
            </SectionCard>
        </div>
    );
};

export default DataSourcesPage;
