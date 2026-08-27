// Central registry of data-testid values so tests + UI stay in sync.

export const AUTH = {
    emailInput: "auth-email-input",
    passwordInput: "auth-password-input",
    submitButton: "auth-submit-button",
    ssoButton: "auth-sso-button",
    switchModeButton: "auth-switch-mode-button",
    demoLoginButton: "auth-demo-login-button",
};

export const SHELL = {
    root: "app-shell-root",
    sidebar: "app-sidebar",
    sidebarBrand: "app-sidebar-brand",
    mobileMenuButton: "app-mobile-menu-button",
    mobileNav: "app-mobile-nav",
    header: "app-header",
    userMenu: "app-user-menu",
    userMenuTrigger: "app-user-menu-trigger",
    logoutMenuItem: "app-user-menu-logout",
    searchInput: "app-header-search-input",
    themeToggle: "app-theme-toggle",
    workspaceSwitcher: "app-workspace-switcher",
    mainContent: "app-main-content",
    navItem: (slug) => `app-nav-item-${slug}`,
};

export const PAGE = {
    overview: "page-overview",
    revenueRecovery: "page-revenue-recovery",
    profitLeaks: "page-profit-leaks",
    opportunities: "page-opportunities",
    actionCenter: "page-action-center",
    dataSources: "page-data-sources",
    imports: "page-imports",
    aiAnalysis: "page-ai-analysis",
    reports: "page-reports",
    settings: "page-settings",
    notFound: "page-not-found",
};

export const OVERVIEW = {
    kpiCard: (slug) => `overview-kpi-${slug}`,
    chart: "overview-chart",
    activityFeed: "overview-activity-feed",
    activityItem: (id) => `overview-activity-item-${id}`,
    exportButton: "overview-export-button",
    dateRangeButton: "overview-date-range-button",
};

export const PLACEHOLDER = {
    root: (slug) => `placeholder-${slug}`,
    ctaButton: (slug) => `placeholder-${slug}-cta`,
};
