import { WarningCircle } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const ErrorState = ({
    title = "Something went wrong",
    description = "We couldn't complete this action. Please try again.",
    onRetry,
    className,
    testId,
}) => {
    return (
        <div
            data-testid={testId}
            className={cn(
                "flex flex-col items-start gap-3 rounded-md border border-destructive/40 bg-destructive/5 p-6",
                className
            )}
        >
            <div className="flex h-10 w-10 items-center justify-center rounded-md border border-destructive/40 bg-destructive/10">
                <WarningCircle
                    size={20}
                    weight="duotone"
                    className="text-destructive"
                />
            </div>
            <div>
                <h3 className="font-heading text-lg font-medium text-foreground">
                    {title}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                    {description}
                </p>
            </div>
            {onRetry ? (
                <Button
                    variant="outline"
                    size="sm"
                    onClick={onRetry}
                    data-testid="error-state-retry"
                >
                    Try again
                </Button>
            ) : null}
        </div>
    );
};

export default ErrorState;
