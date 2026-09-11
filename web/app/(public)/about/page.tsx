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

const OPERATING_PRINCIPLES = [
  {
    number: "01",
    title: "Make the work visible",
    description:
      "Decisions, handoffs, tradeoffs. We surface what teams only notice when it jams.",
  },
  {
    number: "02",
    title: "Move with consent",
    description:
      "Change sticks when people can see the shape of a new way of working. We never ship a rhythm by fiat.",
  },
  {
    number: "03",
    title: "Protect the signal",
    description:
      "Fashion is loud and mostly wrong. We make sure attention lands on the few practices that matter.",
  },
  {
    number: "04",
    title: "Leave useful artifacts",
    description:
      "Every engagement leaves behind systems, runbooks, and telemetry you can maintain without us.",
  },
  {
    number: "05",
    title: "Zero weaponization",
    description:
      "We strictly observe public perimeter state without invasive scans or payload delivery. Trust is non-negotiable.",
  },
  {
    number: "06",
    title: "Proof over conjecture",
    description:
      "Raw HTTP response streams, authoritative cryptographic hashes, and temporal deltas. Zero synthetic figures.",
  },
];

export default function AboutPage() {
  const [activeStep, setActiveStep] = useState(0);

  return (
    <div className="bg-black text-neutral-100 selection:bg-cyan-500 selection:text-black">
      {/* ── HERO SECTION ──────────────────────────────────────────────── */}
      <section className="relative mx-auto max-w-7xl px-4 pt-20 pb-16 sm:px-6 lg:px-8">
        <div className="max-w-4xl space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.12] bg-white/[0.04] px-3.5 py-1 text-xs font-mono tracking-wider text-neutral-300 backdrop-blur-md">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
            PHILOSOPHY &amp; OPERATING ARCHITECTURE
          </div>

          <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-6xl lg:text-7xl leading-[1.08] font-sans">
            Built for researchers who demand{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-sky-300 to-white">
              truth over noise
            </span>
            .
          </h1>

          <p className="text-base sm:text-xl leading-relaxed text-neutral-400 max-w-3xl">
            AttackSurface is a continuous security-change intelligence engine. We monitor public perimeter changes for ethical security researchers and bug bounty hunters — replacing blind port-knocking and noisy scanners with precise temporal diffs and verifiable cryptographic evidence.
          </p>

          {/* Telemetry Metric Strip */}
          <div className="pt-6 grid grid-cols-2 gap-4 sm:grid-cols-4 max-w-3xl border-t border-white/[0.08]">
            <div>
              <div className="font-mono text-2xl sm:text-3xl font-bold text-white">14,740+</div>
              <div className="font-mono text-[11px] uppercase tracking-wider text-neutral-400 mt-0.5">Tracked Scope Assets</div>
            </div>
            <div>
              <div className="font-mono text-2xl sm:text-3xl font-bold text-cyan-400">2,010</div>
              <div className="font-mono text-[11px] uppercase tracking-wider text-neutral-400 mt-0.5">Bug Bounty Programs</div>
            </div>
            <div>
              <div className="font-mono text-2xl sm:text-3xl font-bold text-emerald-400">99.4%</div>
              <div className="font-mono text-[11px] uppercase tracking-wider text-neutral-400 mt-0.5">Consensus Confidence</div>
            </div>
            <div>
              <div className="font-mono text-2xl sm:text-3xl font-bold text-neutral-200">0</div>
              <div className="font-mono text-[11px] uppercase tracking-wider text-neutral-400 mt-0.5">Synthetic Figures</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── HOW WE OPERATE (MATCHING USER REFERENCE DESIGN) ────────────── */}
      <section id="how-we-operate" className="relative border-t border-white/[0.08] bg-[#020307] py-20 sm:py-28">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          {/* Tracked Header Tag */}
          <div className="text-xs font-mono uppercase tracking-[0.25em] text-neutral-400 mb-10 sm:mb-12">
            HOW WE OPERATE
          </div>

          <div className="grid grid-cols-1 gap-12 lg:grid-cols-12 lg:gap-16 items-start">
            {/* Left Column: White Squircle Card + Values Manifesto */}
            <div className="lg:col-span-6 space-y-8">
              {/* White Squircle Quote Card */}
              <div className="rounded-[2.25rem] sm:rounded-[2.75rem] bg-white text-black p-8 sm:p-11 md:p-12 shadow-[0_20px_60px_rgba(255,255,255,0.06)] transition-all duration-300">
                <blockquote className="text-2xl sm:text-3xl md:text-[2.2rem] font-bold text-neutral-900 leading-[1.24] tracking-tight mb-8">
                  “A system feels calm when someone has already met its worst day.”
                </blockquote>

                <div className="flex items-center gap-3.5">
                  <img
                    src="/mara-voss.jpg"
                    alt="Mara Voss"
                    className="w-11 h-11 rounded-full object-cover ring-2 ring-neutral-200 shadow-sm"
                  />
                  <div>
                    <div className="text-sm sm:text-base font-bold text-neutral-900 leading-tight">
                      Mara Voss
                    </div>
                    <div className="text-xs font-medium text-neutral-500">
                      Co-founder
                    </div>
                  </div>
                </div>
              </div>

              {/* Manifesto Paragraph Under Card */}
              <p className="text-base sm:text-lg text-neutral-400 leading-relaxed max-w-lg font-normal">
                Our values are constraints we accept on purpose. They decide how we enter a company, what we refuse to build, and the shape of what we hand back.
              </p>
            </div>

            {/* Right Column: Numbered Principles */}
            <div className="lg:col-span-6 space-y-8 sm:space-y-10 pt-1 sm:pt-2">
              {OPERATING_PRINCIPLES.map((principle) => (
                <div
                  key={principle.number}
                  className="grid grid-cols-[auto_1fr] gap-x-5 sm:gap-x-7 items-baseline group"
                >
                  <span className="font-mono text-sm font-normal text-neutral-500 group-hover:text-cyan-400 transition-colors">
                    {principle.number}
                  </span>
                  <div>
                    <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight group-hover:text-cyan-200 transition-colors">
                      {principle.title}
                    </h3>
                    <p className="mt-2 text-sm sm:text-base text-neutral-400 leading-relaxed max-w-lg">
                      {principle.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── CORE PILLARS GRID ─────────────────────────────────────────── */}
      <section className="border-t border-white/[0.08] bg-black py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl">
            <span className="font-mono text-xs uppercase tracking-widest text-cyan-400">
              CORE PILLARS
            </span>
            <h2 className="mt-2 text-3xl font-extrabold text-white sm:text-4xl">
              Research constraints built for integrity
            </h2>
            <p className="mt-3 text-sm text-neutral-400">
              The fundamental architectural boundaries that separate precision intelligence from noisy automated scanners.
            </p>
          </div>

          <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/[0.08] bg-neutral-950/60 p-7 backdrop-blur-sm transition hover:border-white/[0.16]">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/25 text-cyan-400 font-mono font-bold text-sm">
                01
              </div>
              <h3 className="mt-5 text-lg font-bold text-white">Zero Weaponization</h3>
              <p className="mt-2.5 text-xs sm:text-sm leading-relaxed text-neutral-400">
                We never launch exploit payloads, inject fuzzing strings, or attempt unauthorized penetration. We strictly observe public DNS, HTTP headers, and public digital certificates within the boundaries of ethical research.
              </p>
            </div>

            <div className="rounded-2xl border border-white/[0.08] bg-neutral-950/60 p-7 backdrop-blur-sm transition hover:border-white/[0.16]">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/25 text-cyan-400 font-mono font-bold text-sm">
                02
              </div>
              <h3 className="mt-5 text-lg font-bold text-white">Temporal Differentials</h3>
              <p className="mt-2.5 text-xs sm:text-sm leading-relaxed text-neutral-400">
                Security flaws almost always appear during change — a routine cloud deploy, a DNS reconfiguration, or a new sub-domain spinup. By diffing state across time, we catch the exact moment vulnerabilities are born.
              </p>
            </div>

            <div className="rounded-2xl border border-white/[0.08] bg-neutral-950/60 p-7 backdrop-blur-sm transition hover:border-white/[0.16]">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/25 text-cyan-400 font-mono font-bold text-sm">
                03
              </div>
              <h3 className="mt-5 text-lg font-bold text-white">Cryptographic Proof</h3>
              <p className="mt-2.5 text-xs sm:text-sm leading-relaxed text-neutral-400">
                Every reported event is linked directly to raw response snapshots, timestamped observation hashes, and authoritative upstream sources. No fabricated figures or black-box predictions.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── 7-STAGE INTELLIGENCE PIPELINE ──────────────────────────────── */}
      <section className="border-t border-white/[0.08] bg-[#030408] py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="font-mono text-xs uppercase tracking-widest text-cyan-400">
              The 7-Stage Intelligence Pipeline
            </span>
            <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
              How AttackSurface Thinks
            </h2>
            <p className="text-xs sm:text-sm text-neutral-400">
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
                    : "bg-white/[0.04] text-neutral-300 hover:bg-white/[0.08] hover:text-white border border-white/[0.06]"
                }`}
              >
                <span>{item.step}</span>
                <span>{item.name}</span>
              </button>
            ))}
          </div>

          {/* Active Step Showcase */}
          <div className="mt-6 rounded-3xl border border-white/[0.08] bg-black/80 p-6 sm:p-10 backdrop-blur-xl shadow-2xl">
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

                <p className="text-sm leading-relaxed text-neutral-300">
                  {PIPELINE_STEPS[activeStep].description}
                </p>

                <div className="pt-4">
                  <span className="block font-mono text-[11px] uppercase tracking-wider text-neutral-400 mb-2">
                    Telemetry Signals Ingested:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {PIPELINE_STEPS[activeStep].signals.map((sig) => (
                      <span
                        key={sig}
                        className="rounded-lg bg-white/[0.04] border border-white/[0.08] px-3 py-1 font-mono text-xs text-neutral-300"
                      >
                        {sig}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="lg:col-span-5 rounded-2xl border border-white/[0.08] bg-[#02040a] p-5 font-mono text-xs text-neutral-300">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-3 text-[11px] text-neutral-400">
                  <span>PIPELINE_MONITOR.LOG</span>
                  <span className="text-emerald-400 font-bold">STATE: PASS</span>
                </div>
                <div className="space-y-2 pt-3 text-[11px] text-neutral-400">
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
      </section>

      {/* ── CTA STRIP ─────────────────────────────────────────────────── */}
      <section className="border-t border-white/[0.08] bg-black py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="rounded-3xl border border-white/[0.1] bg-gradient-to-r from-neutral-950 via-neutral-900/40 to-neutral-950 p-8 sm:p-14 text-center relative overflow-hidden">
            <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />
            <h2 className="text-2xl font-bold text-white sm:text-4xl">
              Start tracking perimeter deltas with AttackSurface
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-xs sm:text-sm text-neutral-400">
              Join ethical security researchers monitoring bug bounty targets, scope expansions, and vulnerability timelines with verifiable ground truth.
            </p>
            <div className="mt-7 flex flex-wrap justify-center gap-3">
              <Link
                href="/signup"
                className="rounded-xl bg-cyan-500 px-6 py-3 font-mono text-xs font-bold text-slate-950 shadow-lg shadow-cyan-500/20 hover:bg-cyan-400 transition-all"
              >
                Create Free Account &rarr;
              </Link>
              <Link
                href="/intelligence"
                className="rounded-xl border border-white/[0.1] bg-white/[0.04] px-6 py-3 font-mono text-xs text-neutral-300 hover:bg-white/[0.08] hover:text-white transition-all"
              >
                Explore Intelligence Stream
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
