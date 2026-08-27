import { PlaceholderPage } from "@/components/shared/PlaceholderPage";

export const ProfitLeaksPage = () => (
    <PlaceholderPage
        slug="profit-leaks"
        eyebrow="Workspace"
        title="Profit Leaks"
        description="Continuously scan spend, contracts and operations for duplicate charges, waste and margin erosion."
        features={[
            "Duplicate payment and vendor overlap detection",
            "Contract price-drift monitoring",
            "Discount and rebate leakage analysis",
            "Root-cause traces linked to source documents",
        ]}
    />
);

export default ProfitLeaksPage;
