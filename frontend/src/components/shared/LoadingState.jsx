import { cn } from "@/lib/utils";

export const LoadingState = ({ rows = 3, className, testId }) => {
    return (
        <div
            data-testid={testId}
            className={cn("space-y-3", className)}
            role="status"
            aria-busy="true"
            aria-live="polite"
        >
            {Array.from({ length: rows }).map((_, idx) => (
                <div
                    key={idx}
                    className="h-10 w-full animate-pulse rounded-md border border-border/60 bg-card/40"
                />
            ))}
            <span className="sr-only">Loading…</span>
        </div>
    );
};

export default LoadingState;
