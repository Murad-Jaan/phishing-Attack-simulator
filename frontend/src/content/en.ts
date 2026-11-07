export const en = {
  app: {
    name: "Phishing Simulation + Detection",
    skipToContent: "Skip to main content",
    dash: "-",
  },
  nav: {
    dashboard: "Dashboard",
    campaigns: "Campaigns",
    templates: "Templates",
    groups: "Groups",
    reports: "Reports",
    analyzer: "Mail Analyzer",
    settings: "Settings",
  },
  common: {
    loading: "Loading...",
    save: "Save",
    cancel: "Cancel",
    confirm: "Confirm",
    back: "Back",
    next: "Next",
  },
  theme: {
    toggle: "Toggle theme",
    switchToDark: "Switch to dark theme",
    switchToLight: "Switch to light theme",
  },
  auth: {
    signIn: "Sign in",
    signInWorking: "Signing in...",
    signOut: "Sign out",
    welcomeTitle: "Welcome back",
    emailLabel: "Email address",
    emailPlaceholder: "you@organization.com",
    passwordLabel: "Password",
    showPassword: "Show password",
    hidePassword: "Hide password",
    forgotPassword: "Forgot password?",
    loginPurpose: "Sign in to manage your phishing simulations.",
    authorizationNotice:
      "Use of this platform requires a signed authorization covering scope, dates and domains. All activity is logged.",
    genericErrorTitle: "Sign-in problem",
    invalidCredentials:
      "Email or password is incorrect. Check your credentials and try again.",
    rateLimitTitle: "Too many attempts",
    rateLimitMessage:
      "Too many sign-in attempts. Wait {seconds} seconds before trying again. If the problem continues, contact your administrator for an unlock.",
    networkError: "Sign in failed. Check your connection and try again.",
    signOutError: "Sign out failed. Try again.",
    roleLabel: "Role",
    signedInAs: "Signed in as",
    shellWelcome: "You are ready to use the platform. Features appear as milestones are completed.",
  },
  health: {
    status: "Health Status",
  },
} as const;

export type AppContent = typeof en;
export default en;
