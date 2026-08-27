import { Link } from "react-router-dom";
import { ArrowLeft } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { PAGE } from "@/constants/testIds";

export const NotFoundPage = () => (
    <div
        data-testid={PAGE.notFound}
        className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-start justify-center gap-4"
    >
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-primary">
            404
        </p>
        <h1 className="font-heading text-3xl font-medium tracking-tight text-foreground">
            We couldn&apos;t find that page.
        </h1>
        <p className="text-sm text-muted-foreground">
            The route you followed doesn&apos;t exist yet. Head back to the workspace
            overview to keep exploring SeekProfit.
        </p>
        <Button asChild variant="outline" className="border-border">
            <Link to="/app/overview" data-testid="not-found-back">
                <ArrowLeft size={14} weight="bold" />
                Back to Overview
            </Link>
        </Button>
    </div>
);

export default NotFoundPage;
