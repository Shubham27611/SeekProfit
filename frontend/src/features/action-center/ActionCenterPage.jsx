import { PlaceholderPage } from "@/components/shared/PlaceholderPage";

export const ActionCenterPage = () => (
    <PlaceholderPage
        slug="action-center"
        eyebrow="Workspace"
        title="Action Center"
        description="The single queue where every SeekProfit finding turns into an owned, tracked action with measurable outcome."
        features={[
            "Unified queue across leaks, recovery and opportunities",
            "Owner assignment, SLAs and status tracking",
            "Financial impact captured at close",
            "Audit trail and export for finance leadership",
        ]}
    />
);

export default ActionCenterPage;
