import { ArrowsClockwise } from "@phosphor-icons/react";
import { CategorySignalsPage } from "@/components/shared/CategorySignalsPage";
import { PAGE } from "@/constants/testIds";

export const RevenueRecoveryPage = () => (
    <CategorySignalsPage
        slug="revenue-recovery"
        testId={PAGE.revenueRecovery}
        eyebrow="Workspace"
        title="Revenue Recovery"
        description="Unbilled services, dropped renewals and payment-term drift. Every finding cites the source records and comes with a recommended action."
        category="revenue_recovery"
        emptyIcon={ArrowsClockwise}
    />
);

export default RevenueRecoveryPage;
