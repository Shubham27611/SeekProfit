import { cn } from "@/lib/utils";

export const PageHeader = ({
    eyebrow,
    title,
    description,
    actions,
    className,
}) => {
    return (
        <header
            className={cn(
                "flex flex-col gap-4 border-b border-border/70 pb-6 sm:flex-row sm:items-end sm:justify-between",
                className
            )}
        >
            <div className="max-w-2xl">
                {eyebrow ? (
                    <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                        {eyebrow}
                    </p>
                ) : null}
                <h1 className="font-heading text-3xl font-medium tracking-tight text-foreground md:text-4xl">
                    {title}
                </h1>
                {description ? (
                    <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
                        {description}
                    </p>
                ) : null}
            </div>
            {actions ? (
                <div className="flex flex-wrap items-center gap-2">
                    {actions}
                </div>
            ) : null}
        </header>
    );
};

export default PageHeader;
