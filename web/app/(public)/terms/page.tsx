"use client";

import React from "react";
import Link from "next/link";

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
      <div className="space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.1] bg-white/[0.03] px-3.5 py-1 text-xs font-mono text-slate-300">
          <span>TERMS OF SERVICE · UPDATED SEPTEMBER 2026</span>
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          Terms of <span className="text-cyan-400">Service</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          Please review these Terms of Service carefully before utilizing the AttackSurface platform, REST API, or intelligence streams.
        </p>
      </div>

      <div className="mt-14 space-y-8 text-sm text-slate-300 leading-relaxed">
        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <h2 className="text-xl font-bold text-white">1. Authorized Research &amp; Acceptable Use Policy</h2>
          <p>
            AttackSurface is engineered exclusively for defensive cybersecurity monitoring, authorized security assessments, and ethical bug bounty research under recognized platform policies (e.g. HackerOne, Bugcrowd, Intigriti).
          </p>
          <div className="rounded-2xl border border-rose-500/30 bg-rose-950/20 p-4 text-xs font-mono text-rose-300 space-y-2">
            <span className="font-bold block">STRICT PROHIBITION AGAINST HARMFUL ACTIVITIES:</span>
            <p>
              You agree never to use AttackSurface telemetry, differential alerts, or asset discoveries to execute unauthorized intrusions, data theft, extortion, Denial-of-Service attacks, or any activity in violation of the Computer Fraud and Abuse Act (CFAA) or applicable local laws.
            </p>
          </div>
        </div>

        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <h2 className="text-xl font-bold text-white">2. Subscription Tiers, Billing &amp; Refunds</h2>
          <p>
            AttackSurface offers free Community Hunter access along with paid subscription plans (Pro Hunter, Enterprise Team).
          </p>
          <ul className="list-disc list-inside space-y-2 text-xs sm:text-sm pl-2">
            <li>Paid subscriptions are billed in advance on a recurring monthly or annual cycle.</li>
            <li>You may cancel recurring subscriptions at any time via your Account Settings. Cancellation takes effect at the conclusion of the current billing period.</li>
            <li>Export limits and API rate limits are enforced in accordance with your designated plan tier.</li>
          </ul>
        </div>

        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <h2 className="text-xl font-bold text-white">3. Disclaimer of Warranties &amp; Limitation of Liability</h2>
          <p>
            AttackSurface provides continuous security-change intelligence on an &quot;AS IS&quot; and &quot;AS AVAILABLE&quot; basis. While we strive for absolute accuracy and zero synthetic data, public internet infrastructure is fluid and subject to upstream third-party modifications.
          </p>
          <p className="text-xs sm:text-sm text-slate-300">
            In no event shall AttackSurface, its developers, or affiliates be liable for any indirect, punitive, or consequential damages resulting from your use of the platform or reliance on public telemetry data.
          </p>
        </div>

        <div className="rounded-3xl border border-white/[0.08] bg-[#02050b] p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-3">
          <h2 className="text-xl font-bold text-white">4. Governing Law &amp; Inquiries</h2>
          <p className="text-xs sm:text-sm">
            For legal inquiries or questions regarding these terms, please contact:
          </p>
          <p className="font-mono text-cyan-400 text-xs">
            attacksurface.alerts@gmail.com
          </p>
        </div>
      </div>
    </div>
  );
}
