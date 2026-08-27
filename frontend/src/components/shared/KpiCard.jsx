import { StatBadge } from "@/components/shared/StatBadge";
import { cn } from "@/lib/utils";

export const KpiCard = ({
    label,
    value,
    delta,
    deltaTone = "neutral",
    hint,
    icon: Icon,
    className,
    testId,
}) => {
    return (
        <div
            data-testid={testId}
            className={cn(
                "group relative flex flex-col gap-4 rounded-md border border-border bg-card p-5 transition-colors hover:border-border/80 hover:bg-card/80",
                className
            )}
        >
            <div className="flex items-start justify-between gap-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    {label}
                </p>
                {Icon ? (
                    <div className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-background/60 text-muted-foreground transition-colors group-hover:text-primary">
                        <Icon size={16} weight="duotone" />
                    </div>
                ) : null}
            </div>
            <div className="space-y-2">
                <div className="font-mono text-2xl font-medium tracking-tight text-foreground md:text-[28px]">
                    {value}
                </div>
                <div className="flex items-center gap-2">
                    {delta ? <StatBadge tone={deltaTone} value={delta} /> : null}
                    {hint ? (
                        <p className="text-xs text-muted-foreground">{hint}</p>
                    ) : null}
                </div>
            </div>
        </div>
    );
};

export default KpiCard;
