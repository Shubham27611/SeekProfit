import {
    ChartPieSlice,
    ArrowsClockwise,
    Warning,
    Lightbulb,
    Target,
    Database,
    ArrowSquareIn,
    Brain,
    FileText,
    Gear,
} from "@phosphor-icons/react";

// Feature-oriented navigation. Each item maps 1:1 with a route + a placeholder
// or full page under src/features/*.
export const NAV_SECTIONS = [
    {
        id: "workspace",
        label: "Workspace",
        items: [
            {
                slug: "overview",
                label: "Overview",
                path: "/app/overview",
                icon: ChartPieSlice,
            },
            {
                slug: "revenue-recovery",
                label: "Revenue Recovery",
                path: "/app/revenue-recovery",
                icon: ArrowsClockwise,
            },
            {
                slug: "profit-leaks",
                label: "Profit Leaks",
                path: "/app/profit-leaks",
                icon: Warning,
            },
            {
                slug: "opportunities",
                label: "Opportunities",
                path: "/app/opportunities",
                icon: Lightbulb,
            },
            {
                slug: "action-center",
                label: "Action Center",
                path: "/app/action-center",
                icon: Target,
            },
        ],
    },
    {
        id: "data",
        label: "Data",
        items: [
            {
                slug: "data-sources",
                label: "Data Sources",
                path: "/app/data-sources",
                icon: Database,
            },
            {
                slug: "imports",
                label: "Imports",
                path: "/app/imports",
                icon: ArrowSquareIn,
            },
        ],
    },
    {
        id: "insights",
        label: "Insights",
        items: [
            {
                slug: "ai-analysis",
                label: "AI Analysis",
                path: "/app/ai-analysis",
                icon: Brain,
            },
            {
                slug: "reports",
                label: "Reports",
                path: "/app/reports",
                icon: FileText,
            },
        ],
    },
    {
        id: "settings",
        label: "Settings",
        items: [
            {
                slug: "settings",
                label: "Settings",
                path: "/app/settings",
                icon: Gear,
            },
        ],
    },
];

export const FLAT_NAV = NAV_SECTIONS.flatMap((s) => s.items);
