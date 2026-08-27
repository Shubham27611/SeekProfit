import { cn } from "@/lib/utils";

export const EmptyState = ({
    icon: Icon,
    title,
    description,
    action,
    className,
    testId,
}) => {
    return (
        <div
            data-testid={testId}
            className={cn(
                "flex flex-col items-start gap-3 rounded-md border border-dashed border-border bg-card/40 p-8",
                className
            )}
        >
            {Icon ? (
                <div className="flex h-10 w-10 items-center justify-center rounded-md border border-border bg-background">
                    <Icon size={20} weight="duotone" className="text-primary" />
                </div>
            ) : null}
            <div className="max-w-md">
                <h3 className="font-heading text-lg font-medium text-foreground">
                    {title}
                </h3>
                {description ? (
                    <p className="mt-1 text-sm text-muted-foreground">
                        {description}
                    </p>
                ) : null}
            </div>
            {action}
        </div>
    );
};

export default EmptyState;
