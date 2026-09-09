"use client";

import React from "react";
import Link from "next/link";

export default function ResponsibleDisclosurePage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
          VULNERABILITY DISCLOSURE PROGRAM
        </div>

        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl font-sans">
          Responsible <span className="text-cyan-400">Disclosure Policy</span>.
        </h1>

        <p className="text-base text-slate-300 leading-relaxed">
          At AttackSurface, we respect and collaborate with the security research community. If you have discovered a vulnerability within our platform, we invite you to disclose it responsibly so we can remediate it promptly.
        </p>
      </div>

      {/* Program Details */}
      <div className="mt-14 space-y-10">
        {/* Scope */}
        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <h2 className="text-xl font-bold text-white">In-Scope Target Systems</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs">
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-3">
              <span className="text-emerald-400 block font-bold">attacksurface.online</span>
              <span className="text-slate-300 text-[11px]">Primary web application &amp; researcher console</span>
            </div>
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-3">
              <span className="text-emerald-400 block font-bold">api.attacksurface.online</span>
              <span className="text-slate-300 text-[11px]">Public REST API gateway</span>
            </div>
          </div>
          <p className="text-xs text-slate-300">
            * Note: Third-party services used for payment processing or transactional email are out of scope.
          </p>
        </div>

        {/* Safe Harbor */}
        <div className="rounded-3xl border border-emerald-500/30 bg-emerald-950/15 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-emerald-400 font-mono text-sm font-bold">✓ SAFE HARBOR GUARANTEE</span>
          </div>
          <h2 className="text-xl font-bold text-white">Legal Protection for Good-Faith Researchers</h2>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            If you conduct vulnerability research in good faith and in compliance with this policy, we consider your activities authorized. We will not pursue civil action or initiate legal complaints against you regarding your research activities.
          </p>
        </div>

        {/* Ground Rules */}
        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/80 p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-4">
          <h2 className="text-xl font-bold text-white">Researcher Guidelines</h2>
          <ul className="space-y-3 text-xs sm:text-sm text-slate-300 leading-relaxed list-disc list-inside">
            <li><strong>Do not degrade platform availability:</strong> Denial-of-Service (DoS/DDoS) attacks, distributed flood testing, or resource exhaustion attacks are strictly prohibited.</li>
            <li><strong>Protect user privacy:</strong> Never view, alter, extract, or delete data belonging to other user accounts. If a vulnerability reveals data belonging to another user, stop immediately and report.</li>
            <li><strong>No social engineering:</strong> Phishing, vishing, or social engineering targeting AttackSurface staff or contractors is strictly prohibited.</li>
            <li><strong>Coordinated disclosure:</strong> Give us reasonable time (up to 90 days) to address the vulnerability before discussing or publishing any details publicly.</li>
          </ul>
        </div>

        {/* Reporting Channel & SLA */}
        <div className="rounded-3xl border border-white/[0.08] bg-[#02050b] p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-5">
          <h2 className="text-xl font-bold text-white">How to Submit a Report</h2>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            Please email your findings directly to our security intelligence team at:
          </p>

          <div className="rounded-2xl border border-cyan-500/30 bg-cyan-950/20 p-4 font-mono text-xs flex items-center justify-between">
            <span className="text-cyan-300 font-bold">attacksurface.alerts@gmail.com</span>
            <a
              href="mailto:attacksurface.alerts@gmail.com"
              className="rounded-lg bg-cyan-500 px-3 py-1 font-bold text-slate-950 hover:bg-cyan-400 transition"
            >
              Send Email
            </a>
          </div>

          <div className="space-y-2 text-xs font-mono text-slate-300 pt-2 border-t border-white/[0.08]">
            <p>• Initial Acknowledgement SLA: <strong>&le; 24 Hours</strong></p>
            <p>• Triage Assessment SLA: <strong>&le; 72 Hours</strong></p>
            <p>• Please include: Summary, step-by-step reproduction guide, and proof-of-concept.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
