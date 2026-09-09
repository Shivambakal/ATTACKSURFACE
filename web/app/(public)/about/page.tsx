"use client";

import React, { useState } from "react";
import Link from "next/link";

const PIPELINE_STEPS = [
  {
    step: "01",
    name: "Observe",
    headline: "Non-Intrusive Public Signal Capture",
    description:
      "We passively monitor public internet infrastructure without intrusive scans or exploit payloads. Certificate Transparency (CT) streams, DNS authoritative records, public WHOIS revisions, TLS negotiation states, and HTTP response headers are ingested continuously.",
    signals: ["CT Logs", "Authoritative DNS", "TLS Handshakes", "HTTP Headers", "Robots & Sitemaps"],
    badge: "Passive Collection",
  },
  {
    step: "02",
    name: "Normalize",
    headline: "Canonical Model Synthesis",
    description:
      "Heterogeneous raw data from diverse sources is sanitized, schema-validated, and mapped into standardized asset models. Domain trees, IP blocks, and cloud edge networks are resolved into unified entity representations.",
    signals: ["Apex Domains", "Subdomain Hierarchies", "Cloud Edge IPs", "Service Ports"],
    badge: "Schema Unification",
  },
  {
    step: "03",
    name: "Correlate",
    headline: "Bug Bounty Scope & Program Alignment",
    description:
      "Every identified asset is matched against real-world bug bounty policy scopes across HackerOne, Bugcrowd, Intigriti, and direct enterprise VDPs. We instantly classify assets as In-Scope, Out-of-Scope, or Pending Verification.",
    signals: ["HackerOne Programs", "Bugcrowd Scopes", "Wildcard Rules", "Reward Eligibility"],
    badge: "Policy Alignment",
  },
  {
    step: "04",
    name: "Compare",
    headline: "Temporal State Diffing Engine",
    description:
      "The core differential engine computes the mathematical delta between timestamp T0 (baseline) and T1 (current state). We surface added records, removed endpoints, modified headers, or changed IP pointers.",
    signals: ["Delta Calculations", "Header Drift", "DNS Switchovers", "New Endpoints"],
    badge: "Differential Math",
  },
  {
    step: "05",
    name: "Understand",
    headline: "Security Context & Exposure Derivation",
    description:
      "A raw change is meaningless without context. AttackSurface analyzes the significance: Did a staging subdomain suddenly map to an external SaaS? Was an internal admin path exposed? Did a security header disappear after a deployment?",
    signals: ["Staging Leaks", "Dangling CNAMEs", "Deprecated TLS", "Exposed Admin Panels"],
    badge: "Context Intelligence",
  },
  {
    step: "06",
    name: "Prioritize",
    headline: "Evidence-Based Impact Ranking",
    description:
      "We cross-reference the change against CISA Known Exploited Vulnerabilities (KEV), CVSS severity vectors, and asset scope. High-impact perimeter changes surface immediately to focus researcher attention.",
    signals: ["CISA KEV Matches", "CVSS Vectors", "EPSS Scores", "Scope Criticality"],
    badge: "Triage Optimization",
  },
  {
    step: "07",
    name: "Alert",
    headline: "Cryptographic Evidence Dispatch",
    description:
      "Researchers receive verified signals accompanied by raw HTTP response snapshots, TLS hashes, and timestamped audit trails. No false alarms, no synthetic hype — just actionable evidence ready for ethical investigation.",
    signals: ["Real-Time Dispatch", "Raw Wire Proof", "Verifiable Hashes", "Export Ready"],
    badge: "Verified Proof",
  },
];

export default function AboutPage() {
  const [activeStep, setActiveStep] = useState(0);

  return (
    <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Hero Section */}
      <div className="max-w-3xl space-y-6">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          PHILOSOPHY &amp; ARCHITECTURE
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl lg:text-6xl font-sans">
          Built for researchers who demand <span className="text-cyan-400">truth over noise</span>.
        </h1>

        <p className="text-base sm:text-lg leading-relaxed text-slate-300">
          AttackSurface is a continuous security-change intelligence engine. We monitor public perimeter changes for ethical security researchers and bug bounty hunters — replacing blind port-knocking and noisy scanners with precise temporal diffs and verifiable cryptographic evidence.
        </p>
      </div>

      {/* Core Principles Grid */}
      <div className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-3">
        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6 backdrop-blur-sm">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-mono font-bold text-sm">
            01
          </div>
          <h2 className="mt-4 text-base font-bold text-white">Zero Weaponization</h2>
          <p className="mt-2 text-xs leading-relaxed text-slate-300">
            We never launch exploit payloads, inject fuzzing strings, or attempt unauthorized penetration. We strictly observe public DNS, HTTP headers, and public digital certificates within the boundaries of ethical research.
          </p>
        </div>

        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6 backdrop-blur-sm">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-mono font-bold text-sm">
            02
          </div>
          <h2 className="mt-4 text-base font-bold text-white">Temporal Differentials</h2>
          <p className="mt-2 text-xs leading-relaxed text-slate-300">
            Security flaws almost always appear during change — a routine cloud deploy, a DNS reconfiguration, or a new sub-domain spinup. By diffing state across time, we catch the exact moment vulnerabilities are born.
          </p>
        </div>

        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6 backdrop-blur-sm">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-mono font-bold text-sm">
            03
          </div>
          <h2 className="mt-4 text-base font-bold text-white">Cryptographic Proof</h2>
          <p className="mt-2 text-xs leading-relaxed text-slate-300">
            Every reported event is linked directly to raw response snapshots, timestamped observation hashes, and authoritative upstream sources. No fabricated figures or black-box predictions.
          </p>
        </div>
      </div>

      {/* Interactive Pipeline: How AttackSurface Thinks */}
      <div className="mt-24">
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <span className="font-mono text-xs uppercase tracking-widest text-cyan-400">
            The 7-Stage Intelligence Pipeline
          </span>
          <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
            How AttackSurface Thinks
          </h2>
          <p className="text-xs sm:text-sm text-slate-300">
            From raw public telemetry to actionable research intelligence. Step through each phase of our analysis engine.
          </p>
        </div>

        {/* Step Selector Tabs */}
        <div className="mt-10 flex items-center justify-start sm:justify-center gap-2 overflow-x-auto pb-4 scrollbar-none">
          {PIPELINE_STEPS.map((item, idx) => (
            <button
              key={item.step}
              onClick={() => setActiveStep(idx)}
              className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-mono transition-all whitespace-nowrap ${
                activeStep === idx
                  ? "bg-cyan-500 text-slate-950 font-bold shadow-lg shadow-cyan-500/20"
                  : "bg-white/[0.04] text-slate-300 hover:bg-white/[0.08] hover:text-white border border-white/[0.06]"
              }`}
            >
              <span>{item.step}</span>
              <span>{item.name}</span>
            </button>
          ))}
        </div>

        {/* Active Step Showcase */}
        <div className="mt-6 rounded-3xl border border-white/[0.1] bg-slate-950/70 p-6 sm:p-10 backdrop-blur-xl shadow-2xl">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 lg:gap-12 items-center">
            <div className="lg:col-span-7 space-y-4">
              <div className="inline-flex items-center gap-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 px-3 py-1 font-mono text-xs text-cyan-300">
                <span>STAGE {PIPELINE_STEPS[activeStep].step}</span>
                <span>·</span>
                <span>{PIPELINE_STEPS[activeStep].badge}</span>
              </div>

              <h3 className="text-2xl font-bold text-white sm:text-3xl">
                {PIPELINE_STEPS[activeStep].headline}
              </h3>

              <p className="text-sm leading-relaxed text-slate-300">
                {PIPELINE_STEPS[activeStep].description}
              </p>

              <div className="pt-4">
                <span className="block font-mono text-[11px] uppercase tracking-wider text-slate-300 mb-2">
                  Telemetry Signals Ingested:
                </span>
                <div className="flex flex-wrap gap-2">
                  {PIPELINE_STEPS[activeStep].signals.map((sig) => (
                    <span
                      key={sig}
                      className="rounded-lg bg-white/[0.05] border border-white/[0.1] px-3 py-1 font-mono text-xs text-slate-300"
                    >
                      {sig}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="lg:col-span-5 rounded-2xl border border-white/[0.08] bg-[#02050b] p-5 font-mono text-xs text-slate-300">
              <div className="flex items-center justify-between border-b border-white/[0.08] pb-3 text-[11px] text-slate-300">
                <span>PIPELINE_MONITOR.LOG</span>
                <span className="text-emerald-400 font-bold">STATE: PASS</span>
              </div>
              <div className="space-y-2 pt-3 text-[11px] text-slate-400">
                <p className="text-cyan-400">[00:00:00.012] Initializing Stage {PIPELINE_STEPS[activeStep].step}: {PIPELINE_STEPS[activeStep].name.toUpperCase()}</p>
                <p>[00:00:00.045] Ingesting canonical target telemetry...</p>
                <p>[00:00:00.091] Verifying non-intrusive compliance policy: OK</p>
                <p>[00:00:00.143] Synthesizing differential matrix with baseline T-24h</p>
                <p className="text-emerald-400">[00:00:00.198] Stage complete. Zero synthetic figures applied.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Strip */}
      <div className="mt-24 rounded-3xl border border-cyan-500/30 bg-gradient-to-r from-cyan-950/40 via-slate-950 to-cyan-950/40 p-8 sm:p-12 text-center">
        <h2 className="text-2xl font-bold text-white sm:text-3xl">
          Start tracking perimeter deltas with AttackSurface
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-xs sm:text-sm text-slate-300">
          Join thousands of ethical security researchers monitoring bug bounty targets, scope expansions, and vulnerability timelines.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link
            href="/signup"
            className="rounded-xl bg-cyan-500 px-6 py-3 font-mono text-xs font-bold text-slate-950 shadow-lg shadow-cyan-500/20 hover:bg-cyan-400 transition-all"
          >
            Create Free Account &rarr;
          </Link>
          <Link
            href="/intelligence"
            className="rounded-xl border border-white/[0.1] bg-white/[0.04] px-6 py-3 font-mono text-xs text-slate-300 hover:bg-white/[0.08] hover:text-white transition-all"
          >
            Explore Intelligence Stream
          </Link>
        </div>
      </div>
    </div>
  );
}
