"use client";

import React, { useState } from "react";
import Link from "next/link";

interface DocSection {
  id: string;
  category: string;
  title: string;
  content: string[];
  codeSnippet?: string;
}

const DOCS: DocSection[] = [
  {
    id: "getting-started",
    category: "Basics",
    title: "Getting Started with AttackSurface",
    content: [
      "AttackSurface is a non-intrusive continuous intelligence platform designed for ethical security researchers and bug bounty professionals.",
      "Unlike active vulnerability scanners that bombard targets with invasive HTTP payloads, AttackSurface observes public perimeter signals: Certificate Transparency logs, authoritative DNS changes, HTTP response headers, and TLS handshake states.",
      "To start monitoring targets: 1) Browse the Bug Bounty Programs directory, 2) Select in-scope targets to add to your Watchlist, and 3) Configure real-time alerts to be notified the moment perimeter state diverges.",
    ],
  },
  {
    id: "scope-rules",
    category: "Architecture",
    title: "Scope Rules & Wildcard Matching Syntax",
    content: [
      "AttackSurface synchronizes scope definitions directly from major bug bounty platforms (HackerOne, Bugcrowd, Intigriti) and private VDPs.",
      "Scope rules are evaluated using hierarchical pattern matching:",
      "• `*.domain.com`: Matches all subdomains (e.g. `api.domain.com`, `auth.dev.domain.com`).",
      "• `domain.com`: Matches exact apex domain only.",
      "• `198.51.100.0/24`: Matches any IP within the CIDR block.",
      "Assets marked with 'Out-of-Scope' in platform policies are flagged with warning badges to prevent researchers from submitting non-qualifying findings.",
    ],
    codeSnippet: `// Example Scope Rule Evaluation
{
  "pattern": "*.payments.target.com",
  "rule_type": "WILDCARD_DOMAIN",
  "scope_status": "IN_SCOPE",
  "bounty_eligible": true,
  "max_payout_usd": 5000
}`,
  },
  {
    id: "temporal-diffs",
    category: "Intelligence",
    title: "Understanding Temporal Differentials",
    content: [
      "The core differentiator of AttackSurface is its mathematical diffing engine. When an asset's state changes, a differential event is created comparing T0 (baseline) to T1 (new observation).",
      "Key diff types detected automatically:",
      "1. DNS Record Changes: CNAME shifts, new A/AAAA records, SOA updates.",
      "2. Header Drift: Disappearance of security headers (CSP, HSTS, X-Frame-Options), CORS wildcard permissions.",
      "3. TLS Certificate Issuance: Pre-issuance detection via Certificate Transparency logs before DNS is active.",
      "4. New Endpoints: Newly exposed HTTP paths detected via sitemaps, robots.txt, and public APIs.",
    ],
  },
  {
    id: "evidence-verification",
    category: "Evidence",
    title: "Verifying Cryptographic Evidence Chains",
    content: [
      "Bug bounty triage teams frequently reject reports due to lack of reproducible proof. AttackSurface generates RFC-compliant evidence bundles for every detected delta.",
      "Each evidence bundle includes:",
      "• Full raw HTTP response headers with timestamps (RFC 3339).",
      "• Upstream authoritative DNS resolver query responses.",
      "• SHA-256 cryptographic checksum of raw telemetry.",
      "You can export evidence bundles in JSON format directly into your bug report submissions.",
    ],
    codeSnippet: `curl -s -H "Authorization: Bearer <TOKEN>" \\
  https://api.attacksurface.online/api/v1/security-intelligence/events?limit=10`,
  },
  {
    id: "safe-scanning",
    category: "Compliance",
    title: "Safe Harbor & Non-Intrusive Observation",
    content: [
      "AttackSurface operates under strict Zero-Weaponization standards:",
      "• We never send injection strings (SQLi, XSS payloads, SSTI, or buffer overflows).",
      "• All HTTP collection uses standard, non-destructive GET or HEAD requests.",
      "• Rate limiting is strictly enforced (≤ 1 request per second per domain).",
      "• Robots.txt and crawler policies are respected at all times.",
      "This ensures that using AttackSurface will never trigger WAF bans, disrupt target availability, or violate bug bounty code-of-conduct guidelines.",
    ],
  },
];

export default function DocsPage() {
  const [activeDoc, setActiveDoc] = useState<DocSection>(DOCS[0]);
  const [searchFilter, setSearchFilter] = useState("");

  const filteredDocs = DOCS.filter(
    (d) =>
      d.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
      d.category.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="max-w-3xl space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          RESEARCHER DOCUMENTATION
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          AttackSurface <span className="text-cyan-400">Documentation</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          Comprehensive guides, architecture overviews, and best practices for leveraging continuous security-change intelligence in your research workflows.
        </p>

        {/* Search input */}
        <div className="pt-2">
          <input
            type="text"
            placeholder="Search documentation guides..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full sm:w-96 rounded-xl border border-white/[0.1] bg-white/[0.03] px-4 py-2.5 font-mono text-xs text-white placeholder:text-slate-400 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400"
          />
        </div>
      </div>

      {/* Docs Layout */}
      <div className="mt-12 grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* Sidebar Nav (Span 4) */}
        <div className="lg:col-span-4 space-y-2 font-mono text-xs">
          <div className="text-[11px] text-slate-300 uppercase tracking-wider px-3 pb-2 border-b border-white/[0.08]">
            Topics ({filteredDocs.length})
          </div>

          {filteredDocs.map((doc) => (
            <button
              key={doc.id}
              onClick={() => setActiveDoc(doc)}
              className={`w-full text-left rounded-xl px-3 py-2.5 transition-all flex items-center justify-between ${
                activeDoc.id === doc.id
                  ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-semibold"
                  : "text-slate-300 hover:bg-white/[0.04] hover:text-white"
              }`}
            >
              <span>{doc.title}</span>
              <span className="text-[10px] text-slate-300 uppercase">{doc.category}</span>
            </button>
          ))}

          <div className="pt-6">
            <Link
              href="/api"
              className="block rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 text-slate-300 hover:border-cyan-500/30 hover:text-white transition"
            >
              <span className="text-[10px] text-cyan-400 uppercase tracking-wider block">API Reference &rarr;</span>
              <span className="font-sans font-bold text-xs mt-1 block">Inspect REST Endpoints</span>
            </Link>
          </div>
        </div>

        {/* Content Pane (Span 8) */}
        <div className="lg:col-span-8 rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-10 backdrop-blur-xl shadow-2xl space-y-6">
          <div className="border-b border-white/[0.08] pb-4">
            <span className="rounded bg-cyan-500/15 border border-cyan-500/30 px-2.5 py-0.5 font-mono text-[10px] font-bold text-cyan-300">
              {activeDoc.category.toUpperCase()}
            </span>
            <h2 className="mt-3 text-2xl font-bold text-white sm:text-3xl">{activeDoc.title}</h2>
          </div>

          <div className="space-y-4 text-slate-300 text-sm leading-relaxed">
            {activeDoc.content.map((p, idx) => (
              <p key={idx}>{p}</p>
            ))}
          </div>

          {activeDoc.codeSnippet && (
            <div className="pt-2">
              <span className="font-mono text-xs text-slate-300 uppercase block mb-2">Example Reference</span>
              <pre className="rounded-2xl border border-white/[0.08] bg-[#02050b] p-4 font-mono text-xs text-cyan-300 overflow-x-auto leading-relaxed">
                {activeDoc.codeSnippet}
              </pre>
            </div>
          )}

          <div className="pt-6 border-t border-white/[0.08] flex items-center justify-between">
            <span className="text-xs text-slate-300 font-mono">
              Have questions? Reach out to our intelligence desk.
            </span>
            <Link
              href="/contact"
              className="font-mono text-xs text-cyan-400 hover:text-cyan-300 transition"
            >
              Contact Support &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
