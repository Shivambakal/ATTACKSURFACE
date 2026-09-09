"use client";

import React, { useState } from "react";
import Link from "next/link";

interface TimelineMilestone {
  date: string;
  era: "HISTORICAL" | "BASELINE" | "ACTIVE_OBSERVATION";
  title: string;
  summary: string;
  assetCount: number;
  deltaType: string;
  evidence: string;
}

const MILESTONES: TimelineMilestone[] = [
  {
    date: "March 2025",
    era: "HISTORICAL",
    title: "Legacy Monolith & Single Data Center Baseline",
    summary:
      "Historical DNS records and WHOIS registrations show an on-premises physical data center with two monolithic web servers (nginx/1.18). Single wildcard SSL certificate.",
    assetCount: 14,
    deltaType: "Archive Baseline",
    evidence: "Historical WHOIS archive & Wayback Machine snapshots",
  },
  {
    date: "October 2025",
    era: "BASELINE",
    title: "Cloud Migration to AWS & Cloudflare CDN Edge",
    summary:
      "Perimeter shifted to Amazon AWS (us-east-1). DNS zone delegated to Cloudflare Anycast nameservers. 38 new subdomains provisioned for microservices.",
    assetCount: 52,
    deltaType: "Infrastructure Migration",
    evidence: "Certificate Transparency issuance & DNS SOA shift",
  },
  {
    date: "January 2026",
    era: "ACTIVE_OBSERVATION",
    title: "Kubernetes Staging Ingress Exposed During Release",
    summary:
      "A fast automated release exposed an unprotected internal k8s ingress controller with debug metrics on port 8443. AttackSurface flagged delta within 45 seconds.",
    assetCount: 68,
    deltaType: "Perimeter Regression",
    evidence: "Cryptographic HTTP response header delta (SHA-256 verified)",
  },
  {
    date: "Present (September 2026)",
    era: "ACTIVE_OBSERVATION",
    title: "Continuous Real-Time Delta Tracking",
    summary:
      "AttackSurface maintains 60-second temporal diffing across 94 tracked company assets. All scope changes, DNS modifications, and TLS expirations monitored live.",
    assetCount: 94,
    deltaType: "Continuous Surveillance",
    evidence: "Multi-source real-time ingestion stream",
  },
];

export default function TimelinePage() {
  const [selectedMilestone, setSelectedMilestone] = useState<TimelineMilestone>(MILESTONES[2]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="max-w-3xl space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          TEMPORAL TIME MACHINE
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          The Temporal Spine: <span className="text-cyan-400">Time-Travel Your Targets</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          Traditional scanners only see today. AttackSurface maintains a complete historical ledger of perimeter state, enabling researchers to rewind targets to earlier deployments, compare deltas over months, and spot lingering misconfigurations.
        </p>
      </div>

      {/* Interactive Milestone Explorer */}
      <div className="mt-14 grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* Left Spine (Span 5) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-300 mb-2">
            Target Evolution Milestones
          </div>

          <div className="relative border-l border-white/[0.1] pl-6 space-y-6">
            {MILESTONES.map((m) => {
              const isSelected = selectedMilestone.date === m.date;
              return (
                <div
                  key={m.date}
                  onClick={() => setSelectedMilestone(m)}
                  className={`cursor-pointer rounded-2xl p-4 border transition-all relative ${
                    isSelected
                      ? "bg-cyan-500/15 border-cyan-500/40 text-white shadow-lg shadow-cyan-500/10"
                      : "bg-white/[0.02] border-white/[0.06] text-slate-300 hover:border-white/[0.2] hover:text-white"
                  }`}
                >
                  <div
                    className={`absolute -left-[31px] top-5 h-3 w-3 rounded-full border-2 transition-all ${
                      isSelected
                        ? "border-cyan-400 bg-cyan-400 shadow-[0_0_10px_#06b6d4]"
                        : "border-slate-600 bg-slate-950"
                    }`}
                  />
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-cyan-400">{m.date}</span>
                    <span
                      className={`rounded px-1.5 py-0.2 font-mono text-[9px] font-bold border ${
                        m.era === "ACTIVE_OBSERVATION"
                          ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                          : "bg-white/[0.05] text-slate-300 border-white/[0.1]"
                      }`}
                    >
                      {m.era.replace("_", " ")}
                    </span>
                  </div>
                  <h3 className="mt-1 font-bold text-sm text-white">{m.title}</h3>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Detail Pane (Span 7) */}
        <div className="lg:col-span-7 rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-6">
          <div className="border-b border-white/[0.08] pb-4">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-cyan-400">{selectedMilestone.date}</span>
              <span className="text-slate-600">·</span>
              <span className="font-mono text-xs text-slate-300">{selectedMilestone.deltaType}</span>
            </div>
            <h2 className="mt-2 text-2xl font-bold text-white">{selectedMilestone.title}</h2>
          </div>

          <div className="space-y-4">
            <div>
              <span className="font-mono text-[11px] uppercase tracking-wider text-slate-300 block">
                Perimeter Delta Analysis
              </span>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">
                {selectedMilestone.summary}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4 rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4 font-mono text-xs">
              <div>
                <span className="text-slate-300 block text-[10px]">Tracked Assets at Timestamp</span>
                <span className="text-xl font-bold text-cyan-400 mt-1 block">
                  {selectedMilestone.assetCount} Entities
                </span>
              </div>
              <div>
                <span className="text-slate-300 block text-[10px]">Evidence Provenance</span>
                <span className="text-slate-200 mt-1 block text-xs">
                  {selectedMilestone.evidence}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-white/[0.08] flex items-center justify-between">
            <span className="text-xs text-slate-300 font-mono">
              Temporal diffing verified with cryptographic immutability.
            </span>
            <Link
              href="/signup"
              className="rounded-xl bg-cyan-500 px-4 py-2 font-mono text-xs font-bold text-slate-950 hover:bg-cyan-400 transition"
            >
              Scrub Target Timelines &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
