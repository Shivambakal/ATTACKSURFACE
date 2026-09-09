"use client";

import React from "react";
import Link from "next/link";

export default function SecurityPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-950/40 px-3.5 py-1 text-xs font-mono text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          TRUST &amp; PLATFORM SECURITY
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          Security at <span className="text-cyan-400">AttackSurface</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          As a continuous security intelligence platform, our credibility rests on uncompromising adherence to ethical research standards, data integrity, and strict platform defense.
        </p>
      </div>

      {/* Security Pillars */}
      <div className="mt-14 space-y-8">
        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-mono font-bold text-sm">
              01
            </div>
            <h2 className="text-xl font-bold text-white">The Zero-Weaponization Guarantee</h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            AttackSurface is strictly an observation engine, not an active attack tool. We never execute injection attacks (SQLi, XSS, SSRF), payload fuzzing, brute force dictionary attacks, or unauthorized privilege escalation. All telemetry is captured through standard, non-intrusive DNS queries (RFC 1035), Certificate Transparency monitoring (RFC 6962), and benign HTTP GET/HEAD requests.
          </p>
        </div>

        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-mono font-bold text-sm">
              02
            </div>
            <h2 className="text-xl font-bold text-white">Data Integrity &amp; Cryptographic Truth</h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            We adhere to a strict Zero-Fabrication standard. We do not invent synthetic target vulnerabilities, extrapolate speculative threat numbers, or fabricate company metrics. Every flagged delta is backed by raw wire telemetry with a verifiable SHA-256 checksum and timestamp.
          </p>
        </div>

        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400 font-mono font-bold text-sm">
              03
            </div>
            <h2 className="text-xl font-bold text-white">Infrastructure &amp; Cryptographic Protection</h2>
          </div>
          <ul className="space-y-2 text-xs sm:text-sm text-slate-300 leading-relaxed list-disc list-inside">
            <li><strong>Encryption in Transit:</strong> TLS 1.3 enforced across all web interfaces, WebSocket channels, and REST endpoints with strict HSTS preloading.</li>
            <li><strong>Encryption at Rest:</strong> Database volumes and Redis memory snapshots encrypted with AES-256.</li>
            <li><strong>Role-Based Access Control (RBAC):</strong> Granular permissions separating standard researcher sessions from administrative operations.</li>
            <li><strong>Audit Trails:</strong> Immutable audit logs tracking all administrative interventions, source configurations, and telemetry pipelines.</li>
          </ul>
        </div>

        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 font-mono font-bold text-sm">
              04
            </div>
            <h2 className="text-xl font-bold text-white">Researcher Privacy &amp; Watchlist Confidentiality</h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            Your research targets, active watchlists, and temporal queries are strictly confidential. AttackSurface does not monetize researcher search patterns, sell targeting queries to third parties, or alert targets to your investigative focus.
          </p>
        </div>
      </div>

      {/* Reporting Banner */}
      <div className="mt-16 rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6 text-center space-y-3">
        <h3 className="text-lg font-bold text-white">Found a security issue in AttackSurface?</h3>
        <p className="text-xs text-slate-300 max-w-lg mx-auto">
          We welcome vulnerability disclosures through our official security desk at{" "}
          <a href="mailto:attacksurface.alerts@gmail.com" className="text-cyan-400 underline font-mono">
            attacksurface.alerts@gmail.com
          </a>.
        </p>
        <div className="pt-2">
          <Link
            href="/responsible-disclosure"
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-2 font-mono text-xs font-bold text-slate-950 hover:bg-cyan-400 transition"
          >
            <span>Read Responsible Disclosure Policy</span>
            <span>&rarr;</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
