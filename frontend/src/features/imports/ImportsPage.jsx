import { PlaceholderPage } from "@/components/shared/PlaceholderPage";

export const ImportsPage = () => (
    <PlaceholderPage
        slug="imports"
        eyebrow="Data"
        title="Imports"
        description="Bring in CSV, XLSX or JSON exports when a native connector isn't available yet."
        features={[
            "Drag-and-drop import with schema detection",
            "Column mapping presets you can reuse",
            "Validation, deduping and reconciliation",
            "Historical import log with rollback",
        ]}
    />
);

export default ImportsPage;
