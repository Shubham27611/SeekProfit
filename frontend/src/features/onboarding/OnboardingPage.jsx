import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Database, Sparkle, CircleNotch } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import api, { apiError } from "@/lib/api";
import { useAuth } from "@/features/authentication/AuthContext";

const INDUSTRIES = [
    "SaaS",
    "E-commerce",
    "Professional services",
    "Media & advertising",
    "Manufacturing",
    "Healthcare",
    "Fintech",
    "Retail",
    "Other",
];

export const OnboardingPage = () => {
    const { user, refreshMe } = useAuth();
    const navigate = useNavigate();
    const [name, setName] = useState(user?.workspace?.name || "");
    const [industry, setIndustry] = useState("SaaS");
    const [currency, setCurrency] = useState("USD");
    const [busy, setBusy] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (busy || !name.trim()) return;
        setBusy(true);
        try {
            await api.post("/workspace/setup", {
                business_name: name.trim(),
                industry,
                currency,
                load_demo_data: true,
            });
            await refreshMe();
            toast.success("Demo workspace ready — 200 records loaded.");
            navigate("/app/overview", { replace: true });
        } catch (err) {
            toast.error(apiError(err));
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="relative min-h-screen bg-background">
            <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-10 px-6 py-10 md:px-10 md:py-16">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <span className="inline-block h-2 w-2 rounded-full bg-primary" />
                        <span className="font-heading text-lg font-semibold tracking-tight text-foreground">SeekProfit</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                        Signed in as <span className="text-foreground">{user?.email}</span>
                    </p>
                </div>

                <div className="grid flex-1 gap-10 lg:grid-cols-[1.15fr_1fr]">
                    <div className="space-y-8">
                        <div>
                            <p className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-primary">
                                <Sparkle size={12} weight="fill" />
                                One-time setup
                            </p>
                            <h1 className="mt-3 font-heading text-3xl font-medium tracking-tight text-foreground md:text-4xl">
                                Tell us about your business.
                            </h1>
                            <p className="mt-3 max-w-lg text-sm leading-relaxed text-muted-foreground">
                                We'll spin up a seeded demo dataset for your workspace so every KPI, chart and AI finding you see afterwards is grounded in real records. You can replace it with your own CSV anytime.
                            </p>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-5 rounded-md border border-border bg-card p-6">
                            <div className="space-y-2">
                                <Label htmlFor="biz-name" className="text-xs font-medium text-muted-foreground">Business name</Label>
                                <Input
                                    id="biz-name"
                                    placeholder="Acme Financials"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    data-testid="onboarding-name-input"
                                    className="h-11 border-border bg-background"
                                    required
                                />
                            </div>
                            <div className="grid gap-4 sm:grid-cols-2">
                                <div className="space-y-2">
                                    <Label className="text-xs font-medium text-muted-foreground">Industry</Label>
                                    <Select value={industry} onValueChange={setIndustry}>
                                        <SelectTrigger data-testid="onboarding-industry" className="h-11 border-border bg-background">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {INDUSTRIES.map((i) => (
                                                <SelectItem key={i} value={i}>{i}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-xs font-medium text-muted-foreground">Currency</Label>
                                    <Select value={currency} onValueChange={setCurrency}>
                                        <SelectTrigger data-testid="onboarding-currency" className="h-11 border-border bg-background">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {["USD", "EUR", "GBP", "INR", "CAD", "AUD"].map((c) => (
                                                <SelectItem key={c} value={c}>{c}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            <div className="flex items-start gap-3 rounded-md border border-primary/30 bg-primary/5 p-4">
                                <Database size={18} weight="duotone" className="mt-0.5 shrink-0 text-primary" />
                                <div>
                                    <p className="text-sm font-medium text-foreground">Load seeded demo dataset</p>
                                    <p className="mt-1 text-xs text-muted-foreground">
                                        200+ invoices, payments, vendor bills and contracts with pre-baked leaks and opportunities — clearly labelled as demo data. Replace anytime under Data Sources.
                                    </p>
                                </div>
                            </div>

                            <Button
                                type="submit"
                                disabled={busy || !name.trim()}
                                data-testid="onboarding-submit"
                                className="h-11 w-full bg-primary text-primary-foreground hover:bg-primary/90"
                            >
                                {busy ? <><CircleNotch size={16} weight="bold" className="animate-spin" />Setting up your workspace…</> : <>Enter SeekProfit<ArrowRight size={16} weight="bold" /></>}
                            </Button>
                        </form>
                    </div>

                    <aside className="rounded-md border border-border bg-card p-6">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">What happens next</p>
                        <ol className="mt-5 space-y-5">
                            {[
                                {
                                    n: "01",
                                    t: "Seeded workspace",
                                    d: "We load ~200 realistic financial records into MongoDB, tagged as demo data.",
                                },
                                {
                                    n: "02",
                                    t: "Deterministic detectors run",
                                    d: "Duplicate payments, unbilled services, payment-term drift and renewal uplift are surfaced with evidence.",
                                },
                                {
                                    n: "03",
                                    t: "AI enrichment (on demand)",
                                    d: "Claude Sonnet writes the explanation + recommended action for each finding, grounded in the actual records.",
                                },
                                {
                                    n: "04",
                                    t: "Ask anything",
                                    d: "Query the AI analyst in natural language — every claim is cited back to a record ID.",
                                },
                            ].map((s) => (
                                <li key={s.n} className="flex gap-4">
                                    <span className="font-mono text-xs text-primary">{s.n}</span>
                                    <div>
                                        <p className="text-sm font-medium text-foreground">{s.t}</p>
                                        <p className="mt-0.5 text-xs text-muted-foreground">{s.d}</p>
                                    </div>
                                </li>
                            ))}
                        </ol>
                    </aside>
                </div>
            </div>
        </div>
    );
};

export default OnboardingPage;
