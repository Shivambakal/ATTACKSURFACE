"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

const ROLES = [
  { id: "Bug bounty hunter", label: "Bug Bounty Hunter", icon: "🎯", desc: "Finding fresh attack surfaces and bounty scope" },
  { id: "Application security", label: "AppSec Engineer", icon: "🛡️", desc: "Securing applications and corporate infrastructure" },
  { id: "Product security", label: "Product Security", icon: "📦", desc: "Securing product releases and third-party dependencies" },
  { id: "Pentester", label: "Penetration Tester", icon: "⚔️", desc: "Red teaming, adversary emulation, and vulnerability assessment" },
  { id: "Security researcher", label: "Security Researcher", icon: "🔬", desc: "Vulnerability analysis, exploit research, and 0-day discovery" },
  { id: "SOC/security analyst", label: "SOC / Threat Intel Analyst", icon: "📡", desc: "Threat hunting, telemetry correlation, and incident triage" },
  { id: "Developer", label: "Software Engineer", icon: "💻", desc: "Writing secure software and monitoring supply chains" },
  { id: "Student", label: "Student / Learner", icon: "🎓", desc: "Educational security research and skill building" },
];

const PURPOSES = [
  { id: "Find new attack surface", label: "Discover New Attack Surface", desc: "Find newly exposed subdomains, hosts, and services" },
  { id: "Track company changes", label: "Track Corporate & Tech Changes", desc: "Monitor release notes, stack changes, and migrations" },
  { id: "Research vulnerabilities", label: "Research Exploitable Vulnerabilities", desc: "Track CISA KEV feeds, CVEs, and vendor advisories" },
  { id: "Monitor programs", label: "Monitor Bug Bounty Scope", desc: "Stay informed on scope changes and target rules" },
  { id: "Historical security research", label: "Historical Timeline Analysis", desc: "Analyze how organizations remediate security events over time" },
  { id: "Team intelligence", label: "Share Intelligence with Team", desc: "Export intelligence packages for team workflows" },
];

const INTEL_OPTIONS = [
  { id: "vulnerabilities", label: "CISA KEV & Exploited CVEs", desc: "Live Known Exploited Vulnerabilities" },
  { id: "new_assets", label: "Discovered Subdomains & Assets", desc: "Real-time attack surface expansion" },
  { id: "scope_changes", label: "Scope Inclusions & Exclusions", desc: "Bounty program boundary changes" },
  { id: "technology_changes", label: "Technology Stack Diffs", desc: "Framework and CDN shifts" },
  { id: "security_events", label: "Confirmed Company Security Events", desc: "High-confidence security incidents" },
  { id: "timelines", label: "Historical Security Timelines", desc: "Long-term security evolution" },
];

const LEVELS = [
  { id: "Beginner", label: "Beginner", desc: "Getting started in security research" },
  { id: "Intermediate", label: "Intermediate", desc: "Comfortable with recon tools & vulnerability classes" },
  { id: "Advanced", label: "Advanced", desc: "Active researcher with multiple disclosures / bounties" },
  { id: "Expert", label: "Expert", desc: "Specialized researcher, zero-day discoverer, or team lead" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [role, setRole] = useState("Bug bounty hunter");
  const [purpose, setPurpose] = useState("Find new attack surface");
  const [intelligence, setIntelligence] = useState<string[]>(["vulnerabilities", "new_assets", "scope_changes"]);
  const [level, setLevel] = useState("Intermediate");
  const [targets, setTargets] = useState("");
  const [saving, setSaving] = useState(false);

  const toggleIntel = (id: string) => {
    setIntelligence((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleFinish = async (skip: boolean = false) => {
    setSaving(true);
    try {
      if (!skip) {
        const targetList = targets
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean);

        await apiFetch("/api/v1/profile/onboarding", {
          method: "POST",
          body: JSON.stringify({
            researcher_type: role,
            main_purpose: purpose,
            preferred_intelligence: intelligence,
            experience_level: level,
            targets_of_interest: targetList,
          }),
        });
      }
      router.push("/dashboard");
    } catch (err) {
      console.error("Failed to complete onboarding:", err);
      router.push("/dashboard");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col justify-between p-4 sm:p-8 md:p-12 relative overflow-x-hidden overflow-y-auto font-sans">
      {/* Background glowing gradients */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Top Header */}
      <div className="relative z-10 flex items-center justify-between max-w-4xl mx-auto w-full pb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center font-bold text-black text-sm">
            AS
          </div>
          <span className="font-bold text-sm tracking-wider uppercase text-slate-200">
            AttackSurface Timeline
          </span>
        </div>
        <button
          onClick={() => handleFinish(true)}
          className="text-xs font-mono text-cyan-400 hover:text-cyan-300 transition bg-cyan-950/40 border border-cyan-500/30 px-3 py-1.5 rounded-lg"
        >
          Skip to Dashboard →
        </button>
      </div>

      {/* Step Container */}
      <div className="relative z-10 max-w-4xl mx-auto w-full py-4 flex-1 flex flex-col justify-between">
        {/* Step Indicator */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-2">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  i === step
                    ? "w-8 bg-cyan-400"
                    : i < step
                    ? "w-4 bg-cyan-800"
                    : "w-4 bg-slate-800"
                }`}
              />
            ))}
          </div>
          <span className="text-xs font-mono text-slate-500">
            Step {step} of 6
          </span>
        </div>

        {/* Step 1: Welcome */}
        {step === 1 && (
          <div className="space-y-6">
            <span className="px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-400 text-xs font-mono">
              GETTING STARTED
            </span>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Welcome to AttackSurface Timeline
            </h1>
            <p className="text-sm text-slate-300 leading-relaxed max-w-xl">
              A high-precision research intelligence platform tracking 304 canonical companies, live CISA KEV feeds,
              authorized attack surfaces, and temporal security milestones with zero fabricated records.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4">
              <div className="rounded-xl p-4 bg-slate-950/80 border border-slate-800">
                <span className="text-cyan-400 text-xl font-bold font-mono">304</span>
                <p className="text-xs font-semibold text-white mt-1">Canonical Companies</p>
                <p className="text-[11px] text-slate-400 mt-1">Verified corporate intelligence</p>
              </div>
              <div className="rounded-xl p-4 bg-slate-950/80 border border-slate-800">
                <span className="text-emerald-400 text-xl font-bold font-mono">LIVE</span>
                <p className="text-xs font-semibold text-white mt-1">CISA KEV Engine</p>
                <p className="text-[11px] text-slate-400 mt-1">Direct official government feed</p>
              </div>
              <div className="rounded-xl p-4 bg-slate-950/80 border border-slate-800">
                <span className="text-blue-400 text-xl font-bold font-mono">100%</span>
                <p className="text-xs font-semibold text-white mt-1">Cryptographic Provenance</p>
                <p className="text-[11px] text-slate-400 mt-1">SHA-256 verifiable snapshots</p>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Primary Role */}
        {step === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">What is your primary role?</h2>
              <p className="text-xs text-slate-400 mt-1">We customize your dashboard view based on what matters to you most.</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {ROLES.map((r) => (
                <div
                  key={r.id}
                  onClick={() => setRole(r.id)}
                  className={`cursor-pointer rounded-xl p-4 border transition flex items-start gap-3 ${
                    role === r.id
                      ? "bg-slate-900 border-cyan-500 shadow-md shadow-cyan-500/10 ring-1 ring-cyan-500"
                      : "bg-slate-950/80 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <span className="text-2xl">{r.icon}</span>
                  <div>
                    <h3 className="text-sm font-semibold text-white">{r.label}</h3>
                    <p className="text-xs text-slate-400 mt-0.5">{r.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 3: Main Purpose */}
        {step === 3 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">What is your primary research objective?</h2>
              <p className="text-xs text-slate-400 mt-1">This prioritizes key intelligence widgets on your default screen.</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {PURPOSES.map((p) => (
                <div
                  key={p.id}
                  onClick={() => setPurpose(p.id)}
                  className={`cursor-pointer rounded-xl p-4 border transition ${
                    purpose === p.id
                      ? "bg-slate-900 border-cyan-500 shadow-md shadow-cyan-500/10 ring-1 ring-cyan-500"
                      : "bg-slate-950/80 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <h3 className="text-sm font-semibold text-white">{p.label}</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">{p.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 4: Preferred Intelligence */}
        {step === 4 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">Which intelligence feeds do you care about?</h2>
              <p className="text-xs text-slate-400 mt-1">Select all intelligence categories relevant to your workflow.</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {INTEL_OPTIONS.map((opt) => {
                const active = intelligence.includes(opt.id);
                return (
                  <div
                    key={opt.id}
                    onClick={() => toggleIntel(opt.id)}
                    className={`cursor-pointer rounded-xl p-4 border transition flex items-start justify-between gap-3 ${
                      active
                        ? "bg-slate-900 border-cyan-500 shadow-md shadow-cyan-500/10 ring-1 ring-cyan-500"
                        : "bg-slate-950/80 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div>
                      <h3 className="text-sm font-semibold text-white">{opt.label}</h3>
                      <p className="text-xs text-slate-400 mt-0.5">{opt.desc}</p>
                    </div>
                    <div className={`w-4 h-4 rounded border flex items-center justify-center mt-0.5 ${
                      active ? "bg-cyan-500 border-cyan-400" : "border-slate-700"
                    }`}>
                      {active && <span className="text-black text-xs font-bold">✓</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Step 5: Experience Level */}
        {step === 5 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">What is your experience level?</h2>
              <p className="text-xs text-slate-400 mt-1">Helps calibrate technical depth and detail level.</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {LEVELS.map((lvl) => (
                <div
                  key={lvl.id}
                  onClick={() => setLevel(lvl.id)}
                  className={`cursor-pointer rounded-xl p-5 border transition ${
                    level === lvl.id
                      ? "bg-slate-900 border-cyan-500 shadow-md shadow-cyan-500/10 ring-1 ring-cyan-500"
                      : "bg-slate-950/80 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <h3 className="text-base font-bold text-white">{lvl.label}</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">{lvl.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 6: Targets of Interest */}
        {step === 6 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">Any specific targets or programs of interest?</h2>
              <p className="text-xs text-slate-400 mt-1">Optional. Enter comma-separated company names or domains.</p>
            </div>
            <div className="space-y-3">
              <input
                type="text"
                value={targets}
                onChange={(e) => setTargets(e.target.value)}
                placeholder="e.g. google.com, microsoft.com, cloudflare.com"
                className="w-full px-4 py-3 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-slate-500 text-sm focus:border-cyan-500 focus:outline-none transition"
              />
              <p className="text-xs text-slate-500">
                You can add or update your watchlist anytime from the Watchlist tab.
              </p>
            </div>
          </div>
        )}

        {/* Step Navigation Controls */}
        <div className="sticky bottom-0 z-20 flex items-center justify-between pt-6 pb-2 border-t border-slate-800/80 mt-8 bg-black/95 backdrop-blur-md">
          {step > 1 ? (
            <button
              onClick={() => setStep((s) => s - 1)}
              className="px-5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs font-semibold text-slate-200 hover:bg-slate-800 transition"
            >
              ← Back
            </button>
          ) : (
            <div />
          )}

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleFinish(true)}
              className="text-xs font-mono text-slate-400 hover:text-white px-3 py-2 transition"
            >
              Skip
            </button>
            {step < 6 ? (
              <button
                onClick={() => setStep((s) => s + 1)}
                className="px-7 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-black font-extrabold text-xs transition shadow-lg shadow-cyan-500/25"
              >
                Continue →
              </button>
            ) : (
              <button
                onClick={() => handleFinish(false)}
                disabled={saving}
                className="px-7 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-extrabold text-xs transition shadow-lg shadow-cyan-500/25 disabled:opacity-50"
              >
                {saving ? "Personalizing..." : "Complete Setup & Launch 🚀"}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Footer */}
      <div className="relative z-10 text-center text-xs text-slate-600 font-mono">
        ATTACKSURFACE TIMELINE • ZERO FABRICATION GUARANTEE
      </div>
    </div>
  );
}
