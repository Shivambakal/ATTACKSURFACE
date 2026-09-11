"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Stepper, Step } from "@/components/Stepper";

interface CanonicalCompanyOption {
  id: string;
  name: string;
  domain: string;
  industry: string;
  assetsCount: number;
  hasBounty: boolean;
}

const DEFAULT_POPULAR_COMPANIES: CanonicalCompanyOption[] = [
  { id: "google", name: "Google", domain: "google.com", industry: "Technology", assetsCount: 4820, hasBounty: true },
  { id: "microsoft", name: "Microsoft", domain: "microsoft.com", industry: "Software & Cloud", assetsCount: 8240, hasBounty: true },
  { id: "apple", name: "Apple", domain: "apple.com", industry: "Hardware & Tech", assetsCount: 2410, hasBounty: true },
  { id: "openai", name: "OpenAI", domain: "openai.com", industry: "AI & LLM", assetsCount: 430, hasBounty: true },
  { id: "github", name: "GitHub", domain: "github.com", industry: "Developer Tools", assetsCount: 890, hasBounty: true },
  { id: "stripe", name: "Stripe", domain: "stripe.com", industry: "Fintech & Payments", assetsCount: 340, hasBounty: true },
  { id: "amazon", name: "Amazon", domain: "amazon.com", industry: "Cloud & Retail", assetsCount: 6120, hasBounty: true },
  { id: "cloudflare", name: "Cloudflare", domain: "cloudflare.com", industry: "Edge & CDN", assetsCount: 1240, hasBounty: false },
  { id: "meta", name: "Meta", domain: "meta.com", industry: "Social & VR", assetsCount: 3950, hasBounty: true },
  { id: "uber", name: "Uber", domain: "uber.com", industry: "Mobility", assetsCount: 780, hasBounty: true },
  { id: "shopify", name: "Shopify", domain: "shopify.com", industry: "E-Commerce", assetsCount: 560, hasBounty: true },
  { id: "slack", name: "Slack", domain: "slack.com", industry: "Collaboration", assetsCount: 310, hasBounty: true },
];

export default function SignupPage() {
  const router = useRouter();
  const { signup } = useAuth();

  // Stepper state (1: Credentials, 2: Companies, 3: Payment)
  const [currentStep, setCurrentStep] = useState(1);

  // ── Slide 1: Profile & Credentials ──────────────────────────────
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [step1Error, setStep1Error] = useState<string | null>(null);

  // ── Slide 2: Companies to Track & Pin on Dashboard ──────────────
  const [availableCompanies, setAvailableCompanies] = useState<CanonicalCompanyOption[]>(DEFAULT_POPULAR_COMPANIES);
  const [pinnedCompanies, setPinnedCompanies] = useState<string[]>(["Google", "Microsoft", "OpenAI"]);
  const [companySearch, setCompanySearch] = useState("");
  const [customCompanyName, setCustomCompanyName] = useState("");

  // ── Slide 3: Subscription & Payment ─────────────────────────────
  const [selectedPlan, setSelectedPlan] = useState<"FREE" | "RESEARCHER" | "PRO">("FREE");
  const [billingInterval, setBillingInterval] = useState<"monthly" | "annual">("monthly");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);

  // Fetch live companies from platform database
  useEffect(() => {
    const loadCompanies = async () => {
      try {
        const res = await apiFetch<{ items: any[] }>("/api/v1/companies?limit=40");
        if (res?.items && res.items.length > 0) {
          const mapped: CanonicalCompanyOption[] = res.items.map((c) => ({
            id: String(c.id),
            name: c.name,
            domain: c.canonical_domain || `${c.name.toLowerCase().replace(/\s+/g, "")}.com`,
            industry: c.industry || "Technology",
            assetsCount: c.assets_count || 120,
            hasBounty: Boolean(c.bug_bounty_url),
          }));

          // Merge without duplicates
          const seen = new Set<string>();
          const combined: CanonicalCompanyOption[] = [];
          for (const comp of [...mapped, ...DEFAULT_POPULAR_COMPANIES]) {
            if (!seen.has(comp.name.toLowerCase())) {
              seen.add(comp.name.toLowerCase());
              combined.push(comp);
            }
          }
          setAvailableCompanies(combined);
        }
      } catch {
        // Fallback to defaults
      }
    };
    loadCompanies();
  }, []);

  // Filter companies by search query
  const filteredCompanies = useMemo(() => {
    const q = companySearch.trim().toLowerCase();
    if (!q) return availableCompanies;
    return availableCompanies.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.domain.toLowerCase().includes(q) ||
        c.industry.toLowerCase().includes(q)
    );
  }, [availableCompanies, companySearch]);

  // Toggle company pin
  const handleTogglePin = (companyNameOrDomain: string) => {
    setPinnedCompanies((prev) =>
      prev.includes(companyNameOrDomain)
        ? prev.filter((name) => name !== companyNameOrDomain)
        : [...prev, companyNameOrDomain]
    );
  };

  // Add custom company/domain
  const handleAddCustomCompany = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = customCompanyName.trim();
    if (!clean) return;
    if (!pinnedCompanies.includes(clean)) {
      setPinnedCompanies((prev) => [...prev, clean]);
    }
    setCustomCompanyName("");
  };

  // Validation for Step 1 -> Step 2
  const handleProceedFromStep1 = () => {
    setStep1Error(null);
    if (!fullName.trim()) {
      setStep1Error("Please enter your name or researcher handle.");
      return;
    }
    if (!email.trim() || !email.includes("@")) {
      setStep1Error("Please enter a valid email address.");
      return;
    }
    if (password.length < 8) {
      setStep1Error("Password must be at least 8 characters long.");
      return;
    }
    if (password !== confirmPassword) {
      setStep1Error("Passwords do not match.");
      return;
    }
    if (!agreedToTerms) {
      setStep1Error("Please confirm agreement to the Terms and Bug Bounty Policy.");
      return;
    }
    setCurrentStep(2);
  };

  // Step 2 -> Step 3
  const handleProceedFromStep2 = () => {
    setCurrentStep(3);
  };

  // Step 3: Complete registration and launch dashboard
  const handleFinalSubmit = async () => {
    setIsSubmitting(true);
    setGeneralError(null);

    try {
      // 1. Sign up user
      await signup(email, password);

      // 2. Persist profile info & pinned companies to preferences
      try {
        const prefPayload = {
          pinnedCompanies: pinnedCompanies,
          companyPriorities: pinnedCompanies.reduce((acc, c) => {
            acc[c] = "CRITICAL";
            return acc;
          }, {} as Record<string, "CRITICAL">),
        };

        // Local storage cache for instant dashboard render
        const storageKey = "ast_workspace_preferences_v2";
        const existing = localStorage.getItem(storageKey);
        const parsed = existing ? JSON.parse(existing) : {};
        localStorage.setItem(storageKey, JSON.stringify({ ...parsed, ...prefPayload }));
        localStorage.setItem("pinned_companies", JSON.stringify(pinnedCompanies));

        // Sync to API profile
        await apiFetch("/api/v1/profile", {
          method: "PATCH",
          body: JSON.stringify({
            handles: {
              full_name: fullName.trim(),
              pinned_companies: pinnedCompanies,
              selected_plan: selectedPlan,
              billing_interval: billingInterval,
              terms_accepted: true,
              terms_accepted_at: new Date().toISOString(),
            },
          }),
        });
      } catch {
        // Non-blocking preference sync
      }

      // 3. Launch directly to our website main dashboard page
      router.replace("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Account registration failed";
      setGeneralError(msg);
      setIsSubmitting(false);
    }
  };

  const stepsList = [
    { label: "Credentials", description: "Name, email & password" },
    { label: "Tracked Companies", description: "Pin targets to dashboard" },
    { label: "Plan & Payment", description: "Select tier & activate" },
  ];

  return (
    <div className="w-full">
      {/* Top Title */}
      <div className="mb-6 text-center">
        <h2 className="text-xl sm:text-2xl font-black text-white font-display tracking-tight">
          Create Researcher Profile
        </h2>
        <p className="mt-1 text-xs text-slate-400 font-sans">
          Step {currentStep} of 3: {stepsList[currentStep - 1].description}
        </p>
      </div>

      {generalError && (
        <div className="mb-4 rounded-xl border border-red-500/50 bg-red-950/40 p-3.5 text-xs text-red-300 font-sans flex items-center gap-2">
          <span className="text-sm">⚠️</span>
          <span>{generalError}</span>
        </div>
      )}

      {/* ── REACT BITS STEPPER ──────────────────────────────────── */}
      <Stepper
        currentStep={currentStep}
        steps={stepsList}
        onStepChange={(st) => {
          if (st < currentStep) setCurrentStep(st);
        }}
        onNext={() => {
          if (currentStep === 1) handleProceedFromStep1();
          else if (currentStep === 2) handleProceedFromStep2();
          else handleFinalSubmit();
        }}
        onBack={() => setCurrentStep((prev) => Math.max(1, prev - 1))}
        nextButtonText={
          currentStep === 1
            ? "Continue to Tracked Companies →"
            : currentStep === 2
            ? "Continue to Plan & Payment →"
            : isSubmitting
            ? "Activating..."
            : "Complete Profile & Launch Dashboard →"
        }
        isBusy={isSubmitting}
      >
        {/* ── SLIDE 1: NAME, EMAIL, PASSWORD ───────────────────── */}
        {currentStep === 1 && (
          <Step>
            <div className="space-y-4">
              {step1Error && (
                <div className="rounded-xl border border-red-500/40 bg-red-950/50 p-3 text-xs text-red-300 font-sans flex items-center gap-2">
                  <span className="text-sm">⚠️</span>
                  <span>{step1Error}</span>
                </div>
              )}

              {/* Full Name / Handle */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1 font-mono">
                  Full Name or Researcher Handle <span className="text-cyan-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  autoFocus
                  placeholder="e.g. Shivam Bakal, CyberAnalyst, or RootAdmin"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-sans"
                />
              </div>

              {/* Email */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1 font-mono">
                  Email Address <span className="text-cyan-400">*</span>
                </label>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="operator@company.com or researcher@security.io"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-sans"
                />
              </div>

              {/* Password & Confirm */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1 font-mono">
                    Password (min 8 chars) <span className="text-cyan-400">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      required
                      minLength={8}
                      autoComplete="new-password"
                      placeholder="••••••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full rounded-xl border border-slate-700 bg-slate-900/80 pl-4 pr-10 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-sans"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-2.5 text-xs text-slate-400 hover:text-slate-200"
                    >
                      {showPassword ? "Hide" : "Show"}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1 font-mono">
                    Confirm Password <span className="text-cyan-400">*</span>
                  </label>
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    placeholder="••••••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-sans"
                  />
                </div>
              </div>

              {/* Terms and Conditions */}
              <div className="pt-2">
                <label className="flex items-start gap-2.5 cursor-pointer text-xs text-slate-300 select-none">
                  <input
                    type="checkbox"
                    checked={agreedToTerms}
                    onChange={(e) => setAgreedToTerms(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-500/40"
                  />
                  <span className="leading-snug">
                    I agree to the <span className="text-cyan-400 hover:underline">Terms of Service</span>,{" "}
                    <span className="text-cyan-400 hover:underline">Privacy Policy</span>, and strict Bug Bounty
                    Responsible Disclosure standards.
                    <span className="text-rose-400 ml-1 font-bold">*</span>
                  </span>
                </label>
              </div>

              {/* Already have an account */}
              <div className="text-center pt-2">
                <span className="text-xs text-slate-400">Already registered? </span>
                <Link href="/login" className="text-xs font-bold text-cyan-400 hover:underline font-mono">
                  Sign in here &rarr;
                </Link>
              </div>
            </div>
          </Step>
        )}

        {/* ── SLIDE 2: COMPANIES TO TRACK & PIN ON DASHBOARD ───── */}
        {currentStep === 2 && (
          <Step>
            <div className="space-y-4">
              {/* Header explanation */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-800 pb-3">
                <div>
                  <div className="text-sm font-bold text-white font-display">
                    Pin Companies to Track on Your Dashboard
                  </div>
                  <div className="text-xs text-slate-400">
                    Click to pin organizations into your real-time change stream and telemetry radar.
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/40 font-mono text-xs font-bold text-cyan-300">
                    📌 {pinnedCompanies.length} Pinned
                  </span>
                </div>
              </div>

              {/* Search Bar */}
              <div className="relative">
                <svg className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  placeholder="Search canonical company or domain (e.g. Google, Microsoft, OpenAI, Apple, Stripe)..."
                  value={companySearch}
                  onChange={(e) => setCompanySearch(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/80 pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-sans"
                />
              </div>

              {/* Company Selection Grid */}
              <div className="max-h-72 overflow-y-auto pr-1 space-y-2 scrollbar-thin">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {filteredCompanies.map((c) => {
                    const isPinned = pinnedCompanies.includes(c.name);
                    return (
                      <div
                        key={c.id || c.name}
                        onClick={() => handleTogglePin(c.name)}
                        className={`p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                          isPinned
                            ? "bg-cyan-950/40 border-cyan-500/80 shadow-md shadow-cyan-500/15 ring-1 ring-cyan-500/40"
                            : "bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/90"
                        }`}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div
                            className={`h-9 w-9 rounded-lg flex items-center justify-center font-display font-extrabold text-xs shrink-0 transition ${
                              isPinned
                                ? "bg-cyan-500 text-slate-950 shadow-sm"
                                : "bg-slate-800 text-slate-300 border border-slate-700"
                            }`}
                          >
                            {c.name.slice(0, 2).toUpperCase()}
                          </div>

                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5 truncate">
                              <span className="text-xs font-bold text-white truncate">{c.name}</span>
                              {c.hasBounty && (
                                <span className="px-1.5 py-0.2 rounded bg-emerald-950/80 border border-emerald-800/60 text-[9px] font-mono text-emerald-400">
                                  Bounty
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-slate-400 font-mono truncate">
                              {c.domain} · {c.assetsCount.toLocaleString()} assets
                            </div>
                          </div>
                        </div>

                        <div className="shrink-0">
                          <button
                            type="button"
                            className={`px-2 py-1 rounded-lg text-[10px] font-mono font-bold transition flex items-center gap-1 ${
                              isPinned
                                ? "bg-cyan-500 text-slate-950 shadow-sm"
                                : "bg-slate-800 text-slate-400 hover:text-white"
                            }`}
                          >
                            <span>{isPinned ? "PINNED" : "+ PIN"}</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Custom Add Form */}
              <form onSubmit={handleAddCustomCompany} className="flex items-center gap-2 pt-1 border-t border-slate-800/80">
                <input
                  type="text"
                  placeholder="Want to pin another company or domain? (e.g. target.corp)..."
                  value={customCompanyName}
                  onChange={(e) => setCustomCompanyName(e.target.value)}
                  className="flex-1 rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-cyan-500 font-sans"
                />
                <button
                  type="submit"
                  disabled={!customCompanyName.trim()}
                  className="rounded-xl border border-cyan-800/60 bg-cyan-950/40 px-3 py-2 text-xs font-mono font-bold text-cyan-300 hover:bg-cyan-900/60 disabled:opacity-40 transition"
                >
                  + PIN CUSTOM
                </button>
              </form>
            </div>
          </Step>
        )}

        {/* ── SLIDE 3: PAYMENT & SUBSCRIPTION ──────────────────── */}
        {currentStep === 3 && (
          <Step>
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-800 pb-3">
                <div>
                  <div className="text-sm font-bold text-white font-display">
                    Select Intelligence Tier
                  </div>
                  <div className="text-xs text-slate-400">
                    Activate your workspace and launch directly into the main dashboard.
                  </div>
                </div>

                {/* Monthly vs Annual Toggle */}
                <div className="flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-950 p-1 text-[11px] font-mono">
                  <button
                    type="button"
                    onClick={() => setBillingInterval("monthly")}
                    className={`px-2.5 py-1 rounded transition ${
                      billingInterval === "monthly" ? "bg-cyan-500 text-slate-950 font-bold" : "text-slate-400"
                    }`}
                  >
                    Monthly
                  </button>
                  <button
                    type="button"
                    onClick={() => setBillingInterval("annual")}
                    className={`px-2.5 py-1 rounded transition ${
                      billingInterval === "annual" ? "bg-cyan-500 text-slate-950 font-bold" : "text-slate-400"
                    }`}
                  >
                    Annual (20% OFF)
                  </button>
                </div>
              </div>

              {/* Plans Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* 1. Community Free */}
                <div
                  onClick={() => setSelectedPlan("FREE")}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between ${
                    selectedPlan === "FREE"
                      ? "bg-cyan-950/40 border-cyan-500 shadow-lg shadow-cyan-500/15 ring-1 ring-cyan-500/50"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold text-slate-300 uppercase">Community</span>
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        FREE
                      </span>
                    </div>
                    <div className="mt-2 flex items-baseline gap-1">
                      <span className="text-2xl font-black text-white font-display">$0</span>
                      <span className="text-xs text-slate-400 font-mono">/forever</span>
                    </div>
                    <p className="mt-2 text-[11px] text-slate-400 leading-relaxed">
                      Zero card required. Full access to public bounty directory, KEV feed, and basic diffs.
                    </p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] font-mono text-slate-300 space-y-1">
                    <div>✓ 10 Monitored Targets</div>
                    <div>✓ Daily Diff Snapshots</div>
                    <div>✓ Public Program Graph</div>
                  </div>
                </div>

                {/* 2. Professional Researcher */}
                <div
                  onClick={() => setSelectedPlan("RESEARCHER")}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between relative ${
                    selectedPlan === "RESEARCHER"
                      ? "bg-cyan-950/40 border-cyan-500 shadow-lg shadow-cyan-500/15 ring-1 ring-cyan-500/50"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="absolute -top-2.5 right-3 px-2 py-0.5 rounded-full bg-cyan-500 text-slate-950 font-mono text-[9px] font-extrabold uppercase shadow-sm">
                    MOST POPULAR
                  </div>

                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold text-cyan-400 uppercase">Researcher</span>
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                        PRO
                      </span>
                    </div>
                    <div className="mt-2 flex items-baseline gap-1">
                      <span className="text-2xl font-black text-white font-display">
                        ${billingInterval === "annual" ? "39" : "49"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">/mo</span>
                    </div>
                    <p className="mt-2 text-[11px] text-slate-400 leading-relaxed">
                      Real-time signals, prioritized attack leads, and unlimited AI Threat Analyst access.
                    </p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] font-mono text-slate-300 space-y-1">
                    <div className="text-cyan-300 font-bold">✓ 50 Monitored Targets</div>
                    <div>✓ Real-time Diff Alerts</div>
                    <div>✓ AI Threat Analyst Pro</div>
                  </div>
                </div>

                {/* 3. Enterprise Operations */}
                <div
                  onClick={() => setSelectedPlan("PRO")}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between ${
                    selectedPlan === "PRO"
                      ? "bg-cyan-950/40 border-cyan-500 shadow-lg shadow-cyan-500/15 ring-1 ring-cyan-500/50"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold text-amber-400 uppercase">Enterprise</span>
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800">
                        SCALE
                      </span>
                    </div>
                    <div className="mt-2 flex items-baseline gap-1">
                      <span className="text-2xl font-black text-white font-display">
                        ${billingInterval === "annual" ? "159" : "199"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">/mo</span>
                    </div>
                    <p className="mt-2 text-[11px] text-slate-400 leading-relaxed">
                      Multi-seat teams, continuous hourly sweeps, webhooks, and full audit provenance.
                    </p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] font-mono text-slate-300 space-y-1">
                    <div className="text-amber-300 font-bold">✓ Unlimited Target Graph</div>
                    <div>✓ Hourly Automation</div>
                    <div>✓ Custom Webhooks & API</div>
                  </div>
                </div>
              </div>

              {/* Order / Activation Summary Box */}
              <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-950/80 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 font-sans text-xs">
                <div className="flex items-center gap-2.5">
                  <div className="h-8 w-8 rounded-lg bg-emerald-950/60 border border-emerald-800/50 flex items-center justify-center text-emerald-400 font-bold text-sm">
                    ✓
                  </div>
                  <div>
                    <div className="font-bold text-white">
                      {selectedPlan === "FREE"
                        ? "Community Free Tier Selected"
                        : `${selectedPlan} Tier (${billingInterval === "annual" ? "Annual Billing" : "Monthly Billing"})`}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono">
                      {pinnedCompanies.length} companies will be pre-pinned to your dashboard.
                    </div>
                  </div>
                </div>

                <div className="text-right font-mono">
                  <div className="text-base font-bold text-cyan-400">
                    {selectedPlan === "FREE"
                      ? "$0.00 DUE TODAY"
                      : `$${billingInterval === "annual" ? (selectedPlan === "RESEARCHER" ? "468" : "1908") : (selectedPlan === "RESEARCHER" ? "49" : "199")}.00`}
                  </div>
                  <div className="text-[10px] text-slate-500">
                    {selectedPlan === "FREE" ? "No credit card required" : "14-day risk-free trial"}
                  </div>
                </div>
              </div>
            </div>
          </Step>
        )}
      </Stepper>
    </div>
  );
}
