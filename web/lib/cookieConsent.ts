export interface CookieConsentPreferences {
  essential: boolean;
  functional: boolean;
  analytics: boolean;
  answered: boolean;
  updated_at?: string;
}

const COOKIE_NAME = "attacksurface_cookie_consent";
const STORAGE_KEY = "attacksurface_cookie_consent";

export function getCookieConsent(): CookieConsentPreferences {
  if (typeof window === "undefined") {
    return {
      essential: true,
      functional: false,
      analytics: false,
      answered: false,
    };
  }

  try {
    const rawLocal = localStorage.getItem(STORAGE_KEY);
    if (rawLocal) {
      const parsed = JSON.parse(rawLocal);
      return {
        essential: true,
        functional: Boolean(parsed.functional),
        analytics: Boolean(parsed.analytics),
        answered: Boolean(parsed.answered),
        updated_at: parsed.updated_at,
      };
    }

    const match = document.cookie.match(new RegExp(`(^|;\\s*)${COOKIE_NAME}=([^;]+)`));
    if (match) {
      const parsed = JSON.parse(decodeURIComponent(match[2]));
      return {
        essential: true,
        functional: Boolean(parsed.functional),
        analytics: Boolean(parsed.analytics),
        answered: true,
        updated_at: parsed.updated_at,
      };
    }
  } catch {
    // Ignore error
  }

  return {
    essential: true,
    functional: false,
    analytics: false,
    answered: false,
  };
}

export function setCookieConsent(prefs: {
  functional: boolean;
  analytics: boolean;
}): CookieConsentPreferences {
  const fullPrefs: CookieConsentPreferences = {
    essential: true,
    functional: Boolean(prefs.functional),
    analytics: Boolean(prefs.analytics),
    answered: true,
    updated_at: new Date().toISOString(),
  };

  if (typeof window !== "undefined") {
    try {
      const serialized = JSON.stringify(fullPrefs);
      localStorage.setItem(STORAGE_KEY, serialized);

      const maxAge = 60 * 60 * 24 * 365;
      const isHttps = window.location.protocol === "https:";
      document.cookie = `${COOKIE_NAME}=${encodeURIComponent(serialized)}; path=/; max-age=${maxAge}; SameSite=Lax${
        isHttps ? "; Secure" : ""
      }`;

      window.dispatchEvent(
        new CustomEvent("attacksurface_cookie_consent_changed", {
          detail: fullPrefs,
        })
      );
    } catch {
      // Storage error
    }
  }

  return fullPrefs;
}

export function acceptAllCookies(): CookieConsentPreferences {
  return setCookieConsent({
    functional: true,
    analytics: true,
  });
}

export function rejectNonEssentialCookies(): CookieConsentPreferences {
  return setCookieConsent({
    functional: false,
    analytics: false,
  });
}
