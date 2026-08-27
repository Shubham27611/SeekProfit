import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadSimple, FileCsv, CircleNotch, CheckCircle } from "@phosphor-icons/react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import api, { apiError, API_BASE, readSession } from "@/lib/api";
import axios from "axios";
import { PAGE } from "@/constants/testIds";

export const ImportsPage = () => {
    const navigate = useNavigate();
    const inputRef = useRef(null);
    const [file, setFile] = useState(null);
    const [busy, setBusy] = useState(false);
    const [result, setResult] = useState(null);
    const [workspace, setWorkspace] = useState(null);

    const loadWorkspace = () =>
        api.get("/workspace/me").then(({ data }) => setWorkspace(data)).catch(() => {});

    useEffect(() => {
        loadWorkspace();
    }, []);

    const handlePick = (e) => {
        const f = e.target.files?.[0];
        if (f) setFile(f);
    };

    const handleUpload = async () => {
        if (!file || busy) return;
        setBusy(true);
        setResult(null);
        try {
            const form = new FormData();
            form.append("file", file);
            const session = readSession();
            const { data } = await axios.post(`${API_BASE}/imports/csv`, form, {
                headers: {
                    "Content-Type": "multipart/form-data",
                    Authorization: session?.token ? `Bearer ${session.token}` : undefined,
                },
            });
            setResult(data);
            toast.success(`${data.imported_records} records imported.`);
            await loadWorkspace();
        } catch (e) {
            toast.error(apiError(e));
        } finally {
            setBusy(false);
        }
    };

    return (
        <div data-testid={PAGE.imports} className="sp-fade-in space-y-8">
            <PageHeader
                eyebrow="Data"
                title="Imports"
                description="Replace the workspace dataset with your own CSV. All KPIs, signals and AI analysis will re-run against the new records."
            />

            <SectionCard
                title="Upload CSV"
                description="Required columns: type, date, amount, counterparty. Optional: memo, status, currency."
                bodyClassName="space-y-5"
            >
                <div className="rounded-md border border-dashed border-border bg-background p-8 text-center">
                    <FileCsv size={28} weight="duotone" className="mx-auto text-primary" />
                    <p className="mt-3 text-sm font-medium text-foreground">
                        {file ? file.name : "Drop or select a .csv file"}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                        Max 5 MB. Types supported: invoice, payment, vendor_bill, contract, refund.
                    </p>
                    <input
                        ref={inputRef}
                        type="file"
                        accept=".csv,text/csv"
                        onChange={handlePick}
                        data-testid="imports-file-input"
                        className="hidden"
                    />
                    <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
                        <Button
                            variant="outline"
                            onClick={() => inputRef.current?.click()}
                            data-testid="imports-pick-file"
                            className="border-border bg-transparent hover:bg-accent"
                        >
                            <UploadSimple size={14} weight="bold" />
                            {file ? "Choose a different file" : "Choose file"}
                        </Button>
                        {file && (
                            <Button
                                onClick={handleUpload}
                                disabled={busy}
                                data-testid="imports-upload"
                                className="bg-primary text-primary-foreground hover:bg-primary/90"
                            >
                                {busy ? <><CircleNotch size={14} weight="bold" className="animate-spin" />Importing…</> : <><UploadSimple size={14} weight="bold" />Replace workspace data</>}
                            </Button>
                        )}
                    </div>
                </div>

                {result && (
                    <div className="rounded-md border border-primary/25 bg-primary/5 p-4">
                        <p className="flex items-center gap-2 text-sm font-medium text-foreground">
                            <CheckCircle size={16} weight="fill" className="text-primary" />
                            Import successful
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                            {result.imported_records} records loaded. {result.generated_signals} new signals detected.
                        </p>
                        <div className="mt-3 flex gap-2">
                            <Button size="sm" onClick={() => navigate("/app/overview")} data-testid="imports-view-overview" className="bg-primary text-primary-foreground hover:bg-primary/90">
                                View Overview
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => navigate("/app/ai-analysis")} data-testid="imports-view-signals" className="border-border bg-transparent hover:bg-accent">
                                Review signals
                            </Button>
                        </div>
                    </div>
                )}
            </SectionCard>

            {workspace && (
                <SectionCard
                    title="Current dataset"
                    description="What SeekProfit is analyzing right now"
                    bodyClassName="grid grid-cols-3 gap-4"
                >
                    <div>
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Source</p>
                        <p className="mt-2 font-mono text-lg font-medium capitalize text-foreground">
                            {workspace.workspace?.data_source || "empty"}
                        </p>
                    </div>
                    <div>
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Demo records</p>
                        <p className="mt-2 font-mono text-lg font-medium text-foreground">
                            {workspace.counts?.demo_records ?? 0}
                        </p>
                    </div>
                    <div>
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">CSV records</p>
                        <p className="mt-2 font-mono text-lg font-medium text-foreground">
                            {workspace.counts?.csv_records ?? 0}
                        </p>
                    </div>
                </SectionCard>
            )}
        </div>
    );
};

export default ImportsPage;
