import { ArrowUpRight, Sparkle } from "@phosphor-icons/react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PAGE, PLACEHOLDER } from "@/constants/testIds";

// slug -> canonical PAGE test-id (kebab-case to camelCase).
const pageTestIdFor = (slug) => {
    const camel = slug.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    return PAGE[camel];
};

// Standard placeholder used by every not-yet-implemented feature route.
// It intentionally does NOT fake product data — it clearly states that the
// module is planned for the next development stage.
export const PlaceholderPage = ({
    slug,
    eyebrow,
    title,
    description,
    features = [],
    stage = "Stage 2",
}) => {
    return (
        <div
            data-testid={PLACEHOLDER.root(slug)}
            data-page-testid={pageTestIdFor(slug)}
            className="sp-fade-in space-y-8"
        >
            <div data-testid={pageTestIdFor(slug)} className="hidden" aria-hidden="true" />
            <PageHeader
                eyebrow={eyebrow}
                title={title}
                description={description}
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        data-testid={PLACEHOLDER.ctaButton(slug)}
                        className="border-border bg-background hover:bg-accent"
                    >
                        <ArrowUpRight size={14} weight="bold" />
                        Read the roadmap
                    </Button>
                }
            />

            <div className="grid gap-6 lg:grid-cols-5">
                <div className="lg:col-span-3">
                    <div className="rounded-md border border-border bg-card p-8">
                        <Badge
                            variant="outline"
                            className="mb-4 border-primary/30 bg-primary/10 text-primary"
                        >
                            <Sparkle
                                size={12}
                                weight="fill"
                                className="mr-1"
                            />
                            Planned — {stage}
                        </Badge>
                        <h2 className="font-heading text-2xl font-medium tracking-tight text-foreground">
                            This module is on the SeekProfit roadmap
                        </h2>
                        <p className="mt-3 max-w-lg text-sm leading-relaxed text-muted-foreground">
                            The <span className="text-foreground">{title}</span>{" "}
                            module is scaffolded and ready to be built out in the
                            next development stage. The routing, navigation and
                            layout for this section are already wired end-to-end.
                        </p>
                    </div>
                </div>

                <div className="lg:col-span-2">
                    <div className="h-full rounded-md border border-border bg-card p-6">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                            What ships next
                        </p>
                        <ul className="mt-4 space-y-3">
                            {features.map((f) => (
                                <li
                                    key={f}
                                    className="flex items-start gap-3 text-sm text-foreground"
                                >
                                    <span className="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                                    <span className="text-muted-foreground">
                                        {f}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PlaceholderPage;
