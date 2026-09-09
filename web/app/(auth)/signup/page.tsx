"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const { signup } = useAuth();

  // Wizard step
  const [step, setStep] = useState<"credentials" | "subscription">("credentials");

  // Step 1: Credentials
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [termsError, setTermsError] = useState<string | null>(null);

  // Selected subscription tier
  const [selectedPlan, setSelectedPlan] = useState<"FREE" | "PRO" | "ENTERPRISE">("FREE");

  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Handle Step 1 -> Step 2
  const handleProceedToSubscription = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setTermsError(null);

    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setErrorMessage("Password must be at least 8 characters long.");
      return;
    }

    if (!agreedToTerms) {
      setTermsError("Please check the box to agree to the Terms and Conditions to continue.");
      return;
    }

    setStep("subscription");
  };

  // Complete registration with selected subscription
  const handleCompleteRegistration = async (chosenTier: "FREE" | "PRO" | "ENTERPRISE") => {
    setSelectedPlan(chosenTier);
    setBusy(true);
    setErrorMessage(null);

    try {
      await signup(email, password);

      // If user selected a paid tier, note the preference in profile
      if (chosenTier !== "FREE") {
        try {
          await apiFetch("/api/v1/profile", {
            method: "PATCH",
            body: JSON.stringify({
              handles: {
                selected_plan: chosenTier,
                terms_accepted: true,
                terms_accepted_at: new Date().toISOString(),
              },
            }),
          });
        } catch {
          // Non-blocking
        }
      }

      router.push(chosenTier === "FREE" ? "/dashboard" : "/billing");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Account registration failed";
      setErrorMessage(msg);
      setStep("credentials");
    } finally {
      setBusy(false);
    }
  };

  const handleGoogleAuth = () => {
    // Standard OAuth entrypoint
    window.location.href = "/api/v1/auth/google";
  };

  return (
    <div>
      {/* Step Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">
            {step === "credentials" ? "Register Researcher" : "Select Subscription Plan"}
          </h2>
          <span className="font-mono text-xs text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/30">
            STEP {step === "credentials" ? "1 OF 2" : "2 OF 2"}
          </span>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          {step === "credentials"
            ? "Create an operator profile for authorized surface discovery."
            : "Choose the intelligence tier for your threat telemetry workflow."}
        </p>
      </div>

      {errorMessage && (
        <div className="mb-4 rounded-lg border border-red-500/40 bg-red-950/40 p-3 text-xs text-red-300">
          <span className="font-semibold text-red-200">Error: </span>
          {errorMessage}
        </div>
      )}

      {/* ── STEP 1: CREDENTIALS & TERMS ────────────────── */}
      {step === "credentials" && (
        <div className="space-y-4">
          {/* Continue with Google */}
          <button
            type="button"
            onClick={handleGoogleAuth}
            className="w-full flex items-center justify-center gap-3 rounded-lg border border-slate-700 bg-slate-800/90 py-2.5 px-4 text-xs font-semibold text-slate-100 hover:bg-slate-700/80 transition active:scale-[0.99]"
          >
            <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24">
              <path
                fill="#EA4335"
                d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"
              />
              <path
                fill="#4285F4"
                d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"
              />
              <path
                fill="#FBBC05"
                d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12 0 12s.7 2.3 1.9 4.7l3.7-2.9z"
              />
              <path
                fill="#34A853"
                d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16c1.8 3.7 5.6 7 10.1 7z"
              />
            </svg>
            <span>Continue with Google</span>
          </button>

          <div className="relative my-4 flex items-center justify-center text-xs">
            <div className="w-full border-t border-slate-800" />
            <span className="bg-slate-900 px-2 text-[10px] font-mono uppercase text-slate-500 shrink-0">
              or register with email
            </span>
            <div className="w-full border-t border-slate-800" />
          </div>

          <form onSubmit={handleProceedToSubscription} autoComplete="on" className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300">Email Address</label>
              <input
                type="email"
                required
                autoFocus
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="researcher@attacksurface.online"
                className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300">
                Master Password (min 8 chars)
              </label>
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300">Confirm Password</label>
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••••••"
                className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            {/* Terms and Conditions Checkbox */}
            <div className="pt-1 space-y-1.5">
              <label className="flex items-start gap-2.5 cursor-pointer text-xs text-slate-300 select-none">
                <input
                  type="checkbox"
                  checked={agreedToTerms}
                  onChange={(e) => {
                    setAgreedToTerms(e.target.checked);
                    if (e.target.checked) setTermsError(null);
                  }}
                  className="mt-0.5 h-4 w-4 rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-500/40"
                />
                <span className="leading-5">
                  I agree to the <span className="text-cyan-400 hover:underline">Terms of Service</span>,{" "}
                  <span className="text-cyan-400 hover:underline">Privacy Policy</span>, and strict Bug Bounty
                  Responsible Disclosure standards.
                  <span className="text-rose-400 ml-1 font-bold">*</span>
                </span>
              </label>

              {termsError && (
                <div className="rounded-lg border border-red-500/60 bg-red-950/60 p-2.5 text-xs font-mono text-red-300 flex items-center gap-2 animate-pulse">
                  <span className="shrink-0 text-sm">⚠️</span>
                  <span>{termsError}</span>
                </div>
              )}
            </div>

            <button
              type="submit"
              className="w-full rounded-lg bg-cyan-500 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 font-mono tracking-wide mt-2"
            >
              CONTINUE TO SUBSCRIPTION →
            </button>
          </form>
        </div>
      )}

      {/* ── STEP 2: SELECT SUBSCRIPTION ────────────────── */}
      {step === "subscription" && (
        <div className="space-y-4">
          <div className="space-y-3">
            {/* Free Tier */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 transition hover:border-slate-700">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-sm text-white">Community Hunter</h3>
                  <div className="text-xs text-slate-400 mt-0.5">Basic intelligence &amp; discovery</div>
                </div>
                <div className="font-mono text-sm font-bold text-slate-200">$0 <span className="text-[10px] text-slate-400 font-normal">/mo</span></div>
              </div>
              <ul className="mt-3 space-y-1 text-xs text-slate-300 font-sans">
                <li className="flex items-center gap-2 text-slate-300">
                  <span className="text-emerald-400">✓</span> 5 Active Monitored Targets
                </li>
                <li className="flex items-center gap-2 text-slate-300">
                  <span className="text-emerald-400">✓</span> Standard Program Catalog (H1/Bugcrowd)
                </li>
                <li className="flex items-center gap-2 text-slate-300">
                  <span className="text-emerald-400">✓</span> Community Threat Feed
                </li>
              </ul>
              <button
                type="button"
                disabled={busy}
                onClick={() => handleCompleteRegistration("FREE")}
                className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-800 py-2 text-xs font-mono font-semibold text-slate-200 hover:bg-slate-700 transition"
              >
                {busy && selectedPlan === "FREE" ? "STARTING ACCOUNT..." : "START WITH FREE TIER"}
              </button>
            </div>

            {/* Pro Tier (Highlighted) */}
            <div className="rounded-xl border border-cyan-500/50 bg-cyan-950/20 p-4 relative shadow-lg shadow-cyan-500/5">
              <div className="absolute -top-2.5 right-4 bg-cyan-500 text-slate-950 text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase tracking-wider">
                Recommended
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-sm text-white flex items-center gap-1.5">
                    <span>Professional Hunter</span>
                  </h3>
                  <div className="text-xs text-slate-400 mt-0.5">Full continuous attack-surface telemetry</div>
                </div>
                <div className="font-mono text-sm font-bold text-cyan-400">₹3,999 <span className="text-[10px] text-slate-400 font-normal">($49/mo)</span></div>
              </div>
              <ul className="mt-3 space-y-1 text-xs text-slate-200">
                <li className="flex items-center gap-2">
                  <span className="text-cyan-400 font-bold">✓</span> Unlimited Monitored Targets
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-cyan-400 font-bold">✓</span> Real-Time CISA KEV Exploitation Alerts
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-cyan-400 font-bold">✓</span> Continuous Scope Drift &amp; Diff Notifications
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-cyan-400 font-bold">✓</span> Full Data Exports (CSV, JSON, NDJSON, ZIP)
                </li>
              </ul>
              <button
                type="button"
                disabled={busy}
                onClick={() => handleCompleteRegistration("PRO")}
                className="mt-3 w-full rounded-lg bg-cyan-500 py-2 text-xs font-mono font-bold text-slate-950 hover:bg-cyan-400 transition shadow-md"
              >
                {busy && selectedPlan === "PRO" ? "SETTING UP PRO TIER..." : "ACTIVATE PRO HUNTER →"}
              </button>
            </div>

            {/* Enterprise Tier */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 transition hover:border-slate-700">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-sm text-white">Enterprise Team</h3>
                  <div className="text-xs text-slate-400 mt-0.5">Dedicated crawlers, APIs, and multi-seat</div>
                </div>
                <div className="font-mono text-sm font-bold text-slate-200">₹15,999 <span className="text-[10px] text-slate-400 font-normal">($199/mo)</span></div>
              </div>
              <ul className="mt-3 space-y-1 text-xs text-slate-300">
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span> Dedicated Collector Infrastructure
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span> Direct REST API &amp; Webhook Access
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span> Team Shared Findings &amp; Role Controls
                </li>
              </ul>
              <button
                type="button"
                disabled={busy}
                onClick={() => handleCompleteRegistration("ENTERPRISE")}
                className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-800 py-2 text-xs font-mono font-semibold text-slate-200 hover:bg-slate-700 transition"
              >
                {busy && selectedPlan === "ENTERPRISE" ? "SETTING UP..." : "SELECT ENTERPRISE →"}
              </button>
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between text-xs">
            <button
              type="button"
              onClick={() => setStep("credentials")}
              className="text-slate-400 hover:text-slate-200 font-mono transition"
            >
              ← Back to credentials
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => handleCompleteRegistration("FREE")}
              className="text-cyan-400 hover:text-cyan-300 font-mono transition"
            >
              Skip for now (Start Free) →
            </button>
          </div>
        </div>
      )}

      <div className="mt-6 border-t border-slate-800 pt-5 text-center text-xs text-slate-400">
        Already registered?{" "}
        <Link
          href="/login"
          className="font-medium text-cyan-400 hover:text-cyan-300 hover:underline"
        >
          Sign in here
        </Link>
      </div>
    </div>
  );
}
