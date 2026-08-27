import { PlaceholderPage } from "@/components/shared/PlaceholderPage";

export const SettingsPage = () => (
    <PlaceholderPage
        slug="settings"
        eyebrow="Settings"
        title="Settings"
        description="Workspace preferences, members, roles, billing and audit — all in one place."
        features={[
            "Workspace profile, branding and locale",
            "Members, roles and single sign-on",
            "Billing, plan and usage metering",
            "Audit log and data retention policy",
        ]}
    />
);

export default SettingsPage;
