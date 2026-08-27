import { useEffect, useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { SignalCard } from "@/components/shared/SignalCard";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import api, { apiError } from "@/lib/api";

/**
 * Reusable page shell for a category signal list (Revenue Recovery, Profit
 * Leaks, Opportunities). Fetches signals for the given category with any
 * status.
 */
export const CategorySignalsPage = ({
    slug,
    testId,
    eyebrow,
    title,
    description,
    category,
    emptyIcon,
}) => {
    const [signals, setSignals] = useState([]);
    const [status, setStatus] = useState("loading");
    const [errMsg, setErrMsg] = useState("");

    const load = async () => {
        setStatus("loading");
        try {
            const { data } = await api.get("/signals", { params: { category } });
            setSignals(data.signals);
            setStatus("ready");
        } catch (e) {
            setErrMsg(apiError(e));
            setStatus("error");
        }
    };

    useEffect(() => {
        load();
    }, [category]); // eslint-disable-line react-hooks/exhaustive-deps

    const open = signals.filter((s) => s.status === "open");
    const closed = signals.filter((s) => s.status !== "open");

    return (
        <div data-testid={testId} className="sp-fade-in space-y-8">
            <PageHeader eyebrow={eyebrow} title={title} description={description} />

            {status === "loading" && <LoadingState rows={4} />}
            {status === "error" && (
                <ErrorState title="Couldn't load signals" description={errMsg} onRetry={load} />
            )}

            {status === "ready" && (
                <>
                    <SectionCard
                        title={`Open · ${open.length}`}
                        description="Highest-priority findings awaiting review"
                        bodyClassName="space-y-3"
                    >
                        {open.length === 0 ? (
                            <EmptyState
                                icon={emptyIcon}
                                title="No open findings here"
                                description="Either you've resolved everything or this category is clean today."
                                testId={`${slug}-empty`}
                            />
                        ) : (
                            open.map((s, i) => (
                                <SignalCard
                                    key={s.signal_id}
                                    signal={s}
                                    defaultOpen={i === 0}
                                    onStatusChange={() => load()}
                                />
                            ))
                        )}
                    </SectionCard>

                    {closed.length > 0 && (
                        <SectionCard
                            title={`Closed · ${closed.length}`}
                            description="Recently resolved or dismissed"
                            bodyClassName="space-y-3"
                        >
                            {closed.map((s) => (
                                <SignalCard
                                    key={s.signal_id}
                                    signal={s}
                                    onStatusChange={() => load()}
                                    showActions={false}
                                />
                            ))}
                        </SectionCard>
                    )}
                </>
            )}
        </div>
    );
};

export default CategorySignalsPage;
