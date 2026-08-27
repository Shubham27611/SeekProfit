import { PlaceholderPage } from "@/components/shared/PlaceholderPage";

export const ReportsPage = () => (
    <PlaceholderPage
        slug="reports"
        eyebrow="Insights"
        title="Reports"
        description="Executive-ready briefings that translate every anomaly and opportunity into money terms."
        features={[
            "Board-ready quarterly recovery brief",
            "Custom saved views with scheduled delivery",
            "PDF and CSV export with data lineage",
            "Shareable read-only links with expiry",
        ]}
    />
);

export default ReportsPage;
