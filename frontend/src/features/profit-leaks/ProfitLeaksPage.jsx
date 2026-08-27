import { Warning } from "@phosphor-icons/react";
import { CategorySignalsPage } from "@/components/shared/CategorySignalsPage";
import { PAGE } from "@/constants/testIds";

export const ProfitLeaksPage = () => (
    <CategorySignalsPage
        slug="profit-leaks"
        testId={PAGE.profitLeaks}
        eyebrow="Workspace"
        title="Profit Leaks"
        description="Duplicate payments, overlapping subscriptions and other silent margin erosion — with source-linked evidence."
        category="profit_leak"
        emptyIcon={Warning}
    />
);

export default ProfitLeaksPage;
