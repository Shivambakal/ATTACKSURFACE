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

export default function CookiesPage() {
  const [mounted, setMounted] = useState(false);
  const [functional, setFunctional] = useState(true);
  const [analytics, setAnalytics] = useState(false);
  const [answered, setAnswered] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    const consent = getCookieConsent();
    setFunctional(consent.functional);
    setAnalytics(consent.analytics);
    setAnswered(consent.answered);
    setUpdatedAt(consent.updated_at || null);

    const handleConsentChange = (e: Event) => {
      const customEvent = e as CustomEvent<CookieConsentPreferences>;
      if (customEvent.detail) {
        setFunctional(customEvent.detail.functional);
        setAnalytics(customEvent.detail.analytics);
        setAnswered(customEvent.detail.answered);
        setUpdatedAt(customEvent.detail.updated_at || null);
      }
    };

    window.addEventListener("attacksurface_cookie_consent_changed", handleConsentChange);
    return () => {
      window.removeEventListener("attacksurface_cookie_consent_changed", handleConsentChange);
    };
  }, []);

  const handleSave = () => {
    const updated = setCookieConsent({
      functional,
      analytics,
    });
    setAnswered(true);
    setUpdatedAt(updated.updated_at || new Date().toISOString());
    setFeedback("Cookie preferences have been saved and applied to your current session.");
    setTimeout(() => setFeedback(null), 4000);
  };

  const handleAcceptAll = () => {
    const updated = acceptAllCookies();
    setFunctional(true);
    setAnalytics(true);
    setAnswered(true);
    setUpdatedAt(updated.updated_at || new Date().toISOString());
    setFeedback("All cookies (essential, functional, and telemetry) have been activated.");
    setTimeout(() => setFeedback(null), 4000);
  };

  const handleRejectNonEssential = () => {
    const updated = rejectNonEssentialCookies();
    setFunctional(false);
    setAnalytics(false);
    setAnswered(true);
    setUpdatedAt(updated.updated_at || new Date().toISOString());
    setFeedback("Non-essential cookies rejected. Only strictly necessary cookies remain active.");
    setTimeout(() => setFeedback(null), 4000);
  };

  const handleReset = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("attacksurface_cookie_consent");
      document.cookie = "attacksurface_cookie_consent=; path=/; max-age=0";
    }
    setFunctional(false);
    setAnalytics(false);
    setAnswered(false);
    setUpdatedAt(null);
    setFeedback("Cookie preferences reset. The consent banner will reappear on your next action.");
    setTimeout(() => setFeedback(null), 4000);
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.1] bg-white/[0.03] px-3.5 py-1 text-xs font-mono text-slate-300">
          <span>COOKIE POLICY &amp; CONSENT PREFERENCES · COMPLIANT SEPTEMBER 2026</span>
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          Cookie <span className="text-cyan-400">Governance</span> &amp; Privacy Center
        </h1>

        <p className="text-base text-slate-300 leading-relaxed max-w-2xl">
          AttackSurface maintains a zero-advertising, zero-cross-site-tracker architecture. Review our active cookie registry below and customize your preferences in real-time.
        </p>
      </div>

      {/* Live Status & Feedback Notice */}
      <div className="mt-8 space-y-3">
        {feedback && (
          <div className="rounded-xl border border-emerald-500/40 bg-emerald-950/40 p-4 text-xs font-mono text-emerald-300 flex items-center justify-between gap-3 animate-in fade-in">
            <div className="flex items-center gap-2">
              <span>✓</span>
              <span>{feedback}</span>
            </div>
            <button onClick={() => setFeedback(null)} className="text-emerald-400 hover:text-white">✕</button>
          </div>
        )}

        {mounted && (
          <div className="rounded-2xl border border-white/[0.1] bg-slate-900/60 p-4 sm:p-5 backdrop-blur-xl flex flex-wrap items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                <span className={`h-2 w-2 rounded-full ${answered ? "bg-emerald-400" : "bg-amber-400 animate-pulse"}`} />
                <span>
                  Consent Status: {answered ? "Configured & Active" : "Pending User Decision (Defaulting to Essential Only)"}
                </span>
              </div>
              <p className="text-[11px] font-mono text-slate-400">
                Essential: <span className="text-emerald-400 font-bold">LOCKED ACTIVE</span> · Functional:{" "}
                <span className={functional ? "text-cyan-400 font-bold" : "text-slate-400"}>
                  {functional ? "ENABLED" : "DISABLED"}
                </span>{" "}
                · Telemetry:{" "}
                <span className={analytics ? "text-cyan-400 font-bold" : "text-slate-400"}>
                  {analytics ? "ENABLED" : "DISABLED"}
                </span>
                {updatedAt && ` · Last Synced: ${new Date(updatedAt).toLocaleTimeString()}`}
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <button
                type="button"
                onClick={handleReset}
                className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition-colors"
              >
                Reset Preferences
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Cookie Preference Cards */}
      <div className="mt-10 space-y-8 text-sm text-slate-300 leading-relaxed">
        {/* Category 1: Strictly Necessary (Locked) */}
        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-5">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2.5">
                <h2 className="text-xl font-bold text-white">1. Strictly Necessary Cookies</h2>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800">
                  Always Active
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-400">
                These cookies are vital for the cryptographic security, user authentication, and CSRF protection of AttackSurface. They cannot be disabled.
              </p>
            </div>

            <input
              type="checkbox"
              checked={true}
              disabled={true}
              className="mt-1 h-5 w-5 rounded bg-slate-800 border-slate-700 text-cyan-500 cursor-not-allowed opacity-80"
              aria-label="Strictly Necessary Cookies - Always Active"
            />
          </div>

          <div className="overflow-x-auto rounded-xl border border-white/[0.08] bg-white/[0.02]">
            <table className="w-full text-left font-mono text-xs">
              <thead className="border-b border-white/[0.08] bg-white/[0.03] text-slate-400">
                <tr>
                  <th className="py-2.5 px-4 font-semibold">Cookie / Storage Key</th>
                  <th className="py-2.5 px-4 font-semibold">Purpose &amp; Security Scope</th>
                  <th className="py-2.5 px-4 font-semibold">Duration</th>
                  <th className="py-2.5 px-4 font-semibold">Type</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] text-slate-300">
                <tr>
                  <td className="py-2.5 px-4 text-cyan-400 font-bold">session_token</td>
                  <td className="py-2.5 px-4 font-sans text-slate-300">Cryptographically signed operator session credential for authenticated routes</td>
                  <td className="py-2.5 px-4 text-slate-400">14 Days</td>
                  <td className="py-2.5 px-4 text-slate-400">HTTP-Only / Secure</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 text-cyan-400 font-bold">csrftoken</td>
                  <td className="py-2.5 px-4 font-sans text-slate-300">Cryptographic nonces preventing Cross-Site Request Forgery attacks</td>
                  <td className="py-2.5 px-4 text-slate-400">Session</td>
                  <td className="py-2.5 px-4 text-slate-400">Cookie (SameSite Lax)</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 text-cyan-400 font-bold">attacksurface_cookie_consent</td>
                  <td className="py-2.5 px-4 font-sans text-slate-300">Preserves your governance consent choices across visits</td>
                  <td className="py-2.5 px-4 text-slate-400">1 Year</td>
                  <td className="py-2.5 px-4 text-slate-400">Cookie &amp; LocalStorage</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Category 2: Functional & Preferences (Interactive Checkbox) */}
        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-5">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2.5">
                <h2 className="text-xl font-bold text-white">2. Functional &amp; Interface Preferences</h2>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800">
                  Optional
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-400">
                These cookies remember your interface preferences between browser visits, such as the White Aesthetic 3D canvas, sidebar pin state, and data density.
              </p>
            </div>

            <label className="flex items-center gap-2 cursor-pointer mt-1">
              <input
                type="checkbox"
                checked={functional}
                onChange={(e) => setFunctional(e.target.checked)}
                className="h-5 w-5 rounded bg-slate-800 border-slate-600 text-cyan-500 focus:ring-cyan-400 cursor-pointer"
              />
              <span className="text-xs font-bold text-slate-300">
                {functional ? "Enabled" : "Disabled"}
              </span>
            </label>
          </div>

          <div className="overflow-x-auto rounded-xl border border-white/[0.08] bg-white/[0.02]">
            <table className="w-full text-left font-mono text-xs">
              <thead className="border-b border-white/[0.08] bg-white/[0.03] text-slate-400">
                <tr>
                  <th className="py-2.5 px-4 font-semibold">Cookie / Storage Key</th>
                  <th className="py-2.5 px-4 font-semibold">Purpose &amp; Security Scope</th>
                  <th className="py-2.5 px-4 font-semibold">Duration</th>
                  <th className="py-2.5 px-4 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] text-slate-300">
                <tr>
                  <td className="py-2.5 px-4 text-cyan-400 font-bold">theme_preference</td>
                  <td className="py-2.5 px-4 font-sans text-slate-300">Remembers selected visual HUD theme (White Aesthetic 3D / Dark AMOLED)</td>
                  <td className="py-2.5 px-4 text-slate-400">1 Year</td>
                  <td className="py-2.5 px-4">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${functional ? "bg-cyan-950 text-cyan-300" : "bg-slate-800 text-slate-500"}`}>
                      {functional ? "ALLOWED" : "BLOCKED"}
                    </span>
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 text-cyan-400 font-bold">sidebar_collapsed</td>
                  <td className="py-2.5 px-4 font-sans text-slate-300">Saves your preferred operator navigation sidebar dock state</td>
                  <td className="py-2.5 px-4 text-slate-400">1 Year</td>
                  <td className="py-2.5 px-4">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${functional ? "bg-cyan-950 text-cyan-300" : "bg-slate-800 text-slate-500"}`}>
                      {functional ? "ALLOWED" : "BLOCKED"}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Category 3: Diagnostic & Telemetry (Interactive Checkbox) */}
        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-5">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2.5">
                <h2 className="text-xl font-bold text-white">3. Operational &amp; Diagnostic Telemetry</h2>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800">
                  Optional
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-400">
                Anonymous first-party telemetry that measures API latency and detects client-side rendering crashes. We never sell data or share data with ad exchanges.
              </p>
            </div>

            <label className="flex items-center gap-2 cursor-pointer mt-1">
              <input
                type="checkbox"
                checked={analytics}
                onChange={(e) => setAnalytics(e.target.checked)}
                className="h-5 w-5 rounded bg-slate-800 border-slate-600 text-cyan-500 focus:ring-cyan-400 cursor-pointer"
              />
              <span className="text-xs font-bold text-slate-300">
                {analytics ? "Enabled" : "Disabled"}
              </span>
            </label>
          </div>

          <div className="overflow-x-auto rounded-xl border border-white/[0.08] bg-white/[0.02]">
            <table className="w-full text-left font-mono text-xs">
              <thead className="border-b border-white/[0.08] bg-white/[0.03] text-slate-400">
                <tr>
                  <th className="py-2.5 px-4 font-semibold">Key</th>
                  <th className="py-2.5 px-4 font-semibold">Purpose &amp; Security Scope</th>
                  <th className="py-2.5 px-4 font-semibold">Duration</th>
                  <th className="py-2.5 px-4 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] text-slate-300">
                <tr>
                  <td className="py-2.5 px-4 text-cyan-400 font-bold">_as_perf_telemetry</td>
                  <td className="py-2.5 px-4 font-sans text-slate-300">Anonymous percentile latency aggregation across geographic regions</td>
                  <td className="py-2.5 px-4 text-slate-400">30 Days</td>
                  <td className="py-2.5 px-4">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${analytics ? "bg-cyan-950 text-cyan-300" : "bg-slate-800 text-slate-500"}`}>
                      {analytics ? "ALLOWED" : "BLOCKED"}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Global Save Controls */}
        <div className="rounded-3xl border border-cyan-500/30 bg-gradient-to-r from-cyan-950/40 via-slate-900/60 to-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <h3 className="text-base font-bold text-white">Ready to Save Your Choices?</h3>
            <p className="text-xs text-slate-400">
              Your preferences take effect instantly and synchronize across all open AttackSurface tabs.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={handleRejectNonEssential}
              className="px-4 py-2 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all"
            >
              Reject Non-Essential
            </button>
            <button
              type="button"
              onClick={handleAcceptAll}
              className="px-4 py-2 rounded-xl border border-slate-600 bg-slate-700/80 hover:bg-slate-700 text-white text-xs font-semibold transition-all"
            >
              Accept All
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold shadow-lg shadow-cyan-950/60 transition-all"
            >
              Save Preferences
            </button>
          </div>
        </div>

        {/* Zero Ad Guarantee */}
        <div className="rounded-3xl border border-white/[0.08] bg-[#02050b] p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-3">
          <h2 className="text-xl font-bold text-white">4. Absolute Zero Advertising Guarantee</h2>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            AttackSurface is a security intelligence system engineered for elite penetration testers, security engineers, and enterprise blue teams. We do not integrate Google AdSense, Facebook Pixel, LinkedIn Insight Tags, or commercial broker cookies. Your research activity, target watchlists, and observed differences are strictly private.
          </p>
          <div className="pt-2 flex items-center justify-between text-xs font-mono text-cyan-400">
            <span>Direct Security Desk: attacksurface.alerts@gmail.com</span>
            <Link href="/privacy" className="hover:underline text-slate-400 hover:text-cyan-300">
              Privacy Policy &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
