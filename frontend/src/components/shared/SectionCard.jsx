import { cn } from "@/lib/utils";

export const SectionCard = ({
    title,
    description,
    actions,
    children,
    className,
    bodyClassName,
    testId,
}) => {
    return (
        <section
            data-testid={testId}
            className={cn(
                "rounded-md border border-border bg-card",
                className
            )}
        >
            {(title || actions) && (
                <header className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
                    <div>
                        {title ? (
                            <h2 className="font-heading text-base font-medium text-foreground">
                                {title}
                            </h2>
                        ) : null}
                        {description ? (
                            <p className="mt-1 text-xs text-muted-foreground">
                                {description}
                            </p>
                        ) : null}
                    </div>
                    {actions ? (
                        <div className="flex items-center gap-2">{actions}</div>
                    ) : null}
                </header>
            )}
            <div className={cn("p-5", bodyClassName)}>{children}</div>
        </section>
    );
};

export default SectionCard;
