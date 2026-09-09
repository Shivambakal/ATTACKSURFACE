"use client";

import React from "react";
import Link from "next/link";

interface ChangelogRelease {
  version: string;
  date: string;
  badge?: string;
  highlights: string;
  changes: {
    type: "Added" | "Improved" | "Security" | "Fixed";
    text: string;
  }[];
}

const RELEASES: ChangelogRelease[] = [
  {
    version: "v2.4.0",
    date: "September 08, 2026",
    badge: "Latest Release",
    highlights:
      "CISA KEV live synchronization, public evidence explorer, 14,740 scope rules synchronized across 2,010 programs.",
    changes: [
      { type: "Added", text: "Real-time CISA Known Exploited Vulnerabilities (KEV) synchronization with automated perimeter matching." },
      { type: "Added", text: "Interactive Cryptographic Evidence Inspector supporting RFC-compliant JSON export." },
      { type: "Improved", text: "Multi-platform program directory scaling to 2,010 live programs across HackerOne, Bugcrowd, and enterprise VDPs." },
      { type: "Security", text: "Strict zero-weaponization policy enforcement: non-intrusive rate limiting and read-only telemetry audits." },
    ],
  },
  {
    version: "v2.3.0",
    date: "August 15, 2026",
    highlights:
      "Temporal Time Machine architecture, DNS CNAME takeover detection, and real-time security signal card upgrades.",
    changes: [
      { type: "Added", text: "Temporal Time Machine scrubbing spine for tracking historical perimeter shifts over 12+ months." },
      { type: "Added", text: "Automated dangling CNAME detection for AWS S3, Azure TrafficManager, and GitHub Pages." },
      { type: "Improved", text: "Differential calculation speed: sub-minute delta detection on authoritative DNS modifications." },
      { type: "Fixed", text: "Resolved edge-case normalization for internationalized domain names (IDN) in Certificate Transparency stream." },
    ],
  },
  {
    version: "v2.2.0",
    date: "July 01, 2026",
    highlights:
      "Cryptographic SHA-256 evidence anchoring, multi-platform bug bounty scope integration, and researcher watchlist alerts.",
    changes: [
      { type: "Added", text: "SHA-256 cryptographic hash generation for every wire-level HTTP response and DNS zone snapshot." },
      { type: "Added", text: "Custom researcher watchlists with real-time browser notifications on scope expansions." },
      { type: "Improved", text: "Scope wildcard matching engine supporting nested subdomains and CIDR block evaluation." },
    ],
  },
  {
    version: "v2.0.0",
    date: "May 10, 2026",
    highlights:
      "Official launch of the AttackSurface continuous security-change intelligence engine.",
    changes: [
      { type: "Added", text: "Initial release of AttackSurface Timeline: 9-stage intelligence pipeline, canonical company modeling, and differential temporal database." },
      { type: "Added", text: "Passive crawler fleet observing public internet signals with zero payload injection." },
    ],
  },
];

export default function ChangelogPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          PRODUCT RELEASES &amp; UPDATES
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          AttackSurface <span className="text-cyan-400">Changelog</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          Tracking the ongoing evolution of our continuous security-change intelligence platform. Every release is built to provide ethical researchers with verified truth over noise.
        </p>
      </div>

      {/* Release List */}
      <div className="mt-14 space-y-12">
        {RELEASES.map((rel) => (
          <div
            key={rel.version}
            className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-6"
          >
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] pb-4">
              <div className="flex items-center gap-3">
                <span className="font-mono text-xl font-bold text-white">{rel.version}</span>
                {rel.badge && (
                  <span className="rounded bg-cyan-500/20 border border-cyan-500/40 px-2 py-0.5 font-mono text-[10px] font-bold text-cyan-300">
                    {rel.badge}
                  </span>
                )}
              </div>
              <span className="font-mono text-xs text-slate-300">{rel.date}</span>
            </div>

            <p className="text-sm text-slate-200 leading-relaxed font-medium">
              {rel.highlights}
            </p>

            {/* Changes List */}
            <div className="space-y-2.5">
              {rel.changes.map((ch, idx) => (
                <div key={idx} className="flex items-start gap-3 text-xs">
                  <span
                    className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-bold shrink-0 ${
                      ch.type === "Added"
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                        : ch.type === "Improved"
                        ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                        : ch.type === "Security"
                        ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                        : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                    }`}
                  >
                    {ch.type.toUpperCase()}
                  </span>
                  <span className="text-slate-300 leading-relaxed">{ch.text}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-16 text-center">
        <Link
          href="/roadmap"
          className="inline-flex items-center gap-2 font-mono text-xs font-bold text-cyan-400 hover:text-cyan-300"
        >
          <span>View Future Product Roadmap</span>
          <span>&rarr;</span>
        </Link>
      </div>
    </div>
  );
}
