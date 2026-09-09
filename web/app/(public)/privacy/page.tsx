"use client";

import React from "react";
import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
      <div className="space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.1] bg-white/[0.03] px-3.5 py-1 text-xs font-mono text-slate-300">
          <span>LEGAL POLICY · UPDATED SEPTEMBER 2026</span>
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          Privacy <span className="text-cyan-400">Policy</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          AttackSurface is committed to safeguarding the privacy of security researchers and platform operators. This policy details how we collect, store, and process your data.
        </p>
      </div>

      <div className="mt-14 space-y-8 text-sm text-slate-300 leading-relaxed">
        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <h2 className="text-xl font-bold text-white">1. Information We Collect</h2>
          <p>
            We collect only the minimum personal data required to provide security-change intelligence:
          </p>
          <ul className="list-disc list-inside space-y-2 text-xs sm:text-sm pl-2">
            <li><strong>Account Information:</strong> Name, email address, password hash (via bcrypt), and chosen role when creating an account.</li>
            <li><strong>Research Configuration:</strong> Watchlisted bug bounty programs, custom targets, notification webhooks, and alert settings.</li>
            <li><strong>Authentication Logs:</strong> Timestamps, IP addresses, and user-agent strings for session authorization and brute-force prevention.</li>
          </ul>
        </div>

        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <h2 className="text-xl font-bold text-white">2. Public Internet Telemetry</h2>
          <p>
            AttackSurface ingests public internet telemetry including DNS records, Certificate Transparency logs, HTTP headers, and public bug bounty program scopes. This telemetry is inherently public and is not categorized as user personal data.
          </p>
        </div>

        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <h2 className="text-xl font-bold text-white">3. Zero Selling of Researcher Data</h2>
          <p className="text-white font-medium">
            We will never sell, lease, or monetize your research preferences, queries, or watchlists to advertisers, corporate defense teams, or data brokers.
          </p>
          <p className="text-xs sm:text-sm">
            Your investigative intent is treated with confidentiality. We do not notify target companies when a researcher adds an asset to their watchlist.
          </p>
        </div>

        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <h2 className="text-xl font-bold text-white">4. Data Retention &amp; Deletion (GDPR / CCPA)</h2>
          <p>
            Under the European Union General Data Protection Regulation (GDPR) and the California Consumer Privacy Act (CCPA), you retain the right to:
          </p>
          <ul className="list-disc list-inside space-y-1 text-xs sm:text-sm pl-2">
            <li>Access all personal data linked to your account.</li>
            <li>Request immediate deletion and erasure of your account profile.</li>
            <li>Export your watchlists and research data in standard JSON format.</li>
          </ul>
        </div>

        <div className="rounded-3xl border border-white/[0.08] bg-[#02050b] p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-3">
          <h2 className="text-xl font-bold text-white">5. Contact Our Privacy Officer</h2>
          <p className="text-xs sm:text-sm">
            If you have questions regarding this Privacy Policy or wish to request data erasure, please reach out to:
          </p>
          <p className="font-mono text-cyan-400 text-xs">
            attacksurface.alerts@gmail.com
          </p>
        </div>
      </div>
    </div>
  );
}
