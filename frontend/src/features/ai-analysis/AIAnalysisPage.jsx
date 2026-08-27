import { useEffect, useRef, useState } from "react";
import {
    Brain,
    PaperPlaneRight,
    Sparkle,
    CircleNotch,
    Lightning,
} from "@phosphor-icons/react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { SignalCard } from "@/components/shared/SignalCard";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import api, { apiError } from "@/lib/api";
import { askStream } from "@/lib/aiStream";
import { PAGE } from "@/constants/testIds";

const CATEGORIES = [
    { id: "all", label: "All signals" },
    { id: "revenue_recovery", label: "Revenue Recovery" },
    { id: "profit_leak", label: "Profit Leaks" },
    { id: "opportunity", label: "Opportunities" },
];

const SUGGESTIONS = [
    "Which finding has the largest recoverable revenue?",
    "Where am I paying twice for the same thing?",
    "Which customers are drifting past 45-day terms?",
    "What renewal should I raise price on this quarter?",
];

// Render inline [rec:xxx] tokens as citation chips + soften light markdown.
// Only render chips for record_ids that actually appear in `citations` — the
// backend also strips dead tokens, but we guard here too so the UI never has
// a chip that points to nothing.
const renderAnswerWithCitations = (text, citations = []) => {
    if (!text) return null;
    const validIds = new Set((citations || []).map((c) => c.record_id));
    let cleaned = text
        .replace(/^#{1,6}\s+/gm, "")
        .replace(/\*\*(.+?)\*\*/g, "$1")
        .replace(/^-\s+/gm, "· ");
    const parts = cleaned.split(/(\[rec:[a-zA-Z0-9_\-]+\])/g);
    return parts.map((part, i) => {
        const m = part.match(/^\[rec:([a-zA-Z0-9_\-]+)\]$/);
        if (!m) return <span key={i}>{part}</span>;
        if (!validIds.has(m[1])) return null;
        return (
            <a
                key={i}
                href={`#${m[1]}`}
                data-testid={`ai-citation-${m[1]}`}
                className="mx-0.5 inline-flex items-center rounded border border-primary/30 bg-primary/10 px-1 py-0.5 font-mono text-[10px] font-medium text-primary hover:bg-primary/20"
            >
                {m[1]}
            </a>
        );
    });
};

export const AIAnalysisPage = () => {
    const [category, setCategory] = useState("all");
    const [signals, setSignals] = useState([]);
    const [status, setStatus] = useState("loading");
    const [errMsg, setErrMsg] = useState("");
    const [enriching, setEnriching] = useState(false);
    const [pendingCount, setPendingCount] = useState(0);

    const [question, setQuestion] = useState("");
    const [answer, setAnswer] = useState(null); // {text, citations, streaming}
    const [asking, setAsking] = useState(false);
    const abortRef = useRef(null);

    const loadPending = async () => {
        try {
            const { data } = await api.get("/signals", { params: { status: "open", limit: 200 } });
            setPendingCount(data.signals.filter((s) => !s.ai_enriched).length);
        } catch {
            /* ignore */
        }
    };

    const load = async () => {
        setStatus("loading");
        try {
            const params = category === "all" ? {} : { category };
            const { data } = await api.get("/signals", { params: { ...params, status: "open" } });
            setSignals(data.signals);
            setStatus("ready");
        } catch (e) {
            setErrMsg(apiError(e));
            setStatus("error");
        }
    };

    useEffect(() => {
        load();
        loadPending();
    }, [category]); // eslint-disable-line react-hooks/exhaustive-deps

    const handleEnrich = async () => {
        if (enriching) return;
        setEnriching(true);
        toast.info("Claude is enriching your signals — this takes ~15s.");
        try {
            const { data } = await api.post("/signals/enrich");
            toast.success(`${data.enriched} signals enriched with explanations & actions.`);
            await Promise.all([load(), loadPending()]);
        } catch (e) {
            toast.error(apiError(e));
        } finally {
            setEnriching(false);
        }
    };

    const handleAsk = async (q) => {
        const query = (q || question).trim();
        if (!query || asking) return;
        setAsking(true);
        setAnswer({ text: "", citations: [], streaming: true });
        const controller = new AbortController();
        abortRef.current = controller;
        try {
            await askStream({
                question: query,
                signal: controller.signal,
                onDelta: (chunk) => {
                    setAnswer((prev) => ({
                        text: (prev?.text || "") + chunk,
                        citations: prev?.citations || [],
                        streaming: true,
                    }));
                },
                onDone: ({ text, citations }) => {
                    setAnswer({ text: text || "", citations: citations || [], streaming: false });
                },
                onError: (msg) => {
                    toast.error(msg);
                    setAnswer(null);
                },
            });
        } finally {
            setAsking(false);
            abortRef.current = null;
        }
    };

    const onStatusChange = (id, next) => {
        // If a signal is closed, remove it from the open list.
        if (next !== "open") {
            setSignals((prev) => prev.filter((s) => s.signal_id !== id));
        }
    };

    return (
        <div data-testid={PAGE.aiAnalysis} className="sp-fade-in space-y-8">
            <PageHeader
                eyebrow="Insights"
                title="AI Analysis"
                description="Every finding is grounded in the records in your workspace. The engine detects deterministically; Claude Sonnet 4.6 writes the explanation and cites the source records."
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleEnrich}
                        disabled={enriching}
                        data-testid="ai-enrich-button"
                        className="border-border bg-background hover:bg-accent"
                    >
                        {enriching ? (
                            <><CircleNotch size={14} weight="bold" className="animate-spin" />Enriching…</>
                        ) : (
                            <><Sparkle size={14} weight="fill" className="text-primary" />Enrich with Claude ({pendingCount} pending)</>
                        )}
                    </Button>
                }
            />

            <div className="grid gap-6 lg:grid-cols-5">
                {/* Ask SeekProfit */}
                <SectionCard
                    className="lg:col-span-2"
                    title="Ask SeekProfit"
                    description="Grounded in your dataset. Citations link to source records."
                    testId="ai-ask-panel"
                    bodyClassName="space-y-4"
                    actions={<Brain size={16} weight="duotone" className="text-primary" />}
                >
                    <div>
                        <Textarea
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            placeholder="e.g. Which supplier has the highest suspected duplicate spend?"
                            rows={3}
                            data-testid="ai-ask-input"
                            className="resize-none border-border bg-background text-sm"
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                                    e.preventDefault();
                                    handleAsk();
                                }
                            }}
                        />
                        <div className="mt-2 flex items-center justify-between">
                            <p className="text-[10px] text-muted-foreground">Cmd/Ctrl + Enter to send</p>
                            <Button
                                size="sm"
                                onClick={() => handleAsk()}
                                disabled={asking || !question.trim()}
                                data-testid="ai-ask-submit"
                                className="bg-primary text-primary-foreground hover:bg-primary/90"
                            >
                                {asking ? (
                                    <><CircleNotch size={14} weight="bold" className="animate-spin" />Thinking…</>
                                ) : (
                                    <><PaperPlaneRight size={14} weight="fill" />Ask</>
                                )}
                            </Button>
                        </div>
                    </div>

                    <div>
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Try</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                            {SUGGESTIONS.map((s) => (
                                <button
                                    key={s}
                                    type="button"
                                    onClick={() => { setQuestion(s); handleAsk(s); }}
                                    data-testid={`ai-suggestion-${SUGGESTIONS.indexOf(s)}`}
                                    className="rounded-full border border-border bg-background px-3 py-1 text-[11px] text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                                >
                                    {s}
                                </button>
                            ))}
                        </div>
                    </div>

                    {answer && (
                        <div data-testid="ai-answer" className="rounded-md border border-border bg-background p-4">
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-primary">
                                SeekProfit analyst
                                {answer.streaming && (
                                    <span className="ml-2 inline-flex items-center gap-1 text-muted-foreground">
                                        <CircleNotch size={9} weight="bold" className="animate-spin" />
                                        streaming…
                                    </span>
                                )}
                            </p>
                            <div className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                                {renderAnswerWithCitations(answer.text || "", answer.citations)}
                                {answer.streaming && <span className="ml-0.5 inline-block h-4 w-[3px] animate-pulse bg-primary align-middle" />}
                            </div>
                            {!answer.streaming && answer.citations?.length > 0 && (
                                <div className="mt-4 space-y-2 border-t border-border pt-3">
                                    <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                        Cited records
                                    </p>
                                    <ul className="space-y-1">
                                        {answer.citations.map((c) => (
                                            <li
                                                key={c.record_id}
                                                id={c.record_id}
                                                className="flex items-start justify-between gap-3 rounded-md border border-border bg-card px-3 py-2 text-xs"
                                            >
                                                <div>
                                                    <p className="text-foreground">
                                                        <span className="uppercase text-muted-foreground">{c.type}</span> · {c.counterparty}
                                                    </p>
                                                    <p className="mt-0.5 text-[11px] text-muted-foreground">
                                                        {c.memo || c.record_id}
                                                    </p>
                                                    <p className="mt-0.5 font-mono text-[10px] text-primary">{c.record_id}</p>
                                                </div>
                                                <span className="font-mono tabular-nums text-foreground">
                                                    ${Number(c.amount).toLocaleString()}
                                                </span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                </SectionCard>

                {/* Ranked signals */}
                <SectionCard
                    className="lg:col-span-3"
                    title="Ranked financial signals"
                    description="Ordered by Impact × Confidence × Urgency"
                    actions={
                        <Tabs value={category} onValueChange={setCategory}>
                            <TabsList className="bg-background">
                                {CATEGORIES.map((c) => (
                                    <TabsTrigger
                                        key={c.id}
                                        value={c.id}
                                        data-testid={`ai-tab-${c.id}`}
                                        className="text-xs data-[state=active]:bg-accent"
                                    >
                                        {c.label}
                                    </TabsTrigger>
                                ))}
                            </TabsList>
                        </Tabs>
                    }
                    bodyClassName="space-y-3"
                >
                    {status === "loading" && <LoadingState rows={4} testId="ai-signals-loading" />}
                    {status === "ready" && signals.length === 0 && (
                        <EmptyState
                            icon={Lightning}
                            title="Nothing open here"
                            description="No open signals in this category. Try another tab or run the enrichment."
                            testId="ai-signals-empty"
                        />
                    )}
                    {status === "ready" && signals.map((s, i) => (
                        <SignalCard
                            key={s.signal_id}
                            signal={s}
                            defaultOpen={i === 0 && category === "all"}
                            onStatusChange={onStatusChange}
                        />
                    ))}
                </SectionCard>
            </div>
        </div>
    );
};

export default AIAnalysisPage;
