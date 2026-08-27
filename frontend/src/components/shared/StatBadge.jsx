import { ArrowUpRight, ArrowDownRight, Minus } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";

// Small trend badge with restrained color usage.
// tone: "positive" | "warning" | "critical" | "neutral"
export const StatBadge = ({ tone = "neutral", value, className }) => {
    const tones = {
        positive:
            "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
        warning: "border-amber-500/20 bg-amber-500/10 text-amber-400",
        critical: "border-rose-500/20 bg-rose-500/10 text-rose-400",
        neutral:
            "border-border bg-muted/40 text-muted-foreground",
    };

    const Icon =
        tone === "positive"
            ? ArrowUpRight
            : tone === "critical" || tone === "warning"
              ? ArrowDownRight
              : Minus;

    return (
        <span
            className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[11px] font-medium tabular-nums",
                tones[tone],
                className
            )}
        >
            <Icon size={12} weight="bold" />
            {value}
        </span>
    );
};

export default StatBadge;
