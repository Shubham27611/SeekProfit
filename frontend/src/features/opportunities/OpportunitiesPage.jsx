import { Lightbulb } from "@phosphor-icons/react";
import { CategorySignalsPage } from "@/components/shared/CategorySignalsPage";
import { PAGE } from "@/constants/testIds";

export const OpportunitiesPage = () => (
    <CategorySignalsPage
        slug="opportunities"
        testId={PAGE.opportunities}
        eyebrow="Workspace"
        title="Opportunities"
        description="High-impact revenue and margin plays scored by expected value, confidence and urgency."
        category="opportunity"
        emptyIcon={Lightbulb}
    />
);

export default OpportunitiesPage;
