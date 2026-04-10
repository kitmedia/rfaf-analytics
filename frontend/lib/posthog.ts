/**
 * PostHog analytics client for RFAF Analytics frontend.
 * Tracks page views, analysis submissions, PDF downloads, chatbot usage.
 *
 * Safe to import in SSR — all calls are no-ops if POSTHOG_KEY is not set.
 */

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY ?? "";
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://eu.posthog.com";

let _initialized = false;

function getPostHog() {
  if (typeof window === "undefined") return null;
  if (!POSTHOG_KEY) return null;

  if (!_initialized) {
    // Dynamic import so posthog-js is never bundled for SSR
    import("posthog-js").then(({ default: posthog }) => {
      if (!posthog.__loaded) {
        posthog.init(POSTHOG_KEY, {
          api_host: POSTHOG_HOST,
          capture_pageview: false, // We fire manually on route changes
          persistence: "localStorage",
        });
      }
    });
    _initialized = true;
  }

  // Return posthog if already loaded
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const posthog = require("posthog-js").default;
    return posthog.__loaded ? posthog : null;
  } catch {
    return null;
  }
}

type Properties = Record<string, string | number | boolean | null | undefined>;

export function trackEvent(event: string, properties?: Properties) {
  const ph = getPostHog();
  if (!ph) return;
  try {
    ph.capture(event, properties ?? {});
  } catch {
    // Never block the UI for analytics errors
  }
}

export function trackPageView(pageName: string, properties?: Properties) {
  trackEvent("$pageview", { page: pageName, ...properties });
}

export function identifyClub(clubId: string, plan?: string) {
  const ph = getPostHog();
  if (!ph) return;
  try {
    ph.identify(`club_${clubId}`, { plan });
  } catch {
    // Silent fail
  }
}
