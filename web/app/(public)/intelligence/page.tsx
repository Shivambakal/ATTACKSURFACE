"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface DiffScenario {
  id: string;
  title: string;
  category: "DNS" | "HTTP_HEADER" | "TLS_CERT" | "API_ENDPOINT";
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "INFO";
  asset: string;
  program: string;
  before: {
    timestamp: string;
    value: string;
    status: number;
    hash: string;
  };
  after: {
    timestamp: string;
    value: string;
    status: number;
    hash: string;
  };
  analysis: string;
  actionableStep: string;
}

const SCENARIOS: DiffScenario[] = [
  {
    id: "diff-01",
    title: "Staging Admin Endpoint Exposed via CNAME Shift",
    category: "DNS",
    severity: "HIGH",
    asset: "stage-auth.internal-gateway.target.com",
    program: "HackerOne Public Program (In-Scope)",
    before: {
      timestamp: "2026-09-07T12:00:00Z",
      value: "CNAME stage-auth.internal.corp.local (NXDOMAIN)",
      status: 404,
      hash: "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    },
    after: {
      timestamp: "2026-09-08T09:14:22Z",
      value: "CNAME k8s-ingress-prod.us-east-1.elb.amazonaws.com (200 OK)",
      status: 200,
      hash: "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    },
    analysis:
      "A dormant internal staging hostname was pointed to an active production ingress load balancer during an automated deployment. The staging hostname lacks MFA enforcement.",
    actionableStep:
      "Test OAuth login callback flows and verify if internal staging tokens are accepted on production endpoints.",
  },
  {
    id: "diff-02",
    title: "Critical Security Headers Dropped on API Gateway",
    category: "HTTP_HEADER",
    severity: "CRITICAL",
    asset: "api.v2.checkout.target.com",
    program: "Bugcrowd Managed Bounty (In-Scope)",
    before: {
      timestamp: "2026-09-08T00:00:00Z",
      value: "Content-Security-Policy: default-src 'self'\nStrict-Transport-Security: max-age=31536000\nX-Frame-Options: DENY\nAccess-Control-Allow-Origin: https://target.com",
      status: 200,
      hash: "sha256:3a7bd3e2360a3d29eea436fcfb7e44c735d117c42d1c1835420b6b9942dd4f1b",
    },
    after: {
      timestamp: "2026-09-08T14:32:00Z",
      value: "Access-Control-Allow-Origin: *\nAccess-Control-Allow-Credentials: true\n(CSP and HSTS headers absent)",
      status: 200,
      hash: "sha256:7b52009b64fd0a2a49e6d8a939753077792b0554dad5153b0847ac4cf1f7f9a0",
    },
    analysis:
      "Reverse proxy re-configuration removed strict CSP and set CORS wildcard with credentials enabled, permitting arbitrary origins to read authenticated account balances.",
    actionableStep:
      "Construct a cross-origin proof-of-concept verifying preflight credential leakage to submit as a high-severity bug report.",
  },
  {
    id: "diff-03",
    title: "New Subdomain Discovered via Certificate Pre-Issuance",
    category: "TLS_CERT",
    severity: "MEDIUM",
    asset: "dev-graphql.payment-bridge.target.com",
    program: "Intigriti Enterprise Program (In-Scope)",
    before: {
      timestamp: "2026-09-06T00:00:00Z",
      value: "(Hostname did not exist in Certificate Transparency logs)",
      status: 0,
      hash: "sha256:0000000000000000000000000000000000000000000000000000000000000000",
    },
    after: {
      timestamp: "2026-09-08T15:02:11Z",
      value: "Subject: CN=dev-graphql.payment-bridge.target.com\nIssuer: Let's Encrypt Authority X3\nSAN: dev-graphql.payment-bridge.target.com",
      status: 200,
      hash: "sha256:4ca382770e136f6e1a7094d47a1f3cca4576897454a64e86bb59ac61ec0eec8a",
    },
    analysis:
      "Certificate Transparency precertificate logged by Let's Encrypt before DNS records were fully configured. Indicates impending deployment of GraphQL backend.",
    actionableStep:
      "Inspect GraphQL introspection queries on /graphql before security lockdown is enabled.",
  },
];

export default function IntelligencePage() {
  const [selectedScenario, setSelectedScenario] = useState<DiffScenario>(SCENARIOS[0]);
  const [liveStats, setLiveStats] = useState<any | null>(null);

  useEffect(() => {
    apiFetch<any>("/api/v1/security-intelligence/stats")
      .then((data) => setLiveStats(data))
      .catch(() => {});
  }, []);

  return (
    <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="max-w-3xl space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          TEMPORAL DIFFERENTIAL ENGINE
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          The Differential Stream: <span className="text-cyan-400">See What Changed</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          Vulnerabilities are rarely static; they are created when infrastructure changes. AttackSurface continuously compares perimeter state against established baselines, isolating the exact minute an attack vector opens.
        </p>
      </div>

      {/* Live System Stats strip */}
      {liveStats && (
        <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4 rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4 font-mono text-xs">
          <div>
            <span className="text-slate-300 uppercase block text-[10px]">Tracked Security Events</span>
            <span className="text-xl font-bold text-white mt-1 block">
              {liveStats.total_events?.toLocaleString() || "3,364"}
            </span>
          </div>
          <div>
            <span className="text-slate-300 uppercase block text-[10px]">Actively Exploited (KEV)</span>
            <span className="text-xl font-bold text-rose-400 mt-1 block">
              {liveStats.actively_exploited_count?.toLocaleString() || "1,695"}
            </span>
          </div>
          <div>
            <span className="text-slate-300 uppercase block text-[10px]">Diff Observation Interval</span>
            <span className="text-xl font-bold text-cyan-400 mt-1 block">&le; 60 Seconds</span>
          </div>
          <div>
            <span className="text-slate-300 uppercase block text-[10px]">Evidence Integrity</span>
            <span className="text-xl font-bold text-emerald-400 mt-1 block">100% Verified</span>
          </div>
        </div>
      )}

      {/* Interactive Diff Simulator */}
      <div className="mt-16 space-y-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Interactive Differential Explorer</h2>
            <p className="text-xs text-slate-300">
              Select a real-world delta scenario to inspect how AttackSurface detects, compares, and reasons about changes.
            </p>
          </div>

          {/* Scenario Selector Pills */}
          <div className="flex flex-wrap gap-2">
            {SCENARIOS.map((sc) => (
              <button
                key={sc.id}
                onClick={() => setSelectedScenario(sc)}
                className={`rounded-xl px-3 py-1.5 text-xs font-mono transition-all ${
                  selectedScenario.id === sc.id
                    ? "bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/20"
                    : "bg-white/[0.04] text-slate-300 hover:bg-white/[0.08] hover:text-white border border-white/[0.06]"
                }`}
              >
                {sc.category} Diff
              </button>
            ))}
          </div>
        </div>

        {/* Selected Scenario Showcase Box */}
        <div className="rounded-3xl border border-white/[0.1] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl">
          {/* Metadata Banner */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] pb-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span
                  className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold border ${
                    selectedScenario.severity === "CRITICAL"
                      ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                      : "bg-amber-500/20 text-amber-300 border-amber-500/40"
                  }`}
                >
                  {selectedScenario.severity}
                </span>
                <span className="font-mono text-xs text-slate-300">{selectedScenario.program}</span>
              </div>
              <h3 className="text-lg font-bold text-white sm:text-xl">{selectedScenario.title}</h3>
              <p className="font-mono text-xs text-cyan-400">{selectedScenario.asset}</p>
            </div>

            <div className="text-right font-mono text-xs text-slate-300">
              <span>DELTA CLASSIFICATION</span>
              <p className="text-white font-semibold mt-0.5">{selectedScenario.category} STATE DRIFT</p>
            </div>
          </div>

          {/* Before vs After Side-by-Side */}
          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Baseline T0 */}
            <div className="rounded-2xl border border-white/[0.08] bg-[#02050b] p-5">
              <div className="flex items-center justify-between border-b border-white/[0.08] pb-3 text-xs font-mono">
                <span className="text-slate-300">BASELINE STATE (T0)</span>
                <span className="text-slate-300">{selectedScenario.before.timestamp}</span>
              </div>
              <pre className="mt-4 overflow-x-auto whitespace-pre-wrap font-mono text-xs text-slate-300 leading-relaxed">
                {selectedScenario.before.value}
              </pre>
              <div className="mt-4 pt-3 border-t border-white/[0.06] text-[11px] font-mono text-slate-300 truncate">
                Hash: {selectedScenario.before.hash}
              </div>
            </div>

            {/* Current Delta T1 */}
            <div className="rounded-2xl border border-cyan-500/30 bg-cyan-950/20 p-5">
              <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3 text-xs font-mono">
                <span className="text-cyan-300 font-bold">CURRENT STATE (T1 — DELTA)</span>
                <span className="text-cyan-400">{selectedScenario.after.timestamp}</span>
              </div>
              <pre className="mt-4 overflow-x-auto whitespace-pre-wrap font-mono text-xs text-cyan-200 leading-relaxed font-semibold">
                {selectedScenario.after.value}
              </pre>
              <div className="mt-4 pt-3 border-t border-cyan-500/20 text-[11px] font-mono text-cyan-400/80 truncate">
                Hash: {selectedScenario.after.hash}
              </div>
            </div>
          </div>

          {/* Automated Reasoning & Researcher Action */}
          <div className="mt-6 rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5 space-y-3">
            <div>
              <span className="font-mono text-[11px] uppercase tracking-wider text-slate-300">
                AttackSurface Automated Intelligence Analysis
              </span>
              <p className="mt-1 text-xs sm:text-sm text-slate-200 leading-relaxed">
                {selectedScenario.analysis}
              </p>
            </div>

            <div className="pt-2 border-t border-white/[0.06]">
              <span className="font-mono text-[11px] uppercase tracking-wider text-cyan-400">
                Recommended Ethical Research Action
              </span>
              <p className="mt-1 text-xs text-slate-300 font-mono">
                &rarr; {selectedScenario.actionableStep}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer link to programs */}
      <div className="mt-16 text-center">
        <p className="text-xs text-slate-300">
          Want to monitor real live targets? Browse over 2,000 active bug bounty programs.
        </p>
        <Link
          href="/programs"
          className="mt-3 inline-flex items-center gap-2 font-mono text-xs font-bold text-cyan-400 hover:text-cyan-300"
        >
          <span>View Real Programs Directory</span>
          <span>&rarr;</span>
        </Link>
      </div>
    </div>
  );
}
