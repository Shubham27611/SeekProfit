import { PlaceholderPage } from "@/components/shared/PlaceholderPage";

export const AIAnalysisPage = () => (
    <PlaceholderPage
        slug="ai-analysis"
        eyebrow="Insights"
        title="AI Analysis"
        description="Ask deep questions of your data and receive explanations grounded in source records — with citations."
        features={[
            "Natural-language analysis with source-linked citations",
            "Financial anomaly detection tuned to your ledger",
            "What-if modeling for pricing and terms",
            "Human-in-the-loop review before any action ships",
        ]}
    />
);

export default AIAnalysisPage;
