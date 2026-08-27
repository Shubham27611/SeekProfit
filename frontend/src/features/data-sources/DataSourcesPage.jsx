import { PlaceholderPage } from "@/components/shared/PlaceholderPage";

export const DataSourcesPage = () => (
    <PlaceholderPage
        slug="data-sources"
        eyebrow="Data"
        title="Data Sources"
        description="Connect the systems SeekProfit reads from — ledgers, billing, CRM and payment processors."
        features={[
            "Native connectors for common finance and revenue systems",
            "Freshness, drift and health monitoring per source",
            "Field-level mapping and lineage",
            "Read-only credentials with granular scopes",
        ]}
    />
);

export default DataSourcesPage;
