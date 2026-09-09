"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  getCookieConsent,
  setCookieConsent,
  acceptAllCookies,
  rejectNonEssentialCookies,
  CookieConsentPreferences,
} from "@/lib/cookieConsent";

export default function CookieBanner() {
  const [mounted, setMounted] = useState(false);
  const [showBanner, setShowBanner] = useState(false);
  const [showCustomize, setShowCustomize] = useState(false);
  const [functional, setFunctional] = useState(true);
  const [analytics, setAnalytics] = useState(false);

  useEffect(() => {
    setMounted(true);
    const consent = getCookieConsent();
    if (!consent.answered) {
      setShowBanner(true);
      setFunctional(consent.functional);
      setAnalytics(consent.analytics);
    }

    const handleConsentChange = (e: Event) => {
      const customEvent = e as CustomEvent<CookieConsentPreferences>;
      if (customEvent.detail?.answered) {
        setShowBanner(false);
      }
    };

    window.addEventListener("attacksurface_cookie_consent_changed", handleConsentChange);
    return () => {
      window.removeEventListener("attacksurface_cookie_consent_changed", handleConsentChange);
    };
  }, []);

  if (!mounted || !showBanner) {
    return null;
  }

  const handleAcceptAll = () => {
    acceptAllCookies();
    setShowBanner(false);
  };

  const handleRejectNonEssential = () => {
    rejectNonEssentialCookies();
    setShowBanner(false);
  };

  const handleSaveCustom = () => {
    setCookieConsent({
      functional,
      analytics,
    });
    setShowBanner(false);
  };

  return (
    <div
      role="region"
      aria-label="Cookie Preferences Notification"
      className="fixed bottom-4 left-4 right-4 md:left-auto md:right-6 md:max-w-xl z-50 animate-in fade-in slide-in-from-bottom-5 duration-300"
    >
      <div className="rounded-2xl border border-white/[0.12] bg-[#030712]/95 backdrop-blur-2xl p-5 sm:p-6 shadow-[0_20px_50px_rgba(0,0,0,0.6)] text-slate-200">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-mono text-sm">
              🍪
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight font-sans">
                Cookie &amp; Telemetry Governance
              </h3>
              <p className="text-[11px] font-mono text-cyan-400">
                STRICT PRIVACY · ZERO THIRD-PARTY ADVERTISING TRACKERS
              </p>
            </div>
          </div>
          <button
            onClick={handleRejectNonEssential}
            className="text-slate-400 hover:text-white p-1 transition-colors text-xs"
            title="Dismiss with essential cookies only"
            aria-label="Close banner with essential cookies only"
          >
            ✕
          </button>
        </div>

        <p className="mt-3 text-xs leading-relaxed text-slate-300">
          AttackSurface uses strictly necessary cookies to maintain cryptographically signed operator sessions and CSRF defenses. Optional functional cookies store your interface preferences (e.g. White Aesthetic theme), while diagnostic cookies aid latency tracking.
        </p>

        {showCustomize && (
          <div className="mt-4 pt-4 border-t border-white/[0.08] space-y-3">
            {/* Essential (Locked) */}
            <div className="flex items-start justify-between gap-3 p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white">Strictly Necessary Cookies</span>
                  <span className="text-[9px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                    Always Active
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Required for operator authentication, session tokens, and security isolation. Cannot be deactivated.
                </p>
              </div>
              <input
                type="checkbox"
                checked={true}
                disabled={true}
                className="mt-1 h-4 w-4 rounded bg-slate-800 border-slate-700 text-cyan-500 cursor-not-allowed opacity-80"
              />
            </div>

            {/* Functional (Toggleable) */}
            <div className="flex items-start justify-between gap-3 p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white">Functional &amp; Interface Preferences</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Remembers your display theme (White Aesthetic / Dark), sidebar toggle state, and table pagination sizing.
                </p>
              </div>
              <input
                type="checkbox"
                checked={functional}
                onChange={(e) => setFunctional(e.target.checked)}
                className="mt-1 h-4 w-4 rounded bg-slate-800 border-slate-600 text-cyan-500 focus:ring-cyan-400 cursor-pointer"
              />
            </div>

            {/* Analytics (Toggleable) */}
            <div className="flex items-start justify-between gap-3 p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white">Operational &amp; Performance Telemetry</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Collects anonymous API response times and client diagnostic error logs. Zero third-party marketing beacons.
                </p>
              </div>
              <input
                type="checkbox"
                checked={analytics}
                onChange={(e) => setAnalytics(e.target.checked)}
                className="mt-1 h-4 w-4 rounded bg-slate-800 border-slate-600 text-cyan-500 focus:ring-cyan-400 cursor-pointer"
              />
            </div>
          </div>
        )}

        <div className="mt-4 pt-3 flex flex-wrap items-center justify-between gap-2.5">
          <div className="flex items-center gap-2 text-xs">
            <button
              type="button"
              onClick={() => setShowCustomize(!showCustomize)}
              className="text-cyan-400 hover:text-cyan-300 font-medium underline underline-offset-4 transition-colors"
            >
              {showCustomize ? "Hide Customization" : "Customize Preferences"}
            </button>
            <span className="text-slate-600">·</span>
            <Link
              href="/cookies"
              className="text-slate-400 hover:text-slate-300 transition-colors"
            >
              Policy Details &rarr;
            </Link>
          </div>

          <div className="flex items-center gap-2">
            {showCustomize ? (
              <>
                <button
                  type="button"
                  onClick={handleRejectNonEssential}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-800 text-slate-300 text-xs font-semibold transition-all"
                >
                  Reject Non-Essential
                </button>
                <button
                  type="button"
                  onClick={handleSaveCustom}
                  className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-md transition-all shadow-cyan-950/40"
                >
                  Save Preferences
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={handleRejectNonEssential}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-800 text-slate-300 text-xs font-semibold transition-all"
                >
                  Reject Non-Essential
                </button>
                <button
                  type="button"
                  onClick={handleAcceptAll}
                  className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-md transition-all shadow-cyan-950/40"
                >
                  Accept All Cookies
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
