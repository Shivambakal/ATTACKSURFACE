"use client";

import React from "react";
import Link from "next/link";

interface RoadmapItem {
  title: string;
  desc: string;
  tag: string;
}

interface RoadmapColumn {
  status: string;
  badgeColor: string;
  items: RoadmapItem[];
}

const ROADMAP: RoadmapColumn[] = [
  {
    status: "Shipped",
    badgeColor: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    items: [
      {
        title: "CISA KEV Live Synchronization",
        desc: "Automated ingestion and correlation of 1,695+ actively exploited CVEs against perimeter assets.",
        tag: "Intelligence",
      },
      {
        title: "2,010 Bug Bounty Programs Directory",
        desc: "Full indexing of 14,740 wildcard scope rules across HackerOne, Bugcrowd, and private VDPs.",
        tag: "Scopes",
      },
      {
        title: "Cryptographic Evidence Engine",
        desc: "RFC-compliant evidence bundles with wire-level HTTP headers and SHA-256 validation.",
        tag: "Evidence",
      },
      {
        title: "Temporal Time Machine",
        desc: "Historical baseline diffing enabling researchers to scrub target state back 12 months.",
        tag: "Architecture",
      },
    ],
  },
  {
    status: "In Progress (Now)",
    badgeColor: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
    items: [
      {
        title: "Sub-30s Authoritative DNS Diffing",
        desc: "High-frequency SOA polling to detect CNAME switchovers and record modifications faster.",
        tag: "Performance",
      },
      {
        title: "Automated Dangling CNAME Takeover Triggers",
        desc: "Continuous detection of dangling CNAME records pointing to unclaimed S3, Azure, and Heroku slots.",
        tag: "Detection",
      },
      {
        title: "GraphQL Schema Drift Detection",
        desc: "Diffing introspection responses between deployments to highlight new admin queries and mutations.",
        tag: "API Intel",
      },
    ],
  },
  {
    status: "Planned (Next)",
    badgeColor: "bg-purple-500/20 text-purple-300 border-purple-500/30",
    items: [
      {
        title: "Autonomous Cloud Bucket Leakage Diffing",
        desc: "Monitoring newly referenced storage buckets in JavaScript bundles for public read/write misconfigurations.",
        tag: "Cloud",
      },
      {
        title: "SARIF & STIX/TAXII Export Standardization",
        desc: "Exporting verified evidence bundles into standardized threat intelligence formats.",
        tag: "Integrations",
      },
      {
        title: "Team Watchlists & Shared Annotations",
        desc: "Multi-seat collaborative target tracking and internal triage tags for enterprise red teams.",
        tag: "Collaboration",
      },
    ],
  },
  {
    status: "Exploring",
    badgeColor: "bg-amber-500/20 text-amber-300 border-amber-500/30",
    items: [
      {
        title: "BGP Route Leak & Hijack Telemetry",
        desc: "Detecting anomalous ASN route advertisements and RPKI invalidity affecting target perimeters.",
        tag: "Network",
      },
      {
        title: "Zero-Knowledge Proof of Discovery",
        desc: "Verifiable cryptographic proofs of perimeter change timestamping without leaking underlying target assets.",
        tag: "Cryptography",
      },
    ],
  },
];

export default function RoadmapPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="max-w-3xl space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          RESEARCH &amp; PRODUCT DIRECTION
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          Engineering <span className="text-cyan-400">Roadmap</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          Our public commitment to continuous advancement. We build openly, prioritizing features that give ethical researchers actionable signals without noise or synthetic fabrication.
        </p>
      </div>

      {/* Kanban Grid */}
      <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {ROADMAP.map((col) => (
          <div key={col.status} className="space-y-4">
            {/* Column Header */}
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <span className="font-mono text-xs font-bold text-white uppercase">{col.status}</span>
              <span className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold border ${col.badgeColor}`}>
                {col.items.length} Items
              </span>
            </div>

            {/* Column Cards */}
            <div className="space-y-3">
              {col.items.map((item) => (
                <div
                  key={item.title}
                  className="rounded-2xl border border-white/[0.08] bg-slate-950/80 p-5 backdrop-blur-xl space-y-2.5 hover:border-white/[0.2] transition-colors"
                >
                  <span className="rounded bg-white/[0.05] border border-white/[0.1] px-2 py-0.5 font-mono text-[9px] text-slate-300 font-medium">
                    {item.tag}
                  </span>
                  <h3 className="font-bold text-sm text-white">{item.title}</h3>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Feature Request Strip */}
      <div className="mt-20 rounded-3xl border border-white/[0.08] bg-white/[0.02] p-8 text-center space-y-3">
        <h2 className="text-xl font-bold text-white">Have an idea or feature request?</h2>
        <p className="text-xs text-slate-300 max-w-md mx-auto">
          We actively shape our roadmap around researcher needs. Reach out to our intelligence desk with your recommendations.
        </p>
        <div className="pt-2">
          <Link
            href="/contact"
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-2.5 font-mono text-xs font-bold text-slate-950 hover:bg-cyan-400 transition"
          >
            <span>Submit Feature Recommendation</span>
            <span>&rarr;</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
